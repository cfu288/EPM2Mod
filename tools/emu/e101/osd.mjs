// E-PM2 OSD draw engine 0x9AA00000 (same command family as om-emu's src/dev/engine.mjs, another register use).
// Registers (driver 0x7ECCD276..0x7ECCE2xx, VERIFIED by reading it): +0x04 status (bit 0 done, bit 1 error; write 1 to
// clear), +0x08 interrupt enable, IRQ 111 = status & enable; +0x18 / +0x1C command list address (CPU uncached alias),
// +0x20 = 1 list mode, +0x38 / +0x3C command count, +0x24 start (1 = list, 2 = the FIFO written through +0x28),
// +0x2C = 1 FIFO reset. Commands run at the start write; completion is immediate (FAKE timing).
import { h8 } from './machine.mjs';
export function installOsd(e) {
  const intc = e.m.devices.intc;
  intc.drive(111);
  const o = e.osd = { st: 0, en: 0, fifo: [], runs: 0, cmds: 0, log: [], unknown: new Map(), lut: new Uint8Array(256), trace: null };
  const line = () => intc.setLine(111, (o.st & o.en & 3) !== 0);
  const cpu = (a) => (((a >>> 0) & 0x3FFFFFFF) | 0x40000000) >>> 0;     // engine bus address / CPU alias -> the cached CPU address
  o.cpu = cpu;
  const len = (w0) => { switch (w0 & 0xff) { case 0x10: return 4; case 0x20: return 5; case 0x30: return 4 + ((w0 & 0x6000) ? 1 : 0) + ((w0 & 0x1000) ? 4 : 0); case 0x40: case 0x41: return 2; case 0x60: return 5; case 0xff: return 1; default: return 0; } };
  // Pixel access. A surface is addressed in bits: `bits` = byte address * 8 + bit offset; depth d = log2(bits per pixel)
  // (2 = 4 bpp, 3 = 8 bpp). 4 bpp pixels: the low nibble is the left pixel (INFERRED; checked on rendered text).
  const RAM0 = 0x60000000;
  const rdPix = (bits, d) => { const a = cpu(bits / 8); if (d === 3) return e.r8(a); const b = e.r8(a); return (bits & 4) ? b >> 4 : b & 15; };
  const wrPix = (bits, d, v) => { const a = cpu(bits / 8); if (d === 3) { e.w8(a, v); return; } const b = e.r8(a); e.w8(a, (bits & 4) ? (b & 0x0f) | ((v & 15) << 4) : (b & 0xf0) | (v & 15)); };
  const hi = (w0) => (w0 & 0x60000000) >>> 0;
  const dims = (w) => ({ h: (w & 0x7ff) + 1, wd: ((w >>> 11) & 0x7ff) + 1, stride: (w >>> 22) * 64 });
  const bad = (msg, w) => { const k = msg + ' ' + h8(w[0]); if (!o.unknown.has(k)) o.log.push(`${msg}: ${w.map((x) => h8(x)).join(' ')}`); o.unknown.set(k, (o.unknown.get(k) || 0) + 1); };
  // 0x10 fill: w0 = opcode | depth << 8 | address bits 29..30; w1 = colour; w2 = (address & 0x1FFFFFFF) << 3 | bit;
  //   w3 = (lines - 1) | (width - 1) << 11 | (stride bytes / 64) << 22        (builder 0x7ECCD77A, VERIFIED by reading it)
  const fill = (w) => {
    const d = (w[0] >>> 8) & 7, { h, wd, stride } = dims(w[3]), base = (hi(w[0]) + (w[2] >>> 3)) * 8 + (w[2] & 7), bpp = 1 << d;
    if (d !== 2 && d !== 3) return bad('fill depth', w);
    for (let y = 0; y < h; y++) {
      const row = base + y * stride * 8;
      if (d === 3) { e.wr(cpu(row / 8), new Uint8Array(wd).fill(w[1] & 255)); continue; }
      if (!(row & 7) && !(wd & 1)) { e.wr(cpu(row / 8), new Uint8Array(wd / 2).fill((w[1] & 15) * 0x11)); continue; }
      for (let x = 0; x < wd; x++) wrPix(row + x * bpp, d, w[1]);
    }
  };
  // 0x20 copy: w0 = opcode | depth << 8 | source address bits 29..30 at bits 26..27 | destination's at 29..30;
  //   w1 = source << 3; w2 = size and source stride (as fill's w3); w3 = destination << 3; w4 = destination stride << 22
  const copy = (w) => {
    const d = (w[0] >>> 8) & 7, { h, wd, stride } = dims(w[2]), dstride = (w[4] >>> 22) * 64, bpp = 1 << d;
    const src = ((((w[0] >>> 26) & 3) << 29 >>> 0) + (w[1] >>> 3)) * 8 + (w[1] & 7), dst = (hi(w[0]) + (w[3] >>> 3)) * 8 + (w[3] & 7);
    if (d !== 2 && d !== 3) return bad('copy depth', w);
    const nbytes = d === 3 ? wd : (wd + 1) >> 1, whole = !(src & 7) && !(dst & 7) && (d === 3 || !(wd & 1));
    for (let y = 0; y < h; y++) {
      const s = src + y * stride * 8, t = dst + y * dstride * 8;
      if (whole) { e.wr(cpu(t / 8), e.rd(cpu(s / 8), nbytes).slice()); continue; }
      const row = []; for (let x = 0; x < wd; x++) row.push(rdPix(s + x * bpp, d));
      for (let x = 0; x < wd; x++) wrPix(t + x * bpp, d, row[x]);
    }
  };
  // 0x40 colour table: w1 = address >> 6; 256 bytes
  const lut = (w) => { o.lut = e.rd(cpu((w[1] << 6) >>> 0), 256).slice(); o.lutAddr = cpu((w[1] << 6) >>> 0); };
  // 0x30 run-length bitmap: w0 = opcode | depth << 8 | 0x800 through a colour table | 0x1000 the table is the 4 words
  //   after w3 (16 entries) | 0x2000 / 0x4000 scaled (one more word; not modelled); w1 = source (CPU address);
  //   w2 = destination << 3 | bit; w3 = stride bytes / 64 (0x0E = 896 for the 8-bit plane, 7 = 448 for a 4-bit plane; an earlier reading
  //   `(w3 >> 1) * 128` gave 384 for the 4-bit planes and sheared every 4-bit bitmap into stripes). Source: 4-byte header {lines - 1 : 12, width - 1 : 12,
  //   format : 8}, then tokens (formats as in om-emu's engine model for later bodies: 1, 2, 3, 9, 0x0A, 0x0B).
  //   A pixel whose token colour is 0, or whose table value is 0, is not written (transparent; INFERRED).
  const field64 = (lo, hiw, start, n) => (start >= 32 ? hiw >>> (start - 32) : start + n <= 32 ? lo >>> start : (lo >>> start) | (hiw << (32 - start)));
  const bitmap = (w) => {
    const d = (w[0] >>> 8) & 7, src = cpu(w[1]);
    if (w[0] & 0x6000) bad('bitmap scaled (drawn unscaled)', w);
    if (d !== 2 && d !== 3) return bad('bitmap depth', w);
    const hdr = e.rd(src, 4), lines = (hdr[0] | (hdr[1] & 0xF) << 8) + 1, width = (hdr[1] >> 4 | hdr[2] << 4) + 1, fmt = hdr[3];
    let bits, runbits, perWord;
    switch (fmt) {
      case 0x02: case 0x0A: bits = 8; runbits = 4; perWord = 0; break;
      case 0x09: bits = 8; runbits = 6; perWord = 0; break;
      case 0x01: bits = 4; runbits = 2; perWord = 16; break;
      case 0x03: bits = 10; runbits = 2; perWord = 6; break;
      case 0x0B: bits = 12; runbits = 4; perWord = 5; break;
      default: return bad('bitmap format ' + fmt, w);
    }
    const useLut = (w[0] & 0x800) !== 0, inline = (w[0] & 0x1000) !== 0, map = new Uint8Array(256);
    const ext = 4 + ((w[0] & 0x6000) ? 1 : 0);
    if (inline) for (let i = 0; i < 16; i++) map[i] = w[ext + (i >> 2)] >>> (8 * (i % 4));
    else if (useLut) map.set(o.lut);
    else for (let i = 0; i < 256; i++) map[i] = i;
    const stride = (w[3] & 0x7ff) << 6, dst = (hi(w[0]) + (w[2] >>> 3)) * 8 + (w[2] & 7), bpp = 1 << d;
    const total = width * lines, need = perWord ? Math.ceil(total / perWord) * 8 : total;
    const data = e.rd(src + 4, Math.min(need + 8, 0x40000)), dv = new DataView(data.buffer, data.byteOffset, data.length);
    const px = new Uint8Array(total), mask = 2 ** bits - 1, runmask = (1 << runbits) - 1;
    let count = 0, pos = 0;
    while (count < total && pos + (perWord ? 8 : 1) <= data.length) {
      if (perWord) {
        const lo = dv.getUint32(pos, true), hw = dv.getUint32(pos + 4, true);
        for (let k = 0; k < perWord && count < total; k++) { const t = field64(lo, hw, bits * k, bits) & mask, run = (t & runmask) + 1; px.fill(t >>> runbits, count, Math.min(total, count + run)); count += run; }
        pos += 8;
      } else { const t = data[pos++], run = (t & runmask) + 1; px.fill(t >>> runbits, count, Math.min(total, count + run)); count += run; }
    }
    for (let y = 0; y < lines; y++) for (let x = 0; x < width; x++) {
      const idx = px[y * width + x], v = map[idx];
      if (idx === 0 || v === 0) continue;
      wrPix(dst + (y * stride * 8) + x * bpp, d, v);
    }
    o.bitmaps++;
  };
  o.bitmaps = 0;
  o.exec = (w) => {
    o.cmds++;
    if (o.trace) o.trace(w);
    const op = w[0] & 0xff;
    o.unknown.set(op, (o.unknown.get(op) || 0) + 1);
    try {
      if (op === 0x10) fill(w); else if (op === 0x20) copy(w); else if (op === 0x30) bitmap(w); else if (op === 0x40) lut(w); else bad('opcode not modelled', w);
    } catch (err) { bad('error ' + err.message, w); }
  };
  const run = (words) => {
    o.runs++;
    for (let i = 0; i < words.length;) {
      const n = len(words[i]);
      if (!n) { o.log.push(`unknown opcode ${h8(words[i])} at word ${i}`); break; }
      if ((words[i] & 0xff) === 0xff) break;
      o.exec(words.slice(i, i + n)); i += n;
    }
  };
  e.mmio.set(0x9AA, {
    read(a) { if (a === 0x9AA00004) return o.st; return undefined; },
    write(a, v) {
      const off = a - 0x9AA00000;
      if (off === 0x04) { o.st &= ~v; line(); return true; }
      if (off === 0x08) { o.en = v >>> 0; line(); return false; }
      if (off === 0x28) { o.fifo.push(v >>> 0); return false; }
      if (off === 0x2C) { if (v & 1) o.fifo = []; return false; }
      if (off === 0x24 && v) {
        if (v === 1) {
          const base = cpu(e.store.get(0x9AA00018) ?? 0), words = [];
          for (let i = 0; i < 0x4000; i++) { const w = e.r32(base + 4 * i); words.push(w); if ((w & 0xff) === 0xff && false) break; }
          // the list ends with a word 0xFF; read command by command
          const out = []; let p = 0;
          for (;;) { const n = len(words[p]); if (!n) { o.log.push(`list: unknown ${h8(words[p])}`); break; } for (let k = 0; k < n; k++) out.push(words[p + k]); if ((words[p] & 0xff) === 0xff) break; p += n; if (p > 0x3ff0) break; }
          run(out);
        } else { run(o.fifo); o.fifo = []; }
        o.st |= 1; line();
        return false;
      }
      return false;
    },
  });
}

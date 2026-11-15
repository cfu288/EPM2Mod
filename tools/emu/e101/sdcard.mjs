// SD card model at the E-PM2's command seam, and a FAT16 image builder (our code).
//
// Seam: the SD driver's command exchange 0x7E5CEABB(a0 = host context, a1 = command record), hooked as S-SDCMD in
// boot.mjs, which calls e.sdCmd(record). Record layout (VERIFIED by reading 0x7E5CE3E1, 0x7E5CE767, 0x7E5CBF44, 0x7E5CC3D6):
//   +8 completion callback, +12 u16 host slot, +14 u16 type (3 = a card command; 0, 4, 0x10, 0x11, 0x12 = host set-up)
//   +36 command word: bits 0..5 index, bits 6..7 = 01 application command (the driver sends CMD55 itself natively),
//       bits 8..10 response form (3 = none, 6 = R2: 8 half-words, else 32 bits), bit 11 = with data
//   +40 argument, +44..+59 response (R2: bits 8..127 of the register, low word first)
//   +60 data buffer (bus address; 0 = no data), +64 block count, +68 block size, +73 u8 direction (0 = read from card)
//   +88 u16 status: 0 = done, 0x1405 = no response, 0x1404 = error
// The card: SD version 2, standard capacity (byte addresses in CMD17/18/24/25), one FAT16 partition behind an MBR.
import fs from 'node:fs';
import path from 'node:path';

// ---- FAT16 image from a host folder (8.3 names only; sub-folders allowed)
export function buildFatImage(dir, { sizeMiB = 64, label = 'E101EMU' } = {}) {
  const SEC = 512, total = sizeMiB * 2048, partStart = 63, partSecs = total - partStart, spc = 8, reserved = 1, nfats = 2, rootEnts = 512;
  const rootSecs = rootEnts * 32 / SEC;
  let fatSecs = 1;
  for (;;) { const clusters = Math.floor((partSecs - reserved - nfats * fatSecs - rootSecs) / spc); const need = Math.ceil((clusters + 2) * 2 / SEC); if (need <= fatSecs) break; fatSecs = need; }
  const dataStart = partStart + reserved + nfats * fatSecs + rootSecs, clusters = Math.floor((total - dataStart) / spc);
  const img = Buffer.alloc(total * SEC), fat = Buffer.alloc(fatSecs * SEC);
  fat.writeUInt16LE(0xFFF8, 0); fat.writeUInt16LE(0xFFFF, 2);
  let next = 2;
  const alloc = (data) => {                      // -> first cluster (0 for empty)
    const n = Math.ceil(data.length / (spc * SEC)); if (!n) return 0;
    if (next + n > clusters + 2) throw new Error('FAT image full');
    const first = next;
    for (let i = 0; i < n; i++) fat.writeUInt16LE(i === n - 1 ? 0xFFFF : next + i + 1, 2 * (next + i));
    data.copy(img, (dataStart + (first - 2) * spc) * SEC);
    next += n; return first;
  };
  const name83 = (n) => { const m = /^([^.]{1,8})(?:\.([^.]{0,3}))?$/.exec(n.toUpperCase()); if (!m) throw new Error(`not an 8.3 name: ${n}`); return Buffer.from(m[1].padEnd(8) + (m[2] || '').padEnd(3), 'latin1'); };
  const DATE = ((2026 - 1980) << 9) | (11 << 5) | 14, TIME = 12 << 11;
  const entry = (nameBuf, attr, cluster, size) => { const e = Buffer.alloc(32); nameBuf.copy(e, 0); e[11] = attr; e.writeUInt16LE(TIME, 14); e.writeUInt16LE(DATE, 16); e.writeUInt16LE(DATE, 18); e.writeUInt16LE(TIME, 22); e.writeUInt16LE(DATE, 24); e.writeUInt16LE(cluster, 26); e.writeUInt32LE(size, 28); return e; };
  const files = [];
  const addDir = (hostDir, parentCluster, isRoot, rel) => {         // -> directory bytes
    const ents = [];
    if (isRoot) ents.push(entry(Buffer.from(label.padEnd(11).slice(0, 11), 'latin1'), 0x08, 0, 0));
    const self = { cluster: 0 };
    const kids = hostDir ? fs.readdirSync(hostDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name)) : [];
    const pending = [];
    for (const k of kids) {
      const p = path.join(hostDir, k.name);
      if (k.isDirectory()) pending.push([k.name, p]);
      else if (k.isFile()) { const data = fs.readFileSync(p); ents.push(entry(name83(k.name), 0x20, alloc(data), data.length)); files.push(`${rel}/${k.name.toUpperCase()} ${data.length}`); }
    }
    return { ents, pending, self };
  };
  // directories are laid out depth first; a sub-directory needs its own cluster before its entries are final
  const layoutDir = (hostDir, parentCluster, rel) => {
    const { ents, pending } = addDir(hostDir, parentCluster, false, rel);
    const sub = [];
    const nEnts = 2 + ents.length + pending.length, bytes = Math.ceil(nEnts * 32 / (spc * SEC)) * spc * SEC;
    const my = alloc(Buffer.alloc(bytes));
    for (const [n, p] of pending) sub.push(entry(name83(n), 0x10, layoutDir(p, my, `${rel}/${n.toUpperCase()}`), 0));
    const dot = entry(Buffer.from('.          ', 'latin1'), 0x10, my, 0), dotdot = entry(Buffer.from('..         ', 'latin1'), 0x10, parentCluster, 0);
    Buffer.concat([dot, dotdot, ...ents, ...sub]).copy(img, (dataStart + (my - 2) * spc) * SEC);
    return my;
  };
  const root = addDir(dir, 0, true, '');
  const rootSub = root.pending.map(([n, p]) => entry(name83(n), 0x10, layoutDir(p, 0, `/${n.toUpperCase()}`), 0));
  const rootBuf = Buffer.concat([...root.ents, ...rootSub]);
  if (rootBuf.length > rootEnts * 32) throw new Error('root directory full');
  // MBR
  img[446 + 4] = 0x06; img.writeUInt32LE(partStart, 446 + 8); img.writeUInt32LE(partSecs, 446 + 12); img[510] = 0x55; img[511] = 0xAA;
  // boot sector
  const bs = Buffer.alloc(SEC);
  bs[0] = 0xEB; bs[1] = 0x3C; bs[2] = 0x90; bs.write('MSDOS5.0', 3, 'latin1');
  bs.writeUInt16LE(SEC, 11); bs[13] = spc; bs.writeUInt16LE(reserved, 14); bs[16] = nfats; bs.writeUInt16LE(rootEnts, 17);
  if (partSecs < 65536) bs.writeUInt16LE(partSecs, 19); else bs.writeUInt32LE(partSecs, 32);
  bs[21] = 0xF8; bs.writeUInt16LE(fatSecs, 22); bs.writeUInt16LE(63, 24); bs.writeUInt16LE(255, 26); bs.writeUInt32LE(partStart, 28);
  bs[36] = 0x80; bs[38] = 0x29; bs.writeUInt32LE(0x1010E101, 39); bs.write(label.padEnd(11).slice(0, 11), 43, 'latin1'); bs.write('FAT16   ', 54, 'latin1'); bs[510] = 0x55; bs[511] = 0xAA;
  bs.copy(img, partStart * SEC);
  for (let i = 0; i < nfats; i++) fat.copy(img, (partStart + reserved + i * fatSecs) * SEC);
  rootBuf.copy(img, (partStart + reserved + nfats * fatSecs) * SEC);
  return { img, files, info: { total, partStart, fatSecs, dataStart, spc, clusters, used: next - 2 } };
}

// ---- list the files of a FAT16 image made (or changed by the firmware) above: [{path, size, cluster}] (short names only)
export function listFat(img) {
  const SEC = 512, p = img.readUInt32LE(446 + 8), bs = img.subarray(p * SEC, p * SEC + SEC);
  const spc = bs[13], reserved = bs.readUInt16LE(14), nf = bs[16], re = bs.readUInt16LE(17), fs16 = bs.readUInt16LE(22);
  const fatOff = (p + reserved) * SEC, rootOff = (p + reserved + nf * fs16) * SEC, dataOff = rootOff + re * 32, out = [];
  const chain = (c) => { const parts = []; for (let n = 0; c >= 2 && c < 0xFFF0 && n < 70000; n++) { parts.push(img.subarray(dataOff + (c - 2) * spc * SEC, dataOff + (c - 1) * spc * SEC)); c = img.readUInt16LE(fatOff + 2 * c); } return Buffer.concat(parts); };
  const walk = (buf, rel) => { for (let o = 0; o + 32 <= buf.length; o += 32) { const e = buf.subarray(o, o + 32); if (e[0] === 0) break; if (e[0] === 0xE5 || (e[11] & 0x0F) === 0x0F || (e[11] & 0x08) || e[0] === 0x2E) continue; const n = e.toString('latin1', 0, 8).trim(), x = e.toString('latin1', 8, 11).trim(), name = x ? `${n}.${x}` : n, cl = e.readUInt16LE(26), size = e.readUInt32LE(28); if (e[11] & 0x10) walk(chain(cl), `${rel}/${name}`); else out.push({ path: `${rel}/${name}`, size, cluster: cl, data: () => chain(cl).subarray(0, size) }); } };
  walk(img.subarray(rootOff, rootOff + re * 32), '');
  return out;
}

// ---- the card
export function attachCard(e, img, { log = false } = {}) {
  const SEC = 512, sectors = img.length / SEC, RCA = 0x1234;
  const card = e.card = { img, log: [], state: 'idle', blocklen: 512, reads: 0, writes: 0, unknown: new Map(), dirty: false };
  // CSD version 1: READ_BL_LEN 9, C_SIZE_MULT 7 (x 512), C_SIZE + 1 = sectors / 512
  const csd = Buffer.alloc(16), setBits = (buf, hi, lo, v) => { for (let b = lo; b <= hi; b++, v = Math.floor(v / 2)) if (v & 1) buf[15 - (b >> 3)] |= 1 << (b & 7); };
  setBits(csd, 119, 112, 0x0E); setBits(csd, 111, 104, 0x00); setBits(csd, 103, 96, 0x32); setBits(csd, 95, 84, 0x5B5); setBits(csd, 83, 80, 9);
  setBits(csd, 79, 79, 1); setBits(csd, 73, 62, sectors / 512 - 1); setBits(csd, 49, 47, 7); setBits(csd, 46, 46, 1); setBits(csd, 45, 39, 0x7F); setBits(csd, 25, 22, 9); setBits(csd, 0, 0, 1);
  const cid = Buffer.from([0x03, 0x53, 0x44, 0x45, 0x31, 0x30, 0x31, 0x20, 0x10, 0x10, 0x10, 0xE1, 0x01, 0x01, 0x1B, 0x01]);
  const scr = Buffer.from([0x02, 0x25, 0x00, 0x00, 0, 0, 0, 0]);                 // SD spec 2.00, 1- and 4-bit bus
  const r2 = (c, reg) => { for (let k = 0; k < 15; k++) e.w8(c + 44 + k, reg[14 - k]); e.w8(c + 59, 0); };   // register bits 8..127, low byte first
  const cpu = (a) => (((a >>> 0) & 0x3FFFFFFF) | 0x40000000) >>> 0;
  const status = () => ((card.state === 'tran' ? 4 : card.state === 'stby' ? 3 : card.state === 'ident' ? 2 : card.state === 'ready' ? 1 : 0) << 9) | 0x100 | (card.app ? 0x20 : 0);
  const dataOut = (c, bytes) => { const buf = e.r32(c + 60), n = e.r32(c + 64) * e.r32(c + 68); if (buf) e.wr(cpu(buf), bytes.subarray(0, Math.min(n, bytes.length))); };
  e.pins.set(0xBE, 0);
  e.sdCmd = (c) => {
    const type = e.r16(c + 14);
    if (type !== 3) return 0;                                      // host set-up (clock, power, bus width): done
    const w = e.r32(c + 36), idx = w & 63, app = (w & 0xC0) === 0x40, arg = e.r32(c + 40) >>> 0;
    const buf = e.r32(c + 60), count = e.r32(c + 64), size = e.r32(c + 68), write = e.r8(c + 73) !== 0;
    const R = (v) => { e.w32(c + 44, v >>> 0); return 0; };
    if (log || card.log.length < 300) card.log.push(`${(e.m.devices.clock.t / 1e6).toFixed(1)} ${app ? 'A' : ''}CMD${idx} arg ${arg.toString(16)}${buf ? ` data ${count} x ${size} ${write ? 'write' : 'read'}` : ''}`);
    if (app) switch (idx) {
      case 41: card.state = 'ready'; return R(0x80FF8000);         // OCR: power up done, standard capacity
      case 6: return R(status());
      case 51: dataOut(c, scr); return R(status());
      case 13: dataOut(c, Buffer.alloc(64)); return R(status());
      case 23: case 42: return R(status());
      default: card.unknown.set('A' + idx, (card.unknown.get('A' + idx) || 0) + 1); return 0x1405;
    }
    switch (idx) {
      case 0: card.state = 'idle'; return 0;
      case 8: return R(arg);
      case 55: return R(status() | 0x20);
      case 2: card.state = 'ident'; r2(c, cid); return 0;
      case 3: card.state = 'stby'; return R((RCA << 16) | 0x0500);
      case 9: r2(c, csd); return 0;
      case 10: r2(c, cid); return 0;
      case 7: card.state = (arg >>> 16) === RCA ? 'tran' : 'stby'; return R(status());
      case 13: return R(status());
      case 16: card.blocklen = arg; return R(status());
      case 12: return R(status());
      case 6: { const st = Buffer.alloc(64); st[0] = 0x00; st[1] = 0x64; st[13] = 0x03; st[16] = (arg >>> 31) ? (arg & 15) : 0; dataOut(c, st); return R(status()); }   // switch function: default speed only
      case 17: case 18: { const n = count * size, off = arg; if (off + n > img.length) return 0x1404; if (buf) e.wr(cpu(buf), img.subarray(off, off + n)); card.reads += count; return R(status()); }
      case 24: case 25: { const n = count * size, off = arg; if (off + n > img.length) return 0x1404; if (buf) Buffer.from(e.rd(cpu(buf), n)).copy(img, off); card.writes += count; card.dirty = true; return R(status()); }
      case 32: case 33: case 38: return R(status());
      default: card.unknown.set('C' + idx, (card.unknown.get('C' + idx) || 0) + 1); return 0x1405;
    }
  };
  return card;
}

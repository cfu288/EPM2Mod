// Frame composer and PNG writer for the E-PM2 display controller 0x9A900000 (our code).
// Layers (VERIFIED from the register values the firmware writes and the OSD engine's destinations):
//   +0x44: a 4-bit plane with the 8-entry palette +0x300 (frames: black, white, orange, green, blue);
//   +0x48: a 4-bit plane with the 16-entry palette +0x340 (black at several alphas: the shade behind menus);
//   +0x4C: the 8-bit OSD plane; its palette has two banks of 128 entries, +0x400 and +0x600, loaded in turn (the bank
//   written last is used, see devices.mjs); it and is indexed by the pixel's low 7 bits
//   (the firmware clears the plane with 0xFF = entry 127, transparent; the meaning of bit 7 is UNKNOWN).
//   4-bit planes have a stride of 448 bytes, the 8-bit plane 896; 720 x 480 visible.
//   A palette entry is A << 24 | Cr << 16 | Cb << 8 | Y with A 0..15 (INFERRED from the values: 0x0F6BFF1D is BT.601
//   blue, 0x0F8080FE white, 0x008080FF transparent). Which palette belongs to which plane is INFERRED from the values
//   the firmware fills the planes with.
// The video plane under the OSD is not modelled: it is drawn as a flat colour (default dark grey).
// Plane order bottom to top: frames (+0x44), shade (+0x48), OSD (+0x4C): INFERRED (E101_ORDER overrides).
import zlib from 'node:zlib';
import fs from 'node:fs';
const W = 720, H = 480;
const crcT = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const crc = (b) => { let c = 0xFFFFFFFF; for (const x of b) c = crcT[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
export function png(rgb, w, h) {
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w * 3 + 1)] = 0; Buffer.from(rgb.buffer, rgb.byteOffset + y * w * 3, w * 3).copy(raw, y * (w * 3 + 1) + 1); }
  const chunk = (type, data) => { const b = Buffer.alloc(12 + data.length); b.writeUInt32BE(data.length, 0); b.write(type, 4, 'ascii'); data.copy(b, 8); b.writeUInt32BE(crc(b.subarray(4, 8 + data.length)), 8 + data.length); return b; };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]);
}
const clamp = (v) => (v < 0 ? 0 : v > 255 ? 255 : v | 0);
function pal(e, base, n) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const v = e.store.get(0x9A900000 + base + 4 * i) ?? 0, a = (v >>> 24) & 15, cr = ((v >>> 16) & 255) - 128, cb = ((v >>> 8) & 255) - 128, y = v & 255;
    out.push([clamp(y + 1.402 * cr), clamp(y - 0.344 * cb - 0.714 * cr), clamp(y + 1.772 * cb), a / 15]);
  }
  return out;
}
// While a ROM picture is shown (e.videoRom: the top menu's and the menus' background pictures, which live in a flash area
// that is not in the update file) the video plane is a flat light grey; otherwise (live view) dark grey. Both FAKE.
export function compose(e, { video = e.videoRom != null ? [176, 176, 176] : [40, 40, 40] } = {}) {
  const reg = (o) => e.store.get(0x9A900000 + o) ?? 0, cpu = (a) => (((a >>> 0) & 0x3FFFFFFF) | 0x40000000) >>> 0;
  const rgb = new Uint8Array(W * H * 3);
  for (let i = 0; i < W * H; i++) { rgb[3 * i] = video[0]; rgb[3 * i + 1] = video[1]; rgb[3 * i + 2] = video[2]; }
  const planes = { p8: { addr: reg(0x4C), depth: 8, pal: pal(e, (e.vsc && e.vsc.palBank) || 0x600, 128) }, p4b: { addr: reg(0x48), depth: 4, pal: pal(e, 0x340, 16) }, p4a: { addr: reg(0x44), depth: 4, pal: pal(e, 0x300, 16) } };
  const order = (process.env.E101_ORDER || 'p4a,p4b,p8').split(',');
  const stats = {};
  for (const name of order) {
    const p = planes[name]; if (!p || !p.addr) continue;
    const stride = p.depth === 8 ? 896 : 448, buf = e.rd(cpu(p.addr), stride * H);
    let drawn = 0;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const idx = p.depth === 8 ? buf[y * stride + x] & 127 : (x & 1 ? buf[y * stride + (x >> 1)] >> 4 : buf[y * stride + (x >> 1)] & 15);
      const c = p.pal[idx], a = c[3]; if (a === 0) continue;
      drawn++;
      const o = 3 * (y * W + x);
      rgb[o] = rgb[o] * (1 - a) + c[0] * a; rgb[o + 1] = rgb[o + 1] * (1 - a) + c[1] * a; rgb[o + 2] = rgb[o + 2] * (1 - a) + c[2] * a;
    }
    stats[name] = drawn;
  }
  return { rgb, w: W, h: H, stats };
}
export function screenshot(e, file, opts) { const f = compose(e, opts); fs.writeFileSync(file, png(f.rgb, f.w, f.h)); return f.stats; }

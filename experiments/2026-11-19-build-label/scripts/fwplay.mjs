// fwplay.mjs OUTDIR STEP...: the steps of tools/emu/boot/play.mjs (w:MS, key:NAME[:MS], shot:NAME) plus
//   wstr:HEX[:N]   print the UTF-16 text at a run-time address (at most N characters, default 64)
//   hex:HEX[:N]    print N bytes (default 32) at a run-time address
// HDR=1 writes block 0's container header (32 bytes) at 0x7E421000 before the first instruction, as the camera's
// first-stage loader leaves it (inferred: the payload runs at 0x7E421020 = header + 32). The emulator does not model
// that loader, so without HDR=1 the Firmware screen shows "Body : 0.0" (the boot copies 0x7E421010 into prm 0xC082).
// Run: tools/emu/emu-run IMAGE /abs/path/fwplay.mjs OUTDIR STEP...   (E101_STATE, E101_RTC as in play.mjs)
import fs from 'node:fs';
import path from 'node:path';
const E = path.join(process.env.EPM2_REPO, 'tools/emu/e101');
const { createBoot } = await import(path.join(E, 'boot.mjs'));
const { screenshot } = await import(path.join(E, 'screen.mjs'));
const { KEYS, press, release } = await import(path.join(E, 'keys.mjs'));
const { R, PC, SP, PSW } = await import(path.join(E, 'machine.mjs'));
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
if (process.env.HDR) {
  // the header of block 0 as the container holds it: 'OE', model 10 10, load address, length, build 0x1600, kind 0x100
  const bin = fs.readdirSync(process.env.BLOCKS).find((f) => /block0|\.0\.|^0/.test(f));
  const h = new Uint8Array(32);
  const src = process.env.HDR_HEX ?? '4f4510100000000000002c40c0ffd70000160000000100000000000000000000';
  for (let i = 0; i < 32; i++) h[i] = parseInt(src.slice(2 * i, 2 * i + 2), 16);
  e.wr(0x7E421000, h);
  console.log('header written at 0x7E421000', bin ?? '');
}
// DUMPAT=HEXPC:N[,HEXPC:N]: each time the pc is reached, print a0, a1 and N bytes at a0 (to find a widget's fields)
const { A0, A1 } = await import(path.join(E, 'machine.mjs'));
for (const w of (process.env.DUMPAT ?? '').split(',').filter(Boolean)) {
  const [pc, n] = w.split(':'); let hits = 0;
  e.hook(parseInt(pc, 16), 'dump' + pc, () => {
    if (hits++ > 8) return;
    const a = R[A0] >>> 0, bb = (x) => (e.r32(x & ~3) >>> (8 * (x & 3))) & 0xFF;
    console.log(`at ${pc}: a0 ${a.toString(16)} a1 ${(R[A1] >>> 0).toString(16)} :: ${Array.from({ length: Number(n) }, (_, i) => bb(a + i).toString(16).padStart(2, '0')).join('')}`);
  });
}
// FAKEVER=KIND:HEX[,KIND:HEX]: the Firmware page's version reads (page slot 0x7EDFD8E6) of kind 6 (Lens), 10 (Flash)
// or 8 (Acc) succeed with that u16, e.g. 6:1100 = "1.1". The hook is on the instruction after each read: d0 = 0 (read
// ok) and the u16 written into the page's record (d3 + 4, + 6, + 8), as a real read would
const { D0, D3 } = await import(path.join(E, 'machine.mjs'));
const AFTER = { 6: [0x7EDFD930, 4], 10: [0x7EDFD94D, 6], 8: [0x7EDFD96A, 8] };
for (const w of (process.env.FAKEVER ?? '').split(',').filter(Boolean)) {
  const [k, v] = w.split(':'); const [pc, off] = AFTER[k]; const val = parseInt(v, 16);
  e.hook(pc, 'fakever' + k, () => { R[D0] = 0; e.wr((R[D3] >>> 0) + off, new Uint8Array([val & 0xFF, val >> 8])); });
}
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
const b = (a) => (e.r32(a & ~3) >>> (8 * (a & 3))) & 0xFF;
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(3)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') { screenshot(e, path.join(out, f[1] + '.png')); console.log('shot', f[1]); }
  else if (f[0] === 'wstr') {
    const a = parseInt(f[1], 16); let s = '';
    for (let i = 0; i < Number(f[2] || 64); i++) { const c = b(a + 2 * i) | (b(a + 2 * i + 1) << 8); if (!c) break; s += String.fromCharCode(c); }
    console.log(`wstr ${f[1]}: ${JSON.stringify(s)}`);
  } else if (f[0] === 'hex') {
    const a = parseInt(f[1], 16); const n = Number(f[2] || 32);
    console.log(`hex ${f[1]}: ${Array.from({ length: n }, (_, i) => b(a + i).toString(16).padStart(2, '0')).join('')}`);
  } else if (f[0] === 'wset') {
    // wset:HEX:TEXT writes TEXT as UTF-16 with its end mark at a run-time address (to try other labels without a build)
    const a = parseInt(f[1], 16), t = f.slice(2).join(':');
    const bytes = new Uint8Array(2 * t.length + 2);
    for (let i = 0; i < t.length; i++) { bytes[2 * i] = t.charCodeAt(i) & 0xFF; bytes[2 * i + 1] = t.charCodeAt(i) >> 8; }
    e.wr(a, bytes);
    console.log(`wset ${f[1]}: ${JSON.stringify(t)}`);
  } else { console.log('unknown step', step); process.exit(2); }
}
console.log('done at lab ms', (e.m.devices.clock.t / 1e6).toFixed(0), '| firmware errors', e.errLog.length);

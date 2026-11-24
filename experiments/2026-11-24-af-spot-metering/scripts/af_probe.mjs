// af_probe.mjs OUTDIR STEP...: the steps of emulator/boot/play.mjs (w:MS, key:NAME[:MS], shot:NAME) plus
//   tag:HEX   print the stored value of a prm tag (index table 0x603A0E38, as tagplay.mjs of 2026-11-17)
// and a log of every prm store of the tags in TAGS (default 88b2,84d1,6761,9681): the inner setters 0x7E457E7D and
// 0x7E457E9E (d0 tag, d1 index, a1 value), with the caller chain.
// Run: E101_STATE=s.json emulator/emu-run IMAGE /abs/path/af_probe.mjs OUTDIR STEP...
import fs from 'node:fs';
import path from 'node:path';
const E = path.join(process.env.EPM2_REPO, 'emulator/e101');
const { createBoot, backtrace } = await import(path.join(E, 'boot.mjs'));
const { screenshot } = await import(path.join(E, 'screen.mjs'));
const { KEYS, press, release } = await import(path.join(E, 'keys.mjs'));
const { R, PC, SP, PSW, D0, D1, A1, MDR } = await import(path.join(E, 'machine.mjs'));
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const TAGS = new Set((process.env.TAGS || '88b2,84d1,6761,9681').split(',').map((x) => parseInt(x, 16)));
let step = 'boot';
for (const pc of [0x7E457E7D, 0x7E457E9E]) {
  e.hook(pc, 'set' + pc.toString(16), (lab) => {
    const t = R[D0] & 0xFFFF;
    if (!TAGS.has(t)) return;
    const bt = backtrace(lab, R[SP] >>> 0, 6).map((s) => s.replace(/^\[sp\+\w+\] /, '')).join(' < ');
    console.log(`[${step}] set 0x${t.toString(16)}[${R[D1] & 0xFFFF}] = ${R[A1] | 0} via ${(R[MDR] >>> 0).toString(16)} | ${bt}`);
  });
}
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
function tag(hex) {
  const t = parseInt(hex, 16), ent = 0x603A0E38 + 8 * (t >> 4), ptr = e.r32(ent + 4) >>> 0;
  const b = (a) => (e.r32(a & ~3) >>> (8 * (a & 3))) & 0xFF;
  const wide = (t & 0xF) === 0xA || (t & 0xF) === 0x2;
  let v = wide ? b(ptr) | (b(ptr + 1) << 8) : b(ptr);
  if ((t & 0xF) === 0xA && v & 0x8000) v -= 0x10000;
  console.log(`[${step}] tag 0x${t.toString(16)} = ${v} (data at 0x${ptr.toString(16)})`);
}
run(Number(process.env.BOOTMS || 1500));
for (const s of process.argv.slice(3)) {
  step = s;
  const f = s.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') screenshot(e, path.join(out, f[1] + '.png'));
  else if (f[0] === 'tag') tag(f[1]);
  else { console.log('unknown step', s); process.exit(2); }
}
if (process.env.SAVE && e.saveState()) console.log('state saved to', e.stateFile);
console.log('done at lab ms', (e.m.devices.clock.t / 1e6).toFixed(0), '| firmware errors', e.errLog.length);

// sensor_mode_probe.mjs OUTDIR STEP...: the steps of af_probe.mjs, and a log of each write of exp's sensor-mode
// globals 0x605A7254 (mode) / 0x605A7258 (index): the writers 0x7E699635 (d0 mode, d1 index) and 0x7E697B56.
// Run: E101_STATE=s.json emulator/emu-run IMAGE /abs/path/sensor_mode_probe.mjs OUTDIR STEP...
import fs from 'node:fs';
import path from 'node:path';
const E = path.join(process.env.EPM2_REPO, 'emulator/e101');
const { createBoot } = await import(path.join(E, 'boot.mjs'));
const { screenshot } = await import(path.join(E, 'screen.mjs'));
const { KEYS, press, release } = await import(path.join(E, 'keys.mjs'));
const { R, PC, SP, PSW, D0, D1 } = await import(path.join(E, 'machine.mjs'));
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
let step = 'boot';
e.hook(0x7E699635, 'modeinit', () => console.log(`[${step}] 0x7E699635 mode ${R[D0] | 0} index ${R[D1] | 0}`));
e.hook(0x7E697B56, 'modeset', () => console.log(`[${step}] 0x7E697B56 mode ${e.r32((R[SP] + 152) >>> 0) | 0} index ${e.r32((R[SP] + 168) >>> 0) | 0}`));
e.hook(0x7E6908CE, 'zones', () => console.log(`[${step}] zone builder runs, mode ${e.r32(0x605A7254) | 0}`));
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
run(Number(process.env.BOOTMS || 1500));
for (const s of process.argv.slice(3)) {
  step = s;
  const f = s.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') screenshot(e, path.join(out, f[1] + '.png'));
  else { console.log('unknown step', s); process.exit(2); }
}
console.log(`end: 0x605A7254 = ${e.r32(0x605A7254) | 0}, 0x605A7258 = ${e.r32(0x605A7258) | 0}`);

// drive.mjs STEP...: keys and waits (w:MS, key:NAME), with SETUP observers; for the panel dumps of the level-gauge work.
const REPO = process.env.EPM2_REPO;
const { createBoot } = await import(REPO + '/emulator/e101/boot.mjs');
const { press, release } = await import(REPO + '/emulator/e101/keys.mjs');
const { R, PC, SP, PSW } = await import(REPO + '/emulator/e101/machine.mjs');
const { screenshot } = await import(REPO + '/emulator/e101/screen.mjs');
const OUT = process.env.OUT || '.';
const e = createBoot({ blocksDir: process.env.BLOCKS });
if (process.env.SETUP) (await import(process.env.SETUP)).default(e);
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 900000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'shot') { screenshot(e, OUT + '/' + f[1] + '.png'); console.log('shot', f[1], (e.m.devices.clock.t / 1e6).toFixed(0)); }
  else if (f[0] === 'key') { press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
}

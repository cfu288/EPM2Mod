// pmread.mjs STEP...: prints the value of each firmware read of the stored Picture Mode (prm tag 0x9481) after the
// boot, so a session can show which value the camera holds. Steps: w:MS, key:NAME.
import { createBoot } from '../../../emulator/e101/boot.mjs';
import { KEYS, press, release } from '../../../emulator/e101/keys.mjs';
import { R, PC, SP, PSW } from '../../../emulator/e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const ms = () => Number((e.m.devices.clock.t / 1e6).toFixed(1));
const seen = new Set();
let pending = false, shown = 0;
e.hook(0x7E457C75, 'prm_get', () => {
  if ((R[0] & 0xFFFF) !== 0x9481) return;
  const ret = R[11] >>> 0;
  pending = true;
  if (!seen.has(ret)) {
    seen.add(ret);
    e.hook(ret, 'prm_ret', () => {
      if (!pending) return;
      pending = false;
      if (shown < 3) { shown++; console.log(JSON.stringify({ ms: ms(), picture_mode: R[0] >>> 0 })); }
    });
  }
});
const run = (t) => { const r = e.run({ maxLabMs: t, maxMs: 900000 }); if (r.why !== 'labtime') { console.log('stop', JSON.stringify(r)); process.exit(2); } };
run(Number(process.env.BOOTMS || 2500));
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
}
if (process.env.SAVE && e.saveState()) console.log('state saved');

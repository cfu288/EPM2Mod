// prmtest.mjs STEP...: SWAP=1: the setSetting(449, v) of the card-looks row writes setting 447 instead.
// Every session: the first prm_get(0xD7B1) after BOOTMS reads tag 0xD791 (setting 447) instead, prints it, returns 1.
import { createBoot } from '../../../emulator/e101/boot.mjs';
import { KEYS, press, release } from '../../../emulator/e101/keys.mjs';
import { R, PC, SP, PSW } from '../../../emulator/e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const ms = () => Number((e.m.devices.clock.t / 1e6).toFixed(1));
let reads = 0, armed = false, retAt = 0;
e.hook(0x7E457C75, 'prm_get', () => {
  if ((R[0] & 0xFFFF) !== 0xD7B1 || !armed || reads) return;
  reads = 1; R[0] = 0xD791; retAt = R[11] >>> 0;
  e.hook(retAt, 'prm_ret', () => { if (reads === 1) { reads = 2; console.log(JSON.stringify({ ms: ms(), setting447: R[0] })); R[0] = 1; } });
});
e.hook(0x7EE01D4E, 'setSetting', () => {
  if (R[0] >= 446 && R[0] <= 449) console.log(JSON.stringify({ ms: ms(), setSetting: R[0], value: R[1] }));
  if (process.env.SWAP && R[0] === 449) { R[0] = 447; R[1] = 1; console.log('swapped to setSetting(447, 1)'); }
});
const run = (t) => { const r = e.run({ maxLabMs: t, maxMs: 900000 }); if (r.why !== 'labtime') { console.log('stop', JSON.stringify(r)); process.exit(2); } };
run(Number(process.env.BOOTMS || 2500));
armed = true;
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('bad step', JSON.stringify(step)); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
}
run(500);
if (process.env.SAVE && e.saveState()) console.log('state saved');
console.log('end', ms(), 'errors', JSON.stringify(e.errLog));

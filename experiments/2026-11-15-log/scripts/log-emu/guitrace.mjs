// guitrace.mjs OUTDIR STEP...: play.mjs steps; prints every GUI log line (0x7ECE6333 with value, 0x7ECE631E without) with its caller.
import fs from 'node:fs';
import { createBoot } from '../e101/boot.mjs';
import { KEYS, press, release } from '../e101/keys.mjs';
import { R, PC, SP, PSW, MDR, A1, D0, h8 } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const glog = [];
const skip = /getSetting|TouchPanel|EXCLUSIVE|waitEvent|isBackLight|NormalProc|updateResearch|getKeyState|getMedia|getExistMedia/;
e.hook(0x7ECE6333, 'guilogv', () => { const s = e.cstr(R[A1] >>> 0, 70); if (!skip.test(s)) glog.push(`${(e.m.devices.clock.t / 1e6).toFixed(0)} V ${s} ${h8(R[D0])} from ${h8(R[MDR])}`); });
e.hook(0x7ECE631E, 'guilog', () => { const s = e.cstr(R[A1] >>> 0, 70); if (!skip.test(s)) glog.push(`${(e.m.devices.clock.t / 1e6).toFixed(0)} - ${s} from ${h8(R[MDR])}`); });
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
run(Number(process.env.BOOTMS || 1500));
glog.length = 0;
for (const step of process.argv.slice(3)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  console.log(`## ${step}`); console.log(glog.splice(0).slice(0, Number(process.env.GLN || 40)).join('\n'));
}
console.log('errors', e.errLog.join(' ; '));

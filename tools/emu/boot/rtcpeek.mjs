// rtcpeek.mjs: print the date record the RTC driver 0x7E467D17 produces (after the seconds -> date conversion, at 0x7E467D33)
import { createBoot } from '../e101/boot.mjs';
import { R, PC, SP, PSW, h8 } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
let n = 0;
for (const pc of [0x7E467D33, 0x7E467D47, 0x7E467D57]) e.hook(pc, 'rp' + pc, () => { if (n++ < 12) { const b = e.rd(R[6] >>> 0, 12); console.log(pc.toString(16), 't', (e.m.devices.clock.t / 1e6).toFixed(1), 'year', b[0] | b[1] << 8, 'm/d', b[2], b[3], 'h:m:s', b[4], b[5], b[6], 'b7', b[7], 'status', b[8] | b[9] << 8); } });
import { press, release } from '../e101/keys.mjs';
const run = (ms) => e.run({ maxLabMs: ms, maxMs: 600000 });
run(1500);
for (const step of process.argv.slice(2)) { const f = step.split(':'); if (f[0] === 'w') run(Number(f[1])); else { press(e, f[1]); run(120); release(e, f[1]); run(400); } }

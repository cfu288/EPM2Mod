// canexec.mjs STEP...: during the LAST step print every row-enable check the menu makes:
// app_check_mode (0x7E9E8CCD) mode = setting id, check = index into the check table 0x7EC1C368, status (0 = allowed).
import { createBoot } from '../e101/boot.mjs';
import { KEYS, press, release } from '../e101/keys.mjs';
import { R, PC, SP, PSW, A0, A1, D0, D1, MDR, h8 } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
if (process.env.SETUP) (await import(process.env.SETUP)).default(e);
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
let on = false; const out = [];
const u32 = (a) => { const b = e.rd(a, 4); return (b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24) >>> 0; };
e.hook(0x7E9E8D33, 'ce', () => { if (on) out.push(`mode ${u32((R[SP] >>> 0) + 24) & 0xFFFF} check ${R[2] & 0xFFFF} (fn ${u32(0x7EC1C368 + 4 * (R[2] & 0xFFFF)).toString(16)}) status ${R[D0] & 0xFFFF}`); });
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
run(Number(process.env.BOOTMS || 1500));
const steps = process.argv.slice(2);
steps.forEach((step, i) => {
  const f = step.split(':'); on = i === steps.length - 1 || !!process.env.ALLSTEPS;
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'port') e.setPorts(parseInt(f[1], 16));
});
console.log(out.join('\n'));

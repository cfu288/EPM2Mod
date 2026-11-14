// ramcheck.mjs STEP...: play.mjs steps (w:MS, key:NAME) plus chk:LABEL, which prints the Custom Menu row-state array
// (RAM 0x606A3118, u16 per row: 0 = normal, 1 = grey, 2 = hidden) and whether the bytes after it, up to the next
// addressed object 0x606A32F0, are all zero. Run from the emulator work folder.
import { createBoot } from '../e101/boot.mjs';
import { KEYS, press, release } from '../e101/keys.mjs';
import { R, PC, SP, PSW } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
const ROWS = Number(process.env.ROWS || 78);
const words = (a, n) => { const o = []; for (let i = 0; i < n; i += 4) o.push(e.r32(a + i) >>> 0); return o; };
function chk(label) {
  const st = []; for (const w of words(0x606A3118, 160)) st.push(w & 0xFFFF, w >>> 16);
  const end = 0x606A3118 + 2 * ROWS, tail = words(end & ~3, 0x606A32F0 - (end & ~3));
  if (end & 2) tail[0] >>>= 16;
  const nz = tail.map((w, i) => [i, w]).filter(([, w]) => w);
  console.log(`${label}: rows 70..79 state ${st.slice(70, 80).join(' ')} | 0x${end.toString(16)}..0x606A32F0 ${nz.length ? 'NOT ZERO: ' + nz.map(([i, w]) => `+${i * 4}=${w.toString(16)}`).join(' ') : 'all zero'}`);
}
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'chk') chk(f[1]);
}
console.log('firmware errors', e.errLog.length);

// camregs.mjs MS [OUT.json]: boot an image in the full-boot emulator with live view's start sent to the real TAKE task
// (E101_TAKEFAKE=none), run MS of lab time, and report what the camera core wrote for the sensor-mode request: each
// call of the TAKE request builder 0x7E5A897F (mode code, and the request after it returns: window x0, y0, width,
// height, the resize block +44..+55), each call of the camera-core size writer 0x7E6540F8 (its struct), and the final
// contents of the camera-core register block 0x99900000-0x99900600 (plain storage in the emulator: the last value
// written stays). Run with emulator/emu-run IMAGE experiments/2026-11-19-movie-sampling/scripts/camregs.mjs MS.
// Env: E101_STATE (a movie-mode state from emulator/mkstate), E101_TAKEFAKE=none.
import fs from 'node:fs';
import { createBoot } from '../../../emulator/e101/boot.mjs';
import { R, PC, SP, PSW, D0, D1, A0, h8 } from '../../../emulator/e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = { requests: [], sizeWriter: [], regs: {} };
const hw = (a, n) => Array.from({ length: n }, (_, k) => e.r16(a + 2 * k));
let pending = null;
e.hook(0x7E5A897F, 'req', () => { pending = { code: R[D0] & 0xFFFF, a3: R[A0] >>> 0, sp: R[SP] >>> 0 }; });
e.hook(0x7E5A8ACF, 'req-ret', () => {             // `ret` of the builder: the request is complete
  if (!pending) return;
  const a = pending.a3;
  out.requests.push({ code: pending.code, at: h8(a), win: hw(a, 4), resize: [e.r8(a + 44), e.r8(a + 45), ...hw(a + 46, 5)], ptr40: h8(e.r32(a + 40)) });
  pending = null;
});
e.hook(0x7E6540F8, 'size', () => { const a = R[A0] >>> 0; out.sizeWriter.push({ at: h8(a), mode: e.r8(a), fields: hw(a + 2, 12) }); });
// No sensor: the AE code divides by a statistics count that stays 0 (0x7E69053A `divu d1,d0`); give it 1.
e.hook(0x7E69053A, 'ae-div0', () => { if ((R[D1] >>> 0) === 0) R[D1] = 1; });
// Optional key presses after the boot (KEYS=CUSTOM2:3000,...): NAME:LABMS-before-the-press.
import { press, release } from '../../../emulator/e101/keys.mjs';
let r = e.run({ maxLabMs: Number(process.argv[2] || 4000), maxMs: 900000 });
for (const k of (process.env.KEYS || '').split(',').filter(Boolean)) {
  if (r.why !== 'labtime') break;
  const [name, ms] = k.split(':'); press(e, name); r = e.run({ maxLabMs: 120, maxMs: 900000 }); release(e, name);
  if (r.why === 'labtime') r = e.run({ maxLabMs: Number(ms || 2000), maxMs: 900000 });
}
for (let a = 0x99900000; a < 0x99900600; a += 4) { const v = e.r32(a) >>> 0; if (v) out.regs[h8(a)] = h8(v); }
out.stop = JSON.stringify(r); out.pc = h8(R[PC]); out.errors = e.errLog.slice(0, 12);
const text = JSON.stringify(out, null, 1);
if (process.argv[3]) fs.writeFileSync(process.argv[3], text); else console.log(text);
console.log('requests', out.requests.length, 'size writer', out.sizeWriter.length, 'regs', Object.keys(out.regs).length, 'stop', r.why);

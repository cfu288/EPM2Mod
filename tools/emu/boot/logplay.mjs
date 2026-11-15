// logplay.mjs OUTDIR STEP...: play.mjs for the structured-log checks (epm2-tools experiments/2026-11-15-log).
// Steps: w:MS, key:NAME[:MS], shot:NAME, ring:LABEL (prints both ring headers), burst:N (calls log_put N times through
// a firmware call from interrupt context: the ring-overflow check), seed:FILE (before boot: load a saved ring RAM image,
// as a warm restart would leave it), save:FILE (save the ring RAM image).
// Env: BLOCKS, E101_STATE, E101_RTC, E101_CARD=<host folder>: after the run every file of the card's root that the
// firmware wrote is copied back to the host folder (so EPM2LOG.BIN appears there and the next run starts with it).
import fs from 'node:fs';
import path from 'node:path';
import { createBoot, listFat } from '../e101/boot.mjs';
import { screenshot } from '../e101/screen.mjs';
import { KEYS, press, release } from '../e101/keys.mjs';
import { R, PC, SP, PSW, MDR, D0, D1, A0, h8 } from '../e101/machine.mjs';
const RING0 = 0xBE4F9000, RING1 = 0xBE4FB020, PST = 0xBE4FD040, RAMLEN = 0x4200, LOGPUT = Number(process.env.LOGPUT || 0x7E4C9531);
const e = createBoot({ blocksDir: process.env.BLOCKS });
const steps = process.argv.slice(3);
for (const s of steps) if (s.startsWith('seed:')) { e.wr(RING0, new Uint8Array(fs.readFileSync(s.slice(5)))); console.log('seeded ring RAM from', s.slice(5)); }
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); console.log('errors', e.errLog.slice(-5).join(' ; ')); process.exit(2); } };
const ring = (label) => { for (const [n, a] of [['cpu0', RING0], ['cpu1', RING1]]) console.log(`ring ${label} ${n}: magic ${h8(e.r32(a))} w ${e.r32(a + 4)} f ${e.r32(a + 8)} drops ${e.r32(a + 12)} session ${e.r32(a + 16)}`); console.log(`ring ${label} state: busy ${e.r8(PST)} result ${e.r8(PST + 1)} trigger ${h8(e.r32(PST + 4))} gui ${h8(e.r32(PST + 8))}`); };
// burst: a tiny routine in lab low RAM that calls log_put N times; posted through the firmware's deferred-call ring (interrupt context)
const burst = (n) => {
  const a = 0x00013000, code = [];
  // movm [d2,d3],(sp); mov N,d2; 1: mov 0x7ffe,d0; mov d2,d1; mov d2,a0; calls log_put (abs through a0? use call rel32); add -1,d2; bne 1b; movm (sp),[d2,d3]; retf? -> written as machine code below
  const le32 = (v) => [v & 255, (v >> 8) & 255, (v >> 16) & 255, (v >>> 24) & 255];
  code.push(0xCF, 0xC0);                               // movm [d2,d3],(sp)
  code.push(0xF8, 0xFE, 0xFC);                         // add -4,sp
  code.push(0xFC, 0xCE, ...le32(n));                   // mov n,d2
  const loop = a + code.length;
  code.push(0x2C, 0xFE, 0x7F);                         // mov 0x7ffe,d0
  code.push(0x89);                                     // mov d2,d1
  code.push(0xF1, 0xE8);                               // mov d2,a0
  const at = a + code.length;
  code.push(0xDD, ...le32((LOGPUT - at) | 0), 0x00, 0x00); // call log_put,[],0
  code.push(0x2A, 0xFF);                               // add -1,d2
  const br = a + code.length;
  code.push(0xC9, (loop - br) & 255);                  // bne loop
  code.push(0xF8, 0xFE, 0x04);                         // add 4,sp
  code.push(0xCE, 0xC0);                               // movm (sp),[d2,d3]
  code.push(0xF0, 0xFC);                               // rets
  e.wr(a, new Uint8Array(code)); e.post(a, 0, 0);
};
for (const a of (process.env.PROBE || '').split(',').filter(Boolean)) e.hook(parseInt(a, 16), 'probe', () => console.log(`probe ${a} t=${(e.m.devices.clock.t / 1e6).toFixed(1)} d0=${h8(R[D0])} d1=${h8(R[D1])} a0=${h8(R[A0])} sp=${h8(R[SP])}`));
const ctrace = [];
if (process.env.CARDTRACE && e.sdCmd) { const real = e.sdCmd; e.sdCmd = (c, h) => { const w = e.r32(c + 36), st = real(c, h); if (e.r16(c + 14) === 3) ctrace.push(`${(e.m.devices.clock.t / 1e6).toFixed(2)} ${(w & 0xC0) === 0x40 ? 'A' : ''}CMD${w & 63} arg ${(e.r32(c + 40) >>> 0).toString(16)} n ${e.r32(c + 64)} -> ${st.toString(16)}`); return st; }; }
run(Number(process.env.BOOTMS || 1500));
for (const step of steps) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') { screenshot(e, path.join(out, f[1] + '.png')); console.log('shot', f[1]); }
  else if (f[0] === 'ring') ring(f[1]);
  else if (f[0] === 'cpu1') { const n = Number(f[1]); e.w32(RING1, 0x314C5045); for (const o of [8, 12, 16]) e.w32(RING1 + o, 0); for (let i = 0; i < n; i++) { const a = RING1 + 32 + 16 * i; e.w16(a, 0x7FFD); e.w16(a + 2, i); e.w32(a + 4, (0x3FFFFFFF - Math.round(e.m.devices.clock.t / 1e3)) >>> 0); e.w32(a + 8, i); e.w32(a + 12, 0xC1); } e.w32(RING1 + 4, n); }
  else if (f[0] === 'gap') { let n = 0; const b = e.rd(0x7E4C9800, 0x7E4FE000 - 0x7E4C9800); for (let i = 0; i < b.length; i++) if (b[i]) n++; let m = 0; const c = e.rd(0x7E4F9000, 0x5000); for (let i = 0; i < c.length; i++) if (c[i]) m++; console.log(`gap ${f[1]}: non-zero bytes in 0x7E4C9800-0x7E4FE000: ${n}; in 0x7E4F9000-0x7E4FE000: ${m}`); }
  else if (f[0] === 'burst') { burst(Number(f[1])); run(50); }
  else if (f[0] === 'save') { fs.writeFileSync(step.slice(5), Buffer.from(e.rd(RING0, RAMLEN))); console.log('saved ring RAM to', step.slice(5)); }
  else if (f[0] === 'seed') { /* done before boot */ }
  else { console.log('unknown step', step); process.exit(2); }
}
if (e.saveState()) console.log('state saved');
if (process.env.CARDTRACE) console.log(ctrace.filter((l) => Number(l.split(' ')[0]) > Number(process.env.CARDTRACE)).join('\n'));
if (process.env.FILELOG) console.log(e.fileLog.slice(-Number(process.env.FILELOG)).join('\n'));
if (e.card) {
  console.log(`card: ${e.card.reads} blocks read, ${e.card.writes} written`);
  for (const f of listFat(e.card.img)) {
    if (f.path.lastIndexOf('/') > 0) continue;                  // root files only
    const data = f.data(), host = path.join(process.env.E101_CARD, f.path.slice(1));
    if (!fs.existsSync(host) || !fs.readFileSync(host).equals(data)) { fs.writeFileSync(host, data); console.log(`card -> host: ${f.path.slice(1)} (${f.size} bytes)`); }
  }
}
console.log('done at lab ms', (e.m.devices.clock.t / 1e6).toFixed(0), '| firmware errors', e.errLog.length, e.errLog.slice(0, 4).join(' ; '));

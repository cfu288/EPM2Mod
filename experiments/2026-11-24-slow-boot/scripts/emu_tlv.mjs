// emu_tlv.mjs: check of slow-boot-probe: start_kind is written once in the boot, just before seg_loaded; then a
// function check of T_LV on the booted firmware (the emulator has no live view, so the
// struct refresh never runs by itself). After 1500 ms of boot it enters the peaking hook 0x7E6ECF91 with set registers
// and stops at T_A 0x7E4C920B, three times (Debug Log On):
//   1. segments loaded: one lv_first record with seg2 0xA0602BE8, seg3 0x7EEBF5E1
//   2. again: no record (once per start)
//   3. flag cleared, T_MF's word overwritten (as before the copy on a cold start): a record with the other word
// Each time every register (d0-d3, a0-a3, sp, mdr, lir, lar) and the flags must be as at the entry.
//   emulator/emu-run data/builds/slow-boot-probe.json /abs/path/emu_tlv.mjs
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const REPO = process.env.EPM2_REPO;
const { createBoot } = await import(pathToFileURL(path.join(REPO, 'emulator/e101/boot.mjs')).href);
const M = await import(pathToFileURL(path.join(REPO, 'emulator/e101/machine.mjs')).href);
const { R, PC, SP, PSW, h8 } = M;

const RING0 = 0xBE4F9000, LOGON = 0xBE4FD042, FLAG = 0xBE4FD0A8, HOOK = 0x7E6ECF91, T_A = 0x7E4C920B, SEG2 = 0xBECB0B84;
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
let r = e.run({ maxLabMs: 1500, maxMs: 600000 });
if (r.why !== 'labtime') { console.log('FAIL boot', JSON.stringify(r)); process.exit(1); }
// start_kind: written by T_PW during the boot, before seg_loaded (ids 2561, then 1801)
const ids = [];
for (let i = 0; i < Math.min(e.r32(RING0 + 4), 512); i++) ids.push(e.r16(RING0 + 32 + 16 * i));
const k = ids.indexOf(2561);
console.log(`boot records: ${ids.join(' ')}; start_kind ${k >= 0 ? 'at ' + k : 'missing'}, seg_loaded at ${ids.indexOf(1801)}`);
let ok = k >= 0 && ids.indexOf(1801) === k + 1;
e.w8(LOGON, 1);                       // Debug Log On (the camera test's setting); the emulator's state has it Off
e.hook(T_A, 'T_A', () => 'stop');
const N = R.length;
const call = (label) => {
  const save = Array.from(R);
  const w0 = e.r32(RING0 + 4);
  R[PC] = HOOK | 0;
  for (let i = 0; i < 4; i++) R[i] = (0x11110000 * (i + 1) + 0x1234) | 0;          // d0..d3 (index order of machine.mjs)
  const before = Array.from(R);
  const res = e.run({ maxInsns: 5000, maxMs: 60000 });
  const after = Array.from(R);
  const diff = [];
  for (let i = 0; i < N; i++) if (i !== PC && (before[i] | 0) !== (after[i] | 0)) diff.push(`${i}: ${h8(before[i])} -> ${h8(after[i])}`);
  const w1 = e.r32(RING0 + 4);
  let rec = null;
  if (w1 !== w0) { const a = RING0 + 32 + 16 * ((w1 - 1) & 511); rec = { id: e.r16(a), arg0: h8(e.r32(a + 8)), arg1: h8(e.r32(a + 12)) }; }
  console.log(`${label}: stop ${res.why} at ${h8(res.pc)}; records ${w1 - w0}${rec ? ` id ${rec.id} seg2 ${rec.arg0} seg3 ${rec.arg1}` : ''}; registers changed: ${diff.length ? diff.join(', ') : 'none'}`);
  for (let i = 0; i < N; i++) R[i] = save[i];
  return { res, rec, diff, n: w1 - w0 };
};
const c1 = call('1 segments loaded');
ok &&= c1.res.why === 'hook:T_A' && c1.n === 1 && c1.rec.id === 2560 && c1.rec.arg0 === h8(0xA0602BE8) && c1.rec.arg1 === h8(0x7EEBF5E1) && !c1.diff.length;
const c2 = call('2 again');
ok &&= c2.res.why === 'hook:T_A' && c2.n === 0 && !c2.diff.length;
const keep = e.r32(SEG2);
e.w8(FLAG, 0); e.w32(SEG2, 0xFFFFFFFF);
const c3 = call('3 flag cleared, T_MF word 0xFFFFFFFF');
ok &&= c3.res.why === 'hook:T_A' && c3.n === 1 && c3.rec.arg0 === h8(0xFFFFFFFF) && !c3.diff.length;
e.w32(SEG2, keep);
console.log(ok ? 'PASS' : 'FAIL');
process.exit(ok ? 0 : 1);

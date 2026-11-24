// coldwarm.mjs MODE MS: boot an image in the emulator for MS ms of lab time with a chosen DRAM content at reset,
// and print the timeline of the start (GUI states, the quick start's log, the mod's log records, errors).
//
//   emulator/emu-run IMAGE /abs/path/coldwarm.mjs zero 8000             DRAM zero at reset (the emulator's default)
//   emulator/emu-run IMAGE /abs/path/coldwarm.mjs ff 8000               every DRAM byte 0xFF at reset
//   emulator/emu-run IMAGE /abs/path/coldwarm.mjs rand:SEED 8000        every DRAM byte random at reset (a cold start)
//   emulator/emu-run IMAGE /abs/path/coldwarm.mjs warm:FILE 8000        DRAM as FILE holds it (a restart that kept RAM)
//   add save:FILE as a third argument to save DRAM at the end of the run (gzip, 512 MiB raw)
//
// DRAM is 0x60000000-0x80000000 (512 MiB; 0xA0000000.. is its uncached alias). The pattern is written after the
// lab's set-up and before the first instruction, except 0x7E421020-0x7E430000, which the first-stage loader fills
// before the reset code runs. The reset code's own clears and copies then run as on the camera.
// Env: BLOCKS (emu-run sets it), LOGPUT: the address after log_put's Off gate (default 0x7E4C953F, the pinned build).
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const REPO = process.env.EPM2_REPO;
const { createBoot } = await import(pathToFileURL(path.join(REPO, 'emulator/e101/boot.mjs')).href);
const { R, PC, SP, PSW, D0, D1, A0, h8 } = await import(pathToFileURL(path.join(REPO, 'emulator/e101/machine.mjs')).href);

const [mode, msArg, saveArg] = process.argv.slice(2);
const MS = Number(msArg || 8000);
const DRAM = 0x60000000, DRAM_END = 0x80000000, PRE_LO = 0x7E421020, PRE_HI = 0x7E430000, CHUNK = 1 << 24;
const e = createBoot({ blocksDir: process.env.BLOCKS });

// the DRAM content at reset
const fillRange = (lo, hi, gen) => {
  for (let a = lo; a < hi; a += CHUNK) {
    const n = Math.min(CHUNK, hi - a), buf = gen(a, n);
    e.wr(a, buf);
  }
};
const fillDram = (gen) => { fillRange(DRAM, PRE_LO, gen); fillRange(PRE_HI, DRAM_END, gen); };
if (mode === 'ff') fillDram((a, n) => new Uint8Array(n).fill(0xff));
else if (mode.startsWith('rand')) {
  let x = (Number(mode.split(':')[1] || 1) * 2654435761) >>> 0 || 1;
  fillDram((a, n) => {
    const w = new Uint32Array(n >>> 2);
    for (let i = 0; i < w.length; i++) { x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0; w[i] = x; }
    return new Uint8Array(w.buffer);
  });
} else if (mode.startsWith('warm:')) {
  const img = zlib.gunzipSync(fs.readFileSync(mode.slice(5)));
  if (img.length !== DRAM_END - DRAM) throw new Error('warm image: wrong size ' + img.length);
  fillDram((a, n) => img.subarray(a - DRAM, a - DRAM + n));
} else if (mode !== 'zero') throw new Error('MODE: zero, ff, rand[:SEED] or warm:FILE');

// what the start does, in lab time
const lab = () => e.m.devices.clock.t / 1e6;
const cpu = () => (e.onCpu1 ? 1 : 0);
const lines = [];
const gui = [];
e.hook(0x7ECDF6E4, 'gui-state', () => { const s = R[D0] >>> 0; gui.push([lab(), s]); lines.push(`${lab().toFixed(1).padStart(8)} cpu${cpu()} GUI state ${h8(s)}`); });
const LOGPUT = Number(process.env.LOGPUT || 0x7E4C953F);
const NAMES = { 1: 'boot', 3: 'fw_error', 4: 'fw_error_args', 5: 'gui_state', 6: 'log_setting', 259: 'pk_heap_mode', 769: 'lv_values', 1800: 'card_task', 1801: 'seg_loaded', 1802: 'film_applied' };
let records = 0;
if (process.env.LOGPUT !== 'none') e.hook(LOGPUT, 'log-record', () => {
  const id = R[D0] & 0xffff;
  if (records++ < 200 && id !== 5) lines.push(`${lab().toFixed(1).padStart(8)} cpu${cpu()} log ${NAMES[id] || id} ${h8(R[D1])} ${h8(R[A0])}`);
});

R[PC] = PRE_LO | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const t0 = Date.now();
const r = e.run({ maxLabMs: MS, maxMs: 1800000 });
const first = (pred) => { const g = gui.find(([, s]) => pred(s)); return g ? g[0].toFixed(1) : '-'; };
console.log(`mode ${mode}: stop ${JSON.stringify(r)} at lab ms ${lab().toFixed(1)}, wall ${((Date.now() - t0) / 1000).toFixed(0)} s, problems: ${e.m.cores.problem()?.message ?? 'none'}`);
console.log(`first GUI state at ${first(() => true)} ms; first 0x5000 (live view starts) at ${first((s) => s === 0x5000)} ms; first 0x2000 (power off) at ${first((s) => s === 0x2000)} ms`);
console.log('GUI states:', gui.slice(0, 12).map(([t, s]) => `${t.toFixed(0)}:${(s >>> 0).toString(16)}`).join(' '));
console.log('quick start log:', e.fastLog.join(' | '));
console.log('firmware error log entries:', e.errLog.length, e.errLog.slice(0, 6).join(' ; '));
console.log('console tail:', e.console.split('\n').filter((l) => l && !/TAG_NOT_EXIST|^ 0000/.test(l)).slice(-6).join(' / '));
console.log('timeline:\n' + lines.slice(0, 80).join('\n'));
if (saveArg && saveArg.startsWith('save:')) {
  const out = Buffer.alloc(DRAM_END - DRAM);
  for (let a = DRAM; a < DRAM_END; a += CHUNK) out.set(e.rd(a, CHUNK), a - DRAM);
  fs.writeFileSync(saveArg.slice(5), zlib.gzipSync(out, { level: 1 }));
  console.log('DRAM saved to', saveArg.slice(5));
}

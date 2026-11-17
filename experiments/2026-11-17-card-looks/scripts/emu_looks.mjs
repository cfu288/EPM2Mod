// emu_looks.mjs STEP...: the card-looks build in the boot lab (run by emu_looks.py through tools/emu/emu-run).
// Steps: w:MS, key:NAME[:MS], dump:NAME, shot:NAME (a screenshot into $SHOTS). A dump prints one JSON line: the bytes of every span of $SPANS (the slot
// tables, in order), the store's first 32 bytes, the flags, and what the task did so far.
// Env: as play.mjs (E101_STATE, E101_CARD, E101_RTC); SPANS = a JSON file [[address, length], ...]; SYMS = a JSON
// file of the build's labels (T_TASK, T_STORED, V_BAD, T_END, SAVE, FLAGS, STORE).
import fs from 'node:fs';
import { createBoot } from '../../../tools/emu/e101/boot.mjs';
import { KEYS, press, release } from '../../../tools/emu/e101/keys.mjs';
import { screenshot } from '../../../tools/emu/e101/screen.mjs';
import { R, PC, SP, PSW, D0, h8 } from '../../../tools/emu/e101/machine.mjs';

const spans = JSON.parse(fs.readFileSync(process.env.SPANS, 'utf8'));
const sym = JSON.parse(fs.readFileSync(process.env.SYMS, 'utf8'));
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const ms = () => Number((e.m.devices.clock.t / 1e6).toFixed(1));
const events = [];
const at = (name, a, f) => e.hook(a, name, () => events.push([ms(), name, ...(f ? [f()] : [])]));
at('task', sym.T_TASK, () => e.r8(sym.FLAGS + 3));
at('verify-bad', sym.V_BAD);
at('verify-ok', sym.V_OK);
at('save', sym.SAVE);
at('apply', sym.APPLY);
at('task-end', sym.T_END);
const run = (t) => {
  const r = e.run({ maxLabMs: t, maxMs: 900000 });
  if (r.why !== 'labtime') { console.log(JSON.stringify({ stop: r, errors: e.errLog.slice(-5) })); process.exit(2); }
};
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'dump') {
    const hex = spans.map(([a, n]) => Buffer.from(e.rd(a, n)).toString('hex')).join('');
    console.log(JSON.stringify({ dump: f[1], ms: ms(), tables: hex, store: Buffer.from(e.rd(sym.STORE, 32)).toString('hex'),
      flags: Buffer.from(e.rd(sym.FLAGS + 0x40000000, 4)).toString('hex'), events: events.splice(0),
      flash: e.flashLog.splice(0).filter((l) => / (write|erase) /.test(l)).length, errors: e.errLog.length }));
  } else if (f[0] === 'shot') { fs.mkdirSync(process.env.SHOTS, { recursive: true }); screenshot(e, `${process.env.SHOTS}/${f[1]}.png`); }
  else { console.log('unknown step', step); process.exit(2); }
}
if (e.saveState()) console.log(JSON.stringify({ state: 'saved' }));
console.log(JSON.stringify({ done: ms(), errors: e.errLog, problems: e.m.cores.problem()?.message ?? 'none' }));

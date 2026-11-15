// Read-only views of the E-PM2's uITRON kernel objects (layout as om-emu's kernel spec for the same kernel family,
// checked on the E-PM2: kcb +124 static task table, +204 TCB pointer array; TCB +12 state, +16 id, +68 T_CTSK copy).
import fs from 'node:fs';
import path from 'node:path';
import { sym } from './sym.mjs';
import { REPO } from './paths.mjs';
const STATES = { 1: 'RUN', 2: 'RDY', 4: 'WAI', 8: 'SUS', 12: 'WAS', 16: 'DMT' };
let names = null;
function taskNames() {
  if (names) return names;
  names = new Map();
  try {
    const repo = REPO;
    for (const l of fs.readFileSync(path.join(repo, 'build/map/tasks.tsv'), 'utf8').split('\n').slice(1)) {
      const f = l.split('\t'); if (f.length > 3) names.set(parseInt(f[3], 16), f[2]);
    }
  } catch { /* none */ }
  return names;
}
export function tasks(e, cpu = 0) {
  const kcb = e.r32(0x8FF00004 + 4 * cpu), table = e.r32(kcb + 124), arr = e.r32(kcb + 204), out = [];
  const n = taskNames();
  for (let i = 0; i < 400; i++) {
    const id = e.r32(table + 28 * i); if (!id) break;
    const idx = id & 0xfff;
    const tcb = e.r32(arr + 4 * (idx - 1));
    if (tcb < 0x60000000) continue;
    const st = e.r16(tcb + 12), entry = e.r32(table + 28 * i + 12);
    out.push({ id, tcb, state: STATES[st] ?? st, entry, name: n.get(entry) ?? '?', sp: e.r32(tcb + 24), words: Array.from({ length: 16 }, (_, k) => e.r32(tcb + 4 * k)) });
  }
  return out;
}
export function taskReport(e, cpu = 0, { all = false } = {}) {
  return tasks(e, cpu).filter((t) => all || t.state !== 'DMT').map((t) => `${t.id.toString(16).padStart(4)} ${String(t.state).padEnd(3)} ${t.name.slice(0, 22).padEnd(22)} tcb=${t.tcb.toString(16)} sp=${t.sp.toString(16)} w=${t.words.slice(0, 12).map((w) => w.toString(16)).join(',')}`).join('\n');
}

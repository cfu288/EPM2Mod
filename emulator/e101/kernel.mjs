// Compatibility: the boot lab's task view (emulator/om-emu/emu/src/boot/e101.mjs tasks) with the task names of this
// repository's function database (build/map/tasks.tsv, when it exists).
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { OM_EMU_DIR, REPO } from './paths.mjs';
const body = await import(pathToFileURL(path.join(OM_EMU_DIR, 'emu/src/boot/e101.mjs')).href);
let names = null;
function taskNames() {
  if (names) return names;
  names = new Map();
  try {
    for (const l of fs.readFileSync(path.join(REPO, 'build/map/tasks.tsv'), 'utf8').split('\n').slice(1)) {
      const f = l.split('\t'); if (f.length > 3) names.set(parseInt(f[3], 16), f[2]);
    }
  } catch { /* none */ }
  return names;
}
export function tasks(e, cpu = 0) { return body.tasks(e, cpu, taskNames()); }
export function taskReport(e, cpu = 0, { all = false } = {}) { return body.taskReport(e, cpu, { all, names: taskNames() }); }

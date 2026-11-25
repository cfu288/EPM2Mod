import fs from 'node:fs';
import path from 'node:path';
import { REPO } from '../e101/paths.mjs';
const m = new Map();
try {
  const repo = REPO;
  for (const f of ['13c-event-ids.tsv', '15c-event-id-fixes.tsv']) for (const l of fs.readFileSync(path.join(repo, 'emulator/boot', f), 'utf8').split('\n').slice(1)) {
    const c = l.split('\t'); const id = Number(c[0]); if (!id) continue;
    const name = c.find((x, i) => i > 0 && /^ev[A-Z]/.test(x)) || c[5] || '';
    if (name && !m.has(id)) m.set(id, name);
  }
} catch { /* none */ }
export const evName = (id) => m.get(id) || '';

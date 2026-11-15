// Symbol help from the repo's function database (read-only): pc -> function start, first strings, task names.
import fs from 'node:fs';
import path from 'node:path';
import { REPO } from './paths.mjs';
let starts = null, strs = null;
function load() {
  if (starts) return;
  starts = []; strs = new Map();
  try {
    for (const l of fs.readFileSync(path.join(REPO, 'build/map/functions.tsv'), 'utf8').split('\n').slice(1)) { const a = parseInt(l.split('\t')[0], 16); if (a) starts.push(a); }
    starts.sort((a, b) => a - b);
    for (const l of fs.readFileSync(path.join(REPO, 'build/map/strrefs.tsv'), 'utf8').split('\n').slice(1)) {
      const f = l.split('\t'); const a = parseInt(f[0], 16); if (!a) continue;
      if (!strs.has(a)) strs.set(a, []); if (strs.get(a).length < 3) strs.get(a).push(f[3]);
    }
  } catch (e) { /* no database: addresses only */ }
}
export function fnOf(pc) {
  load(); pc >>>= 0;
  let lo = 0, hi = starts.length - 1, r = 0;
  while (lo <= hi) { const mid = (lo + hi) >> 1; if (starts[mid] <= pc) { r = starts[mid]; lo = mid + 1; } else hi = mid - 1; }
  return r;
}
export function sym(pc) {
  const f = fnOf(pc); if (!f) return (pc >>> 0).toString(16);
  const s = strs.get(f);
  return `${(pc >>> 0).toString(16)}(fn ${f.toString(16)}${s ? ' "' + s.join('|').slice(0, 60) + '"' : ''})`;
}
// heuristic backtrace: stack words that follow a call instruction
export function backtrace(e, sp, depth = 12, span = 0x400) {
  const out = [];
  for (let a = sp >>> 0; a < (sp >>> 0) + span && out.length < depth; a += 4) {
    let v; try { v = e.r32(a); } catch { break; }
    if (v < 0x7E421020 || v > 0x7F1A0FE0) continue;
    let b; try { b = e.rd(v - 7, 7); } catch { continue; }
    if (b[2] === 0xCD || b[0] === 0xDD || (b[1] === 0xFC && b[2] === 0xFF) || (b[5] === 0xF0 && (b[6] & 0xFC) === 0xF0) || (b[3] === 0xFA && b[4] === 0xFF)) out.push(`[sp+${(a - sp).toString(16)}] ${sym(v)}`);
  }
  return out;
}

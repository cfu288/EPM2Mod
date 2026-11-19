// watch_reads.mjs: a SETUP module for emulator/boot/play.mjs. It puts read watchpoints on the stored Picture
// Mode and ART mode code (the RAM image of the settings bank "mode") and writes every reader to WATCH_OUT (JSON):
//   SETUP=$PWD/experiments/2026-11-16-films-max/scripts/watch_reads.mjs WATCH_OUT=/tmp/scratch/reads.json \
//     emulator/emu-run builds/films-12.json play.mjs /tmp/scratch/shots STEP...
// A record: the pc of the reading instruction and the first six code addresses on the stack (the callers: the
// settings getter reads the byte for everybody, so the caller is what tells the readers apart).
// The bank is at 0x60404674 (emulator/e101/boot.mjs). Offsets found by choosing entries and comparing states:
// 51880 and 60080 = Picture Mode (prm 0x9481); 76, 808, 51421, 51532, 51540, 51868, 52560, 55364, 60373 = the
// ART mode code and its copies. Both address aliases (0x60.. and 0xA0..) are watched.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const repo = process.env.EPM2_REPO;
const { R, SP, h8, mem } = await import(pathToFileURL(path.join(repo, 'emulator/e101/machine.mjs')).href);
const BANK = 0x60404674;
const WATCHED = { 51880: 'picture mode', 60080: 'picture mode (copy)', 76: 'art code', 808: 'art code', 51421: 'art code', 51532: 'art code',
  51540: 'art code', 51868: 'art code', 52560: 'art code', 55364: 'art code', 60373: 'art code' };
export default function (e) {
  const seen = new Map();
  const list = []; let id = 0;
  for (const off of Object.keys(WATCHED)) for (const base of [BANK, BANK + 0x40000000])
    list.push({ id: id++, lo: (base + Number(off)) >>> 0, hi: ((base + Number(off)) >>> 0) + 1, kind: 1, stop: false });
  mem.setWatchpoints(list, { stop() {}, log(rec) {
    const sp = R[SP] >>> 0; const stack = [];
    for (let i = 0; i < 400 && stack.length < 6; i += 4) { let v; try { v = e.r32(sp + i) >>> 0; } catch { break; } if (v >= 0x7e430000 && v < 0x7f1a0000) stack.push(h8(v)); }
    const what = WATCHED[((rec.addr & 0x3fffffff) - (BANK & 0x3fffffff))];
    const key = `${h8(rec.pc)} ${what} ${stack.join(' ')}`;
    seen.set(key, (seen.get(key) || 0) + 1);
  } });
  process.on('exit', () => fs.writeFileSync(process.env.WATCH_OUT, JSON.stringify([...seen].map(([k, n]) => ({ key: k, n })), null, 1)));
}

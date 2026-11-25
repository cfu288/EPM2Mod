// hookhits.mjs SITES.txt MS: boot an image for MS ms of lab time and print, for each hook site of SITES.txt (one
// "0xADDR SEGMENT SPEC" per line), how often it ran and the lab time of its first run, and the time of the first GUI
// state and of the first 0x5000 (ShootingCommon: live view starts). The sites are observers: the pc is left alone.
//   emulator/emu-run build/peaking-mf.BIN /abs/path/hookhits.mjs /abs/path/hook-sites.txt 3000
// Extra sites: the GUI state trace 0x7ECDF6E4 and the end of the segment copies (segment 3's last constructor entry
// is reached through 0x7E44B6B0, the constructor walker).
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const REPO = process.env.EPM2_REPO;
const { createBoot } = await import(pathToFileURL(path.join(REPO, 'emulator/e101/boot.mjs')).href);
const { R, PC, SP, PSW, D0 } = await import(pathToFileURL(path.join(REPO, 'emulator/e101/machine.mjs')).href);

const [sitesFile, msArg] = process.argv.slice(2);
const sites = fs.readFileSync(sitesFile, 'utf8').split('\n').filter(Boolean).map((l) => l.split(/\s+/));
const e = createBoot({ blocksDir: process.env.BLOCKS });
const lab = () => e.m.devices.clock.t / 1e6;
const hits = new Map();
for (const [a, seg, spec] of sites) {
  const pc = parseInt(a, 16);
  hits.set(pc, { a, seg, spec, n: 0, t: null, cpu: new Set() });
  e.hook(pc, 'site', () => { const h = hits.get(pc); if (!h.n) h.t = lab(); h.n++; h.cpu.add(e.onCpu1 ? 1 : 0); });
}
let gui = null, lv = null, ctor = null;
e.hook(0x7ECDF6E4, 'gui', () => { if (gui === null) gui = lab(); if (lv === null && (R[D0] >>> 0) === 0x5000) lv = lab(); });
e.hook(0x7E44B6B0, 'ctor-walk', () => { ctor = lab(); });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const r = e.run({ maxLabMs: Number(msArg || 3000), maxMs: 1800000 });
console.log(`stop ${JSON.stringify(r)}; last constructor walk ${ctor?.toFixed(1)} ms; first GUI state ${gui?.toFixed(1)} ms; live view starts ${lv?.toFixed(1)} ms (lab time)`);
console.log('site        segment    spec                          runs  first ms  cpus  before-LV');
for (const h of [...hits.values()].sort((x, y) => (x.t ?? 1e12) - (y.t ?? 1e12))) {
  const before = h.t !== null && lv !== null && h.t < lv;
  console.log(`${h.a.padEnd(11)} ${h.seg.padEnd(10)} ${h.spec.padEnd(29)} ${String(h.n).padStart(5)} ${h.t === null ? '       -' : h.t.toFixed(1).padStart(9)}  ${[...h.cpu].join(',').padEnd(4)}  ${before ? 'yes' : ''}`);
}

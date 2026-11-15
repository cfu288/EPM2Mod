// update-boot.mjs [LABMS]: power on with OK held (pin 0x35 low from reset): the firmware-update path.
// E101_CARD=<folder> gives a card (put DCOLYMP/E1019999.BIN in it for "update file present").
// Prints the console, when the watched pcs are reached, and how far the boot got. NO_OK=1: OK not held (a normal start).
import { createBoot } from '../e101/boot.mjs';
import { tasks } from '../e101/kernel.mjs';
import { R, S, PC, SP, PSW } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
if (!process.env.NO_OK) e.pins.set(0x35, 0);
const W = { '7e5056ab': 'update flag byte cleared (OK held)', '7e504629': 'boot task takes the UPDATE branch', '7e504631': 'boot task takes the NORMAL branch',
  '7e504c18': 'segment-2 load call', '7e54350e': 'FIRMUP_CLI task body', '7e5435bd': 'firmup: binary file found', '7e5436c2': 'firmup: Are?', '7e54398b': 'FIRMUP_SRV task body' };
// WATCH=hex:name,hex:name adds pcs to report (for example a build's hook site and its target)
for (const w of (process.env.WATCH || '').split(',').filter(Boolean)) { const [p, ...n] = w.split(':'); W[p.toLowerCase()] = n.join(':') || 'watched pc'; }
const seen = {};
for (const [p, n] of Object.entries(W)) e.hook(parseInt(p, 16), 'w' + p, () => { if (!seen[p]) console.log(`t=${(e.m.devices.clock.t / 1e6).toFixed(3)} ms first reach ${p}: ${n}`); seen[p] = (seen[p] || 0) + 1; });
const r = e.run({ maxLabMs: Number(process.argv[2] || 3000), maxMs: 600000 });
console.log('stop:', JSON.stringify(r), 'lab ms', (e.m.devices.clock.t / 1e6).toFixed(1));
console.log('console:\n  ' + e.console.split('\n').filter((l) => !/TAG_NOT_EXIST|^ 0000/.test(l)).join('\n  '));
console.log('counts', JSON.stringify(seen));
for (const c of [0, 1]) { const by = {}; for (const t of tasks(e, c)) by[t.state] = (by[t.state] || 0) + 1; console.log(`cpu${c} tasks`, JSON.stringify(by)); }
console.log('errors', e.errLog.length, e.errLog.slice(0, 4).join(' ; '));
if (e.card) console.log(`card: ${e.card.reads} blocks read, ${e.card.writes} written`);
console.log('problems:', e.m.cores.problem()?.message ?? 'none');

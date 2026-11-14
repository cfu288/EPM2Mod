// trace-adjust.mjs OUTDIR STEP...: play.mjs with a trace of the level-gauge calibration chain (Level Adjust panel).
// Run from the emulator work folder (it imports ../e101/, our driver): $NODE level-adjust/trace-adjust.mjs OUT STEP...
// Steps: w:MS, key:NAME, tilt:X:Y:Z | tilt:off, shot:NAME (as play.mjs), dump:LABEL = print the stored offsets, and
//   raw:X:Y:Z | raw:off   accelerometer stand-in at the sample ring (1000 = 1 g). The driver's ring read 0x7E4585DC
//   then answers "sample" / "no sample" in turn and the sample is X, Y, Z. Unlike tilt: (which replaces the output of
//   the read 0x7E4583BF), the firmware's own offset and gain correction runs on it, so the effect of the stored
//   offsets shows on the gauge. raw: is this script's own stand-in; the emulator has no accelerometer chip.
// Printed per call: the panel's OK handler 0x7EE00535 (selected item), OlyHfwOpeLevel::calibration 0x7E9782AF / reset
// 0x7E97858C, api_adj_Set_Slope_Adjust 0x7E676261 (d0 = mode, d1 = rotate) and its return value, the driver entry
// 0x7E469F16 and 0x7E45937A (d0 = driver mode, d1 = orientation), the 100-sample measurement 0x7E459693, the
// factory -> user copy 0x7E4599EA, and every parameter write 0x7E457CED to a level tag (0x4E7A..0x4F2A).
import fs from 'node:fs';
import path from 'node:path';
import { createBoot } from '../e101/boot.mjs';
import { screenshot } from '../e101/screen.mjs';
import { KEYS, press, release } from '../e101/keys.mjs';
import { R, PC, SP, PSW, A0, A1, D0, D1, h8 } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const t = () => (e.m.devices.clock.t / 1e6).toFixed(1);
const say = (s) => console.log(`  t=${t()} ${s}`);
const TAGS = { 0x4E7A: 'factory x', 0x4E8A: 'factory y', 0x4E9A: 'factory z', 0x4EAA: 'factory temp', 0x4EBA: 'user x', 0x4ECA: 'user y', 0x4EDA: 'user z', 0x4EEA: 'user temp', 0x4EFA: 'adj x', 0x4F0A: 'adj y', 0x4F1A: 'adj z', 0x4F2A: 'adj 4' };
let reads = 0, sets = 0;
const d = (r) => R[r + 3] >>> 0;   // boot.mjs indexes data registers as R[D0 + 3] in its own hooks
const reg = (name) => { const m = e.regs().match(new RegExp(name + '=([0-9a-f]+)')); return parseInt(m[1], 16); };
e.hook(0x7EE00535, 't', () => say(`panel 173 OK handler 0x7EE00535`));
e.hook(0x7E9782AF, 't', () => say(`OlyHfwOpeLevel::calibration 0x7E9782AF`));
e.hook(0x7E97858C, 't', () => say(`OlyHfwOpeLevel::reset 0x7E97858C`));
e.hook(0x7E676261, 't', () => say(`api_adj_Set_Slope_Adjust 0x7E676261 mode d0=${reg('d0')} rotate d1=${reg('d1')}`));
e.hook(0x7E67629F, 't', () => say(`api_adj_Set_Slope_Adjust returns d0=${reg('d0') & 0xFFFF} (0 = ok); accelerometer reads so far ${reads}, level-tag writes ${sets}`));
e.hook(0x7E469F16, 't', () => say(`driver entry 0x7E469F16 mode d0=${reg('d0') & 0xFFFF} d1=${reg('d1') & 0xFFFF}`));
e.hook(0x7E45937A, 't', () => say(`calibration core 0x7E45937A mode d0=${reg('d0') & 0xFFFF} orientation d1=${reg('d1') & 0xFFFF}`));
e.hook(0x7E459693, 't', () => say(`measurement 0x7E459693 starts (100 samples)`));
e.hook(0x7E4599EA, 't', () => say(`copy factory -> user offsets 0x7E4599EA`));
e.hook(0x7E4583BF, 't', () => { reads++; });
let raw = null, phase = 0;
e.hook(0x7E4585DC, 'S-ACC-ring-raw', () => {
  if (!raw && !e.tilt) return;
  phase ^= 1;
  if (raw && !phase) { const a = R[A0] >>> 0; e.w32(a, raw[0] | 0); e.w32(a + 4, raw[1] | 0); e.w32(a + 8, raw[2] | 0); e.w32(a + 12, 0); }
  e.ret(phase ? 1 : 0);
});
e.hook(0x7E457CED, 't', () => { const tag = reg('d0') & 0xFFFF; if (TAGS[tag]) { sets++; const v = reg('a1') & 0xFFFF; say(`set tag 0x${tag.toString(16)} (${TAGS[tag]}) [${reg('d1') & 0xFFFF}] = ${v > 32767 ? v - 65536 : v}`); } });
const tagPtr = (tag) => e.r32(0x603A0E38 + 8 * (tag >> 4) + 4) >>> 0;
const r16 = (a) => { const w = e.r32(a & ~3) >>> 0; const v = (a & 2) ? w >>> 16 : w & 0xFFFF; return v > 32767 ? v - 65536 : v; };
const dump = (label) => {
  console.log(`dump ${label} (t=${t()}): six orientations per tag`);
  for (const tag of [0x4E7A, 0x4E8A, 0x4E9A, 0x4EAA, 0x4EBA, 0x4ECA, 0x4EDA, 0x4EEA]) { const p = tagPtr(tag); const v = []; for (let i = 0; i < 6; i++) v.push(r16(p + 2 * i)); console.log(`  0x${tag.toString(16)} ${TAGS[tag].padEnd(12)} at ${h8(p)}: ${v.join(' ')}`); }
};
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(3)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'tilt') { e.tilt = f[1] === 'off' ? null : [Number(f[1]), Number(f[2]), Number(f[3])]; console.log('--', step); }
  else if (f[0] === 'raw') { raw = f[1] === 'off' ? null : [Number(f[1]), Number(f[2]), Number(f[3])]; console.log('--', step); }
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } console.log('--', step); press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') { const file = path.join(out, f[1] + '.png'); screenshot(e, file); console.log('shot', file); }
  else if (f[0] === 'dump') dump(f.slice(1).join(':'));
  else { console.log('unknown step', step); process.exit(2); }
}
if (e.flashLog.length && process.env.FLASHLOG) console.log(e.flashLog.join('\n'));
if (e.saveState()) console.log('state saved to', e.stateFile);
console.log('done at lab ms', t(), '| firmware errors', e.errLog.length, e.errLog.slice(2).join(' ; '));

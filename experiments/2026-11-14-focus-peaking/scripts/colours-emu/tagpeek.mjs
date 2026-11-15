// tagpeek.mjs OUTDIR STEP...: play.mjs steps (w:MS, key:NAME, shot:NAME) plus tag:LABEL, which prints the stored value of
// the prm tag 0x8971 (setting 458, the Peaking row of the builds peaking-menu and peaking-colours): the byte that the firmware's index
// table 0x603A0E38 points to. E101_STATE as in play.mjs. Run from the emulator work folder.
import fs from 'node:fs';
import path from 'node:path';
import { createBoot } from '../e101/boot.mjs';
import { screenshot } from '../e101/screen.mjs';
import { KEYS, press, release } from '../e101/keys.mjs';
import { R, PC, SP, PSW } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
const TAG = 0x8971, NAMES = { 1: 'Off', 2: 'Red', 3: 'White', 4: 'Yellow', 5: 'Blue' };
function tag(label) {
  const ent = 0x603A0E38 + 8 * (TAG >> 4), head = e.r32(ent) >>> 0, ptr = e.r32(ent + 4) >>> 0;
  const v = e.r32(ptr & ~3) >>> (8 * (ptr & 3)) & 0xFF;
  console.log(`tag ${label}: index entry tag 0x${(head & 0xFFFF).toString(16)} count ${head >>> 16}, data at 0x${ptr.toString(16)}, value ${v} (${NAMES[v] || 'not in the list'})`);
}
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(3)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') { screenshot(e, path.join(out, f[1] + '.png')); console.log('shot', f[1]); }
  else if (f[0] === 'tag') tag(f[1]);
  else { console.log('unknown step', step); process.exit(2); }
}
if (e.saveState()) console.log('state saved to', e.stateFile);
console.log('done at lab ms', (e.m.devices.clock.t / 1e6).toFixed(0), '| firmware errors', e.errLog.length, e.errLog.slice(-3).join(' ; '));

// menu_tagplay.mjs OUTDIR STEP...: the steps of emulator/boot/play.mjs (w:MS, key:NAME[:MS], shot:NAME) plus
//   tag:HEX[:N] print the stored values of a prm tag (N bytes of an array tag; default 1 value, u8 or s16 by the low nibble),
//               read through the firmware's index table 0x603A0E38 (8 bytes per tag number)
// Run it with emulator/emu-run IMAGE /abs/path/to/menu_tagplay.mjs OUTDIR STEP...   (E101_STATE as in play.mjs). Copy of ../../2026-11-17-auto-iso-min-shutter/scripts/tagplay.mjs with N.
import fs from 'node:fs';
import path from 'node:path';
const E = path.join(process.env.EPM2_REPO, 'emulator/e101');
const { createBoot } = await import(path.join(E, 'boot.mjs'));
const { screenshot } = await import(path.join(E, 'screen.mjs'));
const { KEYS, press, release } = await import(path.join(E, 'keys.mjs'));
const { R, PC, SP, PSW } = await import(path.join(E, 'machine.mjs'));
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
function tag(hex, n) {
  const t = parseInt(hex, 16), ent = 0x603A0E38 + 8 * (t >> 4), head = e.r32(ent) >>> 0, ptr = e.r32(ent + 4) >>> 0;
  const b = (a) => (e.r32(a & ~3) >>> (8 * (a & 3))) & 0xFF;
  const wide = (t & 0xF) === 0xA || (t & 0xF) === 0x2;
  let v = wide ? b(ptr) | (b(ptr + 1) << 8) : b(ptr);
  if ((t & 0xF) === 0xA && v & 0x8000) v -= 0x10000;
  if (n) { const bs = []; for (let i = 0; i < Number(n); i++) bs.push(b(ptr + i)); console.log(`tag 0x${t.toString(16)}: count ${head >>> 16}, data at 0x${ptr.toString(16)}, bytes ${bs.join(' ')}`); return; }
  console.log(`tag 0x${t.toString(16)}: index entry 0x${(head & 0xFFFF).toString(16)} count ${head >>> 16}, data at 0x${ptr.toString(16)}, value ${v} (0x${(v & 0xFFFF).toString(16)})`);
}
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(3)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') { screenshot(e, path.join(out, f[1] + '.png')); console.log('shot', f[1]); }
  else if (f[0] === 'tag') tag(f[1], f[2]);
  else { console.log('unknown step', step); process.exit(2); }
}
if (e.saveState()) console.log('state saved to', e.stateFile);
console.log('done at lab ms', (e.m.devices.clock.t / 1e6).toFixed(0), '| firmware errors', e.errLog.length, e.errLog.slice(-3).join(' ; '));

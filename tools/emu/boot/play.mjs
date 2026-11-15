// play.mjs OUTDIR STEP...: boot, then run scripted steps and write screenshots into OUTDIR. Steps:
//   w:MS            run MS of lab time
//   key:NAME[:MS]   press a named key (table KEYS below) for MS (default 120), release, run 400 ms
//   pin:HEX:LEVEL   set a GIO input pin level;  adc:CH:VALUE (CH = * for all inputs);  port:HEX (system-controller ports)
//   tilt:X:Y:Z      accelerometer stand-in vector (16384 = 1 g), tilt:off = the native read (0, 0, 0)
//   shot:NAME       write OUTDIR/NAME.png
//   E101_CARD=folder  SD card model with a FAT16 image built from the folder (CARDLOG=N prints the first N commands)
//   E101_STATE=file  flash state (settings banks) loaded at start and saved at the end (see boot.mjs S-FLASHWRITE)
// The first step runs after BOOTMS (default 1500) of lab time. GUILOG=1 prints the GUI's event lines between steps.
import fs from 'node:fs';
import path from 'node:path';
import { createBoot } from '../e101/boot.mjs';
import { screenshot } from '../e101/screen.mjs';
import { KEYS, press, release } from '../e101/keys.mjs';
import { R, PC, SP, PSW, MDR, A1, D0, h8 } from '../e101/machine.mjs';
const e = createBoot({ blocksDir: process.env.BLOCKS });
if (process.env.SETUP) (await import(process.env.SETUP)).default(e);
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const glog = [];
if (process.env.GUILOG) {
  e.hook(0x7ECE6333, 'guilogv', () => { const s = e.cstr(R[A1] >>> 0, 60); if (/RCV_EV|key_event|keyID|state = /.test(s)) glog.push(`${(e.m.devices.clock.t / 1e6).toFixed(0)} ${s} ${h8(R[D0])}`); });
  e.hook(0x7ECE631E, 'guilog', () => { const s = e.cstr(R[A1] >>> 0, 60); if (process.env.GUILOG === '2' && !/getSetting|TouchPanel|EXCLUSIVE|waitEvent|isBackLight|NormalProc|updateResearch|getKeyState|getMedia|getExistMedia/.test(s)) glog.push(`${(e.m.devices.clock.t / 1e6).toFixed(0)} ${s}`); });
}
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(3)) {
  const f = step.split(':');
  if (f[0] === 'w') { if (!(Number(f[1]) > 0)) { console.log('bad step', step); process.exit(2); } run(Number(f[1])); }
  else if (f[0] === 'pin') e.pins.set(parseInt(f[1], 16), Number(f[2]));
  else if (f[0] === 'adc') { if (f[1] === '*') e.adc.fill(Number(f[2])); else e.adc[Number(f[1])] = Number(f[2]); }
  else if (f[0] === 'tilt') e.tilt = f[1] === 'off' ? null : [Number(f[1]), Number(f[2]), Number(f[3])];
  else if (f[0] === 'port') e.setPorts(parseInt(f[1], 16));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') { const file = path.join(out, f[1] + '.png'); screenshot(e, file); console.log('shot', file, 'osd runs', e.osd.runs, e.videoRom != null ? 'rom picture 0x' + e.videoRom.toString(16) : ''); }
  else { console.log('unknown step', step); process.exit(2); }
  if (glog.length) { console.log(`[${step}] ` + glog.splice(0).slice(-Number(process.env.GLN || 12)).join(' | ')); }
}
if (e.flashLog.length && process.env.FLASHLOG) console.log(e.flashLog.join('\n'));
if (e.saveState()) console.log('state saved to', e.stateFile);
if (e.card) { console.log(`card: ${e.card.reads} blocks read, ${e.card.writes} written; unknown commands ${[...e.card.unknown].join(' ') || 'none'}`); if (process.env.CARDLOG) console.log(e.card.log.slice(0, Number(process.env.CARDLOG)).join('\n')); if (e.card.dirty) { const { listFat } = await import('../e101/sdcard.mjs'); console.log('card files now:', listFat(e.card.img).map((f) => `${f.path} (${f.size})`).join(', ')); } if (e.saveCard) e.saveCard(); }
if (e.osd.log.length) console.log('osd notes:', e.osd.log.slice(0, 6));
console.log('done at lab ms', (e.m.devices.clock.t / 1e6).toFixed(0), '| errors', e.errLog.slice(-3).join(' ; '));

// emu_desc.mjs STEP...: the EXIF template's ImageDescription in the boot lab (run through emulator/emu-run).
// Steps: w:MS, key:NAME[:MS], shot:NAME (a screenshot into $SHOTS), dump:NAME. A dump prints one JSON line: the 32 bytes
// at 0x605BAEC0 (cached) and 0xA05BAEC0 (uncached), the Picture Mode that FILMNAME read last (at FN_PM), the value of
// the firmware's last prm_get of 0x9481, the loader's flags, and the calls counted since the last dump (FILMNAME,
// rec_art_set_exif_data 0x7E70DC24, the template fill 0x7E708F24).
// Env: as play.mjs (E101_STATE, E101_CARD, E101_RTC); SYMS = build/stock-films-2/syms.json.
import fs from 'node:fs';
import { createBoot } from '../../../emulator/e101/boot.mjs';
import { KEYS, press, release } from '../../../emulator/e101/keys.mjs';
import { screenshot } from '../../../emulator/e101/screen.mjs';
import { R, PC, SP, PSW } from '../../../emulator/e101/machine.mjs';

const sym = JSON.parse(fs.readFileSync(process.env.SYMS, 'utf8'));
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const ms = () => Number((e.m.devices.clock.t / 1e6).toFixed(1));
const count = { filmname: 0, exif_art: 0, template_fill: 0 };
let pm = null, prm = null, first = {};
e.hook(sym.FILMNAME, 'filmname', () => { count.filmname++; first.filmname ??= ms(); });
e.hook(sym.FN_PM, 'fn_pm', () => { pm = R[0] >>> 0; });
e.hook(0x7E70DC24, 'exif_art', () => { count.exif_art++; });
e.hook(0x7E708F24, 'template_fill', () => { count.template_fill++; first.template_fill ??= ms(); });
const seen = new Set();
let pending = false;
e.hook(0x7E457C75, 'prm_get', () => {
  if ((R[0] & 0xFFFF) !== 0x9481) return;
  pending = true;
  const ret = R[11] >>> 0;
  if (ret === sym.FN_PM >>> 0) { pending = false; return; }   // one hook per pc: FN_PM has its own
  if (!seen.has(ret)) { seen.add(ret); e.hook(ret, 'prm_ret', () => { if (pending) { pending = false; prm = R[0] >>> 0; } }); }
});
const text = (b) => Buffer.from(b).toString('latin1').replace(/\0/g, '\\0');
const run = (t) => {
  const r = e.run({ maxLabMs: t, maxMs: 900000 });
  if (r.why !== 'labtime') { console.log(JSON.stringify({ stop: r, errors: e.errLog.slice(-5) })); process.exit(2); }
};
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'dump') {
    console.log(JSON.stringify({ dump: f[1], ms: ms(), cached: text(e.rd(0x605BAEC0, 32)), uncached: text(e.rd(0xA05BAEC0, 32)),
      fn_pm: pm, prm_9481: prm, flags: Buffer.from(e.rd(sym.FLAGS + 0x40000000, 5)).toString('hex'), count: { ...count }, first }));
    for (const k in count) count[k] = 0;
  } else if (f[0] === 'shot') { fs.mkdirSync(process.env.SHOTS, { recursive: true }); screenshot(e, `${process.env.SHOTS}/${f[1]}.png`); }
  else { console.log('unknown step', step); process.exit(2); }
}
if (e.saveState()) console.log(JSON.stringify({ state: 'saved' }));
console.log(JSON.stringify({ done: ms(), errors: e.errLog.length, errlog: e.errLog.slice(0, 5), problems: e.m.cores.problem()?.message ?? 'none' }));

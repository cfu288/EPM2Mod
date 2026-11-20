// artbkt.mjs STEP...: rawedit.mjs's steps (w:MS, key:NAME[:MS], shot:NAME) on the ART BKT candidate, with stand-ins that
// let a RAW development run to the card without an image engine (NOTES.md section 8.4). Prints the callback events,
// the frame list SETUP made, each Picture Mode the run sets, the Picture Mode the developer sees at each preview, and
// the EXIF ImageDescription template at each save, and the files on the card at the end.
// Env: as rawedit.mjs (E101_STATE, E101_CARD, E101_RTC, SHOTS), plus
//   SYMS=data/specs/raw-edit-art-bkt.json (its _symbols; without it the run hooks are off: a stock image)
//   STANDIN=1: skip play_cic_decode_raw (no CIC interrupt in the emulator) and the histogram statistics 0x7E575651
//   (a division by zero on the engine's zero output), and treat the image-engine blocks 0x99000000-0x9AF00000 as plain
//   storage. HEADS=DIR: write the first 64 KB of each JPEG on the card there at the end. Stand-ins, not hardware models: the pictures are empty; the control flow is the firmware's.
import fs from 'node:fs';
const ROOT = new URL('../../../emulator/e101/', import.meta.url).href;
const { createBoot, listFat, backtrace } = await import(ROOT + 'boot.mjs');
const { KEYS, press, release } = await import(ROOT + 'keys.mjs');
const { screenshot } = await import(ROOT + 'screen.mjs');
const { R, PC, SP, PSW, D0, D1, A0, A1, A2, A3, MDR } = await import(ROOT + 'machine.mjs');
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const ms = () => Number((e.m.devices.clock.t / 1e6).toFixed(1));
const hex = (v) => (v >>> 0).toString(16);
const say = (...a) => console.log(ms(), ...a);
if (process.env.STANDIN) {
  for (let b = 0x99000000; b < 0x9B000000; b += 0x100000) { try { e.block(b, 'scratch plain ' + hex(b)); } catch { /* a device block */ } }
  e.hook(0x7E947D61, 'stand-in: cic decode', () => { R[D0] = 0; R[PC] = 0x7E947D68 | 0; });
  e.hook(0x7E575651, 'stand-in: statistics', () => e.ret(0));
}
const N = { 0x7EAD0163: 'ERaw state_start_current_mode', 0x7EAD1AE1: 'ERaw save_current_start', 0x7EAD3430: 'ERaw end_current_mode_edit',
  0x7E94B011: 'play_save_raw', 0x7E688268: 'api_rec_Reserve_Media' };
const desc = () => Buffer.from(e.rd(0x605BAEC0, 32)).toString('latin1').replace(/\0.*$/, '').trimEnd();  // EXIF ImageDescription
for (const [a, n] of Object.entries(N)) e.hook(Number(a), n, () => say(n, n.includes('save_current') ? `(ImageDescription "${desc()}")` : ''));
e.hook(0x7EDF7F60, 'cb', () => { if ((R[D1] >>> 0) !== 3) say('CB cmd', R[D0] >>> 0, 'status', R[D1] >>> 0, 'result', hex(R[A1])); });
e.hook(0x7E457CED, 'prm_set', () => { if ((R[D0] & 0xffff) === 0x9481) say('PRM_SET 0x9481 =', R[A1] >>> 0, 'from', hex(R[MDR])); });
e.hook(0x7E70DC24, 'rec_art_set_exif_data', () => say('developer: take', hex(R[A0]), 'mode byte +16479 =', e.rd(((R[A0] >>> 0) + 16479) >>> 0, 1)[0]));
if (process.env.SYMS) {
  const s = Object.fromEntries(Object.entries(JSON.parse(fs.readFileSync(process.env.SYMS, 'utf8'))._symbols).map(([k, v]) => [k, parseInt(v, 16)]));
  const list = () => { const out = []; for (let i = 0; i < 32; i++) { const v = e.rd(s.LIST + i, 1)[0]; if (!v) break; out.push(v); } return out; };
  const state = () => `ACT ${e.rd(s.ACT, 1)[0]} PH ${e.rd(s.PH, 1)[0]} K ${e.rd(s.K, 1)[0]}`;
  e.hook(s.ROWS, 'ROWS', () => say('ROWS row', e.rd(((R[A3] >>> 0) + 1744) >>> 0, 1)[0]));
  e.hook(s.CBDONE, 'CBDONE', () => say('CBDONE', state(), 'result', hex(R[A2])));
  e.hook(s.STOP, 'STOP', () => say('STOP', state(), 'PM0', e.r32(s.PM0)));
  // after SETUP: ACT is written last, then ret; read the list at the jump to the [Current] path
  e.hook(0x7EDF7E14, 'Current path', () => { if (e.rd(s.ACT, 1)[0]) say('SETUP list', JSON.stringify(list()), 'PM0', e.r32(s.PM0), state()); });
}
const fin = (why) => {
  if (process.env.HEADS && e.card) {  // the first 64 KB of each JPEG (the EXIF block), for exiftool
    fs.mkdirSync(process.env.HEADS, { recursive: true });
    for (const x of listFat(e.card.img)) if (/\.JPG$/.test(x.path)) fs.writeFileSync(`${process.env.HEADS}/${x.path.split('/').pop()}`, x.data().subarray(0, 65536));
  }
  const files = e.card ? listFat(e.card.img).filter((f) => /DCIM/.test(f.path)).map((f) => `${f.path} ${f.size}`) : [];
  console.log(JSON.stringify({ end: why, ms: ms(), pc: hex(R[PC]), files, errlog: e.errLog.slice(-6), problem: e.m.cores.problem()?.message ?? 'none' }));
};
const run = (t) => { const r = e.run({ maxLabMs: t, maxMs: 1800000 }); if (r.why !== 'labtime') { fin(r); console.log(backtrace(e, R[SP] >>> 0, 10).join(' | ')); process.exit(2); } };
run(Number(process.env.BOOTMS || 1500));
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  console.log('STEP', step, ms());
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') { fs.mkdirSync(process.env.SHOTS, { recursive: true }); screenshot(e, `${process.env.SHOTS}/${f[1]}.png`); }
  else { console.log('unknown step', step); process.exit(2); }
}
fin('done');

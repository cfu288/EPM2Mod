// findtext.mjs STEP...: artbkt.mjs's steps; at each hook site named in FIND_AT (hex, comma-separated) search RAM for
// the text FIND (latin1) and print where it is. Research probe for the film-name fix (plan.md section 5 step 2).
import fs from 'node:fs';
const ROOT = new URL('../../../emulator/e101/', import.meta.url).href;
const { createBoot, listFat } = await import(ROOT + 'boot.mjs');
const { KEYS, press, release } = await import(ROOT + 'keys.mjs');
const { screenshot } = await import(ROOT + 'screen.mjs');
const { R, PC, SP, PSW, D0, D1, A0, A1, A2, A3, MDR } = await import(ROOT + 'machine.mjs');
const e = createBoot({ blocksDir: process.env.BLOCKS });
R[PC] = 0x7E421020 | 0; R[SP] = 0x47001FFC | 0; R[PSW] = 0;
const ms = () => Number((e.m.devices.clock.t / 1e6).toFixed(1));
const hex = (v) => (v >>> 0).toString(16);
for (let b = 0x99000000; b < 0x9B000000; b += 0x100000) { try { e.block(b, 'scratch plain ' + hex(b)); } catch { /* device */ } }
e.hook(0x7E947D61, 'stand-in: cic decode', () => { R[D0] = 0; R[PC] = 0x7E947D68 | 0; });
e.hook(0x7E575651, 'stand-in: statistics', () => e.ret(0));
const needle = Buffer.from(process.env.FIND || 'RAWTEXT', 'latin1');
const search = (why) => {
  const hits = [];
  for (const [lo, hi] of [[0x60000000, 0x68000000], [0xB8000000, 0xC0000000]]) {
    for (let a = lo; a < hi; a += 0x100000) {
      let b; try { b = Buffer.from(e.rd(a >>> 0, 0x100000 + needle.length)); } catch { continue; }
      let i = -1; while ((i = b.indexOf(needle, i + 1)) >= 0 && i < 0x100000) hits.push(hex(a + i));
    }
  }
  console.log(ms(), 'FIND at', why, hits.join(' '));
};
for (const a of (process.env.FIND_AT || '').split(',').filter(Boolean)) e.hook(parseInt(a, 16), 'find ' + a, () => search(a + ' a0 ' + hex(R[A0]) + ' a1 ' + hex(R[A1]) + ' d0 ' + hex(R[D0])));
e.hook(0x7E9411B3, 'mode', () => console.log(ms(), 'set_exif_default: mode byte', R[D0] & 0xff, 'take', hex(R[A2]), 'kind (20,a3)', e.r16(((R[A3] >>> 0) + 20) >>> 0)));
e.hook(0x7E70DC24, 'rec_art_set_exif_data', () => console.log(ms(), 'developer: mode byte', e.rd(((R[A0] >>> 0) + 16479) >>> 0, 1)[0]));
e.hook(0x7EDF7F60, 'cb', () => { if ((R[D1] >>> 0) !== 3) console.log(ms(), 'CB', R[D0] >>> 0, R[D1] >>> 0, hex(R[A1])); });
const run = (t) => { const r = e.run({ maxLabMs: t, maxMs: 1800000 }); if (r.why !== 'labtime') { console.log('END', JSON.stringify(r), hex(R[PC])); process.exit(2); } };
run(1500);
for (const step of process.argv.slice(2)) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'shot') { fs.mkdirSync(process.env.SHOTS, { recursive: true }); screenshot(e, `${process.env.SHOTS}/${f[1]}.png`); }
  else if (f[0] === 'key') { press(e, f[1]); run(Number(f[2] || 120)); release(e, f[1]); run(400); }
}
if (process.env.HEADS) {
  fs.mkdirSync(process.env.HEADS, { recursive: true });
  for (const x of listFat(e.card.img)) if (/\.JPG$/.test(x.path)) fs.writeFileSync(`${process.env.HEADS}/${x.path.split('/').pop()}`, x.data().subarray(0, 65536));
}
console.log('files', listFat(e.card.img).filter((f) => /DCIM/.test(f.path)).map((f) => f.path).join(' '));

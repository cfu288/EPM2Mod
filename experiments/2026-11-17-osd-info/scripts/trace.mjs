// SETUP module for emulator/boot/play.mjs: observers for the GUI of the shooting screen.
//   SETUP=/abs/path/trace.mjs TRACE=create,kids TRACE_FROM=0 E101_STATE=... emulator/emu-run IMAGE play.mjs OUT STEP...
// TRACE (comma list):
//   create  widget factory 0x7ED17DB8: type, parent, resource record (44 bytes)
//   text    text label setText 0x7ED2D510 and set-by-text-id 0x7ED2CE0C
//   num     image-font string setter 0x7ED28AB1 (shutter speed, aperture, counts): widget id, font, text
//   vis     setVisible 0x7EDC1851
//   set     data-model set 0x7ECEF667: slot, size, bytes
//   batt    battery level API 0x7E68CC46 and every battery A/D result (0x7E539E70)
//   tick    panel first refresh 0x7ED60A95 and data-update refresh 0x7ED60F27 of the live-view panel
//   kids    at the end: the 155 child slots of the live-view panel (class 0x600A): type, id, rectangle, status
//   fonts   at the end: the image fonts (table 0x602BA8D8): characters of each
// Lines are printed at the end; the first number is lab time in ms. TRACE_FROM = first lab ms to log (default 1400).
const M = await import(process.env.EPM2_REPO + '/emulator/e101/machine.mjs');
const { R, D0, D1, A0, A1, MDR } = M;
const hx = (v) => (v >>> 0).toString(16);
export default function (e) {
  const from = Number(process.env.TRACE_FROM || 1400), t = () => e.m.devices.clock.t / 1e6;
  const out = [];
  const log = (s) => { if (t() >= from && out.length < 6000) out.push(t().toFixed(0) + ' ' + s); };
  const want = (process.env.TRACE || 'create,text,set,batt').split(',');
  const u = (a, n) => { const b = e.rd(a, n); let v = 0; for (let i = n - 1; i >= 0; i--) v = v * 256 + b[i]; return v; };
  const wstr = (p) => { let s = ''; if (p) for (let i = 0; i < 24; i++) { const c = u(p + 2 * i, 2); if (!c) break; s += c < 127 && c > 31 ? String.fromCharCode(c) : `\\u${hx(c)}`; } return s; };
  const wid = (w) => `id${u(w, 8) && u(w + 6, 2)}@(${u(w + 8, 2) << 16 >> 16},${u(w + 10, 2) << 16 >> 16})`;
  if (want.includes('create')) e.hook(0x7ED17DB8, 't-create', () => { const r = R[A1] >>> 0; log(`create type=${hx(R[D0])} parent=${hx(R[D1])} res=${hx(r)} ${r ? Buffer.from(e.rd(r, 44)).toString('hex') : ''} from ${hx(R[MDR])}`); });
  if (want.includes('text')) {
    e.hook(0x7ED2D510, 't-settext', () => log(`setText w=${hx(R[A0])} "${wstr(R[A1] >>> 0)}" from ${hx(R[MDR])}`));
    e.hook(0x7ED2CE0C, 't-setid', () => log(`setTextId w=${hx(R[A0])} id=${R[D0] & 0xffff} from ${hx(R[MDR])}`));
  }
  if (want.includes('num')) e.hook(0x7ED28AB1, 't-numstr', () => log(`numstr ${wid(R[A0] >>> 0)} font=${u((R[A0] >>> 0) + 128, 1)} "${wstr(R[A1] >>> 0)}" from ${hx(R[MDR])}`));
  if (want.includes('vis')) e.hook(0x7EDC1851, 't-vis', () => { const w = R[A0] >>> 0; if (w) log(`vis ${wid(w)} ${R[D0] & 1} from ${hx(R[MDR])}`); });
  if (want.includes('set')) e.hook(0x7ECEF667, 't-dmset', () => log(`dmset slot=${R[D0]} size=${R[D1]} ${Buffer.from(e.rd(R[A0] >>> 0, Math.min(R[D1], 80))).toString('hex')} from ${hx(R[MDR])}`));
  if (want.includes('tick')) { e.hook(0x7ED60F27, 't-upd', () => log('panel update')); e.hook(0x7ED60A95, 't-init', () => log('panel first refresh')); }
  if (want.includes('batt')) {
    e.hook(0x7E68CC46, 't-battlevel', () => log(`battery level API read from ${hx(R[MDR])}`));
    e.hook(0x7E539E70, 't-adc', () => log(`battery module A/D read -> ${R[D0] & 0xffff}`));
  }
  let panel = 0;
  if (want.includes('kids')) e.hook(0x7ED17DB8, 't-panel', () => { if ((R[D0] & 0xffff) === 0x8013) panel = R[D1] >>> 0; });
  process.on('exit', () => {
    console.log(out.join('\n'));
    if (want.includes('kids') && panel) for (let i = 0; i < 155; i++) {
      const w = u(panel + 792 + 4 * i, 4);
      if (w < 0x60000000 || w > 0x61000000) { console.log(`kid ${i} off=${792 + 4 * i} -`); continue; }
      console.log(`kid ${i} off=${792 + 4 * i} type=${hx(u(w + 4, 2))} id=${u(w + 6, 2)} xy=(${u(w + 8, 2) << 16 >> 16},${u(w + 10, 2) << 16 >> 16}) wh=(${u(w + 12, 2)},${u(w + 14, 2)}) status=${hx(u(w + 16, 4))}`);
    }
    if (want.includes('fonts')) for (let f = 1; f < 31; f++) {
      const p = u(0x602BA8D8 + 4 * f, 4); if (!p) continue;
      let s = '', first = 0;
      for (let i = 0; i < 256; i++) { const c = u(p + 4 * i, 2), im = u(p + 4 * i + 2, 2); if (!c) break; if (!first) first = im; s += c > 32 && c < 127 ? String.fromCharCode(c) : `[${hx(c)}]`; }
      console.log(`font ${f} table=${hx(p)} first image=${first} chars=${s}`);
    }
  });
}

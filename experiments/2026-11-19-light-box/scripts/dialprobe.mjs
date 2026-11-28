// dialprobe.mjs BIN STATE CARD OUTDIR STEP...: lbprobe.mjs with the control dial. The lab has no dial, so a dial
// detent rides on a key press: `dial:DELTA[:EVENT]` presses KEYN (env, default UP; use OK, KEYEV=900c, when INFO is
// held: UP and INFO share the ADC ladder) and turns its GUI event (KEYEV, the message builder 0x7ECE7597) into
// ST_CHANGE_MAIN_DIAL 0x9032; the dial filter 0x7EDC4F9D then gets DELTA as the detent count (hook 0x7EDC4FBA).
//   OM_EMU_DIR=... OM_EMU_MODEL=E101 KEYN=OK KEYEV=900c node dialprobe.mjs build/X.BIN state.json card/ out/ \
//     settag:9171:1:0 settag:9171:4:1 key:PLAY w:1500 key:INFO w:1500 dial:1 w:800 dial:-1 w:800
// Steps: w:MS, key:NAME, hold:NAME, rel:NAME, shot:NAME, tag:HEX[:I], settag:HEX:I:V, dial:DELTA[:EVENT].
// SET342=N overrides setting 342 (Dial Function, playback) where 0x7ED01A81 reads it.
// The lab decodes no JPEG, so a picture's size is 0: the divisors of the `div` sites in divs.txt are set to 1 when
// they are 0 (lab only). gjs-sites.txt and 9a40-sites.txt are the call sites of getJumpState and the posts of
// GUI_PLAY_ERROR 0x9A40 (build/map/functions.txt of the stock block 0). Printed per step: the handlers and paths
// taken, then the SS, the state and CPlayLightBox's zoom ratio. NOTES.md, "Light Box dial (2026-11-28)".
import fs from 'node:fs';
import path from 'node:path';

const OM = process.env.OM_EMU_DIR;
const imp = (p) => import(path.join(OM, 'emu', p));
const host = await imp('host/boot.mjs');
const { createE101 } = await imp('src/boot/e101.mjs');
const { compose } = await imp('src/boot/e101screen.mjs');
const { KEYS, press, release } = await imp('src/boot/e101keys.mjs');
const { buildFat16 } = await imp('src/boot/e101card.mjs');
const { R, D0, SP } = await imp('src/boot/bootlab.mjs');

const [bin, stateFile, cardDir, out, ...steps] = process.argv.slice(2);
const fw = host.readBin(bin, 'E101');
// JPEG=store: the codec block 0x99400000 as plain storage and the PLAY commands run natively; else they are faked
const apiFake = (process.env.APIFAKE ?? '80:1,80:5').split(',').filter(Boolean);
if (process.env.JPEG !== 'store') for (let i = 0; i < 64; i++) apiFake.push(`80:${i.toString(16)}`);
const e = createE101({
  rom: fw.rom, blocks: fw.blocks, flashState: host.readState(stateFile), card: buildFat16(host.folderTree(cardDir)).img,
  rtc: host.rtcSeconds('2026-11-24T12:00:00'), fast: false, cam: false, img: false, flashWrites: true, tilt: null,
  apiFake: [...new Set(apiFake)],
});
if (process.env.JPEG === 'store') for (const b of (process.env.STORE ?? '99400000').split(',')) e.block(parseInt(b, 16), 'lbprobe: plain storage');
const probes = [];
const tagPtr = (hex, i = 0) => { const t = parseInt(hex, 16); return (e.r32(0x603A0E38 + 8 * (t >> 4) + 4) + Number(i)) >>> 0; };
const tag = (hex, i = 0) => console.log(`tag 0x${hex}[${i}] = ${e.r8(tagPtr(hex, i))}`);
const sp32 = (o) => e.r32((R[SP] >>> 0) + o);
const sp8 = (o) => e.r8((R[SP] >>> 0) + o);
const A1 = 5;
let pending = null, count = null;
// guiEventFilter::changeEventMainDial 0x7EDC4F9D reads the dial's detent count through the API (vt+72, out (12,sp));
// the injected event gets the count here (d0 = 0: read done)
e.hook(0x7EDC4FBA, 'dialcount', () => { const real = e.r16((R[SP] >>> 0) + 12); if (count !== null) { R[D0] = 0; e.w16((R[SP] >>> 0) + 12, count & 0xffff); probes.push(`changeEventMainDial: count ${count} (API gave ${real})`); count = null; } else probes.push(`changeEventMainDial: API count ${real} d0=${R[D0]|0}`); });
const KEYN = process.env.KEYN ?? 'UP', KEYEV = parseInt(process.env.KEYEV ?? '9004', 16);
const VERB = !!process.env.VERB;
e.hook(0x7ECE67E1, 'sendEventToGui', () => {
  const m = R[A1] >>> 0, code = e.r32(m);
  if (VERB && code !== 1) probes.push(`toGui code 0x${code.toString(16)} p=${e.r32(m + 4) | 0}`);
});
// GuiCallerImp::sendEvent (no parameter) at its call of the message builder 0x7ECE7597: d0 = GUI event. An UP press
// (0x9004) is turned into the dial event with the delta in d1, as the dial path 0x7ECE700A builds it (a0 = a1 = 0)
e.hook(0x7ECE7597, 'inject', () => {
  if (VERB) probes.push(`sendEvent d0=0x${(R[D0]>>>0).toString(16)}`);
  if (pending !== null && (R[D0] & 0xffff) === KEYEV) { R[D0] = pending.ev; R[1] = pending.delta >>> 0; R[4] = 0; R[A1] = 0; probes.push(`INJECT event 0x${pending.ev.toString(16)} delta ${pending.delta}`); count = pending.delta; pending = null; }
});
// the lab decodes no JPEG, so the picture's size is 0: a zoom's scale division 0x7ED00CF6 divides by 0 (lab only)
for (const line of fs.readFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), 'divs.txt'), 'utf8').trim().split('\n')) {
  const [a, r] = line.split(' '); const reg = Number(r), pc = parseInt(a, 16);
  e.hook(pc, 'div0', () => { if ((R[reg] | 0) === 0) { R[reg] = 1; probes.push(`   (lab: divisor 0 set to 1 at ${a})`); } });
}
for (const site of fs.readFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), 'gjs-sites.txt'), 'utf8').trim().split(' '))
  e.hook(parseInt(site, 16), 'gjs-site', () => probes.push(`   call getJumpState at 0x${site}`));
for (const site of fs.readFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), '9a40-sites.txt'), 'utf8').trim().split(' '))
  e.hook(parseInt(site, 16), '9a40-site', () => probes.push(`   post 0x9A40 at 0x${site}`));
const P = (a, n, f) => e.hook(a, n, () => probes.push(f()));
P(0x7EDBAF84, 'lb16-main', () => `LB state16 MAIN-dial ss handler d0=0x${(R[D0] >>> 0).toString(16)} a1=${R[A1] | 0}`);
P(0x7EDBA0A9, 'lb16-sub', () => `LB state16 SUB-dial ss handler d0=0x${(R[D0] >>> 0).toString(16)} a1=${R[A1] | 0}`);
P(0x7EDBD84E, 'lb17-main', () => `LB state17 MAIN-dial ss handler a1=${R[A1] | 0}`);
P(0x7EDBAD85, 'sf-main', () => `single-frame MAIN-dial ss handler a1=${R[A1] | 0}`);
P(0x7EDBA59E, 'sf-sub', () => `single-frame SUB-dial ss handler a1=${R[A1] | 0}`);
P(0x7ED01A94, 'dialfn', () => { if (process.env.SET342) e.w32((R[SP] >>> 0) + 4, Number(process.env.SET342)); return `0x7ED01A81: event 0x${(R[2] >>> 0).toString(16)} setting342=${sp32(4)}`; });
P(0x7ED0E05B, 'e05b', () => `-> 0x7ED0E05B (EvtStChgMainDial: picture move unless INFO held) d1=${R[1] | 0}`);
P(0x7ED0E085, 'e05b-info', () => `   INFO-held flag (+24) = ${R[D0] | 0}`);
P(0x7ED0DFA0, 'dfa0', () => `-> 0x7ED0DFA0 (zoom) d1=${R[1] | 0}`);
P(0x7ED0DFAF, 'dfa0-ratio', () => `   zoom ratio = ${R[D0] & 0xffff}`);
P(0x7ED06181, 'lbcmd', () => `   CPlayLightBox cmd ${R[2] | 0} sub-mode (+24) ${R[D0] | 0}`);
P(0x7ED0D77C, 'd77c', () => `-> 0x7ED0D77C (single-frame prev/next)`);
P(0x7ED0D8D6, 'd8d6', () => `-> 0x7ED0D8D6 (single-frame zoom)`);
P(0x7ED05F76, 'zi', () => `   zoomImage 0x7ED05F5E: API info (124,sp)=${sp32(124)} (76,sp)=${sp32(76)} -> ${sp32(124)||sp32(76) ? 'posts 0x9A40 GUI_PLAY_ERROR' : 'zooms'}`);
P(0x7EDBCF4B, 'perr', () => `   0x9A40 GUI_PLAY_ERROR handler 0x7EDBCF4B in state ${e.r8((R[4]>>>0)+1)}`);
P(0x7ED09135, 'gjs', () => `-> getJumpState 0x7ED09135 d0=${R[D0] | 0} from 0x${e.r32(R[SP] >>> 0).toString(16)}`);
P(0x7ED09611, 'gjs-ret', () => `   getJumpState returns ${R[3] & 0xff}`);
P(0x7ED09400, 'gjs-read', () => `   getJumpState reads 257=${sp32(32)} 321=${sp32(20)} check1=${R[D0] >>> 0}`);
P(0x7ED09616, 'gjs2', () => `-> twin 0x7ED09616 d0=${R[D0] | 0}`);
P(0x7EDBAFEE, 'lb16-ret', () => `   state16 main-dial handler returns state ${sp8(17)}`);
P(0x7EDBD8FC, 'lb17-ret', () => `   state17 main-dial handler returns ${R[2] & 0xff}`);
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log(probes.splice(0).join('\n  ')); console.log('STOP', JSON.stringify(r)); process.exit(2); } };
fs.mkdirSync(out, { recursive: true });
run(1500);
for (const step of steps) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { press(e, f[1]); run(120); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') host.writePng(path.join(out, f[1] + '.png'), compose(e));
  else if (f[0] === 'tag') tag(f[1], f[2]);
  else if (f[0] === 'settag') { e.w8(tagPtr(f[1], f[2]), Number(f[3])); tag(f[1], f[2]); }
  // dial:DELTA[:CODE] rides on the next UP press: its GUI message becomes CODE (0x3D main dial, 0x3E sub dial)
  else if (f[0] === 'dial') { pending = { delta: Number(f[1]), ev: f[2] ? parseInt(f[2], 16) : 0x9032 }; press(e, KEYN); run(120); release(e, KEYN); run(600); }
  else if (f[0] === 'hold') { press(e, f[1]); run(400); }
  else if (f[0] === 'rel') { release(e, f[1]); run(400); }
  else { console.log('unknown step', step); process.exit(2); }
  probes.push(`=> SS ${e.r8(0x6069FAC8)} state ${e.r8(0x6069FAC9)}; zoom ratio ${e.r32(0x602B605C) ? e.r16(e.r32(0x602B605C) + 32) : '-'}`);
  if (probes.length) console.log(`[${step}]\n  ` + probes.splice(0).join('\n  '));
}
console.log('done at lab ms', e.labMs().toFixed(0), '| errors', e.errLog.length, e.errLog.slice(-2).join(' ; '));

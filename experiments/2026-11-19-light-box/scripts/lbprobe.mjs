// lbprobe.mjs BIN STATE CARD OUTDIR STEP...: the boot lab's play (om-emu emu/bin/boot.mjs play) with probes in the
// INFO key's rule of single-picture playback, CPlaySingleFrame::getJumpState 0x7ED09135 (design.md section 3).
//   OM_EMU_DIR=... OM_EMU_MODEL=E101 node lbprobe.mjs build/light-box.BIN state.json card/ out/ w:500 key:PLAY ...
// Steps as play: w:MS, key:NAME, shot:NAME. The PLAY module's API commands (queue 80, 0..0x3f) are answered "done" by
// the lab (S-TAKEAPI's apiFake), because a picture's decode reads the JPEG codec 0x99400000, which the lab does not
// model (it faults at 0x7E557770 without this). So no picture is drawn; the GUI's states run.
// Printed per INFO step: the values getJumpState reads and the state it returns.
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
// tag:HEX[:I] prints the stored value I (default 0) of a prm tag (u8), through the firmware's index table 0x603A0E38 (as
// experiments/2026-11-17-auto-iso-min-shutter/scripts/tagplay.mjs)
const tag = (hex, i = 0) => {
  const t = parseInt(hex, 16), ptr = (e.r32(0x603A0E38 + 8 * (t >> 4) + 4) + Number(i)) >>> 0;
  console.log(`tag 0x${t.toString(16)}[${i}] = ${(e.r32(ptr & ~3) >>> (8 * (ptr & 3))) & 0xff}`);
};
const sp32 = (o) => e.r32((R[SP] >>> 0) + o);
// after the call of check 1 (0x7ED009D6): (32,sp) = setting 257, (20,sp) = setting 321, d0 = the check
e.hook(0x7ED09400, 'lb-read', () => probes.push(`getJumpState: 257=${sp32(32)} 321=${sp32(20)} check1=${R[D0] >>> 0}`));
e.hook(0x7ED0940F, 'lb-mode11', () => probes.push('display mode (info 27) := 11'));
e.hook(0x7ED09609, 'lb-check2', () => probes.push(`state-15 path: check2=${R[D0] >>> 0}`));
e.hook(0x7ED09611, 'lb-ret', () => probes.push(`getJumpState returns ${R[3] & 0xff}`));
const run = (ms) => { const r = e.run({ maxLabMs: ms, maxMs: 600000 }); if (r.why !== 'labtime') { console.log('STOP', JSON.stringify(r)); process.exit(2); } };
fs.mkdirSync(out, { recursive: true });
run(1500);
for (const step of steps) {
  const f = step.split(':');
  if (f[0] === 'w') run(Number(f[1]));
  else if (f[0] === 'key') { if (!KEYS[f[1]]) { console.log('unknown key', f[1]); process.exit(2); } press(e, f[1]); run(120); release(e, f[1]); run(400); }
  else if (f[0] === 'shot') host.writePng(path.join(out, f[1] + '.png'), compose(e));
  else if (f[0] === 'tag') tag(f[1], f[2]);
  else { console.log('unknown step', step); process.exit(2); }
  if (probes.length) console.log(`[${step}] ` + probes.splice(0).join(' | '));
}
if (process.env.TAKELOG) console.log(e.takeLog.filter((l) => !/queue 113 cmd 19 /.test(l)).join('\n'));
console.log('done at lab ms', e.labMs().toFixed(0), '| errors', e.errLog.length, e.errLog.slice(-2).join(' ; '));

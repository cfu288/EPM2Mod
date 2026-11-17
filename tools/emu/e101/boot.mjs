// Compatibility for the scripts of this repository: createBoot({blocksDir}) as the earlier drivers had it, on the om-emu
// fork's boot lab (third_party/om-emu/emu/src/boot/e101.mjs createE101). The environment the earlier drivers read is
// read here and given to the boot lab as its options:
//   E101_STATE, E101_CARD, E101_CARD_IMG, E101_RTC, E101_CD, E101_FAST, E101_NOFLASHWRITE, E101_CAM, E101_IMG,
//   E101_TAKEFAKE, E101_APIFAKE, E101_TILT (tools/emu/boot/README.md)
// and the lab gets the earlier members saveState() and saveCard(), which write those files.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { OM_EMU_DIR, loadBlocks, R, S, PC, SP, h8 } from './machine.mjs';
import { sym, backtrace } from './sym.mjs';
const imp = (p) => import(pathToFileURL(path.join(OM_EMU_DIR, 'emu', p)).href);
const { createE101 } = await imp('src/boot/e101.mjs');
const card = await imp('src/boot/e101card.mjs');
const host = await imp('host/boot.mjs');
export const listFat = card.listFat;
export { sym, backtrace };

export function createBoot(opts = {}) {
  const env = process.env, blocks = loadBlocks(opts.blocksDir);
  const rom = blocks.find((b) => b.block.flags === 0x0100).data;
  const stateFile = opts.stateFile ?? env.E101_STATE ?? null;
  const cardDir = opts.cardDir ?? env.E101_CARD, imgFile = env.E101_CARD_IMG;
  let img = null;
  if (imgFile && fs.existsSync(imgFile)) img = new Uint8Array(fs.readFileSync(imgFile));
  else if (cardDir || imgFile) img = card.buildFat16(cardDir ? host.folderTree(cardDir) : { entries: [] }).img;
  const list = (s, f) => s.split(',').filter((x) => x && x !== 'none').map(f);
  const e = createE101({
    rom, blocks, sym, faithfulLoad: opts.faithfulLoad ?? true,
    log: opts.verbose ? (s) => process.stderr.write(s + '\n') : null, consoleOut: opts.verbose ? (c) => process.stderr.write(c) : null,
    flashState: stateFile ? host.readState(stateFile) : null, flashWrites: !env.E101_NOFLASHWRITE,
    rtc: env.E101_RTC ? host.rtcSeconds(env.E101_RTC) : null, card: img, cardDetect: Number(env.E101_CD ?? 1),
    fast: !!env.E101_FAST, cam: !!env.E101_CAM, img: !!env.E101_IMG,
    takeFake: list(env.E101_TAKEFAKE ?? '19', (x) => parseInt(x, 16)), apiFake: list(env.E101_APIFAKE ?? '80:5,80:1', (x) => x),
    tilt: env.E101_TILT ? env.E101_TILT.split(',').map(Number) : null,
  });
  e.stateFile = stateFile;
  e.saveState = () => { if (!e.stateFile) return false; host.writeState(e.stateFile, e.flashStateDoc()); return true; };
  if (e.card) e.saveCard = () => { if (imgFile && e.card.dirty) fs.writeFileSync(imgFile, e.card.img); };
  return e;
}
export function report(e, r) {
  const out = [JSON.stringify(r) + ' ' + e.regs() + ' insns ' + S.insns, 'at ' + sym(R[PC]), ...backtrace(e, R[SP])];
  const t = e.stderrTail(600); if (t) out.push(t);
  return out.join('\n');
}
export function seenReport(e, max = 60) {
  return [...e.seen.entries()].slice(-max).map(([k, v]) => `${k} n=${v.n} pc=${sym(v.pc)} v=${h8(v.v)} w=${v.w}`).join('\n');
}

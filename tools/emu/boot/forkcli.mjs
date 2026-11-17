// The boot tools of this folder (play.mjs, crawl.mjs, stage2-boot.mjs, update-boot.mjs, shot.mjs) as the earlier
// drivers had them, run by the om-emu fork's tool: third_party/om-emu/emu/bin/boot.mjs report | update | play | crawl.
// The arguments pass through; the environment the earlier drivers read becomes the fork tool's options:
//   BLOCKS (the image's unpacked folder) or EMU_BIN -> --bin (the .BIN: EMU_BIN, else the .BIN tools/emu/emuenv.py
//   unpacked into that folder: stock, or build/NAME.BIN, its sha256 the folder name's), E101_STATE -> --state,
//   E101_CARD -> --card, E101_CARD_IMG -> --card-img, E101_RTC -> --rtc, E101_TILT -> --tilt, E101_FAST -> --fast,
//   E101_CAM -> --cam, E101_IMG -> --img, E101_TAKEFAKE -> --take-fake, E101_APIFAKE -> --api-fake,
//   E101_NOFLASHWRITE -> --no-flash-write, E101_CD -> --card-detect, BOOTMS -> --boot-ms; play: GUILOG -> --gui-log,
//   GLN -> --gui-lines, FLASHLOG -> --flash-log, CARDLOG -> --card-log; update: NO_OK -> --no-ok, WATCH -> --watch;
//   crawl: DEPTH, MAXLIST, MAXSHOTS, BUDGET, TOPMAX -> --depth, --maxlist, --maxshots, --budget, --topmax.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { REPO, OM_EMU_DIR } from '../e101/paths.mjs';

const sha8 = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 8);
function binOf(env) {
  if (env.EMU_BIN) return env.EMU_BIN;
  if (!env.BLOCKS) return null;
  const m = /^(.*)-([0-9a-f]{8})$/.exec(path.basename(path.resolve(env.BLOCKS)));
  if (!m) return null;
  const cands = m[1] === 'stock' ? [path.join(REPO, 'firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN')] : [path.join(REPO, 'build', m[1] + '.BIN')];
  return cands.find((f) => fs.existsSync(f) && sha8(f) === m[2]) ?? null;
}
export function forkArgs(cmd, args, env = process.env) {
  const bin = binOf(env);
  if (!bin) { console.error(`no .BIN for BLOCKS=${env.BLOCKS ?? ''}: run the tool through tools/emu/emu-run IMAGE, or set EMU_BIN`); process.exit(3); }
  const out = [cmd, '--bin', bin];
  const opt = (v, flag, value = true) => { if (v !== undefined && v !== '') out.push(...(value ? [flag, v] : [flag])); };
  opt(env.E101_STATE, '--state'); opt(env.E101_CARD, '--card'); opt(env.E101_CARD_IMG, '--card-img'); opt(env.E101_RTC, '--rtc');
  opt(env.E101_TILT, '--tilt'); opt(env.E101_FAST, '--fast', false); opt(env.E101_CAM, '--cam', false); opt(env.E101_IMG, '--img', false);
  opt(env.E101_TAKEFAKE, '--take-fake'); opt(env.E101_APIFAKE, '--api-fake'); opt(env.E101_NOFLASHWRITE, '--no-flash-write', false);
  opt(env.E101_CD, '--card-detect');
  if (cmd === 'play' || cmd === 'crawl') opt(env.BOOTMS, '--boot-ms');
  if (cmd === 'play') { opt(env.GUILOG, '--gui-log'); opt(env.GLN, '--gui-lines'); opt(env.FLASHLOG, '--flash-log', false); opt(env.CARDLOG, '--card-log'); }
  if (cmd === 'update') { opt(env.NO_OK, '--no-ok', false); for (const w of (env.WATCH || '').split(',').filter(Boolean)) out.push('--watch', w); }
  if (cmd === 'crawl') { opt(env.DEPTH, '--depth'); opt(env.MAXLIST, '--maxlist'); opt(env.MAXSHOTS, '--maxshots'); opt(env.BUDGET, '--budget'); opt(env.TOPMAX, '--topmax'); }
  return [...out, ...args];
}
export function runFork(cmd, args) {
  const env = { ...process.env, OM_EMU_MODEL: 'E101' };
  const r = spawnSync(process.execPath, [path.join(OM_EMU_DIR, 'emu/bin/boot.mjs'), ...forkArgs(cmd, args)], { stdio: 'inherit', env });
  process.exit(r.status ?? 1);
}

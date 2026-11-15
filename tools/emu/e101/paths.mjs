// Paths the drivers use. Every one comes from the environment, with a default inside the repository.
//   EPM2_REPO    the repository root (default: two folders above tools/emu/e101/)
//   OM_EMU_DIR   the patched om-emu working tree (default: REPO/build/om-emu, made by tools/emu/setup.sh)
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

export const REPO = process.env.EPM2_REPO || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
export const OM_EMU_DIR = process.env.OM_EMU_DIR || path.join(REPO, 'build/om-emu');
if (!fs.existsSync(path.join(OM_EMU_DIR, 'emu/src/machine.mjs'))) {
  console.error(`no om-emu working tree at ${OM_EMU_DIR}: run tools/emu/setup.sh (or set OM_EMU_DIR)`);
  process.exit(3);
}

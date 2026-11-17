// Paths of the emulator. The emulator itself is the om-emu fork in the submodule third_party/om-emu (its boot lab,
// emu/src/boot/, runs the E-PM2); the files of this folder only adapt it to the scripts of this repository.
//   EPM2_REPO    the repository root (default: two folders above tools/emu/e101/)
//   OM_EMU_DIR   the om-emu checkout (default: REPO/third_party/om-emu; tools/emu/setup.sh initialises it)
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

export const REPO = process.env.EPM2_REPO || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
export const OM_EMU_DIR = process.env.OM_EMU_DIR || path.join(REPO, 'third_party/om-emu');
if (!fs.existsSync(path.join(OM_EMU_DIR, 'emu/src/boot/e101.mjs'))) {
  console.error(`no om-emu with the boot lab at ${OM_EMU_DIR}: run tools/emu/setup.sh (or set OM_EMU_DIR)`);
  process.exit(3);
}

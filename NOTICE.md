# What the licence covers

The [MIT licence](LICENSE) covers what the authors of this repository wrote: the tools, the
scripts, the documentation and the lab notes. Some material here comes from, or is derived from,
other people's work. That material keeps its own terms.

## Not covered by the MIT licence

| Material | Where | Terms |
|---|---|---|
| **Olympus firmware.** No firmware image is in this repository. The patch specs hold short runs of original bytes (the `expect` fields, which the build tool checks before it writes, and one 512-byte tone table that is copied to other addresses). The firmware map and the function tables describe the firmware and quote names and strings from it. | `data/specs/`, `docs/reference/firmware-map.md`, `experiments/2026-11-08-feature-map/` | Copyright Olympus / OM Digital Solutions. Included only as far as needed to identify and modify a firmware file that you supply yourself. This project is not affiliated with them. |
| **Camera screens.** Screenshots of the camera's menus and displays, drawn by the firmware in an emulator. | `docs/images/ui/`, the guides in `docs/` | The interface shown (fonts, icons, texts, layout) is Olympus / OM Digital Solutions's. Shown only to explain how to use this mod. |
| **Film look data.** The matrices, curves and other values of the seven film looks were fitted to reproduce the output of spektrafilm film simulations. | `data/films/fits/`, `data/specs/seven-films-*.json`, `data/specs/films12-looks.json`, `data/specs/films12bw-doublex*.json`, the film specs in `data/specs/`, `experiments/2026-11-09-film-portra/slots/seven_films_*.json` | Derived from spektrafilm by Andrea Volpato, https://github.com/andreavolpato/spektrafilm. Licensed CC BY-SA 4.0 (https://github.com/andreavolpato/spektrafilm/blob/main/SPEKTRAFILM_LICENSE.txt). Modified by the authors of this repository: fitted to the adjustable stages of the Olympus E-PM2. The black-and-white look Double-X (`data/films/fits/doublex.npz` and its second fit `doublex2.npz`, `data/specs/films12bw-doublex.json`, `data/specs/films12bw-doublex2.json`) is fitted the same way from the profiles `kodak_doublex` (Kodak Double-X 5222 negative) and `kodak_2302` (Kodak 2302 print film) of spektrafilm's `dev` branch, commit `6cd00c8d4f30b5b550f50f4bbd3753c9f2a48507`, which carries the same licence file (CC BY-SA 4.0); modified: reduced to a grey mix and one tone curve for this camera. The black-and-white look Tri-X (`data/films/fits/trix.npz`) is fitted the same way from the profile `kodak_trix` (Kodak Tri-X Reversal Film 7266) of the same `dev` commit, rendered as a reversal film without a print. |
| **om-emu**, an emulator for Olympus and OM System firmware. It is a git submodule: our fork of it, branch `e101`, which adds the E-PM2 (model E101): its model entry, the boot lab that runs its firmware from the reset vector (`emu/src/boot/`, `emu/bin/boot.mjs`, `emu/host/boot.mjs`), its tests and documents, and small changes to the second core and the interrupt controller. This repository holds only the link. | `emulator/om-emu` | Upstream https://github.com/flatpanda/om-emu, MIT License, Copyright (c) 2026 om-emu contributors; the fork https://github.com/cfu288/om-emu, whose added and changed lines are by the authors of this repository under the same MIT terms. The notice is `emulator/om-emu/LICENSE` and travels with every checkout of the submodule. Three files in it have other terms (its README, section Licence): two GPL-2.0-or-later files for QEMU and one file with the MT19937 notice. The fork does not change them. Our scripts in `emulator/e101/` and `emulator/boot/` are our own code; they import om-emu and contain none of it. |
| **Synthetic test RAW files.** The raw data is ours. The file header (EXIF and maker notes) has the camera's own layout and contents. | `experiments/2026-11-09-film-portra/testraw/*.ORF` | Raw data: MIT. Header format and contents: the camera maker's. |
| **Photographs** in the comparison sheet. | `docs/images/film-sim-comparison.jpg`, `docs/dev/film-sim-comparison.pdf` | Copyright the repository author. You may redistribute them unchanged with this repository. |

## Credits for code written here

- **dcraw** by Dave Coffin. `experiments/2026-11-09-film-portra/orfcodec.py` is a Python port of the
  Olympus raw decoder `olympus_load_raw`, with a matching encoder written here. dcraw's notice says
  that all code except its Foveon functions "remains free for all uses".
- **GRKit** by ahonn, https://github.com/ahonn/GRKit (MIT). The fit's sample set and weights follow
  GRKit's (gray 150, chart 20, skin 60, random natural colours 1), re-implemented in Python.
- **spektrafilm** (GPL-3.0) is called as an installed program to make target LUTs
  (`bake_slide.py`, `spektrafilm-lut`). None of its code is in this repository. The LUTs it makes
  are not in the repository either.

## Included tool

`third_party/ste100/ste_lint.py` is the linter of https://github.com/danyuchn/asd-ste100-skill by
Dustin Yuchen Teng, MIT licence (`third_party/ste100/LICENSE`). It checks the documents.

## Tools you install yourself

GNU binutils for MN10300 (the submodule `third_party/binutils-gdb`, release 2.43.1, GPL-3.0-or-later; `tools/setup.sh` builds it into `build/toolchain/`, and none of its code is copied into this repository's files), Node.js
(version 26 or newer, for om-emu), ExifTool, and the Python packages numpy, scipy, numba, Pillow and rawpy.

# What the licence covers, and what it does not

The [MIT licence](LICENSE) covers what the authors of this repository wrote: the tools, the
scripts, the documentation and the lab notes. Some material here comes from, or is derived from,
other people's work. That material keeps its own terms.

## Not covered by the MIT licence

| Material | Where | Terms |
|---|---|---|
| **Olympus firmware.** No firmware image is in this repository. The patch specs hold short runs of original bytes (the `expect` fields, which the build tool checks before it writes, and one 512-byte tone table that is copied to other addresses). The firmware map and the function tables describe the firmware and quote names and strings from it. | `patches/`, `docs/firmware-map.md`, `experiments/2026-11-08-feature-map/` | Copyright Olympus / OM Digital Solutions. Included only as far as needed to identify and modify a firmware file that you supply yourself. This project is not affiliated with them. |
| **Film look data.** The matrices, curves and other values of the seven film looks were fitted to reproduce the output of spektrafilm film simulations. | `patches/seven-films-*.json`, the film specs in `patches/history/`, `experiments/2026-11-09-film-portra/slots/seven_films_*.json` | Derived from spektrafilm by Andrea Volpato, https://github.com/andreavolpato/spektrafilm. Licensed CC BY-SA 4.0 (https://github.com/andreavolpato/spektrafilm/blob/main/SPEKTRAFILM_LICENSE.txt). Modified by the authors of this repository: fitted to the adjustable stages of the Olympus E-PM2. |
| **Patch against om-emu.** The context lines of the patch are from om-emu, which has no licence file. The added lines are ours. | `tools/emu/om-emu-E101.patch`, `experiments/2026-11-12-om-emu-port/om-emu-changes.diff` | om-emu: https://github.com/flatpanda/om-emu, copyright its author. Get om-emu from its own repository; it is not included here. |
| **Synthetic test RAW files.** The raw data is ours. The file header (EXIF and maker notes) has the camera's own layout and contents. | `experiments/2026-11-09-film-portra/testraw/*.ORF` | Raw data: MIT. Header format and contents: the camera maker's. |
| **Photographs** in the comparison sheet. | `docs/images/film-sim-comparison.jpg`, `docs/film-sim-comparison.pdf` | Copyright the repository author. You may redistribute them unchanged with this repository. |

## Credits (compatible terms, code written here)

- **dcraw** by Dave Coffin. `experiments/2026-11-09-film-portra/orfcodec.py` is a Python port of the
  Olympus raw decoder `olympus_load_raw`, with a matching encoder written here. dcraw's notice says
  that all code except its Foveon functions "remains free for all uses".
- **GRKit** by ahonn, https://github.com/ahonn/GRKit (MIT). The fit's sample set and weights follow
  GRKit's (gray 150, chart 20, skin 60, random natural colours 1), re-implemented in Python.
- **spektrafilm** (GPL-3.0) is called as an installed program to make target LUTs
  (`bake_slide.py`, `spektrafilm-lut`). None of its code is in this repository. The LUTs it makes
  are not in the repository either.

## Tools you install yourself (not included)

GNU binutils for MN10300 (`scripts/build-binutils-mn10300.sh` downloads and builds it), om-emu,
Node.js, ExifTool, and the Python packages numpy, scipy, numba, Pillow and rawpy.

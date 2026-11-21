# Generators

Scripts whose output ships: each writes patch specs into `data/specs/` from committed inputs (Olympus's firmware, the
`.s` sources here, the package). CI runs `gen/run.sh --check`, which fails when a committed spec is not what its
generator makes. A generator makes only the current version of its specs; a version that a build has been camera-tested with stays as a committed file under a new name for the next version.

| Folder | Writes | Notes |
|---|---|---|
| `lss-core/` | `data/specs/lss-core.json` | Lowest S/S Setting, exposure part: `lss.s` (MN103) assembled into the exp debug printers. `experiments/2026-11-17-auto-iso-min-shutter/NOTES.md` section 12 |
| `build-label/` | `data/specs/build-label.json` | The Firmware screen's label, with the placeholder date that `epm2mod make` replaces. `experiments/2026-11-19-build-label/NOTES.md` |
| `stock-films/` | `data/specs/stock-films-structure-3.json`, `data/specs/looks-menu-4.json`, `data/specs/card-looks-7.json` | Film simulations on the stock art filters: `structure.py` first (it writes `build/stock-films/layout.json`), then `loader.py`. Version 3 of the structure and 7 of the loader give the film codes no 12-region table (`experiments/2026-11-20-model-calibration/NOTES.md` §6). The earlier versions (`stock-films-structure.json`, `-2`, `card-looks-5.json`, `-6`) are committed spec files that a camera-tested build names; these scripts made them at earlier commits and no longer do. `mkspec_looks.py`, `mkspec_looks3.py` and `mkspec_slots.py` are copies of `experiments/2026-11-17-card-looks/scripts/` that the loader imports. `experiments/2026-11-18-stock-filters/design.md` |
| `interval/` | `data/specs/interval-timelapse-v2.json`, `data/specs/interval-frames-240.json` | Interval shooting: `mkspec_v2.py`, then `mkspec_frames240.py`. Both compare their tables with the E-PL6 firmware when its file is given or is at the default place; without it they skip the comparison. `experiments/2026-11-13-intervalometer/README.md` |
| `level-gauge/` | `data/specs/level-gauge-lvinfo-row.json`, `data/specs/level-adjust-row.json` | The level gauge's two menu rows. `experiments/2026-11-14-level-gauge/NOTES.md` |
| `peaking/` | `data/specs/peaking-direct-4.json`, `data/specs/peaking-colours.json`, `data/specs/peaking-fast.json`, `data/specs/peaking-save-guard.json` | Focus peaking, in that order: each of the last three reads the pinned build's specs before it. `experiments/2026-11-14-focus-peaking/NOTES.md` |
| `log-menu/` | `data/specs/log-menu-2.json` | The Debug Log row and the log's code. Its `BUILD_ID` names the event list `data/logdict/events-33ca8d15f4f1c877.json`. `experiments/2026-11-18-log-menu/` |
| `lss-menu/` | `data/specs/custom-menu-rows-3.json`, `data/specs/lss-menu.json` | The Custom Menu table with the four added rows, and the Lowest S/S Setting row's list and texts. `experiments/2026-11-17-auto-iso-min-shutter/NOTES.md` section 11 |
| `gauge-info/` | `data/specs/gauge-info.json`, `data/specs/gauge-bar-left-2.json` | Shooting information on the level gauge screen. `experiments/2026-11-19-gauge-info/NOTES.md` |

Run them all: `gen/run.sh`. It needs the MN103 binutils (`tools/setup.sh --binutils`) and Olympus's firmware
(`uv run epm2mod fetch-stock`).

`data/specs/peaking-gain-2x.json` is one byte written by hand. Every other spec that no folder here writes was made by an experiment script; its notes in `experiments/` are the record.

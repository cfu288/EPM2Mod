# Generators

Scripts whose output ships: each writes patch specs into `data/specs/` from committed inputs (Olympus's firmware, the
`.s` sources here, the package). CI runs `gen/run.sh --check`, which fails when a committed spec is not what its
generator makes. A generator makes only the current version of its specs; a version that a build has been camera-tested with stays as a committed file under a new name for the next version.

| Folder | Writes | Notes |
|---|---|---|
| `lss-core/` | `data/specs/lss-core.json` | Lowest S/S Setting, exposure part: `lss.s` (MN103) assembled into the exp debug printers. `experiments/2026-11-17-auto-iso-min-shutter/NOTES.md` section 12 |
| `build-label/` | `data/specs/build-label.json` | The Firmware screen's label, with the placeholder date that `epm2mod make` replaces. `experiments/2026-11-19-build-label/NOTES.md` |
| `stock-films/` | `data/specs/stock-films-structure-3.json`, `data/specs/looks-menu-4.json`, `data/specs/card-looks-8.json` | Film simulations on the stock art filters: `structure.py` first (it writes `build/stock-films/layout.json`), then `loader.py`. Version 3 of the structure gives the film codes no 12-region table (`experiments/2026-11-20-model-calibration/NOTES.md` §6). Version 8 of the loader applies the stored file from the last entry of segment 3's constructor table, and its text table also holds the texts of the rows Peaking and Lowest S/S Setting (`experiments/2026-11-21-firmware-dive/plan.md`); its spec's key `_symbols` gives the labels that `log-menu/` hooks. The earlier versions (`stock-films-structure.json`, `-2`, `card-looks-5.json`, `-6`, `-7`) are committed spec files that a camera-tested build names; these scripts made them at earlier commits and no longer do. `loader.s` is the loader's assembly; `loader.py` fills its fields and assembles it. `experiments/2026-11-18-stock-filters/design.md` |
| `interval/` | `data/specs/interval-timelapse-v2.json`, `data/specs/interval-frames-240.json` | Interval shooting: `mkspec_v2.py`, then `mkspec_frames240.py`. Both compare their tables with the E-PL6 firmware when its file is given or is at the default place; without it they skip the comparison. `experiments/2026-11-13-intervalometer/README.md` |
| `level-gauge/` | `data/specs/level-gauge-lvinfo-row.json`, `data/specs/level-adjust-row.json` | The level gauge's two menu rows. `experiments/2026-11-14-level-gauge/NOTES.md` |
| `peaking/` | `data/specs/peaking-direct-4.json`, `data/specs/peaking-colours.json`, `data/specs/peaking-fast.json`, `data/specs/peaking-save-guard.json` | Focus peaking, in that order: each of the last three reads the pinned build's specs before it. `experiments/2026-11-14-focus-peaking/NOTES.md` |
| `log-menu/` | `data/specs/log-menu-3.json` | The Debug Log row and the log's code, for `data/builds/films-start-texts.json`. It runs last: it reads the film loader's labels from `_symbols` of the build's `card-looks` spec, and the bytes it hooks from the build's other specs. Its `BUILD_ID` names the event list of `data/logdict/events.json` (`afe27672d672fc95`). The earlier version `log-menu-2.json` is a committed spec file that a camera-tested build names; this script made it at an earlier commit and no longer does. `experiments/2026-11-18-log-menu/` |
| `lss-menu/` | `data/specs/custom-menu-rows-3.json`, `data/specs/lss-menu.json` | The Custom Menu table with the four added rows, and the Lowest S/S Setting row's list and texts. `experiments/2026-11-17-auto-iso-min-shutter/NOTES.md` section 11 |
| `gauge-info/` | `data/specs/gauge-info.json`, `data/specs/gauge-bar-left-2.json` | Shooting information on the level gauge screen. `experiments/2026-11-19-gauge-info/NOTES.md` |

Run them all: `gen/run.sh`. It needs the MN103 binutils (`tools/setup.sh --binutils`) and Olympus's firmware
(`uv run epm2mod fetch-stock`).

`data/specs/peaking-gain-2x.json` is one byte written by hand. Every other spec that no folder here writes was made by an experiment script; its notes in `experiments/` are the record.

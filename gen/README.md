# Generators

Scripts whose output ships: each writes patch specs into `data/specs/` from committed inputs (Olympus's firmware, the
`.s` sources here, the package). CI runs `gen/run.sh --check`, which fails when a committed spec is not what its
generator makes.

| Folder | Writes | Notes |
|---|---|---|
| `lss-core/` | `data/specs/lss-core.json` | Lowest S/S Setting, exposure part: `lss.s` (MN103) assembled into the exp debug printers. `experiments/2026-11-17-auto-iso-min-shutter/NOTES.md` section 12 |
| `build-label/` | `data/specs/build-label.json` | The Firmware screen's label, with the placeholder date that `epm2mod make` replaces. `experiments/2026-11-19-build-label/NOTES.md` |
| `stock-films/` | `data/specs/stock-films-structure.json`, `data/specs/looks-menu-4.json`, `data/specs/card-looks-5.json`; with `--v2`: `data/specs/stock-films-structure-2.json`, `data/specs/card-looks-6.json` | Film looks on the stock art filters: `structure.py` first (it writes `build/stock-films/layout.json`, with `--v2` `build/stock-films-2/layout.json`), then `loader.py`. Version 2 adds the identity look stub and the ArtFilter Off and film name in EXIF (`experiments/2026-11-20-film-name-exif/NOTES.md`). `mkspec_looks.py`, `mkspec_looks3.py` and `mkspec_slots.py` are copies of `experiments/2026-11-17-card-looks/scripts/` that the loader imports. `experiments/2026-11-18-stock-filters/design.md` |

Run them all: `gen/run.sh`. It needs the MN103 binutils (`tools/setup.sh --binutils`) and Olympus's firmware
(`uv run epm2mod fetch-stock`).

The other shipped specs come from experiment scripts that do not run again as they are: they start from an
unpacked older build, or write to a fixed path. Their notes in `experiments/` are the record. The film-look specs come
from the package (`uv run epm2mod generate`).

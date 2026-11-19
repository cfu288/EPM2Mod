# Moved paths

Dated notes (`experiments/`, the camera log) keep the paths of their time. This table gives the new place of each
path that moved. A folder row covers every file in it.

| Old path | New path | Since |
|---|---|---|
| `patches/history/NAME.json` | `data/specs/NAME.json`, marked `history` in `tools/space-ledger/superseded.tsv` | 2026-11-19 |
| `patches/history/README.md` | `data/specs/HISTORY.md` | 2026-11-19 |
| `raws/`, `references/` | `.local/raws/`, `.local/references/` (not in git) | 2026-11-19 |
| `tools/doclint.py` | `.githooks/doclint.py` | 2026-11-19 |
| `tools/doc_links.py` | `.claude/hooks/doc_links.py` | 2026-11-19 |
| `tools/doc_links.json` | `docs/links.json` | 2026-11-19 |
| `tools/third_party/ste100/` | `third_party/ste100/` | 2026-11-19 |
| `experiments/2026-11-17-auto-iso-min-shutter/scripts/mkspec_lss_core.py`, `scripts/lss.s` | `gen/lss-core/mkspec.py`, `gen/lss-core/lss.s` | 2026-11-19 |
| `experiments/2026-11-19-build-label/scripts/mkspec_label.py` | `gen/build-label/mkspec.py` | 2026-11-19 |
| `experiments/2026-11-18-stock-filters/scripts/mkspec_structure.py`, `scripts/mkspec_loader.py` | `gen/stock-films/structure.py`, `gen/stock-films/loader.py` | 2026-11-19 |
| `tools/build.py`, `tools/make_firmware.py`, `tools/fetch_stock.py` | removed: `uv run epm2mod make`, `uv run epm2mod fetch-stock` | 2026-11-19 |
| `tools/emu/` | `emulator/` | 2026-11-19 |
| `third_party/om-emu/` | `emulator/om-emu/` | 2026-11-19 |
| `docs/camera-log.md` | `docs/camera-log/`, one file per flash | 2026-11-19 |
| `docs/install.md`, `docs/flashing.md`, `docs/debug-log.md` | `docs/user/` | 2026-11-19 |
| `docs/cli.md`, `docs/look-file-format.md`, `docs/firmware-format.md`, `docs/firmware-map.md`, `docs/logging.md`, `docs/model-matrix.md`, `docs/code-space-map.md`, `docs/code-space-map.tsv`, `docs/memory-map.svg` | `docs/reference/` | 2026-11-19 |
| `docs/conventions.md`, `docs/feasibility.md`, `docs/verification.md`, `docs/art-filter-slots.md`, `docs/art-slots-evaluation.md`, `docs/film-emulation.md`, `docs/film-sim-comparison.pdf` | `docs/dev/` | 2026-11-19 |
| `docs/todo.md` | `TODO.md` | 2026-11-19 |
| `docs/space-candidates.tsv`, `docs/space-bounds.tsv`, `docs/space-pointer-waivers.tsv`, `docs/space-superseded.tsv` | `tools/space-ledger/candidates.tsv`, `bounds.tsv`, `pointer-waivers.tsv`, `superseded.tsv` | 2026-11-19 |
| `patches/` | `data/specs/` | 2026-11-19 |
| `builds/` | `data/builds/` | 2026-11-19 |
| `pinned-build.json` | `data/pinned-build.json` | 2026-11-19 |
| `looks/` | `data/films/` | 2026-11-19 |
| `logs/` | `data/logdict/` | 2026-11-19 |

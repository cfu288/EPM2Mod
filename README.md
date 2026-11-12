# epm2-tools

Film looks (seven films as art-filter menu entries: Portra 400, Ektachrome 100, Pro 400H, Kodachrome 64, Vision3 250D, Velvia 100, Superia 400): plain-language summary in [docs/film-emulation.md](docs/film-emulation.md); which other filters can become film slots: [docs/art-slots-evaluation.md](docs/art-slots-evaluation.md).

Custom firmware tooling for the Olympus PEN **E-PM2** (model 1010, TruePic VI, body firmware 1.6).

**Status (2026-11-08):** modified firmware flashes and runs on a real E-PM2 via the SD-card updater. See [docs/camera-log.md](docs/camera-log.md).

## Quick start

```bash
python3 tools/build.py patches/pixel-hacking.json      # -> build/pixel-hacking.BIN
python3 -m unittest discover -s tests                   # round-trip + reproducible builds
```

Flash `build/<name>.BIN` as `DCOLYMP/E1019999.BIN`, hold OK and power on. Full steps: [docs/flashing.md](docs/flashing.md).

## Layout

| Path | What |
|---|---|
| `tools/oetool.py` | OE container: `info`, `unpack`, `pack`, `patch` (recomputes checksums) |
| `tools/build.py` | applies JSON patch specs to a stock BIN → `build/` |
| `tools/disasm.py`, `tools/fwmap.py` | MN103 disassembly (GNU objdump, `scripts/build-binutils-mn10300.sh`) and the block-0 function database with `fn`/`str`/`range`/`xref`/`tasks` queries |
| `patches/` | one spec per mod, with a status and expected hash once camera-tested; `patches/history/` holds superseded and failed specs (record only) |
| `firmware/` | stock and reference BINs (git-ignored), `SHA256SUMS`, provenance |
| `docs/` | [firmware map](docs/firmware-map.md) (what the firmware contains and where), [flashing](docs/flashing.md), [camera log](docs/camera-log.md), [format](docs/firmware-format.md), [verification](docs/verification.md), [conventions](docs/conventions.md) |
| `experiments/` | dated ad-hoc work; promote results into tools/patches/docs |
| `tests/` | unittest suite |

## Patches

Current film build (`seven-films-5`, camera-tested 2026-11-12): `remap7b-code` + `seven-fixes-1` + `seven-structure-extra` + `seven-films-5` + `xp-adaptive-hue-off` + `seven-labels`. Every other film spec in the table below is in `patches/history/`.

| Spec | Status |
|---|---|
| `pixel-hacking` | camera-tested, works (PoC: renames a menu label) |
| `curve-probe-2` | built, **not camera-tested** (Cross Process I := Natural + Saturation +2; verifies the per-channel base-gamma tables, NOTES §14.3) |
| `film-portra-xp` (+ `label-portra`) | **camera-tested 2026-11-11, works** as `build/film-portra-xp-labelled.BIN` (Portra 400 in the Cross Process I slot; NOTES §14.4, §15) |
| `film-portra-xp2` (+ `label-portra`) | built, **not camera-tested** (as above plus a fitted luma look curve; NOTES §16.3) |
| `film-portra-xp` + `label-portra` | camera-tested 2026-11-11, works (first Portra build) |
| + `sixaxis-probe-1` / `sixaxis-portra-1` (xp3) | camera-tested 2026-11-11, work (see docs/camera-log.md) |
| `sixaxis-portra-2` (xp4), `sixaxis-portra-3` (xp5) | built, not camera-tested |
| `xp-adaptive-hue-off`, `film-portra-xp7` (xp6 / xp7 builds) | xp7 flashed OK 2026-11-12; first patches that change code bytes (NOTES §22–23) |
| `film-portra-xp8` | flashed OK 2026-11-12; measured with the synthetic test RAW (NOTES §23–25) |
| `film-portra-xp9` | flashed OK 2026-11-12; mock natural colours ΔE 1.31 vs target, as predicted (NOTES §25) |
| `film-ektachrome-pa2` | built, **not camera-tested**; Ektachrome 100 in the Pop Art II slot, data only (NOTES §26) |
| `film-ektachrome-lt`, `label-ektachrome-lt` | flashed OK 2026-11-12; Ektachrome 100 in the Light Tone slot, ΔE 1.55 on mock natural colours (NOTES §26.5–26.6; slot map in `docs/art-filter-slots.md`) |
| `film-ektachrome-lt2` | flashed OK 2026-11-12; ΔE 1.39 on mock natural colours, as predicted (NOTES §26.6) |
| `film-portra-xp10`, `film-ektachrome-lt3` | flashed OK 2026-11-12 (current build); refits against the measured fit objective; scene-independence confirmed with the blue-scene test RAW (NOTES §27–28) |
| `slot3-code`, `film-pro400h-pa1`, `label-pro400h-pa` (+ `…-s3` copies of the two film patches) | flashed OK 2026-11-12 (`three-films-1`): **first new code, works**; third film (Fuji Pro 400H) in the Pop Art entry, look distorted by Pop Art's chroma curves (NOTES §29–30) |
| `slot3-chroma-linear` | flashed OK 2026-11-12 (`three-films-2`, current build): Pro 400H natural colours ΔE 1.20 (NOTES §30.4) |
| `film-pro400h-pa2` | built, **not camera-tested** (`three-films-3`): correction refit of Pro 400H (NOTES §30.4) |
| `slots7-code`, `slots7-neutral` | built, **not camera-tested** (`seven-slots-neutral`): Pale&Light, Soft Focus, Pin Hole and Diorama as film slots with a neutral test look; emulator-checked (docs/art-slots-evaluation.md, NOTES §32) |
| `slots12-code`, `slots12-neutral`, `film-pro400h-pa2-s12` | built, **do not flash** (uses effect numbers 106 / 108; NOTES §35) (`twelve-slots-neutral`): all twelve visible filters as film slots; the five effect filters use the numbers of hidden second types; emulator-checked (docs/art-slots-evaluation.md §4, NOTES §33) |
| `slots7-kind` | flashed 2026-11-12 with slots7-code (`seven-slots-neutral-b`): **live view freezes** in Soft Focus, Pin Hole, Diorama (NOTES §34–35) |
| `remap7-code`, `remap7-neutral` | flashed 2026-11-12 (`seven-slots-remap-neutral`): **live view freezes** in Soft Focus, Pin Hole, Diorama (NOTES §35–36) |
| `four-code`, `four-neutral` | built, **not camera-tested** (`four-slots-neutral`): the three films + Pale&Light as a fourth slot; no effect filter touched (NOTES §36) |
| `remap7b-code` | flashed OK 2026-11-12 (`seven-slots-remap2-neutral`, current build): **live view no longer freezes** in the three remapped entries (NOTES §37) |
| `seven-structure-extra`, `seven-films-1`, `seven-labels` | **camera-tested** (`seven-films-1`, 2026-11-12; `seven-films-2`, corrected fits for the four new films, camera-tested the same day; open: rare restart when RAW Data Edit saves, see camera log): seven films in menu order: Portra 400, Ektachrome 100, Pro 400H, Kodachrome 64, Vision3 250D, Velvia 100, Superia X-tra 400 (NOTES §39) |
| `curve-probe-1`, `film-portra` | superseded drafts, not camera-tested (NOTES §12.5, §13) |

## Background

Landscape research: `../reports/Olympus firmware modding landscape.md` and `../research_notes/Olympus firmware modding landscape/`.

Commits follow Conventional Commits. Run `git config core.hooksPath .githooks` once. See [docs/conventions.md](docs/conventions.md).

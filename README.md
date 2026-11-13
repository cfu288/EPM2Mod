# epm2-tools

Custom firmware tooling for the Olympus PEN **E-PM2** (model 1010, TruePic VI, body firmware 1.6), and
a firmware mod built with it: **seven film looks as in-camera art filters**.

![Six photos, each developed in the camera with stock Natural and the seven film looks](docs/images/film-sim-comparison.jpg)

Each row is one RAW file developed in the camera; the first column is the stock Natural mode.
Full-resolution sheet: [docs/film-sim-comparison.pdf](docs/film-sim-comparison.pdf).

## Film looks

Seven of the twelve art-filter menu entries are replaced by film looks. They work for stills and
live view, straight out of the camera as JPEG.

| Menu name | Film | Replaces |
|---|---|---|
| Portra | Kodak Portra 400 (on Portra Endura paper) | Pop Art |
| Ektachrome | Kodak Ektachrome 100 (slide) | Soft Focus |
| Pro 400H | Fuji Pro 400H (on Crystal Archive paper) | Pale&Light Color |
| Kodachrome | Kodak Kodachrome 64 (slide) | Light Tone |
| Vis 250D | Kodak Vision3 250D (on 2383 print film) | Pin Hole |
| Velvia | Fuji Velvia 100 (slide) | Diorama |
| Superia 400 | Fuji Superia X-tra 400 (on Crystal Archive paper) | Cross Process |

Grainy Film, Gentle Sepia, Dramatic Tone, Key Line and Watercolor are unchanged. Colour and tone only:
no grain, no halation. The looks are fitted to [spektrafilm](https://github.com/andreavolpato/spektrafilm)
simulations of each film and measured on the camera with a synthetic test RAW; average colour error is
about 1.1 to 1.5 ΔE2000 on natural colours (stock Natural against the same targets: 4 to 6).
How it works, how it was measured and what the limits are: **[docs/film-emulation.md](docs/film-emulation.md)**.

## Latest known-good build

**`seven-films-5`**, flashed and measured on a real E-PM2 on 2026-11-12 ([camera log](docs/camera-log.md)).

No firmware is distributed here. You build the image from Olympus's own v1.6 firmware file plus the
patch specs in this repository:

```bash
# 1. put the stock E-PM2 v1.6 firmware at firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN
#    sha256 34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300   (sources: firmware/README.md)
# 2. build
python3 tools/build.py patches/remap7b-code.json patches/seven-fixes-1.json \
    patches/seven-structure-extra.json patches/seven-films-5.json \
    patches/xp-adaptive-hue-off.json patches/seven-labels.json -o build/seven-films-5.BIN
# 3. check: sha256 of build/seven-films-5.BIN must be
#    0443a38804061afaf17a12906a6969101d9f54ffe006e0aeca0d21d68f9b29ae
```

Flash it as `DCOLYMP/E1019999.BIN` on the SD card, hold OK and power on. Full steps, and how to go back
to stock: [docs/flashing.md](docs/flashing.md).

Known issues in this build:

- In **movie mode** the display freezes while Ektachrome, Vis 250D or Velvia is selected (leaving the entry
  un-freezes it). Fixed in `seven-films-6` (the same list with `patches/seven-movie-1.json` after
  `seven-fixes-1`), which is built but **not yet camera-tested**.
- Movies get only part of each look. The second type (II) of Portra, Pro 400H and Superia is the same as type I.

**At your own risk.** This is unofficial, for the E-PM2 with body firmware 1.6 only, and not affiliated with
Olympus or OM Digital Solutions. A wrong or interrupted flash can leave a camera unusable. The build tool
refuses any other base file; never put a firmware file for another model on the card.

## Tooling quick start

```bash
python3 tools/build.py patches/pixel-hacking.json      # -> build/pixel-hacking.BIN (proof of concept: renames one menu label)
python3 -m unittest discover -s tests                   # round-trip + reproducible builds
```

Modified firmware has flashed and run on a real E-PM2 through the SD-card updater since 2026-11-08; every
flash is in [docs/camera-log.md](docs/camera-log.md).

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

The current film build is described under *Latest known-good build* above. Every other film spec in the table below is in `patches/history/`; the table is the development history.

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

Commits follow Conventional Commits. Run `git config core.hooksPath .githooks` once: it enables the commit-message check and a check that refuses machine-specific paths and host names (use `/path/to/...`, `USER@HOST`). See [docs/conventions.md](docs/conventions.md).

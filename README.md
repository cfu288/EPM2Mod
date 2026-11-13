# EPM2Mod

![Olympus PEN E-PM2](docs/images/epm2.jpg)

Repository containing the current work for creating a custom firmware mod for the Olympus PEN **E-PM2**. The goal is to unlock or add new features to this camera. Currently, we've implemented replacing the default art filters with film simulations like Portra, Ektachrome, etc., and enabled interval shooting (up to 99 shots), a feature of the E-PL6.

| Feature | What you get | Status |
|---|---|---|
| **Film looks** | Seven film emulations as art filters, for stills and live view | Tested on the camera |
| **Interval shooting** | The Time Lapse Settings menu of the E-PL6: 1 to 99 frames, start delay, interval, optional time-lapse movie | Interval shooting tested on the camera. The time-lapse movie and long intervals are not yet reported |
| Video quality and recording limit | Research and patch specs | Not built. See `experiments/2026-11-12-hardware/` |

See below for an example of the film looks:

![Eight photos, each developed in the camera with stock Natural and the seven film looks](docs/images/film-sim-comparison.jpg)

Each row shows one RAW file. The camera developed the file with each look. The first column shows the standard Natural mode.
Full-resolution sheet: [docs/film-sim-comparison.pdf](docs/film-sim-comparison.pdf).

## Film looks

Seven of the twelve art-filter menu entries are replaced by film looks. They work for stills and
live view, straight out of the camera as JPEG.

<!-- BEGIN GENERATED: films -->
| Menu name | Film | Replaces |
|---|---|---|
| Portra | Kodak Portra 400 (negative, on Kodak Portra Endura paper) | Pop Art |
| Ektachrome | Kodak Ektachrome 100 (slide) | Soft Focus |
| Pro 400H | Fuji Pro 400H (negative, on Fuji Crystal Archive paper) | Pale&Light Color |
| Kodachrome | Kodak Kodachrome 64 (slide) | Light Tone |
| Vis 250D | Kodak Vision3 250D (cinema negative, on Kodak 2383 print film) | Pin Hole |
| Velvia | Fuji Velvia 100 (slide) | Diorama |
| Superia 400 | Fuji Superia X-tra 400 (negative, on Fuji Crystal Archive paper) | Cross Process |
<!-- END GENERATED: films -->

Grainy Film, Gentle Sepia, Dramatic Tone, Key Line and Watercolor are unchanged. Colour and tone only:
no grain, no halation. The looks are fitted to [spektrafilm](https://github.com/andreavolpato/spektrafilm)
simulations of each film and measured on the camera with a synthetic test RAW; average colour error is
about 1.1 to 1.5 ΔE2000 on natural colours (stock Natural against the same targets: 4 to 6).
How it works, how it was measured and what the limits are: **[docs/film-emulation.md](docs/film-emulation.md)**.

## Interval shooting

The E-PM2 firmware contains the interval-shooting code of its sister model, the E-PL6, but no menu
entry for it. The mod adds the entry: **Shooting Menu 2 → Time Lapse Settings**. Set the number of
frames, the start waiting time, the interval time (1 second or more), and if the camera makes a
time-lapse movie when the sequence is complete. The camera stays awake during a sequence.

The frame count goes from 1 to 99 in steps of 1, then from 100 to 240 in steps of 5. The stock
E-PL6 stops at 99. The steps are there because the menu's value list holds 128 entries at most; the
firmware keeps the count in one byte. Each frame uses the mechanical shutter.

What was in the firmware, how the patch works, how it was checked and what is not yet tested:
[experiments/2026-11-13-intervalometer/README.md](experiments/2026-11-13-intervalometer/README.md).

## Install the latest tested firmware

<!-- BEGIN GENERATED: pinned-build -->
The pinned build is **`seven-films-6-interval-240`**: seven film looks as art filters, and interval shooting with up to 240 frames. We tested this build on a real E-PM2 on 2026-11-13 ([camera log](docs/camera-log.md)).

| | sha256 |
|---|---|
| Stock firmware, `OLY_E_101_1600_0000_0000.BIN` | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` |
| Pinned build, `seven-films-6-interval-240` | `01837f962f8a8ca0d189d9cd65ad9b5b35402ca3f3ed54a3872af044e050de11` |
<!-- END GENERATED: pinned-build -->

This repository does not contain firmware. The firmware is the maker's copyrighted software. One
command downloads the maker's v1.6 firmware, applies the patches of this repository, and makes sure
that the result is the tested build.

**You need:**

- a computer with [uv](https://docs.astral.sh/uv/getting-started/installation/). uv gets the correct
  Python for you.
- an SD card
- a fully charged battery
- an E-PM2 with body firmware 1.6. To see the version, open Setup menu → Firmware.

**Steps:**

1. Get this repository. On GitHub, click **Code → Download ZIP**, then unzip the file. As an
   alternative, use git:

   ```bash
   git clone https://github.com/cfu288/EPM2Mod.git
   cd EPM2Mod
   ```

2. Put the SD card in the computer.

3. Run this command. Give the location of the card after `--card`.

   ```bash
   uv run tools/make_firmware.py --card /Volumes/NAME
   ```

   On macOS the location is `/Volumes/NAME`. On Windows it is a drive letter, for example `E:\`. On
   Linux it is the mount point of the card.

   The script does five steps. If a step fails, the script stops and tells you the cause. It does
   not write an incorrect file.

   | Step | What the script does |
   |---|---|
   | 1 | It downloads the maker's firmware file (43 MB), if the file is not there. It makes sure that the file is correct. |
   | 2 | It makes sure that the patches do not use the same bytes. Only an untested build needs this step. |
   | 3 | It applies the patches. |
   | 4 | It makes sure that the result is the tested build. |
   | 5 | It writes the firmware to the card as `DCOLYMP/E1019999.BIN`. It reads the file again to make sure that the copy is correct. |

4. Eject the card. Put the card in the camera.

5. Make sure that the camera is off. Hold the **OK** button and push the **ON/OFF** button.

6. Wait. The lamp is orange for approximately one minute. Do not touch the camera during this time.
   When the lamp blinks, the update is complete.

7. Push the **ON/OFF** button to stop the camera. Push it again to start the camera.

8. Make sure that the update is correct. The art filter list shows Portra, Ektachrome, Pro 400H,
   Kodachrome, Vis 250D, Velvia and Superia 400. Shooting Menu 2 shows Time Lapse Settings.

### If you do not give `--card`

The script writes the firmware to `build/card/DCOLYMP/E1019999.BIN`. Copy the `DCOLYMP` folder to
the card. The firmware must be the only file in `DCOLYMP`.

### To go back to the original firmware

1. Run `uv run tools/fetch_stock.py`. This command downloads the maker's firmware file, or makes
   sure that the file you have is correct.
2. Copy `firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN` to the card as `DCOLYMP/E1019999.BIN`.
   It must be the only file in `DCOLYMP`.
3. Do steps 4 to 7.

More about the update procedure: [docs/flashing.md](docs/flashing.md).

### Limits of this build

- A movie gets only a part of each film look.
- Type II of Portra, Pro 400H and Superia is the same as type I.
- The film looks do not add grain or halation.
- Each interval frame uses the mechanical shutter.
- Not yet tested: a full sequence of 240 frames, the cancellation of a sequence, and intervals
  longer than 90 seconds.

### Warning

**Use this firmware at your own risk.** It is unofficial. It is for the E-PM2 with body firmware 1.6
only. Olympus and OM Digital Solutions have no part in it. An incorrect or interrupted update can
make a camera unusable. Do not put a firmware file for a different camera model on the card.

## Builds, for developers

Each firmware build has a description file in [`builds/`](builds/). The description names the patch
specs in order. After a camera test it also holds the sha256 of the result and the date.
[`pinned-build.json`](pinned-build.json) names the description of the last tested build. To make a
different build, give its description to the script:

```bash
uv run tools/make_firmware.py builds/seven-films-6.json
```

<!-- BEGIN GENERATED: builds -->
| Build | What | Patch specs | Camera-tested | sha256 |
|---|---|---|---|---|
| `seven-films-6-interval-240` (pinned) | Seven film looks as art filters, and interval shooting with up to 240 frames | 9 | 2026-11-13 | `01837f962f8a8ca0d189d9cd65ad9b5b35402ca3f3ed54a3872af044e050de11` |
| `seven-films-6` | Seven film looks as art filters | 7 | 2026-11-13 | `5badb0796731b40a27ef015e57da134d7d793486d4c6262a3f483c1aae60fd05` |
| `seven-films-6-interval` | Seven film looks as art filters, and interval shooting with up to 99 frames | 8 | 2026-11-13 | `f52ea6976ac2e9c567b2c07d7556b96b6431c8fcd2d90de195abdb76059e0104` |
<!-- END GENERATED: builds -->

The project makes its own firmware with the same script. The procedure for a new build is in
[docs/conventions.md](docs/conventions.md), section "Making firmware".

The scripts use only the Python standard library. If you have Python 3.10 or newer, you can use
`python3` in place of `uv run`.

To run the tests: `uv run python -m unittest discover -s tests`. Some tests need the maker's
firmware file.

## Layout

| Path | What |
|---|---|
| `src/epm2mod/` | the Python package that makes the firmware: container format, patch specs, stock download, build descriptions, the build steps, the film-spec generator. Typed, formatted with black, tested. Command: `uv run epm2mod --help` |
| `tools/make_firmware.py`, `tools/fetch_stock.py` | the package's two main commands as stand-alone scripts |
| `tools/oetool.py`, `tools/build.py` | older command-line forms, kept for the scripts that call them; they use the package |
| `builds/`, `pinned-build.json` | one description per firmware build; the pointer to the last camera-tested one |
| `looks/` | the film list and the fitted values that the film patch specs are generated from |
| `tools/disasm.py`, `tools/fwmap.py` | MN103 disassembly (GNU objdump, `scripts/build-binutils-mn10300.sh`) and the block-0 function database with `fn`/`str`/`range`/`xref`/`tasks` queries |
| `patches/` | one spec per mod, with a status and expected hash once camera-tested; `patches/history/` holds superseded and failed specs (record only) |
| `firmware/` | stock and reference BINs (git-ignored), `SHA256SUMS`, provenance |
| `docs/` | [firmware map](docs/firmware-map.md) (what the firmware contains and where), [flashing](docs/flashing.md), [camera log](docs/camera-log.md), [format](docs/firmware-format.md), [verification](docs/verification.md), [conventions](docs/conventions.md) |
| `experiments/` | dated ad-hoc work; promote results into tools/patches/docs |
| `tests/` | unittest suite |

## Patches

The current build is described under *Install the latest tested firmware* above. Every other film spec in the table below is in `patches/history/`; the table is the development history.

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

## Licence

Code, documentation and notes: [MIT](LICENSE). Some material keeps other terms: the film look data is
derived from [spektrafilm](https://github.com/andreavolpato/spektrafilm) by Andrea Volpato (CC BY-SA 4.0),
and excerpts of the Olympus firmware remain Olympus's. No firmware and no third-party tool is included.
Details and credits: [NOTICE.md](NOTICE.md).

## Background

Landscape research: `../reports/Olympus firmware modding landscape.md` and `../research_notes/Olympus firmware modding landscape/`.

Commits follow Conventional Commits. Run `git config core.hooksPath .githooks` once: it enables the commit-message check and a check that refuses machine-specific paths and host names (use `/path/to/...`, `USER@HOST`). See [docs/conventions.md](docs/conventions.md).

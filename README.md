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

Film looks replace seven of the twelve art filters. They work for still pictures and for live view.
The camera writes the look into the JPEG.

<!-- BEGIN GENERATED: films -->
| Menu name | Film | Replaces |
|---|---|---|
| Portra | Kodak Portra 400 (negative, on Kodak Portra Endura paper) | Pop Art |
| Ektachrome | Kodak Ektachrome 100 (slide) | Soft Focus |
| Pro 400H | Fuji Pro 400H (negative, on Fuji Crystal Archive paper) | Pale&amp;Light Color |
| Kodachrome | Kodak Kodachrome 64 (slide) | Light Tone |
| Vis 250D | Kodak Vision3 250D (cinema negative, on Kodak 2383 print film) | Pin Hole |
| Velvia | Fuji Velvia 100 (slide) | Diorama |
| Superia 400 | Fuji Superia X-tra 400 (negative, on Fuji Crystal Archive paper) | Cross Process |
<!-- END GENERATED: films -->

- Grainy Film, Gentle Sepia, Dramatic Tone, Key Line and Watercolor do not change.
- A film look changes colour and tone only. It does not add grain or halation.
- Each look is fitted to a [spektrafilm](https://github.com/andreavolpato/spektrafilm) simulation
  of the film.
- We measured each look on the camera with a synthetic test RAW file. The average colour error on
  natural colours is 1.1 to 1.5 ΔE2000. ΔE2000 is a standard measure of colour difference: 1 is
  about the smallest difference that you can see. The stock Natural mode is 4 to 6 from the same
  targets.

[docs/film-emulation.md](docs/film-emulation.md) tells you how the looks work, how we measured them
and what their limits are.

## Interval shooting

The E-PM2 firmware contains the interval-shooting code of the E-PL6, but no menu entry for it. The
mod adds the entry: **Shooting Menu 2 → Time Lapse Settings**. In this menu you set:

- the number of frames
- the waiting time before the first frame
- the interval between frames (1 second or more)
- whether the camera makes a time-lapse movie at the end of the sequence

The camera stays on during a sequence. Each frame uses the mechanical shutter.

The number of frames goes from 1 to 99 in steps of 1, then from 100 to 240 in steps of 5. The stock
E-PL6 stops at 99. The steps of 5 are necessary because the menu list can hold only 128 values.

[experiments/2026-11-13-intervalometer/README.md](experiments/2026-11-13-intervalometer/README.md)
tells you what was in the firmware, how the patch works, how we checked it and what is not yet
tested.

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

## For developers

Each firmware build has a description file in [`builds/`](builds/). The description names the patch
specs in order. After a camera test it also holds the sha256 of the result and the date of the test.
[`pinned-build.json`](pinned-build.json) names the description of the last tested build.

<!-- BEGIN GENERATED: builds -->
| Build | What | Patch specs | Camera-tested | sha256 |
|---|---|---|---|---|
| `seven-films-6-interval-240` (pinned) | Seven film looks as art filters, and interval shooting with up to 240 frames | 9 | 2026-11-13 | `01837f962f8a8ca0d189d9cd65ad9b5b35402ca3f3ed54a3872af044e050de11` |
| `seven-films-6` | Seven film looks as art filters | 7 | 2026-11-13 | `5badb0796731b40a27ef015e57da134d7d793486d4c6262a3f483c1aae60fd05` |
| `seven-films-6-interval` | Seven film looks as art filters, and interval shooting with up to 99 frames | 8 | 2026-11-13 | `f52ea6976ac2e9c567b2c07d7556b96b6431c8fcd2d90de195abdb76059e0104` |
<!-- END GENERATED: builds -->

To make a different build, give its description to the script:

```bash
uv run tools/make_firmware.py builds/seven-films-6.json
```

The scripts in `tools/` that make firmware use only the Python standard library. If you have
Python 3.10 or newer, you can use `python3` in place of `uv run`.

To run the tests:

```bash
uv run python -m unittest discover -s tests
```

Some tests need the maker's firmware file. Without the file, the test run skips them.

| To learn about | Read |
|---|---|
| Where each file goes, the code rules, the commit rules, and how to make and test a new build | [docs/conventions.md](docs/conventions.md) |
| What the firmware contains and where | [docs/firmware-map.md](docs/firmware-map.md) |
| The firmware file format | [docs/firmware-format.md](docs/firmware-format.md) |
| The update procedure and recovery | [docs/flashing.md](docs/flashing.md) |
| Each update that we did on a camera, with its result | [docs/camera-log.md](docs/camera-log.md) |
| How we check a patch before a camera test | [docs/verification.md](docs/verification.md) |
| The patch specs that are not in the current build, and their history | [patches/history/README.md](patches/history/README.md) |

## Licence

Code, documentation and notes: [MIT](LICENSE). Some material has other terms:

- The film look data is derived from [spektrafilm](https://github.com/andreavolpato/spektrafilm) by
  Andrea Volpato (CC BY-SA 4.0).
- Excerpts of the Olympus firmware remain the property of Olympus.

This repository includes no firmware and no third-party tool. [NOTICE.md](NOTICE.md) gives the
details and the credits.

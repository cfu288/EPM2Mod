# To do

Open work, most recent first. When an item is done, move its result to the camera log or the README
and delete the item here.

## Engineering checks

From the ninth review of the clean-up (2026-11-25). First decide if the check is worth having.

- CI does not check a build when only one of its specs changes. The test of the build selection matches text only.
- The pre-commit hook reads the working tree, not the staged content, for documents and web files.
- The pull request title check does not run when the title is edited.
- `epm2mod init` accepts an edited binutils source as the pinned one.
- Untracked files under `cli/`, `tools/`, `emulator/` and `gen/` take part in local checks.

## Film simulations

- RAW Data Edit keeps the source RAW's ImageDescription, so a RAW re-developed with another film carries the old name
  (the playback EXIF path, `experiments/2026-11-20-film-name-exif/NOTES.md`).
- RAW Data Edit → ART BKT (one RAW developed in every selected ART entry), a developer tool for film-simulation tests,
  not for release: works on the camera (calibration run and the films-twelve-off round, 2026-11-20); kept in test
  builds only (`experiments/2026-11-20-raw-edit-art-bkt/NOTES.md`).
- One more correction round from the 2026-11-21 readings, weighted for skin and grays: 12 films lost 0.07–0.24 on skin
  against films-look-exif, and grays improved less than model3 predicted (0.75 against 0.63)
  (`experiments/2026-11-20-model-calibration/NOTES.md` §11).
- Per-film 12-region tables: only after the stage rules predict a real table (`experiments/2026-11-20-model-calibration/NOTES.md` §6).
- To consider with the next film feature that needs a flash, not decided: film codes 185 to 255 with one range test
  per colour stage, in place of table and hash entries per code. Each stage has one dispatch site that stills and
  live view share, and codes above 184 take the default branch today (read in the disassembly, 2026-11-21). It
  removes the in-place kind of entry and its special cases (white-balance pair, adaptive-hue hook, matrix pointer);
  the hidden-value kind, the ART BKT hooks and the settings remap stay. Cost: 5 or 6 new hooks in segment 1 and a
  full film re-test on the camera. Check first in the emulator: `emulator/filmcheck.py` with one entry on code 200.

## Level gauge

- Level Adjust works (2026-11-14), and the calibration is kept after power off and on (owner). Not yet reported:
  Reset.
- Not yet reported: the info menu of an electronic
  viewfinder (the new row re-uses the unused panel 594, "EVF Info Settings").

## Focus peaking

- The crash at a focus-ring turn after a shot is fixed in the pinned build (save guard; five clean
  tries on the camera, 2026-11-16). Two small windows stay open (NOTES §18.5). The proven kernel
  code area is nearly full ([code-space map](docs/reference/code-space-map.md)): the next early-loaded code needs a
  new area. The log's build id names the dictionary, not the firmware: put a firmware id in `boot`.
- More than 10 frames per second of peaking needs a shorter pass list or the 50 ms frame class
  (NOTES §17).
- Peaking in movie mode (no lines there, recording or not: the latch's movie condition).
- The row name Peaking is English only.

## Film simulations

- Grain: stock-strength grain needs about 40 bytes of code.
- Look packs from the card: not yet seen on the camera: the film name in playback info. Later: live-view tables
  for movies' own columns if movies need them.
- The published test RAW files (owner name and serial numbers blanked) are not yet developed on the
  camera.
- Add Effects (glow, vignette, white edge, frame) on a film simulation: a data edit, not yet tried.
- In-camera look edits and look import (LUT): requirements, limits and open questions in
  `experiments/2026-11-18-look-editor/NOTES.md`.

## Interval shooting

- Sequences of more than 100 frames work (owner). Not yet reported: a full sequence of 240 frames, the
  cancellation of a sequence, intervals longer than 90 seconds, a full card.
- In the emulator, Time Lapse On with 230 frames and 16 shots left gives "Card Full", and after a
  restart the row reads Off. Find out on the camera: set more frames than the card has room for.
- An empty settings store shows Frame 99, 00:00:01, 00:00:01 in the emulator, not 10 frames and
  5 seconds. Find out on the camera after Reset → Full.

## Exposure

Deferred by the owner on 2026-11-17: anti-shock 0 s, silent shutter, on-screen information. The notes and the
candidate `osd-battery` are kept.

- Exposure compensation in M with Auto ISO: 2 bytes at 0x7E5878AF, not run.
  Notes: `experiments/2026-11-17-auto-iso-min-shutter/NOTES.md` section 6.

- **Anti-shock 0 s and a silent shutter: not settled.** The E-P5 is no donor: the bodies with 0 s
  program the sensor with another register set. A route of our own: stock shutter order, sensor
  start about 30 ms after the first curtain. First, without a build: two RAW pictures of a plain
  wall, Live Time 0.5 s against a normal 0.5 s, to see the reset type and the read-out time.
  Notes: `experiments/2026-11-17-anti-shock/NOTES.md`.

- **On-screen information.** `osd-battery` is a candidate on the old films-12d base: rebase it on the pinned
  build. It shows a battery percentage on the live-view screen. Next in the same label: the lens's focus distance,
  the shutter count, a calibration of the percentage scale, and a row in LV-Info to switch it.
  Notes: `experiments/2026-11-17-osd-info/NOTES.md`.

## Foundations

- From the firmware review of 2026-11-21 (`experiments/2026-11-21-firmware-dive/NOTES.md`). The owner's rule
  (2026-11-21): what is flashed and works is not moved. The two work items are done in `films-start-texts` (wrong menu texts outside English; the race margin). The rest are rules for new work.
  - Measured on the camera with `films-start-texts` (2026-11-21): the segment copies end 1.28 s before the first
    colour stage job (three lever starts in P), so the 7 film hooks from segment 1 into segment 2 have that margin.
    Not measured: a start with the shutter held, and wake from sleep. Nothing is moved.
  - For new work:
    - new code goes in segment 2 or 3; when the proven room there runs out, prove a slice of the 123,745 B of
      debug-shell handlers in segment 2 (§1). The kernel range gets nothing new unless an early hook forces it;
    - code that must run at start uses an entry of segment 3's constructor table, not a jump over code (§2);
    - new menu texts are set at run time (§5);
    - a new film-table layout uses 15 tone tables per entry, not 24 (§4);
    - to try on the camera before a build: the card folder `PARAMDT` overrides settings on stock firmware in the
      emulator (§7). Its worst case is not bounded: start with one harmless tag.

- Structured log: works on the camera (2026-11-15). Evaluation of the first log and the next
  probes (power-on factor, real restart count, per-CPU gates, peaking loop time, flush end):
  `experiments/2026-11-15-log/evaluation-1.md`. Unknown: if the ring RAM survives a crash restart.
  A ring overflows after about 100 s of peaking without a menu. The camera writes compact binary event
  records to `EPM2LOG.BIN` on the card; `epm2mod log` decodes them with the dictionary
  `data/logdict/events.json`. The pinned build has it: Custom Menu J → Debug Log (Off by default). Probes go into the old
  features too (peaking, picture mode changes, level gauge, interval, film looks, firmware errors).
  Next: code from the card.
- To explore, not decided: a loader, as [OMKit](https://github.com/necrostaz/omkit) has for the OM-5 Mark II. One
  small flashed hook starts a task that reads code from the card into RAM and runs it, so a new feature is a file copy
  and not a flash; holding OK at power-on skips it. Unknown on the E-PM2: a start-up point late enough, and free RAM
  that may hold code. Smallest probe, one flash: our task reads a file into RAM we own, jumps to it, and writes one
  line to the Debug Log. Cost to weigh: a feature loaded this way needs the card in the camera. OMKit also builds C
  with GCC for this processor and wraps the firmware's calls in one driver layer.
- Feature candidates from the survey of 22 other bodies and of other mods:
  `experiments/2026-11-15-feature-survey/`. Cheap ones: video bitrate and time limit (patches
  written), Light Box (hidden in this firmware), Add Effects on film simulations, more film simulations.

- The load-order check (`uv run python emulator/hookcheck.py data/builds/NAME.json`) counts 87 transfers from segment 1
  or the kernel into segments 2 and 3 in the pinned build ([load-order.md](docs/dev/load-order.md), section 5). Two are task entries that only segment-2 code starts (proof).
  The other 85 are from `stock-films-structure-3` and safe by timing only: the two colour-stage hooks 0x7E56C6A5 and
  0x7E546160, ten hooks of the ART BKT frame composer, and 73 table words (the colour stage's cases of the film
  codes, and the live-view rows of the hidden art values 111 to 118). Nothing waits for the segment-2 copy
  (`experiments/2026-11-21-firmware-dive/NOTES.md` §2). Not known: whether a cold start in ART mode with a film
  simulation on the selected entry reaches one of them before the copy ends. Probe: the start list of
  `experiments/2026-11-24-slow-boot/NOTES.md` §7 in that state. A clean fix for 0x7E56C6A5 moves 219 bytes into a
  dead function of segment 1.
  The candidate `film-tables-fix` removes 25 of the 73 table words from that list (the routes of the hidden art
  values, `experiments/2026-11-25-film-tables/NOTES.md`); when it is pinned, remove their three rows from the allow list and
  update `cli/tests/test_hookcheck.py`, which holds spot-af-2 to one FAIL.
- Emulator ([emulator/boot/README.md](emulator/boot/README.md)), open points:
  - The row Time Lapse Settings is grey when the clock is not set. Start the emulator with
    `E101_RTC=2026-11-14T12:00:00`.
  - Not reached: the screens of a viewfinder, the super control panel. The live control
    (OK → Picture Mode strip) is reached.
  - Power-off does not finish. Half-press and full press are not tried. A real JPEG in playback is
    not tried.
  - The background pictures of the menus are in a flash area that is not in the update file, so
    they are grey.

- The probes in [feasibility.md](docs/dev/feasibility.md), section "Unknowns": the longer load range.

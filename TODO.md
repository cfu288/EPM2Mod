# To do

Open work, most recent first. When an item is done, move its result to the camera log or the README
and delete the item here.

## One-click installer

Test releases up to v2026.11.19-rc.2. Open: the final release.

## Level gauge

- Level Adjust works (2026-11-14). Not yet reported: the calibration after power off and on, and
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
- Peaking without the zoom: the trigger is the MF Assist state object, which also asks for the zoom.
  It needs the E-P5 state object paired (NOTES §15.5).
- The row name Peaking is English only.

## Film simulations

- Grain: stock-strength grain needs about 40 bytes of code.
- Film files from the card: not yet seen on the camera: the film name in playback info. Later: live-view tables
  for movies' own columns if movies need them.
- The published test RAW files (owner name and serial numbers blanked) are not yet developed on the
  camera.
- Add Effects (glow, vignette, white edge, frame) on a film simulation: a data edit, not yet tried.
- In-camera look edits and look import (LUT): requirements, limits and open questions in
  `experiments/2026-11-18-look-editor/NOTES.md`.

## Interval shooting

- Not yet reported: a full sequence of 240 frames, the cancellation of a sequence, intervals longer
  than 90 seconds, a full card.
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

- Structured log: works on the camera (2026-11-15). Evaluation of the first log and the next
  probes (power-on factor, real restart count, per-CPU gates, peaking loop time, flush end):
  `experiments/2026-11-15-log/evaluation-1.md`. Unknown: if the ring RAM survives a crash restart.
  A ring overflows after about 100 s of peaking without a menu. The camera writes compact binary event
  records to `EPM2LOG.BIN` on the card; `epm2mod log` decodes them with the dictionary
  `data/logdict/events.json`. The pinned build has it: Custom Menu J → Debug Log (Off by default). Probes go into the old
  features too (peaking, picture mode changes, level gauge, interval, film looks, firmware errors).
  Next: code from the card.
- Feature candidates from the survey of 22 other bodies and of other mods:
  `experiments/2026-11-15-feature-survey/`. Cheap ones: video bitrate and time limit (patches
  written), Light Box (hidden in this firmware), Add Effects on film simulations, more film simulations.

- The load-order check (`python3 emulator/hookcheck.py SPEC...`) reports seven failures in the pinned build, all
  from `stock-films-structure`: hooks in segment 1, among them 0x7E56C6A5, that jump to code in segment 2. All
  seven are in `emulator/hookcheck-allow.tsv`, and `python3 tools/freespace.py check` passes with them. For
  0x7E56C6A5, the audit shows that the host function is reached only through the image-job table 0x7E789604, and
  it did not run before segment 2 was loaded on a normal start, a quick start and the update path. That is a test
  result, not a proof. A clean fix moves 219 bytes into a dead function of segment 1.
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

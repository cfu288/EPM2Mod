# To do

Open work, most recent first. When an item is done, move its result to the camera log or the README
and delete the item here.

## One-click installer

- A zip for any platform: double-click, a local page makes the firmware, adds film looks (optional), and writes to
  an SD card or gives a zip. Olympus's art filters stay the default. Plan and criteria:
  [installer design](../experiments/2026-11-17-installer/design.md).
- Separate project: Olympus's art filters by default, films only in the slots where a user loads one (criteria F1-F5
  in the same design). The installer doesn't wait for it.
- Not published (owner, 2026-11-17): first a camera test of the firmware with and without film looks, and of every
  feature, with a build that writes the log: `log-menu` (pinned 2026-11-18) writes it, switched by Custom Menu J ->
  Debug Log. Next: Olympus's art filters by default
  ([stock-filters design](../experiments/2026-11-18-stock-filters/design.md)).

## Level gauge

- Level Adjust works (2026-11-14). Not yet reported: the calibration after power off and on, after
  a flash of a different build, and Reset.
- Not yet reported: the gauge in portrait orientation, and the info menu of an electronic
  viewfinder (the new row re-uses the unused panel 594, "EVF Info Settings").

## Focus peaking

- The crash at a focus-ring turn after a shot is fixed in the pinned build (save guard; five clean
  tries on the camera, 2026-11-16). Two small windows stay open (NOTES §18.5). The proven kernel
  code area is full (18 bytes left with all specs counted): the next early-loaded code needs a new
  area. The log's build id names the dictionary, not the firmware: put a firmware id in `boot`.
- More than 10 frames per second of peaking needs a shorter pass list or the 50 ms frame class
  (NOTES §17). `peaking-fast` is the pinned build (2026-11-15).
- Peaking without the zoom: the trigger is the MF Assist state object, which also asks for the zoom.
  It needs the E-P5 state object paired (NOTES §15.5).
- The words Peaking, White and Black are English only: the other languages keep the old texts of
  ids 1500, 1501, 1505, 1506.
- Make the emulator's boot test a step of `epm2mod make` for every candidate. The commands exist
  (`tools/emu/boot-test`, `tools/emu/update-path-test`, exit status 0 = pass); `make` does not call
  them yet.

## Film looks

- `films-12d` is the pinned build (2026-11-16): twelve films with Double-X, and the peaking save
  guard. Not yet reported from the camera: movie mode and ART shooting mode in the five new entries,
  an interval sequence with the ring turning, a flash of the log-free bytes. Open: a selection of an
  old filter stored before the flash keeps that filter until a Picture Mode is chosen; Filter Type
  and Add Effects do nothing in the five entries; Double-X is fifth in the list, not last; the
  second Double-X fit has no chart measurement; stock-strength grain needs about 40 bytes of code.
- Looks from the SD card (`card-looks-4`, pinned 2026-11-17): not yet seen on the camera: the
  film name in playback info. Later: live-view tables for movies' own columns if movies need them.
- Type II of Portra, Pro 400H and Superia is the same as type I, and is not tested on the camera.
- The published test RAW files (owner name and serial numbers blanked) are not yet developed on the
  camera.
- Add Effects (glow, vignette, white edge, frame) on a film look: a data edit, not yet tried.
- In-camera look edits and look import (LUT): requirements, limits and open questions in
  `experiments/2026-11-18-look-editor/NOTES.md`.
- More film entries through the hidden art-filter numbers 110 to 118: not yet tried.
- The film names in the other 33 languages are in the pinned build; not tested on the camera (the
  owner does not need them). Unknown: where the texts 1173 and 1186 show.

## Interval shooting

- Not yet reported: a full sequence of 240 frames, the cancellation of a sequence, intervals longer
  than 90 seconds, a full card.
- In the emulator, Time Lapse On with 230 frames and 16 shots left gives "Card Full", and after a
  restart the row reads Off. Find out on the camera: set more frames than the card has room for.
- An empty settings store shows Frame 99, 00:00:01, 00:00:01 in the emulator, not 10 frames and
  5 seconds. Find out on the camera after Reset → Full.

## Video

- Higher bitrate and no 29-minute limit: the patches are written
  (`experiments/2026-11-12-hardware/`), not built and not flashed.

## Exposure

Deferred by the owner on 2026-11-17: the items of this section (minimum shutter speed, anti-shock 0 s,
silent shutter, on-screen information). The notes and the candidate `osd-battery` are kept.

- **Minimum shutter speed with Auto ISO: the stock firmware has it.** The program holds the shutter at
  max(1/(2 × focal length), 1/30, Flash Slow Limit), also without a flash. Set MENU → Custom Menu →
  F → Slow Limit to 1/250 (the default is 1/60). Verified in the function harness, not yet on the
  camera. A row of its own up to 1/4000 is prototyped (50 bytes in place, about one day with its
  menu row). Exposure compensation in M with Auto ISO: 2 bytes at 0x7E5878AF, not run.
  Notes: `experiments/2026-11-17-auto-iso-min-shutter/NOTES.md`.

- **Anti-shock 0 s and a silent shutter: not settled.** The E-P5 is no donor: the bodies with 0 s
  program the sensor with another register set. A route of our own: stock shutter order, sensor
  start about 30 ms after the first curtain. First, without a build: two RAW pictures of a plain
  wall, Live Time 0.5 s against a normal 0.5 s, to see the reset type and the read-out time.
  Notes: `experiments/2026-11-17-anti-shock/NOTES.md`.

- **On-screen information.** `osd-battery` is a candidate: a battery percentage on the live-view
  screen. Next in the same label: the lens's focus distance (about 90 bytes), the shutter count
  (about 40 bytes), a calibration of the percentage scale, and a row in LV-Info to switch it. The
  segment-2 code area has 722 bytes left, in runs of 120 bytes or less.
  Notes: `experiments/2026-11-17-osd-info/NOTES.md`.

## Foundations

- Structured log: works on the camera (2026-11-15). Evaluation of the first log and the next
  probes (power-on factor, real restart count, per-CPU gates, peaking loop time, flush end):
  `experiments/2026-11-15-log/evaluation-1.md`. Unknown: if the ring RAM survives a crash restart.
  A ring overflows after about 100 s of peaking without a menu. The camera writes compact binary event
  records to `EPM2LOG.BIN` on the card; `epm2mod log` decodes them to JSON lines with the dictionary
  `logs/events.json`. A debug build only: the pinned build stays without it. Probes go into the old
  features too (peaking, picture mode changes, level gauge, interval, film looks, firmware errors).
  Next after it: read a file, looks from the card, code from the card.
- Feature candidates from the survey of 22 other bodies and of other mods:
  `experiments/2026-11-15-feature-survey/`. Cheap ones: video bitrate and time limit (patches
  written), Light Box (hidden in this firmware), Add Effects on looks, more looks.

- The load-order check (`python3 tools/emu/hookcheck.py SPEC...`) reports one failure in the pinned
  build: the hook at 0x7E56C6A5 (`remap7b-code`, segment 1) jumps to code in segment 2. The audit
  shows that the host function is reached only through the image-job table 0x7E789604, and it did
  not run before segment 2 was loaded on a normal start, a quick start and the update path. That is
  a test result, not a proof. A clean fix moves 219 bytes into a dead function of segment 1.
- Emulator ([tools/emu/boot/README.md](../tools/emu/boot/README.md)), open points:
  - The row Time Lapse Settings is grey when the clock is not set. Start the emulator with
    `E101_RTC=2026-11-14T12:00:00`.
  - Not reached: the screens of a viewfinder, the super control panel. The live control
    (OK → Picture Mode strip) is reached: use it for the screenshot of the film-looks guide.
  - Power-off does not finish. Half-press and full press are not tried. A real JPEG in playback is
    not tried.
  - The background pictures of the menus are in a flash area that is not in the update file, so
    they are grey.

- The probes in [feasibility.md](feasibility.md), section "Unknowns": a file write for a log
  channel, a file read, tables at a RAM address, a longer load range.

# To do

Open work, most recent first. When an item is done, move its result to the camera log or the README
and delete the item here.

## Level gauge

- Level Adjust works (2026-11-14). Not yet reported: the calibration after power off and on, after
  a flash of a different build, and Reset.
- Not yet reported: the gauge in portrait orientation, and the info menu of an electronic
  viewfinder (the new row re-uses the unused panel 594, "EVF Info Settings").

## Focus peaking

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

- Type II of Portra, Pro 400H and Superia is the same as type I, and is not tested on the camera.
- The published test RAW files (owner name and serial numbers blanked) are not yet developed on the
  camera.
- Add Effects (glow, vignette, white edge, frame) on a film look: a data edit, not yet tried.
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

## Foundations

- Log defect (second camera log, 2026-11-15): the ring header is trusted when its magic word is
  right. After a firmware update the RAM held old content with changed bits and a 0x5A5A5A5A
  fill, the magic word matched, and the record numbers were garbage. Give the header a check
  (index and its complement, bounds), start a new ring when it fails, and make the decoder drop
  records that cannot be real.
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

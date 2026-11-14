# To do

Open work, most recent first. When an item is done, move its result to the camera log or the README
and delete the item here.

## Level gauge

- **A way to calibrate the level gauge.** The gauge works (2026-11-14), but the mod has no menu row
  to set its zero. The E-PL6 has the row "Level Adjust" in Custom Menu K, with Reset and Adjust.
  The E-PM2 firmware has the texts (160 "Level Adjust", 478, 847, 223, 749), the panel (173) and the
  calibration call (`api_adj_Set_Slope_Adjust` 0x7E676261: mode 0 resets, mode 1 sets zero at the
  current position). Only the menu row is missing: one item record, one child entry and shifted row
  constants in the custom-menu code, as the interval row was added.
  - The owner reports (2026-11-14): on a flat surface the gauge is slightly off. So this row is
    needed. In work.
  - Before the work: decode fields 6 and 7 of the custom-menu item record.
  - Notes: `experiments/2026-11-14-level-gauge/NOTES.md` §5.2 and §8 (step B).
- Not yet reported: the gauge in portrait orientation, and the info menu of an electronic
  viewfinder (the new row re-uses the unused panel 594, "EVF Info Settings").

## Focus peaking

- Test the build `peaking-direct-3` on the camera (steps: the camera log and NOTES §12 and §13).
  `peaking-direct-2` was withdrawn: it crashed at start-up in the emulator.
- The two crashes of the first build: the scenario tests show a likely cause (the image memory is
  re-divided under live buffers when a filter changes while lines are on). The camera test of
  `peaking-direct-3` must confirm that they are gone.
- If the lines are too coarse: use the E-P5's line settings. This needs a change in the image
  library.
- A menu entry and a colour choice come last.

## Film looks

- Type II of Portra, Pro 400H and Superia is the same as type I, and is not tested on the camera.
- The published test RAW files (owner name and serial numbers blanked) are not yet developed on the
  camera.
- Add Effects (glow, vignette, white edge, frame) on a film look: a data edit, not yet tried.
- More film entries through the hidden art-filter numbers 110 to 118: not yet tried.
- The film names are complete only in English. German and Spanish show two names, French three,
  Greek three; Japanese, Chinese, Russian, Thai, Korean and Bulgarian show the old names. Rename the
  entries of the other language tables.
- Defect: in French, the label of the effect "Soft Focus" (Add Effects) reads "Ektachrome". Remove
  the edit at block 1 offset 0x3D5550 from `patches/seven-labels.json` in the next build.
  Both items: `experiments/2026-11-14-emulator-audit/NOTES.md` §5.

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

- The load-order check (`python3 tools/emu/hookcheck.py SPEC...`) reports one failure in the pinned
  build: the hook at 0x7E56C6A5 (`remap7b-code`, segment 1) jumps to code in segment 2. The audit
  shows that the host function is reached only through the image-job table 0x7E789604, and it did
  not run before segment 2 was loaded on a normal start, a quick start and the update path. That is
  a test result, not a proof. A clean fix moves 219 bytes into a dead function of segment 1.
- Make the load-order check and the emulator's boot test a step of `epm2mod make` for a candidate.
- Emulator (outside the repository, `~/opt/om-emu-e101-boot-work/`), open points:
  - The row Time Lapse Settings is grey when the clock is not set. Start the emulator with
    `E101_RTC=2026-11-14T12:00:00`.
  - Not reached: the screens of a viewfinder, the live control, the super control panel.
  - Power-off does not finish. Half-press and full press are not tried. A real JPEG in playback is
    not tried.
  - The background pictures of the menus are in a flash area that is not in the update file, so
    they are grey.

- The probes in [feasibility.md](feasibility.md), section "Unknowns": a file write for a log
  channel, a file read, tables at a RAM address, a longer load range.

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
  - First: put the camera on a surface that is known to be level, and write down what the gauge
    shows. If it shows level, the factory offsets are good and this item has low priority.
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

## Interval shooting

- Not yet reported: a full sequence of 240 frames, the cancellation of a sequence, intervals longer
  than 90 seconds, a full card.

## Video

- Higher bitrate and no 29-minute limit: the patches are written
  (`experiments/2026-11-12-hardware/`), not built and not flashed.

## Foundations

- The load-order check (`python3 tools/emu/hookcheck.py SPEC...`) reports one failure in the pinned
  build: the hook at 0x7E56C6A5 (`remap7b-code`, segment 1) jumps to code in segment 2. The camera
  has started and updated normally many times with this hook, and the emulator's boot test passes,
  so the hooked function does not run before segment 2 is loaded. Prove that from the code, or move
  the routine into segment 1.
- Make the load-order check and the emulator's boot test a step of `epm2mod make` for a candidate.
- The emulator boots the stock firmware to the application (work outside the repository, in
  `~/opt/om-emu-e101-boot-work/`). In work: the shooting screen, key presses and menus.

- The probes in [feasibility.md](feasibility.md), section "Unknowns": a file write for a log
  channel, a file read, tables at a RAM address, a longer load range.

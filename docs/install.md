# Install

<!-- BEGIN GENERATED: pinned-build -->
The pinned build is **`films-12d`**: twelve film looks in the art-filter entries (eleven colour films and Kodak Double-X in black-and-white), named in all 34 languages; interval shooting with up to 240 frames; the level gauge with Level Adjust; focus peaking with the setting Off / White / Red / Yellow / Blue. We tested this build on a real E-PM2 on 2026-11-16 ([camera log](camera-log.md)).

| | sha256 |
|---|---|
| Stock firmware, `OLY_E_101_1600_0000_0000.BIN` | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` |
| Pinned build, `films-12d` | `2cdd18e7004821b2e443ec4f08db06ab9a0d4f0f700ab53db8c4bbc1dad93e32` |
<!-- END GENERATED: pinned-build -->

The steps are in the [README](../README.md#install).

**Checksums.** The build stops if its sha256 differs from the value above, so no manual
check is needed. With `--out DIR` the script also reads the copy back from `DIR/DCOLYMP/`.

**The lamp.** Recorded on this camera: steady for 70 to 100 seconds, then blinking until power-off
(more than 20 minutes when left alone). No update has failed so far, so there is no tested advice
for a lamp that never blinks.

**After the update.** The camera keeps its settings: the level calibration and the Peaking setting
stayed over four updates (logs of 2026-11-15 and 2026-11-16). The file can stay on the card: the
camera reads it only when **OK** is held at power-on.

**To go back to the original firmware.** Run `uv run tools/fetch_stock.py`. Copy
`firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN` to the card as `DCOLYMP/E1019999.BIN`, then do steps 3 and 4 of the README. This way back was
used on this camera on 2026-11-08.

Use only a file for the E-PM2. How the update works, and the sources: [flashing.md](flashing.md).

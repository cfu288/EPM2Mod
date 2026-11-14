# Install

<!-- BEGIN GENERATED: pinned-build -->
The pinned build is **`seven-films-6-interval-240-level-adjust`**: seven film looks as art filters, interval shooting with up to 240 frames, the level gauge, and Level Adjust (calibrate the level gauge). We tested this build on a real E-PM2 on 2026-11-14 ([camera log](camera-log.md)).

| | sha256 |
|---|---|
| Stock firmware, `OLY_E_101_1600_0000_0000.BIN` | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` |
| Pinned build, `seven-films-6-interval-240-level-adjust` | `e93d1589b3406ec991e3f32225acf6e2c2074aa58fc5394ca06a93da83797b66` |
<!-- END GENERATED: pinned-build -->

**Use this firmware at your own risk.** It is unofficial and only for the E-PM2 with firmware 1.6
(Setup Menu → Firmware). An interrupted update can make a camera unusable. Never put a firmware file
for another camera on the card.

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), an SD card and a full
battery.

1. Get this repository (**Code → Download ZIP**, or `git clone`) and open a terminal in its folder.
2. Put the SD card in the computer. Run this command with the location of the card:

   ```bash
   uv run tools/make_firmware.py --card /Volumes/NAME
   ```

   The script downloads the maker's firmware, applies the patches, checks the result and writes it
   to the card. If a step fails, it stops with a message. This repository contains no firmware.
3. Put the card in the camera. With the camera off, hold **OK** and switch the camera on.
4. The lamp is orange for about one minute. Do not touch the camera. When the lamp blinks, switch
   the camera off and on.

**To go back to the original firmware:** run `uv run tools/fetch_stock.py`, copy the file that it
names to the card as `DCOLYMP/E1019999.BIN`, then do steps 3 and 4.

More about the update and recovery: [flashing.md](flashing.md).

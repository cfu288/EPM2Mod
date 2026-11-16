# Install

<!-- BEGIN GENERATED: pinned-build -->
The pinned build is **`films-12d`**: twelve film looks in the art-filter entries (eleven colour films and Kodak Double-X in black-and-white), named in all 34 languages; interval shooting with up to 240 frames; the level gauge with Level Adjust; focus peaking with the setting Off / White / Red / Yellow / Blue. We tested this build on a real E-PM2 on 2026-11-16 ([camera log](camera-log.md)).

| | sha256 |
|---|---|
| Stock firmware, `OLY_E_101_1600_0000_0000.BIN` | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` |
| Pinned build, `films-12d` | `2cdd18e7004821b2e443ec4f08db06ab9a0d4f0f700ab53db8c4bbc1dad93e32` |
<!-- END GENERATED: pinned-build -->

**Use this firmware at your own risk.** It is unofficial and only for the E-PM2 with firmware 1.6
(Setup Menu → Firmware). An interrupted update can make a camera unusable. Never put a firmware file
for another camera on the card.

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), an SD card and a full
battery.

1. Open a terminal in the folder of this repository.
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

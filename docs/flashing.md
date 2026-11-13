# Flashing the E-PM2 from an SD card

This procedure is **confirmed on the E-PM2** (see [camera-log.md](camera-log.md)): body firmware 1.6, two stock reflashes and one modified flash on 2026-11-08.

## Steps

1. Charge the battery fully. Use a small card formatted in the camera.
2. Build or choose a BIN:
   - Stock: `firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN`
   - Modified: `build/<name>.BIN` (see [../README.md](../README.md))
3. Copy it to the card as **`DCOLYMP/E1019999.BIN`**. It must be the only file in `DCOLYMP`. Check the sha256 on the card against the build output.
   From the Mac:
   ```bash
   scp USER@HOST:/path/to/EPM2Mod/build/NAME.BIN \
     /Volumes/SDCARD/DCOLYMP/E1019999.BIN
   shasum -a 256 /Volumes/SDCARD/DCOLYMP/E1019999.BIN
   cd ~ && diskutil eject /Volumes/SDCARD
   ```
4. With the camera off and the card in, hold **OK** and power on.
5. The lamp shows progress:
   - **Solid orange, about 1–1.5 min:** writing. **Do not touch the camera.**
   - **Blinking:** finished. It keeps blinking until you power off.
6. Power off, then on normally. Check Setup menu → Firmware, and confirm the patch.
7. **Recovery:** flash the stock BIN the same way. Proven on 2026-11-08: it went from modified back to stock.

If the camera boots straight to live view at step 4, the file wasn't recognised and nothing was written. The fallback name is `E1011600.BIN`, but it may be ignored as an equal version.

**Never** put an E-PL5 file (`E100…`) on the card. The E-PM2 updater searches for `E100????BIN` and accepts the E-PL5 model id 0x1000 for main packages (verified in code, see [firmware-map.md](firmware-map.md) §2), so it would not reject one. Check that header bytes 2–3 read `10 10` before every flash.

## Sources (checked 2026-11-08)

| # | Source | Camera | What it says |
|---|---|---|---|
| A | lightsnowdev, "New Olympus OM-D and PEN Firmware Leaks!" (12 Nov 2014, Wayback) | **E-PM2**, E-P5, E-M5, others | "If you have an E-PM2 rename it to `E1011300.BIN` … folder called `DCOLYMP` … start the camera while pushing the OK button. The red LED will go on for about 1 minute. If it's flashing on/off … the process is finished." |
| B | lightsnowdev, Firmware Control page (2014, Wayback) | Includes the E-PM2 | Same method. "Wait until the red LED is blinking on/off. This means the process is finished." |
| C | xdel.ru `install-fw.txt` | E-M5 III | "orange front LED will turn on. DO NOT TURN THE CAMERA OFF WHILE THE LED IS ON. Wait until it blinks rapidly. This means the process is finished." |
| D | ep5-fw-reverse `HARDWARE_RUNBOOK.md` (2026-10-24) | E-P5 | `DCOLYMP\E1089999.BIN`, hold OK. Reads blinking as still writing, which **is wrong for the E-PM2**. |
| E | E-PM2 v1.6 block 0 (local) | E-PM2 | Contains `DCOLYMP`, the pattern table `E101????BIN … E100????BIN`, and `[firmup]` strings. |

The `9999` suffix makes the camera treat the file as newer than anything installed (PhotoDmiK: "9999 in name of BIN file fools updater to think its newer 9.999 version").

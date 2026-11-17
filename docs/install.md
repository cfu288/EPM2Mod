# Install

<!-- BEGIN GENERATED: pinned-build -->
The pinned build is **`card-looks`**: film simulations in the twelve art filter entries (eleven colour films and Kodak Double-X in black-and-white), film looks loaded from the SD card and kept in the camera, interval shooting with up to 240 frames, a level gauge with calibration, and focus peaking. We tested this build on a real E-PM2 on 2026-11-17 ([camera log](camera-log.md)).

| | sha256 |
|---|---|
| Stock firmware, `OLY_E_101_1600_0000_0000.BIN` | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` |
| Pinned build, `card-looks` | `889dbcaf49b3ee0a00266ac6420d87f3f47031d0f9e81e3af9b99640ebe35949` |
<!-- END GENERATED: pinned-build -->

The install steps are in the [README](../README.md#install).

## Checksums

The build script verifies the checksum itself and stops if it does not match. With `--card`, it also verifies the copy on the SD card.

## Restore Original Firmware

1. To download the original Olympus firmware, run

   ```sh
   uv run tools/fetch_stock.py
   ```

   This writes `firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN`.
2. Copy that file to the SD card as `DCOLYMP/E1019999.BIN`.
3. Flash it the same way as the mod (step 3 of the [README](../README.md#install)).

## Notes

- Your camera settings are kept when you flash.
- You can leave the firmware file on the card. The camera only reads it when you hold **OK** while switching on.
- Only use firmware built for the E-PM2.

For how the update process works, see [flashing](flashing.md).

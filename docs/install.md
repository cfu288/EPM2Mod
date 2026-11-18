# Install

<!-- BEGIN GENERATED: pinned-build -->
The pinned build is **`stock-films`**: the twelve Olympus art filters unchanged; film looks loaded from the SD card with Custom Menu J, Load Looks, overwrite the entries the file lists; interval shooting with up to 240 frames, a level gauge with calibration, and focus peaking; a Debug Log row in Custom Menu J (Off by default) that writes EPM2LOG.BIN to the card for bug reports. We tested this build on a real E-PM2 on 2026-11-18 ([camera log](camera-log.md)).

| | sha256 |
|---|---|
| Stock firmware, `OLY_E_101_1600_0000_0000.BIN` | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` |
| Pinned build, `stock-films` | `2859767da0014bcb637ca3016898c940f7678d244794d3d5bb231c7e8c0ba8cd` |
<!-- END GENERATED: pinned-build -->

The install steps are in the [README](../README.md#install).

## Checksums

The build script verifies the checksum itself and stops if it does not match. With `--card`, it also verifies the copy on the SD card.

## Restore Original Firmware

1. Put Olympus's original firmware on the card (it is downloaded from OM Digital Solutions and checked):

   ```sh
   uv run epm2mod restore --card /path/to/card
   ```

   Without a card: `uv run epm2mod restore -o FILE`, then copy the file to the card as `DCOLYMP/E1019999.BIN`.
2. Flash it the same way as the mod (step 3 of the [README](../README.md#install)).

The installer does the same: choose **Olympus original** at the Firmware step.

## Notes

- Your camera settings are kept when you flash.
- You can leave the firmware file on the card. The camera only reads it when you hold **OK** while switching on.
- Only use firmware built for the E-PM2.

For how the update process works, see [flashing](flashing.md).

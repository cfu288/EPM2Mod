# Install

<!-- BEGIN GENERATED: pinned-build -->
The installer and `install` write the firmware **`peaking-mf`**: the twelve Olympus art filters unchanged; film simulations loaded from the SD card with Custom Menu J, Load Looks, overwrite the entries the file lists, without Natural's selective colour changes on top, are applied at power-on before the first picture, and a photo taken with one records the film's name (EXIF ImageDescription); interval shooting with up to 240 frames, a level gauge with calibration that keeps the shooting information of the histogram screen (as the PEN-F does), and focus peaking, which in MF shows the lines in the normal live view the whole time (no magnified view needed, with any lens) and with MF Assist when the focus ring turns; a Debug Log row in Custom Menu J (Off by default) that writes EPM2LOG.BIN to the card for developers; a Lowest S/S Setting row in Custom Menu E (the shutter speed at which ISO Auto starts to rise in P and A); the added menu rows read the same in every menu language; the Firmware screen shows the build's label (Body : 1.6 EPM2Mod 2026.11.20). We tested this build on a real E-PM2 on 2026-11-21 ([camera log](../camera-log/)).

| | sha256 |
|---|---|
| Stock firmware, `OLY_E_101_1600_0000_0000.BIN` | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` |
| Pinned build, `peaking-mf` | `6a47806dfafce15d281358eae2beffe397132e5999c50b28c69b2a2467efcf39` |
<!-- END GENERATED: pinned-build -->

The install steps are in the [README](../../README.md#install).

## Checksums

`install` verifies the checksum itself and stops if it does not match. It also reads each file back from the SD card and compares the checksum. To see what is on the card, run `uv run epm2mod inspect --card /path/to/card`. All commands and options are in the [command-line reference](../reference/cli.md).

## Restore Original Firmware

1. Put Olympus's original firmware on the card (it is downloaded from OM Digital Solutions and checked):

   ```sh
   uv run epm2mod restore --card /path/to/card
   ```

   Without a card: `uv run epm2mod restore -o FILE`, then copy the file to the card as `DCOLYMP/E1019999.BIN`.
2. Do the steps that `restore` prints.

The installer does the same: choose **Olympus original** at the Firmware step.

## Notes

- Your camera settings are kept when you flash.
- You can leave the firmware file on the card. The camera only reads it when you hold **OK** while switching on.
- Only use firmware built for the E-PM2.

For how the update process works, see [flashing](flashing.md).

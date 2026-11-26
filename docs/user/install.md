# Install

<!-- BEGIN GENERATED: pinned-build -->
The installer and `install` write the firmware **`film-tables-fix`**: the twelve Olympus art filters unchanged; film simulations loaded from the SD card with Custom Menu J, Load Looks, overwrite the entries the file lists, without Natural's selective colour changes on top, are applied at power-on before the first picture, and a photo taken with one records the film's name (EXIF ImageDescription); interval shooting with up to 240 frames, a level gauge with calibration that keeps the shooting information of the histogram screen (as the PEN-F does), and focus peaking, which in MF shows the lines in the normal live view the whole time (no magnified view needed, with any lens) and with MF Assist when the focus ring turns; a Debug Log row in Custom Menu J (Off by default) that writes EPM2LOG.BIN to the card for developers; a Lowest S/S Setting row in Custom Menu E (the shutter speed at which ISO Auto starts to rise in P and A); spot metering at the AF target: Custom Menu E, Spot Metering, has an On/Off row each for Spot, Spot Hilight and Spot Shadow (all Off by default); a variant set to On meters at the AF point set by a touch on the screen, or else at the selected AF target in single-target AF; the names of the added menu rows read the same in every menu language; the Firmware screen shows the build's label (Body : 1.6 EPM2Mod YYYY.MM.DD, the day of the release). We tested this build on a real E-PM2 on 2026-11-25 ([camera log](../camera-log/)).

| | sha256 |
|---|---|
| Stock firmware, `OLY_E_101_1600_0000_0000.BIN` | `34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300` |
| Pinned build as tested, `film-tables-fix` | `e029facb38569880c0cec4c16b0f295ca2a96214ed75900fe00585f6b0cedd28` |

A release holds this build with the day of the release on the Firmware screen. Its sha256 is then another one: the release notes give both.
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
2. Do the steps that `restore` prints. One step resets the camera's settings, because the settings that EPM2Mod added stay in the camera after the original firmware is installed.

The installer does the same: choose **Olympus original** at the Firmware step.

## Notes

- Your camera settings are kept when you flash.
- You can leave the firmware file on the card. The camera only reads it when you hold **OK** while switching on.
- Only use firmware built for the E-PM2.

For how the update process works, see [flashing](flashing.md).

# EPM2Mod

![Olympus PEN E-PM2](docs/images/epm2.jpg)

Repository containing the current work for creating a custom firmware mod for the Olympus PEN **E-PM2**. The goal is to unlock or add new features to this camera. Currently, we've implemented replacing the default art filters with film simulations like Portra, Ektachrome, etc. We also enabled interval shooting (up to 240 shots) and added a level gauge and focus peaking.

| Feature | Guide | Status |
|---|---|---|
| Film looks | [docs/guide/film-looks.md](docs/guide/film-looks.md) | Tested on the camera |
| Interval shooting | [docs/guide/interval-shooting.md](docs/guide/interval-shooting.md) | Tested on the camera |
| Level gauge | [docs/guide/level-gauge.md](docs/guide/level-gauge.md) | Tested on the camera |
| Focus peaking | [docs/guide/focus-peaking.md](docs/guide/focus-peaking.md) | Tested on the camera |

## Dependencies

The build script needs [uv](https://docs.astral.sh/uv/getting-started/installation/). uv installs the right Python for you.

## Install

This firmware is only for an E-PM2. The firmware is unofficial, and you use it at your own risk. Start with a full battery, because an update that stops part-way can leave the camera unusable.

1. To build a copy of the firmware, run

   ```sh
   uv run tools/make_firmware.py
   ```

   This downloads the Olympus firmware, applies the patches and writes `build/card/DCOLYMP/E1019999.BIN`.
2. Copy the folder `build/card/DCOLYMP` to the top folder of an SD card, beside `DCIM`. `E1019999.BIN` must be the only file in `DCOLYMP`. If you add `--out /path/to/card` to the command in step 1, the script makes this copy for you.
3. Put the card in the camera. With the camera off, hold **OK** and switch the camera on. An orange lamp shows the progress.
   - While the lamp is steady, the camera is writing the firmware. This takes 1 to 2 minutes. Do not switch the camera off or open the battery door.
   - When the lamp blinks, the update is done. Switch the camera off and on again.
4. To check the result, press **OK** in P, A, S or M mode, select **Picture Mode**, and move right past Custom. The list now shows **Portra 400**.

If the camera starts as usual in step 3, it did not find the file and wrote nothing. Check that `DCOLYMP` is in the top folder of the card, that it holds only `E1019999.BIN`, and that you held **OK** before you switched the camera on.

To go back to the original firmware, see [docs/install.md](docs/install.md).

![Nine photos, each developed in the camera with stock Natural and the film looks](docs/images/film-sim-comparison.jpg)

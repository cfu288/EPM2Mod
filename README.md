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

[uv](https://docs.astral.sh/uv/getting-started/installation/), to run the build script. It gets Python for you.

## Install

For an E-PM2 with firmware 1.6 (**Setup Menu → Firmware**). Unofficial, at your own risk. Use a full battery: an update that stops part-way can leave the camera unusable.

1. To build a copy of the firmware, run

   ```sh
   uv run tools/make_firmware.py
   ```

   This downloads the Olympus firmware, applies the patches and writes `build/card/DCOLYMP/E1019999.BIN`.
2. Copy the folder `build/card/DCOLYMP` to the top folder of an SD card, beside `DCIM`. `E1019999.BIN` must be the only file in `DCOLYMP`. With `--out /path/to/card`, the command of step 1 makes this copy: then eject the card.
3. Card in, camera off. Hold **OK** and switch the camera on. An orange lamp lights:
   - **Steady, 1 to 2 minutes:** the camera writes the firmware. Do not switch it off or open the battery door.
   - **Blinking:** done. It blinks until you switch the camera off. Switch it off, then on.
4. Check, in P, A, S or M mode: **OK → Picture Mode**, right past Custom, shows **Portra 400**.

If the camera starts as usual in step 3, it wrote nothing. Check that `DCOLYMP` is in the top folder of the card and holds only `E1019999.BIN`, and that **OK** was held before you switched on.

To go back to the original firmware: [docs/install.md](docs/install.md).

![Nine photos, each developed in the camera with stock Natural and the film looks](docs/images/film-sim-comparison.jpg)

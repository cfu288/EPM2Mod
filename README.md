# EPM2Mod

![Olympus PEN E-PM2](docs/images/epm2.jpg)

Repository containing the current work for creating a custom firmware mod for the Olympus PEN **E-PM2**. The goal is to unlock or add new features to this camera. Currently, we've implemented replacing the default art filters with film simulations like Portra, Ektachrome, etc. We also enabled interval shooting (up to 240 shots) and added a level gauge and focus peaking.

| Feature | Guide | Status |
|---|---|---|
| Film looks | [docs/guide/film-looks.md](docs/guide/film-looks.md) | Tested on the camera |
| Interval shooting | [docs/guide/interval-shooting.md](docs/guide/interval-shooting.md) | Tested on the camera |
| Level gauge | [docs/guide/level-gauge.md](docs/guide/level-gauge.md) | Tested on the camera |
| Focus peaking | [docs/guide/focus-peaking.md](docs/guide/focus-peaking.md) | Tested on the camera |

## Install

For an E-PM2 with firmware 1.6 only. Use it at your own risk.

1. Build the firmware: `uv run tools/make_firmware.py`. It downloads the Olympus firmware, applies the patches and writes `build/card/DCOLYMP/E1019999.BIN`.
2. Copy that file to the SD card with the same folder and name: `DCOLYMP/E1019999.BIN`, with `DCOLYMP` in the top folder of the card. (`--card /path/to/card` on the command of step 1 does this copy.)
3. With the camera off, hold **OK** and switch the camera on. The update takes about one minute.

Checksums and how to go back to the original firmware: [docs/install.md](docs/install.md).

![Nine photos, each developed in the camera with stock Natural and the film looks](docs/images/film-sim-comparison.jpg)

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

For an E-PM2 with firmware 1.6. You need [uv](https://docs.astral.sh/uv/getting-started/installation/), an SD card and a full battery. Use this firmware at your own risk.

1. Get this repository (**Code → Download ZIP**, or `git clone`) and open a terminal in its folder.
2. Put the SD card in the computer. Run `uv run tools/make_firmware.py --card /Volumes/NAME` with the location of the card. The script downloads the maker's firmware, applies the patches, checks the result and writes it to the card.
3. Put the card in the camera. With the camera off, hold **OK** and switch the camera on.
4. The lamp is orange for about one minute. When it blinks, switch the camera off and on.

Checksums, how to go back to the original firmware, and recovery: [docs/install.md](docs/install.md). For developers: [docs/conventions.md](docs/conventions.md).

![Nine photos, each developed in the camera with stock Natural and the film looks](docs/images/film-sim-comparison.jpg)

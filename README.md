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

```sh
uv run tools/make_firmware.py --card /Volumes/NAME
```

This command makes the patched firmware from Olympus's own file and writes it to your SD card. Put the card in the camera, hold **OK**, and switch the camera on. For an E-PM2 with firmware 1.6, at your own risk. More: [docs/install.md](docs/install.md).

![Nine photos, each developed in the camera with stock Natural and the film looks](docs/images/film-sim-comparison.jpg)

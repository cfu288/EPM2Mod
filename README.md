<h1><img src="docs/images/banner.png" alt="EPM2Mod"></h1>

Repository containing the current work for creating a custom firmware mod for the Olympus PEN **E-PM2**. We've implemented the ability to swap the default art filters with film simulations like Portra, Ektachrome, etc. You can choose which ones to load with the installer. See them compared on [our site](https://cfu288.github.io/EPM2Mod/films). We also enabled interval shooting (up to 240 shots), added a level gauge, focus peaking, and a lowest shutter speed setting for ISO Auto.

> This project was created with heavy use of AI assistance.

## Added Features

| Feature | |
|---|---|
| [Film simulations](docs/guide/film-looks.md) | <img src="docs/images/ui/quick-menu-portra.png" width="240" alt="The quick menu with Picture Mode on Portra 400"> |
| [Interval shooting](docs/guide/interval-shooting.md) | <img src="docs/images/ui/time-lapse-settings.png" width="240" alt="The Time Lapse Settings screen"> |
| [Level gauge](docs/guide/level-gauge.md) | <img src="docs/images/ui/level-gauge.png" width="240" alt="The level gauge in live view"> |
| [Focus peaking](docs/guide/focus-peaking.md) | <img src="docs/images/ui/peaking-list.png" width="240" alt="Custom Menu A with the Peaking list"> |
| [Lowest shutter speed for ISO Auto](docs/guide/lowest-shutter-speed.md) | <img src="docs/images/ui/lowest-ss-list.png" width="240" alt="Lowest S/S Setting set to 1/15"> |

[![Nine photos, each developed in the camera with Natural and the film simulations](docs/images/film-sim-comparison.jpg)](https://cfu288.github.io/EPM2Mod/films)

## Landscape of Olympus Custom Firmware

The E-PM2 came out in 2012. The [landscape page](docs/reference/landscape.md) lists the other Olympus custom firmware projects we know of.

[![A timeline of Olympus and OM SYSTEM cameras that have custom firmware projects, from the E-PL3 in 2011 to the OM-5 Mark II in 2025](docs/images/landscape.png)](docs/reference/landscape.md)

## Install

This firmware is only for an E-PM2. The firmware is unofficial, use it at your own risk. Ensure your battery is full prior to flashing. You can either use the installer or the CLI/command line. CLI is preferred.

### Using the installer

Download the zip from [Releases](https://github.com/cfu288/EPM2Mod/releases), unzip it, and double-click **Start (Mac).command** or **Start (Windows).bat** (Linux: `./start.sh`). Follow the page that opens. On a Mac, the first start is blocked: allow it in System Settings → Privacy & Security → **Open Anyway**.

### Using the command line

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and [git](https://git-scm.com/downloads).

Format the card in the camera and put it in the computer (`uv run epm2mod cards` shows its folder). Then:

```sh
git clone https://github.com/cfu288/EPM2Mod.git && cd EPM2Mod
uv run epm2mod install --card /path/to/card --film ART1=portra-400 --film ART2=ektachrome --film ART3=pro-400h --film ART4=kodachrome --film ART5=double-x --film ART6=vision3-250d --film ART7=velvia --film ART8=superia-400 --film ART9=provia --film ART10=portra-160 --film ART11=gold-200 --film ART12=vision3-500t
```

Do the steps that `install` prints. To use other film simulations, change the names ([film table](docs/guide/film-looks.md#available-film-simulations)).

To go back to the original firmware, see [docs/user/install.md](docs/user/install.md).


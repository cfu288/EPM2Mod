# EPM2Mod

![Olympus PEN E-PM2](docs/images/epm2.jpg)

Repository containing the current work for creating a custom firmware mod for the Olympus PEN **E-PM2**. We've implemented the ability to swap the default art filters with film simulations like Portra, Ektachrome, etc. You can choose which ones to load with the installer. See them compared on [our site](https://cfu288.github.io/EPM2Mod/films). We also enabled interval shooting (up to 240 shots), added a level gauge, focus peaking, and a lowest shutter speed setting for ISO Auto.

## Added Features

| Feature | 
|---|
| [Film simulations](docs/guide/film-looks.md) |
| [Looks from the SD card](docs/guide/card-looks.md) |
| [Interval shooting](docs/guide/interval-shooting.md) | 
| [Level gauge](docs/guide/level-gauge.md) | 
| [Focus peaking](docs/guide/focus-peaking.md) | 
| [Debug log](docs/guide/debug-log.md) |
| [Lowest shutter speed for ISO Auto](docs/guide/lowest-shutter-speed.md) |

## Dependencies

- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Install

This firmware is only for an E-PM2. The firmware is unofficial, use it at your own risk. Ensure your battery is full prior to flashing. You can either use the installer or the CLI/command line. CLI is preferred.

### Using the installer

Download the zip from [Releases](https://github.com/cfu288/EPM2Mod/releases), unzip it, and double-click **Start (Mac).command** or **Start (Windows).bat** (Linux: `./start.sh`). Follow the page that opens. On a Mac, the first start is blocked: allow it in System Settings → Privacy & Security → **Open Anyway**.

### Using the command line

1. To build a copy of the firmware, run

   ```sh
   uv run epm2mod make
   ```

   This downloads the Olympus firmware, applies the patches and writes `build/card/DCOLYMP/E1019999.BIN`.

   Alternatively, build and install the firmware directly to the SD card (allowing you to skip step 2)

   ```sh
   uv run epm2mod make --card /path/to/card
   ```

   Both also write `EPM2LOOK.BIN` with the 12 default film simulations, as the installer does. To choose others, write the look file again after `make`. Put a film simulation in each ART slot: ART1 is the first entry of the camera's ART menu (Pop Art), ART12 the last (Watercolor). The names are in the [film table](docs/guide/film-looks.md#available-film-simulations), or run `uv run epm2mod looks list`. A slot you leave out keeps its Olympus art filter:

   ```sh
   uv run epm2mod looks pack ART1=portra-400 ART2=ektachrome ART3=pro-400h ART4=kodachrome ART5=double-x ART6=vision3-250d ART7=velvia ART8=superia-400 ART9=provia ART10=portra-160 ART11=gold-200 ART12=vision3-500t --card /path/to/card
   ```
2. Copy the folder `build/card/DCOLYMP` and the file `build/card/EPM2LOOK.BIN` (the 12 default films) to the top folder of an SD card, beside `DCIM`. `E1019999.BIN` must be the only file in `DCOLYMP`.
3. Put the card in the camera. With the camera off, hold **OK** and the **ON/OFF** button together. When the orange lamp on the front of the camera (the AF illuminator) lights steadily, let go of both.
   - While the lamp is steady, the camera is writing the firmware. This takes 1 to 2 minutes. Do not switch the camera off.
   - When the lamp blinks, the update is done. Switch the camera off and on again.
4. To load the film simulations: MENU → Custom Menu → J → **Load Looks** → **Load** → OK ([more](docs/guide/card-looks.md)).

To go back to the original firmware, see [docs/install.md](docs/install.md).

![Nine photos, each developed in the camera with stock Natural and the film simulations](docs/images/film-sim-comparison.jpg)

> This project was created with heavy use of AI assistance.

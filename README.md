# EPM2Mod

![Olympus PEN E-PM2](docs/images/epm2.jpg)

Repository containing the current work for creating a custom firmware mod for the Olympus PEN **E-PM2**. We've implemented the ability to swap the default art filters with film simulations like Portra, Ektachrome, etc. You can choose which ones you want to load via our [ film looks page](https://cfu288.github.io/EPM2Mod/) to download the looks you want. We also enabled interval shooting (up to 240 shots), added a level gauge, and added focus peaking.

## Added Features

| Feature | 
|---|
| [Film simulations](docs/guide/film-looks.md) |
| [Looks from the SD card](docs/guide/card-looks.md) |
| [Interval shooting](docs/guide/interval-shooting.md) | 
| [Level gauge](docs/guide/level-gauge.md) | 
| [Focus peaking](docs/guide/focus-peaking.md) | 

## Install

This firmware is only for an E-PM2. The firmware is unofficial, use it at your own risk. Ensure your battery is full prior to flashing.

There are two ways to install. Both make the same firmware.

### Installer

Download the zip from [Releases](https://github.com/cfu288/EPM2Mod/releases), unzip it, and double-click **Start (Mac).command** or **Start (Windows).bat** (Linux: `./start.sh`). Follow the page that opens.

On a Mac, the first start is blocked: allow it in System Settings → Privacy & Security → **Open Anyway**.

### Command line

For developers. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/).

1. To build a copy of the firmware, run

   ```sh
   uv run tools/make_firmware.py
   ```

   This downloads the Olympus firmware, applies the patches and writes `build/card/DCOLYMP/E1019999.BIN`.

   Alternatively, build and install the firmware directly to the SD card (allowing you to skip step 2)

   ```sh
   uv run tools/make_firmware.py --card /path/to/card
   ```
2. Copy the folder `build/card/DCOLYMP` to the top folder of an SD card, beside `DCIM`. `E1019999.BIN` must be the only file in `DCOLYMP`.
3. Optional, your own film looks: `uv run epm2mod looks list` shows the films. Pick one for any ART number and write the file to the card:

   ```sh
   uv run epm2mod looks pack ART2=velvia ART6=double-x --card /path/to/card
   ```
4. Put the card in the camera. With the camera off, hold **OK** and the **ON/OFF** button together. When the orange lamp on the front of the camera (the AF illuminator) lights steadily, let go of both.
   - While the lamp is steady, the camera is writing the firmware. This takes 1 to 2 minutes. Do not switch the camera off.
   - When the lamp blinks, the update is done. Switch the camera off and on again.
5. If you packed film looks: MENU → Custom Menu → J → **Load Looks** → **Load** → OK. See [Looks from the SD card](docs/guide/card-looks.md).

To go back to the original firmware, choose **Olympus original** in the installer, or see [docs/install.md](docs/install.md).

![Nine photos, each developed in the camera with stock Natural and the film looks](docs/images/film-sim-comparison.jpg)

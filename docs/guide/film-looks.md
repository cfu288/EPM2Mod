# Film Simulations

The camera comes with the Olympus art filters. Load Looks puts the film simulations in their place. They work for
photos and live view.

## Usage

Install with the installer, which puts the film simulations on the SD card. Then MENU → SETUP → Custom Menu → J → **Load Looks** →
**Load** → OK ([more](card-looks.md)).

In P, A, S or M mode, press **OK**, select **Picture Mode**, and scroll right past Custom. The film simulations are also in the **ART** mode list.

<img src="../images/ui/quick-menu-portra.png" width="320" alt="The quick menu with Picture Mode on Portra 400">

## Available Film Simulations

<!-- BEGIN GENERATED: films -->
| Menu name | Command-line name | Film | Type |
|---|---|---|---|
| Portra 400 | `portra-400` | Kodak Portra 400 (negative, on Kodak Portra Endura paper) | Colour negative |
| Ektachrome | `ektachrome` | Kodak Ektachrome 100 (slide) | Slide |
| Pro 400H | `pro-400h` | Fujifilm Pro 400H (negative, on Fuji Crystal Archive paper) | Colour negative |
| Kodachrome | `kodachrome` | Kodak Kodachrome 64 (slide) | Slide |
| Double-X | `double-x` | Kodak Double-X 5222 (black-and-white negative, on Kodak 2302 print film) | Black and white |
| Vis 250D | `vision3-250d` | Kodak Vision3 250D (cinema negative, on Kodak 2383 print film) | Cinema, daylight |
| Velvia | `velvia` | Fujifilm Velvia 100 (slide) | Slide |
| Superia 400 | `superia-400` | Fujifilm Superia X-tra 400 (negative, on Fuji Crystal Archive paper) | Colour negative |
| Provia | `provia` | Fujifilm Provia 100F (slide) | Slide |
| Portra 160 | `portra-160` | Kodak Portra 160 (negative, on Kodak Portra Endura paper) | Colour negative |
| Gold 200 | `gold-200` | Kodak Gold 200 (negative, on Fuji Crystal Archive paper) | Colour negative |
| Vis 500T | `vision3-500t` | Kodak Vision3 500T (cinema negative, on Kodak 2383 print film) | Cinema, tungsten light |
| Ektar 100 | `ektar-100` | Kodak Ektar 100 (negative, on Kodak Portra Endura paper) | Colour negative |
| Portra 800 | `portra-800` | Kodak Portra 800 (negative, on Kodak Portra Endura paper) | Colour negative |
| Portra 800 +1 | `portra-800-push1` | Kodak Portra 800, pushed 1 stop (negative, on Kodak Portra Endura paper) | Colour negative, approximate colours |
| Portra 800 +2 | `portra-800-push2` | Kodak Portra 800, pushed 2 stops (negative, on Kodak Portra Endura paper) | Colour negative, approximate colours |
| Tri-X | `tri-x` | Kodak Tri-X Reversal 7266 (black-and-white reversal film) | Black and white |
| C200 | `c200` | Fujifilm C200 (negative, on Fuji Crystal Archive paper) | Colour negative |
| UltraMax 400 | `ultramax-400` | Kodak UltraMax 400 (negative, on Kodak Portra Endura paper) | Colour negative |
| Verita 200D | `verita-200d` | Kodak Verita 200D (cinema negative, on Kodak 2383 print film) | Cinema, daylight |
| Vis 50D | `vision3-50d` | Kodak Vision3 50D (cinema negative, on Kodak 2383 print film) | Cinema, daylight |
| Vis 200T | `vision3-200t` | Kodak Vision3 200T (cinema negative, on Kodak 2383 print film) | Cinema, tungsten light |
<!-- END GENERATED: films -->

## Limits

- The simulations change colour and tone only. There is no halation and no grain.
- There is no colour wheel. The camera has a 12-colour stage for photos only (not live view or movies), and EPM2Mod does not change it ([more](../feasibility.md#colour-wheel-and-twelve-colour-editors)).
- You can choose another film simulation for any of them: [Film simulations from the SD card](card-looks.md).
- Movies only get part of each simulation.
- Filter Type and Add Effects are not tested with the film simulations.
- An ART entry that has a film simulation does not have its Olympus art filter. To get the art filter back, load a file that does not list that entry ([more](card-looks.md)).

For how the simulations were made and measured, see [film emulation](../film-emulation.md).

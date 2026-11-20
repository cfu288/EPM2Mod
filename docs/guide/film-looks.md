# Film Simulations

The camera comes with the Olympus art filters. A film file on the SD card puts a film simulation in each ART entry it
lists. The camera keeps them, with their names, after power-off and without the card. They work for photos and live
view.

## Usage

1. Put the film file on the card with the installer, or on the command line with `--film`
   ([install](../../README.md#using-the-command-line)). To change only the film simulations later:
   `uv run epm2mod films set --card /path/to/card --film ART2=velvia`.
2. MENU → SETUP → Custom Menu → J → **Load Looks** → **Load** → OK. The row reads Loading, then **Loaded**.

   <img src="../images/ui/load-looks-list.png" width="320" alt="Load Looks with Off and Load">
   <img src="../images/ui/load-looks-loaded.png" width="320" alt="Load Looks reads Loaded">
3. In P, A, S or M mode, press **OK**, select **Picture Mode**, and scroll right past Custom. The film simulations
   are also in the **ART** mode list.

   <img src="../images/ui/quick-menu-portra.png" width="320" alt="The quick menu with Picture Mode on Portra 400">

Each Load replaces the last one: an ART entry the file leaves out goes back to its Olympus art filter.

A photo taken with a film simulation records the film's name in its metadata (EXIF Image Description, the caption in
Lightroom) and its art filter as Off. RAW Data Edit keeps the name that the RAW file has.

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
| Velvia 50 | `velvia-50` | Fuji Velvia 50 (slide) | Slide |
| Natura 1600 | `natura-1600` | Fuji Natura 1600 (negative, on Fuji Crystal Archive paper) | Colour negative |
| Pro 160S | `pro-160s` | Fuji Pro 160S (negative, on Fuji Crystal Archive paper) | Colour negative |
| Superia Reala | `superia-reala` | Fuji Superia Reala (negative, on Fuji Crystal Archive paper) | Colour negative |
| Agfa Vista 100 | `agfa-vista-100` | Agfa Vista 100 (negative, on Kodak Portra Endura paper) | Colour negative |
| Vericolor III | `vericolor-iii` | Kodak Vericolor III (negative, on Kodak Portra Endura paper) | Colour negative |
| Aerocolor IV | `aerocolor-iv` | Kodak Aerocolor IV 2460 (aerial negative, on Kodak Portra Endura paper) | Colour negative |
| Eterna 500 | `eterna-500` | Fuji Eterna 500 (cinema negative, on Fuji Eterna-CP 3513DI print film) | Cinema, tungsten light |
| EXR 200T | `exr-200t` | Kodak EXR 200T 5293 (cinema negative, on Kodak 2383 print film) | Cinema, tungsten light |
| FP-100C | `fp-100c` | Fuji FP-100C (instant peel-apart film) | Instant |
<!-- END GENERATED: films -->

## Limits

- The simulations change colour and tone only. There is no halation and no grain.
- There is no colour wheel. The camera has a 12-colour stage for photos only (not live view or movies), and EPM2Mod does not change it ([more](../dev/feasibility.md#colour-wheel-and-twelve-colour-editors)).
- Movies only get part of each simulation.
- Filter Type and Add Effects are not tested with the film simulations.
- The Load Looks row's texts are English in every menu language.

How the simulations were made and measured: [film emulation](../dev/film-emulation.md). The file format:
[look-file-format.md](../reference/look-file-format.md).

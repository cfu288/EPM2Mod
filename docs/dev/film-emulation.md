# Film simulations: how they are made and measured

A film simulation is a set of numbers for the camera's own colour stages (matrix, six-axis, tone curves, saturation,
chroma curves), fitted so that the camera's JPEG matches a simulation of the film. The firmware keeps Olympus's 12
art filters; a film file on the SD card puts a film into the ART entries it lists
([guide](../guide/film-looks.md)). The stages and how a film reaches them: [colour-pipeline.md](colour-pipeline.md).
The lab notes: `experiments/2026-11-09-film-portra/NOTES.md` (method, model) and
`experiments/2026-11-20-film-camera-round/NOTES.md` (the latest round); every flash is in the
[camera log](../camera-log/README.md).

The catalogue has 32 films (`data/films/catalogue.json`). 22 are fitted to simulations of **spektrafilm**
(CC BY-SA 4.0), 10 to **Spectral Film LUT** (MIT); the second simulator renders the same film differently (ΔE 5–9),
so its films carry the note "simulated with Spectral Film LUT" (`experiments/2026-11-19-film-sources/NOTES.md`).
No grain, halation or other texture: only colour and tone.

## 1. What "accurate" means

**The target.** For each film, a 3-D table that says which output colour each input colour should give: the
simulator's rendering of the film (a negative printed on its paper or print film, a slide viewed directly), with
V-Log/V-Gamut input and sRGB output. It is a simulation, not a scan of real film: everything below measures how
close the camera comes to the simulation, not how close the simulation is to the film.

**The score.** For each colour patch, the difference between the camera's colour and the target's in **ΔE**
(CIEDE2000):

| ΔE | What it looks like |
|---|---|
| below 1 | no visible difference, even side by side |
| 1 to 2 | visible only side by side, if you look for it |
| 2 to 3 | visible at a glance side by side |
| 5 and up | clearly a different colour |

A group's score ("natural colours 1.2") is the mean over its patches.

## 2. How a film is measured: a synthetic test RAW

Photographing charts brings errors as large as what is measured (light, lens, patch finding, white balance). We give
the camera a **synthetic RAW** instead: a file in its own raw format with every pixel value known
(`experiments/2026-11-09-film-portra/testraw/`, made by `make_mock2.py` with our encoder `orfcodec.py` and a real
photo's header, owner name and serial blanked).

1. Put the film on the card (a film file, `epm2mod films set` or `films pack`) and the RAW in `DCIM/100OLYMP/`.
2. On the camera: Load Looks; for each ART entry, choose it as Picture Mode, then RAW Data Edit → [Current] on the RAW.
   The camera writes a JPEG as it would for a photo with that film.
3. `read_mock.py` finds each patch (it undoes the camera's lens distortion correction) and reads its colour, and the
   white balance and colour matrix the camera applied (EXIF).
4. `check_film.py` scores the JPEG against the target and against the model's prediction.

The file never changes, so builds can be compared directly; two developments with one build give the same colours
(2026-11-20: pixel-equal).

`PB130001.ORF`, the main image:

| Group | Patches | Why |
|---|---|---|
| Natural colours | 3,535 | ordinary colours at ordinary brightness; the best single summary |
| Hold-out colours | 1,000 | ordinary colours the fitting never uses; an honesty check |
| Gray ramps | 644 | neutral tones from black to clipping; tints in shadows and highlights |
| Near-neutrals | 576 | almost-gray colours, where small tints show |
| ColorChecker at five exposures | 336 | the 24-colour chart, two stops under to two stops over |
| Skin series | 45 | skin tones from dark to bright |
| Edge-of-gamut colours | 300 | extreme colours |
| Coarse colour cube, markers, repeats | about 480 | coverage, patch location, uniformity |

`PB130002.ORF` is two thirds sky and sea blue and one third repeats of the main patches: some processing depends on
the whole picture, and a film free of it gives the repeats the same colours in both files.

What it cannot test: real light and spectra (the patches are written as camera raw values under one light), the
processing of real scenes (flat patches: no noise reduction, sharpening or local contrast), live view and movies.

## 3. How a film is fitted

1. **Model fit.** A model of the camera (`model2.py`: it predicts the JPEG of any raw input for given stage values)
   is fitted to the target with no camera involved: `fit_film2.py --lut TARGET --name NAME`. The model's constants
   come from developments of the test RAW alone (`calib/model2.npz`); it predicts the stock picture modes to about
   0.9 ΔE.
2. **Camera reading.** Develop the test RAW with the film, read it.
3. **Correction.** Refit, predicting each patch as "what the camera measured, plus the change the model expects":
   `fit_film2.py --name NAME2 --anchor READING FIT.npz`. Only the change relies on the model. Develop again and score.

One correction is normally enough: a second round was predicted to gain 0.1 or less for the films corrected so far.

## 4. Results (2026-11-20, all 32 films on `films-look-exif`)

Camera against target, ΔE2000, range over the films of each batch (`experiments/2026-11-20-film-camera-round/NOTES.md`
§7):

| Films | Natural colours | ColorChecker × 5 | Skin | Camera against model (natural) |
|---|---|---|---|---|
| 7 corrected in 2026-11 (Portra 400, Ektachrome, Pro 400H, Kodachrome, Vis 250D, Velvia, Superia 400) | 1.07–1.44 | 1.41–1.96 | 0.80–1.56 | 0.85–1.15 |
| 12 spektrafilm films corrected 2026-11-20 | 1.12–1.44 | 1.56–2.54 | 0.85–1.78 | 0.81–1.03 |
| Vis 200T, Tri-X, 10 Spectral Film LUT films, corrected 2026-11-20 | 0.80–1.24 | 1.48–2.40 | 0.32–1.38 | 0.17–0.97 |

Stock Natural against the same targets: 3.9–6.0 on natural colours. Double-X is scored in black and white: the camera
matches its model to 0.11, and the fit is 0.07 L* from its target.

How to read this:

- **Ordinary colours, skin and grays are at "visible only side by side" or better** for every film.
- **Saturated chart colours are the weak spot** (single patches 3 to 10 off, worst when overexposed): the six-axis
  stage cannot treat neighbouring hues or dark and bright colours separately. The 12-region stage could; it is being
  tested ([colour-pipeline.md](colour-pipeline.md) §3).
- **Edge-of-gamut colours stay 11 to 17 off** for every film (stock Natural 14 to 22): after the colour matrix one
  channel goes negative, the tone curves darken it and the camera caps chroma. A limit of the camera.
- **Floor:** about 0.8 on natural colours and 0.9 on grays (8-bit JPEG and the camera's rounding).
- **For scale:** a tenth of a stop of exposure moves the picture about 1.2; auto white balance drifting 2 % about 0.7.
- **Scene independence:** in the blue-scene test all 2,194 repeated patches matched the main image (Portra,
  Ektachrome, Pro 400H, 2026-11-12).
- **Weakest:** Portra 800 +1 and +2 (ColorChecker 2.2 and 2.5; their catalogue note says "less accurate"), and
  among the Spectral Film LUT films Natura 1600, FP-100C, Vericolor III and Agfa Vista 100 (ColorChecker 2.3–2.4).

## 5. Limits and open points

- The films match a **simulation**; nobody has compared them with real film here.
- No grain or halation.
- Live view and movies show the film (camera-tested 2026-11-18) through stages 1 to 6 only; how close they are to the
  photo is not measured.
- White balance presets Shade (7500 K) and Incandescent (3000 K) were measured, and the films hold
  (`experiments/2026-11-09-film-portra/NOTES.md` §44).
- RAW Data Edit froze and restarted the camera twice (2026-11-12): one cause was found and fixed (`seven-fixes-1`);
  the other is open (camera log).
- Deep shadows are a little darker than negative-film targets ask for (lifted blacks are not fully reproduced).
- A photo records the film's name in ImageDescription; RAW Data Edit keeps the RAW's own name.

## 6. Adding or changing a film

1. **Target:** `spektrafilm-lut build --film F --print P --input vlog --output srgb --resolution 33` for a negative
   with its print (`bake_slide.py` for a slide), or Spectral Film LUT for a film spektrafilm does not have
   (`experiments/2026-11-19-film-sources/scripts/sfl_build.py`, same input and output).
2. **Fit:** `fit_film2.py --lut TARGET --name NAME --edge-weight 0.25`.
3. **Try it on the camera without the catalogue:** `uv run epm2mod films pack LIST -o EPM2LOOK.BIN` from a look list
   of fit files; develop the test RAW with it; read and score it.
4. **Correct** from that reading (§3) and check again.
5. **Add it:** the fit in `data/films/fits/` (a new file name when a firmware spec already uses the old one), an entry
   in `data/films/catalogue.json`, then `uv run python web/scripts/export_films.py`, `web/scripts/render_previews.py`
   (the name picture of the menu strip) and `uv run epm2mod generate`.

To return to the original firmware, flash `firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN`.

# Film looks on the Olympus E-PM2: what we built, how we measured it, what we learned

Plain-language summary, written 2026-11-12. The detailed lab notes are in
`experiments/2026-11-09-film-portra/NOTES.md`; the technical slot reference is
[`art-filter-slots.md`](art-filter-slots.md); every flash is logged in [`camera-log.md`](camera-log.md).

## 1. What we built

A modified firmware (version 1.6 base) in which seven of the camera's twelve art filters are replaced
by film looks. They are ordinary menu entries: pick one and the camera writes the JPEG with that
look. Live view shows it too.

| Menu entry (top to bottom) | Was | Film look |
|---|---|---|
| **Portra** | Pop Art | Kodak Portra 400 negative, printed on Kodak Portra Endura paper |
| **Ektachrome** | Soft Focus | Kodak Ektachrome 100 slide film |
| **Pro 400H** | Pale&Light Color | Fuji Pro 400H negative, printed on Fuji Crystal Archive paper |
| **Kodachrome** | Light Tone | Kodak Kodachrome 64 slide film |
| Grainy Film | (unchanged) | |
| **Vis 250D** | Pin Hole | Kodak Vision3 250D cinema negative, printed on Kodak 2383 print film |
| **Velvia** | Diorama | Fuji Velvia 100 slide film |
| **Superia 400** | Cross Process | Fuji Superia X-tra 400 negative, printed on Fuji Crystal Archive paper |
| Gentle Sepia, Dramatic Tone, Key Line, Watercolor | (unchanged) | |

Current build on the camera: `build/seven-films-2.BIN`, built with

```
python3 tools/build.py patches/remap7b-code.json patches/slot3-chroma-linear.json \
    patches/seven-structure-extra.json patches/seven-films-2.json \
    patches/xp-adaptive-hue-off.json patches/seven-labels.json -o build/seven-films-2.BIN
```

Earlier and failed patch specs are kept in `patches/history/` as a record; do not build from them
without reading the camera log.

What a look is made of: the camera has no "film" feature and no general colour lookup table. Each
look is assembled from the adjustable parts the camera already has: a colour-mixing matrix,
separate brightness curves for red, green and blue, twelve per-colour saturation and hue values, an
overall saturation setting and a brightness curve. We replace the numbers in those parts.

Not included: film grain, halation (the glow around bright lights) or any other texture. Only
colour and tone.

## 2. What "accurate" means here

### The target
For each film we need a reference that says "this input colour should come out as that output
colour". We take it from **spektrafilm**, an open-source program that simulates film from
measured film data (how each layer responds to light, how the dyes look, how the print paper
responds). It gives a table covering all colours. That table is the target.

- Negatives (Portra, Pro 400H) are simulated as film printed on photographic paper.
- Slide film (Ektachrome) is simulated as the slide viewed directly. The stock tool only does
  negative-plus-paper, so we run it with the slide scanned directly instead (`bake_slide.py`).

The target is a simulation, not a scan of real film. Everything below measures how well the camera
matches the simulation. It says nothing about how faithful the simulation is to the real film.

### The score
For one colour patch, we compare the colour the camera produced with the colour the target says it
should be. The difference is expressed in **ΔE** ("delta E", the CIEDE2000 formula), a standard
measure of how different two colours look to a person. The usual rule of thumb:

| ΔE | What it looks like |
|---|---|
| below 1 | no visible difference, even side by side |
| 1 to 2 | visible only side by side, if you look for it |
| 2 to 3 | visible at a glance side by side |
| 5 and up | clearly a different colour |

A score such as "natural colours 1.3" is the average ΔE over all patches in that group.

## 3. How we measure: one synthetic test photo

We do not photograph charts. Photographing introduces errors of its own (lighting, lens, patch
finding, white balance drift), and those errors were as large as what we were trying to measure.

Instead we give the camera a **synthetic RAW file**: a file in the camera's own raw format that we
generate ourselves, in which every pixel value is known exactly.

1. **Make the file** (`make_mock2.py`). It contains 6,912 flat colour patches, 96 across and 72
   down. The camera's raw compression is reproduced by our own encoder (`orfcodec.py`), and the
   file borrows its header from a real photo so the camera accepts it.
2. **Develop it in the camera.** The camera has a built-in function, RAW Data Edit, that re-develops
   a raw file on the card using the current settings. Select a film look, run RAW Data Edit on the
   test file, and the camera writes a JPEG exactly as it would for a real photo with that look.
3. **Read the JPEG** (`read_mock.py`). The program finds each patch (it corrects for the lens
   distortion correction the camera applies) and reads its colour. It also reads, from the JPEG's
   metadata, the white balance and colour matrix the camera actually applied.
4. **Score it** against the target, patch by patch (`analyze_mock2.py`, `check_film.py`).

Because the file never changes, results from different firmware builds can be compared directly,
and two developments of it with the same build give the same colours.

### What is in the test file
`PB130001.ORF`, the main image:

| Group | Patches | Why |
|---|---|---|
| Natural colours | 3,535 | ordinary colours at ordinary brightness; the best single summary |
| Hold-out colours | 1,000 | ordinary colours the fitting never uses; an honesty check |
| Gray ramps | 644 | neutral tones from black to clipping; shows tints in shadows and highlights |
| Near-neutrals | 576 | almost-gray colours, where small tints are easy to see |
| ColorChecker at five exposures | 336 | the standard 24-colour chart, from two stops under to two stops over |
| Skin series | 45 | skin tones from dark to bright |
| Bright edge-of-gamut colours | 300 | extreme colours, to see where the camera misbehaves |
| Coarse colour cube, markers, repeats | about 480 | coverage, patch location, uniformity check |

`PB130002.ORF`, the "blue scene" image: two thirds sky and sea blue, one third patches repeated
from the main image. Some camera processing depends on what is in the whole picture. If a look is
free of that, the repeated patches must come out the same in both images.

### How a look is fitted
1. A **model** of the camera (a program that predicts the JPEG colour for any input and any
   settings) is fitted to the target with no camera involved. The model is calibrated against the
   camera's own stock modes on the test file and predicts them to about 0.9 ΔE.
2. Flash, develop the test file, measure.
3. **One correction round:** refit, this time predicting each patch as "what the camera measured,
   plus the change the model expects". Only the change relies on the model. Flash and measure again.

Two flashes per film is normally enough.

## 4. Results

Camera versus target, average ΔE, measured with the test file:

| Group | Portra | Ektachrome | Pro 400H | Kodachrome | Vis 250D | Velvia | Superia 400 | Camera's Natural mode vs the same targets |
|---|---|---|---|---|---|---|---|---|
| Natural colours | 1.33 | 1.36 | 1.19 | 1.07 | 1.22 | 1.52 | 1.39 | about 3.5 to 6 |
| Hold-out colours | 1.35 | 1.36 | 1.22 | 1.11 | 1.24 | 1.52 | 1.39 | about 3.5 to 6 |
| Skin series | 1.36 | 1.35 | 1.14 | 0.97 | 1.13 | 1.68 | 1.56 | about 5 |
| Grays | 0.98 | 0.77 | 0.61 | 0.89 | 0.74 | 0.79 | 0.74 | about 3 to 5 |
| Near-neutrals | 1.08 | 1.04 | 0.92 | 0.86 | 0.91 | 1.06 | 1.10 | about 4.5 |
| ColorChecker, five exposures | 2.58 | 2.24 | 2.33 | 1.79 | 2.71 | 2.50 | 2.66 | about 5 to 7 |

Each film had one model-only first fit and one correction round against its own measurement
(Portra and Ektachrome had more while the method was being developed).

How to read this:

- **Ordinary colours, skin and grays are at "visible only side by side" or better** for all seven.
- **Strongly saturated chart colours are the weak spot** (individual patches 3 to 10 off, worst when
  overexposed). This is a limit of the camera's adjustable parts, not of the tuning: the model
  predicted most of it.
- **Very bright, extreme colours** (pure cyan, pure green at high brightness) are far off, 13 and
  more. The camera compresses them in a way we have not modelled. Natural scenes rarely contain them.
- **There is a floor of about 0.8** on natural colours and about 0.9 on grays. The JPEG stores 256
  levels per channel and the camera rounds at several steps, so its output scatters by about one
  level around anything we ask for. Grays are already at that floor.
- **For scale:** exposing a tenth of a stop differently moves the picture by about 1.2; auto white
  balance drifting 2 % between shots, about 0.7.
- **Scene independence:** in the blue-scene test all 2,194 repeated patches matched the main image,
  for the three looks tested this way (Portra, Ektachrome, Pro 400H).

Against other open-source projects that rewrite a camera's own colour tables, the best
camera-measured figure we found was 1.32 (a Ricoh GR III project, on a different and harder chart).
The test sets differ, so this is only a rough comparison.

## 5. How the camera turns a menu entry into a look

A menu entry is just a number, the filter code (Pop Art is 70, Light Tone 72, Cross Process 85).
Nothing else is stored per entry. Six separate steps in the camera's image processing each look at
that number and choose their own settings:

| Step | What it does | How it chooses per filter |
|---|---|---|
| Colour matrix | mixes the three colour channels | four fixed comparisons in code, two matrices |
| Per-colour values | saturation and hue for six colour ranges | lookup table |
| Red, green, blue curves | brightness curve per channel | lookup table; only two entries give three *different* curves |
| Brightness curve | one curve on overall brightness | lookup table |
| Saturation | one overall strength | lookup table |
| Chroma curves | how weak and strong colours are treated | lookup table |

Three things follow from this:

1. **Entries are not interchangeable.** What an entry can do depends on which settings the stock
   firmware wired up for its number in each of the six steps.
2. **Re-pointing is easy, new parts are not.** A lookup can be pointed at another filter's settings,
   but then the two filters share them. A separate look needs its own set at every step.
3. **Other code reacts to the same number.** Some filters add effects after the colour processing.

## 6. What we found about each filter

| Menu entry | Finding | Use as a film slot |
|---|---|---|
| Cross Process | Has separate red, green, blue curves built in. Also had a routine that shifts blue and cyan depending on how blue the scene is; we switched it off. | **Portra 400** |
| Light Tone | No hidden processing: the model reproduces its stock look to 0.94 ΔE. Has one type only, so the menu entry is the slot. | **Ektachrome** |
| Pop Art | Its code number could not get separate curves or its own matrix without new code. It also has S-shaped chroma curves that erase faint colour and boost strong colour; we replaced them with straight lines. | **Pro400H** (needed 120 bytes of new code) |
| Pale&Light | Shifts the white balance by itself, and has chroma curves that compress strong colour. The white balance change has not been located. | Not usable yet |
| Soft Focus | Adds blur in a separate effect program (visible on the test file). | No |
| Pin Hole, Diorama | Add vignette or blur the same way. | Only if the effect can be switched off |
| Grainy Film, Gentle Sepia | Monochrome, with grain or toning. | No |
| Dramatic Tone, Key Line, Watercolor | Effect programs. | No |

Other findings:

- **Types.** Some filters have a second type (Pop Art II, Pale&Light II, Cross Process II), chosen in
  ART mode with the right arrow. The quick menu only shows the twelve filters, so only the first
  type of each is practical as a slot.
- **The stock firmware has parts for exactly two full film looks:** two sets of separate
  red/green/blue curves and two matrices. Portra and Ektachrome use them.
- **The third look needed new code**, the first in this project: one routine that gives Pop Art three
  separate curves, and one that chooses the matrix for all three films. It fits in 164 unused bytes
  that the camera loads into memory. Its curve tables are borrowed from Pale&Light, Light Tone and
  Pop Art II.
- **Slots four to seven** use a second piece of new code that gives any listed filter number its
  own three curves and matrix. Pale&Light was converted in place. Soft Focus, Pin Hole and Diorama
  are *effect* filters (blur, vignette, tilt-shift), and removing an effect in place froze live
  view three times. What worked was leaving the effect filters alone and pointing their **menu
  entries** at other, colour-only filter numbers. The menu-entry-to-number table exists three
  times (stills, and twice in the live-view code); all three must agree or live view freezes.
  A test build with the same film in all the new slots produced pixel-identical files, so the
  seven slots are interchangeable.
- **Free space is scarce.** The firmware file has large empty areas, but they are gaps the camera
  never loads into memory. About 3.5 KB of loaded free space exists in total.
- **The camera rounds the colour matrix** in a specific way before using it, and records the result
  in each JPEG's metadata. Reproducing that rule lets us predict the recorded matrix exactly, which
  is a quick check that a build did what we intended.
- **The camera's "neutral" brightness curve is not neutral:** it compresses highlights. Every look
  that keeps it has to allow for that.
- **Menu labels** can be replaced only by text no longer than the original ("Velvia" for "Diorama"), which is why some names are abbreviated.

Side effects on entries we did not turn into films: the second types (Pop Art II, Pale&Light II, Cross Process II) lose their own look or share curves with a film, and the original Soft Focus, Pin Hole and Diorama stills effects are no longer reachable from the menu (their movie versions are).

## 7. Limits and open points

- The looks match a **simulation** of each film; nobody has compared them with real film here.
- No grain or halation.
- All measurements use the camera's daylight colour matrix. Other white balance settings
  (tungsten, shade) use different matrices and are untested.
- Live view works in all seven entries. **Movie mode is not converted**: in the Ektachrome,
  Vis 250D and Velvia entries a movie still gets the old Soft Focus / Pin Hole / Diorama effect.
- **Open problem:** twice the camera froze and restarted at the moment RAW Data Edit was about to
  save. It is not known whether the modified firmware, or the hand-made test file, is involved; it
  has not been tried on stock firmware. See the camera log.
- Art bracketing and other white balance presets are untested with the new entries.
- Deep shadows are a little darker than the film targets ask for (the lifted blacks of negative
  film are not fully reproduced).
- Seven is the practical limit. Grainy Film, Gentle Sepia, Dramatic Tone, Key Line and Watercolor
  have no low-risk route to becoming film slots ([`art-slots-evaluation.md`](art-slots-evaluation.md)).
- The menu order itself was not changed; films were assigned to the seven usable entries from the
  top down, which leaves Grainy Film in the middle.

## 8. Adding or changing a film

1. Make the target: `spektrafilm-lut build …` for a negative with a print paper, `bake_slide.py` for
   a slide film.
2. Fit: `fit_film.py --lut <target> --slot xp1 --name <name>`. The fitted numbers do not depend on
   the slot; the slot only decides where a stand-alone patch would write them.
3. Put the fit file into the `FILMS` table of `experiments/2026-11-09-film-portra/slots/build_seven_films.py`
   (and a label no longer than the entry's stock name), run it, build with `tools/build.py` as in
   section 1, flash, develop `PB130001.ORF` with that look, copy the JPEG back.
4. Correct: `fit_film.py … --anchor <measurement> <first fit> --robust 3`, rebuild, flash, check again.

Before using a new menu entry as a slot, develop the test file with its **stock** look first and
check that the model reproduces it to about 0.9 ΔE. A worse match means the entry has processing
we do not know about, which is how Pop Art's chroma curves would have been caught before a flash.

To return to the original firmware, flash `firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN`.

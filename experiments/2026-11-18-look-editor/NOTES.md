# Look editor and LUT import: research plan

Question (owner, 2026-11-18): with the hardware we have, can EPM2Mod give an editing experience and look import
like the PEN-F, E-P7, OM-3 and E-M10 I mods (Caduceus, oly_fw_analysis, om10mi-mods)? Not a 12-colour wheel (that
is a TruePic VII stage, see `docs/feasibility.md`, "Colour wheel and twelve colour editors"), but the same kind of
editor and `.cube` import, on the stages the E-PM2 has.

Status labels: V verified on the camera, E checked in the emulator, I inferred, U unknown.

## 1. What we start from

A look record (`docs/look-file-format.md`, 1,708 B) already holds every stage that can be edited:

| Stage | In the record | Editor controls it can carry | Status |
|---|---|---|---|
| 3x3 art matrix (rows sum 256) | yes | colour mix, white balance shift and tint, global saturation, a Color Creator-like hue turn | V (not cached, next photo) |
| Red, green, blue tone curves (1,024 points) | yes | contrast, Blacks, Whites, fade, RGB curves, split toning | V (stills); live view from card-looks-3 |
| Saturation gain | yes | saturation | V |
| Six-axis hue and saturation (R, Y, G, C, M, B) | yes | hue and saturation for 6 colours | V for the photo; model approximate on G, C, M (I) |
| Cb/Cr chroma curves | yes | saturation by brightness (shadows and highlights) | V |
| Lightness per colour | no stage | none | absent |
| 12-colour table, 3D LUT | no stage | none | absent (`docs/feasibility.md`) |
| Grain, glow, vignette | separate effect stages | maybe Add Effects on a film slot | U (`docs/todo.md`, Film looks) |

Tools that exist:

- The fitter `experiments/2026-11-09-film-portra/fit_film2.py` fits all stages at once to a `.cube` target with
  CIEDE2000 (weights: greys, ColorChecker, skin, natural colours). It assumes a V-Log input and an sRGB output.
- The forward model `experiments/2026-11-09-film-portra/model2.py` (`render`): about 0.9 dE against the camera on
  natural colours, near a rounding floor of about 0.8 (that experiment's NOTES section 46). It reads stock tables
  from the firmware (`mocklib.py`, BASE 0x7E74E9BC), so it cannot ship in a web page as it is.
- The test RAW (`make_mock2.py`, `orfcodec.py`) and RAW Data Edit as the camera measurement.
- Load Looks: a look file takes effect from the card with no flash (V, card-looks-4). The forced refresh of the
  cached stages works (V, `experiments/2026-11-17-card-looks/design.md` section 9.2.1).
- `log-card-probe`: LKP1 records that write any RAM range from a card file, plus the refresh flag. A RAM-poke
  harness that needs one flash, then only card files.
- The debug log (`docs/logging.md`): 31 to 66 B per probe point, `EPM2LOG.BIN` on the card.

## 2. Features by evidence

The owner's rule (2026-11-18): build first what can be confirmed deterministically at low effort, and tell users
only what is measured. A feature moves up a tier only with the evidence its tier asks for.

### Tier 1: ship. Camera-verified stages, inside measured ranges, no camera round needed

An editor in the installer that starts from one of the 19 film simulations and changes it with:

| Control | Stage | Why no new camera work |
|---|---|---|
| Warmth, tint | art matrix (diagonal) | V stage, not cached; a linear step: the EXIF ColorMatrix equals the prediction (V) |
| Saturation | saturation gain | V |
| Contrast, Blacks, Whites, fade | the three tone curves (same change on all three) | V for stills and live view; the camera builds its tables from the curve by a documented rule |

Limits that keep it in Tier 1: every control is clamped to the range the 19 fitted films already span (their
values were measured on the camera through RAW Data Edit); no six-axis control; output is a normal
`EPM2LOOK.BIN` for Load Looks, which is camera-verified (card-looks-4).

The preview runs on our own RAWs (the comparison scenes), decoded and white-balanced (daylight), through the
model's matrix, curve and saturation steps. What users are told: "Preview is approximate; the camera shows the
result after Load Looks." No accuracy number is shown until one is measured for these controls.

Desk work only: A1 (model and fitter into the package, with tests), A2 (tables from the user's own downloaded
firmware), A3 (the preview, matrix, curves and saturation only), A4 (controls and their clamps).

### Tier 2: one planned confirmation round, then ship

| Feature | Evidence needed | Round |
|---|---|---|
| Wider ranges than the films span | The camera's response at 1x, 2x and 4x the fitted range: clipping or wrapping | R1 |
| Hue and saturation for 6 colours | The six-axis stage at its extremes; the G, C, M and C-hue directions refitted | R1 |
| White balance presets other than daylight | Preview vs camera with 4 presets | R1 |
| A stated preview accuracy ("within N dE") | Preview vs camera on the test RAW for each control | R1 |

R1 is one visit, no flash: the pinned build, one look file with 12 slots, one RAW Data Edit of the test RAW per
slot (about 15 minutes). Pass marks are fixed before the visit: natural colours below 2 dE preview vs camera,
greys below 1 dE. A feature whose mark fails stays in Tier 2 or is dropped. If R1 shows an effect it was not
designed for, the smallest follow-up is written down with its gap; no open-ended re-runs.

### Tier 3: research. No user-facing claim until measured

| Feature | Why it is research | What would move it up |
|---|---|---|
| `.cube` import | A LUT does not say its input encoding; strong LUTs need stages this camera lacks (3D LUT, per-colour lightness); fit error varies per LUT | Fit 10 well-known LUTs (A6) and measure 3 on the camera (R2). If shipped: the user picks the encoding, the page shows that LUT's own fit error and the colours it cannot reach, and the text never says "any LUT" |
| `.xmp` import (Lightroom) | Parameters map only partly (8 HSL colours to 6 axes, no per-colour lightness) | A7, then the same rule as `.cube` |
| An editor on the camera | Run-time stage updates without refresh, free settings for rows, code space and lag are unknown | Track B probes, one probe flash (F1) |
| A hidden colour stage in TruePic VI | Not known to exist | C3 (static first, then slots in F1) |
| Add Effects (glow, vignette) as editor options | Not tried | One data-edit flash (F2) |

## 3. Track A details (installer editor)

| Step | Work | Pass mark | Tier |
|---|---|---|---|
| A1 | `model2.py` and the fitter into the package (`src/epm2mod/looks/model.py`, `fit.py`) with tests | Same output as the experiment code, dE difference below 0.05 | 1 |
| A2 | The model's stock tables from the user's own downloaded firmware, never from our files | Byte-equal to what `mocklib.py` reads | 1 |
| A3 | Preview in TypeScript on our comparison-scene RAWs | Browser vs Python model below 0.3 dE | 1 |
| A4 | Controls, clamps to the films' measured span | Every extreme gives a valid record (`looks show`) | 1 |
| A5 | Preview vs camera, all controls, in R1 | Natural below 2 dE, greys below 1 dE | 2 |
| A6 | `.cube` fit with a chosen input encoding; per-LUT error report | dE spread for 10 LUTs | 3 |
| A7 | `.xmp` mapping | Preview vs a Lightroom export of the same photo | 3 |
| A8 | Where fitting runs (standard-library installer: small solver, or numpy in the release) | Within 0.1 dE of `least_squares` on the 19 films | 3 |
| A9 | 3 imported LUTs on the camera (R2) | Within 0.5 dE of the fit's own error | 3 |

## 4. Track B details (editor on the camera, Tier 3)

Only after Track A, and only if the probes below pass. Today's mods in other bodies do this with menu rows.

| Step | Unknown | Probe | Camera? |
|---|---|---|---|
| B1 | Which stages change at run time without the refresh (step 1 of the card-looks probes was never run) | One probe build with `log-card-probe` and the debug log. Then card files only: poke each stage alone, photo + live view, with and without the refresh flag. The log records when the refresh ran | **yes, flash F1** |
| B2 | Settings for editor rows: only setting 448 is known free | Emulator: list dormant settings (as 446, 447, 449 were found) and check that none is read by stock code | no (emulator) |
| B3 | A host for the editor: list rows, the stock Highlight&Shadow screen (a tone editor with live preview), or a new panel | Emulator: trace the Highlight&Shadow panel's code and whether its curve can be fed from our tables | no (emulator) |
| B4 | Code space: 679 B of code and about 1.4 KB of segment 3 are free; an editor needs more | Prove one of the large unproven areas (95 KB NEEDS-DECISION, 123 KB sdk shell) with the existing marker probe: code there writes a marker to a card file | **yes, in flash F1** |
| B5 | Saving edits: the settings store holds 20.5 of 53.7 KB; when to save | Emulator: the save call per edit and its time | no (emulator), then F2 |
| B6 | Live-view lag after an edit | In F1: log the time from the key press to the refreshed frame | **yes, F1** |

Go or no-go after B1 to B4: go if the stages change at run time with the refresh, there are settings for at least
6 rows, and 2 KB or more of proven code space.

## 5. Track C details (hardware facts)

| Step | Question | Probe | Camera? |
|---|---|---|---|
| C1 | The six-axis stage at its extremes, and its G, C, M and C-hue directions | One look file: 12 slots, each one axis at one extreme; one RAW Data Edit of the test RAW per slot. Refit the model's six-axis directions | **yes, round R1** (with A5) |
| C2 | The range the hardware takes for each value (saturation gain, six-axis, chroma curves) before it clips or wraps | Same method: slots at 1x, 2x and 4x the fit bounds | **yes, round R1** |
| C3 | A hidden colour stage in TruePic VI | Static: compare the image-library builders (0x7E56224C, 0x7E562404) with the PEN-F COLOR builder layout (12 records, 28 B, sectors 2(r%6)+r/6). Hidden art-filter numbers 110 to 118 (`docs/todo.md`): on the E-M10 I one of them held a YCbCr colour key. Point a slot at each and log the parameter blocks | static: no; slots: **yes, flash F1** |
| C4 | Other white balance presets | Test RAW developed with 4 presets per look | **yes, round R1** |
| C5 | Add Effects (glow, vignette, white edge) on a film slot, as editor options | The data edit from `docs/todo.md` | **yes, flash F2** |
| C6 | The freeze at the RAW Data Edit save | The same round on stock firmware | **yes, flash F0 (stock) or skip** |

## 6. What the owner is asked to do on the camera

Only for Tier 2 and 3, each only when the desk work before it is done. Tier 1 needs none. No flash is needed
before F1.

| Id | What | Flash? | Brings back |
|---|---|---|---|
| R1 | Copy the test RAW and one `EPM2LOOK.BIN` (made by us); Load Looks; RAW Data Edit once per slot (12 slots, about 15 min) | no (pinned card-looks-4) | 12 JPEGs |
| R2 | The same with 3 imported LUTs | no | 3 JPEGs |
| F1 | Flash one probe build (`log-card-probe` + Debug Log + the space probe); then load 5 to 10 card files we send, a photo and a look at live view after each | yes, once | `EPM2LOG.BIN`, photos, notes on live view |
| F2 | Only if Track B is a go: flash the first editor build | yes | log and notes |
| F0 | Optional: the RAW Data Edit freeze test on stock firmware | yes (stock, then back) | yes/no |

Each build passes the usual gates first (`opcheck.py`, `hookcheck.py`, boot and update-path tests in the
emulator; `docs/flashing.md`). Recovery is the stock update from the card.

## 7. Order of work

1. Tier 1, desk only: A1 to A4, ship the installer editor with film-based controls.
2. Round R1 (A5, C1, C2, C4 in one visit); move Tier 2 features up or drop them by their pass marks.
3. Tier 3 only on the owner's call, one item at a time, each with its evidence before any user-facing text.

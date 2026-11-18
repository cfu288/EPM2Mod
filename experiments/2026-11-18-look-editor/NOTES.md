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

## 2. Track A: an editor in the installer, with a preview and LUT import

The first deliverable. It needs no new firmware: it writes `EPM2LOOK.BIN`, and Load Looks does the rest.

| Step | Work | Probe and pass mark | Camera? |
|---|---|---|---|
| A1 | Move `model2.py` and the fitter into the package (`src/epm2mod/looks/model.py`, `fit.py`) with tests | Same output as the experiment code on the synthetic RAW, dE difference below 0.05 | no |
| A2 | Get the model's stock tables from the user's own downloaded firmware (the installer already fetches it), never from our files | The extracted tables equal the ones `mocklib.py` reads, byte for byte | no |
| A3 | A preview: the forward model in TypeScript on a sample photo in camera RGB (our own RAWs, decoded by `orfcodec.py` to the model's input) | Browser preview vs Python model below 0.3 dE on the test chart | no |
| A4 | Map editor controls to record values (table in section 1); set the safe range of each control | Every control's extremes give a valid record (`looks show` checks it) | no |
| A5 | Camera check of the preview: a file with 12 edited looks, one RAW Data Edit round per look on one test RAW | Camera JPEG vs preview: natural colours below 2 dE, greys below 1 dE | **yes, round R1** |
| A6 | `.cube` import: the input encoding is chosen by the user (sRGB, V-Log, LogC3, S-Log3, ...); the fitter fits the stages to it; the page shows the mean and worst dE and the colours out of reach | 10 well-known free LUTs: report the dE spread per LUT | no |
| A7 | `.xmp` import (Lightroom): presets are parameters (HSL in 8 colours, tone curve, split toning, calibration). Map them; profiles that hold a colour table (`RGBTable`) are a LUT and go through A6 | A few presets, preview vs Lightroom export of the same photo | no |
| A8 | Where fitting runs: the installer is standard-library Python only. Choose between a small pure-Python or TypeScript solver (Gauss-Newton on these few dozen parameters) and adding numpy to the release | Solver within 0.1 dE of `least_squares` on the 19 films; zip size | no |
| A9 | Camera check of imports: 3 imported LUTs, measured as A5 | Camera within 0.5 dE of the fit's own error | **yes, round R2** |

Risks: the model is fitted on daylight white balance only (other presets untested); the freeze at the RAW Data
Edit save (`docs/film-emulation.md` section 7) can stop rounds R1 and R2; the G, C, M axes of the six-axis model
are approximate, so the preview can be off on those colours (C1 measures it).

## 3. Track B: an editor on the camera

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

## 4. Track C: hardware explorations that both editors need

| Step | Question | Probe | Camera? |
|---|---|---|---|
| C1 | The six-axis stage at its extremes, and its G, C, M and C-hue directions | One look file: 12 slots, each one axis at one extreme; one RAW Data Edit of the test RAW per slot. Refit the model's six-axis directions | **yes, round R1** (with A5) |
| C2 | The range the hardware takes for each value (saturation gain, six-axis, chroma curves) before it clips or wraps | Same method: slots at 1x, 2x and 4x the fit bounds | **yes, round R1** |
| C3 | A hidden colour stage in TruePic VI | Static: compare the image-library builders (0x7E56224C, 0x7E562404) with the PEN-F COLOR builder layout (12 records, 28 B, sectors 2(r%6)+r/6). Hidden art-filter numbers 110 to 118 (`docs/todo.md`): on the E-M10 I one of them held a YCbCr colour key. Point a slot at each and log the parameter blocks | static: no; slots: **yes, flash F1** |
| C4 | Other white balance presets | Test RAW developed with 4 presets per look | **yes, round R1** |
| C5 | Add Effects (glow, vignette, white edge) on a film slot, as editor options | The data edit from `docs/todo.md` | **yes, flash F2** |
| C6 | The freeze at the RAW Data Edit save | The same round on stock firmware | **yes, flash F0 (stock) or skip** |

## 5. What the owner is asked to do on the camera

In order, each only when the desk work before it is done. No flash is needed before F1.

| Id | What | Flash? | Brings back |
|---|---|---|---|
| R1 | Copy the test RAW and one `EPM2LOOK.BIN` (made by us); Load Looks; RAW Data Edit once per slot (12 slots, about 15 min) | no (pinned card-looks-4) | 12 JPEGs |
| R2 | The same with 3 imported LUTs | no | 3 JPEGs |
| F1 | Flash one probe build (`log-card-probe` + Debug Log + the space probe); then load 5 to 10 card files we send, a photo and a look at live view after each | yes, once | `EPM2LOG.BIN`, photos, notes on live view |
| F2 | Only if Track B is a go: flash the first editor build | yes | log and notes |
| F0 | Optional: the RAW Data Edit freeze test on stock firmware | yes (stock, then back) | yes/no |

Each build passes the usual gates first (`opcheck.py`, `hookcheck.py`, boot and update-path tests in the
emulator; `docs/flashing.md`). Recovery is the stock update from the card.

## 6. Order of work

1. Desk: A1, A2, A3, A4, A8, the static half of C3; B2, B3 in the emulator.
2. Round R1 (A5 + C1 + C2 + C4 in one visit).
3. Desk: refit the model from R1; A6, A7.
4. Round R2 (A9).
5. Flash F1 (B1, B4, B6, the slot half of C3).
6. Go or no-go for Track B.

# Film looks in the E-PM2's art-filter slots

Start with the plain-language write-up, `docs/film-emulation.md`. This folder is the lab bench.

| File | What |
|---|---|
| `NOTES.md` | dated lab notes, §1–41, in the order things happened (including what failed) |
| `CODE_DIG.md` | firmware addresses and what was read from the disassembly |
| `make_mock2.py`, `orfcodec.py`, `read_mock.py`, `mocklib.py` | the synthetic test RAW (written with our own ORF encoder), and reading its patches back from a camera JPEG |
| `model2.py`, `chroma.py`, `calib_model.py`, `eval_model.py` | the camera model, its chroma-curve stage, its calibration and its score against the camera |
| `fit_film2.py` | fit a film target with the model; `--anchor` for a correction round against a measurement |
| `fit_film.py` (uses `fit_xp9.py`) | the first model's fit tool (superseded) |
| `check_film.py`, `analyze_mock2.py`, `analyze_filters.py` | score a camera JPEG against a target and against the model |
| `bake_slide.py` | target LUT for slide films (spektrafilm with the print step off) |
| `slots/build_seven_films.py` | writes the current patch specs (`patches/seven-*.json`) from the fit files |
| `slots/`, `slot3/` (other files) | assembly for the new code and the generators of earlier builds |
| other `analyze_*`, `fit_*`, `check_*`, `extract.py`, `make_chart.py`, `make_mock.py` | earlier stages (photographed chart, first synthetic RAW); kept because NOTES refers to them |

## The camera model

`model2.py` predicts the JPEG the camera writes from the raw values and the settings of a look.
The stages, in the camera's order:

| # | Stage | What it does | Where its numbers come from |
|---|---|---|---|
| 1 | White balance | multiplies R and B | the file's EXIF |
| 2 | Colour matrix | 3 × 3; for a film look, the film's matrix times the camera's matrix, rounded by the camera's own rule | rule read from the firmware code; the result is in each JPEG's EXIF |
| 3 | Six per-hue values | saturation and hue for R, G, B, Y, C, M; modelled as 12 direction vectors in linear RGB | vectors fitted on developments of the test image |
| 4 | Base tone curve | one table for all channels | read from the firmware |
| 5 | Per-channel curves | three tables, R, G, B | the look |
| 6 | Look curve | on luma (BT.601 weights); the stock "identity" table has a highlight shoulder | read from the firmware |
| 7 | Saturation | chroma × gain × 0.003839 | scale fitted on the test image |
| 8 | Chroma curves | one curve on Cb, one on Cr, 16 knots each | format decoded from the firmware, checked on the camera |

Values outside the normal range: a negative value after stage 2 is not clipped. It passes stages 4
and 5 with its sign and lowers the luma. Luma below 0 becomes 0. Cb and Cr are limited to ± 124
around 128 before stage 8.

The fitted constants (stages 3 and 7, an exposure scale, the chroma limit) are in `calib/model2.npz`.
`calib_model.py` fits them on 25 developments of the synthetic test image with known settings and
tests them on 7 more. No photographed chart is used.

**How well the model predicts the camera** (ΔE2000, mean over patches; the seven developments of the
final build, which the calibration did not see):

| Group | Camera vs model |
|---|---|
| Natural colours | 0.92 |
| ColorChecker at five exposures | 0.87 |
| Skin series | 0.73 |
| Grays | 0.71 |
| Out-of-range colours | 1.15 |

The camera's rounding (8-bit JPEG, rounding at several stages) gives a floor of about 0.8 on natural
colours, so the model is close to that floor. On the stock picture modes, which it was not fitted on
until the last step, the first calibration gave 0.89 (Natural), 0.92 (Vivid), 0.86 (Muted) and 0.90
(Portrait).

## How well each film matches its target

Target: the spektrafilm 0.3.4 simulation of the film, baked as a 33³ LUT (V-Log in, sRGB out),
exposure 0 EV (camera middle gray = film middle gray). Scored on the patches of the synthetic test
image `PB130001.ORF`, developed in the camera with build `seven-films-5` / `-6`. ΔE2000, mean.

| Group (patches) | Portra 400 | Ektachrome 100 | Pro 400H | Kodachrome 64 | Vision3 250D | Velvia 100 | Superia 400 |
|---|---|---|---|---|---|---|---|
| Natural colours (3,526) | 1.26 | 1.27 | 1.15 | 1.06 | 1.19 | 1.44 | 1.36 |
| Natural colours, 95th percentile | 2.55 | 2.91 | 2.44 | 2.29 | 2.55 | 3.25 | 2.82 |
| Hold-out colours, not in the fit (1,000) | 1.26 | 1.30 | 1.19 | 1.08 | 1.20 | 1.47 | 1.39 |
| Skin series (45) | 1.15 | 1.18 | 1.01 | 0.80 | 1.00 | 1.56 | 1.65 |
| Grays (132) | 0.78 | 0.72 | 0.67 | 0.68 | 0.73 | 0.81 | 0.75 |
| Near-neutrals (576) | 1.00 | 0.91 | 0.91 | 0.85 | 0.93 | 0.99 | 0.98 |
| ColorChecker at five exposures (335) | 1.63 | 1.69 | 1.51 | 1.36 | 1.63 | 1.91 | 1.96 |
| Out-of-range colours (299) | 14.1 | 13.9 | 15.0 | 15.8 | 12.7 | 16.8 | 12.0 |

The same patches in the camera's stock Natural mode, against the same targets: natural colours 3.9
to 6.0, skin 4.3 to 6.2, grays 2.8 to 4.7, ColorChecker 5.6 to 7.8, out-of-range 14 to 22.

Where the remaining difference comes from, for natural colours:

| | Portra | Ektachrome | Pro 400H | Kodachrome | Vision3 | Velvia | Superia |
|---|---|---|---|---|---|---|---|
| Model vs target (what the camera's stages can express) | 0.84 | 0.87 | 0.79 | 0.72 | 0.81 | 1.09 | 1.10 |
| Camera vs model (rounding and model error) | 0.89 | 0.94 | 0.89 | 0.89 | 0.96 | 0.93 | 0.92 |
| Camera vs target (the result) | 1.26 | 1.27 | 1.15 | 1.06 | 1.19 | 1.44 | 1.36 |

Things to keep in mind when you read these numbers:

- The target is a simulation made from film datasheets. Nobody compared these looks with scans of
  real film.
- The scores are for the daylight (5300 K) matrix. Auto white balance uses the same matrix. With the
  Shade and Incandescent presets the model predicts changes of 0.05 or less on natural colours.
- Weights in the fit follow GRKit (grays 150, ColorChecker 20, skin patches 60, natural colours 1),
  plus the skin series at 20, near-neutrals at 4 and the out-of-range colours at 0.25.
- Out-of-range colours cannot be matched: the camera limits chroma (see the model above).
- Grain, halation and other spatial effects are not simulated.

The fitted values of the seven looks are in `fits/` (one `.npz` per film: three curves, gain, six-axis
values, matrix, chroma curves) and, as bytes at firmware addresses, in `patches/seven-films-5.json`.
They are derived from spektrafilm (CC BY-SA 4.0, see `NOTICE.md` at the top of the repository).

Not in git: `shots/` (camera files), `out/` (working fit results, target LUTs, readings). The final
fits are also in `fits/`, which `slots/build_seven_films.py` reads when `out/` is absent. Target LUTs come
from [spektrafilm](https://github.com/andreavolpato/spektrafilm) 0.3.4 (CC BY-SA 4.0).

`shots/` layout (kept small on purpose; only what the current pipeline uses): `testraw/` the
synthetic RAWs and the donor ORF whose header they borrow; `measured/` the camera's development of
the test RAW for each current film (the last measurement and the one its fit was corrected
against), plus stock Natural; `photos/` three ordinary photos taken with the seven-film build.
The photographed-chart series, the per-round folders (`mock1/`, `mock2/`, `stockfilters/`,
`remap7/`, …) and other files that NOTES and the earlier scripts name were deleted on 2026-11-12;
their patch readings remain in `out/mock/read_*.npz` on the machine that made them.

Run scripts from this folder with `../../.venv/bin/python -I <script>`.

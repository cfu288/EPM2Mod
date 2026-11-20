# Calibration run of the colour model (2026-11-20)

Labels: [C] camera, [R] read from the firmware, [I] inferred, V verified here (emulator or computation).

## 1. Why

The per-film 12-region tables of `../2026-11-20-twelve-region/NOTES.md` §9 are predicted to gain about 0.1 ΔE, but
the stage rules they rest on predict Natural's real table only in part (rms 1.77 of a 2.73-code change). `model2`
(stages 1-6) was calibrated on 14 hand developments, one stage at a time on a neutral film. ART BKT (RAW Data Edit,
developer tool) develops a RAW in all 12 entries at once, so one session gives 104 developments with any stage values.

Questions:

1. Do the rules predict realistic tables: the three fitted film tables and Natural's table A, on four films?
2. Saturation: added or multiplied? Natural's table with flat curves (ART 6) against with its curves (ART 2)
   separates the curve shapes from the rule.
3. Where stage 7 sits against the saturation gain and chroma curves: the same tables on four films with gains 282,
   315, and the two others' (ART 1-6 of the four files).
4. `model2` on 24 calibration films (ART 7-12): six-axis across its bounds, gains 160-420, strong art matrices,
   mixes of the catalogue's fits with tone curves per channel from different films.

## 2. Design (`scripts/design.py`)

Build `calib-probe` = films-look-exif-artbkt + data edits only (`../2026-11-20-twelve-region/scripts/mkspec.make`,
the same mechanism as twelve-region-probe): ART 1, 3, 4, 5, 6 get 12-region tables through the hash 0x7E78C6E4,
written over the stock tables of five worker cases' descriptors. ART 2 and 7-12 keep the default path (table A).

| ART | Table (stage 7) | Film, file 1 / 2 / 3 / 4 |
|---|---|---|
| 1 | all records off | clear / Portra 400 / Velvia 100 / Ektachrome |
| 2 | Natural's table A | the same |
| 3 | Portra 400's fitted table (`tables/portra-400.bin`) | the same |
| 4 | Velvia 100's fitted table | the same |
| 5 | Ektachrome's fitted table | the same |
| 6 | Natural's table A, every curve flat at 63 | the same |
| 7-12 | table A | calibration films K01-K06 / K07-K12 / K13-K18 / K19-K24 |

"clear" is the probe's transparent film (identity matrix and curves, six-axis 0, Natural's gain 282, straight chroma
curves). Calibration films (`films/design.json`, seed 20261120): K01-K08 mixes of catalogue fits, K09-K16 Portra 400
with six-axis values drawn across ±40 / ±20, K17-K20 Portra 400 at gain 160, 230, 345, 420, K21-K24 Portra 400 with
art matrices whose off-diagonal terms reach ±48.

Film files `build/calib/EPM2LOOK-<n>.BIN` (`films/list-<n>.json`). Test RAWs: `PB200001.ORF` of the twelve-region
experiment on the card as PB200002.ORF (file numbers must differ, `../2026-11-20-twelve-region/NOTES.md` §7) and
`../2026-11-09-film-portra/testraw/PB130001.ORF`.

## 3. Checks before the flash

| Check | Result |
|---|---|
| `scripts/emucheck.py` (the probe's verify on this build) | PASS: ART 1 the off table (mask 0), 3-5 the fitted tables, 6 the flat table, 2 and 7-12 table A, for both colour spaces and two picture modes; 43 stock codes keep their table pointers |
| twelve-region-probe spec after the `mkspec.make` refactor | byte-identical (sha256 0fe89ba5…); its emucheck output identical to `results/emucheck.txt` there |
| `uv run epm2mod make calib-probe` | sha256 `5a575639033c6d104cf3aeb5faafb0f6809a8327f5d3850b1b139b4955e57d3b` |
| `tools/checks.py --tier full` | free space, op-check, boot-test, update-path-test PASS; save-guard "FAIL", peaking-s1-s5 and s6-s7 REVIEW exactly as twelve-region-probe (flashed 2026-11-20 without fault): the same RESULT lines, the S6 list against the reference the same 174 codes (`../2026-11-20-twelve-region/NOTES.md` §4) |

## 4. Camera sheet (one flash, four film files)

On the Mac, card mounted at `/Volumes/Untitled`:

1. `rm -f /Volumes/Untitled/DCIM/100OLYMP/* && mkdir -p /Volumes/Untitled/DCIM/100OLYMP`
2. `scp USER@HOST:/path/to/epm2-tools/experiments/2026-11-20-twelve-region/testraw/PB200001.ORF /Volumes/Untitled/DCIM/100OLYMP/PB200002.ORF`
3. `scp USER@HOST:/path/to/epm2-tools/experiments/2026-11-09-film-portra/testraw/PB130001.ORF /Volumes/Untitled/DCIM/100OLYMP/PB130001.ORF`
4. `scp USER@HOST:/path/to/epm2-tools/build/calib/EPM2LOOK-1.BIN /Volumes/Untitled/EPM2LOOK.BIN`
5. `epm2flash calib-probe 5a575639033c6d104cf3aeb5faafb0f6809a8327f5d3850b1b139b4955e57d3b`, then the update on the
   camera (OK + ON/OFF, release when the orange lamp lights, wait for the blink, off and on).

Camera, once: P mode, Picture Mode Natural, WB Sunny; ART BKT screen: the 12 entries On, rows below Watercolor Off.

For each film file n = 1, 2, 3, 4:

6. MENU → SETUP → gears tab → J → Load Looks → Load → OK. ART 1 reads Q OFF, ART 7 reads K(6n−5).
7. ▶, PB200002, OK → RAW Data Edit → ART BKT → Yes → OK; at the end Reset / No → No → OK. Then PB130001 the same.
8. Off, card in the Mac; copy and clear the JPEGs:
   `scp /Volumes/Untitled/DCIM/100OLYMP/*.JPG USER@HOST:/path/to/calib/file-n/ && rm /Volumes/Untitled/DCIM/100OLYMP/*.JPG`
9. Unless n = 4: `scp USER@HOST:/path/to/epm2-tools/build/calib/EPM2LOOK-(n+1).BIN /Volumes/Untitled/EPM2LOOK.BIN`.

Back: `build/twelve-probe/EPM2LOOK-restore.BIN` as EPM2LOOK.BIN, `epm2flash films-look-exif af4bcb38…`, Load Looks.

Expected per file: 26 JPEGs (per RAW: the current Picture Mode, then ART 1-12).

## 5. Analysis plan

Readings: PB130001 developments through `read_mock.py` (layout mock2a), PB200002 developments through the probe's
`read_chart` (layout twelve). Order by file name: 13 of PB200002, then 13 of PB130001.

- Q1-Q3: per file, ART k − ART 1 (k = 2-6) is the table's measured change on that film. Predicted from the ART 1
  development by the rules (un-do the film's chroma curves and gain, apply the table, redo), under: stage 7 before
  the gain / after the chroma curves; saturation added / multiplied; the fit's chroma and luma constants. The
  hypothesis with the smallest residual over the four films wins; ART 6 vs ART 2 isolates the curve shapes.
- Q4: ART 7-12 developments of PB130001 against `model2` (camera vs model, as `check_film.py`); then a refit of
  `calib/model2.npz` (`calib_model.py`) with these 24 and the earlier 14 renderings, checked on the films of the
  confirmation round.
- Then `fit_twelve.py` again with the winning rules, and the 31 predictions.

## 6. Results (2026-11-20, all four files, 104 JPEGs, no fault)

`results/analyse.txt` (Q1-Q4), `results/table-gain.txt` (the fitted tables on their own films). [C] for the camera
numbers.

**Q4, model2.** On the 24 calibration films the camera matches model2 to 0.75-1.40 ΔE on natural colours (18 of 24
within 0.8-1.1; worst K05, a mix, 1.40 and grays 1.62; six-axis near its bounds 1.0-1.17), ColorChecker 0.77-1.21.
That is the films' own range (0.8-1.15): model2 holds across and beyond the fitted ranges; a recalibration would gain
little. The camera's ColorMatrix equals the expected one in every file.

**The fitted tables on the camera** (PB130001 against the film's target, natural / ColorChecker / skin):

| Film | no table | Natural's table (today) | its fitted table | predicted, today -> table |
|---|---|---|---|---|
| Portra 400 | 1.17 / 1.63 / 1.15 | 1.26 / 1.63 / 1.15 | 1.15 / 1.56 / 1.18 | 1.24 -> 1.17 / 1.69 -> 1.58 / 1.17 -> 1.18 |
| Velvia 100 | 1.34 / 1.96 / 1.53 | 1.44 / 1.91 / 1.56 | 1.34 / 1.89 / 1.38 | 1.44 -> 1.40 / 1.87 -> 1.66 / 1.51 -> 1.23 |
| Ektachrome | 1.20 / 1.70 / 1.18 | 1.27 / 1.69 / 1.18 | 1.24 / 1.56 / 1.09 | 1.30 -> 1.30 / 1.73 -> 1.47 / 1.23 -> 1.13 |

- The fitted tables gain on the camera about as predicted for Portra; for Velvia and Ektachrome the ColorChecker gain
  is smaller than predicted (0.02 and 0.13 against 0.21 and 0.26).
- **Natural's table itself costs the films 0.07-0.10 on natural colours**: switched off, every film is better on
  natural and hold-out colours, the ColorChecker equal. Most of the natural-colour gain of a fitted table is the
  removal of Natural's table.
- No stock 12-region table has every record off (the smallest mask is 0x001, codes 167 / 168): giving films "no
  table" needs a table of their own in the firmware.

**Q1-Q3, the rules on real tables.** On the four realistic tables (ART 2-5) the fitted rules leave rms 1.1-2.2 codes
of a 1.5-3.7-code change on the patches the table moves. Saturation adds (residual 1.44) rather than multiplies
(1.61). Where stage 7 sits is not resolved: before the gain, between gain and chroma curves, after the curves give
1.44, 1.47, 1.50. Natural's table with flat curves (ART 6) changes the picture by 16-19 codes and the rules miss 12-13
of it: the curve evaluation (or what a flat curve at 63 means) is wrong in the rules. The constants fitted on real
tables differ from the probe's (lightness 0.147 against 0.239 per unit, saturation 0.155 against 0.238, hue ×0.73).

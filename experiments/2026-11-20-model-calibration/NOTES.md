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

## 7. No 12-region table for the film simulations (2026-11-20)

From §6: Natural's table costs every film 0.07-0.10 on natural colours. `gen/stock-films/structure.py` (version 3,
`data/specs/stock-films-structure-3.json`) and `loader.py` (version 7, `data/specs/card-looks-7.json`):

- OFFCASE (9 B at the end of the shared code area, 0x7ECB0B78): `mov OFFDESC,a0; retf [d2,d3,a2,a3],20`, as the stock
  cases of the selector's worker 0x7E56E495. OFFDESC (56 B, segment 3, 0x7EE40728): table = OFFZERO − 3024, the 12
  flat ISO-weight pointers of the stock descriptor 0x7E78BA8C, then OFFZERO = 0. Only the table's enable mask (the u16
  at +3024) is 0; its records are whatever bytes lie there. A record whose bit is off has no effect [C] (probe OVERLAP
  entry: S −256 and L +256 with their bits off changed nothing), so the stage leaves the picture as it is.
- The eight film-only codes (75, 92, 94, 98, 125, 144, 156, 159) get a 12-region hash entry -> OFFCASE.
- The four in-place codes (79, 71, 72, 85), shared with Olympus's filters, get an entry that holds the worker's default
  case 0x7E56E5DC (where an absent key goes too; it reads only d0, d1 and the stack, which the lookup loop leaves as
  they are [R]); the loader switches the case word to OFFCASE while the entry has a film. Filling and emptying the slots
  instead does not work: no placement order keeps every lookup chain clear of a switched slot.
- Builds: `films-twelve-off` (the production candidate: films-look-exif with these two specs) and
  `films-twelve-off-artbkt` (the test build, with ART BKT).

The generators now make only this version; the earlier versions stay as committed spec files (a pinned build names
them). `tools/freespace.py check` no longer counts a later version's bytes against the earlier one (a build holds one
version), so the pinned build's check stays PASS while the successor waits.

| Check | Result |
|---|---|
| `gen/run.sh` | the older committed specs unchanged; versions 3 / 7 byte-identical to the flag-based generator's |
| `scripts/emucheck_off.py` (om-emu, the selector on the image, and on the image with the loader's switch words in their film state) | PASS: film-only codes mask 0 in both states; in-place codes table A (as pinned) with no film, mask 0 with a film; 43 stock codes x 2 colour spaces x 2 modes the pinned tables in both states |
| `tools/freespace.py check` | PASS for films-twelve-off and for the pinned films-look-exif |

`tools/checks.py --tier full` on films-twelve-off-artbkt: free space, op-check, boot-test, update-path-test PASS;
save-guard "FAIL" and the peaking REVIEWs as twelve-region-probe and calib-probe (both flashed without fault): S24 / S25
PASS for the build, the S6 list the same 174 codes.

## 8. Camera round on films-twelve-off-artbkt (2026-11-20)

The owner loaded `build/films-confirm/A`, `B`, `C` in turn and developed PB130001 with ART BKT (WB Auto, as the
confirmation round); batch A also holds PB200002's developments (skipped). `scripts/round_off.py`,
`results/round-off-<A|B|C>.txt`: each film against its target, Natural's table (confirmation round, films-look-exif)
-> no table (this build) [C]. Median over the 31 colour films, with the change per film:

| Group | Natural's table | no table | change, median (range) | better / worse |
|---|---|---|---|---|
| Natural colours | 1.19 | 1.12 | −0.06 (−0.16 … +0.02) | 27 / 2 |
| Hold-out | 1.23 | 1.14 | −0.06 (−0.18 … +0.03) | 27 / 2 |
| ColorChecker | 1.82 | 1.76 | −0.01 (−0.14 … +0.11) | 17 / 12 |
| Skin | 1.14 | 1.14 | 0.00 (−0.03 … +0.11) | 4 / 2 |
| Grays | 0.84 | 0.84 | 0.00 (−0.02 … +0.11) | 5 / 12 |

Natural colours improve for 27 films without any refit; the ColorChecker and grays move both ways (Portra 800 +2
ColorChecker +0.11, Vis 250D grays +0.11). The fits were corrected with Natural's table on; the next step corrects
each film from this round's reading.

`scripts/camera_vs_model.py` (`results/camera-vs-model.txt`): with no 12-region table the camera matches model2
better: natural colours 0.86 -> 0.72, ColorChecker 0.84 -> 0.65 (median over 31 films, closer for 30) [C].

## 9. Corrections and the convergence film files (2026-11-20)

`fit_film2.py --name film-<fit>-n1 --edge-weight 0.25 --anchor OFF_<id> <catalogue fit>` for the 31 colour films
(identity look, no 12-region table: the build of §8). Fits in `../2026-11-09-film-portra/out/fit_film-*-n1.npz` (not
in git until confirmed). Predicted (`results/corrections-n1.txt`), median: natural 1.12 -> 1.03, hold-out 1.14 ->
1.04, ColorChecker 1.76 -> 1.68, skin 1.14 -> 1.11, grays 0.84 -> 0.63. Film files for the convergence round
(`scripts/pack_round2.py`, the entries of `build/films-confirm/`, Double-X as before): `build/films-off2/A`
(`edff5bbd…`), `B` (`35204e92…`), `C` (`a7bad80d…`).

Production build films-twelve-off, `tools/checks.py --tier full`: free space, op-check, boot-test, update-path-test
PASS; save-guard S24 / S25 PASS for the build; peaking S6 lists 174 art codes against the reference, as every test
build of this line (twelve-region-probe, calib-probe, films-twelve-off-artbkt). The reference there is an older peaking build: run against the pinned films-look-exif (`scen_direct4.py s6`), films-twelve-off gives S6 PASS, 0 FAULT and no art code whose six-axis result differs.

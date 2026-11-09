# Film look (Portra 400) for the E-PM2: plan and findings

Started 2026-11-09. Status: **planning done; shoot 1 not yet taken.** Nothing built or flashed.

## 1. Question

Can the E-PM2 render a Kodak Portra 400 look in camera, the way GRKit and gr3-film-mods do on the
Ricoh GR III, by replacing the numbers an existing Picture Mode reads? If so, how close can it get,
and is it better than the best recipe the menus already allow?

## 2. Decisions so far

| Decision | Choice | Why / alternative |
|---|---|---|
| Target | **spektrafilm** Portra 400 → Kodak Portra Endura print, scanned (`spektrafilm-lut build --film kodak_portra_400 --print kodak_portra_endura --input vlog --output srgb --resolution 33`, as gr3-film-mods §13) | User choice. A real roll + lab scan was considered and dropped. Note: this is a *darkroom print* rendering (enlarger balanced to neutral), not a Frontier/Noritsu lab-scan look. |
| Exposure anchor | 0 EV: camera middle gray = film middle gray (GRKit `exposure: 0.0`) | Default, not yet confirmed by the user. +1 EV ("overexposed Portra") is a common alternative and changes the look a lot (gr3 §13: Standard vs target 5.7 at 0 EV, 12.2 at +1 EV). |
| White balance | Camera WB normalizes first; grays must stay neutral | Matches the print's neutral balance and per-frame lab balancing. Default, not yet confirmed. |
| Slot | Replace **Portrait** first; **Cross Process** if per-channel curves exist only in the art path | Decide after step 1e (§6). New menu entries are out of reach (selector table, report). |
| Camera control | **Manual** shooting; no USB/ADJ scripting for now | Saves ~15–30 min of ~2–3 h; revisit only for live RAM edits, many looks, or > 6 rounds. |

## 3. Approach

```
ORF (linear) ─► [ WB → matrix M → tone curve(s) → saturation? ] ─► JPEG     the model, fitted from shoot 1
same input   ─► spektrafilm Portra 400 → Endura (LUT)          ─► target T
fit          ─► change Portrait's M and curve(s) until model ≈ T; write them into the firmware tables
check        ─► flash; RAW Data Edit the same reference ORF; compare camera vs prediction vs T
```

Every pixel's Portra baseline is **computed** (T applied to the ORF's linear RGB), so no real
Portra photos are needed. The photos define the camera model, not the target.

### Loss (follows GRKit `crates/grkit-core/src/fit/`, ported from gr3-film-mods)

```
Loss(θ) = Σ_i w_i · ΔE2000( Lab(cam_θ(L_i)), Lab(T(L_i)) )²
        + λ_smooth · Σ (2nd differences of each curve)²      (GRKit SMOOTHING = 3000)
        + λ_limit  · Σ max(0, |M_jk| − m_max)²              (GRKit MATRIX_LIMIT = 2.0)
subject to: curves monotone and in the table range; rows of M sum to 1; then rounded to firmware format
```

| Samples L_i | Weight w_i (GRKit) |
|---|---|
| Gray ramp, −2…+2 EV | 150 |
| Chart colours, −2…+2 EV | 20 (skin 60) |
| Random natural colours (L* 10–100, any hue, low-chroma bias, in sRGB) | 1 |
| Hold-out: 3,000 more random colours | not fitted; report mean / p95 ΔE |

Excluded: scene levels above the sensor's headroom (~3× diffuse white, GRKit `SENSOR_HEADROOM`).
ΔE2000, not RGB error: gr3's RGB least-squares fits came out under-saturated on camera
(FINDINGS §22m, mean dC −2.1…−2.5); refitting on ΔE2000 took Portra from 2.28 to 1.98.

Before flashing anything, the fit reports three numbers: predicted ΔE for **free tables**, for
the **best menu-only recipe** (modes × Contrast × Saturation × Gradation × WB shift), and for
stock Portrait. If free tables barely beat the menu recipe, stop there.

## 4. What shoot 1 is for ([SHOTS.md](SHOTS.md))

| Set | Gives | Decides |
|---|---|---|
| B1–B7 tone bracket | ~250 gray points (36-step gray row × 7 exposures) with exactly known relative input | Natural's curve; match it against the 148 firmware curves (§5) to find its table address; K (where middle gray lands) |
| M1–M5 modes | Curve + matrix per mode | What differs between modes: matrix, curve, or both |
| G1–G3 gradation | Curve per Gradation | Whether Gradation switches tables (likely: repeating sets of ~30) |
| N1–N4, P1–P4 | Contrast and Saturation effects | Whether those settings still work on top of a new look, and how to keep them working |
| A1–A4 art filters | Gray rendering per channel | **Whether R/G/B curves can differ** (the main limit on fidelity) and which slot to use |
| I1–I2 ISO | Curve at ISO 800 / 3200 | Whether curves vary with ISO (the ~30-curve sets may be per ISO) |
| W1–W2 WB | Matrix under other WB | Whether Portrait's matrix stacks on the per-illuminant matrix from the WB module (14b), so whether the look holds under other light |
| D1 | Repeat of B4 | Drift during the session |
| R1 | RAW Data Edit of B4 | Whether one ORF can be the test input for every later round |
| S1 | Real scene | Side-by-side check against T(ORF) later |

Also from every ORF: ImageProcessing `UnknownBlock1` (0x0635, 5,764 B, starts `CMIO`). Its
builder 0x7E55866A uses table-driven fillers, one of which (0x7E559BE5) also reads the engine
coefficient blocks 0x7E764000–0x7E7885FF (14d). So it may hold the processing parameters of each
shot. Plan: diff it across the M/G/N/P/A shots and search block 0 for the bytes that change.
Not yet tested.

## 5. What is known (repo references)

| Piece | Where | Status |
|---|---|---|
| Picture Mode = prm 0x9481; modes 1–7; per-mode Contrast/Sharpness/Saturation/Gradation; mode switch 0x7E70430B | sections 09, 07, 13e | verified |
| Tone-curve builder: 10-bit spline from knots ctx+3939…3962; signed adjustments +3967…3972 | 0x7E553271, 0x7E55408B (13a §3.3) | verified; writers not traced |
| 16-bit curve tables 0x7E74E000–0x7E763FFF; readers 0x7E56E837, 0x7E56EB95 | 14d | located |
| Engine coefficient / parameter blocks 0x7E764000–0x7E7885FF (readers 0x7E56D1C3, 0x7E566C94, 0x7E559BE5) | 14d | located; contents unknown |
| Pop Art, Pale&Light, Light Tone, Cross Process have no code module (image-processor parameters only) | 09 | verified |
| WB module computes per-illuminant WB gains and colour matrices (`PRM_CAM_SPECTRUM_STL_R/G/B`) | 14b §3 | verified |
| RAW Data Edit → [Current] re-develops an ORF with the current settings | manual p. 65 | documented |
| Modified firmware flashes and runs; stock reflash recovers | docs/camera-log.md (2026-11-08) | camera-tested |
| Equal-length string edits in block 1 work | patches/pixel-hacking.json | camera-tested |

### New: curve-table profile (`profile_curves.py`, output `out/curves.tsv`)

- 158 monotone runs of ≥ 200 u16 words between 0x7E74E5BC and 0x7E763714. **148 are exactly 256
  entries** at a 512-byte stride; all map onto 0…1023 (10-bit output). **105 are unique.**
- The first curve (0x7E74E5BC) is the identity (s32/s64/s128/s192 = 128/257/514/770).
- They repeat in sets of about 30, with near-duplicate pairs inside each set (e.g. 0x7E74E7BC vs
  0x7E74EBBC differ by a few codes). Some curves are 0 until the top (0x7E7513BC: 0,0,0,0,558),
  so probably masks or weights, not tone curves.
- **No obvious R/G/B triple pattern.** Reading (inferred): base gamma and gradation variants per
  mode, ISO or setting, not per-channel look curves. Shoot 1 (B, G, I, A sets) should settle it.

## 6. Plan

| Phase | Work | Gate |
|---|---|---|
| 0 | Shoot 1 ([SHOTS.md](SHOTS.md)) | Test bench valid (R1 ≈ B4 JPEG) |
| 1 | a. match measured curves to the 148 tables; b. trace readers 0x7E56E837 / 0x7E56EB95 → mode-to-table index; c. trace writers of ctx+3939…3972 back to 0x7E70430B; d. find matrices in 0x7E764000–0x7E7885FF (3×3 fixed point, rows summing to a power of two), match to the Saturation shots; e. compare art filters with Natural for per-channel curves; f. `UnknownBlock1` diff | Written E-PM2 pipeline model: stages, where each mode's values live, what each can express |
| 2 | One-flash location proof: an obvious change to one Portrait table | Observed change = predicted |
| 3 | Camera model + fitter (port GRKit or gr3-film-mods); calibrate to shoot 1 until stock modes are predicted within ~ΔE 1 | Model accuracy; predicted ΔE free vs menu-only vs stock |
| 4 | `patches/film-portra.json` (tables + "Portrait" → "Portra" label); flash; RAW Data Edit the B4 and S1 ORFs + 1 live shot; measure | Camera ≈ prediction; ΔE vs T |
| 5 | More looks (Muted → Gold/Ektar, Monotone → Tri-X) | — |

Expected rounds for phase 2–4: about 4–6 flashes, each 1 flash + 2 RAW Data Edits + 1 shot
(~10 min of camera time). gr3's first Portra flash measured chart ΔE 4.0 vs 3.0 predicted; after
fixing unmodelled stages it reached camera vs model 0.55–0.80 and camera vs target 2.28 (Standard
6.4), later 1.98 with a ΔE2000 refit (FINDINGS §13, §14a, §22l–§22m).

## 7. Expectations and limits

- Replaces a mode; adds none. JPEG only: the ORF is unchanged and Olympus software renders it as
  the original mode.
- Fidelity depends on phase 1e. With matrix + per-channel curves + a post matrix, ~ΔE 2 is
  realistic (gr3). With one luminance curve + saturation + one matrix, expect "Portra-ish"
  (custom curve shape and hue-specific shifts, but no split toning).
- Yellow-to-orange rotation (Portra) needs hue sectors; gr3 left it as residual until it found the
  GR's MultiAxial stage. No hue-sector stage is known on the E-PM2 (no Color Creator / HSL strings).
- No grain or halation: the grain texture (block 2) is read only by Grainy Film.

## 8. References

- **GRKit** ([ahonn/GRKit](https://github.com/ahonn/GRKit), MIT; effects CC BY-SA 4.0 / MIT).
  Release zip `../../../references/GRKit-1.5.3-GR-III-20261109-0601.zip` (GR III):
  `SD_ROOT/SCRIPT/GRKIT/EFFECTS/*.GRF` = compiled looks (`GRFX0001` header, id, name, then data),
  `MODULES/FILMLOOK.GRM`, `CORE.BIN`, loader scripts (`STARTUP.TTL`, `LOADER.TTL`). Not run.
  Look model (effects/README.md): Q13 3×3 matrix before the base gamma; three 256-sample curves
  (0–16383) after it; optional Q13 post matrix (folded into the YCbCr matrix); optional hue
  sectors. Portra 400 (`effects/portra-400-endura-v1/effect.json`): matrix
  `[6465,1679,48, -131,7519,804, 33,474,7685]`, fit mean ΔE 1.406 vs Standard 5.784.
  The fitted numbers are GR-specific; reuse the method, not the values.
- **gr3-film-mods** ([idontknownihil/gr3-film-mods](https://github.com/idontknownihil/gr3-film-mods), MIT):
  FINDINGS §11 (how to build a LUT-style film filter), §13 (Portra via spektrafilm; per-channel
  curves taken from a Cross Process preset), §14a (camera test method: rawpy linear develop, JPG
  aligned, model vs camera), §22l–§22m (stage order; ΔE2000 refit). `make_hue_chart.py`: the
  monitor chart idea used by `make_chart.py`.
- **spektrafilm** ([andreavolpato/spektrafilm](https://github.com/andreavolpato/spektrafilm)):
  code GPLv3; profiles and LUTs CC BY-SA 4.0; LUTs also under its own "commercial use, free share,
  no resale" licence. Fitted tables derived from its LUTs inherit CC BY-SA 4.0.
- fishcu, [USB_UPDATE.md](https://github.com/fishcu/oly_fw_analysis/blob/main/docs/protocols/pen-f/USB_UPDATE.md):
  Olympus vendor SCSI transport (C0 command / C1 data / C3 response) for the deferred USB route.

## 9. Tooling

- `../../.venv`: `rawpy` 0.28.0 (LibRaw 0.22.2) and `numpy`. Run analysis with `.venv/bin/python -I`.
- `exiftool`: **not installed** (needs sudo: `sudo apt install libimage-exiftool-perl`). Needed
  for the EXIF settings check and `exiftool -u -b -ImageProcessing:UnknownBlock1 X.ORF`.
- `make_chart.py`: monitor chart PNGs + `out/chart_layout.json` (patch boxes). Stdlib only.
- `profile_curves.py`: §5 curve profile. Stdlib only.
- To write after shoot 1: `extract.py` (ORF + JPEG → patch pairs, EXIF check), `fit_stock.py`,
  `fit_look.py`, `check.py`.

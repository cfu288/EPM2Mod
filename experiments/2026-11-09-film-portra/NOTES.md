# Film look (Portra 400) for the E-PM2: plan and findings

Started 2026-11-09. Status: **shoot 1 taken and analysed (results §10). Test bench valid (RAW Data
Edit output is pixel-identical to the camera JPEG). Per-channel curves exist only in the art-filter
path. Curve table addresses not yet identified.** Nothing built or flashed.

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
| Slot | **Open, recommendation: Cross Process.** Shoot 1 (§10) shows per-channel curves only in the art-filter path (Cross Process, Pale&Light); normal modes, Portrait included, have one luminance curve plus saturation. | Portrait would give a custom tone curve + saturation only ("Portra-ish"). Cross Process gives R/G/B curves and hue shifts (as gr3 used on the GR III), at the cost of art-filter behaviour (RAW-only becomes RAW+JPEG; art filters lock Colour Space to sRGB). New menu entries are out of reach (selector table, report). |
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
| B1–B5 tone bracket (−2…+2 stops; handheld, by aperture and time) | ~180 gray points (36-step gray row × 5 exposures); the actual exposure of each patch is measured from the RAW | Natural's curve; match it against the 148 firmware curves (§5) to find its table address; K (where middle gray lands) |
| M1–M5 modes | Curve + matrix per mode | What differs between modes: matrix, curve, or both |
| G1–G3 gradation | Curve per Gradation | Whether Gradation switches tables (likely: repeating sets of ~30) |
| N1–N4, P1–P4 | Contrast and Saturation effects | Whether those settings still work on top of a new look, and how to keep them working |
| A1–A4 art filters | Gray rendering per channel | **Whether R/G/B curves can differ** (the main limit on fidelity) and which slot to use |
| I1–I2 ISO | Curve at ISO 800 / 3200 | Whether curves vary with ISO (the ~30-curve sets may be per ISO) |
| W1–W2 WB | Matrix under other WB | Whether Portrait's matrix stacks on the per-illuminant matrix from the WB module (14b), so whether the look holds under other light |
| D1 | Repeat of B3 | Drift during the session |
| R1 | RAW Data Edit of B3 | Whether one ORF can be the test input for every later round |
| S1 | Real scene | Side-by-side check against T(ORF) later |

Also from every ORF: ImageProcessing `UnknownBlock1` (0x0635, 5,764 B, starts `CMIO`). Its
builder 0x7E55866A uses table-driven fillers, one of which (0x7E559BE5) also reads the engine
coefficient blocks 0x7E764000–0x7E7885FF (14d). So it might have held each shot's processing
parameters. **Tested 2026-11-09: it does not** (§10.3).

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
| 0 | Shoot 1 ([SHOTS.md](SHOTS.md)) | **Done.** Test bench valid: R1 pixel-identical to its camera JPEG |
| 1 | a. match measured curves to the stored tables (**done: shape measured; address ambiguous**, §10.4); b. trace readers 0x7E56E837 / 0x7E56EB95 → mode-to-table index (**next**); c. trace writers of ctx+3939…3972 back to 0x7E70430B (**next**); d. find the saturation / hue-dependent chroma stage (the camera matrix is per-illuminant only, §10.2); e. per-channel curves (**done: art path only**, §10.5); f. `UnknownBlock1` diff (**done: negative**, §10.3) | Written E-PM2 pipeline model: stages, where each mode's values live, what each can express |
| 2 | One-flash location proof: an obvious change to one candidate table (e.g. 0x7E74E9BC vs its twin 0x7E74EDBC, §10.4), checked with RAW Data Edit of PB090221 | Observed change = predicted |
| 3 | Camera model + fitter (port GRKit or gr3-film-mods); calibrate to shoot 1 until stock modes are predicted within ~ΔE 1 | Model accuracy; predicted ΔE free vs menu-only vs stock |
| 4 | `patches/film-portra.json` (tables + "Portrait" → "Portra" label); flash; RAW Data Edit the B3 and S1 ORFs + 1 live shot; measure | Camera ≈ prediction; ΔE vs T |
| 5 | More looks (Muted → Gold/Ektar, Monotone → Tri-X) | — |

Expected rounds for phase 2–4: about 4–6 flashes, each 1 flash + 2 RAW Data Edits + 1 shot
(~10 min of camera time). gr3's first Portra flash measured chart ΔE 4.0 vs 3.0 predicted; after
fixing unmodelled stages it reached camera vs model 0.55–0.80 and camera vs target 2.28 (Standard
6.4), later 1.98 with a ΔE2000 refit (FINDINGS §13, §14a, §22l–§22m).

## 7. Expectations and limits

- Replaces a mode; adds none. JPEG only: the ORF is unchanged and Olympus software renders it as
  the original mode.
- Fidelity depends on the slot (§10.5). Cross Process: per-channel curves and some hue shift,
  so ~ΔE 2–3 is plausible (gr3 reached 2.3 that way). Portrait: one luminance curve + saturation,
  so expect "Portra-ish" (curve shape and saturation, no split toning).
- Yellow-to-orange rotation (Portra) needs hue sectors. The E-PM2 has **some** hue-dependent chroma
  processing (Vivid and i-Enhance boost different hues by different amounts, §10.6); whether it
  can rotate hue, and where its tables are, is unknown. No Color Creator / HSL strings.
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

- `../../.venv`: `rawpy` 0.28.0 (LibRaw 0.22.2), `numpy`, `scipy`, `opencv-python-headless`,
  `pillow`. Run analysis with `../../.venv/bin/python -I`.
- `exiftool` 12.76 (Ubuntu package, installed 2026-11-09).
- `make_chart.py`: monitor chart PNGs + `out/chart_layout.json` (patch boxes). Stdlib only.
- `profile_curves.py`: §5 curve profile. Stdlib only.
- `extract.py`: shots → `out/patches.npz` (per shot × 252 patches: raw RGB, JPEG RGB, clip and
  spread flags) + `out/settings.json`. Markers found separately in JPEG and raw; per-patch boxes
  refined to the flattest spot with a robust cubic distortion field (§10.1).
- `analyze_tone.py`: model `v = ColorMatrix·(WB⊙raw)`, outlier flag, and matching of the measured
  gray response against every 256-entry curve in block 0 (`out/tone_report.txt`, `out/tone_*.png`).
- `analyze_modes.py`: Natural's measured response F; every other shot vs F (gray per channel;
  colour chroma/hue by sextant) (`out/modes_report.txt`, `out/gray_*.png`, `out/natural_F.npz`).
- Still to write: `fit_stock.py`, `fit_look.py`, `check.py`.

## 10. Shoot 1 results (2026-11-09)

### 10.1 Extraction
- All 36 chart shots (PB090185–0221) decode; markers found in every JPEG and raw. The displayed chart
  was the 1920×1080 layout.
- **The raw is not corrected for lens distortion; the JPEG is.** A four-corner homography put raw
  boxes up to half a patch off on the right side of the chart (on the gap between two gray patches,
  0185 column 26). Fixed by a per-patch flatness search plus a robust cubic offset field; after it
  the gray row rises monotonically in every shot and the f/5.6 vs f/11 ratio is 3.9–4.0 in every
  row. The last gray patch (pure white, right edge) reads ~8 % low in every shot, raw and JPEG: real
  screen fall-off.
- Black level is per file (255 at ISO 200, 253/254 at ISO 800, 251/252 at ISO 3200); the sensor
  saturates at 4045. About 14 % of patch samples are flagged as raw outliers and left out.

### 10.2 What the EXIF already says
- `ColorMatrix` (camera RGB → sRGB, rows sum to 256) is **identical for every Picture Mode,
  Contrast, Saturation, Gradation and art filter**; it changes only with WB (5300K:
  `418 -140 -22 / -56 360 -48 / 14 -132 374`; CWB 3200K: `374 -92 -26 / -70 340 -14 / 22 -184 418`).
  So modes do not differ in this matrix; their colour differences come later.
- `WB_RBLevels` 528/460 (÷256) at 5300K = LibRaw's camera WB. ImageProcessing 0x1401–0x1406 follow
  ISO/exposure (noise), not the look.

### 10.3 Maker-note blocks: no shortcut
- `UnknownBlock1` (5,764 B, `CMIO`): identical for every mode / Contrast / Gradation / Saturation /
  art filter; changes only at ISO 800/3200. Sensor/noise parameters, not the look.
- `UnknownBlock2` (76,608 B) is byte-identical to the firmware's static CMIO blob
  0x7E86DD80–0x7E8808BF in every shot (confirms 14d's inference).
- `UnknownBlock3` (49,152 B) and `UnknownBlock4` (4,608 B) change between identical base shots,
  most with exposure: image statistics (metering/histogram), not settings tables.
- So the ORF records which mode was used, not the mode's curve or matrix values.

### 10.4 Natural's tone response and the stored curves
- The model `v = ColorMatrix · (WB ⊙ raw)`, JPEG = F(v), collapses all three channels of all 11
  Natural shots onto one curve (isotonic fit, residual 1.6 codes = the noise floor). So WB and
  `ColorMatrix` are the camera's first stages and grays then go through one curve.
- F: v 133 → 71, 251 → 115, 472 → 162, 887 → 210, 1669 → 234 (8-bit codes); middle gray
  (code 118) at v ≈ 267; v = 4045 (saturation) → 249.
- No stored 256-entry table fits with only an input scale (best 0x7E74E9BC, 2.95 codes). With
  input offset and output gain/offset free, several reach the floor (1.73–1.93), so the chart
  cannot identify the table. Most plausible: **0x7E74E9BC** (input offset 0.07, output gain 0.244
  ≈ 1/4.1, i.e. the 10-bit table to 8-bit; 1.79 codes); its near-twin 0x7E74EDBC fits as well.
  The tone builder 0x7E553271 makes 10-bit curves from spline knots at run time (13a §3.3), so the
  real curve may not be stored at all. Identification needs the static trace (phase 1b/1c) or the
  phase-2 flash test.
- A fixed-scale test of the art filters' channel responses against stored curves is inconclusive.

### 10.5 Tone and channels per setting (gray row vs F, codes; `out/modes_report.txt`)

| Setting | Gray rendering vs Natural | Channels |
|---|---|---|
| Vivid, Muted, Monotone, i-Enhance | same curve (±2–4) | equal |
| **Portrait** | **own brighter curve**: +3 shadows, +11 from midtones up | equal |
| High Key / Low Key / Auto | own curves (High Key +16…+22 above midtones; Low Key −11 shadows, +7 highlights; Auto lifts shadows/mids +15…+23) | equal |
| Contrast −2 / +2 (Natural) | flatter / steeper (+2 / −10 shadows, −5 / +19 highlights) | equal |
| Contrast −2 / +2 (Portrait) | same kind of change on Portrait's curve | equal |
| ISO 800 / 3200 | **same curve** (±1) | equal |
| WB CWB 3200K / Auto | same curve | equal (B +4…+6 in mids at 3200K) |
| Pop Art | own curve (shadows −5, highlights +11) | equal |
| Light Tone | own curve (shadows/mids +17…+28, highlights −25) | equal |
| **Pale&Light Color** | lifted | **channel-dependent** (B lifted ~10–40 codes more than R) |
| **Cross Process** | | **channel-dependent**: R and B ~33 codes below G in shadows, ~53 in mids; highlights R +40, G/B +56 |

So per-channel curves exist, but only in the art-filter path. Every normal Picture Mode moves
R, G and B together.

### 10.6 Colour per setting (chroma × and hue shift vs Natural, by hue sextant)
Sextants (BT.601 angle of CbCr): blue-magenta, magenta-red, red-yellow, yellow-green, green-cyan,
cyan-blue.

| Setting | Chroma × (6 sextants) | Hue |
|---|---|---|
| Saturation −2 / +2 | 0.79–0.81 / 1.20–1.23, uniform | no shift |
| Vivid | 1.19 1.20 1.13 1.15 1.09 1.22 | ±4° |
| Muted | 1.00 0.95 0.94 1.01 1.01 0.92 | ±4° |
| Portrait | 1.00–1.06 | ±2° |
| i-Enhance | 1.08 1.14 **1.24 1.23** 1.04 1.00 | ±4° |
| Gradation, Contrast, ISO, WB | 0.95–1.06 | ±3° |
| Pop Art | 2.0–2.5 | −10…+5° |
| Pale&Light | 0.53–0.58 (cyan-blue 0.95) | ±14° |
| Light Tone | 0.87–0.93 | ±5° |
| Cross Process | 1.23–1.44 | +10…+14° (magenta-red, red-yellow) |

So the normal path has a **hue-dependent chroma gain** (Vivid and i-Enhance boost hue sectors
differently), and Saturation is a uniform scale. No normal mode rotates hue by more than ~4°.

### 10.7 What this means for Portra
- **Portrait slot:** a custom luminance curve (Portrait already has its own) + saturation
  (+ possibly hue-dependent saturation, once its tables are found). No warm shadows / split toning.
- **Cross Process slot:** per-channel curves (warm shadows, cooler highlights) + hue shifts. Closest
  to what gr3-film-mods did on the GR III (it took over Cross Process's three curves).
- Next (no camera needed): phase 1b/1c static trace from the curve readers (0x7E56E837,
  0x7E56EB95), the art-code compares in the colour handlers (0x7E560B85, codes 85/167 = Cross
  Process), and the mode switch 0x7E70430B, to find where Portrait's curve, Cross Process's channel
  curves and the chroma gains are stored. Then phase 2: one flash that changes one of them visibly.

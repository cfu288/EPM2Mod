# Film look (Portra 400) for the E-PM2: plan and findings

Started 2026-11-09. Status (2026-11-11): **`film-portra-xp-labelled` is flashed and behaves as
modelled (§15). Model corrected after the Caduceus research (§16): the look curve acts on luma
(verified on shoot 1: ΔE model vs camera 1.7 → 0.9, one saturation per mode family); the six-value
records are R/G/B/C/M/Y saturation + hue (axes established, units approximate, not used in fits).
`build/film-portra-xp2-labelled.BIN` (adds a fitted luma curve; predicted hold-out 2.01 vs 2.11) is
built, NOT camera-tested.** Decisions (user, 2026-11-11): GRKit's choices wherever they apply,
camera Auto WB; slot in use: Cross Process I.

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
| Slot | **Cross Process** (user, 2026-11-10, following the recommendation). Shoot 1 (§10) shows channel-dependent rendering only in the art-filter path (Cross Process, Pale&Light); §11 shows it is a split-toning stage, not three curves. | Portrait would give a custom tone curve + saturation only ("Portra-ish"). Cross Process gives R/G/B curves and hue shifts (as gr3 used on the GR III), at the cost of art-filter behaviour (RAW-only becomes RAW+JPEG; art filters lock Colour Space to sRGB). New menu entries are out of reach (selector table, report). |
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
| 1 | a. match measured curves to the stored tables (**done**, §10.4, §11.1); b. curve selector → mode / art-code → table (**done**, §11.1); c. writers of ctx+3939…3972 (not needed for the look curves; open); d. hue-sector / chroma records (**found**, §11.2; meaning of the 6+6 values open); e. per-channel rendering (**done: split toning in the art path**, §11.3); f. `UnknownBlock1` diff (**done: negative**, §10.3); **g. locate the split-toning tables (next)**; h. Cross Process's extra luminance stage (open) | Written E-PM2 pipeline model: stages, where each mode's values live, what each can express |
| 2 | One-flash location proof: an obvious change to Cross Process I's look curve 0x7E75F2F0 (e.g. invert it), checked with RAW Data Edit of a Cross Process ORF | Observed change = predicted |
| 3 | Camera model + fitter (port GRKit or gr3-film-mods); calibrate to shoot 1 until stock modes are predicted within ~ΔE 1 | Model accuracy; predicted ΔE free vs menu-only vs stock |
| 4 | `patches/history/film-portra.json` (tables + "Portrait" → "Portra" label); flash; RAW Data Edit the B3 and S1 ORFs + 1 live shot; measure | Camera ≈ prediction; ΔE vs T |
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
  spread flags) + `out/settings.json` + `out/gridlines.json`. Markers found separately in JPEG and
  raw; boxes centred between the detected gap lines (`grid_quads`, §10.1).
- `analyze_tone.py`: model `v = ColorMatrix·(WB⊙raw)`, outlier flag, and matching of the measured
  gray response against every 256-entry curve in block 0 (`out/tone_report.txt`, `out/tone_*.png`).
- `analyze_modes.py`: Natural's measured response F; every other shot vs F (gray per channel;
  colour chroma/hue by sextant) (`out/modes_report.txt`, `out/gray_*.png`, `out/natural_F.npz`).
- `analyze_pipeline.py`: checks the traced pipeline (§11) against every setting with one fitted
  scale k, and prints Y / Cb / Cr of the gray row for the toning stage (`out/pipeline_report.txt`).
- Still to write: `fit_stock.py`, `fit_look.py`, `check.py`.

## 10. Shoot 1 results (2026-11-09)

### 10.1 Extraction
- All 36 chart shots (PB090185–0221) decode; markers found in every JPEG and raw. The displayed chart
  was the 1920×1080 layout.
- **The raw is not corrected for lens distortion; the JPEG is.** A four-corner homography put raw
  boxes up to half a patch off on the right side of the chart (on the gap between two gray patches,
  0185 column 26).
- **Box placement (revised 2026-11-10, the user's suggestion: find the lines between the squares,
  then centre the boxes between them).** `grid_quads` finds the dark gap lines: horizontal lines
  from profiles down every column, vertical lines from one profile along each row, with valleys
  assigned to line numbers by walking outward from the chart centre (a missing valley is skipped,
  not mis-assigned). Each direction gets a smooth robust fit (cubic in line index × quadratic
  along the line), and each box is the central 45 % × 50 % of the cell between its four lines.
  Raw line fits: median residual 0.2–0.8 px (half-size), 98–100 % inliers, no fallback cells.
  JPEG at base exposure: median 1.5–2 px at full size (a cell is ~92 px). Three images needed a
  second pass with heavier smoothing (raw 0219, darkest; JPEG 0189, +2 stops; JPEG 0208, Soft
  Focus); 0208 still keeps 34 cells from the first guess. The first guess (flatness search) had
  been ~0.7 of a patch off in places (0185 rows 2–4, columns 27–34). Per-shot fit statistics:
  `out/gridlines.json`; full-resolution check crops: `out/check_{raw,jpg}_<shot>.png`.
- Effect of the revision: patches flagged as raw outliers 14 % → **1.9 %**; gray-row drops → **0**
  in all 37 shots; f/5.6 vs f/11 ratio (1st–99th percentile) 2.42–6.1 → **3.81–4.12**; Natural tone
  curve residual 1.6 → **1.07 codes**. The last gray patch (pure white, right edge) reads ~8 % low
  in every shot, raw and JPEG: real screen fall-off.
- Black level is per file (255 at ISO 200, 253/254 at ISO 800, 251/252 at ISO 3200); the sensor
  saturates at 4045. ISO 3200's gray row is mostly left out by the JPEG spread filter (noise).

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
  Natural shots onto one curve (isotonic fit, residual 1.07 codes = the noise floor). So WB and
  `ColorMatrix` are the camera's first stages and grays then go through one curve.
- F: v 132 → 71, 249 → 115, 468 → 163, 879 → 210, 1651 → 234 (8-bit codes); middle gray
  (code 118) at v ≈ 264; v = 4045 (saturation) → 249.
- No stored 256-entry table fits with only an input scale (best 0x7E74E9BC, 2.71 codes). With
  input offset and output gain/offset free, several reach the floor (0x7E74EDBC 1.10,
  0x7E74E9BC 1.12, then 1.21–1.33), so the chart cannot identify the table. 0x7E74E9BC has the
  most natural parameters (input offset 0.3, output gain 0.247 ≈ 1/4, i.e. the 10-bit table to
  8-bit); its near-twin 0x7E74EDBC fits as well.
  The tone builder 0x7E553271 makes 10-bit curves from spline knots at run time (13a §3.3), so the
  real curve may not be stored at all. **Resolved by the static trace (§11.1): the base gamma is
  0x7E74E9BC, followed by a selected look curve.**
- A fixed-scale test of the art filters' channel responses against stored curves is inconclusive.

### 10.5 Tone and channels per setting (gray row vs F, codes; `out/modes_report.txt`)

| Setting | Gray rendering vs Natural | Channels |
|---|---|---|
| Vivid, Muted, Monotone, i-Enhance | same curve (±2–4) | equal |
| **Portrait** | **own brighter curve**: +4…+5 shadows, +11 from midtones up | equal |
| High Key / Low Key / Auto | own curves (High Key +15…+22 above midtones; Low Key −7…−12 shadows/mids, +7 highlights; Auto lifts shadows/mids +16…+20) | equal |
| Contrast −2 / +2 (Natural) | Contrast −2: shadows +3, upper mids −5, highlights 0. Contrast +2: shadows −6…−8, upper mids +8, highlights +20 | equal |
| Contrast −2 / +2 (Portrait) | same kind of change on Portrait's curve | equal |
| ISO 800 / 3200 | **same curve** (±1) | equal |
| WB CWB 3200K / Auto | same curve | equal (B +4…+6 in mids at 3200K) |
| Pop Art | own curve (shadows −5, highlights +11) | equal |
| Light Tone | own curve (shadows/mids +17…+28, highlights −25) | equal |
| **Pale&Light Color** | lifted | **channel-dependent** (B lifted ~10–40 codes more than R) |
| **Cross Process** | | **channel-dependent**: R and B ~33 codes below G in shadows, ~53 in mids; highlights R +39, G/B +55 |

So per-channel curves exist, but only in the art-filter path. Every normal Picture Mode moves
R, G and B together.

### 10.6 Colour per setting (chroma × and hue shift vs Natural, by hue sextant)
Sextants (BT.601 angle of CbCr): blue-magenta, magenta-red, red-yellow, yellow-green, green-cyan,
cyan-blue.

| Setting | Chroma × (6 sextants) | Hue |
|---|---|---|
| Saturation −2 / +2 | 0.79–0.81 / 1.20–1.23, uniform | no shift |
| Vivid | 1.14 1.18 1.13 1.14 1.11 1.20 | ±4° |
| Muted | 1.01 0.96 0.95 1.00 1.01 0.94 | ±5° |
| Portrait | 1.00–1.05 | ±2° |
| i-Enhance | 1.10 1.12 **1.24 1.21** 1.07 1.01 | ±5° |
| Gradation, Contrast, ISO, WB | 0.93–1.02 | ±2° |
| Pop Art | 2.0–2.3 | −11…+3° |
| Pale&Light | 0.53–0.66 (cyan-blue 0.84) | −16…+13° |
| Light Tone | 0.86–0.92 | ±3° |
| Cross Process | 1.27–1.46 | −7…+11° (+10/+11 in magenta-red, red-yellow) |

So the normal path has a **hue-dependent chroma gain** (Vivid and i-Enhance boost hue sectors
differently), and Saturation is a uniform scale. No normal mode rotates hue by more than ~4°.

### 10.7 What this means for Portra
(Superseded by §11.4: the "per-channel curves" turned out to be a split-toning stage.)
- **Portrait slot:** a custom luminance curve (Portrait already has its own) + saturation
  (+ possibly hue-dependent saturation, once its tables are found). No warm shadows / split toning.
- **Cross Process slot:** per-channel curves (warm shadows, cooler highlights) + hue shifts. Closest
  to what gr3-film-mods did on the GR III (it took over Cross Process's three curves).
- Next (no camera needed): phase 1b/1c static trace from the curve readers (0x7E56E837,
  0x7E56EB95), the art-code compares in the colour handlers (0x7E560B85, codes 85/167 = Cross
  Process), and the mode switch 0x7E70430B, to find where Portrait's curve, Cross Process's channel
  curves and the chroma gains are stored. Then phase 2: one flash that changes one of them visibly.

## 11. Static trace of the tone and colour stages (2026-11-10)

Addresses are E-PM2 v1.6 runtime addresses; disassembly via `tools/fwmap.py fn <addr> --dis`.

### 11.1 Tone: base gamma, then a selected look curve
(Corrected in §16.1: the look curve acts on luma, not per channel. Greys are unaffected.)
- **Curve selector 0x7E56E837** (called by the curve-block builder 0x7E56EB95 and by 0x7E570224).
  It returns one 256 × u16 table (0…1023):
  - art code 8–184 (P+79) → jump table **0x7E78C8E4** → one table per code (e.g. Pop Art I
    0x7E75E6F0, Pale&Light I 0x7E75E8F0, Light Tone 0x7E75EAF0, **Cross Process I (85, also movie
    code 87) 0x7E75F2F0, Cross Process II (167) 0x7E7616F0**);
  - Gradation High Key → 0x7E75E0F0, Low Key → 0x7E75E2F0;
  - otherwise Picture Mode family + Contrast: **Portrait (stored mode 4) has its own five tables
    0x7E75D6F0 / D8F0 / DAF0 / DCF0 / DEF0 (Contrast −2…+2)**; the other modes share
    0x7E75CCF0 … 0x7E75D4F0 (Contrast −3…+2, 0 = identity), shifted by a per-mode offset from the
    byte table 0x7E763F14 (modes 1–5: 0, 0, −1, 0, 0, so Muted renders as Contrast −1);
  - Contrast 0 of the shared family is the **identity** (0x7E75B8F0 / 0x7E75B6F0; 0x7E75B0F0 for
    a special flag).
- **The selected table is a second stage after a base gamma.** Model
  `out = LOOK(BASE(k·v)/4)/4` with BASE = **0x7E74E9BC** and one k (0.0621) fitted on Natural
  predicts Natural, Vivid, Portrait, High/Low Key, Contrast ±2 (Natural and Portrait) and Pop Art
  to **0.5–1.1 codes**, Muted to 1.6–1.9 (`analyze_pipeline.py`). The twin 0x7E74EDBC gives
  2.1–3.0 everywhere, so the base gamma is 0x7E74E9BC. Where the base gamma is selected (ISO,
  movie, ...) is not traced.
- A second-curve path in the builder (job flag 0x20000000, lookup table 0x7E78C9A8 keyed by art
  code − 66) adds a further table only for the module filters (Key Line, Dramatic Tone, Watercolor,
  Grainy Film, Fragmented). **Not for Cross Process.**

### 11.2 Hue-sector / chroma records
(Extended in §16.2: slots = R, G, B, C, M, Y; first record saturation, second hue.)
- **0x7E56D1C3** copies two records of six signed 16-bit values per setting into the engine block.
  Normal modes (P byte = Picture Mode): Natural and the others → all 0 (plus one flag-dependent 3);
  Vivid (18, 7, 24, 0, 8, 8) + (0, 5, 4, −1, −6, 0); Muted (−22, 7, −16, 0, 4, −8) + (3, 3, −3, 9, 8,
  10); Portrait (14, 3, 0, 5, 0, 0) + (−1, 3, 2, −2, 0, 0). Art codes via jump table 0x7E78C254:
  Pop Art I (53, 79, 100, 56, −1, 48) + (2, 3, 10, 0, 22, −10); **Cross Process I/II: neutral, same
  as Natural**. Records 0x7E768F8E–0x7E76966A; each setting has four variants (two flags).
- Reading (inferred): saturation / hue-area adjustments, zero for Natural (the reference), large
  for Pop Art (measured chroma ×2.0–2.3). The meaning of each of the six slots is not settled (Pop
  Art's slot 4 is −1, yet green-cyan is still boosted ×2.0).

### 11.3 Split toning (Cross Process, Pale&Light)
- With the traced look curve, Cross Process I is still off by ~30 codes in every channel and
  Pale&Light I by 24 in R. In YCbCr the gray row shows why:
  - **Pale&Light**: Y close to the look-curve prediction (highlights −14…−18); Cb rises to +10 and
    Cr falls to −18 toward the highlights, then both ease off near white;
  - **Cross Process**: Y steeper than its look curve (66 → 47, 136 → 154, 192 → 228), so another
    luminance stage; Cb −15, Cr −19…−22 in shadows/mids (green), about neutral to slightly blue
    near white;
  - Natural: Y, Cb, Cr within ~1 code of the prediction.
- So the art path has a **brightness-dependent Cb/Cr offset stage (split toning)**, the same kind
  of stage gr3-film-mods found on the GR III (toning tables). A shared curve with per-channel gains
  does not explain it (Cross Process 5.6 / 11 codes, vs 0.28 for Natural's single curve).
- Not keyed by art code directly: no function in the IMG library compares the art code with 85 or
  167 apart from the selectors above and 0x7E56D1C3's cache check. Likely keyed by the preset
  fields P+88–90 (09b), which Monotone's Pict. Tone (Sepia / Blue / Purple / Green) may share.
  **Next: find that stage's tables.**

### 11.4 What this means for Portra in the Cross Process slot
- Writable now: Cross Process I's look curve 0x7E75F2F0 (one 256 × u16 curve, all channels, after
  the base gamma), and its hue-sector records (currently neutral). These are fully modelled for
  the normal path.
- Needed for warm shadows / cool highlights: the split-toning stage (Cb/Cr by brightness), still to
  be located, and Cross Process's extra luminance stage (11.3) to be understood or neutralised.
- Fallback if the toning stage stays out of reach: the Portrait slot is now **fully modelled**
  (base gamma + Portrait look curves, 0.6–0.8 codes), i.e. a Portra-shaped tone curve + the
  hue-sector records, without split toning.

## 12. Model, fitter and probe build (2026-11-10)

### 12.1 Colour model of the normal path (`fit_look.py`, `out/fit_report.txt`)
(Superseded by §16.1: with the luma model one saturation fits a whole mode family; the table below is the old per-channel model.)
`c = LOOK(BASE(K·v)/4)/4` per channel, then chroma × SAT about BT.601 luma. SAT fitted per shot;
ΔE2000 model vs camera JPEG, all colour patches away from the 8-bit limits:

| Setting | SAT | mean | p95 |
|---|---|---|---|
| Natural | 1.077 | 1.22 | 2.90 |
| Vivid | 1.227 | 1.50 | 3.21 |
| Muted | 1.065 | 1.99 | 4.43 |
| Portrait | 1.112 | 1.12 | 2.29 |
| Natural Saturation −2 / +2 | 0.864 / 1.300 | 1.30 / 1.24 | 2.92 / 3.17 |
| Natural Contrast +2 | 0.932 | 0.94 | 1.91 |
| Low Key | 0.986 | 0.85 | 1.63 |

Limits: SAT changes with the look curve (Contrast +2 0.93, Low Key 0.99 vs Natural 1.08), so the
camera's saturation is not applied exactly where the model puts it; the hue-sector records (§11.2)
are not modelled (Muted and Vivid are the worst fits).

### 12.2 Saturation table (traced)
0x7E56DC71 picks a (Cb, Cr) gain pair: art codes via jump table 0x7E78C514 (Pop Art I 384, 384;
Cross Process I 281, 281 = default); normal modes by index = per-mode offset (bytes at 0x7E769696,
modes 1–5: 1, 0, 0, 0, 0, so Vivid = +1 step) + Saturation setting + 5, clamped 0…10, through a RAM
pointer table (0x602AB…); the steps seen are 282, 310, 338, … (+28). The gains are then scaled by
144/256 and 182/256.

### 12.3 Cross Process: what is still missing
- `art_stl2ycc_pass3` (0x7E72C018) gives Cross Process (codes 85, 167) an **extra buffer**: it calls
  0x7E5A135C (the second buffer id of the frame record) and stores its address at (P+4)→+16. No
  other ISP-only filter gets one. So Cross Process's toning / extra luminance stage (§11.3)
  probably works from a second image buffer, not from a small table keyed by art code.
- Other art-code-keyed stages seen but not decoded: 0x7E56F63C / 0x7E56F113 (hash tables
  0x7E78CDA8, 0x7E78CE28; 12-byte record pairs 0x7E769A98…), 0x7E56FA27, 0x7E56CB32, 0x7E566C94.
- The probe (12.5) isolates this stage on the camera: with the look curve set to identity, what
  remains in Cross Process I is the toning alone.

### 12.4 Fitter (`fit_look.py --lut FILE.cube --input vlog`)
Fits a monotone look curve (24 knots) and a saturation to a target LUT by weighted ΔE2000 over a
gray ramp (−5…+2.5 stops) and 4,000 random natural colours; reports stock modes vs the fit; writes
`patches/<name>.json` for the **Portrait** slot (all five Contrast tables; the Contrast steps keep
their stock change relative to Contrast 0). Tested end to end with a synthetic LUT (stock Portrait
3.7 → fitted 0.36 mean ΔE with free saturation, 1.72 with Portrait's stock saturation; the spec
builds). Saturation is reported but not yet written into the patch (per-mode offset byte or
hue-sector record: to decide once the target is in). Tone-only by construction: no split toning.

### 12.5 Probe build `patches/history/curve-probe-1.json` → `build/curve-probe-1.BIN`
sha256 `c658d0620c0a0b89adae8b619ce7b4503ab67b022ebb2bb44bdf1decd410ee68`; 590 bytes differ from
stock; all block checksums OK; data only (two 512-byte tables). **Not flashed.**
1. Cross Process I look curve 0x7E75F2F0 := identity → shows its toning stage alone.
2. Portrait Contrast 0 look curve 0x7E75DAF0 := the Low Key curve → Portrait's grays must equal
   Natural + Low Key (shot 0196) to ~1 code.
Camera steps: flash; RAW Data Edit PB090221 with Picture Mode Portrait, then with Cross Process I;
copy both JPEGs; reflash stock (or keep).

### 12.6 To get the Portra target
Either allow `pip install git+https://github.com/andreavolpato/spektrafilm@3bb2c2d` in the venv
and run `spektrafilm-lut build --film kodak_portra_400 --print kodak_portra_endura --input vlog
--output srgb --resolution 33`, or put any `.cube` (V-Log in, sRGB out) in `out/` and run
`fit_look.py --lut`.

## 13. Portra fit, Portrait slot, tone only (2026-11-10)

- spektrafilm 0.3.4 (3bb2c2d) installed in the venv (it downgraded rawpy to 0.26.1 and Pillow to
  12.3; the scripts still run). LUT baked with the command in §2 (Panasonic V-Log on V-Gamut in,
  sRGB out, 33³): `out/lut/…/lut_v034_portra400_portraendura.cube`, sha256 `842310c3…43d09a4` (not
  the hash in GRKit's manifest, `e2d43beb…`; bake options or platform differ, not investigated).
  `fit_look.py` converts linear sRGB to V-Gamut before the V-Log curve.
- Target grays are not neutral (18 % gray → 112.6 / 115.5 / 115.5), which one shared curve cannot
  follow; that is the floor of the gray error below.
- **Predicted ΔE2000 vs the Portra target** (gray ramp mean / colours mean / colours p95;
  `out/fit_report.txt`):

  | Rendering | gray | colour | p95 |
  |---|---|---|---|
  | stock Natural | 2.50 | 3.64 | 6.50 |
  | stock Natural, Saturation −2 (best stock setting tried) | 2.50 | 3.22 | 5.79 |
  | stock Portrait | 4.66 | 6.15 | 9.10 |
  | **fitted curve, Portrait's stock saturation** (= the patch as built) | 1.52 | 2.57 | 5.69 |
  | **fitted curve, saturation ×0.906** (≈ the patch + Saturation −2 in the menu) | 1.52 | 2.29 | 5.12 |

  So the tone-only patch is a real but modest gain over the best menu setting (3.2 → 2.3–2.6).
  The rest needs colour stages (split toning, hue shifts) that this slot's model does not have.
  The menu comparison covers the eight stock settings measured, not every combination.
- **Build:** `patches/history/film-portra.json` → `build/film-portra.BIN` (Portrait's five look curves,
  Contrast −2…+2; nothing else). **Not flashed.** Use it with Portrait, Saturation −2.
- Not done: the "Portrait" → "Portra" menu label; saturation written into the firmware (the
  per-mode offset byte, §12.2, is traced but untested).

## 14. Cross Process: per-channel base gammas (2026-11-11)

### 14.1 Trace
(Variant selection: partly traced in §16.4.)
- **0x7E56B790** (callers 0x7E56AEAF, 0x7E570224) returns three base-gamma pointers (R, G, B). It
  looks the art code up in the hash table 0x7E78C154 (key = code − 70): most codes and all normal
  modes → one record for all three channels (default 0x7E78B39C, or 0x7E78B3BC when a flag is set);
  Pale&Light 71/80 → 0x7E78B3DC; Light Tone 72/81/147/150 → 0x7E78B3FC; Pop Art II 102/103 →
  0x7E78B47C; **Cross Process I 85/87 → R 0x7E78B41C, G 0x7E78B43C, B 0x7E78B45C; Cross Process II
  167/168 → 0x7E78B49C / B4BC / B4DC.**
- A record is 8 pointers = 4 variants × 2; 0x7E56B732 picks the variant from a mode byte and the
  pair member from a flag. Default record: 0x7E74E7BC / **E9BC**, 17BC / 19BC, 47BC / 49BC, 77BC /
  79BC (so the "sets of ~30 curves" of §5 are these four variants). Shoot 1 used the second member
  of variant 0 everywhere; what selects the other variants is not traced.
- Cross Process I's 24 tables are referenced only from its three records.

### 14.2 Check against shoot 1 (gray row rms, codes; k fixed from Natural)
| Setting | old model (shared base 0x7E74E9BC) | with its own base gamma(s) |
|---|---|---|
| Light Tone | 9.42 | **0.86** (0x7E74F5BC) |
| Cross Process I | 28.89 | **3.40** (R 0x7E74FDBC, G 0x7E74FFBC, B 0x7E7501BC) |
| Pale&Light I | 16.18 | 14.78 (0x7E74F1BC): something else still differs |
The "split toning" of §11.3 is therefore three different base gammas, not a Cb/Cr stage. Cross
Process's saturation gain (281) and hue records are neutral (§11.2, §12.2). Not explained: the
remaining 3.4 codes, and the extra buffer of §12.3. The probe below settles whether anything else
in Cross Process differs from Natural.

### 14.3 Verification build `patches/history/curve-probe-2.json` → `build/curve-probe-2.BIN`
sha256 `0d08b3508374b46c2c47601c05e535d7050ad8e9acae94db6317fe24e7623a75`. Data only, 26 ops:
Cross Process I's 24 base tables := the default record's tables, look curve 0x7E75F2F0 := identity,
saturation pair 0x7E7696B4 := 338 (the Saturation +2 step). **Prediction: Cross Process I renders
exactly like Natural with Saturation +2.** Test on this firmware: RAW Data Edit PB090221 once as
Cross Process I and once as Natural with Saturation +2; the two JPEGs should match. Supersedes
curve-probe-1.

### 14.4 Portra build `patches/history/film-portra-xp.json` → `build/film-portra-xp.BIN`
(Re-scored with the corrected model in §16.3: unchanged, because this build's look curve is the identity. A variant with a fitted luma curve is `film-portra-xp2`.)
sha256 `8dacf8c52947805f71070bb2b2498e7a6e109b81d2874e473d87843a1cdf5386`. Data only, same 26
locations. `fit_look.py --slot crossprocess`: three monotone curves G_c (20 knots each) on the
base-gamma output + saturation, weighted ΔE2000 with GRKit's sample weights (gray ramp 150,
ColorChecker 24 at −2…+2 EV 20, skin patches 60, 4,000 random natural colours 1), exposure 0,
V-Log/V-Gamut input. Each of the 24 tables = G_c applied to the matching default variant, so the
variants keep their stock behaviour. Saturation gain written: 245 (Natural 282).

| ΔE2000 vs target | gray | ColorChecker ±2 EV | hold-out mean | hold-out p95 |
|---|---|---|---|---|
| **fit, Cross Process slot** | 0.60 | 4.40 | **2.11** | 5.39 |
| best of 140 menu settings (Muted Contrast +1 Saturation −2 ≈ Natural Saturation −2) | 2.50 | 5.40 | 3.48 | 6.03 |
| stock Natural | 2.50 | 6.27 | 3.89 | 6.55 |
| stock Portrait | 4.66 | 8.60 | 6.63 | 8.91 |
Menu grid = Natural / Vivid / Muted / Portrait × (Contrast −2…+2 or High/Low Key) × Saturation
−2…+2; WB shift not included. GRKit's own Portra fit reaches 1.41 with a matrix and hue sectors,
which this camera's slot does not offer (the hue records of §11.2 are not modelled).
Assumptions still unverified on camera: saturation ∝ gain (checked on Saturation ±2 only), 18 %
gray ↔ v = 264, and that nothing else in Cross Process differs (14.3 tests the first and last).
Art-filter side effects of the slot: RAW-only becomes RAW+JPEG; Colour Space locked to sRGB; the
menu still says "Cross Process" (label not patched); Cross Process II is untouched.

### 14.5 Why not Portrait with per-channel curves, and why no new menu entry
- Normal modes all take the default base-gamma record; 0x7E56B790 is not given the Picture Mode,
  only the art code. Per-channel curves for Portrait need a **code** patch there (a new branch
  and a way to read the mode), not a data edit.
- A new menu entry is possible in principle but is also a code-and-tables project: the Picture
  Mode list is fixed ROM data sized for 19 entries in several places (mcon raw/gui arrays
  0x7E844CC0 / 0x7E83F70C and the record's size fields, label table 0x7EF1F4D6, show-flag table
  0x7E826AFC with one settings id per entry, colorTone hash 0x7EC4A864, Exif writer, the info
  509/510 copies for RAW edit, ART BKT lists; 09a §1–2). Each needs relocating or extending, plus a
  new stored value handled by every selector above. The earlier "impossible" (from the ep5 report)
  was too strong; "not a data-only change" is the accurate statement.

### 14.6 Build audit and label (2026-11-11)
- Decoded diff of both builds against stock: every changed payload byte lies inside the 26
  intended ranges (block 0: the 24 base tables 0x7E74F7BC…0x7E7593BB, look curve 0x7E75F2F0, the
  4-byte saturation pair 0x7E7696B4); blocks 1–3 and the OM tail are identical; the only other
  change is block 0's trailer (its checksum word). File size unchanged.
- Label: `patches/history/label-portra.json` renames "Cross Process" → "Portra 400" (20 English copies in
  block 1, NUL-padded to the same length; nothing blocked this earlier, it was simply left out).
  The label is shared by Cross Process I and II, so II (unchanged, still the stock look) also reads
  "Portra 400"; translated labels in other languages are unchanged.
  `build/film-portra-xp-labelled.BIN` = film-portra-xp + label, sha256
  `6a35cb3b4c6764f5f34e1794487fcd818c9756012577b9693f71f48bed367837`; differs from the unlabelled
  build only in block 1 (260 bytes) and its checksum. NOT camera-tested: a NUL-padded shorter
  string is new (pixel-hacking used an equal-length word).

## 15. Camera result: film-portra-xp-labelled flashed (2026-11-11)

- Flashed by the user (the verification probe was skipped). Files: `shots/PB090223.JPG` = RAW
  Data Edit of PB090221 as Cross Process I; `shots/PA310224.JPG` = the same for PA310087 (cloudy
  outdoor scene; stock Portrait JPEG PA310087.JPG for comparison, `out/compare_PA310087.jpg`).
- **Camera vs prediction (chart, PB090223 vs the fitted model):** gray row rms 1.96 / 1.76 / 1.53
  codes (R / G / B), ΔE2000 1.11; colour patches ΔE2000 mean 1.64, p95 4.46 (n = 192). The same
  check on the stock Natural JPEG gives 0.68 / 1.56, so the patched slot behaves as modelled. The
  table locations of §14 are confirmed on camera. Small residual: blue reads ~2–3 codes above the
  prediction in the mid-tones.
- **Camera vs Portra target on the monitor chart:** gray 1.10, colour 5.80; stock Natural on the
  same shot: 4.02 and 8.89. The chart's colours are far more saturated than the fit's samples, so
  the colour figure is not comparable with the hold-out 2.11 of §14.4.
- Real scene: lower contrast, lifted blacks, a gray (not white) overcast sky, less saturated reds;
  no colour cast in neutrals.
- Not yet confirmed: the "Portra 400" label on screen; live shooting (only RAW Data Edit tested).

## 16. Corrections after the Caduceus research (2026-11-11)

Source of the suggestions: `../../../research_notes/caduceus-om3-ep7.md` (E-P7 / OM-3 / PEN-F docs).
Everything below marked **verified** was tested on our own data; **claim** = taken from those docs.

### 16.1 The look curve acts on luma (verified on shoot 1) — `analyze_lumalook.py`
Model A (old): `out_c = LOOK(b_c)`, chroma × SAT. Model B: `Y = 0.299 b_R + 0.587 b_G + 0.114 b_B`,
`out = LOOK(Y) + SAT·(b − Y)`, with b = per-channel base-gamma output. Colour patches away from the
8-bit limits, one saturation per family, ΔE2000 model vs camera (`out/lumalook_report.txt`):

| Family (settings) | A: mean ΔE, per-setting saturation | B: mean ΔE, per-setting saturation |
|---|---|---|
| Natural (Contrast 0 / −2 / +2, High Key, Low Key) | 1.71; 1.09 / 1.19 / 0.94 / 0.95 / 1.01 | **0.89**; 1.07 / 1.07 / 1.09 / 1.09 / 1.08 |
| Portrait (Contrast 0 / −2 / +2) | 1.92; 1.17 / 1.30 / 1.00 | **0.99**; 1.11 / 1.10 / 1.11 |
| Light Tone | 1.75; 1.68 | **1.24**; 1.07 |
| Cross Process I (stock) | 2.12; 0.93 | **0.94**; 1.06 |

The saturation drift of §12.1 disappears and every setting lands on ≈ 1.07 (Portrait 1.11: its
six-axis record). BT.601 luma fits slightly better than BT.709 (0.89 vs 0.95, 0.94 vs 1.19).
`fit_look.py` now uses model B (`--model channel` keeps A); `analyze_pipeline.py` is unchanged
(greys only, where A = B). The flashed result PB090223 cannot tell A from B: that build's look
curve is the identity.

### 16.2 The six-value records (partly verified) — `analyze_sixaxis.py`, `analyze_sixaxis_model.py`
- Records per setting and variant: `out/sixaxis_records.json`. Normal modes have four variants
  (two flags); they differ only in slot 1 (+3 in both records) and, for Muted, hue slot 3 (9 vs
  7). Art codes have one record pair. Which variant stills use is unknown; all analysis is
  relative to Natural, where the +3 cancels.
- Method: with model B and the setting's saturation gain, compare predicted and measured (Cb, Cr)
  per patch; chroma ratio and hue rotation by hue, relative to Natural.
- **Saturation ∝ gain: verified** (Saturation ±2: ratio 1.00 ± 0.02 at every hue; and on camera,
  §16.3).
- **Axes (verified to ±10° for three slots):** free fit of six axis angles on Vivid + Muted +
  Portrait puts slot 0 at 110–111° (red = 108.7°), slot 2 at 336–349° (blue = 351.3°), slot 5 at
  167–169° (yellow = 171.3°) in the BT.601 angle atan2(Cr, Cb); the best run gives all six at
  [111, 233, 349, 281, 31, 168] ≈ **R, G, B, C, M, Y**. Slots 1, 3, 4 (G, C, M) carry small stock
  values and are not pinned down by the data alone.
- **Units (approximate):** first record ≈ +0.5 % chroma per unit (fit 1/187; 1/256 fits as well);
  second record ≈ −0.4° per unit in atan2(Cr, Cb) (the sign convention of the Caduceus projects is
  itself disputed, claim). Interpolation between axes assumed linear.
- **Forward model check** (axes fixed at the primaries, units fitted on Vivid + Muted + Portrait;
  ΔE2000 model vs camera, `out/sixaxis_model_report.txt`): Vivid 1.51 → 1.35, Muted 2.23 → 1.62,
  Portrait 1.07 → 0.94; not fitted: Pop Art I 7.87 → 5.65 (n = 21, most patches clipped), Light
  Tone 1.25 → 1.30. **Not good enough to fit with:** the gain is small, Light Tone gets no better,
  Muted stays well above Natural's 0.95. The stage is therefore not in `fit_look.py`, and the
  records stay at Cross Process's neutral values in every build. To pin it down: a probe that
  sets one slot at a time to a large value (data only), one RAW Data Edit each.

### 16.3 The flashed build re-scored, and `film-portra-xp2` — `check_flashed.py`
- PB090223 (flashed `film-portra-xp-labelled`): camera vs model unchanged (grey 1.11, colour 1.64,
  p95 4.46; grey-row rms 1.9 / 1.8 / 1.5 codes). **Saturation on camera: 0.937; Natural on the same
  RAW 1.078; ratio 0.869 = 245 / 282 exactly.** So the written gain produced the fitted saturation
  (0.936): saturation ∝ gain is verified at a third value. The residual ~1.5–2 codes (blue +2–3 in
  the mid-tones) is not explained; Natural's is ~0.8.
- The gain is now derived with a ΔE-based Natural saturation (1.070–1.078); an RGB-error estimate
  (1.054) would have written 250 instead of 245.
- Refit with model B and the same samples: identical to §14.4 (hold-out 2.11) when the look curve
  is the identity. Letting the luma look curve vary as well (`--free-look`): loss 1.17 → 0.96,
  grey 0.60 → 0.35, ColorChecker 4.40 → 4.37, hold-out 2.11 → **2.01** (p95 5.39 → 5.35),
  saturation 0.865 (gain 228). A small predicted gain.
- **`patches/history/film-portra-xp2.json`** (26 ops: 24 base tables, look curve 0x7E75F2F0 = fitted luma
  curve, saturation 228) + `label-portra` → **`build/film-portra-xp2-labelled.BIN`**, sha256
  `601817f28cfcb82b57255210c11e269812d8dba651aa831774988c96c2a69e79`. All four block checksums OK;
  decoded diff vs stock: block 0 7,396 bytes, all inside the 26 ranges; block 1 260 bytes, all
  inside the 20 "Cross Process" labels; blocks 2–3 and the tail identical; only the two trailers
  (checksums) otherwise. **Built, NOT camera-tested.** Its luma curve relies on model B holding in
  the Cross Process path (verified on stock Cross Process I, 0.94). The flashed build stays valid.

### 16.4 Base-gamma variants (0x7E56B790 / 0x7E56B732, partly traced)
Caller 0x7E56AEAF passes: P+87 (non-zero → the alternative default row 0x7E78B3BC, whose second
member is the "twin" 0x7E74EDBC of §10.4); bit 0 of the flag word P+20 (the pair member: set →
second table, e.g. 0x7E74E9BC); bit 0x800 of P+20 (→ row 0x7E78B4FC); the art code; and **P+99,
which picks the column** (low three bits 4 / 5 / 7 and top three bits 0x80 / 0xA0 / 0xC0 choose
among the four). The Caduceus docs describe the columns as job types (still / live view / movie /
recording) and the pair as a request flag (claim). On the E-PM2 the column comes from P+99, not
from the job's op type (job+194); what P+99 holds was not traced, so the job-type reading is
**unverified**. All 24 Cross Process I tables are patched, so every column carries the look.

### 16.5 Still unverified
Six-axis units, hue sign and the G / C / M slots; the +3 variants; what P+99 and P+87 are; the
1.5–2 code residual of the patched slot; live shooting, movie and high ISO in the patched slot
(only RAW Data Edit tested); `film-portra-xp2` on camera.

## 17. Real chart check and the six-axis probe (2026-11-11)

### 17.1 SpyderCheckr 24, live captures on the Portra build (`check_spyder.py`, shots PB110225–0237)
Indoor lamp light. 0225–0233: Natural brackets at WB 5300K (strong orange cast; not analysed).
0234 / 0235: Natural / Portra at 5300K. 0236 / 0237: Portra / Natural at Auto WB (the useful pair).
Patch centres from hand-picked corners; v from each file's own WB and ColorMatrix.

| Shot | camera vs model, gray / colour (ΔE2000) | camera vs Portra target, gray / colour / max |
|---|---|---|
| 0237 Natural, Auto WB | 1.06 / 0.76 | 3.80 / 6.81 / 10.55 |
| 0236 Portra, Auto WB | 1.07 / 0.60 | 2.06 / 5.18 / 9.40 |
| 0234 Natural, 5300K | 0.69 / 0.64 | 6.22 / 6.68 / 11.68 (19 patches) |
| 0235 Portra, 5300K | 0.58 / 0.75 | 6.00 / 5.55 / 15.33 (21 patches) |

- **Live shooting behaves as modelled** (0.6–1.1), on real reflective colours and under Auto WB
  with its different ColorMatrix. So RAW Data Edit and live capture agree, and the patched slot
  works outside the conditions it was measured in.
- **Against the target, on real colours, the build helps only modestly: 6.8 → 5.2.** Worst
  patches (0236): yellow B3 8.8, orange C1 8.8, yellow-orange C6 9.4 (target has less green: it
  turns yellow toward orange), blues C2 7.7 and B6 7.2 (target has more green: blue toward cyan),
  lavender D2 6.8. Grays 1.1–2.9. These are hue rotations, which per-channel curves cannot make:
  the per-colour (six-axis) stage is what is missing.
- The 5300K shots under lamp light are far outside the target's assumptions (grays are orange).

### 17.2 `patches/history/sixaxis-probe-1.json` → `build/sixaxis-probe-1.BIN`
= film-portra-xp + label-portra + the probe, sha256
`58e0aeddcf56a1ba6bd7bbbabd77cdb67930358f90345a75913b0817de9ea397`; differs from the installed
build in 154 bytes, all inside the records 0x7E768FBE–0x7E7692BD; checksums OK. NOT flashed.
All four variants of each record written alike (saturation six, then hue six):
Vivid (40, 0, 0, −40, 0, 0) + (0, 20, 0, 0, −20, 0); Muted (0, 40, 0, 0, −40, 0) + (0, 0, 20, 0, 0,
−20); Portrait (0, 0, 40, 0, 0, −40) + (20, 0, 0, −20, 0, 0). Values stay inside the range stock
uses (Pop Art: 100 and 22). Each record address is referenced twice in block 0 (second user not
identified; another mode may share them). Procedure: on the installed build RAW Data Edit PB090221
as Vivid, Muted, Portrait; flash the probe; repeat the three edits; reflash the Portra build.

## 18. Six-axis probe result and first six-axis Portra build (2026-11-11)

### 18.1 Files
The user flashed `sixaxis-probe-1` and sent the card as a zip (unpacked, merged, zip removed;
192 unrelated personal RAW+JPEG files moved to `scenes/`, git-ignored). RAW Data Edits:
before (Portra build) PB090238 / 239 / 240 = Vivid / Muted / Portrait of PB090221, PB110241–243 the
same for the Spyder shot PB110237; after (probe) PB090244–246 and PB110247–249. Probe flash: OK,
camera boots (`docs/camera-log.md` to be updated with the user's timings).

### 18.2 What the stage is (`analyze_probe6.py`, measured on the chart, before vs after)
- Gray row unchanged (≤ 2 codes). Colours move by up to 33° of hue and ×0.75–1.35 of chroma, each
  change confined to a band of hues; luma also changes (up to −20 codes).
- A single 3×3 matrix does not explain a mode's change (residual 4.6–6.0 codes of 8–11); **six
  sectors with a linear map each do (1.2–1.3 codes; Muted 3.1)**, with sector borders at the
  CbCr angles of the pure colours. So: a six-axis colour corrector on the output YCbCr. A colour
  is split onto its two neighbouring axes (M 52°, R 109°, Y 171°, G 232°, C 289°, B 351° in BT.601
  CbCr); each axis has a gain, a rotation and a luma term.
- **Slot order is R, G, B, Y, C, M** (not R, G, B, C, M, Y as §16 guessed), from which axis each
  probe value moved: hue slot 0 (+21) turned R by −25°, slot 1 (+18) G by −23°, slot 2 (+23) B by
  −32°; hue slots 3 / 4 / 5 (−18 / −14 / −30) turned Y / C / M by +7° / +4° / +10°; saturation
  slot 3 (−40) cut Y to 0.85, slot 5 (−40) cut M to 0.83, slot 4 (−44) barely changed C's chroma
  (0.97) but lowered its luma.
- Provisional units (one data point each; linearity and the opposite sign untested):
  hue about −1.2…−1.4° per unit for R, G, B and −0.3…−0.4° per unit for Y, C, M (positive value =
  negative CbCr angle); chroma about +0.2…0.6 % per unit; luma terms in `fit_sixaxis.py` UNIT.
- Forward model (`fit_sixaxis.py`) on the probe itself, ΔE2000 predicted vs real "after":
  Vivid 1.25, Muted 2.45, Portrait 1.37 (no model: 2.90, 4.20, 3.47). In-sample.
- Cross Process I has its own records: saturation **0x7E7694FE**, hue **0x7E76950A** (Cross
  Process II: 0x7E769622 / 0x7E76962E). After loading them, 0x7E56D1C3's Cross Process branch
  (0x7E56D5F5…) runs extra code that reads the P+16 buffer and P+54 / P+56; not decoded, so the
  records may not act exactly as in the normal modes.

### 18.3 `patches/history/sixaxis-portra-1.json` → `build/film-portra-xp3-labelled.BIN`
Curves and saturation as flashed (film-portra-xp), label as before, plus Cross Process I's records:
saturation (R G B Y C M) = (21, −40, 39, −27, 16, −12), hue = (−2, 20, 14, 20, −9, 20). Fitted with
the provisional model on the GRKit-weighted samples plus the real Spyder shot (camera output of
0236 as the base), limits ±40 / ±20. Four values sit on a limit, and several use a sign the probe
did not exercise, so this is an experiment, not a finished look.

| ΔE2000 vs target (predicted) | gray | ColorChecker ±2 EV | hold-out mean / p95 | Spyder shot: all / colours / worst |
|---|---|---|---|---|
| as flashed | 0.60 | 4.40 | 2.11 / 5.38 | 4.40 / 5.18 / 9.40 |
| with the six-axis values | 0.62 | 2.40 | 1.40 / 3.40 | 2.04 / 2.32 / 4.36 |

sha256 `de7a7079e59c5d5ab539ce84f29cf59795e4afb0af99a69342e4790d818a9971`. Differs from the first Portra build only in the 24 record bytes;
Vivid, Muted and Portrait are stock again. NOT camera-tested.
Test: RAW Data Edit PB090221 and PB110237 as Portra 400; the Spyder result is compared with the
prediction above, and the chart result recalibrates the units.

## 19. Camera result: film-portra-xp3-labelled (2026-11-11)

Flashed by the user. Files: PB090250 = RAW Data Edit of PB090221 (monitor chart), PB110251 = RAW
Data Edit of PB110237 (SpyderCheckr, Auto WB, lamp light), PB110252 = a new RAW+JPEG capture.
SpyderCheckr, ΔE2000 vs the Portra target (24 patches / 18 colours / worst):

| | all | colours | worst |
|---|---|---|---|
| first Portra build (model on this RAW) | 3.95 | 4.95 | 9.62 |
| xp3 predicted | 1.85 | 2.23 | 4.50 |
| **xp3 measured (PB110251)** | **2.30** | **2.58** | **4.38** |

Grays 1.44 (were about 1.0). Camera vs prediction 2.03 (colours 2.21, worst 3.92): the provisional
six-axis model is usable but its units are off by enough to matter. Largest improvements: orange
C1 9.5 → 1.6, yellow-orange C6 9.6 → 2.7, blue C2 7.4 → 3.0, yellow B3 9.0 → 3.5. Slightly worse:
red B4 3.1 → 4.4, C3 2.2 → 3.3, D1 2.7 → 3.3. Cyan B1 reads R = 0 (clipped) against a target of 31.
Not yet analysed: PB090250 (to recalibrate the per-axis units from the 216 chart colours) and
PB110252. Next: refit the units from PB090250 + PB110251, then refit the 12 values.

## 20. Recalibration of the six-axis model (2026-11-11, `fit_sixaxis2.py`)

- Calibrated on four before/after chart pairs (Vivid, Muted, Portrait probe; Cross Process I
  first build → xp3: PB090223 → PB090250), with separate gains for positive and negative values, a
  perpendicular (shear) hue term and luma terms per axis; checked on SpyderCheckr pairs it did not
  see.
- **It did not get meaningfully better.** ΔE2000 predicted vs real "after" (old → recalibrated):
  Vivid 1.25 → 1.37, Muted 2.45 → 2.33, Portrait 1.37 → 1.23, Portra xp3 2.20 → 2.19. Spyder check:
  Vivid 1.53, Portrait 1.18, Portra xp3 2.46, Muted 3.00 (no better than no model, 3.03). So the
  model's floor is about 2 ΔE; the limit is its form, not its units. Residuals on the xp3 pair are
  largest for greens (Cb −7.5 codes at CbCr 210–240°) and blues (Cr −4 at 300–30°), the axes whose
  xp3 values sit on the probe's limits; near-neutral patches do not move (≤ 0.2 codes), so the
  gray change seen in §19 is not from this stage.
- Hue at ±20 units (recalibrated): R −26° / +41°, G ∓31°, B ∓35°; Y, C, M only ∓5…8°. Gains
  +0.1…0.6 % per unit. (R's negative side and several others rest on small values.)
- Refit with it ("xp4"): saturation (14, −40, 39, −29, 12, −13), hue (−1, 18, 12, 20, −9, 20), almost
  the xp3 values. Predicted Spyder colours 2.65 → 2.43, hold-out 1.44 → 1.38: **inside the model's
  own error, so not a reason to flash.** Built anyway: `patches/history/sixaxis-portra-2.json` →
  `build/film-portra-xp4-labelled.BIN`, sha256
  `24e24bf320484e9f5d029cdc16a362b607c477a55b93263c94abd9f380fe7e3d`, checksums OK, NOT flashed.
- **Fresh live capture PB110252 (xp3, SpyderCheckr, Auto WB, lamp):** ΔE2000 vs target all 2.31,
  colours 2.77, grays 0.92, worst 4.50 (red B4; then cyan B1 4.2, brown D6 3.9, green D3 3.6).
  Confirms §19 on an independent RAW in live shooting.
- What would move it further: a model of the stage that explains the remaining ~2 ΔE (the Cross
  Process branch's extra code at 0x7E56D5F5, and behaviour at large values), or direct search on the
  camera (several builds with varied values scored on the Spyder), or accepting ~2.5 as the result.

## 21. The six-axis stage acts before the gamma, on RGB by rank order (2026-11-11/12)

Three background investigations (outputs: `CODE_DIG.md`, `../../../research_notes/olympus-color-pipeline-parallels.md`,
`../../../research_notes/camera-color-pipelines-general.md`) pointed to the same correction; tested here.

### 21.1 Test (`fit_sixaxis3.py`)
Model: primary component p = max − mid on the axis of the largest channel (R, G, B), secondary
q = mid − min on Y, C or M; out = in + p·(S a + H b) + q·(S a + H b), with a, b unknown RGB
3-vectors per axis (36 unknowns, linear least squares), applied to **linear RGB after the colour
matrix** (before the base gamma). All four before/after pairs are RAW Data Edits of PB090221, so
the pre-stage signal is known from the raw. ΔE2000 predicted vs real "after":

| Pair | no model | output-CbCr model (§20) | rank-order, linear: fit / held out | rank-order, post-gamma: fit / held out |
|---|---|---|---|---|
| Vivid | 2.99 | 1.38 | 1.16 / 1.37 | 1.41 / 1.73 |
| Muted | 3.84 | 2.09 | 1.15 / 2.09 | 1.98 / 2.87 |
| Portrait | 3.52 | 1.25 | 1.11 / 2.53 | 1.26 / 3.96 |
| Portra xp3 | 3.84 | 2.25 | 1.41 / **1.12** | 2.17 / 2.27 |

- Linear domain wins over post-gamma and over the output model, with one set of vectors and no
  separate treatment of signs. Held out, the three probe pairs predict the Portra pair to 1.12
  (2.25 before). Leaving out a probe pair is worse (2.1–2.5) because each probe is the only data for
  some coefficients.
- **Independent check: the SpyderCheckr xp3 result (another RAW, real patches) is predicted to
  1.32 (colours 1.43); the output model gave 2.46.**
- Fitted directions (per unit, ×1000, RGB): saturation R (5.9, −0.3, −0.2), G (−0.4, 4.2, 0.3),
  B (0.1, −0.8, 3.0), Y (8.5, 7.3, 0), C (0.6, 4.5, 3.9), M (9.0, −1.2, 3.2); hue R (−0.2, −7.6, 6.1),
  G (7.3, 1.7, −4.5), B (−7.9, 6.2, 0.2), Y (11.1, −6.1, −0.2), M (−4.9, −0.3, 6.3), C (1.3, 9.5, 5.3:
  poorly determined, only small C hue values were exercised). I.e. saturation adds the axis's own
  colour, hue trades one neighbouring channel for the other, in steps near 1/128 per unit.
- The scene-adaptive hue of the Cross Process branch (CODE_DIG) does not show in these chart and
  Spyder shots (the fixed model explains them to 1.1–1.4); whether it acts on blue-dominated
  scenes is untested.
- Corrections: §18.2's "six sectors in output CbCr" and §20's units are superseded by this.

### 21.2 Refit (`fit_sixaxis4.py`) → `patches/history/sixaxis-portra-3.json` → `build/film-portra-xp5-labelled.BIN`
Curves and saturation as flashed; 12 values refitted with the new model, inside the probed range:
saturation (R G B Y C M) = (13, −40, 20, −22, 39, −21), hue = (−2, 20, 20, 20, −12, 20).

| ΔE2000 vs target | hold-out mean / p95 | ColorChecker ±2 EV | Spyder all / colours / worst |
|---|---|---|---|
| xp3, predicted by the new model | 1.49 / 3.61 | 2.69 | 2.24 / 2.72 / 4.88 |
| xp3, measured on camera | | | 2.30 / 2.58 / 4.38 |
| **xp5, predicted** | 1.35 / 3.25 | 2.31 | 1.82 / 2.19 / 3.89 |
| wider limits ±64/±32 (not built) | 1.37 / 3.33 | 2.05 | 1.59 / 1.90 / 2.98 |

sha256 `c3cab6b0ccd1787455442d0f9f584c8001077e98e30c3c326750af3288e7d6ec`; differs from the first Portra build only inside the two records; checksums OK.
NOT camera-tested. Six of the twelve values sit on the probed limits.

### 21.3 Not done yet
Search for E-M10-style per-mode chroma curves (100-byte x[16], y[16], slope[17] records); decoding
the 5,764-byte parameter block in the ORFs (nine unidentified 3×3 matrices); the Olympus Viewer 3
edited-ORF test; the adaptive-hue check on a blue-sky ORF; the pre-gamma 3×3 matrix slot that Pop Art
uses (0x7E56C603, CODE_DIG); a joint refit of curves and six-axis values.

## 22. Remaining checks, the art matrix, and builds xp6 / xp7 (2026-11-12)

### 22.1 Scene-adaptive hue (CODE_DIG §2), estimated offline
Re-implemented the statistics approximately on full raws (the camera uses a small buffer and
thresholds not reproduced here): added hue units 0 for the Spyder shots (R, Y dominate), about 4–5
for the monitor chart PB090221 (cancels in before/after pairs), and among 16 of the user's outdoor
RAWs: 0 for eleven, 1–7 for three, **16 (the maximum) for one cyan/blue-dominated frame**. So it is
inactive on the calibration shots but real on sky-heavy pictures, where it would add up to 16
units to B and C hue on top of the look's own 20. Switch-off: `patches/xp-adaptive-hue-off.json`
changes two compare immediates in 0x7E5460F0 (0x7E546161: 02 → 7F, 0x7E546167: 04 → 7E), so the
"dominant bin is B / C" tests never match and the routine exits after copying the ROM hue record
(the path every non-blue scene already takes). Affects Cross Process II as well.

### 22.2 Chroma curves, parameter block
- A search of the rodata for E-M10-style records (16 rising x, 16 y, 17 slopes as u16) finds only
  the gamma tables themselves: no such stage located. Consistent with CODE_DIG's setter table.
- The nine 3×3 matrix slots the research found in the ORF parameter block match the art / B&W
  matrices of 0x7E56C603 (four B&W filters, Pop Art I and II, 0x7E768F6A, identity). Not decoded
  further. The Olympus Viewer 3 edited-ORF test was not tried (needs the user's computer).

### 22.3 Joint refit and the matrix (`fit_joint.py`, `fit_matrix.py`); predictions, ΔE2000 vs target

| Version | hold-out mean / p95 | ColorChecker | Spyder all / colours / worst |
|---|---|---|---|
| xp3 (installed; measured Spyder 2.30 / 2.58 / 4.38) | 1.49 / 3.61 | 2.69 | 2.24 / 2.72 / 4.88 |
| xp5: six-axis refit only | 1.35 / 3.25 | 2.31 | 1.82 / 2.19 / 3.89 |
| joint: curves + saturation + six-axis | 1.18 / 3.03 | 2.33 | 1.78 / 2.16 / 3.66 |
| **joint + 3×3 pre-gamma matrix (xp7)** | **0.98 / 2.19** | **1.87** | **1.42 / 1.72 / 3.30** |
| xp7 if the matrix acts after the colour matrix instead | 1.01 / 2.18 | 1.89 | 1.48 / 1.80 / 3.73 |
| xp7 if the matrix is not applied at all | 1.20 / 3.07 | 2.42 | 1.86 / 2.28 / 3.81 |

- Refitting the curves jointly adds almost nothing; **the matrix is the lever** (as both Ricoh
  projects found). Matrix alone without six-axis: Spyder colours 2.24, worst 5.96.
- Matrix position: 0x7E56C603 right-multiplies the shot's ColorMatrix by the art table, read as
  "A acts on white-balanced camera RGB" (E = M A M⁻¹ in sRGB terms; fitted with each sample set's
  own M). The stock Pop Art shot cannot tell the two orders apart (ΔE 2.01 both; 2.04 without the
  matrix; only the transposed convention is ruled out, 7.2). The fitted matrix is close to
  order-insensitive, and the flash will show which prediction the camera follows.
- xp7 values: A ×256 = [[236, 20, 0], [−5, 242, 19], [−12, −25, 293]]; saturation 0.949 → gain 248;
  six-axis S (9, −40, 20, −19, 38, −15), H (0, 18, 17, 20, −12, 16); new base-gamma tables.

### 22.4 Builds (both NOT camera-tested; audited: every changed block-0 byte inside the intended
ranges, block 1 = the 20 labels only, blocks 2–3 and tail identical, checksums OK)
- `build/film-portra-xp6-labelled.BIN` = first Portra curves + `sixaxis-portra-3` (xp5 values) +
  `xp-adaptive-hue-off`. Code bytes changed: 0x7E546161, 0x7E546167. sha256
  `20a9789a526d9fefb6bd7930dc4e8a34e47d7b8b8f56b1e5214b773fc72f3f4c`.
- `build/film-portra-xp7-labelled.BIN` = `film-portra-xp7` (curves, gain, six-axis, matrix table
  0x7E768F46, and code immediates 0x7E56C6A6: 46 → 55, 0x7E56C6AA: 4F → 57, which give Pop Art I's
  matrix slot to Cross Process I; **Pop Art I loses its mild saturation matrix**) +
  `xp-adaptive-hue-off`. sha256 `316590e30ba8f7c4c26781976e6cdb0b7ee0e9c8578d40ffac2c87ef0b62fcb0`.
- These are the first builds that change code bytes (four one-byte compare immediates on the
  capture path, none on the boot path; instruction lengths unchanged).
- Test for either: RAW Data Edit PB110237 (Spyder), PB090221 (chart) and one blue-sky ORF as
  Portra 400. `out/spyder_pred_xp7.npy` holds the three Spyder predictions (camera-space matrix,
  sRGB-space matrix, no matrix) to compare the result against.

## 23. Camera result xp7, and the delta refit xp8 (2026-11-12)

### 23.1 xp7 on the camera (PB090253 = chart, PB110254 = SpyderCheckr; RAW Data Edits)
- Boots and renders: the four changed code immediates work. No blue-sky RAW Data Edit was sent, so
  the adaptive-hue switch-off is untested.
- **SpyderCheckr vs target: all 2.16, colours 2.52, grays 1.08, worst 5.36 (cyan B1). Predicted
  colours 1.72. So xp7 is no better than xp3 on colours (2.58); grays improved (1.44 → 1.08).**
  Better: C3, B4 (red), B6, D2. Worse: B1 (cyan) 3.5 → 5.4, C1 1.6 → 3.0, C2, C5.
- Camera vs the three predictions (Spyder): matrix after the colour matrix 1.43 (colours 1.58),
  matrix on camera RGB 1.74, no matrix 2.68. Chart (160 colours): matrix (sRGB space) then
  six-axis 1.68; camera-space 2.00; six-axis before the matrix 1.95 / 2.23; no matrix 3.41.
  **Established: the art matrix is applied for codes 85 / 87 after the re-key; it acts in linear
  sRGB (after the ColorMatrix, i.e. total = A · M), and the six-axis stage follows it.**
- The model is still about 1.5 ΔE off on this build, more than on xp3 (1.1–1.3). Not explained;
  candidates: the firmware renormalises the product matrix to 7-bit rows (CODE_DIG §4), six-axis
  linearity at these values, matrix × six-axis interaction.

### 23.2 Delta refit (`fit_delta.py`) → `patches/history/film-portra-xp8.json` → `build/film-portra-xp8-labelled.BIN`
For the colours measured with xp7 (Spyder, chart) the prediction is measured + model(new) −
model(xp7), so only the change relies on the model; parameters are held near xp7.

| ΔE2000 vs target | Spyder all / colours / grays / worst | monitor chart |
|---|---|---|
| xp7 measured | 2.16 / 2.52 / 1.08 / 5.36 | 3.87 |
| xp8 predicted (delta) | 1.71 / 1.92 / 1.07 / 3.98 | 2.97 |

Changes from xp7: S (9, −40, 20, −19, 38, −15) → (15, −36, 16, −11, 29, −7); H (0, 18, 17, 20, −12, 16)
→ (0, 12, 11, 20, −12, 13); matrix ×256 → [[225, 33, −2], [−5, 240, 21], [−12, −13, 281]]; gain 249.
sha256 `1d5791f17ee7c27743fd1c1ca22869850eeb284868310b1ddf44278729bd3dfa`; audited as §22.4 (same four code bytes); NOT camera-tested.
Caution: three predictions in a row were optimistic by 0.4–0.8 (xp3 2.23 → 2.58, xp7 1.72 → 2.52),
so expect xp8 nearer 2.2–2.4 than 1.9 on the Spyder colours.


## 24. Synthetic test RAW ("mock image") for RAW Data Edit (2026-11-12)

Purpose: one file that replaces the chart / Spyder / scene re-developments. The camera develops it
with whatever build is flashed, and the result gives that build's exact output for 6,912 known
input colours, with no photography, lighting or patch-finding error.

- `orfcodec.py`: decoder / encoder for the Olympus compressed raw strip (ported from dcraw
  `olympus_load_raw`). Decode equals LibRaw on real files; encode → decode is exact.
- `make_mock.py` → `out/mock/PB120001.ORF` (13,649,361 bytes): PB090221.ORF with only the raw strip
  replaced (metadata, lens data, embedded preview are the donor's, so the thumbnail on the camera
  shows the old chart photo). 96 × 72 flat patches of 48 × 48 raw pixels: 108 white position
  markers, a 17³ grid over the whole white-balanced camera RGB cube, 512 grays, 162 near-neutrals,
  49 identical mid grays (uniformity check), 1,168 natural colours. `out/mock/mock_layout.npz` holds
  the layout. exiftool and LibRaw read the file (black 255, max 4045).
- `read_mock.py JPEG` → `out/mock/read_<name>.npz` (per patch: JPEG RGB median of the central
  20 × 20 pixels, spread, raw RGB, u = WB ⊙ raw, v = ColorMatrix · u, using the WB and ColorMatrix in
  the output JPEG's EXIF, because RAW Data Edit applies the camera's current WB). Patch positions
  are found by matching the layout against the JPEG (the JPEG is distortion-corrected), then a
  smooth displacement field. `--selftest` (LibRaw development bent by a 30 px lens-like warp, JPEG
  q92): registration rms 0.5 px, all readable patches within 1 code of the truth, 0 outliers;
  patches pushed outside the frame by the warp are dropped (219 of 6,912 in the self-test).
- NOT yet tested on the camera: whether RAW Data Edit accepts the file, and how much of the edge
  the real distortion correction crops.
- Camera settings for the run: WB on the Sunny preset (5300 K), so the applied WB / ColorMatrix
  equal the donor's (528/460, 5300 K matrix) and the grid is neutral on its diagonal. With Auto WB
  the camera would measure a white balance from the random patches (usable, since the applied
  values are read from EXIF, but the neutral patches would not be neutral).

## 25. Mock-image results on xp8, model corrections, refit xp9 (2026-11-12)

### 25.1 The camera accepts the synthetic RAW
xp8 flashed and booted. RAW Data Edit developed `PB120001.ORF` nine times (PB120002 Portra 400 =
Cross Process I, 03 Natural, 04 Vivid, 05 Portrait, 06 Muted, 07 Pop Art, 08 Soft Focus, 09
Pale&Light, 10 Light Tone). `read_mock.py`: 6,551–6,580 of 6,912 patches read (the distortion
correction enlarges the picture; shift up to 87 px, edge patches fall outside); spread inside the
sampling window median 0.2 codes; the 49 identical mid grays are identical (std 0), so no shading.
Camera WB was Auto and came out as 520/470 with the 5300 K matrix (Pale&Light: 406/510).
The old photos are now in `shots/archive/`; the older scripts still look in `shots/`.

### 25.2 What xp8 really does (camera vs target, ΔE2000, no measurement error)
Natural colours (1,122) 1.47 (p95 2.98); near-neutrals 1.55; gray ramp 1.32.

### 25.3 Model corrections found with the mock data
1. **The "identity" look table 0x7E75B8F0 is not an identity**: above luma 208 it falls below the
   diagonal (−28 of 1023 at 232–240). Natural and every build that copied it compress highlights;
   the model had skipped the table. Natural gray-ramp error 1.09 → 0.75 ΔE with it.
2. **The output EXIF ColorMatrix is the matrix the camera loaded** (art table × ColorMatrix). The
   renormalisation code 0x7E56C4C2 (disassembled): off-diagonals = floor of the 7-bit product; made
   even in row 1 column 2 and row 3 column 2, and in row 2 both when their sum is odd; each
   diagonal = 128 − the row's off-diagonals. `fit_xp9.renormalise()` reproduces the EXIF of the xp7
   and xp8 JPEGs exactly (12 of 12 off-diagonals). The camera output follows this matrix (model
   0.82 ΔE) and not the exact product (0.89) or the other order (1.20).
3. **Six-axis vectors recalibrated** (`fit_mock.py`) on Natural, Vivid, Muted, Portrait (stock
   records) and Portra xp8, all unclipped patches: model vs camera on Portra xp8 1.22 → 0.83 (grid
   1.72 → 0.86); the other modes 0.91–0.97. Saturation vectors are now nearly one channel each
   (R, G, B ≈ 1/128 … 1/106 per unit on the axis's own channel; Y, C, M on their two channels).
   The R hue vector is kept from the chart probes (the mock modes only have R hue −1…3).
   Fitted saturation: Natural 1.023, Vivid 1.136, Portra (gain 249) 0.926.
4. Not modelled: for very saturated bright cyan / green the camera compresses Cr strongly (Natural:
   predicted R 41 → camera 104); rare in natural colours. Chroma gain also falls toward clipping.
5. Remaining model error ≈ 0.9 ΔE on natural colours in every mode, much of it 8-bit rounding in
   the dark patches.

### 25.4 Refit xp9 (`fit_xp9.py` → `patches/history/film-portra-xp9.json` → `build/film-portra-xp9-labelled.BIN`)
Objective: GRKit sample set through the corrected model (grays with the measured gray-ramp
correction) + the mock patches as measured xp8 + model change. R hue fixed at 0.

| ΔE2000 vs target | mock natural (p95) | near-neutral | gray ramp | GRKit gray / ColorChecker / random |
|---|---|---|---|---|
| xp8 (mock columns measured) | 1.47 (2.98) | 1.56 | 1.28 | 0.82 / 1.90 / 1.28 |
| xp9 predicted | 1.30 (2.94) | 1.14 | 0.52 | 0.55 / 1.91 / 1.02 |

Changes: gain 249 → 271; S (15, −36, 16, −11, 29, −7) → (10, −30, 12, −11, 9, −6); H (0, 12, 11, 20,
−12, 13) → (0, 13, 9, 20, −2, 12); art table ×256 → [[228, 42, −14], [−5, 241, 20], [−16, 2, 270]];
the camera should report ColorMatrix 364 −60 −48 / −60 332 −16 / −12 −128 396 at 5300 K (a direct
check of the rounding rule). Curves: blacks raised (R 9, G 15, B 31 of 1023 at 0), top lowered.
sha256 `06ff22df53624c7ab2bf7db06bfa4025b4bc51f8b0466958a233d488b683609e`. Audit: differs from
xp8 only in the 24 gamma tables, matrix table, six-axis records, saturation pair and the block-0
checksum; same four code bytes as xp7 / xp8. NOT camera-tested.
Test: RAW Data Edit `PB120001.ORF` as Portra 400, then `read_mock.py` and compare with
`out/fit_xp9.npz` (`mock_pred`).

### 25.5 xp9 on the camera (PB120153 = mock; PA310154 = real photo PA300151, xp8 version PA310152)
| ΔE2000 vs target | natural (p95) | near-neutral | gray ramp |
|---|---|---|---|
| xp8 measured | 1.47 (2.98) | 1.56 | 1.32 |
| xp9 predicted | 1.30 (2.94) | 1.14 | 0.52 |
| **xp9 measured** | **1.31 (2.86)** | **1.10** | **0.77** |

- First prediction that held on colours. Camera vs prediction per patch: 0.75–0.78 mean.
- EXIF ColorMatrix = 364 −60 −48 / −60 332 −16 / −12 −128 396: the rounding rule of §25.3 is confirmed.
- Real photo (`check_scene.py`, 45 flat 64-px blocks in the central half, mostly pale sky): camera
  vs target 1.03, camera vs model 1.06. The sky is not blue enough to exercise the adaptive hue
  stage, so its switch-off is still unconfirmed. `out/compare_PA300151_xp8_xp9.jpg`.
- Same photo, whole frame (229 flat 96-px blocks, flat over a 3 × 3-block JPEG area so the
  distortion shift does not matter): camera vs target 0.63 (p95 1.40), camera vs model 0.51. The
  81 bluest blocks (sky and sea, blue/red ≥ 1.25; pale, JPEG about 208/214/215): camera vs model
  0.55 as built, 1.13 if +16 were added to the B and C hue (the adaptive stage's maximum). So no
  adaptive shift is present in this frame. Whether the stock code would have shifted this frame is
  not known (11 % of it is clearly blue), so this supports but does not prove the switch-off.

## 26. Second film: Ektachrome 100 in the Pop Art II slot (2026-11-12)

### 26.1 Which art slots can carry a film (dispatch tables dumped from block 0)
- Per art code the firmware picks: base gamma (hash table 0x7E78C154, 32 entries of key = code − 70
  and a handler address), look table (jump table 0x7E78C8E4, index code − 8), saturation pair (jump
  table 0x7E78C514, index code − 69), six-axis records (jump table 0x7E78C254) and the matrix (four
  compares in code at 0x7E56C6A5: 70, 79 → table 0x7E768F46; 102, 103 → 0x7E768F58).
- Only two base-gamma handlers load three different records (R, G, B): 0x7E56B7F8 (Cross Process I,
  records 0x7E78B41C / 3C / 5C) and 0x7E56B82A (Cross Process II, 0x7E78B49C / BC / DC). All other
  codes get one record for the three channels. The compares are `cmp imm8` on a zero-extended byte,
  so only codes ≤ 127 can be written into them (not Cross Process II's 167).
- Pure colour-table filters (no effect module, docs/firmware-map.md): Pop Art I / II, Pale&Light
  I / II, Light Tone, Cross Process I / II. The other eight run an effect module (not traced).
- Block 0 has large 0xFF runs (364 KB at 0x7E881003, 351 KB at 0x7F14B569, 217 KB at 0x7E4C90CA, …)
  that could hold new handlers and tables for more slots; not verified to be intact at run time.

### 26.2 Pop Art II slot (codes 102 / 103), data only
Its own look table 0x7E75FAF0, saturation pair 0x7E7696BC (stock 392), six-axis records 0x7E76952E /
0x7E76953A, matrix table 0x7E768F58; and per-channel gamma by changing its two hash entries
(0x7E78C158, 0x7E78C170) from handler 0x7E56B822 to 0x7E56B82A, so it uses Cross Process II's 24
tables. Cross Process II then renders with these curves but its own look / six-axis / saturation
and no matrix (a broken duplicate). No stock Pop Art II mock rendering exists (PB120007 was Pop
Art I: its EXIF matrix is the plain ColorMatrix), so this slot's behaviour is untested.

### 26.3 Target and fit
- `bake_slide.py kodak_ektachrome_100`: spektrafilm-lut only renders film → print; for a positive
  film the builder's pipeline is run with `scan_film` on (film scanned directly). V-Log / V-Gamut in,
  sRGB out, 33³: `out/lut/spektrafilm_v034_kodak_ektachrome_100_scanfilm_1lut_vlog_srgb/
  lut_v034_ektachrome100_scanfilm.cube`, sha256 `964ed447…aa5a064`.
  Grays: black 2, 18 % gray 118 / 117 / 114, white tops out at 219 / 216 / 217.
- `fit_film.py --lut … --slot popart2 --name film-ektachrome-pa2`: calibrated model (§25), GRKit
  samples and weights, model only (no measured anchor yet), R hue fixed at 0. Added to the GRKit
  set: 12 grays from +2.7 EV to sensor clipping, because without them the curve tops were
  unconstrained and clipped highlights took a cast (first fit: R 909, G 839 of 1023).
- Predicted ΔE2000 (model only): GRKit gray 0.37, ColorChecker 1.83, random 0.96; hold-out 0.94;
  mock natural 1.12 (p95 2.94). Stock Natural vs this target: mock natural 4.19. Expect about
  1.5 on the camera before a measured refit (Portra: model-only fits landed 0.4–0.8 above prediction;
  the corrected model has one confirmed prediction).
- Values: gain 252; S (8, −13, −22, 8, −3, −5); H (0, −2, 2, 11, −5, 6); art table ×256 [[213, 56,
  −13], [11, 234, 11], [3, 13, 240]]; camera should report ColorMatrix 336 −32 −48 / −34 320 −30 /
  14 −108 350 at 5300 K.

### 26.4 Build
`build/film-portra-xp9-ektachrome-pa2.BIN` = film-portra-xp9 + film-ektachrome-pa2 +
xp-adaptive-hue-off + label-portra; sha256
`f3cc6798739fd6f6cf0353dc86412a8778c523060e8969b21fcc8b68bdc36ba9`. Differs from the xp9 build by
exactly the Ektachrome ops' 7,920 bytes + the block-0 checksum; no new code bytes. NOT camera-tested.
Test: RAW Data Edit `PB120001.ORF` with art filter Pop Art II.

### 26.5 Menu reach, and the Light Tone slot (2026-11-12)
- The user's quick menu lists the twelve filters only; type II is reached in ART mode with the right
  arrow on a filter (manual; `art_GetFilterType` 0x7E71BD94 maps Pop Art type 1 / 2 → codes 70 /
  102, Pale&Light → 71 / 145, Cross Process → 85 / 167, Light Tone → 72 only). The two JPEGs sent
  for the pa2 build (PB120155, PA310156) are Pop Art I (plain ColorMatrix in EXIF): pa2 is untested.
- The user wants film 2 on a top-level entry. Hosts checked against the stock mock renderings with
  the calibrated model (own gamma record, look table, saturation pair, six-axis records):
  **Light Tone 0.94 ΔE (natural 1.01, gray ramp 0.60, grid 1.12): clean.** Pale&Light I: natural
  0.95 but grid 8.2, and it changes the WB (406/510 instead of 520/470): not clean. Pop Art I 2.0
  (six-axis values far outside the calibrated range); its still code 70 is key 0 in the gamma hash
  table (= empty), so it cannot be re-pointed there.
- `fit_film.py --slot lighttone` → `patches/history/film-ektachrome-lt.json`: same fit values as §26.3;
  gamma hash entries for keys 2 and 11 (codes 72, 81) 0x7E56B7F0 → 0x7E56B82A; look 0x7E75EAF0,
  saturation pair 0x7E7696A8, six-axis 0x7E7694B6 / 0x7E7694C2, matrix table 0x7E768F58 with the
  compares re-keyed 0x7E56C6AE: 66 → 48 (72), 0x7E56C6B2: 67 → 51 (81). Pop Art II loses its
  matrix; Cross Process II shares the curves. Codes 147 / 150 (other Light Tone keys) untouched.
- `patches/history/label-ektachrome-lt.json`: "Light Tone" → "Ektachrome" (same length, 2 copies in block
  1, shared by all languages).
- `build/film-portra-xp9-ektachrome-lt.BIN` = film-portra-xp9 + film-ektachrome-lt +
  xp-adaptive-hue-off + label-portra + label-ektachrome-lt; sha256
  `5d343706935fabbf5cee3ce91c0c46c55b0c7f1fdff64640738a179ac076710d`; differs from the xp9 build
  by the Ektachrome ops, the label and checksums only. NOT camera-tested.

### 26.6 Ektachrome in Light Tone on the camera, and the correction refit (2026-11-12)
- `film-portra-xp9-ektachrome-lt` flashed; "Ektachrome" entry works. PB120158 = mock, PA310157 =
  real photo PA300151. EXIF ColorMatrix 336 −32 −48 / −34 320 −30 / 14 −108 350 = predicted, so the
  compare re-key to 72 works; camera vs model 0.92 (natural), 0.54 (gray ramp), so the re-pointed
  three-record handler and Light Tone's own tables behave as modelled.
- Camera vs Ektachrome target (`check_film.py`): natural 1.55 (p95 3.62; predicted 1.12),
  near-neutral 1.07, gray ramp 0.64.
- `fit_film.py … --anchor PB120158 out/fit_film-ektachrome-lt.npz` → `film-ektachrome-lt2`:
  predicted (measured + model change) natural 1.41 (p95 3.25), near-neutral 0.98, gray ramp 0.55.
  gain 253; S (6, −13, −19, 11, −1, −5); H (0, −2, 0, 13, −5, 3); art table ×256 [[215, 56, −15],
  [11, 230, 15], [3, 11, 242]]; expected EXIF ColorMatrix 340 −32 −52 / −32 312 −24 / 14 −112 354.
- `build/film-portra-xp9-ektachrome-lt2.BIN`, sha256
  `3ba961500c8ea707b63b121119b949f6a22b87040e6a2fee983aa3ec31ccc232`. NOT camera-tested.
- Slot map for all menu entries: `docs/art-filter-slots.md`.
- **lt2 on the camera (PB120159):** EXIF ColorMatrix as predicted. Camera vs target: natural 1.39
  (p95 3.09; anchored prediction 1.41), near-neutral 0.93 (0.98), gray ramp 0.60 (0.55). Camera vs
  model 0.88. Second film now at the same level as Portra (1.31).

## 27. Second-generation test RAWs (2026-11-12)

Why: the first mock (§24) spent 4,913 of 6,912 patches on a cube over all camera RGB (735 unclipped
in Natural), held none of the colours the fit weights most (ColorChecker × 5 EV, skin), was built
for WB 528/460 while the camera applies 520/470 to it, and could not exercise the scene statistics.

`make_mock2.py` (same geometry and donor as §24; colours defined in scene-linear sRGB for WB 520/470):
- **A = `out/mock/PB130001.ORF`** (13,632,500 bytes), layout `mock2a_layout.npz`:
  GRKit gray ramp 120 + 12 grays to clipping (kind 6); ColorChecker × 5 EV, three copies (kind 7,
  336); skin series 45 (kind 8); the fit's own 3,535 random natural colours in order (kind 5); 1,000
  hold-out naturals (kind 9); near-neutrals 12 levels × 12 hues × 4 chroma (kind 3, 576); dense gray
  ramp 512 (kind 2); 25 identical mid grays (kind 4); 300 bright gamut-edge colours (kind 10); a
  coarse 7³ cube (kind 1). Cube and 400 hold-outs sit in the border the lens correction crops.
  The layout stores per patch `sid` (index) and the GRKit `weight`.
- **B = `out/mock/PB130002.ORF`** (13,616,587 bytes), layout `mock2b_layout.npz`: 4,604 sky / sea
  blue patches (kind 11) + 2,200 patches repeated from A with the same raw values (all GRKit grays,
  one ColorChecker set, skin, mid grays, all 983 blue / cyan fit colours, 895 other fit colours).
- Scene statistics of CODE_DIG §2 re-computed on the patch values (approximate: the camera's
  thresholds and gains are not reproduced): A → bins R G B Y C M = .18 .16 .15 .21 .17 .12, dominant
  Y, no adaptive shift; B → .02 .01 .58 .02 .35 .01, dominant B, 16 of 16 hue units on stock code.
  (The first draft of A was cyan-dominant, 5.8 units; the gamut-edge set was rebalanced.)
- `read_mock.py` now finds which test image a JPEG shows (tries every layout, keeps the best
  match) and ignores the EXIF orientation. Self-tests with an 87 px warp: A 6,472 and B 6,506 of
  6,912 read, all within 1 code; lost in A: 174 cube, 231 hold-out, 10 fit colours, 2 ColorChecker
  (of 336), 2 ramp grays; none of the GRKit grays or skin.
- sha256: PB130001 and PB130002 as printed by `sha256sum out/mock/PB13000*.ORF` on 2026-11-12.
- Planned developments: A as Portra 400, Ektachrome, Natural; B as Portra 400 and Natural. Test of
  scene dependence: patches with the same `sid` must render the same in A and B.
- Not included (later): sub-code dither in the patches; other WB presets.

## 28. Results with the second-generation test RAWs; refits xp10 / lt3 (2026-11-12)

Firmware on the camera: `film-portra-xp9-ektachrome-lt2`. PB130001 first did not show on the camera:
the card still held PB120001.ORF, and two files with file number 0001 in one folder clash (DCF);
after deleting PB120001.ORF it worked. The five JPEGs came back as PB120153–PB120157, **the same
names as earlier uploads, which they overwrote** in `shots/` (the old PB120153 = xp9 on mock 1,
PB120154 = real photo, PB120155–157 = Pop Art / Ektachrome shots; their results are in §25–26).
Copies under clear names: `shots/mock2/{A_portra_xp9, A_ektachrome_lt2, A_natural, B_portra_xp9,
B_ektachrome_lt2}.JPG`; reads `out/mock/read_<name>.npz`. `analyze_mock2.py`.

### 28.1 Scene dependence (A vs blue-scene B)
2,194 shared patches (1,016 blue / cyan): **RGB identical in 100 % for Portra and for Ektachrome**
(ΔE mean 0.000 / 0.001). The Portra slot is scene-independent on a frame whose statistics would
give the maximum stock shift (as re-computed, §27). What stock would have done on B was not measured.

### 28.2 The fit objective, measured (camera vs target, image A, ΔE2000 mean / p95)
| Sample set | Portra xp9 | Ektachrome lt2 |
|---|---|---|
| GRKit grays (132) | 0.85 / 1.43 | 0.78 / 1.48 |
| ColorChecker × 5 EV (335) | 2.66 / 6.70 | 2.42 / 5.68 |
| skin series (45) | 1.62 / 2.76 | 1.76 / 2.78 |
| fit natural colours (3,526) | 1.37 / 2.98 | 1.33 / 3.10 |
| hold-out naturals (≈ 830) | 1.38 / 3.06 | 1.33 / 2.89 |
| near-neutrals (576) | 1.10 / 2.28 | 0.97 / 2.04 |
| gamut-edge colours (299) | 13.6 / 27.7 | 15.8 / 29.7 |
| GRKit-weighted | 1.20 | 1.11 |
- ColorChecker per patch (Portra): neutrals and skin 0.4–2.9; saturated patches 3–10 (red +2 EV
  10.6, orange +2 EV 9.0, purplish blue +2 EV 7.7, yellow green 4.6–7.5). The model predicted most
  of it (camera vs model ≈ 1), so it is a limit of the stages, not a model error.
- Gamut-edge colours are far off for both the looks and the model (stock Natural: model vs camera
  17.8): the unmodelled chroma compression. Natural colours are unaffected.
- Stock Natural on A: GRKit grays neutral to 0.42 codes; model vs camera 0.44 (grays), 0.87
  (natural), 0.89 (ColorChecker), 0.63 (skin).

### 28.3 Refits with the measured objective (`fit_film.py --anchor A_… --robust 3`)
With a second-generation anchor the objective is the measured samples themselves (GRKit weights;
skin series 20, near-neutrals 4, dense grays 20), predicted as measured + model change; the
model-only term is dropped. `fit_film.py` gained slot `xp1` (Cross Process I) so Portra uses it too.
- Plain least squares on ΔE let a few saturated ColorChecker patches dominate: Portra weighted
  1.196 → 1.045 but natural 1.37 → 1.56, skin 1.62 → 1.89, hold-out 1.38 → 1.59. Rejected.
- **Soft-L1 loss, scale 3 (my choice, not GRKit's)** improves nearly every group:

| predicted (measured + model change) | weighted | grays | ColorChecker | skin | natural | hold-out |
|---|---|---|---|---|---|---|
| Portra xp9 measured → xp10 | 1.196 → 1.015 | 0.85 → 0.62 | 2.66 → 2.51 | 1.62 → 1.35 | 1.37 → 1.33 | 1.38 → 1.33 |
| Ektachrome lt2 measured → lt3 | 1.107 → 0.933 | 0.78 → 0.58 | 2.42 → 2.15 | 1.76 → 1.52 | 1.33 → 1.37 | 1.33 → 1.38 |
- xp10: gain 274; S (7, −26, 9, −10, 5, −5); H (0, 10, 8, 20, −2, 12); art ×256 [[219, 50, −13],
  [−5, 238, 23], [−17, 2, 271]]; expected EXIF ColorMatrix 348 −44 −48 / −60 328 −12 / −14 −128 398.
- lt3: gain 256; S (−1, −13, −19, 14, 4, −6); H (0, −3, 0, 13, −3, 2); art ×256 [[211, 60, −15],
  [18, 224, 14], [6, 15, 235]]; expected EXIF ColorMatrix 332 −24 −52 / −20 300 −24 / 18 −104 342.
- `build/film-portra-xp10-ektachrome-lt3.BIN`, sha256
  `4bb345faf265ba200a538d5ba46c3c694514bfda3a44ddd940ce6adfedd27a84`; differs from the build on
  the camera only in the gamma tables, the matrix / six-axis / saturation region and the block-0
  checksum. NOT camera-tested. Test: RAW Data Edit PB130001 as Portra 400 and as Ektachrome.

### 28.4 xp10 / lt3 on the camera (2026-11-12)
`film-portra-xp10-ektachrome-lt3` flashed. Uploads PB120158–161 (again overwriting older files of
those names) → `shots/mock2/{A_portra_xp10, A_ektachrome_lt3, B_portra_xp10, B_ektachrome_lt3}.JPG`.
EXIF ColorMatrix as predicted for both. A vs B: RGB identical in 100 % of 2,194 shared patches.

| camera vs target, ΔE2000 | Portra xp9 → predicted → **xp10** | Ektachrome lt2 → predicted → **lt3** |
|---|---|---|
| GRKit grays | 0.85 → 0.62 → **0.98** | 0.78 → 0.58 → **0.77** |
| ColorChecker × 5 EV | 2.66 → 2.51 → **2.58** | 2.42 → 2.15 → **2.24** |
| skin series | 1.62 → 1.35 → **1.36** | 1.76 → 1.52 → **1.35** |
| fit natural colours | 1.37 → 1.33 → **1.33** | 1.33 → 1.37 → **1.36** |
| hold-out naturals | 1.38 → 1.33 → **1.35** | 1.33 → 1.38 → **1.36** |
| near-neutrals | 1.10 → 1.01 → **1.08** | 0.97 → 1.04 → **1.04** |

- Colours followed the prediction; grays did not improve. Gray ramp, camera minus prediction:
  mean ≤ 0.3 codes, **rms 0.65–1.0 codes per channel**: the changes asked for were about one code,
  and the camera's output scatters by about one code around any prediction (8-bit output, several
  rounding stages). The predicted ΔE used unrounded values, which is why gray predictions were
  always optimistic.
- Rounding floor (target ± noise, rounded to 8 bits): grays 0.34 for rounding alone, **0.93 with
  the observed 0.8-code scatter**; natural colours 0.27 / 0.76; skin 0.21 / 0.58. So the grays
  (0.98, 0.77) are at the floor; further gray refits chase noise. Only the darkest grays are a
  real miss (EV −5: camera 7 / 8 / 12, target 13 / 14 / 17 for Portra).
- Verdict: xp10 / lt3 are the better builds for skin (−0.26, −0.41) and chart colours; natural
  colours unchanged; converged.

## 29. Third film slot: feasibility (2026-11-12; nothing built)

### 29.1 Where new code and data can live
- Block 0 is not loaded whole. The boot task reads flash → RAM 0x7E4FE000–0x7E881000; Usr1 loads
  0x7E8F5800–0x7ECB1000, 0x7ECCB800–0x7F034000, 0x7F100000–0x7F119000 (feature-map 01 §2). **The
  large 0xFF runs of §26.1 are exactly the gaps between these ranges (each starts 3 bytes after a
  range's end), so they are never loaded.** The claim "364 KB free" was wrong for practical use.
- 0xFF runs inside the loaded ranges: **0x7E880F5C (164 B, boot segment, next to code)**,
  0x7ECB0888 (1,912 B), 0x7F033B7C (1,156 B), 0x7F118F64 (156 B), 0x7E7E1ECB (92 B), 0x7F030748 (96 B).
  About 3.5 KB in all: room for code, records and matrices, not for a 12 KB set of 24 gamma tables.
- Table space for a third film without new space: the gamma records of Pale&Light (0x7E78B3DC),
  Light Tone (0x7E78B3FC, unused since §26.5) and Pop Art II (0x7E78B47C): 3 records × 8 tables.

### 29.2 Host: the top-level Pop Art entry (code 70, movie 79)
- Its key in the gamma hash is 0 = the empty marker, and the range check is code ≥ 71. Reading the
  probe loop (0x7E56B7BE–0x7E56B7E5): with the check lowered to 70 (0x7E56B7A7: 47 → 46), key 0
  walks entries 0…7 (all occupied, none equal 0) and matches entry 8, whose handler address is
  then used; every other key that reaches entry 8 still treats it as empty and goes to the
  default. So entry 8's handler field can carry the new handler for code 70 alone; code 79 gets a
  normal new entry (key 9, entry 9 is free).
- Pop Art I has its own look table (0x7E75E6F0), saturation pair (0x7E7696A0), six-axis records
  (0x7E769486 / 0x7E769492) and no effect module.

### 29.3 Code needed (draft `slot3/cave_draft.s`, assembled with the mn10300 toolchain: 119 bytes)
- `gamma3` (49 B): the handler at 0x7E56B82A with the three record addresses above, its two calls
  as 32-bit calls, ending in a jump to the common tail 0x7E56B852.
- `matrix3` (52 B + 18 B table): the compare chain at 0x7E56C6A5 replaced by a 5-byte jump to a
  routine that tests 85 / 87 → stock block 0x7E56C6B8 (table 1), 72 / 81 → 0x7E56C6C3 (table 2),
  70 / 79 → a third table, else 0x7E56C76B.
- Fits the 164-byte run at 0x7E880F5C. Stock bytes changed: one compare immediate, a 5-byte jump
  (+ filler) over the 16-byte compare chain, two or three hash entries.
- Side effects: Pale&Light I and Pop Art II lose their own gamma curves (their records become
  film 3's channels); they should be re-pointed to the default record. The stock Pop Art look goes.
- Not verified: that the 164 bytes are really in RAM and unmodified at run time (inferred from
  the boot read's range); the hash reading above; behaviour of movie / live view with code 79.
- A fourth film would need 3 tables (1.5 KB, all 8 variant pointers to one table per channel) in
  the 1.9 KB run, and a clean host entry, which is the harder part (§26.5, docs/art-filter-slots.md).
- Test tooling: `tools/emu` (om-emu) could run the patched selector functions before a flash, but
  om-emu and Node 26 are not installed on this machine.

### 29.4 Candidate films for a third slot (model-only fits, `fit_film.py`, 2026-11-12)
Targets baked as before (negatives through a print, slides with `bake_slide.py`). "Distance" = mean
ΔE2000 between two targets on the hold-out natural colours. Predicted fit = model only; the two
installed films measured 0.4–0.5 above their model-only prediction on the camera.

| Film (print) | predicted fit, natural / ColorChecker | stock Natural vs target | distance to Portra | to Ektachrome |
|---|---|---|---|---|
| Fuji Pro 400H (Crystal Archive II) | 0.85 / 1.79 | 4.79 | 2.92 | 4.24 |
| Kodak Vision3 250D (2383 print film) | 0.92 / 2.11 | 5.87 | 3.37 | 4.02 |
| Kodachrome 64 (slide) | 0.66 / 1.27 | 5.27 | 4.02 | 2.02 |
| Fuji Velvia 100 (slide) | 1.20 / 2.16 | 3.64 | 3.55 | 3.20 |
| Kodak Gold 200 (Portra Endura) | 0.97 / 1.77 | 3.89 | 1.31 | 3.07 |
| Kodak Ektar 100 (Portra Endura) | 1.02 / 2.08 | 4.20 | 1.23 | 3.88 |
Gold 200 and Ektar 100 on the same paper are within 1.3 ΔE of the installed Portra: not worth a slot.
No black-and-white profiles exist in spektrafilm; the user chose to stay with colour (2026-11-12).

## 30. Third slot built: Fuji Pro 400H in the top-level Pop Art entry (2026-11-12; NOT flashed)

- Film chosen by the user: Fuji Pro 400H on Crystal Archive II (§29.4). Target
  `out/lut/spektrafilm_v034_pro400h_crystalarchive_1lut_vlog_srgb/`. Model-only fit
  (`fit_film.py --slot popart1`): predicted GRKit gray 0.36, ColorChecker 1.79, natural 0.86,
  hold-out 0.85. gain 269; S (1, −17, −4, 1, 0, −12); H (0, 8, 3, 16, −3, 7); art ×256 [[224, 48, −16],
  [−6, 259, 3], [−18, 17, 257]]; expected EXIF ColorMatrix 356 −48 −52 / −68 368 −44 / −20 −100 376.
- `slot3/cave.s` (120 bytes at 0x7E880F5C; `gamma3` 0x7E880F5C, `matrix3` 0x7E880F8D, table `t3`
  0x7E880FC2, even address) and `slot3/build_slot3.py` → `patches/history/slot3-code.json`:
  new code; 5-byte `jmp matrix3` at 0x7E56C6A5 (the rest of the old compare chain is dead code);
  range check 0x7E56B7A7 47 → 46; hash entry 8 handler → gamma3, entry 9 := key 9 → gamma3; Pale&Light
  I (keys 1, 10), Pop Art II (32, 33) and codes 147 / 150 → default handler 0x7E56B861.
  The two installed film patches are used without their compare immediates
  (`film-portra-xp10-s3`, `film-ektachrome-lt3-s3`). Label `label-pro400h-pa`: "Pop Art" → "Pro400H".
- `build/three-films-1.BIN`, sha256
  `3cceb50af75e9589d333858d671dc1c20d323657fd22e32531a710a724340853`. Audit against the build on
  the camera: block 0 differs in the range-check byte, 14 bytes of the compare chain, the 24 tables
  of records 0x7E78B3DC / 3FC / 47C, Pop Art I's look table, six-axis records and saturation pair,
  the hash table and the 120 new bytes; block 1 by the label (120 bytes); blocks 2–3 and tail equal.
  Disassembled from the built image: the jump, both calls and all five far jumps hit the intended
  addresses. The lookup loop transcribed to Python and run for codes 0–255 on the patched table:
  only 70, 79 (→ gamma3), 71, 80, 102, 103, 147, 150 (→ default) and 72, 81 (→ 0x7E56B82A, as
  before) differ from stock.
- Not done: an emulator run. Node 26 (`~/opt/node26`) and om-emu (`~/opt/om-emu`, unpatched clone)
  are now on this machine, but running them was refused by the session's permission system.
- Not verified until flashed: that 0x7E880F5C–0x7E880FD3 is in RAM at run time; movie / live view
  with codes 79 and 70; the matrix path now runs through new code for **all three** films.
- Test: RAW Data Edit PB130001 as Portra 400, Ektachrome and Pro400H; one normal shot.

### 30.1 `three-films-1` on the camera (2026-11-12): the new code works
- Flashed by the user (the emulator cases `gamma_select` / `matrix_choice` were written in
  `tools/emu/cases.py` but not run: no permission for those commands; `curve_select` self-check
  passed, 229 rows). Uploads PB120152–154 → `shots/mock2/{A_portra_xp10_3f1, A_ektachrome_lt3_3f1,
  A_pro400h_pa1}.JPG`.
- **Portra and Ektachrome: RGB identical to the previous build in 100 % of 6,588 / 6,587 patches.**
  So `matrix3` routes 85 / 87 and 72 / 81 correctly and nothing else moved.
- **Pro400H entry: EXIF ColorMatrix 356 −48 −52 / −68 368 −44 / −20 −100 376 = predicted**, so the
  code at 0x7E880F5C is in RAM and runs (`matrix3` → `t3`); the per-channel curves act (`gamma3`).
- But camera vs model was 2.1 ΔE (other slots 0.9) and camera vs target: grays 1.61, ColorChecker
  3.88, skin 2.84, natural 2.45 (stock Natural vs this target: 4.5–6.4).

### 30.2 Cause: a sixth per-art-code stage, the chroma curves
- Measured chroma gain camera / model in the Pop Art slot by chroma magnitude: 0.0 (0.5–2 codes),
  0.38 (2–4), 0.58 (4–8), 0.92 (8–16), 1.12 (16–32), 1.22 (32–64); Portra slot: 0.88 … 1.05.
- Found by scanning for other dispatches on the art code: **function 0x7E5662D9** (callers
  0x7E56A0D7, 0x7E570224), jump table **0x7E78AEA4** indexed by code − 69. Each art handler stores
  six table addresses (16, 16, 17, 16, 16, 16 bytes; 97 bytes per filter):
  - Cross Process I (0x7E74BAA4) and Light Tone (0x7E74B97E): 0 0 0 0 64 128 192 255 … and slopes
    128: a straight line through 128 (identical sets).
  - **Pop Art I (0x7E74B8BA): … 23 125 128 131 232 …, slopes 160 42 42 160: flat near neutral,
    steep outside.** That is the measured curve.
  - Pale&Light I (0x7E74B91C): 0 80 112 120 124 128 132 136 144 176 255 …: compresses strong
    chroma. Explains its 8.2 ΔE on the grid (§26.5). Pop Art II (0x7E74BBCA): a hard step.
  - Codes without an entry use sensor-type records at 0x7E74AEB0….
- So a film slot needs **six** things, not five; `docs/art-filter-slots.md` updated.
- `patches/slot3-chroma-linear.json`: Pop Art I's 97 bytes := Cross Process I's (20 bytes change).
- `build/three-films-2.BIN` = three-films-1 + that patch; sha256
  `0942a4b52f825a5c416ea068f5887126a3de7d8744ff23ffed8ef6d57f54f705`; differs from
  three-films-1 by those 20 bytes and the checksum. NOT camera-tested. The Pro 400H values are
  still the model-only fit; a correction refit follows the next measurement.

### 30.3 Emulator runs of the new code (run by the user, 2026-11-12; `tools/emu/cases.py`)
Stock block 0 vs block 0 with film-portra-xp10-s3 + film-ektachrome-lt3-s3 + slot3-code +
film-pro400h-pa1 + xp-adaptive-hue-off.
- `matrix_choice` (256 art codes): **8 changed, 248 identical, 0 flagged.** 70 / 79: table 1 →
  apply with a1 = 0x7E880FC2 and a0 = d3; 85 / 87: none → table 1; 72 / 81: none → table 2;
  102 / 103: table 2 → none. No code outside the chain and `matrix3` ran; d0 and sp unchanged.
- `gamma_select` (524 rows): **40 changed** = codes 70, 79 (→ records 0x7E78B3DC / 3FC / 47C),
  72, 81 (→ 0x7E78B49C / 4BC / 4DC), 71, 80, 102, 103, 147, 150 (→ default) × 4 input sets; 484
  identical. 24 rows flagged, all by the case's own bookkeeping and none by behaviour: 8 × "changed
  without reading patched bytes" (70 / 79: the harness takes the read set from the stock run, which
  reads the unpatched default tables) and 16 × "reads patched bytes but unchanged" (85, 87, 167,
  168: the case reports which tables are chosen, not their rewritten contents). To clean up: hash
  the table contents in the case and let the harness use the patched run's reads too.
- Both agree with the camera result of §30.1.

### 30.4 `three-films-2` on the camera: the chroma fix works; refit pa2 (2026-11-12)
Uploads PB120152 (test RAW A) and PB120153 (blue scene B), both as Pro400H →
`shots/mock2/{A,B}_pro400h_pa1c.JPG`.
- Chroma gain camera / model is now flat (0.93 … 1.05 over chroma 0.5–64 codes); camera vs model
  0.87 (natural), 0.60 (grays): the Pop Art slot behaves like the other two.
- A vs B: RGB identical in 100.0 % of 2,194 shared patches (max difference 1 code): no scene
  dependence in this slot.
- Pro 400H, camera vs target, first (model-only) fit: grays 0.69, ColorChecker × 5 EV 2.48, skin
  1.37, natural 1.20 (p95 2.40), hold-out 1.24, near-neutral 0.94. (With Pop Art's stock chroma
  curves: 1.61 / 3.88 / 2.84 / 2.45 / 2.41 / 2.30.)
- Correction refit `fit_film.py --slot popart1 --anchor A_pro400h_pa1c … --robust 3` →
  `film-pro400h-pa2`: predicted weighted 1.034 → 0.908; grays 0.58, ColorChecker 2.23, skin 1.14,
  natural 1.20, hold-out 1.21. gain 268; S (1, −8, −7, 3, 10, −13); H (0, 1, 1, 18, −4, 5); art ×256
  [[218, 58, −20], [−6, 256, 6], [−16, 13, 259]]; expected EXIF 344 −28 −60 / −68 364 −40 / −16 −108 380.
- `build/three-films-3.BIN`, sha256
  `cf1cf13135e386365882d4ec33cb20960ed578f343386f5433a782cfb0aec1f1`; block 0 differs from
  three-films-2 only in film 3's 24 gamma tables, six-axis records, saturation pair and matrix
  table `t3`; no code bytes. NOT camera-tested.

## 31. Screening the remaining art filters as slot candidates (2026-11-12)

Test RAW A developed with nine stock filters on `three-films-2` (uploads PB120152–160 →
`shots/stockfilters/A_<filter>.JPG`; `analyze_filters.py`). Spatial measures: spread inside a patch
(Natural 0.10 median / 0.9 at the 99th percentile), range of the 25 identical mid grays, change of
the white markers from centre to corner. Colour: the model with the filter's own stock look table,
saturation pair and six-axis records vs the camera (clean slots: natural 0.9, grays 0.5,
ColorChecker 0.9), and the chroma gain camera / model.

| Filter (code) | Spatial | WB applied | Model vs camera (natural / grays / CC) | Chroma curve | Reading |
|---|---|---|---|---|---|
| Pale&Light I (71) | none (0.00; grays identical) | **406 / 510** | 1.02 / 1.09 / 1.54 | own, compressing (gain 0.88 … 1.00 … 0.92) | colour path only; extras = WB shift + stage-(f) tables |
| Diorama (86) | blur bands (spread 2.4 / 12; 2,955 sharp patches) | 520 / 470 | 1.26 / 0.86 / 1.22 on the sharp patches | linear | colour path clean (six-axis 28–64, beyond the calibrated range); blur module on top |
| Pin Hole I (73) | vignette (white −161 codes to the corner) | **506 / 424** | 6.5 / 4.3 / 6.4 (the vignette) | linear | vignette module + WB shift |
| Soft Focus (69) | blur + glow (mid grays range 24) | 520 / 470 | 8.1 / 9.9 / 8.4; chroma gain 0.6, luma −5 | linear | effect module changes tone and colour |
| Grainy Film I (74) | grain (spread 14 / 54) | 520 / 470 | monochrome | default | monochrome + grain |
| Gentle Sepia (91) | none | 520 / 470 | 16.9 (chroma gain ≈ 0) | linear | toning stage |
| Dramatic Tone I (96) | local tone mapping (identical grays range 229) | 520 / 470 | 17.7 | default | effect module |
| Key Line I (163) | flat regions kept; luma +38, chroma ×1.4–1.8 | 520 / 470 | 15.9 | default | effect module |
| Watercolor I (181) | registration failed | – | – | default | effect module |

- **Two filters shift the white balance by themselves: Pale&Light (R ×0.78, B ×1.09) and Pin Hole
  (R ×0.97, B ×0.90).** So there is a per-art-code WB adjustment somewhere, not yet located
  (a seventh per-code item, outside the IMG parameter builders read so far).
- Best fourth-slot candidate: **Pale&Light I** (top-level entry, no spatial effect, colour within
  0.1–0.6 ΔE of a clean slot even with its own chroma curves). Needs: its stage-(f) tables made
  linear (data), the WB shift found and removed, three curve tables, a `gamma3`-style handler entry
  and a `matrix3` test. Second: Diorama, if its blur module can be skipped.
- Pale&Light and Pop Art II were measured on the current build, where they already use the
  default gamma record and have no matrix.

## 32. Evaluation: all twelve visible filters as film slots (2026-11-12)

User goal: evaluate whether every visible art filter can take any film look without making the
firmware unstable. Write-up: `docs/art-slots-evaluation.md`. Working notes:

- **WB shift located:** 0x7E57A028 (callers 0x7E6C5A23, 0x7E7103D4, 0x7E7190AE, 0x7E71B45F): code
  71 / 80 (or mode 102) → pair getter 0x7E550ABA (type 2 → 0x7E550ACC); 73 / 82 → 0x7E550AC3
  (type 2 → 0x7E550AD5, type 3 → 0x7E550ADE); 145 / 146 → 0x7E550ACC. Pairs (u16 × 2, ÷256) at
  0x7E768DB8: (200, 278), (250, 231), (264, 218), (235, 282), (306, 254). 520 × 200/256 = 406 and
  470 × 278/256 = 510: the measured Pale&Light gains.
- **Effect dispatch:** `art_set_func_filter` 0x7E72A562: hash 0x7E85C45C (key = code − 72, 32
  entries of {key, stub}); stubs store a module address; 0x7E72A665 = "no module". Entries: 73, 106,
  108 pinhole; 74, 104 rough_monochrome; 86 diorama; 91 gentle_sepia; 96, 165 dramatic_tone; 163, 169
  artclearline; 181, 182 pastelart; 118 star_light; 151 mirror; 153 composite.
  `art_set_func_effect` 0x7E72A6B0 forces the soft-focus effect when the request's code is 69
  (`cmp 69` at 0x7E72A6F6 and 0x7E72A738).
- **Inventory** (`slots/scan_artcode.py` → `slots/artcode_inventory.json`): jump tables indexed by
  the art code: 0x7E78AEA4 (chroma), 0x7E78C514 (saturation), 0x7E78C8E4 (look), 0x7E78C254
  (six-axis), record side 0x7E8520E0, 0x7E852354; hashes: 0x7E78C154 (gamma), 0x7E74A568,
  0x7E78B29C, 0x7E78CBA8 (IMG; only codes 74, 91, 96, 163, 181 … have entries), 0x7E85C45C
  (effects), 0x7E818CC8 (menu show flags), 0x7E7FF668 / 0x7E7FF568 (movie). Compare clusters per
  family, IMG / WB / record-art-movie: Dramatic 27 / 0 / 2; Key Line 8 / 0 / 14; Watercolor 4 / 0 /
  13; Grainy 3 / 0 / 14; Sepia 5 / 0 / 0; Cross Process 2 / 0 / 1; Pin Hole 0 / 1 / 5; Soft Focus
  0 / 0 / 2; Diorama, Pale&Light (WB 1), Pop Art (the matrix), Light Tone: 0. The scan also hits
  unrelated constants (an "Exif" header parser at 0x7E550F1C); families were counted only where two
  codes of the same family occur together.
- **Gamma variants:** 0x7E56B732 picks column 0…3 from the variant byte (low bits 4 / 5 / 7, top
  bits 0x80 / 0xA0 / 0xC0) and member 0 / 1 from a flag. Default record: member-0 tables are one
  flatter curve (mean |Δ| 131 of 1023 from the stills table), member-1 tables differ by column
  (0x7E74E9BC stills; 0x7E7519BC = 0x7E7579BC, mean |Δ| 22; 0x7E7549BC, 38).
- **Seven-slot mechanism** (`slots/cave2.s`, `slots/build_slots.py` → `patches/history/slots7-code.json`,
  `slots7-neutral.json`; layout `slots/slots7_layout.json`): stubs g4…g7 + `gcommon` (a1 = three
  record addresses; 0x7E56B732 does not touch a1), `matrix7`, tables t4…t7, 12 records, 2 tables at
  0x7ECB0888; 2 tables at 0x7F033B7C; 8 tables in former look tables (0x7E75E4F0, E8F0, ECF0, F0F0,
  F8F0, FAF0, FCF0, 0x7E7616F0). Range check 0x7E56B7A7 → 69 (code 69 = key 0xFFFFFFFF in entry
  31). Gamma hash rebuilt; code 70 (key 0) now matches entry 20. Look entries of the four slots and
  of codes 102, 103, 145, 146, 167, 168, 106 → 0x7E56E94A (Portra's identity copy); chroma entries →
  0x7E5664A0; WB pairs 0 and 1 → 256; effect hash entries 1 and 14 → 0x7E72A665; soft-focus compare
  immediates → 0xFF.
- **Emulator** (`tools/emu/cases.py`: `gamma_select` now models the pick routine and reads slot
  stubs; `matrix_choice` models matrix7; `emurun.py` counts the patched run's reads):
  matrix_choice 256 rows, 16 changed, 0 flagged; gamma_select 917 rows, 116 changed, model equal in
  all, 6 flagged = codes 69, 78, 73, 82, 86, 88 with the P+87 flag set (stock: alternative default
  record 0x7E78B3BC; new slots: their own records).
- `build/seven-slots-neutral.BIN`, sha256
  `2800dc256a53dd9ebd9b84ddce524a2ecd6c57ca68d89266a272248cc6a57f80` = film-portra-xp10-s3 +
  film-ektachrome-lt3-s3 + slots7-code + slot3-chroma-linear + film-pro400h-pa2 + slots7-neutral +
  xp-adaptive-hue-off + three labels. Block 0 differs from three-films-3 in 6,006 bytes, all in
  the intended places; blocks 1–3 and tail equal. NOT flashed.
- `fit_film.py` has the slots `palelight1`, `softfocus`, `pinhole1`, `diorama` (three tables each).

### 32.1 Additions after the first evaluation pass (2026-11-12)
- **P+99 writers** (the gamma column byte): record / art code writes 192 (0xC0) for YC-input jobs
  (rec_3d_yc2jpg 0x7E70C1C3, rec_3d_lens_stl2size, rec_3d_lens_nr_exec, REC MISC YC2VIEW, REC NR
  nr2nr, rec_thum_yc2jpg, rec_thum_yc2yc, art_set_img_ctrl_param 0x7E728AFB / 0x7E728B1F), 194 in
  rec_3d_lens_make_view, `|= 2` / `|= 3` in YC2VIEW; movie code writes 5 (0x7E6C760A) or the result
  of 0x7E6DAE68 / 0x7E6DAF76. No write for the raw still job was found among these, consistent with
  0 = column 0 for raw stills.
- The new slots' records now point member 1 of all four columns at the film's table (was: stock
  defaults outside column 0). Emulator re-run: matrix_choice 16 changed / 0 flagged; gamma_select
  134 changed / 0 flagged (the harness now also counts the patched run's reads).
- `build/seven-slots-neutral.BIN` rebuilt: sha256
  `aeaa8ff0335aac10ee69a1f08ec9b0ad8c05496c2e5caf74bcf7dfdeb6ca5e5b` (first version `2800dc25…`).
- **Record-side classification:** 0x7E70DBB6 (by code, table 0x7E8520E0; 5 callers) and 0x7E70DBDE
  (by picture mode, table 0x7E8522AC; 49 callers). By mode: Pop Art, Pale&Light, Light Tone, Cross
  Process = 1; Soft Focus, Diorama = 3; Grainy, Pin Hole, Sepia, Dramatic, Key Line, Watercolor = 4.
  By code: 70, 71, 72, 85, 145 = 1; 69, 73, 74, 86, 91, 96, 163, 181 = 3; type-II codes 0.
  P+79 is filled from the record context's code (0x7E70E581), which comes from `art_GetFilterType`
  (0x7E70DC05).
- **Design for the five effect filters (not built):** `art_GetFilterType` immediates Grainy 74 → 102,
  Sepia 91 → 106, Dramatic 96 → 108 (two-byte `mov imm8`), Key Line 163 → 145, Watercolor 181 → 167
  (three-byte `mov imm16`); table 0x7E8522AC entries of those modes → kind 1; then the usual slot
  tables for 102, 106, 108, 145, 167. The prototype of §32 keeps kinds 3 / 4 for Soft Focus, Pin
  Hole and Diorama with their module removed; if that flow misbehaves, setting their kind to 1 is
  the fallback.

## 33. Twelve-slot prototype (2026-11-12; NOT flashed)

`slots/build_slots12.py` generates `slots/cave12.s` (nine generic slots: stubs `g_<name>`,
`gcommon`, a two-part compare chain `matrix12` / `chainB`, nine matrix tables, 27 records; 1,456 of
1,912 bytes at 0x7ECB0888, 320 of them code) and writes `patches/history/slots12-code.json`,
`slots12-neutral.json`, `film-pro400h-pa2-s12.json`; layout `slots/slots12_layout.json`.
- Slots and numbers: Pale&Light 71 / 80, Soft Focus 69 / 78, Pin Hole 73 / 82, Diorama 86 / 88;
  Grainy Film → 102 / 103, Gentle Sepia → 106, Dramatic Tone → 108, Key Line → 145 / 146,
  Watercolor → 167 / 168 through `art_GetFilterType` immediates 0x7E71BE3A (4A → 66), 0x7E71BE4C
  (5B → 6A), 0x7E71BE51 (60 → 6C), 0x7E71BE7F (A3 → 91), 0x7E71BE90 (B5 → A7).
- Per number: gamma hash entry → its stub; look → 0x7E56E94A; chroma → 0x7E5664A0; own saturation
  pair and six-axis records (102: 0x7E7696BC, 0x7E76952E / 3A; 106: 0x7E7696C0, 0x7E769546 / 52; 108:
  0x7E7696C4, 0x7E76955E / 6A; 145: 0x7E7696B8, 0x7E769516 / 22; 167: 0x7E7696EC, 0x7E769622 / 2E, the
  Cross Process branch with the adaptive stage off). All five WB pairs → 256. Effect hash entries
  for 73, 86, 106, 108 → 0x7E72A665.
- Table pool (27 of 32 used): 2 in the third free run, 9 former look tables (0x7E75E4F0, E8F0,
  ECF0, F0F0, FAF0, F8F0, FCF0, FEF0, 0x7E7616F0), 21 freed by rewriting Pro 400H's three records so
  that member 1 of every column is its stills table and member 0 the stock default.
- Gamma hash: 27 of 32 entries used; code 70 (key 0) now matches entry 24.
- Emulator, stock vs patch set: `filter_type` (new case; three log helpers stubbed) 75 rows, stock
  = model, 7 changed; `matrix_choice` 22 changed, 0 flagged (the model now decodes the generated
  compare chains from the image); `gamma_select` 156 changed, 0 flagged; 36 distinct stills tables.
- `build/twelve-slots-neutral.BIN`, sha256
  `987d0f2ed96881b7eb200146b65a96576cd7f55dead0be961bf411d27dab69db`. Every block-0 byte that
  differs from stock lies inside a patch op; inside stock code 16 bytes differ (0x7E546161 / 67,
  0x7E56B7A7, 0x7E56C6A5–A9, five `art_GetFilterType` immediates, 0x7E72A6F7, 0x7E72A739).
- Untested by nature of the tools: the record flow with kind 4 entries that have no module, menu
  and playback with the new numbers, movie, art bracketing.

## 34. Camera result of `seven-slots-neutral`: live view freezes in three slots; fix (2026-11-12)

- User report (build `seven-slots-neutral`): in the viewfinder Soft Focus, Pin Hole and Diorama
  **freeze the display**. Pale&Light was not reported as freezing. (A movie clip uploaded as
  PB120161.MOV belongs to a parallel video investigation, not to this one.)
- Reading: the three that freeze are exactly the entries the record code classifies as effect
  filters (by picture mode: Soft Focus 3, Pin Hole 4, Diorama 3; Pale&Light is 1). §32 removed
  their effect modules but left the classification, so live view waits for art processing that
  no longer produces anything. This was the open risk noted in the evaluation (approach "A").
- Fix (the noted fallback): `patches/history/slots7-kind.json` sets all three record-side classifications
  to the colour-only value 1 for those entries: by picture mode (table 0x7E8522AC, read by
  0x7E70DBDE, 49 callers), by code (table 0x7E8520E0, read by 0x7E70DBB6) and by code in the hash
  0x7E852354 (read by 0x7E70E298; key = code − 68; found now). `slots12-kind.json` does the same
  and also sets the five remapped menu entries (104, 108, 109, 119, 120) to 1 by mode.
- Emulator (`art_kind`, new case: the three functions as leaf calls): stock vs `slots12-kind`:
  155 rows, 11 changed (modes 101, 104, 105, 106, 108, 109, 119, 120: 3 / 4 → 1; codes 69, 73, 86:
  3 → 1 in both code tables), 0 flagged.
- Also read: 0x7E70DC24 (jump table 0x7E852300 by picture mode) fills the art request per mode with
  the EXIF ArtFilter ids and four fields at ctx+2416 / 2438 / 2440 / 2442. Not changed.
- Builds: `seven-slots-neutral-b.BIN` sha256
  `da5f1586005315b9363eaa4bf50404902a7b7af7bb67945171bca9c6ccd33838` (10 bytes from the first);
  `twelve-slots-neutral-b.BIN` sha256
  `eab02461d0af1fe749ed6b703a766dd463b65c7fe9eec80a85c8c75f6d36f78f`. NOT camera-tested.

## 35. `seven-slots-neutral-b` still freezes; why; the remap design (2026-11-12)

- User report (build `seven-slots-neutral-b`): Soft Focus, Pin Hole **and Diorama** still freeze
  the viewfinder. So the record-side classification of §34 does not govern live view.
- Cause, read from the code: live view goes through the movie-art code (MOV_ART), not the still
  record flow. It has its own per-code data: `art_chk_type` 0x7E71C0E1 and `art_chk_type_mov`
  0x7E71C28B carry hard-coded lists of effect codes (69, 73, 74, 86, 91, 96, 104, 106, 108, 163,
  165, 169, 181, 182); 0x7E6CC18E uses jump table 0x7E7FF0B0 (code − 69); 0x7E6CC4A6 and 0x7E6CDB83
  use hashes 0x7E7FF300 and 0x7E7FF454 (movie codes, key = code − 77); 0x7E6CDF26 maps (code, type)
  to type-II / III codes through hashes 0x7E7FF668 / 0x7E7FF568. These still say "effect filter"
  for 69, 73, 86, while §32 had removed the effect modules, so live view waits for processing that
  never arrives.
- **Consequence for the evaluation:** converting an effect filter in place means editing the
  still, live-view and movie paths' separate lists and tables. That was not done and is not a
  small or low-risk change. Also: 106 and 108 (Pin Hole II / III) are in those lists, so they are
  not colour-only numbers; the twelve-slot design of §33 used them for Sepia and Dramatic Tone and
  would freeze the same way. **`twelve-slots-neutral(-b)` must not be flashed.**
- **Remap design** (`slots/build_remap7.py` → `patches/history/remap7-code.json`, `remap7-neutral.json`):
  leave 69, 73, 86 and everything about them stock. Send the three MENU ENTRIES to numbers that
  every path already treats as colour-only, through `art_GetFilterType`'s jump table 0x7E854A24
  (data): Soft Focus (mode 101) → 102 (new 2-instruction snippet in code area 2), Pin Hole (105) →
  145 (the stock snippet 0x7E71BE19, used by mode 110), Diorama (106) → 167 (new snippet). Those
  numbers get slot tables (stubs, matrices, their own saturation and six-axis tables, shared
  look, linear chroma; WB pair 2 → 256 for 145). Record-side kind by picture mode → 1 for the
  three entries. Pale&Light I stays converted in place (it is a colour-only filter; it did not
  freeze). Pro 400H is reduced to its three stills tables to free table space.
- Only 102, 145 and 167 are known colour-only spare numbers, so this route yields at most three
  more slots: **seven film slots in total**. Grainy Film, Gentle Sepia, Dramatic Tone, Key Line and
  Watercolor have no number left to go to.
- Open: whether live view takes its number from `art_GetFilterType` (then it shows the film) or
  from the menu's own base number (then live view still shows the stock effect while the photo
  gets the film). Either way nothing that live view expects has been removed.
- Emulator, stock vs the patch set: `filter_type` 9 changed (mode 101 → 102, 105 → 145 for all
  types, 106 → 167), 0 flagged; `art_kind` 3 changed (modes 101, 105, 106 → 1); `matrix_choice` 14
  changed, 0 flagged; `gamma_select` 108 changed, model equal everywhere (12 rows flagged by the
  read-set bookkeeping for codes 147, 150, 102, 103, whose stock tables are not patched).
- `build/seven-slots-remap-neutral.BIN`, sha256
  `b4d239a714835a96e41fd035c9e4c3fc95aef8a540c81fbe9054147469a791ea`. Bytes changed inside stock
  code: the same 8 as in the three-film build (0x7E546161 / 67, 0x7E56B7A7, 0x7E56C6A5–A9). NOT
  camera-tested.

## 36. `seven-slots-remap-neutral` also freezes; retreat to four slots (2026-11-12)

- User report (build `seven-slots-remap-neutral`): the same three entries (Diorama, Pin Hole, Soft
  Focus) freeze the viewfinder. In that build their numbers 69 / 73 / 86, effect modules and all
  IMG tables were stock; what differed from stock for those entries was (a) `art_GetFilterType`
  returning 102 / 145 / 167 and (b) the record-side kind by picture mode set to 1. So at least one
  of those two conflicts with what live view does for these entries. Which one is not known; the
  per-mode art request builder 0x7E70DC24 (it writes a filter id and four fields per picture mode)
  and the movie-art path have not been traced.
- Three builds in a row froze live view for these entries (§34, §35, this one), each from an
  untested reading of code. **No further build touches an effect filter until the live-view path
  is traced on paper.** Open questions to answer first: where live view takes the art number from;
  what the request fields at ctx+2416 / 2438 / 2440 / 2442 and the block at ctx+3616 mean; what
  `art_chk_type_mov` returns for a number outside its lists.
- What the three failures do show: Pale&Light I, converted in place in all three builds, was never
  reported frozen, and the three films kept working.
- `slots/build_four.py` → `patches/history/four-code.json`, `four-neutral.json`: the three-film structure
  plus Pale&Light I only (gamma stub, matrix, shared look, linear chroma, WB pair 1.0); nothing
  else. Pro 400H keeps all 24 tables (`film-pro400h-pa2`). Emulator, stock vs the patch set:
  `filter_type` 0 changed, `art_kind` 0 changed, `matrix_choice` 10 changed / 0 flagged,
  `gamma_select` 98 changed / 0 flagged.
- `build/four-slots-neutral.BIN`, sha256 `c3f0f466663f257656cea321a8307802bb42db08eee45c234b0e70317af85942`. Block 0 differs from three-films-3 in 1,612 bytes: the jump target, Pale&Light I's tables and lookup entries, its WB pair, 256 bytes in code area 2 and two tables in the third free run; blocks 1–3 equal. NOT camera-tested.

## 37. Stills from `seven-slots-remap-neutral`; the live-view cause found; `remap2` (2026-11-12)

### 37.1 RAW Data Edits on `seven-slots-remap-neutral` (uploads PB120002–013 → `shots/remap7/R7_NN.JPG`)
The uploads reused the names PB120002…, overwriting the first-mock files of §25 in `shots/`
(PB120002 was the xp8 anchor of `fit_xp9.py`; that refit can no longer be re-run; the module now
loads without it). Test RAW A, compared with the Natural rendering of the same file:

| Menu entry (number it now produces) | vs Natural | Spatial | Reading |
|---|---|---|---|
| Soft Focus (102) | RGB identical in 88.8 %, within 2 codes in 98.0 %, ΔE 0.09 | none | **clean: no blur, no glow** |
| Pale&Light (71, in place) | the same figures | none | **clean; WB 520/470** |
| Diorama (167) | identical 59.8 %, within 2 codes 82.1 %, ΔE 0.66 | none | no blur; small colour difference: 167 / 168 have entries in one more per-number stage (hash 0x7E78C6E4, 64 entries, key = code − 8, worker 0x7E56E495) |
| Pin Hole (145) | ΔE 4.86 | none: white markers 0.0 centre to corner | **no vignette**; the difference is WB 506/424: the WB multipliers are also chosen by picture mode (105 → pair 1) |
- Portra and Ektachrome: RGB identical to §28.4 in 100 % of patches. Pro 400H differs because this
  build carries the `pa2` refit (first camera result for it; not yet scored).
- So for stills the remap works for all three effect entries. The freeze is a live-view matter.

### 37.2 Why live view froze in the remap build (read from the code, with the tables dumped)
- `mov_art_set_artmode` 0x7E6CCB57 and `mov_art_exec_init` 0x7E6CD1F2 call `art_GetFilterType`, so
  the live-view art request carried the new numbers (102, 145, 167).
- But the movie / live-view code also has **its own menu-entry → number tables**, twice: function
  0x7E6CBFD3 (tables 0x7E7FF05C "still" and 0x7E7FF008 "movie") and function 0x7E6DBA95 (tables
  0x7E807880 and 0x7E80782C). Index = picture mode − 100; each entry is a stub `mov N,d2; jmp tail`
  (tails 0x7E6CC14E and 0x7E6DBBC4). They still gave 69 / 73 / 86 for the three entries. So one part
  of live view worked with an effect number and another with a colour-only number.
- In §34 / §35 (first two builds) the numbers agreed but the effect modules had been removed.
- `rec_art_set_exif_data` 0x7E70DC24 (jump table 0x7E852300) only fills EXIF fields: not involved.

### 37.3 `remap2`
`slots/build_remap7.py` → `patches/remap7b-code.json`: as remap7-code, plus
- entries 101, 105, 106 of the two "still" tables 0x7E7FF05C and 0x7E807880 → stubs for 102 (new),
  145 (the stock stub of entry 110) and 167 (new); the two "movie" tables are left stock (movie
  recording keeps the stock effects for these entries; a parallel investigation covers video);
- all five WB multiplier pairs → 256;
- hash 0x7E78C6E4 entries of 167 and 168 → its default path 0x7E56E5DC.
Emulator (stock vs patch set): `filter_type` 9 changed / 0 flagged, `art_kind` 3 changed,
`matrix_choice` 14 changed / 0 flagged, `gamma_select` 108 changed, model equal in all rows. The
two movie-art functions themselves are not emulated.
`build/seven-slots-remap2-neutral.BIN`, sha256
`bf5ee5c1d83bf26779838e3432f2e454283f5591b0b6b252ffff90fc6d17da29`: 249 bytes of block 0 differ
from the remap build (WB pairs, two hash entries, six table entries, the new stubs); the bytes
changed inside stock code are the same 8 as in the three-film build. NOT camera-tested.

### 37.4 Correction: the earlier uploads were not lost
The user moves older uploads into `shots/archive/`, `archive1/`, `archive2/`, `archive3/`; they are
not overwritten. The first-test-image files of §25 are in `shots/archive/` (PB120002 = xp8,
PB120153 = xp9, PB120158 / 159 = Ektachrome lt / lt2). Copies under clear names:
`shots/mock1/{xp8_mock1, xp9_mock1, ektachrome_lt_mock1, ektachrome_lt2_mock1}.JPG`; reads
`out/mock/read_xp8_mock1.npz`, `read_xp9_mock1.npz`. `fit_xp9.py` uses `xp8_mock1` again
(1,741 anchor patches). The statement in §37.1 that the xp8 anchor could no longer be used is wrong.
Rule from now on: copy every upload to a named folder at once and never rely on a `shots/PB…` name.

### 37.5 `seven-slots-remap2-neutral` on the camera (2026-11-12)
User report: **the viewfinder no longer freezes.** So the freeze of §36 was the disagreement between
`art_GetFilterType` and the live-view code's own menu-entry → number tables (§37.2), and making
them agree fixes it. Still to learn: what live view shows in the three entries (normal or the old
effect), and the RAW developments of the test image on this build.

### 37.6 `seven-slots-remap2-neutral`: live view and stills (2026-11-12)
- User: live view in Soft Focus, Pin Hole and Diorama **looks normal** (no effect, no freeze). No
  ordinary photo taken yet on this build.
- RAW developments of test RAW A (uploads PB120002–008 → `shots/remap2/R2_*.JPG`):
  - **Soft Focus, Pin Hole, Diorama and Pale&Light give pixel-identical images** (the JPEG files
    differ only in metadata). Pin Hole's WB is 520/470 now; Diorama's extra difference is gone.
  - vs Natural on the same build: RGB identical in 88.8 % of patches, within 2 codes in 98.0 %, ΔE
    mean 0.09 (grays 0.000, natural colours 0.085). The 130 patches more than 2 codes off are
    saturated ones (gamut-edge 45, natural 31, cube 27, ColorChecker 19): the slots use the linear
    chroma curves and zero six-axis records, Natural its default chroma records and its own variant.
  - Pro 400H `pa2` (first camera result), camera vs target, first fit → refit: grays 0.69 → 0.61,
    ColorChecker 2.48 → 2.33, skin 1.37 → 1.14 (predicted 1.14), natural 1.20 → 1.19, hold-out
    1.24 → 1.22, near-neutral 0.94 → 0.92.
- **Seven film slots are established for stills and live view:** Cross Process, Light Tone, Pop Art
  (films) and Pale&Light, Soft Focus, Pin Hole, Diorama (empty, rendering as Natural).
- Open: an ordinary photo in the new entries; movie (left stock; parallel investigation); art
  bracketing; playback of saved files.

## 38. Check build: the known Portra look in all four new slots (2026-11-12; NOT flashed)

The neutral test of §37.6 proved which tables each new slot selects, but with a neutral look two
stages do nothing (identity matrix, zero six-axis records) and the three curves are equal. Each new
slot reaches its six-axis records through a different stock handler (Diorama's through the Cross
Process branch), and each has its own matrix table. `slots/fill_slots.py` writes the Portra xp10
fit into all four generic slots (`patches/history/check-portra-in-new-slots.json`);
`build/seven-slots-portra-check.BIN`, sha256
`354a706908a616b4ec8ce843e9c6409d6afa1c75b9e04a3b8bc0a85385949842`.
Expected: a RAW development of the test image in Pale&Light, Soft Focus, Pin Hole and Diorama is
pixel-identical to the Portra 400 entry, and each JPEG's EXIF ColorMatrix reads 348 −44 −48 /
−60 328 −12 / −14 −128 398. Emulator: the four slots select curve tables with the same contents as
the Portra slot.

### 38.1 Result of the Portra check build (2026-11-12)
`seven-slots-portra-check` flashed; uploads PB120002–007 → `shots/portracheck/PC_*.JPG` (test RAW A
developed as Portra 400, Pale&Light, Soft Focus, Pin Hole, Diorama ×2).
- **All four new slots are pixel-identical to the Portra 400 entry: 100.000 % of pixels, maximum
  difference 0.** The Portra entry itself is pixel-identical to its xp10 measurement of §28.4.
- EXIF ColorMatrix 348 −44 −48 / −60 328 −12 / −14 −128 398 in all six files, as expected.
- So curves, matrix, six-axis, saturation, look and chroma behave identically in every generic
  slot, including Diorama's (number 167, through the Cross Process branch). A film fitted for one
  slot renders the same in any other.
- No ordinary photo was uploaded from this build; that check is still open.

### 38.2 More candidate films (2026-11-12)
Targets baked for every remaining stock (negatives on a paper, Provia with `bake_slide.py`; Portra
800 push 2 failed to bake, not investigated). Distance = mean ΔE2000 between targets on the
hold-out natural colours; fit = model-only prediction (natural colours / ColorChecker).

| Film (print) | nearest installed (Portra 400 / Ektachrome / Pro 400H) | nearest of Kodachrome 64 / Vision3 250D / Velvia | fit |
|---|---|---|---|
| Portra 800 (Endura) | 4.21 | 4.66 | 1.59 / 3.11 |
| Velvia 100 | 3.20 | 4.37 | 1.20 / 2.16 |
| Superia X-tra 400 (Crystal Archive) | 3.04 | 4.80 | 1.12 / 2.17 |
| Vision3 250D (2383) | 2.23 (Pro 400H) | 4.12 | 0.92 / 2.11 |
| C200 (Crystal Archive) | 2.15 | 3.95 | 1.05 / 2.00 |
| Provia 100F | 2.05 (Ektachrome) | 2.68 | 0.83 / 1.53 |
| Kodachrome 64 | 2.02 (Ektachrome) | 4.12 | 0.66 / 1.27 |
Near-duplicates: Ultramax 400, Portra 160, Ektar 100, Gold 200 on Endura (1.0–1.3 from Portra 400);
Vision3 50D / 200T / 500T, Verita 200D on 2383 (0.9–1.5 from Vision3 250D); Portra 400 on 2383
(1.9 from Vision3 250D); Gold 200 on Crystal Archive (1.9 from Pro 400H). The print material
dominates the look. Correction to §29.4: Vision3 250D's nearest installed look is Pro 400H at 2.23.

## 39. Seven films, assigned in menu order (2026-11-12; NOT flashed)

- User: build the seven-film firmware, and put the films in the menu in the order they were added.
- The menu's order itself is not changed (its lists and label tables were not studied). Because the
  seven slots are equivalent (§38.1), the same result is reached by assigning films to the film
  slots from the top of the menu down: Pop Art → Portra 400, Soft Focus → Ektachrome 100,
  Pale&Light → Fuji Pro 400H, Light Tone → Kodachrome 64, Pin Hole → Vision3 250D (2383), Diorama →
  Velvia 100, Cross Process → Superia X-tra 400 (Crystal Archive). Grainy Film (stock) stays
  between Light Tone and Pin Hole; Gentle Sepia, Dramatic Tone, Key Line, Watercolor follow, stock.
- `slots/build_seven_films.py` → `patches/seven-structure-extra.json` (identity look tables for
  Cross Process I, Light Tone, Pop Art I; Light Tone's gamma hash entries), `seven-films-1.json`
  (the seven looks), `seven-labels.json` (labels "Portra", "Ektachrome", "Pro 400H", "Kodachrome",
  "Vis 250D", "Velvia", "Superia 400"; exact strings only: 20, 7, 2, 2, 21, 63, 20 copies; longer
  strings such as "Add Soft Focus Effect" untouched). Looks: Portra xp10, Ektachrome lt3, Pro 400H
  pa2 (all camera-corrected); the four new ones are model-only first fits (`out/fit_cand-*.npz`,
  predicted natural 0.66 / 0.92 / 1.20 / 1.12).
- `build/seven-films-1.BIN` = remap7b-code + slot3-chroma-linear + seven-structure-extra +
  seven-films-1 + xp-adaptive-hue-off + seven-labels; sha256
  `a57cb462688a84d32b9a373b00c0947a52096cc1cb06b2d29991d20720656728`. Emulator: `filter_type`
  9 changed / 0 flagged, `matrix_choice` 14 / 0, `gamma_select` model equal in all rows; the seven
  slots select 21 different curve tables; Portra's three stills curves in the Pop Art slot are
  byte-identical to those of the measured Portra slot. Stock-code bytes changed: the same 8.
- Expected on the camera: Portra, Ektachrome and Pro 400H pixel-identical to their last
  measurements (now under other entries); the four new films near their predictions + 0.3–0.5.

## 40. seven-films-1 on the camera; correction refits → seven-films-2 (2026-11-12)

- First upload (`shots/films1/`, 12 files): every film entry byte-identical to the files of
  `seven-slots-portra-check`, so the camera had not been updated. The user reported a crash on
  RAW Data Edit in Diorama in that session; not reproduced (Diorama worked before on that firmware
  and after on seven-films-1, and the two builds differ only in table data). Unexplained.
- Second upload after flashing (`shots/films1b/F1_*.JPG`): menu names correct (user); all seven
  EXIF matrices as predicted; Portra / Ektachrome / Pro 400H pixel-identical to
  `mock2/A_portra_xp10`, `mock2/A_ektachrome_lt3`, `remap2/R2_pro400h_pa2`. So §39's slot
  assignment is confirmed, including Diorama (167) with a look other than Portra.
- First fits measured (natural, predicted in brackets; camera vs model): Kodachrome 1.07 (0.65;
  0.93), Vision3 250D 1.39 (0.93; 0.95), Velvia 1.57 (1.20; 0.84), Superia 1.37 (1.11; 0.89).
- Correction refits, `fit_film.py --slot xp1 --anchor F1_<film> out/fit_cand-… --robust 3` →
  `out/fit_film-{kodachrome64,vision3250d,velvia100,superia400}-2.npz` (logs `out/refit_*.log`).
  Predicted (measured + model change), GRKit-weighted: Kodachrome 1.098 → 0.815 (skin 0.86 → 1.00,
  natural 1.07 → 1.06, grays 0.90 → 0.59); Vision3 1.285 → 0.936 (skin 1.55 → 0.95, natural
  1.39 → 1.21); Velvia 1.210 → 1.070 (skin 2.00 → 1.65, natural 1.57 → 1.53); Superia
  1.175 → 1.064 (skin 1.63 → 1.54, natural 1.37 → 1.39).
- The slide targets' cube files are named `…_portraendura.cube` although baked with
  `scan_film` on (`bake_slide.py` must pass a paper to the CLI; the pipeline ignores it). Naming only.
- `slots/build_seven_films.py 2` → `patches/seven-films-2.json`; `build/seven-films-2.BIN`
  (same patch list with seven-films-2), sha256
  `1f7d0db62f906da4e10de0ad3546f58f4eb5d1b008ae8e4baeb7a1e2b5170c01`. Differs from seven-films-1
  only in the four new films' tables (curves, matrices, six-axis, saturation); blocks 1–3 equal.
  Emulator reports equal to seven-films-1's except table hashes (gamma_select's 12 "changed without
  reading patched bytes" rows, codes 102/103/147/150, are present in both). NOT flashed.

## 41. seven-films-2 measured (2026-11-12)

- `shots/films2/F2_*.JPG`; matrices as predicted. Camera vs target, first fit → corrected:
  Kodachrome natural 1.07 → 1.07, skin 0.86 → 0.97, ColorChecker 2.11 → 1.79, grays 0.90 → 0.89;
  Vision3 250D 1.39 → 1.22, 1.55 → 1.13, 2.82 → 2.71, 0.86 → 0.74; Velvia 1.57 → 1.52,
  2.00 → 1.68, 2.67 → 2.50, 0.79 → 0.79; Superia 1.37 → 1.39, 1.63 → 1.56, 2.80 → 2.66,
  0.75 → 0.74. Camera vs model 0.85–0.97 (the model's floor), so a further round is not expected
  to help.
- Ordinary photos taken in the Diorama, Pin Hole and Pop Art entries saved with the right matrices
  (`shots/films2/photo_*.JPG`): normal shooting works in a remapped and an in-place slot.
- OPEN: user reports rare freeze + restart when RAW Data Edit is about to save (two events known:
  Diorama on seven-slots-portra-check, one unspecified entry on seven-films-2). Not reproduced, not
  explained. Unknown whether it needs the patched firmware or the synthetic RAW PB130001.ORF. The
  code added by the patches runs when the matrix and curves are chosen, not at save time; the
  tables placed in "free" loaded space (0x7ECB0888, 0x7F033B7C) still read back correctly (pixel-
  identical output), which argues against them being overwritten, but does not rule out the
  firmware using that space for something else at save time.

## 42. Clean-up (2026-11-12)

- `shots/` reduced to `testraw/`, `measured/`, `photos/` (see README). All other camera files this
  document names (chart series PB0901xx, SpyderCheckr PB1102xx, real photos PA30/31xxxx, the
  per-round folders) were deleted at the user's request; sections that analyse them cannot be
  re-run. The cached patch readings `out/mock/read_*.npz` were kept.
- Superseded patch specs moved to `patches/history/`; superseded firmware builds deleted.
- `make_mock.py` / `make_mock2.py` now take the donor ORF from `shots/testraw/PB090221.ORF`.

## 43. Restart cause found for Diorama; chroma curves fitted; second types; `seven-films-3` (2026-11-12; NOT flashed)

### 43.1 Audit of the patched image (sub-agent, key points re-checked by me in the bytes)
- **Bug in our remap.** `0x7E716C56` attaches a raw-plane buffer at P+16 only when the *picture mode*
  is 104 (Grainy Film) or 107 (Cross Process). The six-axis handler of art code 167 is Cross
  Process's (`0x7E56D5CF`, jump table 0x7E78C254): it loads (16,P) without a check and runs the
  adaptive-hue statistics over four planes. Stock reaches 167 on the still path only from mode 107.
  Our Diorama entry (mode 106) reaches it with P+16 = leftover stack. The reads change nothing
  (`xp-adaptive-hue-off` discards the statistics), so output is pixel-identical, but a stale pointer
  can fault: rare and history-dependent. Fits the first logged restart (Diorama, after a Grainy Film
  development, the other mode that writes P+16). Does not explain a restart in another entry.
- The three free regions are inside the copied lengths of their loaders (boot task 0x7E44A043;
  Usr1 0x7E504AF9, two segments); no stock pointer or immediate refers into them; the constructor
  walker uses fixed lengths that end where each region starts. New code: register / stack discipline
  matches the stock patterns it replaces. Save path: still art processing is decided by art code
  (`art_IsSupportType`), no wait on an effect for 102 / 145 / 167.
- Open from the audit: the matrix chain and gamma stubs live in the Usr1-loaded segment; a still
  developed before Usr1 finishes loading would jump into unloaded RAM. Not traced whether the camera
  can develop that early (test: power on and shoot at once).

### 43.2 Fixes (`slots/build_fixes.py` → `patches/seven-fixes-1.json`, on top of remap7b-code)
- 167's six-axis entry → new 17-byte handler at 0x7E880FD4 (boot segment): `mov 0x7E769622,a3;
  mov 0x7E76962E,a2; jmp 0x7E56D8D8`, the shape of every plain stock handler. Emulator case
  `six_handler`: 167 exit "statistics (reads P+16)" → "tail", same two records; 17 other codes equal.
- Second types: three immediates in `art_GetFilterType` (0x7E71BDDB 102 → 70, 0x7E71BDF1 145 → 71,
  0x7E71BE0D 167 → 85). The live-view functions never looked at the type. Emulator `filter_type`:
  mode 100 / 102 / 107 type 2 → 70 / 71 / 85.
- Chroma jump table 0x7E78AEA4: stills codes 71, 102, 145, 167 back to their own stock handlers
  (records 0x7E74B91C, BBCA, BB68, BE16; 70, 72, 85 already had B8BA, B97E, BAA4); movie codes 79,
  80, 81, 87, 103, 146, 168 → 0x7E566308 (Soft Focus's record 0x7E74B858, linear, untouched), so
  movies keep straight chroma curves as before.

### 43.3 The chroma-curve stage decoded (`chroma.py`)
- Record = x[16], y[16], slope[17], x[16], y[16], slope[16]; piecewise linear on 8-bit chroma about
  128; `out = y[i] + slope[i]·(c − x[i])/128` for the first knot with x[i] ≥ c. It is the last
  stage: applied to the Cb and Cr of the otherwise finished picture (BT.601 full range).
- Check with the cached readings of the same film with Pop Art's stock curves (`A_pro400h_pa1`) and
  with linear ones (`A_pro400h_pa1c`): curve(linear build) vs Pop Art build 0.47 / 0.50 codes rms
  on Cb / Cr (identity: 1.79 / 2.07); 6,010 patches.
- **Unknown: which stored curve is Cb.** All 16 stock records have two equal curves. Assumed
  first = Cb (`chroma.FIRST_IS_CB`); the first build with unequal curves decides.

### 43.4 Refits with the curves free (`fit_chroma.py`)
Knots at 0, 28, 58, 88, 108, 128, 148, 168, 198, 228, 255; 108–148 kept at slope 1 (neutrals and
faint colours stay with the saturation gain); 8 free heights per curve; everything else refitted
too; objective = measured samples of each film's last build, soft-L1 3, predicted as
curve(measured + model change). Predicted, measured → new:

| film | weighted | ColorChecker ×5 EV | skin | natural | hold-out | grays |
|---|---|---|---|---|---|---|
| Portra | 1.251 → 0.930 | 2.58 → 1.57 | 1.36 → 1.16 | 1.33 → 1.19 | 1.35 → 1.21 | 0.98 → 0.78 |
| Ektachrome | 1.054 → 0.826 | 2.24 → 1.67 | 1.35 → 1.09 | 1.36 → 1.24 | 1.36 → 1.26 | 0.77 → 0.59 |
| Pro 400H | 0.958 → 0.762 | 2.33 → 1.41 | 1.14 → 1.13 | 1.19 → 1.09 | 1.22 → 1.13 | 0.61 → 0.55 |
| Kodachrome | 1.056 → 0.852 | 1.79 → 1.35 | 0.97 → 0.83 | 1.07 → 1.05 | 1.11 → 1.05 | 0.89 → 0.71 |
| Vision3 250D | 1.117 → 0.753 | 2.71 → 1.49 | 1.13 → 1.13 | 1.22 → 1.13 | 1.24 → 1.15 | 0.74 → 0.53 |
| Velvia | 1.165 → 0.897 | 2.50 → 1.76 | 1.68 → 1.54 | 1.52 → 1.40 | 1.52 → 1.40 | 0.79 → 0.63 |
| Superia | 1.140 → 0.913 | 2.66 → 1.86 | 1.56 → 1.52 | 1.39 → 1.30 | 1.39 → 1.30 | 0.74 → 0.62 |

Control (Velvia, same refit with the curves held linear): weighted 1.012, ColorChecker 2.36: the
gain is from the curves. All fitted curves compress strong chroma (slopes 0.4–0.8 outside ±20) with
a higher saturation gain. Fits: `out/fit_film-*-c1.npz`.

### 43.5 Build
`slots/build_seven_films.py 3` → `patches/seven-films-3.json` (also writes each slot's chroma
record). `build/seven-films-3.BIN` = remap7b-code + seven-fixes-1 + seven-structure-extra +
seven-films-3 + xp-adaptive-hue-off + seven-labels (slot3-chroma-linear no longer needed); sha256
`e38ece2331afcd7af98978690a64fce29273cad5ebde4f8a3b683993c8a1ea72`. Checked in the built image:
each of the seven codes reaches its own record and the record equals the fit; movie codes →
linear; blocks 1–3 equal to seven-films-2. Emulator: filter_type 12 changed / 0 flagged,
matrix_choice 14 / 0, curve_select 16 / 0, art_kind 3 / 0, gamma_select as before, six_handler 1 / 0.

### 43.6 White balance (item still to measure)
The matrices for other white-balance settings are not in the firmware as literal tables (searched
all four blocks for the 5300 K matrix in several encodings: no hit), so they cannot be simulated.
Test on the camera: develop PB130001 with WB set to Tungsten and to Shade, in Natural and in two
film entries; the EXIF ColorMatrix gives each setting's matrix.

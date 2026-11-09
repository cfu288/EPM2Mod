# 12. Exposure control, AF control and the files written (E-PM2 v1.6)

This section goes below the module-level map of sections 02 §4–6, 03 §7–8 and 07.

- **Labels:** **verified** = read in the code or bytes; **inferred** = from names, order or layout; **external** = product knowledge or ExifTool, not from the code.
- **Addresses:** E-PM2 v1.6 runtime addresses (base 0x7E421020). "Q8" = signed 16-bit, 256 = 1.0 EV (APEX).
- **MN103 note:** `btst imm,Dn` tests a mask, not a bit number.
- **Scripts** (run with `python3 -I`, firmware path as argument): `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/expaf/`. They are `ifds.py`/`ifdnames.py` (Exif IFD lists), `rec42.py` (per-mode exposure records), `hasht.py` ({key, handler} tables), `etnames.py` (reads ExifTool `Olympus.pm` as data and never runs it), plus the `words.py`/`strs.py` helpers.
- **Not done:** no cross-body comparison for this section (see the open questions).

## 1. Exposure control

### 1.1 Overview

- **Two different exposure engines** (verified):
  - **Still exposure** is computed by `exp_cal_still`, entry 0x7E693D00. It is called from TAKE_EXPOSE.
  - **Live view and movie exposure** is computed by the EXP_MOVIE task (section 03 §7b).
  - Both live in the `exp` module (0x7E68F0DD–0x7E6A9400) and share its Q8 helpers.
- **How the still exposure is computed** (inferred from the structure below):
  1. The shooting mode is reduced to a canonical exposure program.
  2. A per-program 42-byte record of APEX corner values is fetched.
  3. Eight BV breakpoints (BV = Av + Tv − Sv) are built from it.
  4. The scene BV is placed on one of 9 line segments, and each segment has its own solver.
- **There is no fixed table of Tv/Av pairs.** The "program line" is parametric. The corners come from the per-mode record, and the "min" and "max" sentinels in it are replaced by the lens and body limits.

### 1.2 Call chain and key functions

| Step | Address | What it does | Basis |
|---|---|---|---|
| TAKE_EXPOSE handlers (lock, release, continuous) | 0x7E582F9A, 0x7E5832D9, 0x7E583FAA, 0x7E584C97, … | All of them call 0x7E5865B3 | verified (calls.tsv) |
| `continue trace calculate` | 0x7E5865B3 | Takes the semaphore at 0x7E43EAC2, then calls 0x7E5865F2 | verified |
| `exp_cal_still` | 0x7E693D00 | Calls the sub-steps below, then copies its inputs and results into the debug capture (0x7E69E86F → the buffer pointed to by 0x605A7370; `exp still on/info`) | verified |
| Mode canonicalisation | 0x7E69433B, table 0x7E7DBC94 | Maps mode byte 12–183 to a program code (below). A byte at +40 equal to 4 or 5 forces A or S | verified |
| Per-mode record lookup | 0x7E6942CE, table 0x7E7DB508 | 45 records of 42 bytes, key u16 at +40. A missing key gives error 0x0E000050 through 0x7E426D4B | verified |
| Corner resolver | 0x7E6940C6 / 0x7E694181 / 0x7E6941DA → 0x7E694412 | Sentinels (verified): 0x9B00 → user value (0x7E69561E, or 0x7E6A30B0 when byte +40 = 4); 0x6400 → max (field +16); 0x9C00 → min (field +14). Every result is clamped to [min, max] by 0x7E6A8EA4. 0x7E6941DA also has cases for the art codes 69–181 | verified |
| Exposure-mode switch | 0x7E6945EF | Program code 6 or 58 → 0x7E69464B (manual path). Any other code → 0x7E6947C1 (auto path). Then 0x7E694F5D, 0x7E6951A6, 0x7E695591. Mode byte 90 → 0x7E69474D | verified |
| Program line | 0x7E6947C1 | 0x7E6948AE builds 8 s16 breakpoints as sums and differences of the corner fields (+6…+26). A loop finds the first breakpoint that is below the scene BV. Segments 1–7 go to 0x7E694A24, 0x7E694B02, 0x7E694B7F, 0x7E694C68, 0x7E694D34, 0x7E694DDE, 0x7E694E56; segments 0 and 8 are the end clamps | verified structure; Av/Tv/Sv roles inferred |
| Compensation-style bias | 0x7E694540 | clamp(a − b + sel, −768, +768) = ±3.0 EV, then added to the target. `sel` is one of 3 BV inputs, chosen by a byte ∈ {0, 1, 2} (0x7E6A89AD) | verified arithmetic; "exposure compensation" inferred (the ±3 EV range matches `MT_EXP_BIAS_MINUS_3_0…PLUS_3_0`) |
| APEX → Exif rational | 0x7E69B184 (Tv), 0x7E69B1D9 (Av), 0x7E69B31E (bias) | Called by the Exif filler. Each has three variants for step 256 / 128 / other. Small lookup tables at 0x7E7E1xxx | verified calls; tables not decoded |

**Mode numbering** (verified from two independent consumers: the exp remap table and the Exif filler 0x7E7096DC):
- 3 = P, 4 = A, 5 = S, 6 = M, 7 = iAuto.
- 76 / 77 / 89 / 90 also map to P / A / S / M (inferred: probably the movie P/A/S/M modes).
- For the other modes the Exif writer stores CameraSettings SceneMode = mode − 1 (verified). ExifTool's SceneMode names then name each mode (external): 8 → 7 Sport, 9 → 8 Portrait, 11 → 10 Landscape, 12 → 11 Night Scene, 20 → 19 Fireworks, and so on.

Table 0x7E7DBC94 remaps these modes (verified):
- 76→3, 77→4, 89→5, 90→6;
- 78–83 → art codes 69–74, 87→85, 88→86, 93→91, 97→96, 102/103→70, 104/105→74, 106–109→73;
- 128→8, 129→9, 130→11, 131→18 or 12, 132→18, 136→21, 146→145, 158→17, 160→23, 161→157, 164→163, 183→181;
- every other mode passes through unchanged.

### 1.3 Decoded program-line records (table 0x7E7DB508)

Each record holds 19 Q8 values plus a u16 flag. Sentinels: **max** = 0x6400, **min** = 0x9C00, **user** = 0x9B00.
- **Field groups (inferred, strong):** [0–9] Av corners, [10–13] Sv (ISO) corners, [14–18] Tv corners.
- **Evidence for the groups:**
  - A has "user" in [0–9]. S has "user" in [14–18]. M has "user" in both.
  - The literal values fit E-PM2 limits (external): Tv 12.0 = 1/4096 s ≈ 1/4000 (the top shutter speed), Tv −6.0 = 64 s ≈ 60 s (the slowest auto speed), and Sv 6.0 = ISO 200 (the base ISO).

| Mode (key) | Av [0–9] | Sv [10–13] | Tv [14–18] | flag |
|---|---|---|---|---|
| P (3) | max, 7, 7, 7, min, 4, 4, min, min, min | max, 99, 6, 6 | 12, max, 99, −6, 99 | 1 |
| A (4) | user ×10 | max, 99, 6, 6 | 12, max, 99, −6, 99 | 1 |
| S (5) | as P | max, 99, 6, 6 | user ×5 | 0 |
| M (6) / 58 | user ×10 | max, 99, 6, 6 (58: 99, 99, 99, 6) | user ×5 | 0 |
| Sport (8) | as P | as P | 12, max, **9**, −6, 99 | 2 |
| Portrait (9) | max, then min ×9 (open aperture) | as P | as P | 2 |
| Night Scene (12) | as P | **6, 6, 6, 6** (ISO fixed at 200) | as P | 2 |
| Fireworks (20) | 7, 7, 7, 7, 4 ×6 | 6 ×4 | **−2 ×5** (4 s) | 0 |
| key 41 (ExifTool 40 "Digital Image Stabilization") | as P | **10** (ISO 3200), 99, 6, 6 | 12, max, **8**, −6, 99 | 2 |

- **Verified:** the bytes, the sentinel handling and the key order.
- **Inferred:** the field roles and the scene names. Example reading: in Sport, Tv corner [16] is 9.0 (1/500 s) instead of 99, so the line holds a fast shutter.
- **Art codes 69–181** use the P record with flag 1 (verified).

### 1.4 Metering and the 18×18 grid

- **The still result holds every metering candidate.** The capture block +60 is printed by 0x7E69EDF3 (`exp_cal_still[bv]`). It holds `bv_cntr, bv_arnd, bv_ave, bv_ave2, bv_esp, bv_spot`, then `face_num, gyako` (backlight), `mode` and `bv_std` at +200/+201/+202 (verified field offsets).
  - So centre, surround, average, ESP and spot BVs are all computed, and `mode` picks the BV used (`bv_std`) (inferred).
  - **Not mapped:** the selection switch for the five user metering modes (ESP / centre-weighted / spot / spot-highlight / spot-shadow). The highlight and shadow variants are probably the spot BV plus a fixed offset, but this was not found in code.
- **The 18×18 grid** (`*** [EXP] BV_18x18 ***` 0x7E693B6C) feeds three things:
  - ESP (`[exp]esp bv:` 0x7E6913FE);
  - face weighting (`table_calc face pix`);
  - the clip/D-range report (`exp movie clip`: "show once 18x18, bv_std, sdr_record, drange").

  These roles are inferred from strings.
- **Exif metering:** Exif MeteringMode sits at struct +2376 and CameraSettings 0x0202 at +2984. They are copied from the shot info (0x7E70D90D reads +2376). The writer was not traced.

### 1.5 Exif fields filled from the exposure mode (0x7E7096DC, verified)

- **Mode switch:** table 0x7E851948 (key = mode − 2). It sets ExposureProgram (+2400), CameraSettings ExposureMode (+2980) and SceneCaptureType (+2434):

  | Mode | ExposureProgram / ExposureMode | SceneCaptureType |
  |---|---|---|
  | P and iAuto | 2 / 2; ExposureMode 5 ("Program-shift") when the shift flag (+16582) ≠ 0 | – |
  | A | 3 / 3 | – |
  | S | 4 / 4 | – |
  | M | 1 / 1; ExposureBias is cleared | – |
  | mode 9 or 13 | – | 2 (portrait) |
  | mode 11 | – | 1 (landscape) |
  | mode 12 | – | 3 (night); SceneMode then comes from 0x7E66305E (SDET region) − 1 |

- **Defaults** for any other mode: ExposureProgram 5, ExposureMode 2, SceneCaptureType 0.
- **ConversionLens (0x0403, +2892):** "FCON", "MCON", "WCON" or "TCON" from byte +17146 = 1 / 3 / 2 / 4. These are the fisheye, macro, wide and tele converter lenses (names inferred).

### 1.6 EXP_MOVIE message codes (now named)

The `exp` shell `com N` command (jump table 0x7E7E0078, in 0x7E69C056) sends a fixed code to the EXP handler 0x7E68F0EA. It is the same handler that TAKE_EXPOSE calls at 0x7E585A9C, 0x7E585BF9, 0x7E585C80 and 0x7E587999. The help text names every N, so each code below has a name (**verified**):

| Code | Name (help text 0x7E7DDA1B…) | Handler (via hash 0x7E7DA1C0) |
|---|---|---|
| 0x500 | EXP_COM_THROUGH_START | 0x7E68F1FE |
| 0x501 | EXP_COM_THROUGH_END | 0x7E68F296 |
| 0x502 | EXP_COM_THROUGH_ONCE | 0x7E68F178 group |
| 0x503 | EXP_COM_THROUGH_STILL_END | 0x7E68F24B |
| 0x505 | EXP_COM_THROUGH_UPDATE | 0x7E69B03A |
| 0x506 | EXP_COM_THROUGH_ONCE_AF | 0x7E68F17A → 0x7E6904C1 |
| 0x507 | EXP_COM_THROUGH_RESTART | 0x7E68F1FE |
| 0x50A / 0x50B | EXP_COM_THROUGH_ONCE_CONTINUE / _CONTINUE_AF | 0x7E68F178 / 0x7E68F17A |
| 0x700 / 0x701 / 0x702 | EXP_COM_THROUGH_LOCK_START / _LOCK_END / _LOCK_ONCE | 0x7E68F1FE / 0x7E68F296 / 0x7E68F178 |
| 0x801 | EXP_COM_LV_END | 0x7E68F178 |

- **Unnamed codes:** 0x504, 0x50D, 0x50E, 0x90A, 0x90B and 0x1402 have no help line; `com 10` is unused (verified).
- **Live-view mode argument** (verified, help text): 1 = NORMAL_LV, 2 = CLIP_LV, 4 = MULTI_LV, 8 = MOVIE_LV.

### 1.7 Open questions (exposure)

1. The exact segment-to-variable roles of the 9 program-line solvers, and the meaning of the literals 99 and 7 in the P record.
2. Where the ISO-Auto upper limit and default come from. The `exp_cal_still[mode]` dump names `iso_limiter` and `iso_standard`, but the prm tags were not traced.
3. The metering-mode switch, and how the Spot Hi/Sh offsets are applied.
4. The APEX → rational tables at 0x7E7E1xxx.

## 2. AF control

### 2.1 Overview

- **TAKE_FOCUS** (0x7E5881D9) builds an `fcs_packet` and hands AF to the FCS code (0x7E5E2000–0x7E612000). The FCS code runs contrast-detect AF:
  - **S-AF:** a full hill-climbing scan, a reverse, then a second fine scan with peak interpolation;
  - **C-AF and movie:** wobbling.
- **The lens is driven through `fcs_lens_mfts_*`**, which sends packets in the Micro Four Thirds lens protocol (section 02 lens task).
- These points are inferred from the strings listed below; the addresses are verified.

### 2.2 The 8 AF types (0x7E593187, verified order and values)

The result goes to byte +38 of the TAKE_FOCUS globals (pointer at 0x60515FA8). The first test that matches wins:

| Test | af_type | String |
|---|---|---|
| tracking flag (+28) = 1 | 6 | `af_type:tracking` |
| 0x7E5871C0() ≠ 0 | 1 | `clip` (magnified/clip view, inferred) |
| face module 0x7E6FB66A(1) count ≠ 0 | 8 | `t-face` |
| special AF frame (+54) ≠ 0 | 2 | `special` (magnified AF frame; fields enable/mag/x/y at 0x7E59356C) |
| face module 0x7E6FB2A7(1) count ≠ 0 | 3 | `face` |
| prm 0x84D1 (info 40) = 0 | 5 | `spot` |
| prm 0x84D1 = 2 | 4 | `multi` |
| otherwise | 7 | `group` |

- **Reading:** 0x84D1 is the AF target mode, so 0 = single target and 2 = all targets (inferred).
- **The fcs_packet** (dump 0x7E594A50, builder 0x7E592239) carries `mode_focus, mode_af_area, mode_af_frame, mode_af_target_size, mode_saf_mf, mode_relese_priority_saf/caf, mode_drive, mode_af_tracking, special_af_frame{,_mag,_x,_y}, clip_x/y` (verified strings).
- **The builder reads** prm 0x8551, 0x8DF1 (info 79), 0x8E01 (info 80), 0x8081, 0x8372 (digital tele-converter, info 33), 0x8C31, 0x8A21, 0x9981 and 0x8391 (verified).
- **Not mapped:** which of these is S-AF / C-AF / MF / S-AF+MF / C-AF+TR. The two prm tags next to the "Full Time AF End / Single IAF/FA End" hints (0x8DF1 and 0x8E01) are the likely mode_focus and saf_mf (inferred).

### 2.3 Contrast AF and lens drive

- **S-AF scan log** (0x7E5F14A1 / 0x7E5F1A61; verified strings, meaning inferred):
  - **Per step** the log records the lens position (LDP, in pulses), three focus values `AF[0..2]` (left / centre / right, each with a filter frequency in kHz), AE, and the HANTEI (Japanese for "judgement") flags.
  - **Scan shape:** a first scan, then a "Peak1st ⇒ Reverse_Step", then a second scan between `second_start` and `second_end` with `2nd_width`. `Calculated_Peak_LD(offset)` is the interpolated peak.
  - **Units:** `ask_defocus_value(LSB=1/512mm)` and `AV_effect(LSB=1/256EV)`.
  - **Up to 5 scans** (`Scan_5_times`). Failures include `No_Peak`, `Not_Focused!!_(DON-Near/DON-Far)`, `AF_Value_is_too_small_!!_@FullScan` and `Step_Position_error`.
  - **Search modes:** `FCS FA FULL SCAN` (0x7E5EFD3C), `FCS FA STEP FASE` (0x7E5F063E), `4times scan` / `fa->scan_hantei[6..8]` (0x7E5EE9D6).
- **Scan speed** (0x7E60C37B, 1,412 bytes, double-precision maths):
  - It prints `Avofficial, F(*256), Kstep, Delta, Frate, KV(*256), SPD_MAX/MIN, Klimit, Kstep2, Delta2`.
  - The constants 6.0, 12.0, 0.8, 1.2, 2.0, 256 and 1000 are verified. A value is clamped to [1.2, 2.0] (verified).
  - **Reading (inferred):** the step per frame is about Kstep × F-number × δ (depth of focus), scaled by the frame rate.
  - So **the step size is computed from the aperture, not stored in a table.**
- **Lens commands** (verified function strings): `fcs_lens_mfts_scan_lens` 0x7E60D90F (variants `(2Ri)`, `(2Rr)`, `(2Rm)`), `scan_only_lens` 0x7E60DFF4, `scan_lens_wob` 0x7E60E308, `move_lens` 0x7E60E648, `move_lens_ofset(_vd)(_sim)` 0x7E60EAB7–0x7E60EF1E, `stop_lens(_wob/_force)` 0x7E60C919–0x7E60D5B9, `scan_chg_speed(_multi)` 0x7E60BC39 / 0x7E60B908, `chk_lens_stop(2)` 0x7E60F2DC / 0x7E60F7ED.
- **The lens packet** has fields `.prm.lv.{mode, fcs_act_mode, apert_act_mode, exp_delay, ap_target, ap_speed, lens_set, wob_amp, wob_move, ofs_time, ofs_move, iaf_target, iaf_flg, iaf_speed, iaf_dist, mf_flg}` and `.state.laf_dis_m[0..7]`.
- **C-AF:** initial position by F-number (`C-AF inipos fno` 0x7E607180), wobbling logs (`Wob Log 1/2`, `WOB_NGmax!`). There is a separate movie AF task, FCS_MOVIE 0x7E610A65.

### 2.4 Face and eye priority, AF area, illuminator

- **Face and eye priority:**
  - Face priority comes from the face-module counts (0x7E6FB66A, 0x7E6FB2A7) that select af_type 8 or 3 (verified).
  - The eye-AF dump at 0x7E5E7935 prints `is_eye_af, f_size, main_eye, r_size/r_cx/r_cy, l_size/l_cx/l_cy` (verified strings). So the AF target can be the left or right eye.
  - The rule for choosing the eye was not traced.
- **AF areas:**
  - The spot dump 0x7E5E6063 prints `area_no`, the spot, still and AF centres, `bayer_af_w/h`, and `single_area[i].hs/vs/hw/vw` (verified).
  - **Not verified:** a 35-point (7×5) layout. No 35-entry area table was found. The MakerNote AFAreas field is u32 × 64.
- **AF illuminator:**
  - It is driven by the strobe assist task: STB_ASSIST_FUNC 0x7E5E1E94 → `stb_illuminator` 0x7E5E0FA4 → 0x7E5E1106 (abort / err / flush) (verified).
  - The `stb` debug shell has "Drive AF Illuminator --> ill" (0x7E5DB40E).
  - The AF code's request path to it was not traced.

### 2.5 Open questions (AF)

1. The AF-mode prm values for S-AF / C-AF / MF / S-AF+MF / C-AF+TR.
2. The AF area grid and its point count.
3. How `Kstep` and `Delta` combine into the scan pulse rate.
4. What 2Ri / 2Rr / 2Rm stand for.

## 3. Files written

### 3.1 Overview

- **One assembler for all three file types.** Every Exif-type header is built by **0x7E7085D2** from one Exif data struct of about 17 KB. Callers:
  - REC_IMAGE 0x7E7130F7;
  - the ORF header builder 0x7E71969F (`REC ORF header`);
  - playback save 0x7E9413EE.
- **The struct is filled by:**
  - 0x7E708F24: the version strings and ASCII fields;
  - **0x7E7096DC** (6,319 bytes): most of the MakerNote values (with prm reads through 0x7E457C75);
  - `rec_art_set_exif_data` 0x7E70DC24 (section 09): ArtFilter.
- **How an IFD is written:** each one comes from a pointer list of 12-byte tag templates `{u16 tag, u16 type, u32 byte_length, u32 struct_offset}`. The templates are at 0x7E84EF20–0x7E850438 and the lists at 0x7E850434–0x7E851510. The generic writer 0x7E708AAB copies from struct+offset. Tags 256–37500 that hold offsets get special cases (verified).

### 3.2 File types (u16 at struct+16384, verified)

| Type | Header | IFDs written (list address, tag count) | Reading |
|---|---|---|---|
| 0 | `II` 0x002A, IFD0 at offset 8 | IFD0 0x7E850434 (17) or 0x7E8503FC (14); Exif 0x7E850500 (35) or 0x7E850478 (34); IFD1 0x7E85058C (6); Interop 0x7E8505A4 (2); MakerNote main 0x7E8505E0 (7); Equipment 0x7E8505FC (25); CameraSettings 0x7E850660 (64); RawDevelopment 0x7E850760 (14); ImageProcessing 0x7E850798 (93); FocusInfo 0x7E85090C (85) | JPEG APP1 |
| 1 | `II` 0x002A | IFD0 0x7E850ABC or 0x7E850A60 (25/23, with ImageWidth and Strip tags); Exif 0x7E850B98 or 0x7E850B20 (31/30); Main 0x7E850C1C (8, includes 0x0100 ThumbnailImage); then 25 / 62 / 14 / 89 / FocusInfo 0x7E850F34 (71) | TIFF (inferred: the strip tags plus "TIF" in the extension table) |
| 2 | **`IIRO`** (0x4949, 0x4F52) | IFD0 0x7E851050 (23); Exif 0x7E8510AC (31, adds 0xA302 CFAPattern); Main 0x7E851130 (8); Equipment 0x7E851150 (25); CameraSettings 0x7E8511B4 (63); RawDevelopment 0x7E8512B0 (14); ImageProcessing 0x7E8512E8 (138); FocusInfo 0x7E851510 (85) | **ORF** |

- **Type 0 and 1 variants:** the first list of each pair is used when struct+16478 = 1. For type 0 the 17-tag IFD0 adds WhitePoint, PrimaryChromaticities and YCbCrCoefficients. The filler then writes 0.313/0.329, the primaries 0.64/0.33, 0.21/0.71, 0.15/0.06, Gamma 2.2 (0xA500) and InteropIndex `R03` instead of `R98` (verified). This is the **Adobe RGB** marking (the primaries are Adobe RGB 1998; external).
- **Fixed strings:** ExifVersion `0230`, FlashpixVersion `0100`, ImageDescription `OLYMPUS DIGITAL CAMERA`, Software template `Version x.x`, and PrintIM `0300` (0x7E70948C) (verified).
- **MakerNote header:** `OLYMPUS\0` `II` 0x0003, written at 0x7E708A45 (verified). This is the "new" Olympus format with sub-IFDs (external).
- **Sub-IFD offsets** are constants, stored into the 0x2010–0x2050 values. ORF: 114 / 420 / 1182 / 1356 / 3018. JPEG: 102 / 408 / 1182 / 1356 / 2478 (verified).

### 3.3 MakerNote IFDs and tags (ORF lists; struct offsets in the script output)

- **Main (8):** 0x0100 ThumbnailImage, 0x0200 SpecialMode, 0x0209 CameraID, 0x2010 Equipment, 0x2020 CameraSettings, 0x2030 RawDevelopment, 0x2040 ImageProcessing, 0x2050 FocusInfo.
  - **No 0x0000 MakerNoteVersion** is in any main list (verified).
  - 0x2031 RawDevelopment2 and 0x3000 RawInfo are not written.
- **Equipment (25):** all 25 tags have ExifTool names (EquipmentVersion … LensType, LensModel, LensFirmwareVersion, Max/MinFocalLength, Extender*, ConversionLens, Flash*).
- **CameraSettings (63):**
  - **Named by ExifTool:** ExposureMode 0x0200 (+2980), AELock, MeteringMode 0x0202 (+2984), ExposureShift, FocusMode 0x0301 (+3000), FocusProcess, AFSearch, AFAreas (u32 × 64), AFPointSelected, AFFineTune(Adj), Flash*, WhiteBalance2/Temperature/Bracket, ColorSpace 0x0507, SceneMode 0x0509 (+3434), NoiseReduction, DistortionCorrection, ShadingCompensation, Gradation, PictureMode 0x0520 (+3564) and its Saturation/Hue/Contrast/Sharpness/BWFilter/Tone, NoiseFilter, **ArtFilter 0x0529 (+3470)**, PictureModeEffect, ToneLevel, ArtFilterEffect, DriveMode, PanoramaMode, ImageStabilization, ManometerPressure/Reading, ExtendedWBDetect.
  - **Not in ExifTool's table:** 0x0402, 0x0508, 0x050E, 0x0528, 0x052A, 0x052B (u16 × 30), 0x0530 (u16 × 96), 0x0605, 0x0800, 0x0802.
- **RawDevelopment (14):** 0x0000–0x010C; all are named (RawDevExposureBiasValue … RawDevSettings).
- **ImageProcessing (138):**
  - **Named by ExifTool:** WB_RBLevels and the 3000K–7500K and CWB1–4 sets, ColorMatrix (u16 × 9), BlackLevel2, GainBase, ValidBits, CropLeft/Top/Width/Height, UnknownBlock1–4, SensorCalibration, NoiseReduction2, DistortionCorrection2, ShadingCompensation2, MultipleExposureMode, AspectRatio, AspectFrame, FacesDetected, FaceDetectArea, MaxFaces, FaceDetectFrameSize/Crop, CameraTemperature.
  - **95 tags have no ExifTool name**, including 0x0101, 0x0120–0x0126, 0x0350, 0x0617–0x0638, **0x0640–0x0654**, 0x0800–0x0804, 0x1003/0x1004, 0x1105–0x1124, 0x1204–0x120B, 0x1300–0x1308, 0x1401–0x1409 and 0x1500–0x150B.
  - **0x0640–0x0653 are now identified as the CIC codec parameters** (§3.4).
- **FocusInfo (85):**
  - **Named by ExifTool:** FocusInfoVersion, AutoFocus 0x0209, SceneDetect, SceneArea, SceneDetectData (u32 × 800), ZoomStepCount, FocusStepCount, FocusStepInfinity/Near, FocusDistance, AFPoint, AFPointDetails, AFInfo (512 bytes), ExternalFlash*, InternalFlash, ManualFlash, MacroLED, SensorTemperature, ImageStabilization (128 bytes).
  - **63 tags have no name.** The 0x0200–0x021B, 0x0302–0x032E and 0x1200–0x1207 groups are probably AF and flash internals (inferred).
- The full tag-by-tag dump with types, byte lengths and struct offsets is produced by `ifdnames.py` (verified). ExifTool names are external corroboration only.

### 3.4 ORF container and the CIC codec

- **ORF IFD0 values** (0x7E71969F, verified constants):
  - ImageWidth 4640, ImageLength 3472, BitsPerSample 16, **Compression 1**, PhotometricInterpretation 1, SamplesPerPixel 1, PlanarConfiguration 1.
  - StripOffsets is computed: a size read from prm 0xCF94[55], plus a 512-aligned length from 0x7E55871C(), plus 101,376.
  - CFAPattern `02 00 02 00 | 00 01 01 02` = 2×2, **R G / G B**.
  - ImageProcessing ValidBits = 12.
  - So the sensor data is 12-bit in 16-bit containers. Compression = 1 even though the data is coded; dcraw and ExifTool know this ORF quirk (external).
- **CIC decoder** `play_cic_decode_raw` 0x7E93D10F (verified). It fills a `CicCtrl` block and runs it through 0x7E93F8E3 (dump) and 0x7E8F5880, which uses `CIC_MUTEX`.
  - **Fields filled:** ulCompAddr / ulRawAddr (the buffers); pulByteCounts = struct+664 (**StripByteCounts**); usAreaHw / usAreaVw = **4640 / 3472**; usRestartV = struct+660 (**RowsPerStrip**); ucBit = an argument; ucMode = 1.
  - **Then 14 parameters** are copied from struct+4378…+4404, which are **ImageProcessing tags 0x0640–0x0653** in order: SepBitNum, ThPred, ImaginVal, Equation, RestCut, ThDiff, ThRunSm, KparaSm, ThKparaSm, KparaRo, ThKparaRo, KparaMax, MaxPrefix, RstLength (field names from the dump strings).
  - **Reading (inferred):** CIC is a hardware RAW codec. It has interrupt statistics (" CIC %-4d" 0x7E449905) and a mutex. It does predictive coding with adaptive Golomb-style k parameters for smooth and rough areas, and a restart interval every `RowsPerStrip` lines. That matches the public description of Olympus compressed ORF (external).
  - **The encode side** in REC was not found by name. It is probably the same hardware block, driven from the REC_IMAGE pipeline (inferred).
- **Sensor capture packing:** the cam debug at 0x7E62F370 offers "12 = 12bit" and "pack up / pack down" (verified strings). This is the in-memory format, not the file format.

### 3.5 DCF names

- **Name builder 0x7E5B1EFB** (verified). It builds the 8-character name (FAT 8.3, no dot) from `'P'`, the month = (DOS date >> 21) & 15 written as `1`–`9`, `A`–`C`, the day = (date >> 16) & 31 as two digits, and the 4-digit file number. The 4-byte extension is then copied, skipping spaces, from a per-type RAM record (stride 136 at 0x6053E85C+8). Called from 0x7E5B1633 ← 0x7E5B0ADD.
- **Example:** 8 Nov, file 0001 → `PB080001.JPG` (inferred from the rule).
- **REC MEDIA entry 0x7E714203** (verified):
  - when job field +68 = 1, it **overwrites the first character with `_`**;
  - it takes the extension from the table at 0x7E853C14, indexed by file type: 0 `ORF`, 1 `JPG`, 2 `TIF`, 3 `ORF`, 4 `RAW`, 5 `WAV`, 6 `TXT`, 7 `MPO`;
  - types 0 and 7 set flag bits 2 and 16.
  - **Inferred:** +68 = Adobe RGB, following the DCF rule that names Adobe RGB files with `_`. Playback save (0x7E9436E8, 0x7E9439F7) also writes `_`.
- **No "PA" prefix was found.** No 'P' followed by an 'A' store exists in the name code, and the only first-character overrides are `P` and `_` (verified for the store patterns searched). Defaults are folder `100OLYMP` / `xxxOLYMP` and `P1010001JPG` (section 02).
- **Movies only in brief** (section 04):
  - the extension table has no MOV/AVI, so movie names are built in the movie module (not traced);
  - AVCHD uses `%05d.MTS` (0x7E5C1164);
  - the MOV/AVI containers are covered in section 04.

### 3.6 Open questions (files)

1. Who sets struct+16384 = 1 (TIFF?), and whether that path can be reached on the E-PM2.
2. The values of the unnamed ImageProcessing and FocusInfo tags. Field order now gives a way in, for example 0x1105 = bytes 96, 0, 82, 64, 28, … (from 0x7E71969F).
3. The CIC encoder and the actual parameter values written to 0x0640–0x0653.
4. What file types 0 and 4 (`ORF` with flag 2, `RAW`) are used for.
5. A cross-body check: whether the E-PL5 and E-P5 builds use the same template tables and the same CIC parameter tags.

# Code dig: what the E-PM2 colour model is missing (2026-11-12)

Static reading of E-PM2 v1.6 block 0 (runtime base 0x7E421020), `tools/fwmap.py fn <addr> --dis`.
Nothing was built or flashed. **[V]** = read in code or bytes. **[I]** = inferred.

## Summary

1. **Cross Process's hue record is rewritten per picture from scene statistics. [V]** After loading
   the ROM records, the Cross Process branch of 0x7E56D1C3 computes six colour statistics from a
   small raw buffer (P+16), and adds up to **+16 units to hue slots 2 (B) and 4 (C)** when blue or
   cyan dominates the frame. The Portra slot inherits this: blue-heavy and cyan-heavy scenes get
   an extra blue→cyan / cyan→green turn that no table we wrote controls. This is the main thing
   the model lacks for the Cross Process I slot.
2. **The six-axis values go to the image processor unconverted. [V]** No trig, no matrices, no
   scaling on the CPU: 12 halfwords are packed into 6 words of the engine block. The maths is in
   hardware, so its form can only be measured.
3. **The record slot order R, G, B, Y, C, M is confirmed by code. [V]** The statistics function
   fills its six bins in exactly that order, and the adaptive code indexes the hue record with the
   same indices.
4. **There is a pre-gamma 3×3 colour-matrix stage, and Pop Art has a private matrix in it. [V]**
   0x7E56C603 multiplies the per-shot matrix (P+24) by an 18-byte ROM matrix only for art codes
   70 / 79 (0x7E768F46) and 102 / 103 (0x7E768F58). Two one-byte immediates decide which codes get
   it. Re-keying them to 85 / 87 would give the Cross Process I slot a free 3×3 matrix (what GRKit
   calls the look matrix). This is a code change (2 bytes), not a data edit.
5. **No other unmodelled colour stage differs between Natural, Vivid, Muted, Portrait and Cross
   Process I. [V for the list, I for the roles]** The remaining setters are ISO-indexed (noise,
   sharpening, chroma suppression) or belong to other art filters.

## 1. Six-axis records: from ROM to the engine

- 0x7E56D1C3(a0 = out, a1 = job, d0 = mask, d1 = cache) picks two 12-byte records (a3 = saturation
  six, a2 = hue six) and at **0x7E56D8D8** packs them: word k = sat[2k] | sat[2k+1] << 16 for k = 0..2,
  then the same for hue: 6 words. **[V]**
- Callers: setter 0x7E56B682 (mask 0x8, block A + 180) and 0x7E56B6A8 (mask 0x10000, block B + 108).
  When the mask bit is clear, 0x7E56D1AD writes the off state. **[V]**
- Nothing else touches the values: no multiply, clamp or table between the ROM record and the block.
  **[V]** So units, axis geometry, linearity and luma coupling are properties of the image
  processor. **[I]**
- Record choice **[V]**: op class from 0x7E56A844(job+194); art code (P+79) 9–184 through jump table
  0x7E78C254; otherwise picture mode from 0x7E56A8B7 (P+83: 1 Vivid, 3 Muted, 4 Portrait; 2 and
  others = default). Variants: mask 0x10000 vs 0x8 (the two blocks) × P+82 ≠ 0. The "+3 in slot 1"
  is the P+82 = 0 variant. What P+82 holds is not traced.
- The cache check at 0x7E56D262 forces a rebuild for codes 85, 87, 167, 168 (Cross Process) and
  96, 97, 165, 166 (Dramatic Tone) on every job. **[V]** That is consistent with per-picture values.

## 2. The Cross Process branch (0x7E56D5CF–0x7E56D6F4)

**[V] unless marked.**
- Records: Cross Process I (85 / 87) saturation 0x7E7694FE, hue 0x7E76950A; Cross Process II
  (167 / 168) 0x7E769622 / 0x7E76962E.
- It builds a 40-byte argument block on the stack:
  - four plane pointers: P+16, then + 2·n, + 4·n, + 6·n, with n = halfword +10 of a 24-byte
    parameter record (0x7E56A7C4 picks the record by P+97, 0..8; default 0x7E78B0B4);
  - four values P+54, P+56, P+58, P+60 shifted right by record byte +20, multiplied by record
    halfword +4, shifted right by record byte +21 (black levels or thresholds, **[I]**);
  - record halfwords +12, +14, +6;
  - two WB-like gains from 0x7E56A874: (P+42 << 7) / min(P+44, P+46) and (P+48 << 7) / min(...),
    each doubled; and 2·min(P+44, P+46);
  - **the hue record pointer** (at +36 of the block).
- It calls 0x7E546219 or 0x7E54622B (chosen by 0x7E56A737(P+99): results 2–6 take the second).
  Both call **0x7E5460F0** with a statistics routine (0x7E545C4A or 0x7E545E76).
- **Statistics, 0x7E545C4A:** walks the four Bayer planes of the buffer in steps of 4 samples; per
  site forms R, G (two greens averaged) and B after subtracting the thresholds and applying the
  gains; then by the ordering of R, G, B adds (max − mid) to the primary bin of the largest channel
  and (mid − min) to the secondary bin between the two largest. Output order: **[0] R, [1] G,
  [2] B, [3] Y, [4] C, [5] M.**
- **0x7E5460F0:**
  1. copies the six ROM hue values to the output;
  2. 0x7E546066 ranks the three largest bins (t0 ≥ t1 ≥ t2), only bins > 0;
  3. acts only if **t0 is B (2) or C (4)**. The comparison bin is t1, or t2 when t1 is a neighbour
     of the dominant colour (for B: C or M; for C: G or B); it must be > 0;
  4. k = min(256, (dom − other) / max(other >> 7, 1)) → **k / 16 = 0…16 units**;
  5. adds k/16 to the dominant colour's hue slot, and to the partner slot (C for B, B for C)
     k/16 × (1 − (dom − partner) / dom), not below 0;
  6. always returns 0, so the caller **always** replaces the ROM hue record by this output.
  Tables: 0x7E746AD2 (init −1 −1 −1), 0x7E746AD5 (neighbour pairs 4 5 / 1 2), 0x7E746AD9 (slot pairs
  2 4 / 4 2).
- Consequence **[I]**: with the measured sign (positive hue = toward the next axis at a lower CbCr
  angle, about −1.4° per unit for B at +20), a frame dominated by blue gets up to ~20–25° of
  blue→cyan, and the cyan axis moves as well. A chart with all hues is unlikely to trigger much;
  a sky or sea picture will. The saturation record is not changed.
- The buffer at P+16 is the extra buffer art_stl2ycc_pass3 (0x7E72C018) attaches for codes 85 / 167
  (NOTES §12.3). **[V]**
- How to switch it off:
  - by data **[I]**: make the statistics all zero (then no bin is ranked and nothing is added), for
    example through the thresholds or gains of the P+97 parameter records 0x7E78B0B4… (shared with
    0x7E56AA10 / 0x7E56AEAF, so side effects must be checked first);
  - by code: one branch in 0x7E5460F0 (e.g. make the `cmp 2,d0` / `cmp 4,d0` test at 0x7E546160
    always fall through to the exit), a 1–2 byte edit on the capture path.

## 3. All block setters

Builders 0x7E56224C (block A) and 0x7E562404 (block B) call the same family. **[V]** for mask,
offset, callees and what the code compares; roles are **[I]** unless noted.

| Mask A / B | Setter A / B | Worker | Depends on | Role | In our model? |
|---|---|---|---|---|---|
| — | 0x7E562830 | settings getter 0x7E457C75 | a prm value | set-up | n/a |
| 0x8 | 0x7E56259B | table 0x7E78968C | job+84 | op dispatch | n/a |
| — | 0x7E56B64E / B668 | 0x7E56D039 | codes 91, 93 (Gentle Sepia), 0–8 | monochrome / sepia toning | no (not used by colour modes) |
| 0x4 / 0x8000 | 0x7E56B602 / B623 | 0x7E56CB32 | P+62 (ISO, **[I]**), sensor type P+99, codes 96, 97, 155, 163–170 | 12-byte records of ISO breakpoints (1280, 1536 … = 256 per stop): noise / edge parameters | no; not colour |
| — | 0x7E56B3EA / B3FD | 0x7E56BC86 | — | fixed words | n/a |
| — | 0x7E56B421 / B42E | 0x7E56BCB6 | P+96, clamps 33, 1023 | fixed/derived limits | n/a |
| 0x1 / 0x2000 | 0x7E56B446 / B4F5 | 0x7E56BDE9 (+ 0x7E56BED7 in A) | P+96; A also P+81 and codes 84, 119, 123, 124 | 7-point curves (x 59…821, y 143…530, slopes): a knee / compression stage ahead of the gamma (0x7E768E94… two sets by P+96) | implicitly (it is inside the measured Natural response); same for all colour modes |
| — | 0x7E56B55F / B56C | 0x7E56C246 | — | fixed | n/a |
| **0x2 / 0x4000** | 0x7E56B594 / B5BB | **0x7E56C603** | P+24 matrix, P+84 (B&W filter, 4 matrices 0x7E768EFE…), **codes 70, 79, 102, 103**, job+84 bits 0x20000 / 0x40000, op class | **3×3 colour matrix before the gamma** (§4) | yes for normal modes (EXIF ColorMatrix); **Pop Art's extra matrix is not** |
| 0x8 / 0x10000 | 0x7E56B682 / B6A8 | 0x7E56D1C3 | art code, picture mode, P+82; Cross Process: scene statistics | six-axis saturation / hue | partly (measured model; adaptive part missing) |
| 0x10 / 0x20000 | 0x7E56B6D1 / B6FE | 0x7E56DA08 | P+90, P+99, codes 169, 170 | RGB gamma for rec-view / Key Line | no; not the still JPEG path for our modes |
| 0x20 / 0x40000 | 0x7E56B896 / B8BB | 0x7E56DD9E → 0x7E56DC71 | art code, picture mode offset + Saturation; P+80 | Cb / Cr gain pair | yes |
| 0x40 / 0x80000 | 0x7E56B8E7 / B909 | 0x7E56DFCC | — (19 lines, no tables) | fixed block | n/a |
| 0x80 / — | 0x7E56B92A | 0x7E56E661 → 0x7E56E495 (hash 0x7E78C6E4, keys: scene codes, 91, 93, 96, 97, 165–168, 181–184) | art / scene code, P+82, P+84, P+96 | per-code value pairs; includes **Cross Process II (167 / 168) but not I** | no; does not apply to 85 |
| 0x100 / 0x100000 | 0x7E56B949 / B97D | 0x7E56EB95 → 0x7E56E837 | art code, mode, Contrast, Gradation | luma look curve (+ H&S spline 0x7E558466) | yes |
| 0x200 / 0x200000 | 0x7E56B9B6 / B9E9 | 0x7E56F63C → 0x7E56F113 | P+60 / P+62 (ISO), sensor type, P+87, P+90, P+97, codes 74, 96, 97, 165, 166 and hash 0x7E78CDA8 (84, 119, 123, 124, 163–184) | 24-byte records = 6 ISO breakpoints + 6 + 6 bytes, plus a pair (144, 384) by default and (0, 1023), (0, 256), (0, 285), (0, 64) for some codes: **luminance-dependent chroma gain / suppression** | **no**. Same tables for all colour modes and for code 85; changes with ISO |
| 0x400 / 0x400000 | 0x7E56BA1D / BA49 | 0x7E56FA27 | ISO, sensor type, P+82, P+97, codes 91, 93, 96, 97, 119, 123, 165, 166 | 12 ISO breakpoints, 3- and 6-value records: sharpening / edge | no; not colour |
| — / 0x800000 | 0x7E5654BC | 0x7E56A0D7 | codes 96, 97, 117, 121, 165, 166 | art effects | n/a |
| — / 0x1000000 | 0x7E56BA7A | 0x7E56FFCF | code 93, P+88 | art effects | n/a |

Not in these builders: **base gamma**. 0x7E56B790 is called from 0x7E56AEAF (484 lines; also calls
0x7E56A914, 0x7E545A70 and the float helpers 0x7E576191 / 0x7E576245) and from 0x7E570224. So the
per-channel gamma tables are post-processed with floating-point maths before use (fields P+79, P+87,
P+90, P+99; compares 104, 105, 128). **[V]** for the calls; what it does to the curve is not read.
The measured base response already includes it for ISO 200 stills.

## 4. The colour-matrix stage (0x7E56C603)

**[V]**
- Start matrix: the job's own matrix at P+24 for op classes 0 and 1 (stills and their previews);
  identity (128 = 1.0) otherwise.
- Then optional right-multiplications (0x7E56C263):
  - B&W filter matrix chosen by P+84 = 1…4 (0x7E768EFE, F10, F22, F34) when job+192 is 1 or 2
    (monochrome paths);
  - **art code 70 or 79 → 0x7E768F46; 102 or 103 → 0x7E768F58** (both hold 273 −14 −3 / −7 266 −3 /
    −7 −14 277, rows sum to 256): Pop Art's mild saturation matrix;
  - job+84 bit 0x20000 → 0x7E768F6A (311 −59 3 / −12 265 3 / −8 −7 271); bit 0x40000 → 0x7E768F7C
    (identity). Which features set these bits is not traced.
- 0x7E56C4C2 renormalises each row to sum 128 (7-bit coefficients, even values in two columns)
  and the nine halfwords are written to the block (mask 0x2 at A + 56, 0x4000 at B + 32).
- The compares are at 0x7E56C6A5 (`a0 46` = cmp 70), 0x7E56C6A9 (`a0 4f` = cmp 79), 0x7E56C6AD
  (`a0 66` = cmp 102), 0x7E56C6B1 (`a0 67` = cmp 103).
- **[I]** Changing 70 → 85 and 79 → 87 hands table 0x7E768F46 to Cross Process I (stills and
  movie); Pop Art I then renders without its matrix, Pop Art II keeps its own. The table is 9
  signed 16-bit values with rows summing to 256, in the same linear, pre-gamma position as GRKit's
  look matrix. Resolution after renormalisation is 1/128.

## 5. Hypotheses for the missing ~2 ΔE, ranked

1. **Scene-adaptive hue in the Cross Process slot (§2).** Explains why the xp3 chart pair is
   predicted worse (2.2) than the normal-mode probes (1.2–1.4), and why greens / blues carry the
   residual. Tables / code: 0x7E5460F0, statistics 0x7E545C4A, parameter records 0x7E78B0B4….
   Cheapest test, offline: reimplement the statistics on the ORFs already in `shots/` (PB090221,
   PB110237, PB110252) from the half-size Bayer planes and compute the added units; if they are
   non-zero, refit the six-axis model with hue slots B and C shifted by them and see whether the
   xp3 residual drops. On camera: RAW Data Edit a blue-sky ORF and a chart ORF in Portra 400 and
   compare the blue axis (no flash needed).
2. **The six-axis hardware is not linear in its values at the sizes used** (xp3 has four values at
   ±40 / ±20; the probe measured each axis at one value). No code to read (§1). Test: one probe
   flash with a single mode stepping one axis (e.g. Vivid R hue +10, Muted R hue +20, Portrait R
   hue −20, and the same for one saturation slot), RAW Data Edit of PB090221.
3. **Luminance-dependent chroma stage (mask 0x200, 0x7E56F63C / 0x7E56F113).** Not in the model;
   identical for all colour modes at a given ISO, so it cannot explain mode-to-mode error, but it
   makes chroma depend on brightness and so limits any model that scales chroma uniformly (shows
   as the 1–2 ΔE floor on saturated dark and bright patches). Test offline: on shoot 1 Natural,
   regress (camera chroma / model chroma) against output luma; a consistent curve confirms it and
   can be added to `fit_look.py`.
4. **Muted's poor fit**: Muted has no private stage in any setter (same matrix, gamma, chroma
   tables as Natural); it differs only in look-curve offset (−1) and its records. Its probe deltas
   were the largest and mixed five axes, so hypothesis 2 is the likely cause. **[I]**

## 6. Levers this opens (not done)

| Lever | Kind | What it gives |
|---|---|---|
| Re-key Pop Art I's matrix to codes 85 / 87 (0x7E56C6A5 / A9) and write 0x7E768F46 | 2 code bytes + 18 data bytes | a real 3×3 pre-gamma colour matrix for the Portra slot (hue rotations without the six-axis stage's limits) |
| Disable the adaptive hue (0x7E5460F0) | 1–2 code bytes, or parameter data | Portra renders the same hue for every scene |
| Keep it, and model it | none | accept a scene-dependent sky rendering |

Open: what P+82, P+97 and job+84 bits 0x20000 / 0x40000 are; what 0x7E56AEAF does to the base
gamma; whether the statistics routine 0x7E545E76 (other sensor types) differs in more than layout.

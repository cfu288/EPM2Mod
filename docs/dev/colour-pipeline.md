# The colour pipeline of a still picture

How the E-PM2's image processor (TruePic VI) turns raw sensor data into a JPEG, stage by stage, and what a film
simulation writes into each stage. Labels: **[C]** confirmed on the camera; **[R]** read from the firmware's code or
tables, not exercised on the camera; **[I]** inferred. Notes of earlier experiments can be wrong: a claim without
[C] is checked before a design rests on it.

## 1. The stages

Order **[C]** for stages 1 to 6 (each was changed on its own and measured, `art-filter-slots.md` §2.2; the look
stage again on 2026-11-20, `../../experiments/2026-11-20-film-camera-round/NOTES.md`).

| # | Stage | Data it uses | What it does to a pixel | What a film writes there |
|---|---|---|---|---|
| 1 | White balance | 3 gains | multiplies raw R, G, B | nothing (the camera's WB setting) |
| 2 | Colour matrix × art matrix (0x7E56C603) | 3 × 3 matrix, s16, rows sum to 256 | mixes R, G, B: an overall colour shift and saturation | the film's art matrix; the EXIF ColorMatrix is the product |
| 3 | Six-axis (0x7E56D1C3) | 6 saturation + 6 hue values (s16) | per hue direction (red, yellow, green, cyan, blue, magenta, 60° apart) a saturation and hue change; between two axes a blend | the film's 12 values |
| 4 | Tone curves (0x7E56B790) | per channel a table of 256 × u16 (8 tables per record) | brightness and contrast per channel; colour casts that depend on brightness | the film's three curves |
| 5 | Look curve on luma (0x7E56E837) | 256 × u16 | one more brightness curve on luma | the identity table 0x7E75B8F0 |
| 6 | Saturation gain (0x7E56DC71), chroma curves (0x7E5662D9) | a gain pair; two curves of points and slopes on Cb and Cr | how strongly colour shows, as a function of its strength | the film's gain and two curves (where the chroma curves sit among stages 5 and 6 is [I]) |
| 7 | 12-region hue, saturation and lightness (builder 0x7E56E186) | a table of 3028 bytes (§2) | selective changes to colours that fall in up to 12 regions | **nothing yet**: every film code gets Natural's table A **[R]** |
| 8 | JPEG | camera settings | sharpening, noise reduction, 8-bit Y/Cb/Cr | nothing |

Live view and standard movie use a second path (pipe B) without stage 7 **[R]** (code and emulator,
`../../experiments/2026-11-11-caduceus-review/05-imaging-pipeline-and-limits.md` §2 L3). RAW Data Edit uses
pipe A **[I]** (an older note). There is no 3-D lookup table anywhere in the colour uploads **[R]** (L1).

## 2. The 12-region stage

**What it is.** A list of up to 12 selective colour adjustments, of the kind an HSL or selective-colour panel makes
in an editor: "for the pixels whose colour falls in this region, shift the hue by X, change the saturation by Y and
the lightness by Z". The processor applies it in hardware; the CPU only uploads the table **[R]**.

**Where the tables are and which one a picture gets [R].** Table A 0x7E76C3C8 (sRGB) and B 0x7E76CF9C (Adobe RGB).
A hash at 0x7E78C6E4 (64 slots, key = art code − 8, 43 used) gives an art code its own table; else the picture
mode picks a default (0x7E56E5DC). Natural, i-Enhance, Custom, Monotone, Vivid, Portrait and every film code get
table A; Gentle Sepia, Key Line, Cross Process II and Watercolor have their own; Dramatic Tone has none. The table
was read before the card path (2026-11-18) existed: which table the current film codes get is to be checked.

**Layout [R].** 12 records of 28 bytes, then 4 × 96 u32 and 6 × 96 u16 (weight curves: how strongly a record acts
across its window; all ISO weights are flat), then a 12-bit enable mask at +3024. A record:

| Bytes | Field | Meaning |
|---|---|---|
| 0–1, 2–3 | hue start, hue width | an arc of the colour wheel, 32768 = 360° |
| 4–5, 6–7 | chroma start, width | how saturated a pixel must be |
| 8–9, 10–11 | luma start, width | how bright a pixel must be, 0–1024 |
| 12–13 | hue shift | 32768 = 360° (1365 = 15°) [I] |
| 14–15 | saturation change | units [I] unknown |
| 16–17 | lightness change | units [I] unknown |
| 18–27 | multiplier and shift per window | width × multiplier >> shift = 256: the scale of each window's soft edge [I] |

**Per pixel [I].** In Y/Cb/Cr after the tone curves (its order against stage 5 is not established): hue = angle of
(Cb, Cr), chroma = its length, luma = Y. Each enabled record gives a weight from 0 to 1, the product of how far the
pixel lies inside its hue, chroma and luma windows (soft edges from the weight curves). The weighted hue shifts are
added, chroma is scaled by the weighted saturation changes, the weighted lightness changes are added; the result goes
back to Y/Cb/Cr.

**Natural's table A [R]** (mask 0x38F: records 0–3 and 7–9 on). Colour names assume hue = atan2(Cr, Cb) (record 2's
arc is centred on 289.5°; pure cyan is at 288.7°) [I]:

| Record | Hue arc | Colour | Chroma | Luma | Hue | Sat | Light |
|---|---|---|---|---|---|---|---|
| 0 | 133–193° | yellow, orange | 5–629 | 67–643 | +15° | +140 | +32 |
| 1 | 340–44° | blue-violet | 5–741 | all | +5° | −16 | 0 |
| 2 | 270–310° | cyan | 5–417 | 4–768 | −5° | +72 | −64 |
| 3 | 77–117° | red, darker | 5–693 | 4–456 | −5° | 0 | −10 |
| 7 | 281–307° | strong cyan, bright (sky) | 181–949 | 512–1024 | +9° | −128 | 0 |
| 8 | 151–195° | yellow, bright | 102–646 | 744–1020 | −8° | +80 | +64 |
| 9 | 147–216° | pale yellow-green | 5–101 | 83–1106 | +18° | −8 | 0 |

Every film currently carries these: warmer, stronger yellows; darker, stronger cyans; paler bright skies.

**Six-axis and 12-region compared**

| | Six-axis (stage 3) | 12-region (stage 7) |
|---|---|---|
| Space | before the tone curves | Y/Cb/Cr after them [I] |
| Regions | 6 fixed axes, 60° apart | 12, each with its own arc |
| Selects by | hue | hue, chroma and luma |
| Changes | hue, saturation | hue, saturation, lightness |
| Live view, movie | yes | no (pipe B) [R] |

A film's colour signature is often a selective change that six fixed axes cannot make: Velvia darkens blue skies,
Kodachrome darkens reds, portrait negatives soften orange skin and keep reds. The ColorChecker residual of the films
(1.4–2.5 ΔE) sits in those colours. Whether per-film 12-region tables reduce it is not measured; the camera test of
`../../experiments/2026-11-20-twelve-region/` establishes the stage on this camera first.

## 3. Limits that no table changes

- A floor of about 0.8 ΔE on natural colours: 8-bit JPEG and the camera's rounding **[C]**.
- Colours outside the gamut after the colour matrix (a negative channel) are darkened by the tone curves and capped
  in chroma: 11–17 ΔE for every film, stock Natural 14–22 **[C]**.
- Live view and movies get stages 1 to 6 only.

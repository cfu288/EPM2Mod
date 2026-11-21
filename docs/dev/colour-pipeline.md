# The colour pipeline of a still picture

How the E-PM2's image processor (TruePic VI) turns raw sensor data into a JPEG, stage by stage, and what a film
simulation writes into each stage. Labels: **[C]** confirmed on the camera; **[R]** read from the firmware's code or
tables, not exercised on the camera; **[I]** inferred. Notes of earlier experiments can be wrong: a claim without
[C] is checked before a design rests on it.

## 1. The stages

Order **[C]** for stages 1 to 6 (each was changed on its own and measured, `../../experiments/2026-11-09-film-portra/NOTES.md`
§27–30; the look stage again on 2026-11-20, `../../experiments/2026-11-20-film-camera-round/NOTES.md`).

| # | Stage | Data it uses | What it does to a pixel | What a film writes there |
|---|---|---|---|---|
| 1 | White balance | 3 gains | multiplies raw R, G, B | nothing (the camera's WB setting) |
| 2 | Colour matrix × art matrix (0x7E56C603) | 3 × 3 matrix, s16, rows sum to 256 | mixes R, G, B: an overall colour shift and saturation | the film's art matrix; the EXIF ColorMatrix is the product |
| 3 | Six-axis (0x7E56D1C3) | 6 saturation + 6 hue values (s16) | per hue direction (red, yellow, green, cyan, blue, magenta, 60° apart) a saturation and hue change; between two axes a blend | the film's 12 values |
| 4 | Tone curves (0x7E56B790) | per channel a table of 256 × u16 (8 tables per record) | brightness and contrast per channel; colour casts that depend on brightness | the film's three curves |
| 5 | Look curve on luma (0x7E56E837) | 256 × u16 | one more brightness curve on luma | the identity table 0x7E75B8F0 |
| 6 | Saturation gain (0x7E56DC71), chroma curves (0x7E5662D9) | a gain pair; two curves of points and slopes on Cb and Cr | how strongly colour shows, as a function of its strength | the film's gain and two curves (where the chroma curves sit among stages 5 and 6 is [I]) |
| 7 | 12-region hue, saturation and lightness (builder 0x7E56E186) | a table of 3028 bytes (§3) | selective changes to colours that fall in up to 12 regions | **no table**: every film code gets a table with every record off (`stock-films-structure-3`); Olympus's filters keep theirs **[C]** |
| 8 | JPEG | camera settings | sharpening, noise reduction, 8-bit Y/Cb/Cr | nothing |

Live view and standard movie use a second path (pipe B) without stage 7 **[R]** (code and emulator,
`../../experiments/2026-11-11-caduceus-review/05-imaging-pipeline-and-limits.md` §2 L3). RAW Data Edit uses
pipe A **[I]** (an older note). There is no 3-D lookup table anywhere in the colour uploads **[R]** (L1).

## 2. From a menu entry to the stages

**The art code [R].** A menu entry is only a stored Picture Mode value (100–120). `art_GetFilterType` (0x7E71BD94,
jump table 0x7E854A24) turns value and type (I, II, III) into one byte, the art code, stored in the job parameters at
+79. Each stage looks that byte up in its own way:

| Stage | Dispatch [R] |
|---|---|
| 2, art matrix | four compares in code (0x7E56C6A5): codes 70, 79 → 0x7E768F46; 102, 103 → 0x7E768F58; otherwise none |
| 3, six-axis | jump table 0x7E78C254, index code − 9 |
| 4, tone curves | hash 0x7E78C154 (32 entries, key = code − 70; key 0 means empty, so code 70 cannot have an entry; codes 71–170 only) → a handler that loads a record of 8 tables per channel. Only two stock handlers give R, G and B different tables (0x7E56B7F8, 0x7E56B82A) |
| 5, look curve | jump table 0x7E78C8E4, index code − 8 |
| 6, saturation; chroma curves | jump tables 0x7E78C514 and 0x7E78AEA4, index code − 69 |
| 7, 12-region | hash 0x7E78C6E4 (key code − 8), else a default by picture mode |

Other code also switches on the art code: the effect filters' pixel program after development (ART task 0x7E729E25),
Cross Process's scene-adaptive hue routine (0x7E5460F0), Pale&Light's white-balance change.

**How a film gets there today [R; camera-tested as a whole 2026-11-18, 2026-11-20 and 2026-11-21].** `stock-films-structure-3`
(`gen/stock-films/structure.py`) gives each ART entry one film code; the loader (`card-looks-8`) switches the
entry's routing words when a film file lists it and writes the film's tables into the entry's RAM block
(0x7E4D1000 + 0x3200 × entry: tone tables for stills and live view, saturation, six-axis, chroma, matrix). An entry
the file leaves out gets its stock words back.

| Entry | Stored value | Film code | Kind |
|---|---|---|---|
| Pop Art | 100 | 79 | in place (the stock code's words are switched) |
| Soft Focus | 101 | 75 | routed (the value's routing words point at a film code) |
| Pale&Light Color | 102 | 71 | in place |
| Light Tone | 103 | 72 | in place |
| Grainy Film | 104 → 111 | 94 | hidden value |
| Pin Hole | 105 | 92 | routed |
| Diorama | 106 | 125 | routed |
| Cross Process | 107 | 85 | in place |
| Gentle Sepia | 108 → 112 | 98 | hidden value |
| Dramatic Tone | 109 → 114 | 144 | hidden value |
| Key Line | 119 → 115 | 156 | hidden value |
| Watercolor | 120 → 118 | 159 | hidden value |

Each film code gets a tone stub with its own three records (so R, G and B differ), saturation, six-axis and chroma
stubs that point at the RAM block, a matrix chain, and the identity look through the stub `LKID` (until
`films-look-exif`, 2026-11-20, the look entry pointed at Cross Process I's handler and table: every film got its
S-curve), and a 12-region table with every record off (§3; until `films-twelve-off`, 2026-11-21, Natural's table
A). Design and evidence: `../../experiments/2026-11-18-stock-filters/design.md` (its RAM address
0x7E4D8000 / 0x2000 is out of date; the generator has 0x7E4D1000 / 0x3200).

**Facts a fit relies on [C].**

- The camera rounds the product of its colour matrix and the art matrix in a fixed way and writes the result to the
  EXIF ColorMatrix of each JPEG; the fit predicts it exactly, which checks that a build did what it should.
- The base tone table that the curves start from is not neutral: it compresses highlights. A film's curves allow for
  it.
- With the 5300 K preset and with Auto WB the camera uses the same colour matrix; the WB gains differ and are read
  from the EXIF (2026-11-20).

## 3. The 12-region stage

**What it is.** A list of up to 12 selective colour adjustments, of the kind an HSL or selective-colour panel makes
in an editor: "for the pixels whose colour falls in this region, shift the hue by X, change the saturation by Y and
the lightness by Z". The processor applies it in hardware; the CPU only uploads the table **[R]**.

**Where the tables are and which one a picture gets [R].** Table A 0x7E76C3C8 (sRGB) and B 0x7E76CF9C (Adobe RGB).
The selector 0x7E56E661 takes the art code (job+79), looks it up in the hash 0x7E78C6E4 (64 slots, key = art code − 8,
linear probing, key 0 = empty; 43 used), and without a hit takes a default by picture mode (0x7E56A8B7). Natural,
i-Enhance, Custom, Monotone, Vivid, Portrait get table A; Gentle Sepia, Key Line, Cross Process II and Watercolor have
their own; Dramatic Tone has another path. On `films-twelve-off` every film code gets OFFDESC, whose table has
enable mask 0, so no region acts (an in-place code only while its entry has a film; otherwise the stock filter keeps
its table); before it, every film code got table A (emulator and camera, 2026-11-20 and 2026-11-21). Table B serves the Adobe RGB colour space, which ART locks to sRGB (manual p. 66): films
never get it. A second builder (0x7E55E2CE) prebuilds a fixed list of tables at start; what uses its output is not
traced.

**Layout [R].** A descriptor `{table, 12 ISO-weight pointers}` (52 bytes; every ISO weight is flat 256, so the record
values reach the engine unchanged). The table (3028 bytes): 12 records of 28 bytes; then the curves, 7 per record of
16 points each (a point = level << 8 | signed slope), stored as two groups of five arrays (records 0–5 and 6–11);
then a 12-bit enable mask at +3024. The builder (0x7E56E186) writes per record six words to the engine and passes ten
curve pointers. A record:

| Bytes | Field | Meaning |
|---|---|---|
| 0–1, 2–3 | hue start, hue width | an arc of the colour wheel: hue = atan2(Cr, Cb), 32768 = 360° [C] |
| 4–5, 6–7 | chroma start, width | how saturated a pixel must be: about 6 units per 8-bit Cb/Cr radius [C, one hue off] |
| 8–9, 10–11 | luma start, width | how bright a pixel must be: 4.05 × 8-bit Y [C] |
| 12–13 | hue shift | 32768 = 360° within about 3° up to ±30° [C]; larger shifts fall short |
| 14–15 | saturation change | added to the chroma radius, about 0.24 codes per unit on the probe's tables [C] |
| 16–17 | lightness change | added to Y, about 0.24 codes per unit (L / 4) on the probe's tables [C] |
| 18–19, 26–27 | none | never read by the builder [R] |
| 20–25 | multiplier and shift of the hue, chroma and luma windows | width × multiplier >> shift = 256 in every stock record [R] |

Curve roles [I, from the stock tables]: c5 luma; c0 and c3 saturation along hue and along chroma; c2 lightness along
chroma; c4 hue shift along chroma; c1 and c6 lightness and hue shift along hue (which is which is unknown).

**Per pixel** (camera probe, `../../experiments/2026-11-20-twelve-region/NOTES.md` §8). In Y/Cb/Cr after the tone
curves and before the look curve [C] (before or after the saturation gain: not resolved): hue = angle of (Cb, Cr),
chroma = its length, luma = Y [C]. A pixel is inside a record's windows or not: the edges are hard [C]; inside, the
curves weight the effect [I]. The weighted changes of overlapping records add [C]; a record whose bit in the mask is
off has no effect [C]. Saturation adds to the chroma radius, lightness to Y [C on the probe's tables; real tables fit
smaller constants, an open point].

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

Until `films-twelve-off` every film carried these: warmer, stronger yellows; darker, stronger cyans; paler bright skies.
On the camera they cost the films 0.07–0.10 ΔE on natural colours
(`../../experiments/2026-11-20-model-calibration/NOTES.md` §6).

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
(1.3–2.5 ΔE) sits in those colours. Three fitted per-film tables, tried on the camera, gained about 0.1 on the
ColorChecker; the rules of this section explain a real table only in part (Natural's: 1.8 of a 2.7-code change left
over), so per-film tables wait for better rules (`../../experiments/2026-11-20-model-calibration/NOTES.md` §6).

## 4. Limits that no table changes

- A floor of about 0.8 ΔE on natural colours: 8-bit JPEG and the camera's rounding **[C]**.
- Colours outside the gamut after the colour matrix (a negative channel) are darkened by the tone curves and capped
  in chroma: 11–17 ΔE for every film, stock Natural 14–22 **[C]**.
- Live view and movies get stages 1 to 6 only.

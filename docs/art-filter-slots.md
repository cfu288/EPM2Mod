# Art filter slots: what each menu entry can do as a film-emulation slot

E-PM2 firmware 1.6, block 0, runtime base 0x7E421020. Written 2026-11-12 from the work in
`experiments/2026-11-09-film-portra/NOTES.md` §11–26 and `CODE_DIG.md`.

Labels: **[C]** confirmed on the camera; **[R]** read from the code or tables, not exercised on
the camera; **[I]** inferred.

## 1. Summary

- A menu entry is only a number (the *art code*). There is no per-entry record that holds a look.
- Six separate stages of the image pipeline each look that number up in their own way and pick
  their own tables (the sixth, chroma curves, was found on 2026-11-12). A film look needs all six
  under our control.
- The stock firmware has the parts for **two** full film slots: Portra 400 in Cross Process I **[C]**
  and Ektachrome 100 in Light Tone **[C]**.
- A third slot was added with 120 bytes of new code: Fuji Pro 400H in the top-level Pop Art entry.
  The code works **[C]**, and with Pop Art's chroma curves made linear the look is at the same
  level as the other two **[C]** (§4).
- Updated 2026-11-12 after NOTES §27–30. Whether the remaining filters can follow:
  [`art-slots-evaluation.md`](art-slots-evaluation.md) (the per-filter rows below predate it).

## 2. How a menu entry becomes a look

### 2.1 Menu entry → art code
`art_GetFilterType` (0x7E71BD94) switches on the stored picture mode (100–120, jump table
0x7E854A24) and the type (1, 2, 3) and returns one byte. It is stored in the job parameter block
at offset +79. **[R]**

The quick menu lists the twelve filters. A filter's type II (or III) is chosen in ART mode with
the right arrow on the filter (manual; not verified on this camera). **[I]**

### 2.2 The six stages and how each one dispatches

| Stage | Function | Dispatch | What a target is |
|---|---|---|---|
| (a) Base gamma, per channel | 0x7E56B790 | Open-addressed hash, 32 entries of {key = code − 70, handler address} at 0x7E78C154; key 0 = empty; only codes 71–170 are looked up | Code that loads record addresses. A record = 8 pointers to 256 × u16 tables; 0x7E56B732 picks one |
| (b) Look curve on luma | 0x7E56E837 | Jump table 0x7E78C8E4, index code − 8 | `mov <table>, a0; jmp` |
| (c) Saturation gain pair | 0x7E56DC71 | Jump table 0x7E78C514, index code − 69 | `mov <pair>, a3; jmp` |
| (d) Six-axis records (saturation ×6, hue ×6) | 0x7E56D1C3 | Jump table 0x7E78C254, index code − 9 | Code that copies two records of six s16 |
| (e) Art matrix (multiplies the ColorMatrix) | 0x7E56C603 | **Four compares in code** at 0x7E56C6A5: 70, 79 → table 0x7E768F46; 102, 103 → table 0x7E768F58 | 9 × s16, rows sum to 256 |
| (f) Chroma curves (found 2026-11-12, NOTES §30.2) | 0x7E5662D9 | Jump table 0x7E78AEA4, index code − 69 | Code that stores six table addresses (97 bytes of curve points and slopes per filter). Linear for Cross Process I and Light Tone; S-shaped for Pop Art I; compressing for Pale&Light I; a step for Pop Art II |

All **[R]**; (a), (b), (c), (d), (e) are each **[C]** for the two slots in use, and (f) is **[C]** as an effect
(measured in the Pop Art slot before and after replacing its tables, NOTES §30.2, §30.4) (the camera output
follows the tables we wrote, and the output EXIF ColorMatrix is the matrix we predicted).

Pipeline order **[C]**: raw → WB → ColorMatrix × art matrix → six-axis → base gamma per channel →
look curve on luma → saturation. Where (f) sits among the last two is not established **[I: on Cb / Cr,
near the saturation gain]**.

### 2.3 Why the entries are not interchangeable

1. **The dispatch tables are data; the handlers are code with fixed addresses in them.** A slot can
   be pointed at another handler, and then it shares that handler's tables. Two slots through one
   handler give one look.
2. **Only two gamma handlers assign three different records** (R, G, B): 0x7E56B7F8 (records
   0x7E78B41C / 3C / 5C) and 0x7E56B82A (0x7E78B49C / BC / DC). Every other handler sets R = G = B
   to one table. Film targets have non-neutral grays that change with brightness, which needs
   different curves per channel.
3. **The matrix has two tables and four compares.** A compare is `cmp imm8, d0` on a zero-extended
   byte with a sign-extended immediate, so only codes ≤ 127 can be written into it.
4. **Code 70 cannot enter the gamma hash**: its key is 0 (the empty marker) and the range check is
   code ≥ 71. Code 69 (Soft Focus) is below the range too.
5. **Other code switches on the same byte.** Effect filters run a pixel module after development
   (ART task 0x7E729E25). Cross Process (85, 167) runs a scene-adaptive hue routine (0x7E5460F0,
   switched off by `patches/xp-adaptive-hue-off.json`). Pale&Light changes the white balance.
6. **Stage (f) was missed until 2026-11-12** because its tables are straight lines for the first two
   slots used. Until then this document called Pop Art I and II "none found" under extra processing.
   Any other undiscovered per-code stage would show the same way: as a slot whose stock rendering
   the model cannot reproduce (Pop Art I stock was 2.0 ΔE from the model, the clean slots 0.9).

## 3. Capability map

Columns: **Top** = reachable from the quick menu. **RGB curves** = can get three independent
curves. **Matrix** = can get an art matrix. **Own (b)(c)(d)** = has its own look table, saturation
pair and six-axis handler in stock (so they can be overwritten in place). **(f) Chroma** = its stock
chroma-curve tables. **Extra processing** = anything outside the six stages.

| Menu entry (type) | Code | Top | (a) RGB curves | (e) Matrix | Own (b)(c)(d) | (f) Chroma curves (stock) | Extra processing | Film slot? |
|---|---|---|---|---|---|---|---|---|
| **Cross Process I** | 85 | yes | **native** three-record handler | via `matrix3` (was: re-keyed compare) | yes | linear | adaptive hue (disabled) | **In use: Portra 400 [C]** |
| **Light Tone** | 72 | yes | hash entry re-pointed to 0x7E56B82A | via `matrix3` | yes | linear | none: stock output matches the model to 0.94 ΔE **[C]** | **In use: Ektachrome 100 [C]** |
| **Pop Art I** | 70 | yes | new handler `gamma3` (new code) **[C]** | via `matrix3`, own table **[C]** | yes | **S-shaped: kills weak colour, boosts strong** **[C]**; replaced by the linear set in `three-films-2` **[C]** | none other found | **In use: Fuji Pro 400H [C]** |
| Pop Art II | 102 | no | now the default record (its own record is film 3's blue channel) | none now | yes | a hard step | none other found | Not top-level; needs (f) replaced |
| Pale&Light I | 71 | yes | now the default record (its own record is film 3's red channel) | via `matrix3` if added | yes | **compressing curve** (mild on natural colours) | **changes WB** (406/510 where other modes got 520/470) **[C]**; no spatial effect; otherwise the model reproduces it to 1.0 ΔE **[C]** (NOTES §31) | **Best candidate for a fourth film**: needs (f) replaced and the WB change found |
| Pale&Light II | 145 | no | by adding a hash entry | via `matrix3` if added | yes | own set (not read) | as type I **[I]** | Not top-level |
| Cross Process II | 167 | no | native three-record handler (shared with Light Tone) | via `matrix3` if added | look, saturation yes; six-axis shared with type I | own set (not read) | adaptive hue (disabled) | Curves donor for Light Tone |
| Soft Focus | 69 | yes | **no** (code < 70) | via `matrix3` if added | yes | own set (not read) | blur module (visible in the mock rendering) **[C]** | No |
| Pin Hole I / II / III | 73 / 106 / 108 | I only | by adding a hash entry | via `matrix3` if added | yes | linear (73) | vignette module, white −161 codes to the corner **[C]**; **also changes WB** (506/424) **[C]** | Only if the module can be disabled and the WB change found |
| Diorama | 86 | yes | by adding a hash entry | via `matrix3` if added | yes | linear | blur bands **[C]**; colour path otherwise clean (model 1.3 ΔE on the sharp patches) **[C]** | Second candidate, if the blur module can be skipped |
| Grainy Film I / II | 74 / 104 | I only | by adding a hash entry | via `matrix3` if added | look only | default | monochrome + grain texture (block 2) | No |
| Gentle Sepia | 91 | yes | by adding a hash entry | via `matrix3` if added | look only | own set (not read) | monochrome / sepia toning stage | No |
| Dramatic Tone I / II | 96 / 165 | I only | by adding a hash entry (I) | via `matrix3` if added | shares the "identity" look table 0x7E75B8F0; own six-axis handler | own handler (not read) | local-contrast module; ISO-table special cases (CODE_DIG §3) | No |
| Key Line I / II | 163 / 169 | I only | own flag-dependent default | via `matrix3` if added | none | default | edge module | No |
| Watercolor I / II | 181 / 182 | I only | **no** (code > 170) | via `matrix3` if added | yes | default (index > table) | module | No |

"By adding a hash entry": the hash has free entries, so a code in 71–170 can be given a handler.
It then shares one of the two three-record handlers' tables (see 2.3 point 1). **[R]**

With the new code of §5 the matrix is no longer a limit (`matrix3` can test any code and point at any
table). What limits the count now is gamma-table space, a clean host entry, and stage (f).

## 4. Current assignment (build `three-films-2`, on the camera since 2026-11-12)

| Resource | Used by |
|---|---|
| Three-record handler 0x7E56B7F8, 24 tables | Portra 400 (Cross Process I) |
| Three-record handler 0x7E56B82A, 24 tables | Ektachrome 100 (Light Tone); Cross Process II still reads them |
| New handler `gamma3` 0x7E880F5C; records of Pale&Light, Light Tone, Pop Art II (24 tables) | Fuji Pro 400H (Pop Art I) |
| `matrix3` 0x7E880F8D → stock tables 0x7E768F46, 0x7E768F58 and new table 0x7E880FC2 | Portra 400, Ektachrome 100, Pro 400H |

Results: Portra and Ektachrome render bit-identically to the build before the new code. Pro 400H:
with Pop Art's stock chroma curves (stage f) natural colours were 2.45 ΔE from target; with the
linear set (`three-films-2`) 1.20, and the slot follows the model like the other two.

Side effects: Cross Process II = Ektachrome's curves with its own look table, saturation, six-axis
and no matrix (not a usable look). Pale&Light I and Pop Art II use the default gamma record and
have no matrix; the stock Pop Art look is gone. Labels: "Cross Process" → "Portra 400", "Light
Tone" → "Ektachrome", "Pop Art" → "Pro400H" (each shared by the entry's types).

## 5. The third slot, as built (NOTES §29–30), and what a fourth would need

- **Space:** the large 0xFF runs in block 0 are the gaps between the ranges the firmware loads into
  RAM, so they are never loaded. Inside the loaded ranges there are about 3.5 KB of 0xFF: 164 B at
  0x7E880F5C (boot segment; 120 B now used), 1,912 B at 0x7ECB0888, 1,156 B at 0x7F033B7C and three
  runs under 160 B. Enough for code, records and matrices; not for 24 new gamma tables.
- **Curves:** `gamma3`, a copy of the handler at 0x7E56B82A (49 bytes) with the records of
  Pale&Light, Light Tone and Pop Art II, ending in a jump to the common tail 0x7E56B852. **[C]**
- **Host entry:** Pop Art I (code 70). The range check was lowered to 70; key 0 then matches hash
  entry 8, whose handler field no other key can use (emulated for all codes, and **[C]**).
- **Matrix:** `matrix3` replaces the compare chain at 0x7E56C6A5 (a 5-byte jump). **[C]**
- **Chroma curves:** the host's stage-(f) tables must be made linear (found after the first flash).
- **Film 4 and beyond:** gamma-table space only with one table per channel (1.5 KB in the 1.9 KB
  run), and no clean host entry is left: Pale&Light I changes the WB (not located), Pin Hole /
  Diorama / Soft Focus run effect modules. Check stage (f) and the model fit of the stock rendering
  for any candidate first.

## 6. Method for a new film in an existing slot

1. Target: `spektrafilm-lut build` for negative film + print; `bake_slide.py` for slide film.
2. `fit_film.py --lut … --slot … --name …` (calibrated model, no camera).
0. Before choosing a slot: develop the test RAW with the slot's stock look and check that the
   model reproduces it (clean slots: about 0.9 ΔE). A worse fit means an unmodelled stage.
3. Flash; RAW Data Edit `PB130001.ORF` (the second-generation test RAW) with the slot;
   `analyze_mock2.py` / `check_film.py`.
4. `fit_film.py … --anchor <read name> <first fit .npz> --robust 3`; flash; check again.

Measured so far (ΔE2000 vs target, 1,120 natural-colour patches): Portra 1.47 → 1.31 after one
correction; Ektachrome 1.55 on the first, model-only build → 1.39 after one correction.

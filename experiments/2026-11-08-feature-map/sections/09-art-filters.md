# 09 — Art filters: what ships, what is hidden, and where the hidden ones came from

This section sums up the art-filter deep dive. The detail is in [09a-art-gui.md](09a-art-gui.md) (menus, settings, gating) and [09b-art-algorithms.md](09b-art-algorithms.md) (what each module does to pixels).

- **Labels:** **verified** = read in the code or bytes; **inferred** = from names, order or layout.
- **Addresses:** E-PM2 v1.6 runtime addresses (block-0 offset = address − 0x7E421020).
- **Section 03 is superseded here.** It placed Watercolor at menu id 116 and named id 120 "Pastel"; both were inferences, and both were wrong (see §2).

## 1. How an art filter is chosen and run (verified)

1. **Stored setting.** Picture Mode is prm tag 0x9481 (u8). Normal modes are 1–7; art modes are **menu ids 100–120**. The ART shooting mode uses its own list (info 281); see 09a.
2. **GUI to stored value.** The GUI never sees 100–120. The mode controller converts GUI value ↔ stored value through fixed ROM tables: `gui[]` at 0x7E83F70C (19 entries) and `raw[]` at 0x7E844CC0 (19 × 64-byte records).
   - Normal modes: GUI 7 → 7 i-Enhance, 0 → 1 Vivid, 1 → 2 Natural, 2 → 3 Muted, 5 → 4 Portrait, 3 → 5 Monotone, 6 → 6 Custom.
   - Art modes: **GUI 8–17 → 100–109, 18 → 119, 19 → 120.**
   - An unknown GUI value is written as i-Enhance. A stored value with no entry reads back as Watercolor (09a).
3. **Menu id to internal code.** `art_GetFilterType` 0x7E71BD94 maps (menu id, variant I/II/III) to an internal code, for example 100 → 70/102. The full table is in §3.
4. **Code to module.** `art_set_func_filter` 0x7E72A562 looks the code up in the 32-entry table at 0x7E85C45C. Codes with no entry are done purely by image-processor (ISP) parameters.
5. **Running the chain.** The ART task chains three stages: still → YCC conversion, then the filter module, then up to 5 art effects. Each module runs its own pass table.
6. **Exif.** `rec_art_set_exif_data` 0x7E70DC24 (jump table 0x7E852300) writes the Olympus MakerNote ArtFilter value. These numbers match the published ExifTool table (`Image::ExifTool::Olympus`, `%filters`).

## 2. The 12 shipped filters (verified)

| Menu label (string id) | Stored | Internal code(s) | Module | Exif ArtFilter |
|---|---|---|---|---|
| Pop Art (67) | 100 | 70 / 102 | ISP only | 2 / 16 |
| Soft Focus (68) | 101 | 69 | soft-focus effect slot | 1 |
| Pale&Light Color (66) | 102 | 71 / 145 | ISP only | 3 / 15 |
| Light Tone (65) | 103 | 72 | ISP only | 4 |
| Grainy Film (64) | 104 | 74 / 104 | `art_filter_06_rough_monochrome` + block 2 noise | 6 / 19 |
| Pin Hole (69) | 105 | 73 / 106 / 108 | `art_effect_20_pinhole` | 5 / 17 / 18 |
| Diorama (61) | 106 | 86 | `art_filter_09_diorama` | (9) |
| Cross Process (60) | 107 | 85 / 167 | ISP only | 10 / 31 |
| Gentle Sepia (63) | 108 | 91 | `art_filter_0e_gentle_sepia` | 14 |
| Dramatic Tone (62) | 109 | 96 / 165 | `art_filter_14_dramatic_tone` | 20 / 32 |
| **Key Line** (1452) | **119** | 163 / 169 | `art_filter_19_artclearline` ("ligne claire") | 25 / 26 |
| **Watercolor** (1717) | **120** | 181 / 182 | **`art_filter_21_pastel_art`** | **33 / 34** = Watercolor I / II |

Proof that Watercolor is 120:
- The ART BKT list builder 0x7EA7633A pairs bracketing info 469 with stored 120, and the menu table labels info 469 "Watercolor" (string 1717). It pairs info 424 ("Key Line", 1452) with 119.
- The Exif writer records 33/34 for 120, which ExifTool names Watercolor I/II; its comments note an E-PM2 sample.
- The API `colorTone` enum names this slot `COLORTONE_PASTEL`. So "pastel art" is simply the internal name of Watercolor.

Watercolor is a complete 11-pass module: a RAW re-develop with noise reduction, two parallel image-engine branches and an image-DMA merge. I and II differ only by an image-engine preset index (11/13 and 10/12) (09b).

## 3. The hidden menu ids 110–118

| Menu id | Code | Module | Exif in E-PM2 | Exif in E-PL7 / E-M5 II / PEN-F | Identity |
|---|---|---|---|---|---|
| 110 | 145 | (same as Pale&Light II) | **15** = Pale & Light Color II (writer case 0x7E70DE4B: `mov 15,d0; movhu d0,(a3)`; the E-P5 writer 0x7E3ECFAA also stores 15) | default | Pale&Light Color II alias ("Tender Light") — inferred (A10 2026-11-09) |
| 111 | 75 | none | none (default) | **12 = Fish Eye** | Magic Filter "Fish Eye" |
| 112 | 84 | none | none | none | "Drawing" — inferred from order (ExifTool 13) |
| 113 | 69 | soft focus | none | none | "Soft Focus 2" — inferred (ExifTool 22) |
| 114 | 117 | none | none | none | "Punk" — inferred (ExifTool 21) |
| 115 | 118 | `art_effect_10_star_light` | none | **23 = Sparkle** | Magic Filter "Sparkle" |
| 116 | 119 | none | none | none | compact "Watercolor" (ExifTool 24) — inferred |
| 117 | 151 | `art_filter_1c_mirror` (**empty**) | none | **28 = Reflection** | Magic Filter "Reflection" |
| 118 | 153 | `art_filter_1d_composite` | none | **29 = Fragmented** | Magic Filter "Fragmented" |

- **Verified for the bold Exif values.** In the E-PL7 writer 0x7DE40D28, case 111 stores 12, 115 stores 23, 117 stores 28 and 118 stores 29. In the E-PM2 and E-P5 writers, 111–118 all go to the default case and write no art value.
- **These are Olympus's compact-camera "Magic Filters".** ExifTool lists Fish Eye 12, Drawing 13, Punk 21, Soft Focus 2 22, Sparkle 23, Watercolor 24, Miniature 27, Reflection 28 and Fragmented 29 for the SZ-10, TG-820 and SZ-31MR. Ids 111–118 follow nearly the same order. Miniature is missing, since Diorama covers it.
- **Algorithms (09b, verified):**
  - **Sparkle** reuses the user-visible "Add Star Light Effect" module with no extra base look.
  - **Reflection's** two passes only log and set their done bits; the image passes through unchanged. The module is a skeleton.
  - **Fragmented** really works. On the CPU, it fills the frame black, cuts the image into a 16×9 grid (8×6 except for 16:9) and pastes the cells in random order (xorshift32 random generator, seeded from the clock). Each cell is shrunk to 87.5–100 %, shifted, and given one of four soft masks. Its mask buffer may be too small for 16:9 and 1:1 (possible overrun, not confirmed).
  - **Fish Eye, Drawing, Punk and the compact Watercolor** have menu ids and codes, but no module and no Exif value in the E-PM2. The code was never written.
- **Why they cannot be selected (verified, 09a):**
  - The GUI tables have no entry for 110–118.
  - The API `colorTone` enum has no names for them.
  - The ART-mode and picture-mode reset paths change hidden values to Pop Art or Natural.
  - The only ways to store one are the debug shells (`app Set_CameraInfo`, `prmdbg`). What the still pipeline would then do was not traced.
- The movie path also has codes for them: mirror 152, composite 154 (09a, `mov_art` 0x7E6CBFD3).

## 4. Across the lineup (verified unless marked)

All bodies below were downloaded from the `ep5-fw-reverse` archive and checked against its manifest. The E-PL5 file also matches the xdel.ru hash recorded in `firmware/README.md`. Bases were found by counting string-pointer hits (`scripts/art_findbase.py`).

| Body (fw) | Base | Art menu ids handled by the Exif writer | Hidden modules in block 0 | New filters |
|---|---|---|---|---|
| E-PM2 1.6 | 0x7E421020 | 100–120; 111–118 default | star_light, mirror, composite (source names) | — |
| E-PL5 1.6 | 0x7E421020 | (same code as E-PM2) | same | — |
| E-P5 1.8 | 0x7E101020 | 100–120, same as E-PM2 | same | — |
| E-PL6 1.4 | 0x7E421020 | (not decoded) | same | — |
| E-PL7 1.4 | 0x7D971020 | 100–122; **111, 115, 117, 118 now get 12/23/28/29** | no source names (stripped) | 121 Vintage (36–38), 122 Partial Color (39–41) |
| E-M5 II 4.1 | 0x60021020 | 100–123, same as E-PL7 | stripped | + 123 Bleach Bypass (42/43) |
| PEN-F 3.1 | 0x60021020 | 100–123 | stripped | same set |

- **Enums:**
  - The `COLORTONE_*` and `SCENE_PROGRAM_*` enums are identical across E-PM2/E-PL5/E-P5/E-PL6, apart from E_PORTRAIT and RESERVES_NIGHT_SHOT on the E-P5.
  - From the E-PL7 on they add VINTAGE and PARTCOLOR, and the E-M5 II adds BLEACH_BYPASS.
  - None of them ever names Fish Eye, Sparkle, Reflection or Fragmented (`scripts/art_enum.py`).
- **Menu text:** no body's block 1 contains "Sparkle", "Reflection", "Fragmented" or "Punk" as a label (`scripts/art_names.py`). "Fisheye" appears only for the SCN mode "Fisheye Effect" with the FCON-P01 converter (SCENE_PROGRAM_ATTACHMENT_FISH_EYE), which is a separate path.
- **Reading (inferred):** Olympus ported some compact Magic Filters into the shared PEN/OM-D art engine around 2012. They finished Fragmented and Sparkle, left Reflection empty, and never wrote Fish Eye, Drawing, Punk or the compact Watercolor. They were never put in any of these bodies' menus. By 2014 the Exif writer had learnt names for four of them, so the work continued in the shared code even though nothing shipped.

## 5. Open questions

1. **Which still paths could run a hidden filter.** `art_IsSupportType` 0x7E71BC93 runs `art_chk_submode`, `art_chk_proccont`, `art_chk_type` (→ `art_chk_type_rec` 0x7E71C0E1 / `art_chk_type_mov`), `art_chk_effect` and `art_chk_effect_monotorn`. `art_chk_type_rec` switches on the request's processing type (req+2) and accepts only codes that have a module (verified):
   - **Type 1:** 69, 73/106/108, 74/104, 86, 96/165, **118 (Sparkle)**, 163/169, 91, 181/182.
   - **Type 2:** 73/106/108, 96/165, 163/169, 91, 181/182.
   - **Type 3:** the type-1 list plus **151 (Reflection) and 153 (Fragmented)**.
   - **Types 4/5:** as type 1 without 118. **Type 6:** only 67.

   So Sparkle would be processed by an ordinary type-1 request, and Reflection and Fragmented only by type-3 requests. Codes without a module (Fish Eye, Drawing, Punk, compact Watercolor) are never in these lists, so they fall to the ISP-only path. Still open: which caller sets req+2 = 3. In `rec_art_set_artmode` 0x7E70E222 it comes from the caller's second argument, and its callers (still, 3D, view and 3D-view exec, REC VIEW) were not traced back to that value.
2. Whether a compact Olympus firmware (e.g. SZ-31MR, TG-820) uses the same internal codes; this would confirm the 112/113/114/116 names.
3. Whether the Fragmented mask buffer really overflows for 16:9 and 1:1 (`art_buff_alloc` rounding).
4. The Watercolor I/II difference inside the image-engine preset tables (indices 10–13).

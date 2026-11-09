# 10b — Shooting modes: 3D photo, panorama, e-Portrait, smile, SCN list, art effects (E-PM2 v1.6)

Re-check of six shooting-mode features using the method of section 09. Labels: **verified** = read in code or bytes; **inferred** = from names, order or layout; **external** = product knowledge, used only as support. Addresses are E-PM2 runtime addresses (base 0x7E421020) unless a body is named. Scratch scripts: `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/hidden/shooting-modes/` (`scntab.py`, `scnlist.py`, `rec.py`, `lab.py`, `findkv.py`).

## Verdict table

| Feature | Prior claim | Verdict | Real status on E-PM2 | Shipped on (SCN list / menu, verified bytes) |
|---|---|---|---|---|
| 3D Photo | Dormant (inf); "combine step stubbed" | **CORRECTED** | Two paths. **3D-lens path:** Active when a 3D lens is fitted (hardware-gated); code is complete. **Two-shot path:** Stub; its TAKE backend is three empty `clr d0; retf` functions, and combine/record/distance are dummies | SCN code 115 is in the SCN list of all 8 bodies. The two-shot code is in E-PM2/E-PL5/E-PL6/E-P5 only. E-M10/E-PL7 keep only its API name strings. E-M5 II/PEN-F do not have even those strings |
| Panorama | Active (inf), PC-stitched; in-camera stitching stubbed | **CONFIRMED** (details added) | Active: PC-assist panorama (SCN code 14). In-camera stitching: Absent (stub or no body) | SCN code 14 on all 8 bodies |
| e-Portrait / beauty | Active; beauty-preview and eye-point helpers stubbed | **CONFIRMED, refined** | Shooting: Active (SCN code 67, real REC_BEAUTY/CSKIN code). Playback "e-Portrait" edit: Active (real `play_beauty.c`). Multi-kind "Beauty Fix" (clear-skin preview, shiny/dramatic eye, Beauty2): Stub/Absent | Code 67 on all 8 bodies. No body has English "Clear Skin / Sparkle Eye / Dramatic Eye / Beauty" text |
| Smile detection | "stubbed" | **CORRECTED** | **Absent**: the name `api_rec_dummy_Get_Smile_Face_Detect` exists only as an orphan string. No code loads it | Same orphan string on every body; no English "Smile" text on any body |
| SCN / iAuto list | SDET = iAuto detection, 12 types (inf) | **CONFIRMED with corrections** | SCN: 23 fixed entries, all selectable (no per-entry gate). SDET's 12 debug types include 3 that the SCN list does not offer and PROGRAM | 23 on E-PM2/E-PL5/E-PL6/E-P5. 24 on E-M10 (+143). 25 on E-PL7/E-M5 II/PEN-F (+143, +198) |
| Art effects | Active (inf) | **CONFIRMED, now mapped** | Active: one effect at a time, from a fixed per-filter list (12 lists) | Identical lists in E-PL5/E-PL6/E-P5. Later bodies use other bytes (not decoded) |

## 1. SCN list (verified) — used by every section below

**How a SCN mode is chosen (verified):**
- The SCN select screen draws 4 items per page from the ROM table **0x7EFE9240**: 23 × 14-byte records `{u16 code, u16 label, u16 icon, u16 icon, u16 description, …}` (draw fn 0x7EDDA6CA).
- On confirm, **0x7EDDA91D** checks `cursor < 23`, reads `code = *(u16*)(0x7EFE9240 + 14·cursor)` and calls setSetting(**info 280**, code) through 0x7EE01D4E.
- Info 280 = prm 0x2881 (u8, MODE, default 9 = Portrait). Its mcon record at 0x7E84AEA4 is type 1 with 23 bytes at **0x7E84976D** (verified). The bytes match the screen table in the same order.
- The draw loop has no per-entry skip and no model or lens test. So all 23 entries are shown and selectable (verified for 0x7EDDA6CA; the mcon reset hooks for info 280 were not traced).
- A second label table of the same shape is at 0x7EFEA388 (`{idx 2..24, code, icon, icon, label×3}`). It has the same 23 codes.

| # | code | label (string id) | name in code |
|---|---|---|---|
| 1 | 9 | Portrait (242) | PORTRAIT — **verified** (SDET `dbgscnmode` 0x7E6637F2 prints name + code) |
| 2 | 67 | e-Portrait (114) | BEAUTY (inferred from the label) |
| 3 | 11 | Landscape (234) | SCENERY — verified |
| 4 | 17 | Landscape+Portrait (1109) | SCENERY_PORTRAIT — verified |
| 5 | 8 | Sport (244) | SPORTS — verified |
| 6 | 12 | Night Scene (240) | NIGHT_SHOT — verified |
| 7 | 18 | Night+Portrait (239) | NIGHT_SHOT_PORTRAIT — verified |
| 8–11 | 47, 40, 46, 41 | Children, High Key, Low Key, DIS Mode | CHILDREN, HIGHKEY, LOWKEY, ANTI_VIBRATION (inferred) |
| 12 | 23 | Macro (236) | MACRO — verified |
| 13–14 | 49, 31 | Nature Macro, Candle | NATURE_MACRO, CANDLE (inferred) |
| 15 | 21 | Sunset (245) | EVENING_SUN — verified |
| 16–19 | 26, 14, 20, 29 | Documents, Panorama, Fireworks, Beach & Snow | DOCUMENT, PANORAMA, FIRE_WORKS, BEACH_SNOW (inferred) |
| 20–22 | 110, 111, 112 | Fisheye Effect / Wide-Angle / Macro (converters FCON-P01, WCON-P01, MCON-P01) | ATTACHMENT_FISH_EYE/WIDE/MACRO (inferred; `get_scene_program` 0x7EB100BC returns 22/23/24 from lens names "FCON"/"WCON"/"MCON", verified) |
| 23 | 115 | 3D Photo (769) | 3D (inferred; `get_scene_program` returns 42 when its info 1289 = 114, a separate Exif value) |

**SCENE_PROGRAM enum (verified):**
- The `sdk api` printer 0x7E9A87F5 range-checks 0..45 and jumps through the sequential table at 0x7EC0CFAC. So the enum has exactly 46 values, NOTHING = 0 … PASTEL = 45, in the order of the strings.
- It is an API enum for picture info (`getRecViewInfo` 0x7E985746 converts an internal field 0..45 to it), not the SCN code.

**In the enum but not offered on the E-PM2:**
- **Art entries POPART…DRAMATIC_TONE, LIGNE_CLAIR, PASTEL (12).** These are the ART mode's 12 filters (section 09), not SCN items.
- **SPOT_LIGHT and UNDERWATER_SNAP.** iAuto-only:
  - SDET's debug list names them with codes **157** and **50** (verified). SDET also names NIGHT_SHOT_MACRO **156**, which has no SCENE_PROGRAM name.
  - 157 and 50 are in info 24's accepted list (mcon 0x7E84AE78, 120 codes).
  - So iAuto can report these scenes, but the user cannot pick them (inferred).
- **NOTHING, PARTY, SELT_PORTRAIT (sic), COOKING, UNDERWATER_WIDE1/WIDE2/MACRO, ANIMAL, SNOW:**
  - No SCN entry on any of the 8 bodies (verified lists).
  - No English label for them on any body (verified exact-label grep: Cuisine/Cooking/Party/Indoor/Self Portrait/Pet/Animal/Snow/Underwater Wide/Macro).
  - "Underwater" (1306) on the E-PM2 is a WB value (record at 0x7EFEA50E).
  - The mode controller accepts every code 3..61 for info 24 (verified list). The hidden programs probably sit among the unused codes there, but the code → name mapping for them was **not** found, and what each would do was **not** traced.
  - External: these names match Olympus compact scene modes (Cuisine, Self Portrait, Pet, Snow, Underwater Wide1/2/Macro). Read: a compact-heritage superset (inferred).

**SDET (iAuto):**
- The 12 names in `dbgscnmode` are PORTRAIT 9, SCENERY 11, SCENERY_PORTRAIT 17, NIGHT_SHOT 12, NIGHT_SHOT_PORTRAIT 18, NIGHT_SHOT_MACRO 156, EVENING_SUN 21, SPORTS 8, MACRO 23, SPOT_LIGHT 157, UNDERWATER_SNAP 50, PROGRAM 3 (verified immediates at 0x7E663939–0x7E6639E8).
- The prior "12 types" is the right count, but one of them is PROGRAM (no scene), and `gyakkou`/`aozora`/… are flags, not types.
- Orphan strings `OneShot Detect …` add LOW_LIGHT.
- Debug override: `app iauto <val>` (0x7E6776E9).
- Whether the detector really outputs all 12 was not traced (the algorithm block has no strings).

**Cross-body (verified bytes, mcon record found by its pointer):**

| Body | info id | count | list |
|---|---|---|---|
| E-PM2 / E-PL5 / E-PL6 | 280 | 23 | as above (E-PL5 0x7E84A8C5, E-PL6 0x7E84A5C9) |
| E-P5 | 280 | 23 | identical (0x7E54748E) |
| E-M10 | 279 | 24 | **143** inserted after Sport (0x7DC47044) |
| E-PL7 / E-M5 II / PEN-F | 279 | 25 | 143 after Sport and **198** after 115 |

- 143 = "Hand-Held Starlight" and 198 = "Panning" (inferred: new English labels in those bodies' diff lists; external: these are the scene modes Olympus added).

## 2. 3D Photo (SCN code 115)

**Code (verified):**
- **Two-shot path** (`CapT3d_Take3d`, 0x7EA4D0A5–0x7EA4DA5F; GUI init3DShooting 0x7ECD77DE / start3DShooting 0x7ECD7800 / restart… / endShootingPicture3DShooting):
  - `take_3d_start` → `api_rec_Start_Take_3d` 0x7E68B98A → TAKE **0x7E58287F = `clr d0; retf`**.
  - `api_rec_End_Take_3d` 0x7E68B9D8 → **0x7E582883** (same empty body).
  - `api_rec_Get_Take_3d_Count` 0x7E68B9F2 → **0x7E582887** (returns 0).
  - The prior report called Start_Take_3d "real". Its API wrapper is real (log + mode mapping 0/1→1/2), but the work it hands to TAKE is an empty stub.
  - Combine and record are dummies: `create3dCombineYC` → `Make_YC_3D_Still`, `create3dAnimationYC` → `Make_YC_3D_Slide_Amime`, `get3dDistance` → `Get_Rec_Result_3d_Distance`, `start3dCombine` 0x7EA4D845 → `Execute_3D_Still` 0x7E68C72F, `start3dRecording` 0x7EA4D95A → `Record_3D_Still` 0x7E68C756, `notifyCombineResult` → `Get_Rec_Result_3d_Combine` (returns 0).
  - `Execute_3D_Still` and `Record_3D_Still` log, call 0x7E880EFF(0xF00F0000, 1) (an error-report helper with 118 callers; inferred) and return 0xF00F0000 (an error-class code; inferred).
  - Only the alignment overlay is real: `set3dOverlapEffect` 0x7EA4D700 → `api_play_Set_Effect` / Start / Stop_Effect (the EFFECT task's `3d_overlap`).
  - **Verdict: Stub.** It cannot take a second frame or write an MPO (verified chain; what the screen shows was not traced; string 981 "3D photo was not created." is probably its failure message, inferred).
- **3D-lens path:**
  - GUI `checkConnect3DLens` 0x7ECD7899 starts `start3DLensShooting` only when `0x7ECD6117` (info 26 == 115) is true **and** a lens query returns 3. Otherwise it ends the 3D-lens mode.
  - TAKE 0x7E582893: when prm 0x85C1 (info 26) == 115 and the lens status `0x7E522647` (the backend of `api_rec_Get_Lens_Trouble_Status`) == 64, it loads stereo offsets.
  - Bit 0x40 (value 64, bit 6; `or 64` (audit 2026-11-09)) is set when the lens info is ≥ 0x102A and RAM flag 0x604F67AC bit 0x200000 is set. The lens debug `LENS_INFO_3D` 0x7E5288EB prints convergence_angle and baseline_length (verified strings), so this is a 3D-lens test (inferred, strong).
  - REC: handle +17132 == 12 → 0x7E70BD7F: `rec_3d_lens_art_exec` 0x7E70CF0B → `rec_3d_write_mpo` 0x7E70BF3C (→ `rec_3d_make_jpg` 0x7E70C1EB + `rec_3d_make_mpo` 0x7E70C23F, 390 B) → `rec_3d_free`. View: `rec_3d_lens_view`.
  - Every function is real (sizes 64–1054 bytes, no log-and-return).
  - **Verdict: complete, reachable only with a 3D lens fitted** (hardware-gated).
  - External: the only Micro Four Thirds 3D lens is Panasonic's H-FT012. Not checked on hardware.
- **Reachability:** SCN entry 24 → info 280 = 115 (verified, §1). The mapping from SCN code to shooting component (factory ids 16/17 = `Cmp_3dShootingAutoComponentFactory`, section 06) was not traced.
- **Cross-body (verified strings / functions):**
  - E-PL5, E-PL6, E-P5: the same two-shot code and dummies. The TAKE backend is also `clr d0; retf` (E-PL5 0x7E582ADF, E-P5 0x7E247E06).
  - E-M10, E-PL7: `api_rec_Start_Take_3d` and the 3D dummies exist only as strings (no function loads them), and `start3dCombine` is gone.
  - E-M5 II, PEN-F: even those strings are gone.
  - All 8 bodies keep `checkConnect3DLens` and SCN code 115.
  - Read (inferred): the two-shot 3D was never finished in the PEN/OM-D line, and was later deleted. The 3D-lens 3D Photo stayed.

## 3. Panorama (SCN code 14)

- **Take side (verified):**
  - `api_rec_Start_TakePanorama` 0x7E688C7D (caller 0x7EA34520) → TAKE **0x7E59F85E**. That function is real: it clears the shot count, sets RAM 0x605170F4 = 1 (active), and reads prm 0x84A1 (info 463, the direction inferred), keeping 1/4/5 and zeroing any other value.
  - End goes to the real 0x7E59F8A1 (118 B). Get_Count goes to 0x7E59F94D, which returns the shot counter at RAM 0x605170F6.
  - TAKE_EXPOSE logs `panorama_start/end`. The guide uses `getPanoramaCount/CountMax` and `api_rec_dummy_Get_Panorama_Direction` (a dummy with 3 callers).
- **Record / stitch (verified):**
  - `api_rec_dummy_Record_Media_Panorama` 0x7E68C6D0 (caller 0x7EB92DF5, vtable-only) logs, then posts two completion callbacks (0x7E67D2C7 with 0x04080BF0 and 0x04010BFE). It fakes success.
  - `Make_Panorama_BayerToYc/YcToYc` and `Get_Panorama_Target_Info` exist only as strings (no code).
  - Playback of a stitched panorama: `api_play_dummy_Alloc_Panorama_PlayHandle` (dummy).
  - So each frame is saved as an ordinary picture, and stitching is left to the PC (inferred from the stubs; external: Olympus says panorama frames are joined in its PC software).
  - Print-size names `SIZE_4X8PANORAMA` … belong to DPOF/print (strings 1052–1057).
- **Cross-body:** code 14 in all 8 SCN lists. `api_rec_Start_TakePanorama` and the `Record_Media_Panorama` dummy are present on all 8 (verified strings). External: no PEN/OM-D in this set does in-camera sweep panorama.

## 4. e-Portrait and beauty

- **Shooting (verified as real code):**
  - REC usMode 0x1009: `REC_MODE_STILL_CSKIN_PRE` 0x7E70ED0D (still FD, cmd 4 to FACE), `REC_BEAUTY_CSKIN_EXEC_PRE` 0x7E70EE20 (788 B), `REC_BEAUTY_CSKIN_EXEC` 0x7E70F134 (670 B), `REC_BEAUTY_MAKE_IMG` 0x7E70F493, `…MAKE_CMPYC` (+rotate), `REC BEAUTY pre face Exif`, `rec_beauty_set_ctrl` 0x7E70FCBA, `rec_beauty_make_playpic`.
  - API `api_rec_Clear_Skin_Ready/Execute/Recview` (0x7E689E27 / 0x7E68A02B / 0x7E68A2AC) are real.
  - Reached through SCN code 67 (verified, §1).
  - What the user gets: skin smoothing on detected faces. External: the camera saves the corrected and the original image. That is consistent with `CmpSts_EPortraitShootingEditer`'s two rec-views (section 06, inferred).
- **Playback edit (verified as real):**
  - `play_beauty_edit_main` 0x7E93C80D (616 B; calls FACE through `play_face_beauty_revise` 0x7E9431DA) and `play_beauty_check_edit_enable` 0x7E93C78B.
  - The enable check rejects "wide" images and anything wider than 4608 or taller than 3456 (the E-PM2 sensor size). It also has a 16-pixel alignment check.
  - Plus `calc_pic_size`, `make_exif_prm` and the APIs `api_play_Check_Beauty_Edit_Enable` / `Get_…Progress`.
  - That the menu item is the JPEG-edit "e-Portrait" comes from section 06's edit table (inferred).
- **Stubbed or absent:**
  - `api_play_dummy_Alloc_Clear_Skin_Preview_Handle` 0x7E687086 returns 0 (called by CapImg_ImagePlayer 0x7EA0A574).
  - `api_play_dummy_Get_Beauty_Edit_Eye_Point` 0x7E6870AB zeroes the eye points (called from the ImagePlayer draw function 0x7EA01A5F).
  - `Edit/Init/Term_Beauty2` are strings only.
  - So `CmpEBea`'s live clear-skin preview and its BEAUTY_CLEAR_SKIN / SHINY_EYE / DRAMATIC_EYE kinds cannot work (verified stubs; the effect on screen was not traced).
- **Cross-body:** SCN code 67 on all 8. The same dummies exist on E-PL5/E-PL6/E-P5/E-M10/E-PL7. No body has English "Clear Skin", "Sparkle/Shiny Eye", "Dramatic Eye" or "Beauty" text (verified grep). So the multi-kind beauty fix never shipped in these bodies (inferred). External: it is a compact-camera feature.

## 5. Smile detection

- `api_rec_dummy_Get_Smile_Face_Detect` (0x7E7D5DF4) has **no code reference and no pointer** (`fwmap xref`: none). The linker kept the string but no function.
- FACE_MAIN/FD/PT0 commands (section 03) have no smile path.
- `smile_define_lv` (0x7EBB7965) is an unreferenced label in the playback debug-dump strings.
- **Status: Absent** (CORRECTED from "stubbed": there is no stub to call).
- Cross-body: the same orphan string on all 8. On the E-P5, `smile_define_lv %#x` is printed by 0x7E88A36F (not examined). No body has English "Smile" text.

## 6. Art effects ("Add Effects", strings 763–768)

- **Value ↔ label (verified bytes 0x7EFE8664):** 0 Off (1371), 1 Soft Focus (764), 2 Pin-Hole (765), **4 White Edge (766), 3 Frame (767)**, 5 Star Light (768). The menu order is Off, Soft, Pin-Hole, White Edge, Frame, Star.
- **One list per filter:**
  - Tag 0x44D1 (12 × u8, MODE) holds infos 371–381 and 471.
  - `0x7E702A71` switches on the GUI picture-mode value (jump table 0x7E826C5C) and reads the matching info.
  - The output is one-hot (flags +36…+52), so **only one effect can be active at a time** (verified).
  - Each list is an mcon type-1 record (raw bytes 0x7E849E2B–0x7E849E5A).

| Filter (GUI) | info | Effects offered (verified) |
|---|---|---|
| Pop Art (8) | 371 | Soft Focus, Pin-Hole, White Edge, Frame, Star Light |
| Soft Focus (9) | 375 | White Edge, Star Light |
| Pale&Light Color (10) | 376 | Soft Focus, Pin-Hole, White Edge, Frame |
| Light Tone (11) | 379 | Frame |
| Grainy Film (12) | 372 | Pin-Hole, White Edge, Frame |
| Pin Hole (13) | 373 | Frame |
| Diorama (14) | 380 | Frame |
| Cross Process (15) | 377 | Pin-Hole, White Edge, Frame |
| Gentle Sepia (16) | 378 | Soft Focus, Pin-Hole, White Edge, Frame |
| Dramatic Tone (17) | 374 | Pin-Hole, White Edge, Frame, Star Light |
| Key Line (18) | 381 | all five |
| Watercolor (19) | 471 | Soft Focus, White Edge, Frame |

- Every list starts with Off. The variant (I/II/III) infos 364–370 and 472 are read alongside (tag 0x44C1). Infos 465–468 are extra parameters for Grainy and Dramatic (not decoded).
- The step from setting value to `art_effect_*` module (art request slot 0 star, 1 soft, 2 pinhole, 3 frame, 4 white edge; section 03) was not traced. The slot names make it inferred, strong.
- **Cross-body:** the 48 list bytes are byte-identical in E-PL5 (0x7E84AF83), E-PL6 (0x7E84AC87) and E-P5 (0x7E547B54). E-M10 and later do not contain them. Their labels are renamed ("Soft Focus Effect" …). E-M10 adds "Left and Right / Top and Bottom Blur Effect" text, and PEN-F adds "Film Grain Effect" (strings only; not decoded).

## Open questions

1. What the E-PM2 does in SCN 3D Photo without a 3D lens. Does it start the stubbed two-shot statechart and show string 981, or refuse earlier? Which RAM flag sets lens status bit 0x40 (audit 2026-11-09) (0x604F67AC bit 0x200000), and from which lens-info field?
2. The mapping from scene code (info 24/26) to the internal 0..45 field (+172 of the 0x7E96A4EB object) and to Exif. This would name the unused codes 3–61 and show what PARTY, COOKING, UNDERWATER_*, ANIMAL and SNOW would do. The mcon hash 0x7E826CAC (info 24 → handler) and the string `app_mode_expose_scene_to_expose` are the next leads.
3. SCN code → shooting-component id (factory ids 6, 8, 16/17) in `CtgStl_StillImageShooting::getComponentInstance` 0x7EB9D939.
4. Whether mcon reset hooks can change info 280 (no reset path for info 280 was looked for; only the screen code was read).
5. Effect lists in E-M10 and later bodies (different bytes; the blur effects).
6. How each panorama frame is recorded (normal REC path assumed) and what prm 0x84A1 values 1/4/5 mean.

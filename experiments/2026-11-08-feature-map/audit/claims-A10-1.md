# Audit A10 batch 1

## 09-59 (sections/09-art-filters.md, line 59)

- **Verified for the bold Exif values.** In the E-PL7 writer 0x7DE40D28, case 111 stores 12, 115 stores 23, 117 stores 28 and 118 stores 29. In the E-PM2 and E-P5 writers, 111–118 all go to the default case and write no art value.

## 09-96 (sections/09-art-filters.md, line 96)

1. **Which still paths could run a hidden filter.** `art_IsSupportType` 0x7E71BC93 runs `art_chk_submode`, `art_chk_proccont`, `art_chk_type` (→ `art_chk_type_rec` 0x7E71C0E1 / `art_chk_type_mov`), `art_chk_effect` and `art_chk_effect_monotorn`. `art_chk_type_rec` switches on the request's processing type (req+2) and accepts only codes that have a module (verified):

## 09a-12 (sections/09a-art-gui.md, line 12)

- mcon has a value-list table of 505 records of 20 bytes at **0x7E84A0B8**, found by a 128-bucket hash at RAM 0x605B9750 (`0x7E70782A`). The record layout (verified from the users 0x7E707147, 0x7E7071EF, 0x7E7070B4 and 0x7E70708D) is: `+0 u16 info`, `+2 u16 variant key` (128 = default), `+4 ptr raw[]`, `+8 ptr gui[] (u32)`, `+12 u16 total bytes`, `+14 u16 element size`, `+16 u8 clamp` (1 = stop at the ends, 0 = wrap), `+17 u8 type` (1 = u8, 2 = s8, 3 = s16 nearest match, 4 = s16 exact, 5 = u16, 6 = composite) (13e §3.1) (D1 2026-11-09).

## 09a-33 (sections/09a-art-gui.md, line 33)

- GUI value 4 is not used. Info 509 and 510 (tag 0xDF31[0], [1]; composite partners 511 and 512, tag 0xDF41) have **identical** tables, at mcon records 0x7E84A5F4 and 0x7E84A608 (verified). Their prm hints `_current_edit_info` suggest the RAW-edit picture mode (inferred).

## 09a-57 (sections/09a-art-gui.md, line 57)

| ART BKT | info 414–423 → 100–109, 424 → 119, 469 → 120 (coordinator-verified builder 0x7EA7633A / 0x7EA9528D). Each info is a 0/1 flag (mcon records 0x7E84C278…0x7E84C354, raw [0, 1]) | the same 12 filters |

## 09a-68 (sections/09a-art-gui.md, line 68)

- **If 0x9481 holds 110–118** (consequences verified from the code above; end result inferred):

## 09a-78 (sections/09a-art-gui.md, line 78)

- There are no constant-id writes of 111 or 0x9481: 0 prm sets, 0 Set_CameraInfo and 0 GUI setSetting with a constant id (07-settings.tsv, verified earlier). All writes are table-driven, through mcon.

## 09b-57 (sections/09b-art-algorithms.md, line 57)

- **Verified:** op type 21 (desc+194) is the same image-engine job that `[movp]copy` 0x7E6E3161 uses. So it is a

## 09b-76 (sections/09b-art-algorithms.md, line 76)

- **Verified:** `art_chk_type` 0x7E71C0E1 accepts 151/153 only when req+2==3 (block 0x7E71C1BA). They are

## 09b-145 (sections/09b-art-algorithms.md, line 145)

- **Verified:** the star module range 0x7E71E705–0x7E72032F contains no compare with 118. Its `(6,aX)` reads are

## 09b-158 (sections/09b-art-algorithms.md, line 158)

- **Verified:** 73, 106 and 108 all go to case 0x7E72A615 → `art_effect_20_pinhole` 0x7E720332.

## 09b-161 (sections/09b-art-algorithms.md, line 161)

- **Verified:** the only other `cmp 108` sites are a numeric threshold at 0x7E551E93 and printf `%l` at 0x7F0A3479.

## 10-39 (sections/10-hidden-features.md, line 39)

| Art effects | Active (inf) | **Active (verified).** One effect at a time from a per-filter list | Values at 0x7EFE8664 |

## 10a-59 (sections/10a-shooting-timed.md, line 59)

- Panel 637 is in the panel factory hash 0x7EFE5814 and opens the generic sub-item panel 0x7EDE1E3D (verified).

## 10a-65 (sections/10a-shooting-timed.md, line 65)

- 0x7EFF8DF4 is the child list of **GUI panel 91** (record 0x7EFFAB2C). The values 482 and 483 there are panel ids, not info ids (verified).

## 10a-118 (sections/10a-shooting-timed.md, line 118)

- The E-M10, E-PL7, E-M5 II and PEN-F have a top-menu **HDR** item (verified rows at 0x7E5B1CA6 for the E-M10 and 0x7E5DAACE for the E-PL7) and `MODE_HDR1_HDR2_JUDGE_NG`.

## 10a-144 (sections/10a-shooting-timed.md, line 144)

- **Custom self-timer (verified).** Panel 629 holds Frame 473 (1–10), Timer 475 (1–30 s) and Interval 474 (5, 10, 20, 30; units inferred as 0.1 s). It is used by the drive-list entries with info 0 = 5 (GUI 24, 25). `KIND_CUSTOM_INTERVAL` is at 0x7EA981DB. Active.

## 10b-22 (sections/10b-shooting-modes.md, line 22)

- The draw loop has no per-entry skip and no model or lens test. So all 23 entries are shown and selectable (verified for 0x7EDDA6CA; the mcon reset hooks for info 280 were not traced).

## 10b-27 (sections/10b-shooting-modes.md, line 27)

| 1 | 9 | Portrait (242) | PORTRAIT — **verified** (SDET `dbgscnmode` 0x7E6637F2 prints name + code) |

## 10b-39 (sections/10b-shooting-modes.md, line 39)

| 20–22 | 110, 111, 112 | Fisheye Effect / Wide-Angle / Macro (converters FCON-P01, WCON-P01, MCON-P01) | ATTACHMENT_FISH_EYE/WIDE/MACRO (inferred; `get_scene_program` 0x7EB100BC returns 22/23/24 from lens names "FCON"/"WCON"/"MCON", verified) |

## 10b-60 (sections/10b-shooting-modes.md, line 60)

- The 12 names in `dbgscnmode` are PORTRAIT 9, SCENERY 11, SCENERY_PORTRAIT 17, NIGHT_SHOT 12, NIGHT_SHOT_PORTRAIT 18, NIGHT_SHOT_MACRO 156, EVENING_SUN 21, SPORTS 8, MACRO 23, SPOT_LIGHT 157, UNDERWATER_SNAP 50, PROGRAM 3 (verified immediates at bytes 0x7E663939–0x7E6639E8 inside the function 0x7E6637F2 (L1 2026-11-09)).

## 10b-92 (sections/10b-shooting-modes.md, line 92)

- Bit 0x40 (value 64, bit 6; `or 64` (audit 2026-11-09)) is set when the lens info is ≥ 0x102A and RAM flag 0x604F67AC bit 0x200000 is set. The lens debug `LENS_INFO_3D` 0x7E5288EB prints convergence_angle and baseline_length (verified strings), so this is a 3D-lens test (inferred, strong).


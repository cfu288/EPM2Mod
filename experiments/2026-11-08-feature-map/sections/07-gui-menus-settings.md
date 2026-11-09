# 07. GUI, menus, settings, string resources (E-PM2 v1.6)

Scope: the settings store ("prm"), the camera-info API layer above it, the GUI's access path, the menu tables, the block-1 language tables, and the hidden/debug parts of the GUI. All addresses are runtime addresses (block 0 base 0x7E421020) unless they are marked "block-1 offset".

Labels: **verified** = I read the code or bytes and they show this. **inferred** = from names, strings or layout only.

Helper scripts and raw dumps are in the scratch dir `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/gui/` (`dumpbanks.py`, `infotab.py`, `lang.py`, `menutab3.py`, `menumap.py`, `strings_en.tsv` = all 1970 English and Japanese strings).

## Overview

Settings have **two id spaces**. They are easy to mix up:

| Layer | Id | Accessor | Example |
|---|---|---|---|
| prm store (low level) | 16-bit **prm tag**. `tag>>4` = slot (0..4095), `tag&0xF` = element type | `0x7E457C75` get, `0x7E457CED` set | 26225 = 0x6671 (movie format), 33105 = 0x8151 |
| camera-info API ("MODE_*" names, `api_info_def.h`) | **info id** in 0–700, 1000–1034, 3000–3019, 4000–4021, 10000–10123, 15000–15199 | `0x7E67F822` Get_CameraInfo, `0x7E67F882` Set_CameraInfo | 482 = MODE_INTERVAL_SHOOTING_ONOFF → tag 0xDE11; 405 → 0x6671; 694 → 0x8151[7] |
| GUI (C++) | the same info ids | API object `0x7E9C9E9A()`, vtable 0x7EC0F2E4: slot 0 = setSetting, slot 1 (+4) = getSetting | the language screen calls getSetting(1009) |

So 482 is an **info id**, while 26225 and 33105 are **prm tags**. They come from different tables. **(verified)**

What I recovered:
- The full prm defaults: 1,800 tags in 6 storage classes, with type, count and default value. They are in `07-settings.tsv`.
- The info-id → (tag, index) map: 1,102 ids, 1,097 of them non-zero.
- 252 factory names for prm tags (`PRM_*`).
- The top-level menu table (all 5 menu tabs and the Custom Menu A–J headers).
- The sub-item table (picture modes, bracketing, Myset, time lapse, button and dial functions, ...). It links 120 info ids to menu labels.
- The language tables: 34 languages × 1970 string ids.

---

## 1. Settings store ("prm")

### 1.1 Tag encoding and lookup (verified)
`0x7E45726D(tag)` is the lookup. It reads the index table at RAM **0x603A0E38**: 4096 entries of 8 bytes, `{u16 tag, u16 count, u32 data_ptr}`, indexed by `tag>>4`. A second table at 0x603A8E38 is used first when the flag word at 0x603A0E34 is non-zero. That table is the "CSV" override, loaded by the debug shell's CSV loader (0x7E4564D8/0x7E456667). If the tag is missing, the code prints `DBG_PRM_INDEX_TAG_NOT_EXIST`.

The element type comes from the low nibble of the tag (`0x7E457DE0` get, `0x7E457E7D` set):

| `tag&7` | element | `tag&8` |
|---|---|---|
| 4 | u32 | signed if set (only the 8- and 16-bit getters sign-extend) |
| 2 | u16 | |
| other (0,1,3,5,6,7) | u8 (type 5 is used for strings) | |

So the high 12 bits are only a slot number. They are not a group field. The top nibble roughly follows the owner module, but the storage class does not depend on it (see the histogram in the TSV).

### 1.2 Accessor API (verified from disassembly, 0x7E457C52–0x7E457F30)
| Function | Args | Does | Static call sites |
|---|---|---|---|
| 0x7E457C52 | d0 tag | → a0 data pointer | 91 |
| 0x7E457C62 | d0 tag | → count | 37 |
| **0x7E457C75** | d0 tag, a0 base (0 = look up), d1 index | → value (zero/sign extended) | **2168** |
| **0x7E457CED** | d0 tag, a0 base (0), d1 index, a1 value | store element | **211** |
| 0x7E457CC2 / 0x7E457D34 | d0 tag, a1 buffer | copy whole array out / in | 11 / 4 |
| 0x7E457D0E | tag, index, buffer, n | set a range | 1 |
| 0x7E457D5F / 0x7E457D7E | tag, index / buffer | read the **default** value / array | 4 / 1 |
| 0x7E457DA8 | tag | reset to default (memcpy from ROM) | 9 |
| 0x7E457B9B | tag | → storage class ("getdevice") | 6 |

### 1.3 Storage classes and ROM default lists (verified)
`0x7E4573AB` sets up 6 bank descriptors at 0x60414674–0x6041468C: ROM header, RAM area and size. `0x7E457152` registers each list into the index table. A default record is `{u16 tag, u16 count, data[count×size]}` padded to 4 bytes. The list ends with tag 0. `0x7E457B9B` gives the class number from the RAM address. The class names are from the shell help text `clear <1:CSV,2:CPRAM,3:BKRAM,4:FLASH,6:EEROM,7:MODE>`.

| Class | Number | RAM storage | ROM default list | Tags |
|---|---|---|---|---|
| CSV override | 1 | 0x603B0E38 (+0x2000) | loaded from file | – |
| CPRAM | 2 | 0x603B2E38 (+0x1800) | 0x7E47D7C4 | 273 |
| BKRAM (backup RAM) | 3 | 0x603B4638 (+60 bytes) | 0x7E4762B4 | 15 |
| FLASH (adjustment and serial data) | 4 | 0x603B4674 (+0x40000) | 0x7E47EBB4 | 244 |
| ROM constant (no RAM copy) | 5 | data stays in ROM | 0x7E476330 | 468 |
| EEROM | 6 | 0x603F4674 (+0x10000) | 0x7E4B113C | 64 |
| **MODE** (user settings) | 7 | 0x60404674 (+0x10000) | 0x7E4B40D0 | 728 |
| dynamic "mode bank" | 9 | pointer set at runtime | 0x7E4B40A4 (tag list only) | 8 (stabilizer cal. `PRM_BC_*`, "STAB_FLASH") |

The user-facing settings are almost all in **MODE** (tags 0x6xxx, 0x8xxx–0x9xxx, 0xDxxx). The save/erase errors `DBG_PRM_PROC_{FLASH,BKRAM,EEROM,MODE}_SAVE_ERR` and the strings `Mode_Bank0/1` (0x7E450C4B) show that MODE is saved as a whole bank (two copies). **(inferred)**

Examples (verified):
- `0x62F1` is a ROM constant of 17 bytes = `"E-PM2"`, the model name.
- `0x6551` = `"S0043"`.
- `0x6671` default 1. `0x8151` (8 entries) defaults `0,0,0,0,0,0,2,2`.

### 1.4 prm debug shell (verified strings, 0x7E456928 / 0x7E457002)
`prmdbg [com] [val1] [val2]`. The commands are: `getvalues, getval <TagID>, getstr, setval <(cnt<<16)|TagID> <val>, setstr, getval_def, getstr_def, set_def, getdevice, clear <class>, dump <0:FLASHdef>, psave/pload <bit0 bkram, bit1 flash, bit2 eerom, bit3 mode, bit4 cflash>, chkload, erase, fmem, size`. The `(cnt<<16)|TagID` packing (index in the high half) is also used by a table of u32 words at 0x7E7C95B4. That table is the info-id table in §2.

### 1.5 Factory names (verified text)
A CSV string at **0x7F0E87D2** (10.5 KB, 252 rows) has the form `PRM_NAME,0xTAG,,,,count,FLASH|STAB_FLASH,`. Examples: `PRM_SERIAL_NUM_CAMERA 0x00FD`, `PRM_DESTINATION_AREA 0x0AA2` (region), `PRM_MODE_SHIPS_ENABLE 0x0DB1`, `PRM_MODE_DPS_ENABLE 0x0DA1`, the AF/AE/TFT/accelerometer calibration tags, and `PRM_BC_*`. All 252 match tags in the FLASH or mode-bank lists. These names are in the TSV `prm_name` column. The names cover only factory and adjustment data. The firmware has no name table for the user-setting tags.

---

## 2. Camera-info API layer (MODE_* ids)

### 2.1 Info id → prm tag (verified, 0x7E67F971 / 0x7E67FAE1)
| Info range | Table | Entry |
|---|---|---|
| 0–700 | 0x7E7C95B4 | `{u16 tag, u16 index}` |
| 1000–1034 | 0x7E7CA0A8 | `{tag, index}` |
| 4000–4021 | 0x7E7CA134 | `u16 tag` (index 0) |
| 3000–3019 | 0x7E7CA160 | `u16 tag` |
| 10000–10123 | 0x7E7CA188 | `{tag, index}` |
| 15000–15199 | 0x7E7CA378 | `{tag, index}` |

The tables are contiguous and end just before the `api_info_*` strings at 0x7E7CA6B9. Lookups are cached in RAM at 0x605A279C. Info id 6000 alone reads a RAM u16 array at 0x605A2798.

Get_CameraInfo `0x7E67F822` (1,763 static callers) does: id → tag → `0x7E6803BC` (a prm getter). Set_CameraInfo `0x7E67F882` has 134 callers. The User variants are `0x7E67FC52` and `0x7E67FC78`. The shell command `app Get_CameraInfo <info[dec]>` (0x7E677990) calls these.

The names `MODE_*` come from debug strings, for example `isStartIntervalShootingEnable return false for MODE_INTERVAL_SHOOTING_ONOFF` beside info 482. Matches that agree with the menu tables (§3): 90 = MODE_BRACKET_WB (`userMenuRec2_WBBKT ModeId = MODE_BRACKET_WB`) and 110 = MODE_PLAYSLIDE_BGM (`Get_CameraInfo(MODE_PLAYSLIDE_BGM)`).

The **mode controller** layer `0x7E6FEA5F` sits between the GUI and Get_CameraInfo. It uses two per-id hash tables:
- 64 buckets at 0x605B52D8, from the ROM list at 0x7E814864. ~~Entries carry a converter function at +20.~~ The entries are the 250 per-setting **60-byte operation records**; slot +20 is the list-variant selector, not a converter; slot +24 is the post-write hook (13e §3.2) (D1 2026-11-09).
- 128 buckets at 0x605B9750, from 505 ROM records of 20 bytes at **0x7E84A0B8** (`{u16 info, u16 flags, ptr, ptr, ...}`). ~~The pointers lead to per-mode availability matrices. These are probably "mcon_if_check_selectable" / "Search_Mode_Conflict". **(inferred)**~~ The pointers are the raw/GUI value arrays (13e §3.1). Availability is the separate 92-record conflict table **0x7E825DA8** ("Search_Mode_Conflict", 13e §2.2) (D1 2026-11-09).

### 2.2 GUI access path (verified)
The GUI never calls prm or Get_CameraInfo directly (0 call sites in 0x7ECA1020–0x7EE21020). It does `obj = 0x7E9C9E9A()` (a singleton at 0x602B2504; vtable 0x7EC0F2E4 has 29 slots) and calls through the vtable:
- slot 0 = setSetting (0x7E9CA978, `setSetting is Unresponsive`)
- slot 1 = getSetting (0x7E9CA19C → 0x7E9E76BE → 0x7E6FCABA → 0x7E6FEA5F → Get_CameraInfo)
- slot 8 = check (0x7E9C9F24; wrapper 0x7EE01F3E)

Common wrappers: `0x7EE01D38(id, &out)` (788 GUI calls), and in CA_MAIN `0x7ECD3975` getSetting / `0x7ECD3933` setSetting (they log `result of setSetting = SUCCESS and modeInfo =`).

The GUI also keeps its own data model, a singleton at 0x602B5EB8 with 16-byte slots `{getter_fn, ?, ptr, size}`. Its get is 0x7ECEF64F (1,638 calls) and its set is 0x7ECEF667 (952 calls). **(verified structure; contents not mapped)**

### 2.3 Settings table (`07-settings.tsv`)
There is one row per prm tag (1,800 rows), with these columns:
- storage class, count, type, ROM default, and factory name
- constant-tag call sites (2,132 gets and 181 sets in total)
- the info ids that map to the tag, with Get/Set_CameraInfo and GUI get/set counts
- the menu label (from §3)
- weak string hints

751 tags have at least one info id. 111 tags have a menu label.

Selected rows (call counts are static and count only constant ids):

| Info id | Tag | Class | Meaning | Source | Info get/set | GUI get/set |
|---|---|---|---|---|---|---|
| 1009 | 0x85E1 | MODE | Language | top menu param + `MODE_LANGUAGE` code (verified) | 3/0 | 5/1 |
| 19 | 0x81E1 | MODE | Rec View time | top menu | 1/0 | 1/0 |
| 33 | 0x8372 | MODE | Digital Tele-converter | top menu | 3/1 | 11/0 |
| 89 | 0x8961 | MODE | playback auto-rotate (`@A04E@`, help "displayed in the correct orientation") | top menu | 71/0 | 1/0 |
| 111 | 0x9481 | MODE | Picture Mode | top menu | 1/0 | 30/0 |
| 180 | 0x9B21 | MODE | Flash RC Mode | top menu | 1/0 | 11/0 |
| 268/269/270 | 0x1841/51/61 | MODE | Multiple Exposure frame / auto gain / overlay | sub-item table | 8/0 … | |
| 271 | 0x3081 | MODE | Image Aspect | top menu, `getAspectRatio` | 18/0 | 33/0 |
| 296 | 0x3151 | MODE | Image Stabilizer (157 still / 160 movie) | top + sub table | 0/0 | 4/0 |
| 2074 | – | – | Drive / self-timer (a virtual id; it is outside the info ranges) | top menu param; key 0 of 0x7E84A0B8 | | |
| 10 / 45 | 0x8141 / 0x8561 | MODE | still / movie record mode (quality) | sub table | 10/5, 7/0 | |
| 90,140,216,406,476,480 | 0x8991… | MODE | WB / FL / ISO / ART / HDR / AE bracketing | sub table + `MODE_BRACKET_WB` | | |
| 110 | 0x8FC1 | MODE | slideshow BGM (97 effect, 101 slide, 289/284 intervals) | sub table + string | 5/0 | 10/0 |
| 283 / 394 | 0x29B1 / 0x61B1 | MODE | "Custom Menu shown" / "Accessory-port menu shown". If either is 0, the menu-tab count drops (0x7EDEBF67) | code verified, labels inferred | 0/0 | 7/0 each |
| 405 | 0x6671 | MODE | movie format (3 = MOV, 2 = AVCHD) | earlier sections | | 1/0 |
| 694 | 0x8151[7] | MODE | movie rate select; 11–14 = 0x8151[2,1,5,0] | info table | | |
| 1000–1007 | 0x8981[0..7] | MODE | Myset 1–4 slots (1000–1003 under Reset/Myset) | sub table | 6/0 | |
| 482 | 0xDE11 | MODE | MODE_INTERVAL_SHOOTING_ONOFF (u8, default 0) | string | 3/0 | 1/0 |
| 483–486 | 0xDE21–0xDE51 | MODE | Time Lapse: Frame, Start Waiting Time, Interval Time, Time Lapse Movie | sub table | 0 | 0 |
| 23 | 0x8262 | MODE | most-read info id (510 Get_CameraInfo sites). Debug strings near it name `MODE_PLAY_1/MODE_PLAY_INDEX`, so it is probably the rec/play state | **inferred** | 510/17 | |
| 4009 / 4012 / 4018 | 0x0AA2 / 0x0DB1 / 0x0DA1 | FLASH | destination area / ships-enable / DPS-enable | factory names | | |

---

## 3. Menu structure

### 3.1 Top-level menu table, 0x7EFFE13C (verified)
The table holds 10-byte records `{u16 item_id, u16 label_str, u16 help_str, u16 kind, u16 param}` and ends with 5 zero words at 0x7EFFE2A4. Code at 0x7EDEC0A5, 0x7EDEC0FA, ... loads its address. After the table come a u16 list of submenu-page ids (176–185, 2125, 2126, 2121) and two arrays of handler pointers into 0x7EDCxxxx/0x7EDExxxx (0x7EFFE2C6 onward).

`kind`:
- 0x100 = submenu or action (param 1)
- 0x101/0x102 = select a value of info id `param`
- 0x002 = on/off of info `param`
- 0x001 = drive-mode screen (2074)
- 0x000 = IS screen (296)
- 0x106 = date/time dialog
- 0x107 = monitor-adjust dialog

The tab split below is **inferred** from item order and help text. The labels are block-1 string ids.

```
Shooting Menu 1 (str 738)        Card Setup(85) · Reset/Myset(225) · Picture Mode(203, info 111)
                                 · Record mode @A023@(213) · Image Aspect(70, info 271)
                                 · Digital Tele-converter(363, toggle info 33)
Shooting Menu 2 (494)            Drive/Self-timer @A028@/@A029@(1648, 2074) · Image Stabilizer(147, 296)
                                 · Bracketing(76) · Multiple Exposure(182, info 268) · Flash RC Mode(526, toggle 180)
Playback Menu (739)              Slideshow @A057@(262) · auto-rotate @A04E@(226, info 89) · Edit(115)
                                 · Print Order(1966) · Reset Protect(212) · Connection to Smartphone(1719)
Custom Menu (527), ids 166-175   A AF/MF(48) · B Button/Dial(79) · C Release/@A028@(1305) · D Disp/@A006@/PC(108)
                                 · E Exp/@A019@/ISO(127) · F @A01C@ Custom(135) · G @A023@/Color/WB(146)
                                 · H Record/Erase(217) · I Movie(179) · J @A008@ Utility(81)
Accessory-port menu, 2122-2124   OLYMPUS PENPAL Share(268) · PENPAL Album(270) · Electronic Viewfinder(269)
Setup Menu (1020)                Date/Time @A04B@(253) · Language @A085@(1688, info 1009) · Monitor adjust @A032@(175)
                                 · Rec View(218, info 19) · Menu Display(168) · Firmware(134)
```
`@Axxx@` is an inline icon escape in the string text (verified: present in all languages).

### 3.2 Sub-item table, 0x7EFEF4FC–0x7EFF044B (196 records; first read as 0x7EFEF50C–0x7EFEFE04, 114 items) (D1 2026-11-09)
**Corrected (13d §5) (D1 2026-11-09):** the table is **0x7EFEF4FC–0x7EFF044B, 196 records of 20 bytes** `{group, title, info, 0, kind, 0, 7, 1, label, 0}`. The label is at +16 of the **same** record. The reading below starts 16 bytes late, so its rows are out of phase; its rule "the label sits 16 bytes after the group field" still pairs each label with the right item. The "second table at 0x7EFEFE04" is the same table continued.

The rows are 20 bytes. Each row holds `{u16 group, u16 group_title_str, u16 info_id, 0, u16 kind(2), 0, 7, 1}`. The **item label is the first u16 of the next row**: the label sits 16 bytes after the group field.

I checked this pairing in three ways:
- WB BKT = 90, which matches `MODE_BRACKET_WB`.
- slideshow BGM = 110, which matches `MODE_PLAYSLIDE_BGM`.
- Monotone has B&W Filter and Pict. Tone, and i-Enhance has Effect, as on the camera.

Groups:
- **Reset/Myset (9):** Myset1–4 → 1000–1003.
- **Record mode (11):** Still 10, Movie 45.
- **Picture Mode (10):** i-Enhance 345, Vivid 346, Natural 1, Muted 348, Portrait 349, Monotone 350, Custom 351, Pop Art 1, Soft Focus 353, Pale&Light Color 354, Light Tone 355, Grainy Film 356, Pin Hole 357, Diorama 358, Cross Process 359, Gentle Sepia 360, Dramatic Tone 361, Key Line 443, Watercolor 470. Info 1 seems to mean "no setting" (it is also used for the slideshow Start action). The ids 345–470 are probably per-mode show/hide flags for "Picture Mode Settings". **(inferred)**
- **Per-mode parameters (groups 268–274):** Contrast, Sharpness, Saturation, Gradation, Effect, B&W Filter, Pict. Tone. For example, i-Enhance uses 297/298/299/312/300 and Custom uses 205–211/305.
- **Custom Self-timer (629):** Frame 473, Timer 475, Interval 474.
- **Bracketing (15):** AE 480, WB 90, FL 140, ISO 216, ART 406, HDR 476.
- **Multiple Exposure (16):** 268, 269, 270.
- **ART BKT (478):** 12 art filters 414–424 and 469, and 7 picture modes 407–413.
- **Time Lapse Settings (637):** 483–486.
- **IS (14):** 157 still, 160 movie.
- **Slideshow (20):** 110, 97, 101, 289, 284.
- **AF Mode (100):** 291 still, 292 movie.
- **Button Function (114):** 47, 48, 53, 51, 158, 56.
- **Dial Function (110):** P 70, A 74, S 72, M 76.

A second table follows at 0x7EFEFE04 with a different 20-byte layout, `{7,1,label,0,group,value,...}`. It looks like option-value lists. **(not decoded)** **Corrected:** it is the same sub-item table continued, read out of phase (13d §5) (D1 2026-11-09).

I did **not** find the item lists for Custom Menu A–J (for example AF illuminator or anti-shock). They are probably built by the per-panel C++ classes (`userMenuCustomA_AFPos`, `userMenuCustomG_WbRev`, `userMenuRec2_WBBKT`, `userMenuPlay_*`, 17 class names). Panels are created by number through a switch over 1..651 (0x7EDCBE97 → 0x7EDC7DBA). **Corrected (13d §5) (D1 2026-11-09):** the A–J lists are the ROM row table 0x7EFF7E80 (78 rows); the `userMenu*` classes do not build them. 0x7EDCBE97 → 0x7EDC7DBA creates **menu pages**; panels are created by 0x7ED19D3F (0..159).

**Caution:** the sub-item table is a **superset**. It has HDR BKT and Time Lapse, which the E-PM2 does not offer in its public menus. A record in this table does not prove that the item can be reached.

### 3.3 Interval shooting / time lapse (coordinator question 1)
- Info 482 → prm tag 0xDE11, MODE class, u8, default 0. **(verified)**
- **No menu record sets 482.** It is not in the top table, and the sub table has only group 637 with 483–486. The only u16 482 inside the top table is a help string id. **(verified for these two tables)**
- All constant-id writes of 482 store **0**. These are the 7 calls to setSetting wrapper 0x7ECD3933 with `clr d1`, in `resetIntervalShooting`, `excuteCancelIntervalForBoot`, `completeIntervalShooting cancel/continue`, `clearIntervalEndMode`, `canselShootingPictureStandby`, and 0x7ECD55AA. There are 0 Set_CameraInfo and 0 direct prm sets of 0xDE11 with a constant. The GUI reads 482 once (0x7ED9E690). **(verified)**
- The strings "Time Lapse Settings" (1357), "Interval Time", "Time Lapse Movie" and their help texts exist in all languages. Block 1 is identical to E-PL5's, so the strings alone do not prove a feature.
- **Conclusion (inferred):** time lapse cannot be reached from the E-PM2 menus. I found no path that writes a non-zero value to 482. Two paths could still do it and I did not trace them: setSetting with a table-driven id (Myset load / reset), and the PTP/remote path (the info tables at 0x7EFF8DF4 and 0x7F019004 list 482 and 483 as data).

### 3.4 Art filters (coordinator question 2)
- The Picture Mode list (§3.2) and the ART BKT list both name exactly **12 art filters**: Pop Art, Soft Focus, Pale&Light Color, Light Tone, Grainy Film, Pin Hole, Diorama, Cross Process, Gentle Sepia, Dramatic Tone, Key Line, Watercolor. **(verified table)**
- The English language table has no label for Crystal, Mirror, Vintage, Partial Color or Pastel (a search for those names finds nothing; I did not check the other 33 languages). Only the generic `ART1…ART12` (341–353, 1649–1704, 1961) exist. **(verified)** So those modules have no English menu text in this firmware, and the GUI cannot list them by name (inferred for the other languages). **Exception (09 §2):** "Pastel" (`art_filter_21_pastel_art`, stored 120) is the shipped **Watercolor**, label 1717, so that module does have English text (D1 2026-11-09).
- Variant I/II selection and the 21-id filter table from section 03 are not mapped to these entries here.
- Model gate: block 1 is shared with E-PL5, and block 0 differs per model, so the gate is per build (which list is compiled in), not a runtime check. I saw no runtime model test in the GUI. I had no E-PL5 block 0 to compare. **(inferred)**

---

## 4. String resources (block 1)

### 4.1 Layout (verified, scratch `lang.py`)
- **Block-1 directory** at block-1 offset 0: records of 16 bytes `{u32 container_addr, u32 size, 0, 0}`, 70 entries.
  - Entry 0 (0x43C40800, 3.1 MB) and entry 69 (0x44379E00, 4.2 MB) are fonts or glyphs. **(inferred)**
  - Entries 1–34 are **34 language tables**.
  - Entries 35–68 are 34 per-language bitmap sections. They hold glyph-like data, perhaps pre-rendered text. **(inferred)**
- **Language blob:** the directory address is about 0x20 *after* the real start, because the addresses are rounded to 0x200. Each blob is: header `{u32 ptr_array, u32 ptr_array_end}`, a UTF-16LE NUL-separated string pool, then the pointer array, then a footer `OlympusLanguage_<code>tft`.
  - All pointers are runtime addresses for a blob loaded at **0xBFF3D000**, the same for every language. One language is loaded into a fixed buffer at a time (`loadLanguageData languageDataAddress`, 0x7EDDBD50, which reads info 1009).
- **String id = index into the pointer array.** All 34 languages have **1970** ids.
- English blob: block-1 offset 0x3781E0. Pointer array at 0x38B758. `Pixel Mapping` = id 207, text at block-1 offset 0x37928A (this matches the known fixed point).
- Language codes: bgr chs cht csy dan deu ell **enu** esp eti fin fra hrv hun ind ita jpn kor lth lvi msl nld nor plk ptg rom rus sky slv srb sve tha trk ukr.

### 4.2 How code refers to strings (verified)
The string id is a plain u16 immediate or table field: `mov 207,d0` (0x7ED4CF57), and the label/help fields of the menu records. Id 14 is the language's own name ("English"). Ids 8–13 and 15–39 are empty in English.

Examples: 738 Shooting Menu 1, 494 Shooting Menu 2, 739 Playback Menu, 527 Custom Menu, 1020 Setup Menu, 806 Live Control, 207 Pixel Mapping, 134 Firmware, 544 Touch Screen Settings, 1719 Connection to Smartphone, 1357 Time Lapse Settings.

---

## 5. Control panels, touch, OSD, warnings
- **"SPC" means SmartPhone Connection, not Super Control Panel.** The `[GUI App SPC]` state machine (0x7EDC0019: `SsSpc_StSpcInitPass`, `StSpcStartPrivat`, `Input_String_Actuator::ok_on`) goes with the SPC_MAIN task (`spc_ctrl_write_ssid`, `chk_flashair`, iSDIO). So it is the Toshiba FlashAir Wi-Fi pairing UI. **(inferred, consistent strings)** The Super Control Panel is `Func_Scp_Actuator` (`updateScpSelectState`, `main_dial`). It reads info 111 and others. Live Control is string 806.
- **FuncMenu** (0x7EDA622C): this dumps `sAppCallerData` capability flags such as dust_reduction, count_self_timer, record_movie, lv_magnify, operate_touch, bulb_shooting, operate_custom, mf_assist, movie_effect, finder_style, operate_mode_direct and display_wizard. **(verified strings)** The function decides which function and menu paths are allowed in the current state.
- **GuiTouch:** touch coordinates and active-index logs (0x7EDE040E, 0x7EDE0983). Panel change through `guiUtility::ShowPanelEx` (0x7EDC5D2D, 193 callers) with the log `[GuiTouch] ... changePanel Fail`.
- **GUI substates:** SS_COMMON, SS_REC, SS_MENU_MAIN, SS_MENU_LV, SS_MENU_PLAY, SS_PLAY_SINGLE, SS_PLAY_MOVIE_SLIDE, SS_PLAY_INDEX, **SS_SELFADJ, SS_DEBUGMENU**, SS_USB, SS_DPS, SS_BTSEND, SS_BTRECEIVE (name table near 0x7EFDD233). **(verified strings)** The descriptor table 0x7EFB8BCC has **17** SS ids: these 14 named ones (1–11, 14–16), the unnamed stubs 12 and 13, and 17 = SS_SPC; SS 5 (MENU_PLAY) is an empty placeholder (13d §4.2) (D1 2026-11-09).
- **OSD:** OSDDRAW/OSDDBG (0x7ECCBA45 `osddraw_init`, 0x7ECCC5BD `exec_bitmap`, 0x7ECCE613 `exec_line`) is a low-level layer that draws dots, lines and bitmaps in the CA_MAIN region. **(verified strings)** The GUI itself also has GL-like code (`gl_ModelViewMatrix`, `glReadPixels`). **Corrected:** that code (0x7EE02095–~0x7EE294B4; end moved from 0x7EE21020 (C2 2026-11-09)) is a DMP GL library used only by C3D, not GUI (13d §1) (D1 2026-11-09).
- **Warnings:** `[GUI Warning]` and `Warning_Viewer` strings in 0x7EDB0847 and 0x7EDC25D4 respectively (audit 2026-11-09). I did not map them further.

## 6. Hidden, debug and service features
| Feature | Evidence | Status |
|---|---|---|
| `prmdbg` shell (read/write any tag, psave/pload/erase banks) | §1.4 | verified strings and dispatch |
| `GUI Debug` shell: `DEBUGLEVEL/DBGLVL 0-3, hist, showev, ca on/off, gpi on/off, rec on/off, ev <EventID hex>, TOUCH, CONV, INFO, SHOWEC` | 0x7EDC3D85 | verified strings |
| `app Get_CameraInfo/Set_CameraInfo/Get_CameraUserInfo <info>`, `getmodeinfo`, `modedial`, `iauto`, `evtset/evexec` | 0x7E677990 | verified |
| GUI debug menu `SS_DEBUGMENU` (`gdbDebugMenu.usRightMark/usItem/usPrg`, `doCmdSsDebugMenuColor_Setting/Result EvtKeyPowerOn`) | 0x7ED48BBA, 0x7EDA0968 | strings verified; ~~entry key combination not found~~ superseded: entry through SS_MENU_MAIN HIDE_MODE (13d §4.3), plus a second OK-long/MENU-long/OK sequence (14e §4.4) (D2 2026-11-09) |
| Self-adjust menu `SS_SELFADJ` (`startSelfAdjustMenuSubAppStateMisc` 0x7ECE067B, `SelfAdjust::getMenuItem…turnOnTFT`, `api_adj_Check_Execute_Self_Adjust`) | | verified strings |
| Version-check menu (`CAM_MISC_VERCHK_MENU`, `startVersionCheckMenuSubAppStateMisc` 0x7ECE0653, `[GUI App Version]:OkOn called , F/W Version up start`) | 0x7EDA9D03 (loads the F/W string at 0x7EDAA63F), 0x7EDFD86F (audit 2026-11-09) | verified strings. The Firmware item can start a firmware update. |
| Life test (`[GUI App]:Life Test Start`, `registerCode`, `eraseCode`, `LifeTest::getLifeTestMode`) | 0x7EFD1FB4 | verified strings |
| Shipping info: `API_SHIPPING_INFO_{DEST_AREA, FLAG, DPS, TIME_ADJUST, MENU_BUTTON}` (Maintenance::getShippingInfo) → FLASH tags 0x0AA2/0x0DB1/0x0DA1 | 0x7EC0A321, 0x7EDFD665 | verified strings and names |
| Pixel Mapping (CmpCst_Function 0x7EAA8FF9…, api_rec_Calculate/Save_Pixelmaping) | | verified strings. That it is a normal Custom Menu J item is **inferred** (the A–J item lists are not decoded) (audit 2026-11-09) |

**Model identity:** the model name is ROM-constant prm tag 0x62F1 = `"E-PM2"`, with product code 0x6551 = `"S0043"`. The firmware has no "E-PL5" string; `PL5GAMMACSV` is a display gamma table name, not a model. Block 1 is shared with E-PL5. Block 0 is per model. I found no runtime E-PL5/E-PM2 switch in the GUI; the differences come from the build. **(verified absence of model strings; the gate conclusion is inferred)**

## Open questions
1. Custom Menu A–J item lists. They are not in the two decoded tables. Next step: follow `userMenu*` constructors and the panel switch at 0x7EDCBE97. There is also the second value table at 0x7EFEFE04.
2. Meaning of most of the 1,097 mapped info ids. The TSV gives call counts and weak hints. A pass that pairs each GUI setSetting/getSetting site with nearby `[GUI App]` strings would name many more.
3. The 505-record mode-conflict table at 0x7E84A0B8 and its availability matrices (which settings each exposure mode allows).
4. How SS_DEBUGMENU and SS_SELFADJ are entered (key combination or flag), and whether `PRM_MODE_SHIPS_ENABLE` / `API_SHIPPING_INFO_MENU_BUTTON` gates them.
5. Whether anything non-constant (Myset load, PTP set-property, the info tables at 0x7EFF8DF4/0x7F019004) can write a non-zero value to info 482 or turn on HDR BKT (476).
6. Block-1 entries 35–68 (per-language bitmaps) and the two big font sections.

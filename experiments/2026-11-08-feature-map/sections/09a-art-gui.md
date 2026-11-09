# 09a. Art filters in the GUI: value conversion, list building, hidden ids (E-PM2 v1.6)

Scope: how the GUI's picture-mode values become stored values in prm 0x9481, which art filters the GUI can select, and whether anything can store the hidden ids 110–118. Then a comparison with E-PL5 v1.6 and E-P5 v1.8 block 0.

Labels: **verified** = I read it in the code or the bytes. **inferred** = from names, strings or layout only. Addresses are E-PM2 runtime addresses (base 0x7E421020) unless marked otherwise. The scratch scripts are in `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/art-gui/` (`mcon.py`, `comp.py`, `scan.py`, `fsig.py`, `cmpbody.py`, `body2.py`).

## Q1. Conversion between info 111 and prm 0x9481

### 1.1 Where the conversion happens (verified)
- Get_CameraInfo `0x7E67F822` → `0x7E67F82B` and Set_CameraInfo `0x7E67F882` → `0x7E67F899` do **no** value conversion. They only map info id → (tag, index) and call prm get/set. Set_CameraInfo does no range check: its only test is a lock byte at RAM 0x605A5B50 (`0x7E680266`).
- The conversion is in the **mode controller** ("mcon", ~~0x7E6FC000–0x7E708000~~ 0x7E6FCA60–0x7E70787F, 13e §1 (D1 2026-11-09)), which the GUI reaches through getSetting: 0x7E9CA19C → 0x7E9E76BE → 0x7E6FCABA → **`0x7E6FEA5F`**.
- mcon has a value-list table of 505 records of 20 bytes at **0x7E84A0B8**, found by a 128-bucket hash at RAM 0x605B9750 (`0x7E70782A`). The record layout (verified; the users 0x7E707147, 0x7E7071EF, 0x7E7070B4 and 0x7E70708D read +4, +8, +12, +14 and +17 (6 vs not 6); +2 is read by 0x7E707854, the +16 clamp is used by the u8 step 0x7E7074B5, and the type codes come from the dispatcher 0x7E70761C (cases 1–6, `extb` for type 2)) is: `+0 u16 info`, `+2 u16 variant key` (128 = default), `+4 ptr raw[]`, `+8 ptr gui[] (u32)`, `+12 u16 total bytes`, `+14 u16 element size`, `+16 u8 clamp` (1 = stop at the ends, 0 = wrap), `+17 u8 type` (1 = u8, 2 = s8, 3 = s16 nearest match, 4 = s16 exact, 5 = u16, 6 = composite) (13e §3.1) (D1 2026-11-09). (A10 2026-11-09)
- Type 6 is a **composite**: each raw element is 64 bytes (16 u32). It holds the values of several info ids, and the id list comes from the table at **0x7E8182FC** (68 records of 34 bytes `{u16 info, u16 ids[..], 2000 = end}`, `0x7E6FF5D3`).
- **Read path:** `0x7E6FED4C` zeroes a 64-byte buffer and fills it with Get_CameraInfo of each listed id. `0x7E707147` then compares it with memcmp (`0x7E508294`) against each raw element, and `0x7E70708D` returns `gui[index]`.
- **Write path:** `0x7E6FEB74` → `0x7E7070B4` → `0x7E7071EF` finds the GUI value in `gui[]` and takes `raw[index]`. Then `0x7E6FF4C7` → `0x7E6FF788` calls Set_CameraInfo for each listed id.

### 1.2 Info 111 (Picture Mode): mcon record 0x7E84A388, composite ids {111, 553} at 0x7E8186D6 (verified bytes)
raw[] is at 0x7E844CC0 (19 × 64 bytes) and gui[] is at 0x7E83F70C. Info 553 is prm tag 0x84B1 (u8, MODE).

| GUI value | stored 0x9481 (info 111) | info 553 | Menu label (string id, from table 0x7EF1F4D6) | API colorTone (§1.4) |
|---|---|---|---|---|
| 0 | 1 | 0 | Vivid (1574) | 1 VIVID |
| 1 | 2 | 0 | Natural (1575) | 2 NATURAL |
| 2 | 3 | 0 | Muted (183) | 3 FLAT |
| 3 | 5 | **1** | Monotone (176) | 5 MONOTONE |
| 5 | 4 | 0 | Portrait (1578) | 4 PORTRAIT |
| 6 | 6 | 0 | Custom (95) | resolved through info 211 (the base mode of Custom) |
| 7 | 7 | 0 | i-Enhance (145) | 6 IFINISH |
| 8–17 | 100–109 | 0 | Pop Art, Soft Focus, Pale&Light Color, Light Tone, Grainy Film, Pin Hole, Diorama, Cross Process, Gentle Sepia, Dramatic Tone | 7, 9, 10, 12, 11, 8, 13, 14, 15, 16 |
| 18 | 119 | 0 | Key Line (1452) | 17 LIGNE_CLAIR |
| 19 | **120** | 0 | Watercolor (1717) | 18 PASTEL |

- GUI value 4 is not used. Info 509 and 510 (tag 0xDF31[0], [1]; composite partners 511 and 512, tag 0xDF41) have **identical** tables, at mcon records 0x7E84A5F4 and 0x7E84A608 (verified). Their prm hints `_current_edit_info` suggest the RAW-edit picture mode (inferred).
- **Ids 110–118 have no GUI value** (verified). The only mcon records whose values include 100..120 are 111, 509 and 510 (`scan.py` over all 505 records). The "110, 111, 112, 115" in the lists of info 26 and info 280 are scene codes, not art ids.
- **Edge cases (verified from the code logic):**
  - **Read fallback:** the compare loop in 0x7E707147 tests only entries 0..n−2. When nothing matches, it returns index n−1 = 18 → **GUI 19 (Watercolor)**. So a stored value of 110–118 (or 0, the ROM default of 0x9481, or 5 with 553 = 0) **reads back as Watercolor** in the GUI.
  - **Write fallback:** a GUI value that is not in gui[] gives index 0 → stored 7 (i-Enhance). So the GUI write path can produce only the 19 stored values above.

### 1.3 Show/hide flags and the reset checks (verified)
- Table **0x7E826AFC**: 19 pairs of `{u32 gui, u32 info}`: 7→345, 0→346, 1→347, 2→348, 5→349, 3→350, 6→351, 8..17→352..361, 18→443, 19→470. `0x7E703FB2` uses it.
- `0x7E703FDA` (a hook in the 60-byte records at 0x7E814864) reads the GUI value of 111, 509 or 510 and looks up its flag. If the flag is 0, it sets the mode to GUI 1 (Natural) through `0x7E6FEAE0`, unless the mode in info 24 is in the code→handler hash at 0x7E826CAC (info 24 values 3..115, handler not decoded). The ids 345..470 are the items in the Picture Mode group of the sub-item table (07 §3.2), so these are probably the "show this mode" settings (inferred).

### 1.4 API colorTone enum (verified)
- `0x7E9AB5F1` (jump table 0x7EC0D110) shows that the enum is sequential: 0 NONE, 1 VIVID, 2 NATURAL, 3 FLAT, 4 PORTRAIT, 5 MONOTONE, 6 IFINISH, 7 POPART, 8 TOY_PHOTO (= Pin Hole), 9 SOFT_FOCUS, 10 DAYDREAM (= Pale&Light), 11 GRAINY_FILM, 12 LIGHT_TONE, 13 DIORAMA, 14 CROSS_PROCESS, 15 GENTLE_SEPIA, 16 DRAMATIC_TONE, 17 LIGNE_CLAIR, 18 PASTEL.
- The enum is **not** the mcon GUI value (for example GUI 13 Pin Hole = colorTone 8). The stored-value → colorTone conversion is **`0x7EA766C7`**:
  - It uses the hash at 0x7EC4A864 (keys 1–5, 7, 100–109, 119, 120). Value 6 (Custom) is resolved through info 211 first.
  - Any other value, including 110–118, logs `[ASSERT][CmpSts_RecViewController.cpp]ln.%d setSlideRecViewInfo()` and gives colorTone 0 (NONE).
  - It writes the result to RAM 0x602B0D14 (`0x7E969EDD`). The getter is vtable 0x7EC0F494 slot +256 (`0x7E9CCB2C` → `0x7E969AAA`).
  - It is used for the rec-view and slide information (the name is from strings, inferred). Its other caller is 0x7EA757AC, which stores 0.

## Q2. How the GUI builds the art filter lists

| List | Source (verified) | Entries and order |
|---|---|---|
| Picture Mode menu, plus Live Control / SCP for info 111 | the ROM mcon list of info 111 (19 entries). mcon API: count `0x7E6FCB15`→`0x7E6FF741`, item by index `0x7E6FCAD6`→`0x7E6FEE8E`→`0x7E70726D`, value→index `0x7E6FCACC`→`0x7E6FEE02` | 7 picture modes, then 12 art filters, in the §1.2 order. Labels from the u16 table 0x7EF1F4D6, in display order (i-Enhance, Vivid, Natural, Muted, Portrait, Monotone, Custom, Pop Art … Watercolor), read by `0x7ED3E6C5` with index 1..19 |
| ART shooting mode (the E-PM2 has no mode dial; the mode is chosen on a screen) | **info 281** = tag 0x2891 (u8, MODE). mcon type-1 list at 0x7E849784 (record 0x7E84AEB4, 13 bytes) | internal codes `70, 69, 71, 72, 74, 73, 86, 85, 91, 96, 163, 181, 3`: Pop Art, Soft Focus, Pale&Light, Light Tone, Grainy, Pin Hole, Diorama, Cross Process, Gentle Sepia, Dramatic Tone, Key Line, Watercolor, then **3 = ART BKT**. Verified: `0x7EA951E0` tests info 281 == 3 together with infos 109/279 and logs `FUNC ARTD_ARTBKT ON` |
| ART BKT | info 414–423 → 100–109, 424 → 119, 469 → 120 (coordinator-verified builder 0x7EA7633A / 0x7EA9528D). Each info is a 0/1 flag (mcon records 0x7E84C278…0x7E84C354, raw [0, 1]) | the same 12 filters |

- **What decides inclusion: fixed ROM lists (verified).**
  - No count variable, model check or debug flag selects the entries. The 12 art values are compiled into the mcon raw/GUI arrays (info 111, 509, 510), into the info-281 list, and into the ART BKT info ids.
  - mcon has two runtime override slots at RAM 0x605B4C1C (76 bytes each: id +68, count +70). `0x7E6FFFF5` checks them first.
  - The only writer of those slots that I found is the init routine `0x7E6FFF9F` (it sets id 2000, count 0). I searched only immediate references, so this is incomplete.
- The ART-mode reset check is `0x7E700185`. It maps the code in info 281 to its show flag through the hash 0x7E818CC8 (`0x7E70010D`; it covers codes 69–74, 78–83, 85–88, 91, 93, 96, 97, 163, 164, 181 and 183). If the flag is 0, it resets 281 to **70 (Pop Art)**. Codes 75, 84, 117, 118, 119, 145, 151 and 153 have no flag entry (verified). An unknown code gets the default info 352 (the Pop Art flag) (verified).

### Can a hidden filter (110–118) become selectable?
- **GUI / mcon:** no (verified, §1.2 write fallback). The GUI cannot produce these values.
- **`app Set_CameraInfo <info> <value>` shell** (`0x7E677990`; at 0x7E6780AC it passes both parsed arguments straight to Set_CameraInfo): **yes, it can store any u8 in 0x9481** (verified code path; no range check in Set_CameraInfo). `prmdbg setval` (07 §1.4) can also write the tag. Whether a retail camera exposes these shells (UART) is unknown.
- **If 0x9481 holds 110–118** (consequences verified from the code above; end result inferred):
  - The GUI shows **Watercolor** (read fallback).
  - The rec-view colorTone is NONE, with an assert log.
  - The Exif value has no art entry for 111–118 (coordinator's 0x7E70DC24 result). For **110** the writer has a real case, 0x7E70DE4B, which stores **15** (ExifTool: Pale & Light Color II); the E-P5 writer does the same (0x7E3ECFAA). (A10 2026-11-09)
  - `mov_art` 0x7E6CBFD3 maps 110–118 to the codes 145/75/84/69/117/118/119/151/153.
  - The still path's acceptance (`art_IsSupportType` 0x7E71BC93, `art_chk_type` 0x7E71C075 → `art_chk_type_rec` 0x7E71C0E1) was not re-traced here. (A10 2026-11-09)
  - The next GUI change of picture mode overwrites the value.
- **Not traced (open):**
  - Myset recall (`OlyHfwUserSettingManager::loadCustomSetting` 0x7E9E77E6). If it restores raw bank bytes, it would preserve an injected value, but it cannot create one (inferred).
  - PTP/remote property writes. The Set_CameraInfo callers at 0x7F08xxxx belong to `adj_p15740_p.c` (factory-adjustment PTP); I did not check which ids they write.
- **Corrected:** constant-id writes of info 111 exist, but every one goes through mcon. There are 0 direct prm sets of 0x9481 and 0 `Set_CameraInfo` 0x7E67F882 calls with 111 (07-settings.tsv). But the GUI setSetting 0x7EE01D4E (`setSetting Mode=%d Val=%d`) is called with id 111 at 0x7EDE26EC (value from the table 0x7EFF63EC) and at 0x7EE00E6F/0x7EE00E75 (values 8 and 1, one shared call 0x7EE00E79); the Set_CameraInfo wrapper 0x7E6FCC72 (it calls the mcon setter 0x7E6FEAE0) is called with 111 at 0x7EA807AC, 0x7EA817F6 and 0x7EA81823 (value 1 at the last two); and the mcon setter 0x7E6FEAE0 itself at 0x7E704036 (value 1, the §1.3 reset hook). The gui_set column of 07-settings.tsv (0) misses these. All of them use the mcon GUI→raw conversion, so the conclusion stands: the GUI cannot store 110–118. (A10 2026-11-09)

## Q3. E-PL5 v1.6 and E-P5 v1.8

The bodies were unpacked with `oetool.py unpack` into the scratch folders `u_100_1600` and `u_108_1800`.

Bases (verified): in each body, the mcon record for 111 has its gui[] and raw[] pointers both landing on the matching tables when the base is E-PL5 **0x7E421020** or E-P5 **0x7E101020**. This check uses data pointers, not string pointers. The E-PL5 block 0 has the same size as the E-PM2 block 0 (14,155,712 bytes) but differs in about 9.96 M bytes, because the code is shifted.

| Item | E-PM2 | E-PL5 (identical?) | E-P5 (identical?) |
|---|---|---|---|
| info 111 gui[] / raw[] (76 + 1216 B) | 0x7E83F70C / 0x7E844CC0 | yes: 0x7E840868 / 0x7E845E1C | yes: 0x7E53C2A0 / 0x7E541958 |
| 509 / 510 tables | as 111 | yes | yes |
| composite ids of 111 | {111, 553} 0x7E8186D6 | yes: {111, 553} 0x7E818D2A | **{111, 648}** 0x7E50E7F2 (partner info renumbered, same role inferred) |
| show/hide map (152 B) | 0x7E826AFC | yes: 0x7E827C58 | yes: 0x7E522850 |
| info 281 ART list (13 B) | 0x7E849784 | yes: 0x7E84A8DC (record p1 at 0x7E84C010) | yes: 0x7E5474A5 (p1 at 0x7E548CF8) |
| label table 0x7EF1F4D4 (40 B) | | yes: 0x7EF1FBA0 | yes: 0x7ECEC024 |
| colorTone hash keys and results | 0x7EC4A864 | yes: 0x7EC4BBEC | yes, 2 copies: 0x7E94EA54 / 0x7E94EB54. The returns 1..18 are in the same order (fn near 0x7E77E318) |
| mcon code: 0x7E707147, 0x7E7071EF, 0x7E70726D, 0x7E7070B4, 0x7E70708D, 0x7E6FF788, 0x7E6FED4C, 0x7E703FB2, 0x7E703FDA, 0x7E700185, 0x7E70010D, 0x7E6FEA5F | | same instructions (calls and 32-bit immediates wildcarded). E-PL5: 0x7E707503, 0x7E7075AB, 0x7E707629, 0x7E707470, …, 0x7E70436E, 0x7E704396, 0x7E700541 | same instructions. E-P5: 0x7E3E58AD, 0x7E3E5955, 0x7E3E59D3, 0x7E3E581A, …, 0x7E3E215F, 0x7E3E2187, 0x7E3DE205 |
| `0x7EA766C7` colorTone fn | | same instructions at 0x7EA777C5 | rewritten (other struct offsets, info 211 read through a call), same mapping |
| Set_CameraInfo inner `0x7E67F899` | | same instructions | did not match the signature (not examined) |

**Conclusion (verified for the listed tables and functions):** the three bodies use the same 19-value picture-mode conversion, the same 12-filter ART list (with ART BKT = 3) and the same fallbacks. None of them has a GUI value for 110–118. The model difference is outside this mechanism. I checked only the tables listed, not every byte of each function.

## Open questions
1. What info 553 (tag 0x84B1) is. It is 1 only for Monotone. The ROM defaults (0x9481 = 0, 553 = 0) do not match any entry, so the defaults would read back as Watercolor. Where are the real factory-reset values (0x7E457DA8 or a reset table)?
2. The purpose of the mcon override slots at 0x605B4C1C, and who fills them (if anyone).
3. Does Myset recall or PTP SetDeviceProp write 0x9481 through mcon (validated) or through raw Set_CameraInfo?
4. Is the still path's art check (`art_IsSupportType` / `art_chk_type`) also fine with 110–118? This decides whether an injected value gives an image or an error.
5. The meaning of info 162 (list [76, 77, 89, 90], reset to 79 in 0x7E700185) and of info 280 (the SCN list).
6. Variant I/II selection for each filter (for example tag 0x9161, 20 × u8, info 244–252/322/388–393/661) was not mapped here.

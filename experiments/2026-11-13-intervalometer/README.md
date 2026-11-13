# Interval shooting + time-lapse movie on the E-PM2 v1.6 (2026-11-13)

Goal: enable the dormant interval / time-lapse feature (info 482–486), using the E-PL6 1.4 as the template. The output is a patch spec that is emulator-checked but **not built and not camera-tested**.

- **Labels:** **V** = read in the bytes or run in the emulator; **I** = inferred.
- **Addresses:** E-PM2 v1.6 runtime addresses (base 0x7E421020) unless the E-PL6 is named. The E-PL6 1.4 block 0 has the same base.
- **Specs (all block 0 only, none built). Use v2; the others are kept for reference:**
  - [patches/interval-timelapse-v2.json](patches/interval-timelapse-v2.json): **the current spec** (48 ops, 921 bytes on stock). It is insert + keep-awake + the movie guard, with everything added moved out of the film builds' way. It applies on stock and on the seven-films-6 set. See §12.
  - [patches/interval-timelapse.json](patches/interval-timelapse.json): **replace** Flash RC Mode (5 ops, 14 bytes; the fallback).
  - [patches/interval-timelapse-insert.json](patches/interval-timelapse-insert.json): **insert** the row exactly as the E-PL6 does (43 ops, 626 bytes changed). See §10.
  - [patches/interval-timelapse-insert-awake.json](patches/interval-timelapse-insert-awake.json): insert + the E-PL6 **keep-awake** timer hold (47 ops, 818 bytes changed). See §11.

## Summary
- **Missing on the E-PM2:** only menu wiring, in four places. The interval engine, the guards, panels 628/636/637/638–641, the panel factory entries and all 34 languages' strings are already there and match the E-PL6 (V).
- **Approach, replace spec:** the E-PL6's Time Lapse row goes into the place of **Flash RC Mode** (Shooting Menu 2, last row), and Flash RC Mode loses its menu row.
- **Approach, insert spec:** a 37-row menu matching the E-PL6. In the emulator, every row's help, OK target and value matches the E-PL6 1.4 (V, §10).
- **Keep-awake:** the E-PL6 holds the sleep and power-off timers while a sequence runs (0x7E998F12 and its new callers). Only the `-insert-awake` spec ports this (two trampolines, §11). With the other two specs, set Sleep to Off for tests.

## 1. The menu row

### 1.1 What draws and opens a top-menu row (V)
There are four structures. The E-PL6 changes all four; the E-PM2 has no slack in any of them.

| # | Structure | E-PM2 | E-PL6 1.4 | Who reads it |
|---|---|---|---|---|
| a | Top-menu table: 10-byte records `{u16 item, label, help, kind, param}`, ended by 5 zero words; rows are numbered 1..N globally | 0x7EFFE13C, 36 rows. The terminator at 0x7EFFE2A4 is followed at once by the u16 page-id lists 0x7EFFE2AE / 0x7EFFE2C2 | 0x7EFFF864, 37 rows; row 11 = `{0, 1357, 1358, 0x102, 1}` | builder 0x7EDEBF67, help/DM 0x7EDEC745, 0x7EDECE64 (6 address loads) |
| b | Tab layout in **.data** (ROM image 0x7E8EE88E → RAM 0x602BE3CE): 6 × 20-byte lists of 1-based global rows (12 slots, 0xFF padding), then 6 row counts | tab 1 = 07–0B, counts 06 05 06 0A 03 06 | tab 1 = 07–0C, later tabs +1, counts 06 06 06 0A 03 06 | the same functions; RAM 0x602BE48C = tab, 0x602BE490 = row |
| c | Tab pages 2–7 (page 1's 8-byte child list 0x7EFF8BAC). Each page's 12-byte child list `{u32 panel, u32 info, u32 flag}` gives the panel that OK / right opens (0x7EDEC618 via the record lookup 0x7EDCCA8C) | page 3 (Shooting Menu 2) at 0x7EFF8C38: 13, 14, 15, 16, **(18, 180)**. Page 4's list starts right after the terminator | page 3 at 0x7EFFA324: 13, 14, 15, 16, **(628, 482)**, (18, 180) | OK handler 0x7EDAAFDD → 0x7EDEC618 |
| d | Right-column value per global row: a switch in 0x7EDEC2C0 (getSetting id per row number), then 0x7EE01DDA with the per-row `{value, string}` list pointer table (.data RAM 0x602BE874) | row 11 → getSetting(**180**), list 0x7F0118E4 (Off/On) | row 11 → getSetting(**482**), row 12 → 180; both use the same Off/On list | menu page |

- **What the walker assumes (V).**
  - The builder and the help writer stop on the table terminator, and they index rows only through the .data tab lists and counts (b). No code holds a row count.
  - The builder pages rows by 7 (`div 7`). Tab 1 keeps 5 rows.
  - The row record itself does not name its submenu. The panel comes from the page child list (c).
- **The other code is the same in both bodies (V).** All 300 / 53 / 265 instructions of 0x7EDEBF67 / 0x7EDEC745 / 0x7EDECE64, the page factory 0x7EDCBE97 and the 361 page/panel records (ids, types, flags) are the same after address normalisation. Only 0x7EDEC2C0 and the child lists of pages 3 and 25/26 differ.
- **Inserting a row would cost more (V).** After an insert, every global row number above 10 moves. A constant-shift scan (`results/rowshift-constants.txt`) finds the E-PL6 renumbered `mov/cmp 31..35` in 0x7EDEC2C0 and `mov 33,d0` (→ 34) in 9 panel functions (0x7EDE35AC, 0x7EDE4FBD, 0x7EDFD3A8 …). An insert would also need (a) and (c) moved to free space, the 6 imm32 table loads repointed, and (b) rewritten.

### 1.2 Replace spec: Flash RC Mode's slot (V for the bytes, I for the value judgement; the insert spec is §10)
- **No room:** there is no slack after (a) or (c), and neither table has a size field (V).
- **Row 11 is the right slot.** Flash RC Mode is row 11, so the new row lands exactly where the E-PL6 has Time Lapse. Rows 1–10 and 12–36 keep their numbers, so (b), the row constants and the cursor memory stay valid (V).
- **The value list already fits.** Row 11's value list is Off/On, the same list the E-PL6 uses for its Time Lapse row (V).
- **The cost (I):** Flash RC Mode is the wireless commander for the clip-on FL-LM1 / RC flashes. Few E-PM2 users rely on it, and info 180 keeps its value (it is just not settable from the menu any more).
- **Row 11 is not used elsewhere (V for the scan):** the shift scan found `mov 11` only in 0x7EDEC2C0. The one `cmp 10 → 11` (0x7EDE3131, pages 35–37) is a list size, not a row.

### 1.3 The submenu exists on the E-PM2 (V unless marked)
- **Panels:**
  - Panel 628: type 23 (the same type as RC Mode's panel 18), with children 636 and 637.
  - Panel 637: type 7, a sub-item list (the generic sub-item panel 0x7EDE1E3D). Its children are 638 (483 Frame, type 23), 639 (484 Start Waiting Time, type 39), 640 (485 Interval Time, type 39) and 641 (486 Time Lapse Movie, type 9).
  - All records are the same as on the E-PL6.
- **Factory and code:** the panel-factory hash entries for 628 and 636–641 exist in both bodies (E-PM2 0x7EFE1E7C, 0x7EFE4F24–0x7EFE4F5C). The 638 class code (0x7EE01604…, 437 instructions) and the 628 panel code (0x7EDFF500…) match apart from addresses.
- **Value ranges:**
  - 483: 1..99 (mcon record 0x7E84C5FC, section 10a).
  - 486: [0, 1].
  - 484 and 485: u32 **seconds**. `recordingDone_interval` 0x7EA997E5 multiplies 485 by 1000 for a ms timer when 485 ≤ 90. Above 90 s it uses the RTC next-time path and the camera sleeps between frames.

## 2. Strings (V)
- **All Time Lapse strings are present on the E-PM2:**
  - 1357 "Time Lapse Settings", 1358 help;
  - 1359 "Start Waiting Time", 1360 help;
  - 1361 "Interval Time", 1709 help;
  - 1711 "Time Lapse Movie", 1712 / 1713 Off / On helps;
  - 696 "Frame".
- **All 34 languages:** none of these ids is empty in any language. All ids 0–1969 match the E-PL6 apart from `@Axxx@` glyph codes (the E-PL6 adds ids 1970–1973, EVF Auto Switch).
- **Result:** no string edits are needed. Data: `results/strings-timelapse.tsv`.

## 3. Defaults (V for the bytes, I for the effect)
- **The two bodies match:**
  - MODE ROM default list: E-PM2 0x7E4B40D0, E-PL6 0x7E4B5000.
  - Both have 728 tags, and no tag's default differs.
  - 0xDE11 (482), 0xDE21 (483), 0xDE34 (484), 0xDE44 (485), 0xDE51 (486) and 0xDE64/74/84 (487 next-shot time, 488, 489 frames done) all default to 0 in both.
- **A count of 0 does not block the feature (V; this corrects 10a).**
  - ` IntervalShooting Count ZERO ` (0x7ECD2DC2) tests **489**, the frames-done counter. It means "fresh start", not "blocked".
  - The end test compares 483 == 489 (0x7EA89F39, GUI 0x7ECDA5C8).
- **Risk of the zeros (I):** 483 = 0 would never match, and 485 = 0 gives a 0 ms timer. Stock zeros would therefore be a frame burst with no frame limit.
- **Proposed E-PM2 defaults:**

  | Info | Tag | Record | New default | Bytes |
  |---|---|---|---|---|
  | 483 Frame | 0xDE21 | 0x7E4C3EB4 | 10 frames | data byte 0x7E4C3EB8 (block-0 0xA2E98): `00` → `0a` |
  | 485 Interval Time | 0xDE44 | 0x7E4C3EC4 | 5 s | u32 at 0x7E4C3EC8 (0xA2EA8): `00000000` → `05000000` |

  Keep 484 = 0 (start now) and 486 = 0 (movie off).
- **When the new defaults apply (I):** ROM defaults are used only when the MODE bank is reset. The camera's saved bank (two copies, section 07 §1.3) keeps its zeros until a full reset or a menu edit.

## 4. The E-PL6's extra call, and every functional difference

How the bodies were compared:
- Function by function: normalised disassembly with addresses replaced, paired through 31,037 unique anchors or through the unique log strings both bodies reference.
- Raw outputs: `results/pair-*.txt`.

| # | Where (E-PM2 → E-PL6) | Difference | Needed? |
|---|---|---|---|
| 1 | Menu (a)–(d) above | The extra row / child / value case | **Yes** (V). This is the spec |
| 2 | `startIntervalShooting` 0x7E98849B → 0x7E98948E | The E-PL6 adds `call 0x7E998F12` on the fresh-start branch, after the RealTime/next-time read. **0x7E998F12 = E-PM2 0x7E997E94** (same code, OlyHfwPower): flag 0x602B2074 = 1, `PWROFF TIMER(0)`, `SLEEP TIMER(0)`, flag = 0. It disables the auto power-off and sleep timers. The E-PM2 already calls it from format, erase-all, pixel mapping and other long jobs. It is a power hold, not a bug fix (V code; I purpose) | Robustness (I). Ported only in the `-insert-awake` spec (§11) |
| 3 | Interval sleep-timer selector 0x7E997BD9 → 0x7E998C41 | Mode 1 (482 on, sequence running) and mode 3: the E-PL6 also calls 0x7E998F12. Mode 0 / not running: it also calls 0x7E998E47(0) (= E-PM2 0x7E997DC9, the timer restore; I). The E-PM2 only sets the interval sleep timer (0 or 60001 ms) | Same as #2: the timers are held during the run and restored at the end |
| 4 | Guards 0x7E969C11 / 0x7E969ACE / 0x7E969B43 / 0x7E969BA2, interval state set/get/clear | Same | — (V) |
| 5 | SequencePartsBase interval states 0x7EA98600–0x7EA99A80 (start, end, next time, first shot, shot done, movie, error) | Same (V, 30 functions) | — |
| 6 | Movie maker: `mov_edit_check_param` 0x7E6D493D, MOV_EDIT, `rcvCreateTimeLapseMovieIn_active`, `api_play_Create_TimeLapseMovie` | Same (V) | — |
| 7 | Card full (`cardFull` 0x7E9A9AFA), battery (`shutDown() Power OFF by BATTERY` 0x7ECE01DB, LED), `intervalRemainCount`, wake-up (`CAM_INTERVAL_*` 0x7ECD68D8), `TimeLapseGuard` error sequence 0x7EA95BDF | Same (V) | — |
| 8 | GUI `executeClearIntervalShootingEnd` 0x7ECD2EFA, `receiveSubAppServiceStopReady` 0x7ECDA202 | The E-PL6 also skips / branches on GUI state **10**, which the E-PM2 does not have (EVF auto-switch era) | No (I) |
| 9 | GUI `receiveEndIntervalShootingTimer` 0x7ECDA146 | The E-PL6 adds an AF-lock / zoom-frame restore (`getAflState` 344, `changeZoomStateScrollToFrame*`) | No (I): a magnified-LV nicety |
| 10 | GUI `createTimeLapseMovie` 0x7ECDA530, `receiveEndCreateMovie` / `receiveErrorCreateMovie` 0x7ECDA1A0 / 0x7ECDA1C3 | The E-PL6 sets a **time-lapse-movie guard flag** (RAM 0x602B4B20) to 1 after an accepted movie request (0x7ECDA8C1) and clears it when the movie ends or fails (0x7ECDA4B3, 0x7ECDA4DD). These 3 sites and row 11 are the only users of the flag (V) | **Yes with Time Lapse Movie On** (I; review 2 S2). Ported only in v2 (§12) |
| 11 | GUI `receiveEndMediaMountForEndWait` 0x7ECDA28D | The E-PL6 **tests the same flag** (0x7ECDA5CA) and skips the end check while a movie is being made. The E-PM2 has this handler without the test (corrected: this is not a NULL check, and the reader is not E-PL6-only code) | As row 10 |
| 12 | GUI mode-change 0x7ECD5270 / 0x7ECD5E61 | Same logic. If the 6 date/time fields from the clock getter are all 0, 482 is cleared (V code; "clock" is I) | — (set the clock) |
| 13 | 0x7ECD5D80 and others | Event ids +1 (renumbering) | No |

## 5. Spec ops ([patches/interval-timelapse.json](patches/interval-timelapse.json))
- **Base:** sha256 34d339ac…3e300. Each `expect` carries 4 context bytes on each side.
- **Checked:** `tools/emu/patchblock.py` applies all 5 ops (14 bytes differ in 7 runs, scratch image only) (V).

| # | Block-0 offset (runtime) | Change |
|---|---|---|
| 1 | 0xBDD17C (row record 0x7EFFE1A0) | `0000 0e02 9301 0200 b400` → `0000 4d05 4e05 0201 0100`: label 1357, help 1358, kind 0x102, param 1. Byte-identical to E-PL6 0x7EFFF8C8 |
| 2 | 0xBD7C44 (page-3 child 0x7EFF8C68) | `{18, 180, 0}` → `{628, 482, 0}`, as in E-PL6 0x7EFFA354 |
| 3 | 0x9CB315 (0x7EDEC339) | `2c b4 00` `mov 180,d0` → `2c e2 01` `mov 482,d0`, as E-PL6 0x7EDED1CF |
| 4 | 0xA2E94 (0xDE21 default) | 483: 0 → 10 |
| 5 | 0xA2EA4 (0xDE44 default) | 485: 0 → 5 s |

The .data tab layout (b) needs no change, because the row count of tab 1 stays 5.

## 6. Emulator (V; om-emu, function level, `results/emu-*.txt|json`)
The new cases are in `tools/emu/cases.py`. Each has an independent Python model that reads the image's own tables.

| Case | Entry | Rows | Stock model | Diff vs the spec |
|---|---|---|---|---|
| `menu_help` | 0x7EDEC745 (help id → DM 45, through the .data tab lists and the top table) | 43 (every tab bar and row slot; tab 1 has 6 slots so the E-PL6 fits) | 43/43 | **1 changed:** tab 1 row 4 (global row 11), help **403 → 1358**. 42 identical. Every changed row read a patched byte; 0 flagged |
| `menu_child` | 0x7EDEC618 + 0x7EDCCA8C (the panel that OK opens) | 43 | 43/43 | **1 changed:** tab 1 row 4, panel **18 → 628**. 0 flagged |
| `menu_value` | 0x7EDEC2C0 + 0x7EE01DDA (right-column value) | 74 (global rows 1–37 × value 0/1) | 74/74 | **2 changed:** row 11 reads **180 → 482**; it shows 1371 "Off" / 198 "On" as before. 0 flagged |
| `ivl_guard` | 0x7E969C11 start guard, 0x7E969ACE movie guard | 192 (482 × 4 state inputs × 6 state words) | 192/192 | 0 changed. The guards read **only info 482**: 483–485 and the defaults do not affect them |

- **Guard results:** both guards return 1 exactly when 482 = 1 and no blocking state is set (RecView/recording, multiple-exposure flag, state bits 1–3; for the movie guard, the time-lapse-movie state).
- **Not emulated:** the full menu builder 0x7EDEBF67 (drawing and many callees), and the label read. The label comes from the same record, so it is checked by the byte parse in §1 only.
- **Skipped rows:** `menu_value` skips the IS row (kind 0), because its .data value-list pointer is NULL and the formatter faulted reading address 0 (V; the same in both bodies). It also skips the date row (kind 0x106), whose case calls an object through a vtable.
- **Both bodies:** the menu cases pick their addresses from the image (E-PM2 or E-PL6 profile) and follow relocated tables. Results: `results/emu-replace-*`, `results/emu-insert-*`, `results/compare-bodies*`.

**What only the camera can test (I):**
- the row draws and is selectable, and panel 628 / 637 open;
- the editors show and store sane values;
- whether the old MODE bank keeps the zeros;
- the shot loop, sleep and wake above 90 s, movie creation, and every timing, power or card interaction.

## 7. Camera test plan (the user flashes; keep stock v1.6 to restore)
1. **Before flashing:** set Date/Time. Set the Custom Menu **Sleep** option to **Off** (menu location I). Use a full battery, an empty card, and a cheap lens or body cap with MF.
2. **Menu row:** Shooting Menu 2 should show Drive, IS, Bracketing, Multiple Exposure, **Time Lapse Settings  Off**, and no Flash RC Mode. Check the help text (INFO). Check another language if wanted.
3. **Submenu:** open the row. Expect Off / On (636) and the settings list (637): Frame, Start Waiting Time, Interval Time, Time Lapse Movie. Note the values. If they show 0 or blank, do Reset (Full) or set them by hand (Frame 10, Start Waiting 0, Interval 5 s, Movie Off).
4. **Short run:** P mode, JPEG, set On, half-press and full-press. Expect 10 frames at about 5 s, a frame counter on screen, and the end at 10. Check that the file count is 10.
5. **Movie:** set Time Lapse Movie On, run 10 frames at 2 s, and check for an MJPEG 720p MOV after the stills (mov_edit accepts only that format).
6. **Cancel paths:** start a run, then press MENU, the shutter, and the mode dial. Each must end the sequence cleanly. Also check that Multiple Exposure turns interval Off (mcon interlock, 10a §1.1).
7. **Long interval:** Interval 120 s, 3 frames. The camera should sleep between frames and wake to shoot (RTC path).
8. **Sleep timer:** with Sleep = 1 min, a 75 s interval and 3 frames.
   - With `-insert-awake`, all 3 frames should be taken with no sleep in between (the timers are held), and after the run the normal 1-min sleep should come back.
   - With the other specs, this tests whether the missing hold matters.
9. **Card full:** a nearly full card, 99 frames at 1 s. It should stop with a card-full message and no hang.
10. **Restore:** flash stock v1.6. Flash RC Mode returns.

## 8. Risks
- **Shutter count:** every frame is a mechanical shutter cycle (I). 99 frames at 1 s is 99 actuations. Keep tests short. The 10-frame default limits accidents. Stock zeros (no frame limit, 0 s interval) are the worst case and are why ops 4–5 exist.
- **Battery:** long runs with Live View between ≤ 90 s frames drain the battery. The battery shutdown path is the same as the E-PL6's (V). Low battery mid-run: does the movie get made? Untested.
- **Overheating:** long ≤ 90 s runs keep the sensor and LV powered (I). The E-PM2 has no fan or heat warning found for this path. Watch for a temperature warning.
- **Card full:** the `cardFull` handling and the error sequence are the same as the E-PL6's (V). The movie needs room after the stills (I).
- **Live View:** frames ≤ 90 s keep LV on. The E-PL6's extra zoom-frame restore (#9) is absent, so a magnified LV may not come back (I).
- **Sleep / power-off:** the E-PM2 lacks the E-PL6 timer hold (#2, #3). With Sleep ≠ Off, the normal sleep may interrupt a 61–90 s interval run (I). Workaround: Sleep = Off, or use the `-insert-awake` spec (§11).
- **Mode dial:** the mode-change path 0x7ECD5270 clears 482 when the clock check fails (V). Dial changes during a run go through `changeModeDialForIntervalWait` (the same as the E-PL6). Movie / ART / SCN behaviour is untested.
- **Lost feature:** Flash RC Mode has no menu row while patched (V).
- **Overlay:** all patched code and tables beyond 0x7E881000 load as overlays. The emulator maps the whole block, so it does not test overlay loading (I).

## 9. Corrections to section 10a (not edited; for the next map pass)
- 10a §1.2 says "No panel lists 628 as a child in either body". That is **wrong**: the E-PL6 page-3 12-byte child list has (628, 482). The 8-byte panel-tree parse misses the tab pages' 12-byte lists (V).
- 10a §1.2 links ` IntervalShooting Count ZERO ` to the 483 default. That is **wrong**: 0x7ECD2DC2 reads **489** (frames done) (V).
- 10a §1.3 says "the E-PL6 extra call … may be a fix". It is the power/sleep timer hold 0x7E998F12 (V code, I purpose).

## 10. Insert spec: the E-PL6 wiring reproduced (V unless marked)
**Is the free space loaded at run time? Yes.**
- Block 0 is not loaded whole. Usr1 at 0x7E504D50 reads flash 0x80B6A800 into 0xBECCB800 (taken to be the uncached view of 0x7ECCB800: I) through SYSFMEM 0x7E451306. The size is `0x7F034000 − 0x7ECCB800` = 0x368800. Next it runs the segment-3 constructor walker 0x7E44B6B0(3).
- For both Usr1 segments, flash = 0x802C0020 + block-0 offset. So block-0 bytes 0x7ECCB800–0x7F033FFF are what lands in RAM. The menu tables and the GUI code are in this range; 0x7F034000 and above are not loaded.
- **Space used:** 0x7F033B7C–0x7F033FFF is 0xFF (1,156 B). It follows the constructor table 0x7F033AC8–0x7F033B7B, which the walker takes by count (`mov 180,d2`), not up to a terminator.
- An any-alignment scan of block 0 finds no imm32 and no data word in that range (`results/refscan.txt`). The spec leaves 0x7F033B7C–0x7F033BFF untouched and uses 0x7F033C00–0x7F033E12.
- **References to the old tables (same scan):**
  - top table: exactly the 6 imm32 loads (all of the base; no offset into the table is used);
  - page-3 list: only its page record's pointer 0x7EFFA4B0;
  - two unaligned hits at 0x7EFA0A19 / 0x7EFA5EC1 are inside numeric tables (coincidence).

| Part | E-PM2 edit (generated by `scripts/mkspec_insert.py` from the stock bytes; each asserted equal to the E-PL6) | E-PL6 1.4 counterpart |
|---|---|---|
| (a) top table | 37 rows + terminator at **0x7F033C00**, byte-identical to E-PL6 0x7EFFF864. 6 imm32 → 0x7F033C00 (0x7EDEC0A5, …0FA, …121, …7A6, 0x7EDECF42, 0x7EDED085). The old table stays, now unreferenced | its own table |
| (b) .data tab layout (ROM 0x7E8EE8A2) | tab 1 = 7–12, tabs 2–5 +1, tab-1 count 5 → 6: equal to E-PL6 | 0x7E8EE8CA |
| (c) page 3 list | {13, 14, 15, 16, (628, 482), 18} + terminator at **0x7F033D80**; record pointer 0x7EFFA4B0 → it | 0x7EFFA324 |
| (d1) .data row value lists (RAM 0x602BE874; **37 slots, not 40**: corrected in §12) | Off/On inserted at row 11, rows 11–38 → 12–39. Non-zero rows {3, 5, 6, 7, 10, 11, 12, 14, 33, 34, 35} and every list's content equal the E-PL6 | RAM 0x602BE89C (41 entries) |
| (d2) value switch 0x7EDEC2C0 | the constants for rows 13, 31, 32, 33 and 34 +1 (10 sites). The old row-11 case at 0x7EDEC335 becomes `jmp 0x7F033DE0`, a **51-byte cave** that maps row 11 → getSetting(482) and row 12 → getSetting(180), then returns to the formatter tail 0x7EDEC432 or the next case 0x7EDEC34A. The 16 bytes after the jmp are left, unreachable (the only branches into the block target its start) | the case inserted in line, 0x7EDED1CB–0x7EDED1F2 |
| (d3) panel row arguments | 20 × `mov 33,d0` → 34: the formatter / reverse formatter calls in the 10 monitor-adjust panel functions (0x7EDE35AC … 0x7EDFD725) | 34 at all 20 |
| (e) defaults | 483 = 10, 485 = 5 s, as the replace spec | — |

**Row constants (`results/rowshift-constants.txt`, `scripts/rowsites.py`, `scripts/fmtsites.py`):**
- **Mirrored (V):** every `k → k+1` the E-PL6 made in menu code (31 sites = (d2) + (d3)).
- **Not mirrored, because they are not top-menu rows (V code, I meaning):**
  - CA sub-app command ids (0x7ECDF738, 0x7ECE0004, 0x7ECE078C, 0x7ECE1AB1);
  - dial events in SS_BTSEND / SS_DPS (0x7ED8479E, 0x7EDA21C3);
  - an SS_SPC state (0x7EDC02B7);
  - a page-141 list size (0x7EE00464);
  - a pages 35–37 list size (0x7EDE3131/32DA, `cmp 10 → 11`).
- **The Custom Menu group sizes in .data (RAM 0x602BE390) also differ:** B 4→5, C 6→7, D 17→18, J 5→6. These are the E-PL6's extra Custom Menu items (page 25/26 children 651, 659, 130, 173). They are not ported.
- **.data check:** an aligned u16 diff of the whole .data image (`results/data-diff.txt`) finds only these `+1` runs: the Custom Menu sizes, plus 2 single words (0x8F5A, 0xA6D9) that look like pointer halves. The byte-packed tab layout and the pointer lists are covered above.
- **Constants the E-PM2 needs but the E-PL6 did not change:** none found.
  - All 14 formatter calls and all 12 reverse-formatter calls in the E-PM2 have constant row arguments 33 or 5, or a computed one (0x7EDEA29B uses another, id-indexed table). They map one-to-one to the E-PL6's 14 + 12 sites.
  - The .data value lists are read only by the two formatters.
  - The tab-layout bytes and the top table are read only by the 3 identical page functions.

**Emulator (`results/compare-bodies.txt|json`, `results/compare-bodies-summary.txt`):** the three menu cases ran on four images: stock, replace, insert and the **E-PL6 1.4 block 0**.

| Case | Rows | insert ≠ E-PL6 | replace ≠ E-PL6 | Model errors (all 4 images) |
|---|---|---|---|---|
| `menu_help` (help id per tab/row) | 43 | **0** | 26 (rows 12+ keep the E-PM2 numbering) | 0 |
| `menu_child` (OK target) | 43 | **0** | 1 (no RC row) | 0 |
| `menu_value` (setting + string per global row) | 74 | **0** | 52 | 0 |

- **Flash RC Mode at its new place (insert):** tab 1 row 5, global row 12. Help 403, OK opens panel 18, value getSetting(**180**) → Off/On. This is the same as the E-PL6.
- **Stock vs insert** (`results/emu-insert-*`): `menu_help` 27 changed and `menu_child` 2 changed, all toward the E-PL6 values; `menu_value` 54 changed; `ivl_guard` 0 changed.
  - emurun flags 10 + 4 rows "reads patched bytes but unchanged". These are rows 1–10, read from the relocated copy, whose values match. That is expected for a relocation, not an error.
  - The cave ran inside the case's allowed ranges.
- **Not emulated:** the 20 panel constants (d3). They are checked only by bytes against the E-PL6's 20 sites.

**The two specs compared:**

| | Replace (`interval-timelapse.json`) | Insert (`interval-timelapse-insert.json`) |
|---|---|---|
| Ops / bytes changed | 5 / 14 | 43 / 626 |
| Code changes | 1 immediate | 6 table pointers, 30 immediates, a 5-byte jmp and a 51-byte code cave |
| Data changes | 1 row, 1 child entry, 2 defaults | new 37-row table and page list in padding, .data tab layout and value lists, 1 record pointer, 2 defaults |
| Menu result | 36 rows; Time Lapse replaces Flash RC Mode | 37 rows, equal to the E-PL6 1.4 row for row (emulator) |
| Flash RC Mode | no menu row | kept, row 12 |
| Extra risks (I) | the lost RC row | code executing from the rodata padding (the GUI segment is one RAM copy; no NX is known on this CPU, but not proven); more sites to get wrong (the panel constants are not emulated); the saved menu cursor for tabs 2–5 may land one row off after flashing (DM state) |
| Restore | stock v1.6 | stock v1.6 |

**Extra camera checks for the insert spec:**
- every tab draws, with its row count (Shooting Menu 2 = 6 rows);
- Flash RC Mode toggles;
- Setup ▸ Monitor adjust (`@A032@`) still shows and changes brightness / colour: this is the (d3) panels;
- Language and Rec View show their values;
- Custom Menu entries open the right pages.

## 11. Keep-awake port (`interval-timelapse-insert-awake.json` = the insert spec + 4 ops) (V unless marked)
**What the E-PL6 does (re-checked in its disassembly):**
- **`startIntervalShooting` 0x7E98948E:** the extra `call 0x7E998F12,[],4` is at 0x7E989552.
  - It comes right after `movhu (32,sp),d0 / cmp d3,d0 / bne` (the RTC read 0x7E68CF5D succeeded), and before `clr d0; mov d0,(20,sp)` and the seconds conversion.
  - It is the only added call: the call lists are otherwise identical, 32 vs 33.
- **Selector 0x7E998C41, by branch:**

  | Branch | E-PL6 calls |
  |---|---|
  | mode 0, or mode 1 with 482 = 0 or 489 = 487 = 0 | `isst(0)`, then `restore(0)` (0x7E998E47) |
  | mode 1 with 489 ≠ 0 or 487 ≠ 0 | `hold` (E-PM2 only returns) |
  | mode 2 | unchanged: `isst(0 or 60001)` |
  | mode 3 | `isst(0)`, then `hold` |
  | other | the assert print |

**The E-PM2 port:** trampolines go in the verified padding, after the insert spec's cave. The call and return encodings below were checked with our objdump.

| Site | Hook (5 bytes) | Trampoline |
|---|---|---|
| 0x7E98855F (after `bne 0x7E9885CA`) | `dc` jmp 0x7F033E20; the 6th displaced byte at 0x7E988564 is left and unreachable (no branch targets 0x7E988560–64) | **0x7F033E20, 18 B:** `call 0x7E997E94,[],4` (the frame the E-PM2's own callers use) → the 6 displaced bytes exactly (`clr d0; mov d0,(20,sp); mov sp,a0; add 20,a0`) → `jmp 0x7E988565` |
| 0x7E997BD9 (selector entry) | `dc` jmp 0x7F033E40; the old body is unreachable | **0x7F033E40, 177 B:** E-PL6 0x7E998C41 re-assembled with E-PM2 callees: getter 0x7E6FCC91 `[],4`; `isst` 0x7E997C67 `[d2],16`; `restore` 0x7E997DC9 `[d2,a2],16`; `hold` 0x7E997E94 `[],4`; the stock assert print (0x7EBF074D/075D, line 721). Calls are `dd` d32 and branches rel8; it ends with `ret [],16`, the frame all 9 callers use |

**Register and flag safety of T1 (V for the code; MN103 call convention I):**
- The call clobbers d0, d1, a0, a1, MDR and the loop registers, exactly as the E-PL6's own call at the same point does.
- After the hook, d0 and a0 are set by the displaced code, a1 at 0x7E988565, and d1 at 0x7E988581. LIR/LAR are reloaded by `setlb` at 0x7E988583. The flags come from `add 20,a0`, as in stock.
- d2, d3, a2 and a3 are callee-saved. T2 replaces a whole function, so no state crosses its hook.

**Emulator:** `results/compare-awake.txt|json` and `results/emu-awake-*`. The new cases are `ivl_selector` and `ivl_start`; every callee is stubbed by role and logged in call order.

| Case | Rows | stock (model) | patched vs E-PL6 1.4 | stock vs patched |
|---|---|---|---|---|
| `ivl_selector` (modes 0–4 × 482 × 489 × 487) | 40 | 40/40 | **call sequence identical in 40/40** (the E-PL6 also matches the model, 40/40) | 24 changed: the extra `restore` / `hold` only, in the branches listed above; 16 identical (all of mode 2 and mode 4) |
| `ivl_start` (guard, busy, release, RTC error, validity, ≤ / > 90 s, NULL object, results) | 14 | 14/14 | **calls and return value identical in 14/14**. The frame differs only in body-specific return addresses and string pointers | 8 changed, each by exactly one `hold` after the RTC read on the fresh-start branch. Return values and the whole frame (84 B + saved registers) are identical in 14/14 |

- **Menu cases:** they give the same results as the insert spec.
- **Not tested here:** whether the held timers come back after a run on the camera (restore happens in mode 0, as on the E-PL6); timing; sleep/wake above 90 s.

**Remaining risk (I):**
- two more code edits running from the rodata padding;
- if a run ends through a path that never calls the selector with mode 0, the timers stay held until the next restore (the E-PL6 has the same design);
- power-off is held for the whole run, so the battery drains faster on long runs.

## 12. v2 after the two reviews (`interval-timelapse-v2.json`) (V unless marked)
Reviews: [review-1-memory.md](review-1-memory.md), [review-2-code.md](review-2-code.md). v2 is the insert + keep-awake spec with the fixes below. The three earlier specs are unchanged.

### 12.1 B1: a new home for everything added
- **The collision (V, `scripts/specscan.py`).** `seven-films-5` (on the camera as seven-films-6) writes 0x7F033B7C–0x7F033F7B. The insert specs wrote 0x7F033C00–0x7F033EF0. So `-insert` and `-insert-awake` **cannot be combined with the films**, and built alone they would remove the films.
- **New place:** the segment-2 padding, **0x7ECB0BA4–0x7ECB0EE2** (831 B used; free up to 0x7ECB0FFF).

| Check | Result |
|---|---|
| 0xFF in stock | 0x7ECB0888–0x7ECB0FFF is all 0xFF |
| 0xFF after the film set | The film set ends at 0x7ECB0B9D (remap7b-code 0x7ECB0888 + 760 B, seven-movie-1 0x7ECB0B80 + 30 B). 0x7ECB0B9E–0x7ECB0FFF is 0xFF in the scratch-built films block 0. v2 starts at 0x7ECB0BA4, so its 4 context bytes are 0xFF on both bases |
| Loaded at boot | Usr1 0x7E504BF2–0x7E504C18: SYSFMEM read, source 0x80794800, destination 0xBE8F5800, size `0x7ECB1000 − 0x7E8F5800`. This is before the segment-3 load, so segment-3 GUI code can always read the table, and the two segment-2 hooks no longer jump into a later segment (review 2 S1, review 1 §7.1) |
| Unreferenced | An any-alignment scan of 0x7ECB0888–0x7ECB1000 (and the 0xBE… alias) finds only the copy-end constant 0x7ECB1000 |
| Code already runs there | remap7b-code puts code at 0x7ECB0888 (`mov imm,a1; bra; … call 0x7E56B732`). It is in every seven-films build, which are camera-tested (docs/camera-log.md) |
| Every spec in `patches/` | None of the 8 current specs touches the range or any v2 op window (0 overlaps, including the .data and menu-table ops). **Three superseded specs in `patches/history/` do use the padding** (film-vision3-250d-pl1, slots7-neutral, slots12-code: 0x7ECB0888–0x7ECB0F3F), so v2 cannot be combined with those. Only 0x7ECB0F40–0x7ECB0FFF (192 B) is free of every spec ever written, which is too small. `results/specscan-v2.txt` |

- **Layout:**

  | Address | Size | Contents |
  |---|---|---|
  | 0x7ECB0BA4 | 380 B | top table |
  | 0x7ECB0D24 | 84 B | page-3 list |
  | 0x7ECB0D78 | 51 B | value-switch cave |
  | 0x7ECB0DB0 | 18 B | T1 |
  | 0x7ECB0DC8 | 177 B | T2 |
  | 0x7ECB0E80 / E98 / EB0 / EC8 | | movie-guard trampolines |

  All 6 table pointers, the record pointer and the 7 `jmp` hooks are regenerated (`scripts/mkspec_v2.py`), and the trampolines are re-assembled at the new addresses.
- **Review 2 N2 stays (I).** An unused tab slot (0xFF) would index base + 2,544, which is 0x7ECB1594, in the unloaded gap. As in stock and the E-PL6, the cursor is bounded by the tab counts, so the slot is not read.
- **Applies on both bases (V, `tools/emu/patchblock.py` into scratch):**
  - stock + v2: block-0 sha256 `d8c35ce3…2c327f69`, 921 bytes changed;
  - the seven-films-6 specs + v2: `8992f2c2…693d28ec`.

### 12.2 S2: the time-lapse-movie guard flag
- **E-PL6 sites (re-derived; the flag address occurs exactly 4 times in its code):** set at 0x7ECDA8C1, clear at 0x7ECDA4B3 and 0x7ECDA4DD, test at 0x7ECDA5CA.
- **E-PM2 flag: RAM 0x602BE878**, the row-1 slot of the value-list pointer table.
  - The table is read only by the two formatters, indexed by row.
  - No call passes row 1: the indices are 3, 5–8, 10–12, 14 and 33–35 (`results/fmtindex-v2.txt`).
  - No code immediate equals 0x602BE875–0x602BE87F.
  - Its .data initial value is 0, so it starts cleared at every boot, like the E-PL6's.
- **Hooks (each replaces a call, which the trampoline re-issues with the same frame):**

  | Function | Hook → trampoline | Trampoline |
  |---|---|---|
  | `createTimeLapseMovie`, accepted path | 0x7ECDA56C → 0x7ECB0E80 | print call; `mov 1,d2`; `mov d2,(flag)`; `jmp 0x7ECDA5AE` |
  | `receiveEndCreateMovie` | 0x7ECDA1B2 → 0x7ECB0E98 | print call; `clr d0`; `mov d0,(flag)`; back to 0x7ECDA1B9 |
  | `receiveErrorCreateMovie` | 0x7ECDA1D5 → 0x7ECB0EB0 | the same; back to 0x7ECDA1DC |
  | `receiveEndMediaMountForEndWait` | 0x7ECDA2A7 → 0x7ECB0EC8 | `call 0x7ECD50DE,[],0`; `mov (flag),a1`; `cmp 0,a1`; if set, `jmp 0x7ECDA2B3` (the `ret`); else back to 0x7ECDA2AC |

  After each hook, d0 / a0 / a1 are set again by the following code, as on the E-PL6.

### 12.3 S3 and the notes
- **Description:** rewritten. The "Not ported" sentence is gone, the "rows 11-38" wording is fixed, and it says that the defaults are not E-PL6 parity.
- **Value-list table = 37 slots** (rows 0–36; 0x602BE908 is another variable). §10 said 40.
  - v2 edits only slots 12–35 (96 B at ROM 0x7E8EED64).
  - The older specs also rewrote slots 36–39 with the same zero bytes, which was harmless.
- **Bound check (`scripts/fmtindex.py` on the films + v2 image):** all 25 call sites of 0x7EE01DDA / 0x7EE01E8C pass a constant. The largest is **35**, which is slot 0x602BE900 and in bounds. Row 37 (Firmware) has no value case, as on the E-PL6.

### 12.4 Emulator on five images (`results/compare-v2*.txt|json`, `results/emu-v2-*`)
Images: stock, films, stock + v2, films + v2, E-PL6 1.4. Model errors: 0 in every case on every image.

| Case | Rows | stock+v2 ≠ E-PL6 | films+v2 ≠ E-PL6 | films ≠ stock | stock ≠ v2 |
|---|---|---|---|---|---|
| `menu_help` | 43 | 0 | 0 | 0 | 27 |
| `menu_child` | 43 | 0 | 0 | 0 | 2 |
| `menu_value` | 74 | 0 | 0 | 0 | 54 |
| `ivl_selector` | 40 | 0 | 0 | 0 | 24 |
| `ivl_start` (calls + return) | 14 | 0 | 0 | 0 | 8 (one `hold` each); the frame is identical to its base in 14/14 |
| `ivl_movie_guard` (new: 4 create paths, end, error, mount × flag 0/1) | 10 | 0 | 0 | 0 | 4: flag set on an accepted request, cleared on end and on error, end check skipped while set |

- **`ivl_guard`:** 192/192 unchanged.
- **emurun flags:** `emurun diff` still flags 10 + 4 menu rows as "reads patched bytes but unchanged". These are rows read from the relocated table, with the same values.

### 12.5 Test plan and risk changes for v2
- **Base:** flash v2 **on top of the film set** (the seven-films-6 specs + v2). Restore = seven-films-6. Check first that the seven films still work (one photo in a film entry).
- **Step 5 (movie):** the guard is now in. Still do it last, with a card that can be lost. Also remove and re-insert nothing during movie creation: the media-mount path is the one the flag protects, and it is only emulated.
- **Step 8 (Sleep = 1 min, 75 s interval):** expected to run without sleeping, as in §11.
- **Remaining (I):**
  - all added code runs from the segment-2 padding, as remap7b-code's does;
  - the flag shares a table slot that only a row-1 formatter call could read, and none exists;
  - no spec has an `expected_sha256` until a build is camera-tested.

## 13. Camera result, and frames above 99 (2026-11-13)

| Date | Build | Result |
|---|---|---|
| 2026-11-13 | `build/seven-films-6-interval.BIN` = the seven-films-6 specs + `interval-timelapse-v2.json` | **Works** (user report: "It works!", interval shooting runs). Not yet reported: which steps of §7 / §12.5 passed (movie, cancel paths, > 90 s sleep, Sleep = 1 min, card full) |
| 2026-11-13 | `seven-films-6-interval-240.BIN` = the films + `interval-timelapse-v2.json` + `interval-frames-240.json` | **"Seems to work"** (user report; still testing; which steps passed is not yet reported) |

**Can the frame count go above 99? Yes, to 240, with data edits only:** [patches/interval-frames-240.json](patches/interval-frames-240.json) (6 ops; not built, not camera-tested). This replaces the earlier "not with a safe patch" answer, which missed that the editor can compose a number label. Evidence: `results/framecap.txt`, `results/emu-frames240-*`, `scripts/mkspec_frames240.py`.

### 13.1 Where 99 came from (V)

| Layer | Stock | In the spec |
|---|---|---|
| Storage | prm 0xDE21 is **one u8** (default record 0x7E4C3EB4). 489 "frames done" is u32 (0xDE84) | Unchanged. 240 fits. 999 would need a wider tag, which changes the saved MODE bank and Myset layout |
| mcon value list | record 0x7E84C5FC: 99 × u8 (1..99) at 0x7E849F56, clamped, packed between the lists of 482 and 486. Step function 0x7E7074B5 | New 128-byte list at **0x7E4C9100**; the record gets the pointer and total 128 |
| Frame editor (page class of lists 148 / 638) | descriptor 0x7F00C6EC `{483, count 99, …, items 0x7F00ABD0}`; 99 items of 28 B `{0, kind, u16 args[5], 2000, value, 0xC0, 0xC5}`, values 99 down to 1, kind 2 = label string "99f" … "1f" | 128 items at **0x7EBF1100**; the descriptor gets count 128 and the pointer |
| Value shown in the Time Lapse Settings list (0x7EDE2192, table 0x7EFF0460: 762 rows of 32 B `{info, value, kind, args…}`) | 99 rows `{483, v, 2, label}`; a value with no row shows nothing | The row of value 99 becomes kind 4 |

### 13.2 How a row is drawn, and composition (V)
- **Kinds:** kind 2 = one label string. **Kind 4 = number + unit string.** The stock Custom Self-timer "Timer" editor (list 632, info 475) uses it for "1 sec" … "30 sec": items `{kind 4, args (N, 247 "sec")}`. 149 stock editor items are kind 4.
- **List page shortcut:** in the list page, the first kind-4 row of an info prints the **current value** with that row's unit, whatever the row's own value is (0x7EDE2375; info 474 is excluded).
- **No per-value string is needed** for a composed label. Unit string 0 is the empty string in all 34 languages, so the new labels read "100" … "240". There is no stand-alone localized "f" unit to reuse: the stock labels are whole strings per language ("99f", "99Bill.", "模式99").
- **Editor type 39 is not usable for a count.** The Start Waiting Time / Interval Time editors (639 / 640) are table kind 12, which the code handles only for info 484 / 485 and formats as h:mm:ss through a date helper.
- **List length limit:** the editor keeps its row index in a byte and **sign-extends it before the ×28 item lookup** in the key handler (`extb d1; udf00 28,d1` at 0x7EE017BB and 0x7EE017FC). Index 128 would address item −128. So the limit is **128 rows**, not 240. The look-up of the stored value (0x7EDC81A8) and the draw slot use the index unsigned.
- **Design (preference 2):** 1–99 by 1 with the stock labels, then **100, 105, … 240** = 99 + 29 = 128 rows (the last index is 127).

### 13.3 Block 1 (not needed; for the record, V)
- **Layout:** a directory of 16-byte records; one blob per language with `{u32 ptr_array, u32 ptr_array_end}`, a UTF-16LE NUL-terminated pool, then 1,970 pointers (runtime base 0xBFF3D000), then a footer.
- **Pool:** each id has its own string: no two ids share an offset, and there is no slack between strings (checked for English, Japanese and German).
- **Labels are not language-neutral:** "1f" … "99f" have 20 different spellings.
- **`tools/build.py`** has only an equal-length `utf16-replace-all` for block 1. New strings would need a "rebuild language blob" op (new pool + pointers + directory sizes).

### 13.4 The new homes (V)

| Range | Why it is safe | Other specs |
|---|---|---|
| 0x7E4C9100–0x7E4C917F (mcon list) | 0xFF padding 0x7E4C90CA–0x7E4C97FF at the end of the range the **reset stub** loads (0x7E430000–0x7E4C9800, review 1 §0). The only window into it is the copy-end constant. The record is boot-part data, so its list does not depend on a Usr1 segment | untouched by every spec in `patches/` and `patches/history/` |
| 0x7EBF1100–0x7EBF1EFF (editor items, 3,584 B) | Inside the unreferenced `sdk` shell name list 0x7EBF1090–0x7EBF3BAC (class A in `experiments/2026-11-13-reclaim-space`; my scan again finds no window into the part used). Segment 2, loaded before the GUI segment. Cost: that debug-shell name text is overwritten | untouched by every spec |

- **Applies on:** stock, and the film set + v2 (scratch build of block 0, sha256 `7d460c4c7288…`).
- **Overlaps:** 0 with all specs, including v2.

### 13.5 Emulator (V)

| Case | Rows | Stock | Patched |
|---|---|---|---|
| `frames_step` (0x7E7074B5 on the record's list: next / previous, clamp) | 46 | 46/46 vs model | 99 → next = **100**; 100 → 105; 105 → previous 100; 235 → 240; 240 → next 240 (clamp). A stored value that is not in the list (0, 101–104, 250) steps to 240 / 235. Rows up to 98 are unchanged (flagged only as "reads patched bytes": the list moved) |
| `frames_editor` (0x7EDC81A8: item of the stored value, for every stored byte 0–255) | 256 | 256/256 | each of the 128 values finds its own item (10 → index 118, label 1821 "10f"; 100 → index 28, kind 4 number 100; 240 → index 0). Any other stored byte opens on index 0 = 240, as stock opens on 99. The largest index is 127 |
| Menu, selector, start, movie-guard and guard cases on films + v2 + frames | 416 | — | all still match their models |

### 13.6 Is 240 safe end to end?

| Reader | Finding |
|---|---|
| prm save / restore, Myset | one byte; 240 < 256 (V) |
| End test | 483 == 489 on u32 getter results (0x7EA89F39, 0x7ECDA5C8) (V) |
| Movie maker | The request passes 489 as the frame count (0x7EA9938E). MOV_EDIT is a start / per-frame "make" / end stream, and it sizes its table from its argument (0x7E6D4B82, 2 × n). No `cmp 99/100` in the request, API or MOV_EDIT ranges (V for the scan; I that nothing else caps it). At the 10 fps the E-PL6 documents (external), 240 frames is a 24 s clip, far below the 4 GiB limit |
| Other caps (clamp other than the mcon list, on-screen counter digits, remaining-shots check) | **Not traced.** A counter that shows only 2 digits would be cosmetic |

### 13.6b Independent review (review-4-frames240.md, 2026-11-13): no blocker

- **S1 (I):** the "number + unit" row kind (4) is not used in stock by *this* editor's page class (list 638 shares its class with list 148, kinds 3 and 8; Custom Self-timer's list 632 is another class), and no stock kind-4 row has an empty unit. So the labels "100"…"240" are **untested on this screen**. If they draw wrongly the fault is cosmetic: confirm stores the item value, not the label. Camera test 1 is the gate.
- **S2 (V):** 128 is the mcon error value for u8 lists, so no list value may be 128. The list has 125 and 130; the generator now asserts it.
- **S3 (I):** the movie maker's frame-count scaling and the on-screen counter above 99 are not proven by reading. Add a 240-frame run with Time Lapse Movie On.
- **Confirmed (V):** nothing stores an index (editor, prm and Myset hold the raw value); the value list at 0x7E4C9100 is loaded unconditionally by the reset stub and is the right home (every getter scans it from segment-1 code); 128 rows is the exact maximum; no overlap with any spec; no code touched.
- **Do not** make a frame value "unavailable" in a later patch: the page object holds only 39 row structures and that path writes past them.

### 13.7 Camera tests for `interval-frames-240`
1. In the Frame editor, scroll from 99 up: 100, 105 … 240. The labels show as plain numbers; scrolling stops at 240 and at 1. 1–99 are unchanged.
2. Choose 240, leave and re-enter the menu: the list shows "240"; power-cycle and check again. Check that 99 shows "99" and 98 shows "98f".
3. Run 105 frames at 1 s: it stops at 105, with 105 files. Note what the on-screen counter does past 99.
4. With Time Lapse Movie On, run 120 frames at 1 s: check the clip plays and its length (about 12 s at 10 fps).
5. Save and load a Myset with Frame = 240.

- **Risks (I):** the empty unit string may draw differently from "sec" (spacing); an untraced clamp may pull 240 back to 99.
- **Shutter wear:** 240 frames is 240 actuations.

## 14. Interval Time = 0 (2026-11-13): not safe, no spec

**Verdict: unsafe (it would not shoot back to back; the sequence would stop after a frame). No spec was written.**

- **Where the 1 s minimum is (V).**
  - The Interval Time editor (page 640) is a subclass of the Start Waiting Time editor (page 639). Both are h:mm:ss, with per-field min/max bytes at 0x7EFE22D0 / 0x7EFE22D3, and all-zero is reachable in both.
  - Page 640 adds the helper 0x7EDFF71D "h = m = s = 0?". Its commit slot (vt slot 37, 0x7EDFF702) **skips the store when the value is zero**. Its enter / up / down slots set a state word (this+550 = 4) while it is zero.
  - Page 639 commits zero, so Start Waiting Time 0 is allowed.
  - 484 and 485 have no mcon value list, and no start guard reads 485 (the guards read only 482; `startIntervalShooting` reads 487).
- **What the engine does with 485 = 0 (V).**
  - `recordingDone_interval` 0x7EA997E5 calls the interval timer (this+428, vt+92) with `(14, 485 × 1000 ms)` for every value ≤ 90. It has **no zero case**.
  - **The same call with 0 ms is the engine's "timer stop".** At 0x7EA95F40 it is logged as `startErrorSequenceCtrl Timer Stop`; `rcvEndIntervalShootingIn_active` (0x7EA98EDE) uses it too.
  - The first frame is different: `startIntervalShooting_First` 0x7EA99881 tests 484 == 0 and shoots directly instead of arming a 0 ms timer. So Olympus handled 0 explicitly where they allowed it.
- **Failure mode (I for the last step).** With 485 = 0, after frame 1 the engine stops its own timer and waits for a timer event that never comes. No frame 2. The sequence stays open until MENU / shutter / mode dial cancels it. With the v2 keep-awake the sleep and power-off timers are held meanwhile, so the camera stays on.
- **Emulator** (`ivl_shot_done`, stock code in the films + v2 + frames image; `results/run-ivl_shot_done.txt`): the timer argument is captured through a real store function.

  | 485 | Timer call |
  |---|---|
  | 0 | `(14, 0)` |
  | 1 | `(14, 1000)` |
  | 2 | `(14, 2000)` |
  | 90 | `(14, 90000)` |
  | 91, 120 | no timer call; next-time path |

  The call order is identical for 0, 1 and 2 (`get 485`, `set 487 = 0`, timer, post-shot helper). Only the argument differs, and 0 is the stop code. 7/7 rows match the model.
- **Other bodies.**
  - E-PL6 1.4: the same editor class and the same engine function (both compare equal after address normalisation), so the same 1 s minimum.
  - E-M10 / E-PL7: not traced (a different menu system; their engine was not compared).
- **What a real "0 = back to back" would need:** new engine code in `recordingDone_interval` that, for 0, posts the shoot event directly the way the first-frame path does, plus the two editor edits. That changes the state machine while the previous frame may still be writing. The sequential drive modes already do this job.
- **If it is ever wanted:** on a donor body, set 485 = 0 through the debug shell (`prmdbg setval 0xDE44 0`), start a sequence and watch whether frame 2 comes. Expect it not to.

## Files
- `patches/interval-frames-240.json`: Frame up to 240, on top of v2 (§13); generator `scripts/mkspec_frames240.py`.
- `patches/interval-timelapse-v2.json`: the current spec (§12).
  - generator: `scripts/mk_v2_gen.py` → `mkspec_v2.py` (+ `guard_part.py`);
  - checks: `scripts/specscan.py`, `scripts/fmtindex.py`.
- `patches/interval-timelapse.json`: the replace spec.
- `patches/interval-timelapse-insert.json`: the insert spec (ops carry a `_why` note; build.py ignores it).
- `scripts/` (insert spec):
  - `mkspec_insert.py`: builds the insert ops;
  - `refscan.py`: reference scan;
  - `rowsites.py`, `fmtsites.py`: row constants;
  - `datadiff.py`: .data diff;
  - `compare_bodies.py`: runs cases on several images (`--cases=`);
  - keep-awake: `mkspec_awake.py`, the insert generator + `awake_part.py` (trampolines and a small MN103 assembler).
- `scripts/`: helpers. Run them with `python3 -I`; they use the scratch block copies.
  - `extract.py`, `langs.py`: block and language extraction;
  - `dis.py`, `cmp.py`, `side.py`: disassembly and side-by-side;
  - `fnmatch.py`, `pairlib.py`, `pair.py`, `rangediff.py`, `strpair.py`, `rowshift.py`: cross-body pairing;
  - `pages.py`: page and child lists;
  - `modedef.py`: MODE defaults;
  - `mkspec.py`: builds the ops from the stock bytes.
- `results/`: emulator diffs (`emu-*.txt`, `emu-*.json`), function pairing (`pair-*.txt`), `rowshift-constants.txt`, `mode-defaults.txt`, `page-child-lists.txt`, `strings-timelapse.tsv`.
- `tools/emu/cases.py`: the new cases `menu_help`, `menu_child`, `menu_value` and `ivl_guard`.

# Level gauge for the E-PM2: how the E-PL6 does it, what the E-PM2 has, first camera step

Date: 2026-11-14. Status: desk research and one draft patch spec. Nothing was flashed.

Labels: **V** = verified (read from the firmware bytes, or run in the emulator). **I** = inferred.
**U** = unknown; each one has a probe in §9.

Addresses: E-PM2 = firmware 1.6 block 0, runtime base 0x7E421020. E-PL6 = firmware 1.4 block 0, same
base. A "setting" is a numbered camera setting (the firmware calls it "info"; `getSetting(id)`).
A "panel" is one menu screen; each has a record and a list of child panels.

## 1. Short answer

1. **The E-PM2 already holds the whole level gauge** (**V**): accelerometer driver and task, the
   roll/pitch call, the calibration call, the `LevelCtrl` interface, the live-view screen code, the
   setting (273) that enables the screen, its Off/On value records, the rule table that lets the INFO
   button reach the screen, and the texts. All the code is the same as in the E-PL6, instruction for
   instruction.
2. **What is missing is one menu row** (**V**): the row "Level Gauge" in Custom Menu → Info Settings →
   LV-Info. It is absent in two tables. This is the same kind of gap as the interval timer had.
3. **Draft spec, step A**: 3 data edits, 56 bytes replaced in place, no new bytes, no code
   (`specs/level-gauge-step-a-lvinfo-row.json`). It applies on stock and on the pinned build, passes
   the free-space check, and in the emulator the stock menu code builds the same 4-row LV-Info list as
   the E-PL6.
4. **Not proven at the desk** (**U**): that the gauge graphics are in the E-PM2's block 1 (I found no
   sign that they are missing, §5.3), and that the factory stored level offsets in this body. Step A
   on the camera answers both.
5. Calibration ("Level Adjust", Custom Menu K) is a second missing menu row. It is step B (§8).

## 2. Material and method

- E-PM2: `build/map/`, `build/blocks/…block0.bin`.
- E-PL6 1.4 (model E112): decoded blocks from an earlier session (the interval work used the same
  file, `OLY_E_112_1400_0000_0000.BIN`). A function database was built in scratch with
  `python3 tools/fwmap.py --fw /tmp/scratch/level/pl6/PL6.BIN --base 0x7E421020 --out /tmp/scratch/level/pl6 build`
  (74,837 functions).
- Pairing: `../2026-11-14-focus-peaking/scripts/pair.py`. Result (`results/pairing-summary.txt`):
  **60,187 pairs, 58,642 identical after normalising** (addresses and large numbers replaced).
- Scripts written here (`scripts/`): `difflist.py` (pairs that differ, donor-only functions),
  `panels.py` + `paneldiff.py` (the 361 menu panel records and child lists), `rowtable.py` (sub-item row
  table), `datawalk.py` (walks two data regions in step and prints every insert, delete and change;
  words that are addresses in both bodies count as equal), `immfn.py`, `near.py`, `onlyblobs.py`,
  `imgres.py` (block-1 image table), `mkspec_step_a.py`, `emu_step_a.py`.
- GitHub sweep (`gh search code` for `api_user_Get_Slope_Roll_Pitch`, `LevelCtrl::getSlope`,
  `EVT_REC_DISP_SLOPE`, `PER_SLOPE olympus`; `gh search repos` "olympus level gauge firmware",
  "olympus firmware accelerometer"): no hit. The local Olympus repos have no level-gauge notes.

### Which donor: E-PL6, not E-P5

| | E-PL6 1.4 | E-P5 1.8 |
|---|---|---|
| Pairs with the E-PM2 | 60,187 | 36,912 |
| Identical after normalising | 58,642 | 21,940 (focus-peaking notes) |
| Same body hardware | yes | no (5-axis stabiliser, other board) |
| Level-gauge functions | all identical to the E-PM2 (§4) | not compared; not needed |

The E-PL6 gauge code is already in the E-PM2 byte for byte (apart from addresses), so nothing has to be
ported from any body. The E-P5 has one more thing, a gauge in the viewfinder at half-press (texts
"Half Way Level", "Level Disp"). Those texts are not in the E-PM2 or the E-PL6 (**V**). That variant
would be a real port and is not part of this work.

## 3. How the level gauge works (E-PL6 = E-PM2 code)

All addresses are E-PM2. Every function in this section is paired with an identical E-PL6 function (**V**).

### 3.1 Sensor, driver, task

| Piece | Address | What it does | Label |
|---|---|---|---|
| Accelerometer driver `per_acc` | strings 0x7E4C4190… | 3-axis chip, "ACC: Who am I?" check | V (hardware note) |
| Task PER_SLOPE | body 0x7E469FD2 (task table word 0x7E439970) | Loop: while the run byte 0x6041A0D2 is 1, read the accelerometer (0x7E4583BF), compute the state (0x7E46A094 → byte 0x6041A0CF), and on every 12th sample post the "slope changed" event (0x7E46A0D1, 0x7E46A10C). Else wait for an event flag | V |
| Start / stop | `api_user_Start_Slope_Event` 0x7E68EC99 → 0x7E469DB0 (run byte = 1, set flag); `api_user_End_Slope_Event` 0x7E68ECB2 | The shooting sequencer starts it at standby (0x7EA88C71, 0x7EA89436, debug text "Start_Slope_Event") | V |
| Roll / pitch | `api_user_Get_Slope_Roll_Pitch` 0x7E68ECCB → 0x7E469E05 | returns roll[2], pitch[2], state | V |
| Calibration | `api_adj_Set_Slope_Adjust(mode, rotate)` 0x7E676261 → 0x7E469F16 → 0x7E45937A | mode 0 = reset, 1 = set zero at the current position, 2–4 = factory steps. Returns x, y, z, temperature | V for the calls; where the offsets are stored is U |
| Debug command | 0x7E46A395 ("slope init ok!", "per slope adj strct x:", "readall adj for digitallevel") | shell access to the same calls | V |

### 3.2 Middle layer

| Piece | Address | What it does | Label |
|---|---|---|---|
| `OlyHfwOpeLevel::getSlope` | 0x7E9783C8 | calls Get_Slope_Roll_Pitch; gives vertical, horizon (units 0.1°), body state (orientation 0–5), reliability | V |
| `OlyHfwOpeLevel::calibration` / `reset` | 0x7E9782AF / 0x7E97858C | Set_Slope_Adjust(1, rotate) / (0, rotate) | V |
| `LevelCtrl` interface | getter 0x7E9C4DC8; names table 0x7E8E16BC: startLevel, endLevel, getSlope, reset, calibration, getMaxSlope | what the GUI calls | V |

### 3.3 The setting and the INFO button

| Fact | Evidence | Label |
|---|---|---|
| Setting **273** = "LV-Info: Level Gauge", Off/On. Stored as tag 0x30A1 in the MODE bank, one byte, default 0 | E-PL6 row table (§4); `sections/07-settings.tsv`; value records 0x7EFF4280 (0 → text 1371, 1 → text 198) | V |
| The other LV-Info settings: 244 (Histogram), 245 (Highlight&Shadow), 246 (Image Only), and 669 (no menu row) | row table 0x7EFF0028…; rule table below | V (669's meaning I) |
| The live-view display mode is a setting with these values: 2 = histogram, 15 = highlight&shadow, 13 = multi-exposure overlay, **14 = level gauge** (also 3, 4, 16) | camera application 0x7ECD3F56: it reads setting 28 and starts the matching service | V |
| Which modes the INFO button can reach is a rule table: 32 rules, one per combination of settings 244, 245, 246, 669, 273. Each rule maps the 7 mode values. With 273 = 1 the rule keeps 14; with 273 = 0 it maps 14 → 4 | rules 0x7E823A6C–0x7E823C6C, conditions 0x7E82311C…, lists 0x7E823640…; **all 33 rules and lists are the same in both bodies** | V |
| That this rule table belongs to setting 28 (`MODE_RECINFO`) | the values match the camera-application switch | I |
| INFO key handler | `pressInfoKey` 0x7ECDC3AC (reads setting 28) | V |
| On mode 14 the camera application calls `LevelCtrl::startLevel` with the callback `levelCtrlCbk` 0x7ECD42AB and sets bit 8 of 0x605EFD9C. `stop…` 0x7ECD4112 ends it | 0x7ECD3FD1, 0x7ECD40C7 | V |

### 3.4 Drawing

| Piece | Address | What it does | Label |
|---|---|---|---|
| Screen data function | 0x7ED15989 (function table word 0x7EEFE668) | calls getSlope; rounds both axes to whole degrees; writes a 10-byte record at 0x605F624E: display variant 2–5 (reliable) or 6–9 (not reliable), by orientation; per axis a colour state (2 when the axis is 0, else 3) and a bar position 0–18 (9 = centre, limits at ±10°) | V |
| Second data function | 0x7ED15B13 (table word 0x7EEFE66C) | writes bytes 0x605F624F–52 of the same record | V (meaning U) |
| Data model | slot 68, 10 bytes (written by 0x7ED16143 when the record changes) | the screens listen to this slot | V |
| Rec-view variant | 0x7ED9EAD6, 0x7ED9EC01 | same, with a threshold table at 0x7EFD1D20: −9.5°, −8.5° … +9.5° in 0.1° units (20 values, identical in both bodies) | V |
| So the gauge is two bars (horizontal and vertical axis), 19 positions each, 1° per step, "level" state when the rounded value is 0 | from the two functions | V for the numbers, I for the look (green at level) |
| The widgets and images that show slot 68 | panel layout data; not decoded | U |

## 4. E-PL6 ↔ E-PM2 match table

| Piece | E-PL6 | E-PM2 | Result |
|---|---|---|---|
| PER_SLOPE task and driver | 0x7E46AEBE, 0x7E46B2C2 | 0x7E469F91, 0x7E46A395 | identical |
| `api_user_Get_Slope_Roll_Pitch` | 0x7E68F470 | 0x7E68ECCB | identical |
| `api_adj_Set_Slope_Adjust` | 0x7E6768BC | 0x7E676261 | identical |
| `OlyHfwOpeLevel` getSlope / calibration / reset | 0x7E9793B9 / 0x7E9792A0 / 0x7E97957D | 0x7E9783C8 / 0x7E9782AF / 0x7E97858C | identical |
| Camera application: start/stop of the display services, `levelCtrlCbk`, `pressInfoKey` | 0x7ECD428E, 0x7ECD4346, 0x7ECD43FF, 0x7ECD444A, 0x7ECD45E3, 0x7ECDC6DA | 0x7ECD3F56, 0x7ECD400E, 0x7ECD40C7, 0x7ECD4112, 0x7ECD42AB, 0x7ECDC3AC | identical |
| Screen data functions | 0x7ED16377, 0x7ED9F0FD | 0x7ED15989, 0x7ED9EAD6 | identical |
| Sub-item menu code (list builder, visibility test, 15 functions) | 0x7EDE2C3A–0x7EDE3C3A | 0x7EDE1E3D–0x7EDE2E3D | identical |
| Display-mode rule table (33 rules) | 0x7E82508C… | 0x7E8239FC… | same bytes |
| Level thresholds | 0x7EFD322C | 0x7EFD1D20 | same bytes |
| Setting 273: storage tag, default, value records | – | tag 0x30A1; records 0x7EFF4280 | present (the interval notes checked that all 728 tag defaults are equal) |
| Panel records 203 (Level Gauge picker), 173 (Level Adjust), 198 | present | present (0x7EFFB0F4, 0x7EFFBDEC, 0x7EFFB004); panel factory cases at 0x7EDCC718 | same |
| Texts | – | 866 "Level Gauge", 160 "Level Adjust", 478 "Calibrate the level gauge.", 847 "It adjust the 0 level to the current position.", 223 "Reset", 749 "Adjust" | present; ids 0–1969 are the same in both bodies |
| **Sub-item row "LV-Info / Level Gauge"** | row at 0x7EFF160C (table 0x7EFF0AA4, 197 rows) | **absent** (table 0x7EFEF4FC, 196 rows) | missing |
| **Child entry (panel 203, setting 273) of panel 192** | list 0x7EFFA93C, 4 entries | list 0x7EFF9224, **3 entries** | missing |
| **Custom-menu row "Level Adjust"** | item record at 0x7EFF9A1E `{160, 2213, 0, 3, 478, 0, 1, 9}`; child (173, 2213) in the custom-menu list | **absent**; the K group has items 0, 1, 2, 4, 5 (3 is left out) | missing |
| "EVF Info Settings" (panel 594: settings 446–449, one of them "Level Gauge") | rows and list present, in no menu | rows 0x7EFF03FC–0x7EFF0438 and list 0x7EFFA244 present, **in no menu** | unreachable in both |

No function with a level, slope or LV-Info string differs between the bodies. `results/gui-data-walk.txt`
is the full list of data differences in the GUI data (170 items) and `results/hfw-data-walk.txt` in
the middle-layer data (245 items).

## 5. What is missing, and how big it is

### 5.1 The LV-Info row (step A)

Two tables, both without a free slot (**V**):

1. **Sub-item row table** 0x7EFEF4FC: 196 records of 20 bytes
   `{u16 panel, u16 title text, u32 setting, u32 2, u16 7, u16 1, u16 row text, u16 0}`, ended by a zero
   panel. The E-PL6 has the extra record `{192, 1646, 273, 2, 7, 1, 866, 0}`.
   The code (12 address loads in 0x7EDE1E96, 0x7EDE2192, 0x7EDE2BD6) walks the table from the first
   record to the terminator and takes every record whose panel number matches (**V**, read at all
   sites; e.g. the loop 0x7EDE21F4–0x7EDE2618). So a panel's records do not have to be adjacent.
2. **Child list of panel 192** 0x7EFF9224: `{u32 panel, u32 setting}` × 3, then zeros, then at once the
   list of panel 193. The E-PL6 list has a fourth entry (203, 273).

Panel 594 ("EVF Info Settings") has 4 row records and a 4-entry child list, and no page or panel
lists it as a child in either body (**V**: `results/panel-child-lists-diff.txt` and the full dump of the
361 records). The draft spec re-uses these bytes. No free space is needed.

Alternative, if panel 594 must stay intact: move the whole row table (197 × 20 + 20 = 3,960 bytes) to a
free data area and change the 12 address loads, and put a 40-byte child list in free space.

### 5.2 Level Adjust (step B)

One 16-byte record in the custom-menu item table (0x7EFF7E82, 77 rows, no free slot) and one 8-byte
entry in the custom-menu child list (0x7EFF8E4C, 78 entries, shared by pages 25–34 and others). The
E-PL6 inserted both, and it has shifted constants in the custom-menu page code (pairs
0x7EDE9ACF, 0x7EDE9C38, 0x7EDE9F56 differ only in small numbers). This is the same kind of work as the
interval row insert: about 2 KB of copied tables in a data area, re-pointed loads, and the row
constants. Not traced in detail yet. A smaller form exists: put the Level Adjust record and child
entry **in place of** one K-group row (for example Eye-Fi) in a build that is used once for
calibration. The fields 6 and 7 of the item record are not decoded, so this needs a desk check first.

### 5.3 Graphics (U, with evidence)

- Blocks 2 and 3 are identical in both bodies (**V**). Block 1 (texts, fonts, images) is not: the
  E-PM2's block 1 is the E-PL5's (same hash), the E-PL6 has its own.
- Block-1 entry 0 holds the images and a table of pointers, one per image id: 3,049 ids in the E-PM2,
  3,056 in the E-PL6 (**V**, `scripts/imgres.py`). Ids 0–2808 line up one to one. The E-PL6 adds ids
  2810–2815 (about 20 KB each) and moves one image; it drops one glyph (this is why its texts use
  glyph codes one lower).
- The added images are used by a table in the rec-view data (E-PL6 0x7EFD1078, 160 bytes, a third
  group next to two existing groups of image sets 0x4F6–0x501 and 0x885–0x88A). The existing groups
  are sets of large overlay images selected by a mode key. So the new images are a third set of the
  same kind of overlay (**I**: grid overlays for another display), not gauge parts.
- The GUI data walk shows no E-PL6-only block of layout data for the gauge. The level tables near
  0x7EFD1578–0x7EFD1D48 are the same except one E-PM2 pair (0x7EFD1D14: an E-PM2-only item gets state 3
  in display modes 3, 14 and 21, state 2 otherwise; the E-PL6 has 0 for both). That pair shows the
  E-PM2 build was compiled with mode 14 as a valid mode (**I**).
- I did not decode the panel layout format, so I cannot name the image ids of the gauge bars.

Result: no evidence that an image is missing (**I**: present). The camera shows it in step A.

### 5.4 Texts

No new text is needed for steps A and B. All ids exist in all 34 languages. No block-1 rebuild.

## 6. Steps

| Step | Proves | Changes | The user should see |
|---|---|---|---|
| **A** (draft spec ready) | the menu row works; the INFO button reaches the gauge; the gauge draws; the sensor path is alive; the factory offsets are sane | 3 data edits, 56 bytes in place | §7.3 |
| **B** | calibration from the menu | Level Adjust row in Custom Menu K (§5.2) | "Level Adjust" with Reset / Adjust; after Adjust the gauge reads level at the current position |
| **C** (only if A shows a blank or wrong gauge) | which part fails | a probe that writes the 5 results of `Get_Slope_Roll_Pitch` to a card file (stock file routines 0x7E5C52DC / 0x7E5C5339 / 0x7E5C5308, about 80 bytes of code in a free area, hooked on the half-press event) | a text file with numbers that change when the camera tilts |

Step C is not written. It is needed only if step A fails in a way that does not explain itself.

## 7. Step A: the draft spec

`specs/level-gauge-step-a-lvinfo-row.json` (generator `scripts/mkspec_step_a.py`). It is **not** in
`patches/` and not in a build description.

### 7.1 What it changes

| Op | Address (block-0 offset) | Stock bytes | New bytes | Meaning |
|---|---|---|---|---|
| 0 | 0x7EFF0424 (0xBCF404), 20 B | `52 02 df 05 c0 01 00 00` + 12 B | `c0 00 6e 06 11 01 00 00` + the same 12 B | row record: panel 594 / title 1503 / setting 448 becomes panel 192 / title 1646 / setting 273. The rest (`2, 7, 1`, text 866 "Level Gauge") stays. The result equals the E-PL6 record |
| 1 | 0x7EFFA244 (0xBD9224), 32 B | (607,446) (608,447) (609,448) (610,449) | (200,244) (201,245) (204,246) (203,273) | panel 594's child list becomes the E-PL6's child list of panel 192 |
| 2 | 0x7EFFB040 (0xBDA020), 4 B | `24 92 ff 7e` | `44 a2 ff 7e` | panel 192's record points to that list |

25 bytes differ from stock. Panel 594 loses one row and its child list; no menu reaches it.

### 7.2 Checks done

| Check | Result |
|---|---|
| `uv run epm2mod apply SPEC -o /tmp/scratch/step-a-alone.BIN` | applies on stock; sha256 `071403882cc1e9f056b5cc6e45ecad293b67330b7267fdd3aab9f3e2aa35338f` |
| the same after the nine specs of the pinned build | applies; sha256 `3e7f793ea74b21dab19c61eac33fe1f818d9c627e4fa522a2551ea62fc32c7f6`. (The nine specs alone give the pinned sha256 `01837f96…`, so `apply` reproduces the build tool.) |
| `python3 tools/freespace.py check` (pinned specs + this spec) | PASS, 0 FAIL: "no byte added in a free area (3 block-0 byte ops, all edits of existing content)" |
| Emulator (`scripts/emu_step_a.py`, `results/emu-step-a.txt`): the stock list builder 0x7EDE2192 run for panels 191, 192, 193, 594 on stock, on stock + spec, on pinned + spec and on the E-PL6 image | panel 192: stock gives 3 rows (texts 844, 842, 845; settings 244, 245, 246). **With the spec: 4 rows, texts 844, 842, 845, 866, settings 244, 245, 246, 273, children (200,244) (201,245) (204,246) (203,273): equal to the E-PL6.** Panels 191 and 193 do not change. Panel 594 has 3 rows left |

Not checked, because the emulator runs single functions: the picker panel 203, the INFO cycle and
the screen. These run stock code that is the same as in the E-PL6.

### 7.3 On the camera

For the person who flashes. The build must be made by `tools/make_firmware.py` from a build
description that adds this spec to the pinned list, and the flash logged in `docs/camera-log.md`.

1. MENU → Custom Menu → D (Disp/PC) → Info Settings → LV-Info. **Expected:** four rows: the histogram
   icon, Highlight&Shadow, Image Only, **Level Gauge**. The first three keep their values.
2. Open Level Gauge, choose On, leave the menu.
3. In P mode, press INFO several times. **Expected:** one of the screens shows two bars, one for
   horizontal tilt and one for front/back tilt. Tilt the camera: the marks move, about 1° per step,
   up to ±10°. Hold it level: the bar shows the level state (green on the E-PL6).
4. Turn the camera to portrait: the gauge follows.
5. Half-press, take a photo, record a short movie: all as before.
6. Check that Histogram and Highlight&Shadow still appear in the INFO cycle when they are On.
7. Menu regression: Custom Menu → D → Info Settings → the two other lists (playback Info, Settings)
   open and look as before.

How to read the result:

| Result | Meaning | Next |
|---|---|---|
| Gauge shows and follows the camera | the feature works with 3 data edits. Check the zero against a real level | step B if the zero is off |
| Row is there, INFO never shows the gauge | the rule table's owner is not the INFO cycle of this body, or another gate exists | desk: trace `pressInfoKey` → 0x7ECDC82D and the mode step |
| Gauge screen appears but bars are blank, grey or wrong pictures | images or layout missing in block 1 (§5.3), or reliability is 0 | step C; then compare block-1 images by id |
| Bars shown but stuck, or far off | sensor data or factory offsets | step C, then step B |
| LV-Info list broken or the camera freezes in the menu | my reading of the row walk is wrong | flash the pinned build; no setting was changed |

To go back: flash the pinned build. Note (**I**): setting 273 is kept in the camera's settings. The
stock code honours it. If Level Gauge is On when the pinned build is flashed back, the gauge may stay
in the INFO cycle. Set it Off first, or use a full reset, if that is not wanted.

## 8. Step B: Level Adjust (not written)

Goal: the E-PL6's Custom Menu K row "Level Adjust" (panel 173, setting 2213, label 160, help 478).
The panel code is there (0x7EE00535 calls the LevelCtrl interface). Work: the two tables of §5.2 and the
row constants of the custom-menu page code, by the method of the interval insert
(`../2026-11-13-intervalometer/NOTES.md` §10). The data area 0x7EBF1090–0x7EBF3BAD already holds
camera-tested table data (the 240-frame rows at 0x7EBF1100–0x7EBF1F00); about 7 KB of it is free.

## 9. Real risks and unknowns

Risks with evidence:

1. **A wrong reading of the row walk would break the LV-Info list, or every sub-item list.** The row
   table is read by all sub-item lists (Picture Mode, Button Function and others). The spec changes
   one record at the end of the table and leaves the record count and the terminator as they are. The
   emulator ran the real builder on four panels. A freeze in a menu was recoverable by a card update
   each time (`docs/feasibility.md`).
2. **Panel 594 becomes wrong.** It is in no child list (**V**). A path that opens it by number from code
   was not found, but a search for a constant cannot prove that none exists (the number 594 is also a
   text id). If such a path exists it is for an external viewfinder. With a viewfinder attached, check
   the menus once.
3. **Missing gauge images** (§5.3). Effect: a wrong or empty gauge screen. One press of INFO leaves it.
4. **The gauge stays enabled after going back** (§7.3). This is a setting, not a firmware change.

Unknowns and the probe for each:

| Unknown | Probe |
|---|---|
| Are the gauge images and layouts in the E-PM2's block 1? | step A, check 3 |
| Did the factory store level offsets in this body? | step A: compare the gauge with a real level. Fix: step B |
| Where the calibration offsets are stored | desk: read 0x7E45937A (called by 0x7E469F16) |
| Does the rule table 0x7E8239FC belong to setting 28? | step A, check 3 (if INFO reaches the gauge, yes) |
| What setting 669 is (fifth key of the rule table, mode 13) | desk: who sets tag 0x28A1 |
| Fields 6 and 7 of the custom-menu item record | desk, before step B |
| Does a viewfinder path open panel 594? | camera with a VF-2/3/4 attached, or desk: callers of the panel-show call with a variable panel number |

## 10. Effort (honest)

- Step A: ready. One flash, ten minutes of checks.
- Step B: about one day of desk work (the interval insert is the pattern) and one or two flashes.
- Step C: half a day, only if step A fails.
- The E-P5's viewfinder half-press gauge: not planned; a real port.

## 11. Files

| Path | Contents |
|---|---|
| `specs/level-gauge-step-a-lvinfo-row.json` | draft spec for step A |
| `scripts/mkspec_step_a.py` | writes the spec from the stock bytes |
| `scripts/emu_step_a.py` | the emulator check |
| `scripts/panels.py`, `paneldiff.py`, `rowtable.py` | menu panel records, child lists, sub-item rows |
| `scripts/datawalk.py`, `difflist.py`, `immfn.py`, `near.py`, `onlyblobs.py`, `imgres.py` | comparison helpers |
| `results/emu-step-a.txt` | emulator output |
| `results/panel-child-lists-diff.txt` | every child-list difference between the bodies |
| `results/subitem-rows-diff.txt` | the three row-table differences |
| `results/gui-data-walk.txt`, `results/hfw-data-walk.txt` | all data differences in the two regions |
| `results/pairing-summary.txt` | pair counts |

Note for tool users: `tools/fwmap.py --fw X.BIN --out DIR build` rewrites `DIR/blocks/X.BIN.block0.bin`
from `X.BIN` when `X.BIN` is newer. Give it the decoded block as `X.BIN` and copy the same file to the
cache path afterwards. Nothing was written under `build/`.

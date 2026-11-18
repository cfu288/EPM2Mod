# Look editor from menu rows: stock pickers, limits, cost (2026-11-18)

Question: can an in-camera look editor be made from Custom Menu rows, each a number -7..+7, that edits the film
simulation in use, with live view following?

Labels: V camera-verified, E emulator-checked, R read in code or bytes, I inferred, U unknown.

Scratch (git-ignored): `out/scan_desc.py` (stock list scan), `out/mkdemo.py` (demo spec), `out/setlog.mjs`,
`out/emu/s*/` (screenshots).

## Short answer

- A -7..+7 picker needs **no new text**. Stock item kind 3 prints a signed whole number ("+7", "±0", "-3") with
  stock glyphs. Shown in the emulator on a real row (E).
- Each row needs its own setting **and** its own list panel. The picker writes the setting named in the panel's
  descriptor (E). Only a few dormant setting/panel pairs are known. That is the blocker for 15 rows.
- Recommended: **two rows**. "Look Edit" picks the control (15 names), "Value" is -7..+7. Code swaps the value in
  and out. It needs 2 setting/panel pairs, not 15.
- Code: about 450-600 B (I). Free: 679 B proven code + 3,047 B segment-3 data (`docs/code-space-map.md`). It fits,
  tightly.
- Live view: the menu covers the whole screen (E). The edit is in the tables at once (V for a load from the menu),
  so the user sees it after leaving the menu. No live view while the picker is open.

## 1. Stock pickers with signed values

List descriptors: table 0x7F00D710, `{u16 list id, u16 0, u32 descriptor}`. Descriptor `{u16 setting, u16 count,
u32, u32, u32 items}`. Item, 28 B: `{u8 0, u8 kind, u16 a, u16 b, u16 c, u32 d, u32 2000, i32 value, u16 192, 0,
u16 197, 0}` (R).

Item kinds (R; kind 3 also E):

| Kind | Shows | Fields |
|---|---|---|
| 2 | one text | a = text id |
| 3 | sign and whole number | b = sign (0 "+", 1 "-", 3 "±"; 2 = no sign, used for shutter times), c = number |
| 8 | sign and fraction | a = numerator, b = denominator, d = sign (1 +, 2 -) |
| 4 | number and unit | a = number (unsigned in every stock list), b = unit text id |

Stock lists with signed values (R):

| List | Descriptor | Setting | Items | Values |
|---|---|---|---|---|
| 474, 475, 476 | 0x7F00C63C, C64C, C65C | 274, 275, 276 (s16; Exposure Shift by metering mode, I) | 13, kinds 3 and 8: +1, +5/6 ... ±0 ... -1 | 256 ... -256, steps of 42.67 |
| 289, 316 | 0x7F00C03C, 0x7F00C0BC | 300 i-Enhance Effect, 305 Custom Effect | 3, kind 2: High / Standard / Low | 1, 0, -1 |
| 151 | 0x7F00C53C | 143 (s8) | 4, kind 2: Off / Low / Standard / High | -2 .. 1 |
| 148 | 0x7F00BF6C | 174 (s16) | 40, kinds 3 and 8: shutter times | APEX x 256 |

Not list pages: Picture Mode Contrast / Sharpness / Saturation (lists 285-314, settings 117-127, 181-183, 205-207,
297-299) use another descriptor, a bar: `{setting, 122, 2, 631, 5 steps, pairs}` with pairs (2, 400) ... (-2, 0) at
0x7F00C964 (R). Only -2..+2. Whether 15 steps work there, and whether a Custom Menu row can open it: U.
Exposure compensation and Highlight&Shadow have no list descriptor (R). Highlight&Shadow Control (text 1516,
settings 319/320, prm 0x9192) has 8 GUI read sites, no writer with a constant id and no menu row: no route to it on
this body was found (R). Whether its screen shows live view: U.

No stock list has 15 steps. A copy is needed: 15 kind-3 items (420 B) and, for the row's value text, a value -> text
list of the same kind (16 x 24 B = 384 B; table 0x7F014614, one word per panel). Both can be shared by every row.

## 2. Acting on a change, and live view

| Fact | Label | Source |
|---|---|---|
| Rows run no code. Code polls in the GUI-state hook (0x7ECDF6E4): the GUI calls the state setter at every key, also in the menu (state 0x57xx) | V | card-looks-3/4, log-menu |
| One poll: `prm_get(tag, 0, 0)` and a compare: about 16 B per setting; a table-driven loop about 30 B plus 2 B per setting | R | `mkspec_logmenu.py` T_GUI |
| Setting a row's value from code: the GUI's setSetting 0x7EE01D4E (d0 setting, d1 value) | V | Load Looks status |
| The work runs in task USRTEST_A, started from the hook | V | card-looks |
| Table writes plus the forced refresh change the next photo and live view at once | V | card-looks design 9.2.1, 10.3 ("live view cyan without half-press") |
| The Custom Menu and its picker cover the whole screen | E | screenshots `out/emu/s5/`; the camera's menus are opaque too (I) |
| Live view while the picker is open | no (I) | follows from the line above |
| The firmware saves the settings bank (with the EEROM tail) at power-off | V | card-looks |

So the user changes a value, leaves the menu (half-press), and sees it. The menu reopens where it was (I).

## 3. Rows and pages

| Item | Finding | Label |
|---|---|---|
| Rows now | 82 (log-menu); J has 8 (two pages) | V |
| Row limit | Row constants are 8-bit compares: 128 rows | R |
| Page | 7 rows; J with 23 rows = 4 pages (7, 7, 7, 2) | E (paging), I (count) |
| Row-state array | 2 B per row, 164 -> 194 B; room to 0x606A32F0 | R |
| A new group (K) | needs a tab, an icon and the top-level layout in `.data`: not done before | U |
| Per row in the tables | 16 B item row + 8 B child entry | R |
| Item table | 82 rows at 0x7EBF1FF0, 238 B free after: 14 more rows fit, 15 do not (2 B short) | R |
| Child list | 664 B at 0x7EE3CBF4, 270 B free after Debug Log's value list: 15 rows need 784 B, so it moves again (largest segment-3 run 705-973 B) | R |
| **Setting per row** | the picker writes the descriptor's setting (E: descriptor 448, row 447 -> `setSetting(448, ...)`) | E |
| **Panel per row** | so each row needs its own descriptor and panel id | E |
| Stored value | a negative value does not survive (u8: -3 is 253, the row is blank after a restart). Store 0 = ±0, 1-7 = +1..+7, 8-14 = -1..-7 | E |

Dormant pairs (setting with no constant-id access, R; dynamic check not done, U): 448/panel 609, 450/595,
442/584 (default 1), 285/107, 273/203. Already used: 446, 447, 449, 458. 39 more settings pass the static check but
have no panel. New panel ids mean relocating the 312-entry descriptor table and the page registry (U, research).

## 4. Code size of a minimal editor

Approach: edit the slot's tables directly. Base = the slot's tables before the first edit (RAM gap 0x7E4ED000-
0x7E4F9000, 48 KB, unused). No look record needed, so built-in and loaded films are handled alike.

| Part | Bytes (I) |
|---|---|
| Poll in the hook: 2 settings (two-row) or 15 (table) | 50 / 70 |
| Selector change: setSetting(Value, saved value) | 25 |
| Film in use -> slot (art setting, card-looks' slot table) | 30 |
| Six-axis hue and saturation: 12 deltas, table loop | 35 + 24 table |
| Saturation gain | 15 |
| Warmth and tint: matrix diagonal, rows kept at 256 | 45 |
| Contrast, Blacks, Whites: f(y) on each tone table entry | 90 |
| Apply one slot + refresh (glue to card-looks' code) | 40 |
| Per-film values: 12 x 15 B in the EEROM tail, reload at film change | 40 |
| Selector names (two-row): re-point 15 text ids at run time | 35 |
| **Total** | **about 450-600** |

Data (two-row): value items and list 804 B, selector items and list about 800 B, 15 names about 360 B, row and
child entries, the child list moved (680 B): about 2.7 KB.

Free (`docs/code-space-map.md`): 679 B USABLE-CODE, 3,047 B USABLE-DATA in segment 3. Code ran in a segment-3
reclaimed area on the camera (card-looks-3 at 0x7EE53830, V), so those runs can take code (I). Note: the
stock-filters work claims some of these runs (for example 0x7EE544E4, 973 B); the budget depends on which line the
editor goes on.

## 5. Emulator demo (E)

Build: `builds/log-menu.json` + `out/demo-spec.json` (`out/mkdemo.py`): panel 608 (Debug Log, setting 447) gets 15
kind-3 items and a value -> text list. Not for a camera.

| Step | Result |
|---|---|
| Open J -> Debug Log | row shows ±0 (setting 0) |
| RIGHT | picker +7 ... ±0 ... -7, 7 per page, scroll bar |
| DOWN x3, OK | row shows -3 |
| Restart (saved state) | row shows -3 |
| Firmware errors | the same two as the unchanged build |

Screenshots: `out/emu/s5/list.png`, `out/emu/s6/row-restart.png`.

## Blockers and next checks

| Question | Smallest check |
|---|---|
| Is a second setting/panel pair free (450/595, 285/107, 273/203)? | emulator, as `run_447.sh`: no start write, value kept |
| Do 15 settings and panels exist for a 15-row design? | research; avoid it with the two-row design |
| Does the bar descriptor (Picture Mode) take 15 steps and open from a row? | emulator |
| Live view lag after an edit | one camera run (the refresh itself is V) |

# Light Box: notes

The design and the acceptance criteria are in [design.md](design.md). Labels: **V** verified (firmware bytes,
emulator, manual), **I** inferred, **U** unknown.

## Build light-box (2026-11-24)

Emulator and desk only. Not flashed.

### What was built

`gen/light-box/mkspec.py` writes two specs. `data/builds/light-box.json` is the pinned build peaking-mf with
`custom-menu-rows-4` in place of `custom-menu-rows-3` and `light-box-row` added last. Data only: no code, no hook.
Label 2026.11.24.

| Spec | What it changes |
|---|---|
| `custom-menu-rows-4` (49 ops) | `custom-menu-rows-3` with one row more: ▶ Close Up Mode in group D after LV Close Up Mode. The row is the E-PL5 1.6 record `{3, text 208, setting 321, order 0, help 1126, value list 130, 0}`, and the child entry is (130, 321), both at index 34, as on the E-PL5. Item table: 84 rows at **0x7EBF1FD0**, 16 B earlier than before, in the free run 0x7EBF1FCA–0x7EBF1FE0; it still ends at 0x7EBF2512. Child list: 85 entries in place at 0x7EE3CBF4. Debug Log's value → text list moves 8 B to 0x7EE3CE9C. Constants: last index 83, count 84, row-state array 168 B (RAM to 0x606A31BF; the next object is at 0x606A32F0). Rows in group D: 17 → 18 |
| `light-box-row` (2 ops, 36 B) | The sub-item row of panel 594 for setting 449 (0x7EFF0438) becomes `{191, title 150, setting 257, 2, 7, 1, text 868}`, equal to the E-PL5 row. Panel 191's child list (0x7EFF91FC) gets the fifth entry (198, 257) in place of its end entry, and the end entry moves 8 B into panel 192's old list 0x7EFF9224 |

Two choices differ from the plan in design.md §4:

- **No free space for panel 191's list.** Panel 192's old list at 0x7EFF9224 follows panel 191's list. No word in
  block 0 points at it since `level-gauge-lvinfo-row` moved panel 192's list (**V**, a scan of all four address
  aliases at every byte offset of the build's block 0). So the list grows in place, as the E-PL5's list does. The
  open point "free space for a 48-byte child list" is settled: none is needed.
- **The item table moved 16 B earlier**, as `custom-menu-rows-3` did. The free run before the table is 22 B
  (`tools/freespace.py area 0x7EBF1FE0`).

The texts 208, 1126 and 868, the value list of panel 130 (mode1 / mode2, at 0x7F014584) and the list of setting 257
(Off / On) are stock, so both rows read the same in every menu language (**V**: text table; the value lists from the
build's bytes).

### Checks

sha256 **`4c689d47520f6d7d09c6751174fb8846f7735b8f66c5f4688b564784a3945917`** (`uv run epm2mod make light-box`).

| Check | Result |
|---|---|
| `uv run epm2mod make light-box` with the free-space check | exit 0; check PASS (0 FAIL); 21 specs, 25,278 bytes changed |
| `emulator/hookcheck.py` (all 21 specs) | exit 0; 260 transfers, 0 FAIL |
| `emulator/opcheck.py data/builds/light-box.json` | exit 0; 578 byte ops, 0 FAIL |
| `emulator/boot-test data/builds/light-box.json` | exit 0, PASS |
| `emulator/update-path-test data/builds/light-box.json` | exit 0, PASS |
| Crawl `p-nocard-shallow`, `crawlcmp.py` against peaking-mf | exit 0. 268 screens equal by name; 1 differs: the Firmware screen's label (2026.11.24 against 2026.11.20, `results/firmware-label.png`). Custom Menu rows 83 → 84: 10 screens lost and 11 new, all cursor positions of group D's second page (custrows 28–38). The same firmware errors on both (`0x2a001001` at start) |
| Crawl `p-nocard-full`, `crawlcmp.py` against peaking-mf | exit 0. Units other than the Custom Menu rows: 820 screens, all equal (the full setup unit does not reach the Firmware screen; it ends early on both images). Custom Menu rows, by content: 1,537 screens in both; 41 lost and 47 new, all under group D: the ▶ Info list and its value boxes (5 rows in place of 4), and the value boxes of D's rows, where the greyed list behind the box shows ▶ Close Up Mode in place of Backlit LCD (checked by eye: `lost-12` / `new-15`, Mode Guide). LV-Info and ▦ Settings and their sub-screens: in both. The same firmware errors on both |
| `uv run python -m unittest discover -s cli/tests` | 279 tests OK (6 skipped) |
| `uv run epm2mod generate --check` | up to date |

### Emulator runs

`scripts/lbprobe.mjs` is the boot lab's play with probes in `CPlaySingleFrame::getJumpState` 0x7ED09135 and a
`tag:HEX[:I]` step that reads a stored setting. The card holds two E-PM2 JPEGs. Screens: `results/`.

![Close Up Mode](results/closeup-row-mode2.png) ![▶ Info](results/info-list-lightbox-on.png)
![Light Box](results/lightbox-display.png)

| Run | Result |
|---|---|
| A new settings state (`emulator/mkstate`) | ▶ Close Up Mode shows mode1 (`results/closeup-row-mode1.png`); prm 0x91A1 = 1. ▶ Info shows Light Box Off as the fifth row (`results/info-list-lightbox-off.png`); prm 0x9171[4] = 0 |
| Custom Menu D → ▶ Close Up Mode → ▶ → ▼ → OK | the value screen shows mode1 and the help "Zoom a picture." (`results/closeup-list.png`); the row shows mode2; prm 0x91A1 = 2 |
| ▦/Info Settings → ▶ Info → Light Box → ▶ → ▼ → OK → OK | the Off / On box (`results/lightbox-picker.png`); the row shows On; prm 0x9171[4] = 1 (elements 0–3 unchanged: 1, 1, 0, 0) |
| A restart with the kept settings state | both rows show their values (`results/closeup-mode2-after-restart.png`, `results/lightbox-on-after-restart.png`); 0x91A1 = 2, 0x9171[4] = 1 |
| Playback, Light Box On, mode2, Overall Off | PLAY: getJumpState returns 8 (`ID_ST_DISP_SIMPLE`). INFO: it reads 257 = 1, 321 = 2, check 0x7ED009D6 = 1, sets the display mode to 11 and returns **15, `ID_ST_DISP_LIGHTBOX_PREPARE`**. The screen shows two frames side by side, "1x" and the picture numbers 2 and 1, the right frame green (`results/lightbox-display.png`). INFO again: 2, then 6 (`ID_ST_DISP_OFF`, image only); INFO: 8; INFO: 15 again |
| In Light Box | ▶: the right frame shows picture 2 (`results/lightbox-right.png`); ◀: back to 1; OK: picture 1 goes to the left frame (`results/lightbox-ok.png`), as the E-PL5 manual says. MAGNIFY: the emulator stops on a division by zero at 0x7ED00CF6 (I: the size of a picture that was not decoded; om-emu traps a division by zero, the MN103 does not) |
| Playback, Light Box On, **mode1**, Overall Off | INFO: getJumpState reads 257 = 1, 321 = 1 and returns 6; the cycle is 8 → 6 → 8, without Light Box. This is the rule of design.md §3 |

**Playback in the emulator** (the open point of design.md §6), **V** on peaking-mf too:

- With a picture on the card and the lab's defaults, PLAY stops on a fault at 0x7E557770: the JPEG codec at
  0x99400000 is not modelled. `lbprobe.mjs` answers the PLAY module's API commands (queue 80) as done (S-TAKEAPI's
  `apiFake`). No picture is decoded or drawn; the GUI's states run.
- With Overall On, INFO goes to `ID_ST_DISP_DETAIL_PREV` (10) and stays there: that state waits for the picture's
  data. The same with the codec blocks 0x99400000 and 0x99600000 as plain storage. So the runs above switch Overall
  off, and the cycle is Simple → Light Box → Image Only.
- The first check 0x7ED009D6 returned 1 with two pictures on the card. The second check 0x7ED00A1D was not reached
  by the probe: the state-15 return came through the display-mode-11 branch (0x7ED0941A). What either check tests is
  still not read (**U**).

### Acceptance criteria (design.md §5)

| # | Criterion | Result |
|---|---|---|
| 1 | Custom Menu D has ▶ Close Up Mode, mode1 / mode2, mode1 at first | **pass** (E) |
| 2 | ▶ Info has a fifth row Light Box, Off / On, Off at first | **pass** (E) |
| 3 | Light Box On + mode2: INFO reaches two pictures side by side | **pass in the emulator for the GUI** (state 15, two frames); the pictures: not checked (C) |
| 4 | Choose the picture on each side, zoom both, scroll both | choosing: **pass** (E: ▶ / ◀ and OK); zoom and scroll: not checked (C) |
| 5 | mode2: the playback zoom shows a zoom frame first | not checked (C) |
| 6 | Both settings kept after power-off | **pass** for a restart with the kept state (E); a power-off: not checked (C) |
| 7 | Every other Custom Menu row is where it was and works | **pass** (E, crawls) |
| 8 | The other ▶ Info rows and the LV-Info rows unchanged | ▶ Info rows 1–4: **pass** (E: same values, same order, the elements 0–3 of 0x9171 unchanged); LV-Info: **pass** (E, full crawl: its screens are equal) |
| 9 | Light Box Off or mode1: playback, INFO cycle and zoom as today | the INFO cycle with mode1: **pass** (E); zoom and the rest: not checked (C) |
| 10 | Shooting, film simulations, peaking, interval, level gauge as today | not checked (C) |

### What only the camera settles

- Whether the Light Box display draws both pictures, and its zoom and scroll (criteria 3 and 4). Which control
  zooms in Light Box on the E-PM2: the E-PL5 manual says the zoom button (U); the E-PM2 has no zoom button, but
  U (Magnify) can be put on a button with Button Function (E-PM2 manual p.78–79), and the Light Box state has a
  handler for the control dial (`…_StDispLightBox_EvtStChgMainDial` 0x7ED0E05B, feature map 10d).
- Whether mode2's zoom frame exists on the E-PM2 (criterion 5). The E-PM2 zooms in playback with the control dial
  (E-PM2 manual p.38). The survey found `CPlayZoom::setDbZoomInfo` shorter than on the E-PL6 (**I**: mode2 may be
  cut).
- Both settings after a power-off (criterion 6), and that nothing else changed (criteria 9 and 10).
- The owner's stored values of settings 257 and 321 (**U**; the defaults are Off and mode1).

### How it combines with the spot-metering branch

Both changes add a Custom Menu row with a new version of the item-table spec in place of `custom-menu-rows-3`. Two
such specs cannot be in one build: each rewrites the same item table, the same 10 address loads, the same child list
and constants. Combined, one spec holds both rows: `rows4()` of `gen/light-box/mkspec.py` applied to the other
branch's spec gives an 85-row table (constants 84 / 85, row-state array 170 B, child list 86 entries, Debug Log's
value list 8 B later again, at 0x7EE3CEA4: inside the free run that ends at 0x7EE3CFE2). The table itself does not
fit: 85 rows need 1,362 B, 32 B more than `custom-menu-rows-3`, and the free run before 0x7EBF1FE0 holds 22 B (it
starts where `osd-battery` ends, 0x7EBF1FCA). The combined spec needs another place for the table (**I**; not
tried).

### Camera test (draft)

Flash: `epm2flash light-box 4c689d47520f6d7d09c6751174fb8846f7735b8f66c5f4688b564784a3945917`

Go back: `epm2flash peaking-mf 6a47806dfafce15d281358eae2beffe397132e5999c50b28c69b2a2467efcf39`

Menu paths: the E-PM2 manual p.57 (MENU shows the top menu; [SETUP] and OK show the menu tabs; ▲ ▼ and OK choose)
and the firmware's texts as the emulator draws them (`results/`). Each path was walked in the emulator with OK. The
Custom Menu tab must be shown (Setup Menu → c/# Menu Display → c Menu Display: On); it is on when Load Looks is in
use. ▲ ▼ ◀ ▶ are the arrow pad; "playback button" is the ▶ button beside it.

1. Update the firmware as usual. Then MENU → [SETUP] → OK → Setup Menu → Firmware → OK.
   Expected: "Body : 1.6  EPM2Mod 2026.11.24". Another date: the update did not take; flash again.
2. Take two photos (any subject; JPEG or RAW+JPEG).
3. MENU → [SETUP] → OK → Custom Menu → D. Disp/(speaker)/PC → ▶ Close Up Mode.
   Expected: the row is after LV Close Up Mode and shows mode1. No row: note the last rows of D and stop.
4. OK → ▼ to mode2 → OK.
   Expected: the value box shows "Display an enlargement frame and push again to enlarge a picture in it." under
   mode2; the row shows mode2.
5. ▲ to ▦/Info Settings → OK → ▶ Info → OK.
   Expected: five rows: Image Only, Overall, (histogram), Highlight&Shadow, Light Box; Light Box Off.
6. ▼ to Light Box → ▶ → ▼ to On → OK → OK.
   Expected: back in D, no message.
7. Close the menu with MENU. MENU → [SETUP] → OK → Custom Menu → B. Button/Dial → Button Function → OK → Fn Function
   → OK → ▼ ▼ to Magnify → OK. Close the menu.
   Expected: Fn Function shows the magnifier. This puts the zoom button of the E-PL5 manual on Fn for steps 10–12;
   step 15 sets it back.
8. Power off, power on. Walk the paths of steps 3 and 5 and read both rows; close the menu.
   Expected: mode2 and Light Box On. mode1 or Off: that setting is not kept (criterion 6); note which.
9. Playback button, then INFO, one press at a time, up to six presses.
   Expected: one press shows two pictures side by side, the right one in a green frame, "1x" at the bottom left.
   Never: note the displays that came (criterion 3 fails). A freeze: battery out, note the step.
10. In the two-picture display: ▶, then OK.
    Expected: ▶ changes the picture on the right; OK puts that picture on the left.
11. Press Fn. Then turn the control dial clockwise one step. Then ▲ ▼ ◀ ▶. Then Fn again.
    Expected: Fn zooms both pictures (the number at the bottom left changes from 1x); the dial changes the zoom; the
    arrows move the view of both; the second Fn changes which side is shown zoomed (E-PL5 manual). Note what each key
    did (criterion 4).
12. INFO until one picture shows. Press Fn, then Fn again. Then turn the dial counterclockwise until the whole picture
    shows, and clockwise one step.
    Expected with mode2: the first Fn shows a frame on the picture, the second zooms into it (criterion 5). A zoom at
    the first Fn: mode2's frame is not in this firmware. Note what the dial does.
13. MENU → [SETUP] → OK → Custom Menu → D. Disp/(speaker)/PC → ▶ Close Up Mode → OK → ▲ to mode1 → OK. Close the
    menu.
14. Playback button, then INFO up to six presses, then the dial clockwise one step.
    Expected: no two-picture display in the cycle; the dial zooms in as before the update (criterion 9).
15. MENU → [SETUP] → OK → Custom Menu → B. Button/Dial → Button Function → Fn Function → OK → ▲ ▲ to Live Guide →
    OK. Close the menu.
16. Short checks (criterion 10): one photo in P; one with an ART film simulation; MF with Peaking on (the lines);
    INFO in shooting to the level gauge.
    Expected: as on peaking-mf.

## Rebuild on main (2026-11-26)

Emulator and desk only. Not flashed. The build of 2026-11-24 does not apply to main: main's spot metering
(`gen/spot-menu`) has its own `custom-menu-rows-4` (Spot Metering in E) and uses panel 594 and list 198. This build
is film-tables-fix (camera-tested 2026-11-25) with `custom-menu-rows-5` in place of `custom-menu-rows-4` and
`light-box-row` last. Data only: no code, no hook. Label 2026.11.27.

### What was built

`gen/light-box/mkspec.py` (rewritten) writes both specs from the specs before them in `data/builds/light-box.json`.

| Spec | What it changes |
|---|---|
| `custom-menu-rows-5` (49 ops) | main's `custom-menu-rows-4` with ▶ Close Up Mode in D at index 34 (the E-PL5 record, as before; Spot Metering moves to index 49). Item table: 85 rows (1,362 B) at **0x7EBF1FC0**, 16 B earlier than rows-4's, same end 0x7EBF2512. Child list: 86 entries in place at 0x7EE3CBF4, to 0x7EE3CEAC. Debug Log's value → text list moves to **0x7EE3CF04**, after spot-menu's page list 0x7EE3CEE4 (rows-4's place 0x7EE3CE9C is under the longer child list). Constants: last index 84, count 85, row-state array 170 B (RAM to 0x606A31C1; next object 0x606A32F0). Group D 17 → 18 |
| `light-box-row` (4 ops) | Sub-item record 119 (0x7EFEFE48, panel 651 "Mode Dial Function", Myset4) takes panel 191's first row (Image Only, setting 253); records 139–142 (0x7EFEFFD8) take panel 191's rows 2–4 and `{191, title 150, setting 257, 2, 7, 1, text 868}`. List 655's descriptor (0x7F00C78C, Myset4's picker: setting 493, 9 items) becomes `{257, 2, 0, 1, 0x7F008C88}`, the stock descriptor of list 198. Panel 191's child list gets `(655, 257)` and its end entry moves into panel 192's old list 0x7EFF9224, as before |

Four things differ from the build of 2026-11-24:

- **The item table needed 10 B of osd-battery's run.** The 85-row table needs 1,362 B. With rows-4 replaced, the
  largest free run in segments 2 and 3 under the ledger was 1,352 B (0x7EBF1FCA–0x7EBF2512, rows-4's own place);
  every other run was 768 B or less (**V**, the ledger's ops against the listed areas). level-adjust-row's two dead
  table copies (0x7EBF3000, 1,906 B; no word at any alias points into 0x7EBF2FF1–0x7EBF3780, **V**) are refused by
  `make`: "changes block0+0x7d207c, a byte that level-adjust-row covers and keeps", at every 2-aligned start (**V**).
  The owner released osd-battery's bytes on 2026-11-26 (`tools/space-ledger/superseded.tsv`: history). The table
  uses 0x7EBF1FC0–0x7EBF1FCA of them. Free-space check: PASS.
- **Another sub-item record.** spot-menu uses all three of panel 594's records. Panel 651 ("Mode Dial Function",
  settings 490–493) is in no child list of the 361 panel records (**V**, `scripts/subrows.py` on film-tables-fix and on
  cold-start-fix), no Custom Menu row names it (**V**), and the code has no `mov 651` but GL register writes and the
  page creator's bound `cmp 651` (**V**, `build/map/linear.txt`). Its menu row exists only on the E-PL5 and E-PL6
  (Custom Menu B; `experiments/2026-11-15-feature-survey/firmware-diff.md`). No word at any alias points at the records
  119 or 139–142 (`scripts/wordscan.py`; two unaligned hits in data at 0x7E857FCA and 0x7E85C056). The table is walked
  from top to bottom, so record 119 alone would put Light Box first: panel 191's rows move one record each, in order.
- **Another picker.** spot-menu re-keyed list 198, Light Box's stock picker, to Spot (setting 593). A build with
  `(198, 257)` wrote Spot = 1 when Light Box was set On (**V** emulator: tag 0x94D1 = 1, 0x9171[4] = 0). List 655 is
  the picker of panel 651's Myset4 row; it is a generic list page (registry 0x7EFE1ED4 → 0x7EDC7ECB) and its
  `{list, descriptor}` entry is 0x7F00DDD8; nothing else points at its descriptor (**V**, word scan).
- **Panel 191's list still grows in place**: no word points at 0x7EFF9224–0x7EFF922C on film-tables-fix (**V**); the
  nearest hit is 0x7EFF9244, panel 193's list, from its record 0x7EFFB180.

### Checks

sha256 **`44925a07bfc29cc203c86ac63b99ef7c134c46142f78233ff18c1d5c01c0363f`** (`uv run epm2mod make light-box`).

| Check | Result |
|---|---|
| `uv run epm2mod make light-box` | exit 0; free-space check PASS (0 FAIL), load-order check 62 transfers, 0 not in the pinned build; 23 specs, 25,811 bytes changed; boot-test PASS; update-path-test PASS |
| `uv run python emulator/hookcheck.py data/builds/light-box.json` | exit 0 |
| `uv run epm2mod lint light-box` | 1 warning: the build changes early-loaded bytes, so test a cold start (camera off 2 minutes). The early-loaded bytes are rows-4's own ops on the kernel range, unchanged here |
| Crawl `p-nocard-shallow`, `crawlcmp.py` against film-tables-fix | exit 0. 268 screens equal by name; 1 differs: the Firmware screen (`results/rebuild/firmware-label.png`). Custom Menu rows 84 → 85: 10 lost, 11 new, all cursor positions of group D's second page (custrows 28–38). Firmware errors equal (36 × 0x2a001001) |
| Crawl `p-nocard-full`, `crawlcmp.py` against film-tables-fix | exit 0. Units other than the Custom Menu rows: 820 screens, all equal (the setup unit ends early on both images and does not reach the Firmware screen). Custom Menu rows, by content: 1,547 screens in both; 41 lost and 47 new, all in group D: the ▶ Info list and its value boxes (5 rows in place of 4) and the screens of D's rows whose list shows ▶ Close Up Mode. LV-Info, ▦ Settings and Custom Menu E with Spot Metering: in both. Firmware errors equal (92 × 0x2a001001). Six units of the light-box run stopped with "no .BIN for BLOCKS" while `tools/ci.sh` ran (I: it remade the image cache); they were run again on the same image (44925a07…) and merged. No other screen differs, so no crawled path shows panel 651: its record 119 now reads Image Only, and a screen that drew it would differ. The crawl covers the P-mode menus without a card (I: other modes and the accessory menus with an EVF are not crawled) |
| `uv run python -m unittest discover -s cli/tests` | 293 tests OK (6 skipped) |
| `gen/run.sh --check`, `uv run epm2mod generate --check` | every generated spec is as committed; the documents are up to date |
| `tools/ci.sh python` | exit 0: "every check passed. Builds made and checked: cold-start-fix light-box"; cold-start-fix comes out as its pinned sha256 eab0c64e… |

### Emulator runs

`scripts/lbprobe.mjs` as before, the card with two E-PM2 JPEGs, Overall Off for playback. Restarts: the state saved
by `play.mjs` after the same keys. Screens: `results/rebuild/`.

| Run | Result |
|---|---|
| New settings state | 0x91A1 = 1 (mode1); 0x9171 = 1, 1, 0, 0, 0; Spot tags 0x94D1, 0x9F91, 0x9821 = 0 |
| D → ▶ Close Up Mode → ▶ → ▼ → OK | the value screen with the mode2 help (`closeup-list-mode2.png`); the row shows mode2; 0x91A1 = 2 |
| D → ▦/Info Settings → ▶ → ▶ Info → ▶ → ▼ ×4 → ▶ → ▼ → OK → OK | five rows, Light Box fifth (`info-list-lightbox-off.png`), the Off / On box (`lightbox-picker-on.png`); back in D; 0x9171[4] = 1, elements 0–3 unchanged; Spot tags 0 |
| Restart with the kept state | 0x91A1 = 2, 0x9171[4] = 1; both rows show their values (`closeup-mode2-after-restart.png`, `lightbox-on-after-restart.png`) |
| Playback, Light Box On, mode2 | PLAY: getJumpState returns 8. INFO: reads 257 = 1, 321 = 2, check1 = 1, display mode 11, returns **15** (`ID_ST_DISP_LIGHTBOX_PREPARE`): two frames, "1x", pictures 2 and 1 (`lightbox-display.png`). INFO: 2, 6; INFO: 8; INFO: 15 again. ▶: right frame picture 2 (`lightbox-right.png`); ◀: 1; ▶ then OK: picture 2 on the left (`lightbox-ok.png`) |
| Playback, Light Box On, **mode1** | INFO: reads 257 = 1, 321 = 1, returns 6; then 8, 6, 8: no Light Box |
| E → Spot Metering → ▶ | the page with Spot, Spot Hilight, Spot Shadow; each row On alone writes only its own tag (0x94D1, 0x9F91, 0x9821) and not 0x9171[4]; the page, the three rows On and the way back draw the same as film-tables-fix (`spot-page.png`, `spot-all-on.png`) |
| Custom Menu B → Button Function → Fn Function → ▶ → ▼ ▼ | Magnify, for the test sheet's step 8 (`fn-function-magnify.png`) |

### Acceptance criteria (design.md §5)

| # | Criterion | Result |
|---|---|---|
| 1 | Custom Menu D has ▶ Close Up Mode, mode1 / mode2, mode1 at first | **pass** (E) |
| 2 | ▶ Info has a fifth row Light Box, Off / On, Off at first | **pass** (E) |
| 3 | Light Box On + mode2: INFO reaches two pictures side by side | **pass** in the emulator for the GUI (state 15, two frames); the pictures: not checked (C) |
| 4 | Choose the picture on each side, zoom both, scroll both | choosing: **pass** (E); zoom and scroll: not checked (C) |
| 5 | mode2: the playback zoom shows a zoom frame first | not checked (C) |
| 6 | Both settings kept after power-off | **pass** for a restart with the kept state (E); a power-off: not checked (C) |
| 7 | Every other Custom Menu row is where it was and works | **pass** (E: crawls; Spot Metering's page and its three rows) |
| 8 | The other ▶ Info rows and the LV-Info rows unchanged | ▶ Info rows 1–4: **pass** (E); LV-Info: **pass** (E, full crawl: its screens are equal) |
| 9 | Light Box Off or mode1: playback, INFO cycle and zoom as today | the INFO cycle with mode1: **pass** (E); zoom and the rest: not checked (C) |
| 10 | Shooting, film simulations, peaking, interval, level gauge, spot metering as today | not checked (C) |

### Camera test (draft)

Flash: `epm2flash light-box 44925a07bfc29cc203c86ac63b99ef7c134c46142f78233ff18c1d5c01c0363f`

Go back: `epm2flash film-tables-fix e029facb38569880c0cec4c16b0f295ca2a96214ed75900fe00585f6b0cedd28`

Menu paths: the E-PM2 manual p.57 (MENU shows the top menu; select [SETUP] and press OK to show the menu tabs) and
the firmware's texts as the emulator draws them (`results/`, `results/rebuild/`). Each path was walked in the
emulator. The Custom Menu tab must be shown (Setup Menu → c/# Menu Display → c Menu Display: On); it is on when Load
Looks is in use. ▲ ▼ ◀ ▶ are the arrow pad; "playback button" is the ▶ button beside it.

1. Update the firmware as usual. Then MENU → [SETUP] → OK → ▼ to Setup Menu (the wrench) → ▶ → ▼ to Firmware → ▶.
   Expected: "Body : 1.6  EPM2Mod 2026.11.27". Another date: the update did not take; flash again.
2. Take two photos (any subject; JPEG or RAW+JPEG).
3. MENU → [SETUP] → OK → ▼ to Custom Menu (the gear) → ▶ → ▼ to E. Exp/▣/ISO → ▶ → ▼ to Spot Metering → ▶. Note
   the three values (Spot, Spot Hilight, Spot Shadow). MENU (back to the rows of E).
4. ◀ to the groups → ▲ to D. Disp/♪/PC → ▶ → ▼ to ▶ Close Up Mode.
   Expected: the row is after LV Close Up Mode and shows mode1. No row: note the last rows of D and stop.
5. ▶ → ▼ to mode2 → OK.
   Expected: the value screen shows "Display an enlargement frame and push again to enlarge a picture in it." under
   mode2; the row shows mode2.
6. ▲ to ▦/Info Settings → ▶ → ▶ Info (the first row) → ▶.
   Expected: five rows: Image Only, Overall, (histogram), Highlight&Shadow, Light Box; Light Box Off.
7. ▼ to Light Box → ▶ → ▼ to On → OK → OK.
   Expected: back in D, no message.
8. ◀ to the groups → ▲ ▲ to B. Button/Dial → ▶ → Button Function (the first row) → ▶ → Fn Function (the first row)
   → ▶ → ▼ ▼ to Magnify → OK. Close the menu with MENU.
   Expected: Fn Function shows the magnifier. This puts the zoom button of the E-PL5 manual on Fn for steps 11–13;
   step 16 sets it back.
9. Power off, power on. Walk the paths of steps 3, 4 and 6 and read the rows; close the menu.
   Expected: mode2, Light Box On, and the three Spot Metering values of step 3. mode1 or Off: that setting is not
   kept (criterion 6). A Spot value changed: the Light Box row writes a spot setting; note which, and go back.
10. Playback button, then INFO, one press at a time, up to six presses.
    Expected: one press shows two pictures side by side, the right one in a green frame, "1x" at the bottom left.
    Never: note the displays that came (criterion 3 fails). A freeze: battery out, note the step.
11. In the two-picture display: ▶, then OK.
    Expected: ▶ changes the picture on the right; OK puts that picture on the left.
12. Press Fn. Then turn the control dial clockwise one step. Then ▲ ▼ ◀ ▶. Then Fn again.
    Expected: Fn zooms both pictures (the number at the bottom left changes from 1x); the dial changes the zoom; the
    arrows move the view of both; the second Fn changes which side is shown zoomed (E-PL5 manual). Note what each key
    did (criterion 4).
13. INFO until one picture shows. Press Fn, then Fn again. Then turn the dial counterclockwise until the whole picture
    shows, and clockwise one step.
    Expected with mode2: the first Fn shows a frame on the picture, the second zooms into it (criterion 5). A zoom at
    the first Fn: mode2's frame is not in this firmware. Note what the dial does.
14. MENU → [SETUP] → OK → ▼ to Custom Menu → ▶ → ▼ to D. Disp/♪/PC → ▶ → ▼ to ▶ Close Up Mode → ▶ → ▲ to mode1 →
    OK. Close the menu.
15. Playback button, then INFO up to six presses, then the dial clockwise one step.
    Expected: no two-picture display in the cycle; the dial zooms in as before the update (criterion 9).
16. MENU → [SETUP] → OK → ▼ to Custom Menu → ▶ → ▼ to B. Button/Dial → ▶ → Button Function → ▶ → Fn Function → ▶ →
    ▲ ▲ to Live Guide → OK. Close the menu.
17. Short checks (criterion 10): one photo in P; one with an ART film simulation; MF with Peaking on (the lines); INFO
    in shooting to the level gauge; with Spot Metering's Spot On, a photo in spot metering (as on film-tables-fix).
    Expected: as on film-tables-fix.

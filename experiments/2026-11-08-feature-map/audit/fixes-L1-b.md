# Fix pass L1-b (2026-11-09): boundary lint and coverage round C4, sections 09–15

Scope: `sections/09*`–`15*` (.md and .tsv) only. Sources: `audit/boundary-lint-1.tsv` (lint `scripts/boundary_lint.py`) and the C4 items of `coverage/round4-review1..4.md`. Every change was re-checked in block 0 of v1.6 (`build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin`, runtime = 0x7E421020 + offset) with `fwmap.py fn/range/str/xref`, `disasm.py`, `build/map/*.tsv` and raw word reads (Python `-I`). Scratch: `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/fixL1b/`. Changed text carries "(L1 2026-11-09)"; old values are struck through. No git, no build, no network.

## 1. Coverage round C4 corrections

| location | old | new | check done |
|---|---|---|---|
| 14d §2 row 0x7E84EE68 | 0x7E84EE68–0x7E851DFF "Exif/MakerNote/ORF IFD templates 0x7E84EF20 and tag lists" | split: 0x7E84EE68–0x7E84EF1F = IMGDMA add-job builder table 0x7E84EE68 (3 pointers 0x7E70795C/0x7E7079EA/0x7E707A1B) + small tables, jump table 0x7E84EEAC, PrintIM header; 0x7E84EF20–0x7E851DFF = Exif templates and tag lists | words at 0x7E84EE68 = {0x7E70795C, 0x7E7079EA, 0x7E707A1B, 0, 1, 1, …}; xref 0x7E84EE68 = `mov` at 0x7E70788F (in 0x7E707880); words 0x7E84EEAC–C8 = 0x7E708270…0x7E708307 (xref 0x7E707B4D/0x7E707DBE/0x7E707F3D); 0x7E84EF20 = 12's template start |
| 14d §5 "Section 03" note (line 318) | "the Exif/MakerNote writer 0x7E707880–0x7E70B434" | IMGDMA add 0x7E707880–0x7E707A9C; unnamed 0x7E707A9D–0x7E708311; Exif writer 0x7E708312–0x7E70B434 | `fwmap range 0x7E707880 0x7E708320`: 0x7E707A1B (130 B) ends 0x7E707A9C; 0x7E708312 is the first `PrintIM` user |
| 15c-class-index.tsv row `TraShareTakeStatus` | singleton, ctor 0x7E967145, vt 0x7EBCDBB4, gi 0x7E967175, 0x7E967145–0x7E96C981, "shared take/shooting status flags" | 4 rows: (1) HLS log-level object 0x7E967145–0x7E967753 (same ctor/vt/gi; RAM 0x602B0C78); (2) HLS root singleton 0x7E967754–0x7E9698EB (gi 0x7E967754, ctor 0x7E9679DF, RAM 0x602B0C88, vt 0x7EBD0C4C at +0); (3) TraShareTakeStatus (module, no this) 0x7E9698EC–0x7E96B13B, old id lists kept; (4) HLS root +0 code-translation object 0x7E96C670–0x7E96C981 | disasm 0x7E967145 (stores 0x7EBCDBB4, +24 = 4), 0x7E967175 (lazy `new 28` → 0x602B0C78); 0x7E9670E9 (logger) calls 0x7E96719D then 0x7E9671BB (compares +24 with d0); 0x7E967754 (lazy `new 28` → 0x602B0C88, ctor 0x7E9679DF, returns via 0x7E967A46); 6 sibling getters 0x7E9677B1…0x7E967982 call 0x7E967A49…0x7E967A61 (`add 4..24,a0`); ctor 0x7E9679DF calls 0x7E96C670 (+0), 0x7E967A66, 0x7E967D5C, 0x7E9682BA, 0x7E968523, 0x7E968DBE, 0x7E9691B7 (→ 0x7E96DB78 HLS_EVENT); 0x7E96C670 = `mov 0x7EBD0C4C,d0; mov d0,(a0)`; vt 0x7EBD0C4C slots = 0x7E96C67F, 6AC, 6D5, 7F9, 822, 847, 86D, 67A; 0x7E96C92F (83 B) ends 0x7E96C981; TraShareTakeStatus.cpp users 0x7E969F7B…0x7E96B048 use RAM 0x602B0CDC/0x602B0DAC and no `this`; 0x7E96B0B1–0x7E96B133 store 0x602B0E04–0x602B0E24; 0x7E96B13C = ctor of event 11761 (13c-event-ids.tsv); 0x7E96C625–0x7E96C661 = event dtors (call 0x7EBA490C) |
| 15c-class-index.tsv row `Cab_CameraBase facade` end | 0x7EB8E2B3 | 0x7EB8C264 | fn 0x7EB8C256 ends 0x7EB8C264; 0x7EB8C265 = DevInfo base ctor (next row); word 0x7EC8DEDC+40 = 0x7EB8CAAF (slot 10 of display-device vtable) |
| 15c-class-index.tsv: 20-row check for "next class start" | — | Exhaustive scan of getInstance-shaped functions (`mov (abs),aN; cmp 0,aN; …; call 0x7EBA62DB`, 108 in 0x7E966000–0x7EBA5000) against all 227 class rows, plus 9 random rows (seed 20261109) for end-is-function-end and overlaps. Of the 20 rows (11 flagged + 9 random): 7 hold only their own getInstance (filled into the empty getInstance column: HLS_CALLBACK 0x7E96CA56, HLS_EVENT 0x7E96DB78, Ope facade 0x7E975E9D, @7E9807DD 0x7E980899, @7E99525D 0x7E995472, OlyHfwUserSettingManager 0x7E9E762F; the HLS root's 6 sibling getters); EyeFi/FlashAir mode info ended 0x7E974DCB over the EVFW router getInstance 0x7E974D11 → end 0x7E974D10; 4 rows hold another singleton and got a note (OlyHfwOpeShoot 0x7E98D287, Tra request base 0x7E99975E + EVFW ctor 0x7E999809, key timer 0x7E9D715D, OlyHfwOpeSndCtl 0x7E9E4310/0x7E9E59A9); the 9 random rows end on function ends and overlap only their own member observers (CM, CmpPls) | `scratchpad/fixL1b/gi_scan.py`; each embedded getInstance's callee list read from calls.tsv: OWN = calls the row's ctor; `fwmap range 0x7E974C00 0x7E974DD0`; `fwmap fn` of 0x7E98D27D/0x7E999670/0x7E9D7153/0x7E9E4306/0x7E9E5809. The "Ope API front" row (45 OlyApi getters) is a documented multi-file row (15c §1) and was left |
| 15c §1 boundary table | — | 3 rows: TraShareTakeStatus split, Cab facade end, EyeFi end; sentence on the 4 annotated rows | as above |
| 13d §1 row 0x7EDC15B0– (end and GuiTouch) | row end ~0x7EDE161C; GuiTouch 0x7EDDD21D–0x7EDE161C; "last helpers 0x7EDE15A3–0x7EDE15EE" | row end 0x7EDE15ED; GuiTouch 0x7EDDD21D–0x7EDE15ED; last helpers to 0x7EDE15ED (last helper 0x7EDE15DA, 20 B) | `fwmap range 0x7EDE1500 0x7EDE1660`; disasm 0x7EDE15DA (`ret` at 0x7EDE15EB), 0x7EDE15EE = `mov (0x602BDF48),a0; cmp 0,a0; bne; mov 172,d0; call 0x7EBA62DB; call 0x7EDE161D; mov d0,(0x602BDF48)` (no call to 0x7EDE12CF) |
| 13d §1 row ~0x7EDE161D–0x7EE01FF5 | start ~0x7EDE161D | start 0x7EDE15EE; USB-connect screen 0x7EDE15EE–0x7EDE1DD8 named first | ctor 0x7EDE161D = `call 0x7EDCD621; mov 0x7EFEF47C,d0; mov d0,(a0)`; 14 caller fns of 0x7EDE15EE (16 sites) all in 0x7EDC0D90–0x7EDC156F (SS_USB, 13d §4.2); string `userGuiUsbConnectCallBack` user 0x7EDE1D0A, its pointer loaded at 0x7EDE1C87 in 0x7EDE1BF3 (← 0x7EDE1A56 ← 0x7EDE1933 ← 0x7EDE1914, 12 SS_USB callers); ShowPanelEx immediates 82/103 (0x7EDE18F0/F5) and 4 (0x7EDE1C47); 0x7EDE1DD9/0x7EDE1E1B are called from 0x7EDEA948/0x7EDEA827 (not USB) |
| 15a §1 table GuiTouch row, page-class row, framework table, §2.4 item 6, §4 item 1 | GuiTouch …–0x7EDE161C; page classes 0x7EDE161D–; "0x7EDCCA5D (direct) … and 0x7EDE1649" | GuiTouch …–0x7EDE15ED; new row USB-connect screen 0x7EDE15EE–0x7EDE1DD8; page classes 0x7EDE1DD9–; 0x7EDE1649 struck (its ctor calls page base 0x7EDCD621) | as above; disasm 0x7EDCD621 = `call 0x7EDCCA5D; mov 0x7EFE79FC,d0` (page base) |
| 15a-gui-pages.tsv rows 0x7EDE1448-0x7EDE161C and 0x7EDE161D-0x7EDE1D09; new page-class row | context accessors to 0x7EDE161C; "page class 0x7EDE1649 base (derives from 0x7EDCCA5D) and helpers" | accessors to 0x7EDE15ED; region 0x7EDE15EE-0x7EDE1DD8 = USB-connect screen; page-class row 0x7ede15ee-0x7ede1dd8 (vt 0x7efef47c, 32 slots, own 0/2/3, base 0x7edcd621, 172 B, panels 82/103/4) | vtable words 0x7EFEF47C… compared with page-base vtable 0x7EFE79FC: 32 code words, differing slots 0, 2, 3 |
| 13d §6.1 table | no row for ids 20–22 | row 20–22 = panel-112 message viewer (creators, ctor 0x7ED978DC, vt 0x7EFCE794, Update 0x7ED97907, message tables) | registry words 0x7EFC54A8 = {0x14, 0x7ED97886, 0x15, 0x7ED978A2, 0x16, 0x7ED978BF}; disasm creators (`mov 40,d0; call new; d0 = 0/1/2; call 0x7ED978DC`); ctor stores 0x7EFCE794 and d2 → +36; vt[0] = 0x7ED97907, which compares 0x602BB7C8 with 112 and stores 112; tables 0x7EFCE764 = {0→0x6B7, 1→0x6BE, 2→0x6BE}, 0x7EFCE77C = {0→0x6B9, 1→0x6C0, 2→0x6C5}; strings 1719/1721/1726/1728/1733 from `out/lang/101_1600.en.tsv` |
| 13d new §6.3, 13d §1 row, 15a §1 table, 15a-gui-pages.tsv new class row | singleton 0x7EDDBC06 not in the map | "return-to (SS, state)" singleton 0x7EDDBC06–0x7EDDBD4F: RAM 0x602BDA2C, 52 B, ctor 0x7EDDBC2E, accessors, reset 0x7EDDBCA8; role I | disasm 0x7EDDBC06–0x7EDDBCC9; `fwmap range 0x7EDDBBE0 0x7EDDBD60` (accessor sizes 4–6 B, reset 36 B, 32 callers); calls.tsv: 445 sites / 167 caller fns to 0x7EDDBC06; 0x7EDB0BC5 calls 0x7EDDBC06 ×4, 0x7EDDBC68, 0x7EDDBC72, 0x7EDDBC8A, 0x7EDDBCA8; 0x7EDF2D66 calls 0x7EDDBC06 and 0x7EDDBC68 |
| 15a §2.1 page key table and TSV `page-key 26/27/28` | "26 / 27 / 28 = END_DIRECT / POPUP / mode dial" (no END_ART_MENU, no handlers) | code 26 on its own row: END_DIRECT 0x9AB8 (handler 0x7EDB0EDA) and END_ART_MENU 0x9AC3 (handler 0x7EDB00BE); ART BKT key slot 0x7EDFE82D uses it; 27/28 split to their own row | `mov 26,d0` → `mov (12,a1),a1; calls (a1)` at 0x7EDB0181 (fn 0x7EDB00BE) and 0x7EDB0EE7 (fn 0x7EDB0EDA); D1 handlers.tsv maps 0x7EDB00BE = SS_MENU_MAIN st 7 EVT_END_ART_MENU 0x9AC3, 0x7EDB0EDA = st 4 EVT_END_DIRECT 0x9AB8; 0x7EDFE834 `cmp 26,d0`, then call 0x7EE01D4E |
| 15a line 7 TSV row count | 1,181 | 1,184 | `wc -l` |
| 13f §2.4 FAT row (line 241) | "the U_SHELL `file` entry 0x7E5C2139 is the stub just before it" | 0x7E5C2139 is F008's own indirect (prologue) entry; it falls into 0x7E5C213E (two-entry rule) | disasm 0x7E5C2130: 0x7E5C2136 `retf` ends the previous fn; 0x7E5C2139 `cf a0` + 0x7E5C213B `f8 fe f4`, then 0x7E5C213E; xref 0x7E5C2139 = data words 0x7E732738/0x7E733348/0x7EBCC350; calls.tsv: 0x7E5C213E ← 0x7F09D95D, 0x7F09D9F4 (`call 0x7e5c213e,[d2,a2],20`) |
| 14c-event-ids-extra.tsv | no row for 16143 (13c-event-ids.tsv has it without a name) | new row 16143 = `evTraCmpSts_RecViewAbort`; columns id…n_test_sites copied from 13c-event-ids.tsv; creators 0x7EA98505/0x7EA9A0F8, handler 0x7EA7070D | `fwmap fn 0x7EA7070D`: strings `%s(%d):RECEIVE EVENT evTraCmpSts_RecViewAbort` (0x7EC48B28) and `CmpSts_EPortraitShootingEditer.cpp`; disasm 0x7EA70724 `mov 16143,d0` → `calls (a1)` (isTypeOf) → `cmp d2,d0; beq` → log (`mov 1981,d0`, call 0x7E9670E9) → call 0x7EA6FBB7; calls.tsv: ctor 0x7EA85CCA ← 0x7EA98532, 0x7EA9A117 |
| 15b-camera-core-index.tsv row 0x7E8DE4EC; 15b §6 paragraph; 10f §5 bullet | "FACE_* (13b): 20 code pointers, stride 8 B" (no role); 10f does not list `face` | U_SHELL `face` subcommand table: 20 records {handler, name} start…tune_g, RAM copy 0x602AE02C, dispatcher 0x7E6F4D77 = U_SHELL `face` entry | words 0x7E8DE4EC+8k = handler, +4 = name string (start, stop, get, keep, reset, abort, prog, get_eye, dump, setting, log, pt, load, set_pos, get_pos, set_info, mdm, reg, tune_l, tune_g; zero at 0x7E8DE58C); handler strings `face_dbg_start/stop/pt/load/get_eye/set_info/get_pos in`, `face mdm X Y` (0x7E6F5840), `face reg X Y` (0x7E6F591D), tune_lost/tune_get; 0x7E8DE4EC − 0x1E6304C0 = 0x602AE02C, loaded by `mov 0x602AE02C,a2` at 0x7E6F4D8A in 0x7E6F4D77, loop `cmp 20,d2` with `add 8,a2`, strcmp 0x7E500DCA; U_SHELL table words 0x7E7333B4 = "face", 0x7E7333B8 = 0x7E6F4D77. **Differs from C4:** the review gave 17 names (no start/stop/pt) and called F021 0x7E6F591D `face mdm`; the bytes give 20 names and 0x7E6F591D = `reg` |
| 11 §8 key-address table | version-constant sites only as v1.2/v1.3 addresses (0x7F09261F, 0x7F0A8EB7, 0x7F0A9C30) | new 1.6 row: `mov 0x1600,d0` at 0x7F0A8F06 (in 0x7F0A8E8F), getter 0x7F0A9C08, `mov 0x1600,d2` at 0x7F0926F8 (in 0x7F0925F7); same addresses hold 0x1501 in v1.5 | disasm 0x7F0A8F06 = `2c 00 16` (`mov 5632,d0`), 0x7F0A9C08 = `2c 00 16; de 00 00`, 0x7F0926F8 = `2e 00 16`; byte compare of overlay B v1.6 vs v1.5 (`00 16` vs `01 15`) gives exactly these 3 sites; `fwmap fn 0x7F0A9C08` callers 0x7F0B3E9E/0x7F0B8D18 |
| 14d §5 "Section 03" note | Exif writer 0x7E708312–0x7E70B434 (my first L1 edit) | 0x7E708312–0x7E70B3F7 (coordinator item, from fixes-L1-a) | disasm 0x7E70B3F5 `ret [d2,d3,a2,a3],112`; 0x7E70B3F8 calls 0x7E710D07/0x7E71B605, only caller Usr0 0x7E503DD4 (rec init). Section 12 has no Exif-writer range to fix (grep `7E70B`/`7E7078` in 12: none) |
| 13c §1 row, §6 heading, §6 table row 0x7EB8BCCB–; 14c §1 row 0x7EB85563– | Com_ end 0x7EB8C265 | 0x7EB8C264 | fn 0x7EB8C256 (15 B) ends 0x7EB8C264; 0x7EB8C265 = DevInfo base ctor (Dev part 1 start) |
| 13c §3 event-run list | Tra run 0x7E96B13C–0x7E96C670 | 0x7E96B13C–0x7E96C66F | 0x7E96C661 (last event dtor, 15 B) ends 0x7E96C66F; 0x7E96C670 = `mov 0x7EBD0C4C,d0; mov d0,(a0); retf` |

## 2. Boundary lint (audit/boundary-lint-1.tsv), sections 09–15

| location | old | new | check done |
|---|---|---|---|
| 10b-shooting-modes.md | (verified immediates at 0x7E663939–0x7E6639E8) | (verified immediates at bytes 0x7E663939–0x7E6639E8 inside the function 0x7E6637F2 (L1 2026-11-09)) | lint: both ends inside fn 0x7E6637F2 (0x7E6637F2–0x7E663B43): a byte span, now labelled |
| 10d-playback.md | in 0x7E9BF000–0x7E9CE000 (39 getters; | in ~~0x7E9BF000–0x7E9CE000~~ 0x7E9BFA7E–0x7E9CDEBE (the first and last getter (L1 2026-11-09)) (39 getters; | gi_scan: 39 getInstance-shaped fns in the window, first 0x7E9BFA7E, last 0x7E9CDEBE |
| 10d-playback.md | In the Ope region 0x7E9CD000–0x7E9E2000, | In the Ope region ~0x7E9CD000–~0x7E9E2000 (a page-rounded search window (L1 2026-11-09)), | search window; 0x7E9CCFE3/0x7E9E1FDD cross the bounds; marked approximate |
| 10e-connectivity.md | 0x7E508F00–0x7E50D700, constants normalised | ~0x7E508F00–~0x7E50D700, a page-rounded compare window (L1 2026-11-09), constants normalised | compare window; 0x7E508EDA/0x7E50D6F0 cross the bounds; marked approximate |
| 10e-connectivity.md | (0x7F080B39–0x7F080BC2) | (case code 0x7F080B39–0x7F080BC2 inside the function 0x7F08056A (L1 2026-11-09)) | lint: span lies inside fn 0x7F08056A (0x7F08056A–0x7F080BEB) |
| 10f-debug-service.md | The debug-menu module 0x7ED9F800–0x7EDA1400 registers | The debug-menu module ~~0x7ED9F800–0x7EDA1400~~ (SS_DEBUGMENU handler code 0x7EDA0410–0x7EDA09AC: 13d §4.2 gives 0x7EDA0410 to the last handler 0x7EDA098D, which ends at 0x7EDA09AC (L1 2026-11-09)) registers | 13d §4.2 SS_DEBUGMENU = 0x7EDA0410–0x7EDA098D (last handler start); fn 0x7EDA098D ends 0x7EDA09AC; 0x7ED9F800 lies in the IGui_Controler/Actuator area (15a TSV 0x7ED86DA6-0x7EDA040F) |
| 10f-debug-service.md | (bytes 0x7EDABA14–0x7EDABA54) | (bytes 0x7EDABA14–0x7EDABA54 inside the handler 0x7EDAB9FE (L1 2026-11-09)) | lint: span inside fn 0x7EDAB9FE |
| 11-version-history.md | across the AF code (0x7E5E3000–0x7E627000) | across the AF code (~0x7E5E3000–~0x7E627000, page-rounded (L1 2026-11-09)) | 0x7E5E2FF2 crosses 0x7E5E3000; `fcs` string users run to 0x7E627C84; marked approximate |
| 11-version-history.md | Peripheral code at 0x7E512000–0x7E51C000 | Peripheral code at ~0x7E512000–~0x7E51C000 (page-rounded (L1 2026-11-09)) | 0x7E511C8F/0x7E51BFBA cross the bounds; marked approximate |
| 11-version-history.md | in the AF code 0x7E5E3000–0x7E627000 and | in the AF code ~0x7E5E3000–~0x7E627000 (page-rounded (L1 2026-11-09)) and | as row 19 |
| 11-version-history.md | rework (0x7E512000–0x7E51C000) | rework (~0x7E512000–~0x7E51C000 (L1 2026-11-09)) | as line 82 |
| 12-exposure-af-files.md | hands AF to the FCS code (0x7E5E2000–0x7E612000). | hands AF to the FCS code (~~0x7E5E2000–0x7E612000~~ ~0x7E5E2C00–0x7E627E9E: the first `FCS_PACKET` user is 0x7E5E2DE5 and the 4-letter FCS log tags start a little earlier; `fcs` string users run to the time-lag logger… | `fwmap str (?i)fcs`: users 0x7E5E2DE5…0x7E627C84 (dense in 0x7E5E9–0x7E612 and 0x7E626–0x7E627); 0x7E5E2DE5 = `FCS_PACKET [INPUT]`; 0x7E5E2CCD/0x7E5E2D94 use tags `Seq/`/`fep/`; 0x7E5E2419 is strobe; 0x7E627E9F = cam.c (15b), a fn start |
| 13a-libraries-runtime.md | C1 gave ~0x7E54D000–0x7E578000 for the image library | C1 gave ~~~0x7E54D000–0x7E578000~~ (L1 2026-11-09) for the image library | quoted old value of C1, struck |
| 13a-libraries-runtime.md | not ~0x7E54D000–0x7E578000. | not ~~~0x7E54D000–0x7E578000~~ (L1 2026-11-09). | quoted old value, struck |
| 13a-libraries-runtime.md | gives the float helpers as 0x7E5018BC–0x7E501972. | gives the float helpers as ~~0x7E5018BC–0x7E501972~~ (L1 2026-11-09). | quoted old value of 08, struck (the line gives the true set) |
| 13b-libraries-face-av.md | called from inside 0x7EE63000–0x7EE8F4F3 | called from inside ~~0x7EE63000~~ 0x7EE63005–0x7EE8F4F3 (L1 2026-11-09) | 0x7EE63000 is inside 0x7EE62F80 (to 0x7EE63004); next start 0x7EE63005 |
| 13b-libraries-face-av.md | ctors 0x7EEA36A9/0x7EEA4D84, code 0x7EEA36A9–0x7EEA7B6C) | ctors ~~0x7EEA36A9/0x7EEA4D84~~ 0x7EEA3691/0x7EEA4D6C, which store the vtables at 0x7EEA36A9/0x7EEA4D84, code ~~0x7EEA36A9–0x7EEA7B6C~~ ~0x7EEA3618–0x7EEA7B6C (0x7EEA3618 is the only callee of the ctor 0x7EEA3691) (L1… | disasm 0x7EEA3691–0x7EEA36B2: one fn (call 0x7EEA3618 at 0x7EEA36A4, then `mov 0x7F0302D4,d0; mov d0,(a0); ret` at 0x7EEA36A9); 0x7EEA4D84 is the same store inside fn 0x7EEA4D6C (vt 0x7F0307E8); 0x7EEA3691 has 1 callee 0x7EEA3618 (fn 0x7EEA3618–0x7EEA3634); start left approximate |
| 13b-libraries-face-av.md | Before that, 0x7EE63000–0x7EE8F4F3 is C3D-side code. | Before that, ~~0x7EE63000–0x7EE8F4F3~~ 0x7EE619C7–0x7EE8F4F3 (the C3D framework) (L1 2026-11-09) is C3D-side code. | 0x7EE619C7 is a fn start; 13b line 18 gives the C3D framework 0x7EE619C7–0x7EE8F4F3 |
| 13c-cpp-framework.md | the C++ application layer 0x7E966000–0x7EBAC000. | the C++ application layer ~~0x7E966000–0x7EBAC000~~ 0x7E966A17–0x7EBA7BC0 (HIGHLEVEL_MAIN to the end of OXF; §1 also covers the neighbours 0x7E965FD1–0x7E966A16 and 0x7EBA7BC1–0x7EBABF8D) (L1 2026-11-09). | 13c §1: HIGHLEVEL_MAIN from 0x7E966A17 (fn start), OXF ends 0x7EBA7BC0 (12-B helper 0x7EBA7BB5) |
| 13c-cpp-framework.md | / ~0x7E9EA381–0x7EB80000 / | / ~0x7E9EA381–~~0x7EB80000~~ 0x7EB7FC90 (L1 2026-11-09) / | next row starts at 0x7EB7FC91 (fn start, 13c §1) |
| 13c-cpp-framework.md | - Ctor functions: 0x7E96B000–0x7E9823AB 373; | - Ctor functions (counts per window; the windows are the older, page-rounded bounds (L1 2026-11-09)): 0x7E96B000–0x7E9823AB 373; | count windows kept (changing them would change the counts); labelled |
| 13c-cpp-framework.md | "Event constructors 0x7E96B000–0x7E9823AB" is wrong | "Event constructors ~~0x7E96B000–0x7E9823AB~~" (L1 2026-11-09) is wrong | quoted old label, struck |
| 13c-cpp-framework.md | the row "0x7EBA1020–0x7ECA0000 OXF runtime, DevBlu" | the row "~~0x7EBA1020–0x7ECA0000~~ OXF runtime, DevBlu" (L1 2026-11-09) | quoted old regions row, struck |
| 13d-gui-toolkit.md | / 0x7ECCB800–0x7ECE4000 / CA_MAIN | / 0x7ECCB800–~0x7ECE4000 (a round bound: `setCameraAppData` 0x7ECE3DCD crosses it (L1 2026-11-09)) / CA_MAIN | fn 0x7ECE3DCD (`>>>setCameraAppData`, 2,604 B) runs 0x7ECE3DCD–0x7ECE47F8 across 0x7ECE4000; the CA/bridge edge was not found cheaply (CameraAppData fns to 0x7ECE4B7A, first GuiCallerImp user 0x7ECE6E27); marked approximate |
| 13d-gui-toolkit.md | / 0x7ECE4000–0x7ECEC798 / | / ~0x7ECE4000–0x7ECEC798 (L1 2026-11-09) / | as above |
| 13d-gui-toolkit.md | / **0x7ECEE1D5–0x7ED00000** / | / **0x7ECEE1D5–~~0x7ED00000~~ 0x7ECFF982** (CCommon starts at 0x7ECFF983, next row (L1 2026-11-09)) / | next row CCommon ctor 0x7ECFF983 (fn start); the row text already gives helpers to 0x7ECFF982 |
| 13d-gui-toolkit.md | (D2 2026-11-09)–0x7ED17000 / | (D2 2026-11-09)–~0x7ED17000 (L1 2026-11-09) / | 0x7ED16FE7 crosses 0x7ED17000 |
| 13d-gui-toolkit.md | / **0x7ED17000–0x7ED37DAA** / | / **~0x7ED17000–~~0x7ED37DAA~~ 0x7ED37DA9** (0x7ED37DAA is the first panel class, 15a §1; 0x7ED16FE7 crosses 0x7ED17000 (L1 2026-11-09)) / | 0x7ED37DAA is the first GCPnl_* class (15a §1, fn start); the old end overlapped it by 1 B |
| 13d-gui-toolkit.md | drawing parts (0x7ED2F000–0x7ED37DAA) | drawing parts (~0x7ED2F000–~~0x7ED37DAA~~ 0x7ED37DA9 (L1 2026-11-09)) | as above; 0x7ED2EF75 crosses 0x7ED2F000 |
| 13d-gui-toolkit.md | / ~0x7ED82200–0x7ED82820 / | / ~0x7ED82200–~~0x7ED82820~~ 0x7ED8281F (the next row starts at 0x7ED82820 (L1 2026-11-09)) / | next row 0x7ED82820 (fn start) |
| 13d-gui-toolkit.md | and 0x7ED2F000–0x7ED37DAA (both are round bounds: | and 0x7ED2F000–~~0x7ED37DAA~~ 0x7ED37DA9 (L1 2026-11-09) (both are round bounds: | as row 20 |
| 13d-gui-toolkit.md | No CA_MAIN code (0x7ECCB800–0x7ECE4000) | No CA_MAIN code (0x7ECCB800–~0x7ECE4000 (L1 2026-11-09)) | search window; marked approximate |
| 13e-mcon-sequencers.md | ~0x7E59A24C–0x7E5AB7FF (entries | ~0x7E59A24C–~~0x7E5AB7FF~~ ~0x7E5AB877 (`--takerdy--` 0x7E5AB7E3 crosses 0x7E5AB7FF; 0x7E5AB878 opens a device (L1 2026-11-09)) (entries | `fwmap range 0x7E5AB780 0x7E5AB8A0`: 0x7E5AB7E3 (149 B, `--takerdy--`) ends 0x7E5AB877; 0x7E5AB878 = `Failed to open device` |
| 13e-mcon-sequencers.md | / 0x7E701178–0x7E704701 / | / 0x7E701178–~~0x7E704701~~ 0x7E704700 (L1 2026-11-09) / | 0x7E704701 is a fn start (`add -4,sp` after the `ret` at 0x7E7046FE; data word 0x7E8182D8) |
| 13e-mcon-sequencers.md | / 0x7E704702–0x7E706835 / | / ~~0x7E704702–0x7E706835~~ 0x7E704701–0x7E706834 (0x7E704701 and 0x7E706835 are function starts with data-word pointers 0x7E8182D8/0x7E8182B4 (L1 2026-11-09)) / | 0x7E706835 = `movm [d2,d3,a2],(sp)` after `ret` at 0x7E706832 (data word 0x7E8182B4) |
| 13e-mcon-sequencers.md | / 0x7E706836–0x7E706F79 / | / ~~0x7E706836–0x7E706F79~~ 0x7E706835–0x7E706FA2 (it ends with 0x7E706F79, 42 B, called by 0x7E6FE35B (L1 2026-11-09)) / | 0x7E706F79 (42 B, ← 0x7E6FE35B) ends 0x7E706FA2; next row starts 0x7E706FA3 |
| 13e-mcon-sequencers.md | (not ~0x7E6FC000–0x7E708000). 0x7E6FC000–0x7E6FCA5F is face code | (not ~~~0x7E6FC000–0x7E708000~~ (L1 2026-11-09)). ~0x7E6FC000–0x7E6FCA5F (the face code starts before 0x7E6FC000 (L1 2026-11-09)) is face code | quoted old value struck; 0x7E6FBFB4 crosses 0x7E6FC000 |
| 13f-drivers.md | the driver code in 0x7E421020–0x7E521020, | the driver code in 0x7E421020–~0x7E521020 (the regions-table window; 0x7E520E2D crosses its end (L1 2026-11-09)), | 0x7E520E2D crosses 0x7E521020 (regions-table window) |
| 13f-drivers.md | **Driver code in 0x7E421020–0x7E521020.** | **Driver code in 0x7E421020–~0x7E521020 (L1 2026-11-09).** | as above |
| 13f-drivers.md | / 0x7E44D6EF–0x7E44D7FF / Kernel tick timers / | / 0x7E44D6EF–~~0x7E44D7FF~~ 0x7E44D7D1 (0x7E44D7D2 is a printf-style formatter with 48 callers (L1 2026-11-09)) / Kernel tick timers / | 0x7E44D7D2 (99 B, 48 callers, varargs frame sp+336, callers include `return %x` 0x7E44D835) is a formatter; 0x7E44D7B8 (26 B) ends 0x7E44D7D1 |
| 14a-c3d-graphics.md | The "151 incoming calls into 0x7EE61020–0x7EE81020" could not | The "151 incoming calls into ~~0x7EE61020–0x7EE81020~~" (L1 2026-11-09) could not | quoted unreproduced claim, struck |
| 14b-unlabelled-platform-camera.md | (through 8-byte call stubs 0x7E51789C–0x7E517930) | (through the 8-byte case blocks 0x7E51789C–0x7E517930 of the jump table inside 0x7E51787B; they are not separate functions (L1 2026-11-09)) | disasm 0x7E51789A `jmp (a1)`; 0x7E51789C `mov a2,a0; call 0x7E517952; jmp 0x7E517935` = case blocks inside 0x7E51787B |
| 14b-unlabelled-platform-camera.md | inside 0x7E643800–0x7E64F2A1 | inside ~0x7E643800–0x7E64F2A1 (L1 2026-11-09) | 0x7E6437F1 crosses 0x7E643800 |
| 14c-app-protocols.md | the C++ app layer 0x7E966000–0x7EBA0AA8 | the C++ app layer ~~0x7E966000~~ 0x7E966A17–0x7EBA0AA8 (L1 2026-11-09) | 14c §1 row 12: module starts 0x7E966A17 |
| 14c-app-protocols.md | 0x7E966000–0x7E966A16 is the printf-style formatter | ~~0x7E966000~~ 0x7E96604E–0x7E966A16 (L1 2026-11-09) is the printf-style formatter | fn 0x7E965FD1 spans 0x7E965FD1–0x7E96604D; next start 0x7E96604E |
| 14d-data-and-blobs.md | except the code segment 0x7E8F5800–0x7EBABF8F. | except the code segment 0x7E8F5800–~~0x7EBABF8F~~ 0x7EBABF8D (its last `ret` ends there; 0x7EBABF8E–0x7EBABF8F are 0xFF) (L1 2026-11-09). | disasm 0x7EBABF8B `ret`, 0x7EBABF8E/F = 0xFF; line 29 already gives 0x7EBABF8D |
| 14d-data-and-blobs.md | a jump table 0x7E731714 into libc 0x7E4FEB34–0x7E4FEC8F (printf format switch, I) | a jump table 0x7E731714 (40 words) whose case targets 0x7E4FEB34–0x7E4FEC8F lie inside the libc function 0x7E4FEA8D (printf format switch, I; (L1 2026-11-09)) | 40 words at 0x7E731714, all targets in 0x7E4FEB34–0x7E4FEC8F, all inside fn 0x7E4FEA8D–0x7E4FECF9 |
| 14d-data-and-blobs.md | / "0x7E730000–0x7E8E0000 Mostly read-only data | / "~~0x7E730000–0x7E8E0000~~ (L1 2026-11-09) Mostly read-only data | quoted old regions row, struck |
| 14d-data-and-blobs.md | / "0x7EBA1020–0x7ECA0000 … data from about 0x7EBAC000" | / "~~0x7EBA1020–0x7ECA0000~~ (L1 2026-11-09) … data from about 0x7EBAC000" | quoted old regions row, struck |
| 14d-data-and-blobs.md | / "0x7ECA1020–~0x7ECC8000 is mostly data. | / "~~0x7ECA1020–~0x7ECC8000~~ (L1 2026-11-09) is mostly data. | quoted old 13d row, struck |
| 14e-gui-methods.md | / 0x7EDCB0C5–0x7EDCB1E0 / | / 0x7EDCB0C5–~~0x7EDCB1E0~~ 0x7EDCB1FB (matcher 2 = 0x7EDCB1C5, 55 B; matcher table 0x7EFE2FF8 (L1 2026-11-09)) / | matcher table 0x7EFE2FF8 = {0x7EDCB151, 0x7EDCB18F, 0x7EDCB1C5}; 0x7EDCB1C5 (55 B) ends 0x7EDCB1FB; 0x7EDCB1FC is a 19-B fn with 1 caller (not a matcher) |
| 15a-gui-pages.md | # 15a. GUI app 0x7ED40000–0x7EE02094: | # 15a. GUI app ~~0x7ED40000~~ 0x7ED37DAA–0x7EE02094 (L1 2026-11-09): | 15a §1 first row 0x7ED37DAA–0x7ED82275 (fn start) |
| 15a-gui-pages.md | replaces 13d §1 rows "0x7EDC15B0–~0x7EDE0000" and "~0x7EDE0000–0x7EE01FF5" | replaces 13d §1 rows "~~0x7EDC15B0–~0x7EDE0000~~" and "~~~0x7EDE0000–0x7EE01FF5~~" (L1 2026-11-09) | quoted old 13d rows, struck (13d now has other values) |
| 15a-gui-pages.md | the action handlers 0x7EDDD21D–0x7EDE0383, | the action handlers 0x7EDDD21D–~~0x7EDE0383~~ 0x7EDE03CE (0x7EDE0384 is inside the last handler 0x7EDE033E (L1 2026-11-09)), | disasm 0x7EDE0370–0x7EDE03CE: 0x7EDE0384 is mid-instruction (`mov (0x602bdf18),d0` at 0x7EDE0380) in 0x7EDE033E, which ends 0x7EDE03CE; 0x7EDE03CF = gesture listener region start |
| 15a-gui-pages.md | **Address in 0x7EDDD21D–0x7EDE0383:** | **Address in 0x7EDDD21D–~~0x7EDE0383~~ 0x7EDE03CE (L1 2026-11-09):** | as above |
| 15a-gui-pages.tsv | 0x7EDDD21D-0x7EDE0383 region **GuiTouch action handlers**: per-panel touch-action tables and their handlers (touch-action rows); | 0x7EDDD21D-0x7EDE03CE region **GuiTouch action handlers**: per-panel touch-action tables and their handlers (touch-action rows); end was 0x7EDE0383, inside the last handler 0x7EDE033E (L1 2026-11-09); | as above |
| 15b-camera-core-index.md | (E-PM2 v1.6, 0x7E520000–0x7E731588) | (E-PM2 v1.6, ~0x7E520000–~~0x7E731588~~ 0x7E731584 (L1 2026-11-09)) | title: 0x7E51FFF4 crosses 0x7E520000 (kept ~); code ends at the `ret` 0x7E731582–84 (14d) |
| 15b-camera-core-index.md | / 0x7E63BAA6–0x7E63D0DD / cam_imgdev.c command layer: | / 0x7E63BAA6–~~0x7E63D0DD~~ 0x7E63D1C0 (it ends with the `cam_imgdev.c` dumper 0x7E63D0DD (L1 2026-11-09)) / cam_imgdev.c command layer: | 0x7E63D0DD (228 B) loads `cam_imgdev.c`/`IMGDEV` (it is the command-layer dumper) and ends 0x7E63D1C0 |
| 15b-camera-core-index.md | / **0x7E63D0DE–0x7E63EC58** / | / **~~0x7E63D0DE~~ 0x7E63D1C1–0x7E63EC58** (L1 2026-11-09) / | 0x7E63D1C1 is a fn start (24 B, 8 callers, calls driver 0x7E63E515) |
| 15b-camera-core-index.md | `7e63d0de 7e6401ff imgdev driver/sequences` | `7e63d1c1 7e6401ff imgdev driver/sequences` (was 7e63d0de (L1 2026-11-09)) | modules.tsv proposal list updated to the same start |
| 15b-camera-core-index.md | "EXP_MOVIE … about 0x7E68F000–0x7E6A0000" | "EXP_MOVIE … about ~~0x7E68F000–0x7E6A0000~~" (L1 2026-11-09) | quoted old value, struck |
| 15b-camera-core-index.md | BC is 0x7E53AEA9–0x7E542B4E; | BC is 0x7E53AEA9–~~0x7E542B4E~~ ~0x7E542BA5 (0x7E542B4E is inside `[BC FUP]VERIFY` 0x7E542AFE, which ends at 0x7E542BA5; where BC ends after it was not traced (L1 2026-11-09)); | `fwmap range 0x7E542A80 0x7E542C00`: 0x7E542AFE `[BC FUP]VERIFY` (168 B) ends 0x7E542BA5; 0x7E542B4E is mid-function (disasm); later fns not traced |
| 15b-camera-core-index.md | 0x7E667400–0x7E675000 is the mdet library and res | ~~0x7E667400–0x7E675000~~ 0x7E666C5B–0x7E675D98 (mdet 0x7E666C5B–0x7E674DF4 and res 0x7E674DF5–0x7E675D98, §4 (L1 2026-11-09)) is the mdet library and res | 15b §4 table: mdet 0x7E666C5B–0x7E674DF4, res 0x7E674DF5–0x7E675D98 (fn 0x7E675B1E ends 0x7E675D98) |
| 15b-camera-core-index.tsv | 0x7E63BAA6-0x7E63D0DD range cam_imgdev.c command layer: | 0x7E63BAA6-0x7E63D1C0 range cam_imgdev.c command layer (end was 0x7E63D0DD, the start of its `cam_imgdev.c` dumper (L1 2026-11-09)): | as md row |
| 15b-camera-core-index.tsv | 0x7E63D0DE-0x7E63EC58 range imgdev driver | 0x7E63D1C1-0x7E63EC58 range (start was 0x7E63D0DE (L1 2026-11-09)) imgdev driver | as md row |
| 15c-app-statecharts.md | the C++ app layer 0x7E966000–0x7EBA48BB | the C++ app layer ~~0x7E966000~~ 0x7E966A17–0x7EBA48BB (L1 2026-11-09) | 14c/13c: module starts 0x7E966A17 |
| 15c-app-statecharts.md | Ranges in the Tra/Ope area (0x7E966000–0x7E9EB317) | Ranges in the Tra/Ope area (~~0x7E966000~~ 0x7E966A17–0x7E9EB317 (L1 2026-11-09)) | as above (my own L1 sentence; the class index starts at 0x7E967145) |
| 15d-protocols-platform.md | DPS engine in overlay A (not 0x7F061020–0x7F068F9C) | DPS engine in overlay A (not ~~0x7F061020–0x7F068F9C~~ (L1 2026-11-09)) | quoted old value of 08, struck |
| 15d-protocols-platform.md | "DPS XML library 0x7F061020–0x7F068F9C". | "DPS XML library ~~0x7F061020–0x7F068F9C~~" (L1 2026-11-09). | quoted old value of 08, struck |
| 15d-protocols-platform.md | / 0x7E925A49–0x7E926692 / BT API wrappers | / 0x7E925A49–~~0x7E926692~~ 0x7E9266BD (`BT_SetSecurity` 0x7E926620 ends at 0x7E9266B8, then a 5-B stub 0x7E9266B9; ME + SEC resumes at 0x7E9266BE (L1 2026-11-09)) / BT API wrappers | `fwmap range 0x7E926500 0x7E926720`: 0x7E926620 `BT_SetSecurity set SSP` (153 B) ends 0x7E9266B8; 0x7E9266B9 (5 B, 0 callers); ME+SEC row restarts at 0x7E9266BE (fn start) |
| 15d-protocols-platform.tsv | 0x7E925A49..0x7E926692 bt-api synchronous BT API wrappers | 0x7E925A49..0x7E9266BD bt-api (end was 0x7E926692 (L1 2026-11-09)) synchronous BT API wrappers | as md row |

## 3. Lint hits left in sections 09–15

Lint before: 169 hits in these files (audit/boundary-lint-1.tsv). After this pass: **131** (whole map: 172, from 242). Every remaining hit has one of these reasons:

| class | count | reason |
|---|---|---|
| A | 57 | data range (strings, tables, LUTs, blobs, rodata, 0xFF fill); the text says data; the code rule does not apply |
| B | 24 | code range whose true edge is a verified `ret` before padding/data (OKAO PT 0x7E731584, Smart Skin 0x7EBABF8D, AVPI/segment-3 0x7EECE318, code block 0x7E880F43, segment-2 code 0x7EBABF8D) or a pointer-only stub that the DB merges into the previous function (0x7EBA79D8, 0x7ED82276, 0x7EDB4B9E); known lint limit |
| C | 26 | explicitly approximate: written with "~"/"about"/"round bound", or a page-rounded search, compare or count window whose bounds define the result |
| D | 12 | byte, case or call-site span inside one function (or a run of sites), labelled as such |
| E | 12 | name of a regions-table row (1 MiB block window) or a quoted window of another section or the brief, being corrected in the same sentence |

Per file: 10b-shooting-modes.md D1; 10d-playback.md C1; 10e-connectivity.md C1, D1; 10f-debug-service.md D1; 11-version-history.md C4; 12-exposure-af-files.md C1; 13a-libraries-runtime.md A1, E2; 13b-libraries-face-av.md A4, B6, D2; 13c-cpp-framework.md B4, C3; 13d-gui-toolkit.md A5, B1, C8, D2; 13e-mcon-sequencers.md C1; 13f-drivers.md C2; 14a-c3d-graphics.md A4, D2, E2; 14b-unlabelled-platform-camera.md C1, D1, E1; 14c-app-protocols.md C2; 14d-data-and-blobs.md A42, B11, D1, E3; 15a-gui-pages.md A1, B1, D1; 15b-camera-core-index.md C2, E3; 15c-app-statecharts.md B1; 15d-protocols-platform.md E1.

Per-hit list (file, line, range, class):

| file | line | range | class |
|---|---|---|---|
| 10b-shooting-modes.md | 60 | 0x7E663939–0x7E6639E8 | D |
| 10d-playback.md | 54 | 0x7E9CD000–~0x7E9E2000 | C |
| 10e-connectivity.md | 85 | 0x7E508F00–~0x7E50D700 | C |
| 10e-connectivity.md | 87 | 0x7F080B39–0x7F080BC2 | D |
| 10f-debug-service.md | 123 | 0x7EDABA14–0x7EDABA54 | D |
| 11-version-history.md | 19 | 0x7E5E3000–~0x7E627000 | C |
| 11-version-history.md | 82 | 0x7E512000–~0x7E51C000 | C |
| 11-version-history.md | 144 | 0x7E5E3000–~0x7E627000 | C |
| 11-version-history.md | 184 | 0x7E512000–~0x7E51C000 | C |
| 12-exposure-af-files.md | 137 | 0x7E5E2C00–0x7E627E9E | C |
| 13a-libraries-runtime.md | 78 | 0x7E73170C–0x7E731904 | A |
| 13a-libraries-runtime.md | 283 | 0x7E4E0000–0x7E521020 | E |
| 13a-libraries-runtime.md | 283 | 0x7E521020–0x7E621020 | E |
| 13b-libraries-face-av.md | 14 | 0x7E72CFA1–0x7E731584 | B |
| 13b-libraries-face-av.md | 14 | 0x7E86DD80–0x7E8808BF | A |
| 13b-libraries-face-av.md | 15 | 0x7EBA7BC1–0x7EBABF8D | B |
| 13b-libraries-face-av.md | 15 | 0x7EC92318– 0x7ECB083B | A |
| 13b-libraries-face-av.md | 16 | 0x7F068FB6–0x7F069093 | D |
| 13b-libraries-face-av.md | 18 | 0x7EE8F4F4–0x7EECE318 | B |
| 13b-libraries-face-av.md | 24 | 0x7F02E947–0x7F02EB24 | A |
| 13b-libraries-face-av.md | 25 | 0x7F02EB68–0x7F02F683 | A |
| 13b-libraries-face-av.md | 114 | 0x7F066995–0x7F0669DE | D |
| 13b-libraries-face-av.md | 132 | 0x7EE8F4F4–0x7EECE318 | B |
| 13b-libraries-face-av.md | 142 | 0x7EECC670–0x7EECE318 | B |
| 13b-libraries-face-av.md | 240 | 0x7EBA7BC1–0x7EBABF8D | B |
| 13c-cpp-framework.md | 3 | 0x7EBA7BC1–0x7EBABF8D | B |
| 13c-cpp-framework.md | 20 | 0x7EBA79D8–0x7EBA7B98 | B |
| 13c-cpp-framework.md | 21 | 0x7EBA7BC1–0x7EBABF8D | B |
| 13c-cpp-framework.md | 78 | 0x7E966000–0x7EBA4868 | C |
| 13c-cpp-framework.md | 122 | 0x7E96B000–0x7E9823AB | C |
| 13c-cpp-framework.md | 122 | 0x7E9EA000–0x7EB80000 | C |
| 13c-cpp-framework.md | 247 | 0x7EBA7BC1–0x7EBABF8D | B |
| 13d-gui-toolkit.md | 14 | 0x7ECA1020–0x7ECCB7FF | A |
| 13d-gui-toolkit.md | 14 | 0x7EC92318–0x7ECAFF3C | A |
| 13d-gui-toolkit.md | 14 | 0x7ECB083C–0x7ECB0887 | A |
| 13d-gui-toolkit.md | 14 | 0x7ECB0888–0x7ECB0FFF | A |
| 13d-gui-toolkit.md | 15 | 0x7ECCB800–~0x7ECE4000 | C |
| 13d-gui-toolkit.md | 16 | 0x7ECE4000–0x7ECEC798 | C |
| 13d-gui-toolkit.md | 20 | 0x7ED17000– 0x7ED37DA9 | C |
| 13d-gui-toolkit.md | 20 | 0x7ED2F000– 0x7ED37DA9 | C |
| 13d-gui-toolkit.md | 22 | 0x7ED82200– 0x7ED8281F | C |
| 13d-gui-toolkit.md | 64 | 0x7ED37EA5–0x7ED37EE7 | D |
| 13d-gui-toolkit.md | 121 | 0x7ECF5000–0x7ECFF000 | C |
| 13d-gui-toolkit.md | 121 | 0x7ED2F000– 0x7ED37DA9 | C |
| 13d-gui-toolkit.md | 197 | 0x7EDB4B9E–0x7EDB6DB0 | B |
| 13d-gui-toolkit.md | 226 | 0x7EDABA14–0x7EDABA54 | D |
| 13d-gui-toolkit.md | 230 | 0x7ECCB800–~0x7ECE4000 | C |
| 13d-gui-toolkit.md | 335 | 0x7ECA1020–0x7ECCB7FF | A |
| 13e-mcon-sequencers.md | 252 | 0x7E6FC000–0x7E6FCA5F | C |
| 13f-drivers.md | 3 | 0x7E421020–~0x7E521020 | C |
| 13f-drivers.md | 13 | 0x7E421020–~0x7E521020 | C |
| 14a-c3d-graphics.md | 15 | 0x7EE026DC–0x7EE2946F | D |
| 14a-c3d-graphics.md | 16 | 0x7EE68935–0x7EE8ED9E | D |
| 14a-c3d-graphics.md | 47 | 0x7F02AA14–0x7F02AD23 | A |
| 14a-c3d-graphics.md | 49 | 0x7F02B24B–0x7F02EB67 | A |
| 14a-c3d-graphics.md | 50 | 0x7F02EB68–0x7F02F683 | A |
| 14a-c3d-graphics.md | 302 | 0x7ECA1020–0x7EE21020 | E |
| 14a-c3d-graphics.md | 302 | 0x7EE21020–0x7EEE1020 | E |
| 14a-c3d-graphics.md | 310 | 0x7F02EB68–0x7F02F683 | A |
| 14b-unlabelled-platform-camera.md | 177 | 0x7E51789C–0x7E517930 | D |
| 14b-unlabelled-platform-camera.md | 205 | 0x7E4E0000–0x7E521020 | E |
| 14b-unlabelled-platform-camera.md | 241 | 0x7E643800–0x7E64F2A1 | C |
| 14c-app-protocols.md | 154 | 0x7E966000–0x7EBA4868 | C |
| 14c-app-protocols.md | 158 | 0x7E966000–0x7EBC0000 | C |
| 14d-data-and-blobs.md | 3 | 0x7E8F5800– 0x7EBABF8D | B |
| 14d-data-and-blobs.md | 3 | 0x7E730000–0x7E8F0000 | E |
| 14d-data-and-blobs.md | 3 | 0x7EBB0000–0x7ECA1020 | E |
| 14d-data-and-blobs.md | 22 | 0x7E72CFA1–0x7E731584 | B |
| 14d-data-and-blobs.md | 23 | 0x7E731588–0x7E8808BF | A |
| 14d-data-and-blobs.md | 23 | 0x7E4FE000–0x7E731584 | B |
| 14d-data-and-blobs.md | 24 | 0x7E8808C0–0x7E880F43 | B |
| 14d-data-and-blobs.md | 26 | 0x7E880F5C–0x7E8D9FFF | A |
| 14d-data-and-blobs.md | 29 | 0x7E8F5800–0x7EBABF8D | B |
| 14d-data-and-blobs.md | 30 | 0x7EBABF90–0x7ECB083B | A |
| 14d-data-and-blobs.md | 31 | 0x7ECB083C–0x7ECB0887 | A |
| 14d-data-and-blobs.md | 32 | 0x7ECB0888–0x7ECCB7FF | A |
| 14d-data-and-blobs.md | 53 | 0x7E731588–0x7E7323FF | A |
| 14d-data-and-blobs.md | 53 | 0x7E4FEB34–0x7E4FEC8F | D |
| 14d-data-and-blobs.md | 56 | 0x7E737A60–0x7E73B48B | A |
| 14d-data-and-blobs.md | 56 | 0x7E737AE0–0x7E73B257 | A |
| 14d-data-and-blobs.md | 57 | 0x7E73B48C–0x7E7430FF | A |
| 14d-data-and-blobs.md | 60 | 0x7E74E000–0x7E763FFF | A |
| 14d-data-and-blobs.md | 60 | 0x7E764000–0x7E7885FF | A |
| 14d-data-and-blobs.md | 62 | 0x7E790C00–0x7E795BFF | A |
| 14d-data-and-blobs.md | 63 | 0x7E795C00–0x7E79F1FF | A |
| 14d-data-and-blobs.md | 69 | 0x7E7E2000–0x7E7E494F | A |
| 14d-data-and-blobs.md | 70 | 0x7E7E4950–0x7E7EFD4F | A |
| 14d-data-and-blobs.md | 71 | 0x7E7EFD50–0x7E7F023F | A |
| 14d-data-and-blobs.md | 82 | 0x7E85CEFC–0x7E86DD5F | A |
| 14d-data-and-blobs.md | 82 | 0x7E86DC5F–0x7E86DD5F | A |
| 14d-data-and-blobs.md | 83 | 0x7E86DD80–0x7E8808BF | A |
| 14d-data-and-blobs.md | 84 | 0x7E880F5C–0x7E8D9FFF | A |
| 14d-data-and-blobs.md | 87 | 0x7EBABF90–0x7EBB11FF | A |
| 14d-data-and-blobs.md | 91 | 0x7EBC39D0–0x7EBCAABF | A |
| 14d-data-and-blobs.md | 92 | 0x7EBCAAC0–0x7EBCDAFF | A |
| 14d-data-and-blobs.md | 93 | 0x7EBCDB00–0x7EBD03FF | A |
| 14d-data-and-blobs.md | 98 | 0x7EC92318–0x7ECB083B | A |
| 14d-data-and-blobs.md | 99 | 0x7ECB0888–0x7ECCB7FF | A |
| 14d-data-and-blobs.md | 146 | 0x7E86DD80–0x7E8808BF | A |
| 14d-data-and-blobs.md | 165 | 0x7E7E4950–0x7E7EFD4F | A |
| 14d-data-and-blobs.md | 172 | 0x7EBC39D0–0x7EBCAABF | A |
| 14d-data-and-blobs.md | 185 | 0x7EC92318–0x7ECB083B | A |
| 14d-data-and-blobs.md | 187 | 0x7EBA7BC1–0x7EBABF8D | B |
| 14d-data-and-blobs.md | 193 | 0x7EC924C4–0x7EC9FD3A | A |
| 14d-data-and-blobs.md | 194 | 0x7EC9FD3B–0x7ECAFD3A | A |
| 14d-data-and-blobs.md | 199 | 0x7E85CEFC–0x7E86DD5F | A |
| 14d-data-and-blobs.md | 203 | 0x7E737A60–0x7E73B48B | A |
| 14d-data-and-blobs.md | 243 | 0x7E737AE0–0x7E73B257 | A |
| 14d-data-and-blobs.md | 245 | 0x7E74E000–0x7E763FFF | A |
| 14d-data-and-blobs.md | 281 | 0x7E4FE000–0x7E731584 | B |
| 14d-data-and-blobs.md | 281 | 0x7E8808C0–0x7E880F43 | B |
| 14d-data-and-blobs.md | 281 | 0x7E8F5800–0x7EBABF8D | B |
| 14d-data-and-blobs.md | 281 | 0x7ECCB800–0x7EECE318 | B |
| 14d-data-and-blobs.md | 298 | 0x7E731588–0x7E8808BF | A |
| 14d-data-and-blobs.md | 298 | 0x7E880F5C–0x7E8D9FFF | A |
| 14d-data-and-blobs.md | 300 | 0x7EC92318–0x7ECB083B | A |
| 14d-data-and-blobs.md | 301 | 0x7ECB083C–0x7ECB0887 | A |
| 14d-data-and-blobs.md | 305 | 0x7E86DD80–0x7E8808BF | A |
| 14d-data-and-blobs.md | 310 | 0x7E85CEFC–0x7E86DCFF | A |
| 14d-data-and-blobs.md | 318 | 0x7E6E0000–0x7E730000 | E |
| 14d-data-and-blobs.md | 318 | 0x7E72CFA1–0x7E731584 | B |
| 15a-gui-pages.md | 24 | 0x7ED82276–0x7EDC15B0 | B |
| 15a-gui-pages.md | 177 | 0x7ED1C38D–0x7ED1C4B7 | D |
| 15a-gui-pages.md | 210 | 0x7EFE3D98–0x7EFE4057 | A |
| 15b-camera-core-index.md | 1 | 0x7E520000– 0x7E731584 | C |
| 15b-camera-core-index.md | 253 | 0x7E520000–0x7E731588 | C |
| 15b-camera-core-index.md | 270 | 0x7E621020–0x7E6A1020 | E |
| 15b-camera-core-index.md | 271 | 0x7E6A1020–0x7E70B000 | E |
| 15b-camera-core-index.md | 271 | 0x7E6A1020–0x7E6C3954 | E |
| 15c-app-statecharts.md | 3 | 0x7EBA7BC1–0x7EBABF8D | B |
| 15d-protocols-platform.md | 286 | 0x7E913984–0x7E91CFFF | E |

## 4. Notes for the 01–08 editor and the coordinator (not applied: outside sections 09–15)

- **01-platform.md line 142:** the U_SHELL table row still says `file | 7E5C2139 (stub)`. 0x7E5C2139 is the indirect (prologue) entry of 0x7E5C213E (see §1, 13f row).
- **02-lens-power-firmup-take.md line 15:** BC end 0x7E542B4E is inside `[BC FUP]VERIFY` 0x7E542AFE (ends 0x7E542BA5). 15b now says ~0x7E542BA5.
- **Differs from the C4 reviews (bytes win):** the `face` table has 20 subcommands, not 17 (start, stop, pt were left out), and F021 0x7E6F591D is `face reg`, not `face mdm` (0x7E6F5840). The old 15c row "TraShareTakeStatus" (ctor 0x7E967145, vt 0x7EBCDBB4, RAM 0x602B0C78) is the HLS log-level object; TraShareTakeStatus itself is a static module 0x7E9698EC–0x7E96B13B. Section 12 had no Exif-writer range to change.
- **15a key code 26** was already in the table (grouped as 26/27/28 = END_DIRECT/POPUP/mode dial); it now has its own row with both events and handlers.

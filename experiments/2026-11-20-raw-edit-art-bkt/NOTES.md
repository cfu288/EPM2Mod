# ART BKT in RAW Data Edit: desk study (2026-11-20)

Goal (owner): a row **ART BKT** in RAW Data Edit that develops the RAW once per entry that is On in the ART BKT
setting, one JPEG each, as a capture ART bracket does. Use: develop the test RAW
(`experiments/2026-11-09-film-portra/testraw/PB130001.ORF`) and site photos in all 12 film entries in one go.

Labels: V = read in the firmware bytes or run in the emulator, I = inferred, U = unknown (with the probe).
All addresses are E-PM2 v1.6 block 0 unless marked PEN-F (PEN-F 3.1, base 0x60021020). No build was made.

## 1. E-PM2 RAW Data Edit

### 1.1 Menu

| Item | Finding | Label |
|---|---|---|
| Path | PLAY → OK → **RAW Data Edit** → OK → list "Current, Custom1, Custom2, No" (emulator: `results/raw-ok-menu.png`, `results/raw-data-edit-list.png`). Manual p. 65: Playback Menu → Edit → Sel. Image → OK → RAW Data Edit | V |
| Texts | 569 "RAW Data Edit", 1760 "Current", 1761 "Custom1", 1762 "Custom2", 496 "No". "ART BKT" exists: 710 and 1699 | V |
| Items | 0x7F00D368, 4 × 12 B `{u16 2, u16 text, 8 B 0}`. Followed directly by the shared Yes/No items 0x7F00D398 | V |
| Descriptor | List 320 in the list table (entry at 0x7F00E000 → 0x7F00D55C): `{u16 569 title, u16 0x0100, u32 0, u32 count 4 (at 0x7F00D564), u32 items 0x7F00D368 (at 0x7F00D568)}` | V |
| Page class | Factory 0x7EDF7C47 (registry row 0x7EFE20FC: list 320). Cursor restore 0x7EDF7CB2 reads GUI setting 527 (rows 0–3) | V |
| OK handler | **0x7EDF7DDD**, row byte at page+1744. Row 0 → `OlyApiEditRaw` vt+32 = startCurrentModeEdit (API 0x031B03), callback 0x7EE00760; writes 527 = 0. Rows 1, 2 → 527 = row, vt+36 = startCustomEdit(d0 = 0, 1). Row 3 → close (0x7EDF7F26) | V |
| API | `OlyApiEditRaw` getter 0x7E9C34D1, vtable 0x7EC0EBBC. Ids by slot: +0 save 01, +4 canRaw 02, +8 endCurrent 06, +12 endCustom 0A, +16 previewCurrent 04, +20 previewCustom 08, +24 saveCurrent 05, +28 saveCustom 09, +32 startCurrent 03, +36 startCustom 07 (names from the string table 0x7E8E1F28 in id order) | V ids; I names |

### 1.2 The development job

| Step | Finding | Label |
|---|---|---|
| Component | `CmpERaw_EditRawComponent` (T_GUI). Kind at +564: 0 Custom1, 1 Custom2, **2 Current** (set by state_start_current_mode 0x7EAD0163) | V |
| [Current] order in the emulator | start_current_mode_edit 0x7EAD1687 → state_start_current_mode 0x7EAD0163 → preview_current_start 0x7EAD2633 → preview_current 0x7EAD278D → state_preview 0x7EACFD75 → check_execute_edit_raw 0x7EACF5D6 → RAW load (play_load_raw_load_prim_raw 0x7E947719) → stops in play_cic_decode_raw 0x7E93D10F (section 5) | V |
| Settings for Custom | check_execute_edit_raw fills `_current_edit_info` (+1032) from info ids 495–523: exp_rev, tone, wb_mode, mwb, custom_wb, owb, **color_tone = 509 / 510**, filter, ps, aspect, color_space, wb_kelvin. For kind 2 it fills nothing | V |
| Settings for Current | The play side reads the stored Picture Mode, prm 0x9481, in play_exif_get_default_raw 0x7E941BC6 (from play_edit_raw_set_exif_default 0x7E94113F, in the preview step) | V read |
| Where the developer takes the Picture Mode | The developer's mode byte is take context +16479 (`rec_art_set_exif_data` jumps on it). Its only constant-offset writer is the bracket frame copy 0x7E71099C. Which step fills it for a RAW edit, preview or save, is not found | **U** (probe P1) |
| Play commands | play_edit_main 0x7E940D7C (hash 0x7EBB8D88). 0x92–0x94 → play_edit_raw_main 0x7E940F1A (sets prm 0x8441 = 0 around the job and restores it) → play_edit_raw_edit 0x7E940F77 → play_rec_raw_edit 0x7E948E4F mode 1 (REC_MAIN message 0x1003), then a 4608 × 3456 resize | V |
| Save | Command 0x90 with buffer mode 0x500 → **play_save_raw 0x7E94B011**: space check 0x7E9435B4, api_rec_Reserve_Media 0x7E688268 (error 14594 = 0x3902 when the card is full), file date, play_rec_raw_edit mode 3 → REC_MAIN message 0x100F. REC_MAIN (0x7E70B435, queue 0x58) develops, names and writes the JPEG | V code; I that REC_MAIN names the file |
| Return | Completion reaches CmpERaw edit_raw_exe_end 0x7EACFA70 ("SUCCESS/ERR EditRaw_PlayPicture") → state_end_edit 0x7EACFC3F; the page's RawEditProcessCallback 0x7EDF7F60 acts on command 47, status 3 or 164 | V strings and compares; I meaning |
| File name prefix | app_select_option_rawedit_change_mode 0x7EB0E1D5: colour space (info 519 / 520 / 60) → file name prefix from settings 147–154 | V |

## 2. E-PM2 capture ART BKT

| Item | Finding | Label |
|---|---|---|
| Composer | Function 0x7E5A7591 (908 B, segment 1), called once from take setup 0x7E5A634B. Gate: prm 0xD191 (53649) ≠ 0, stored at take+17152. **0x7E5A75AE** (after the gate) reads prm 0x9481 = current value | V |
| Frame list | take+17154, 18 B per frame, ended by value 0. Frame 0 = current Picture Mode with the take's live fields (0x7E5A791D). Then one frame per value whose flag is On and that is not the current value | V |
| Flags | prm tags 0xD1A1–0xD201 (Picture Modes) and 0xD211 + 16·(v − 100) for ART values, 0xDD81 one more; the GUI ids are 345–361, 414–424, 443, 469, 470 (films-max §3) | V tags; I tag ↔ id |
| Per-entry fill | One small function per value (e.g. 0x7E5A79C4 for 101: value + prm 0x44D1 sub-setting) | V |
| Per frame | REC IMAGE bracket_update 0x7E7100D7 → 0x7E71099C copies frame k into take+16479 (mode), +16446…+17145 | V |
| Films | stock-films hooks (30) in the composer and the two list builders 0x7EA7633A, 0x7EA9528D give hidden entries their values. Camera 2026-11-18: one shot = Natural + 12 JPEGs, each its film, codes in menu order | V camera |
| On the RAW edit path? | No. RAW edit messages go to REC_MAIN, not to the capture layer that calls the composer | I (strong) |

## 3. PEN-F (the reference)

Traced by a sub-agent; disassemblies in the session scratch, not kept.

| Layer | PEN-F | Label |
|---|---|---|
| List | Items 0x60FDB6D8: Current 1843, Custom1 1844, Custom2 1845, **ART BKT 1782**, No 496; descriptor 0x60FDB8F4, count 5, title 569 | V |
| OK handler | 0x60D3E685, row byte +1776: 3 = ART BKT. Gate 0x60D3E881: start only if one of 41 flag ids (table 0x60FD9460) is On, else stay on the list | V |
| API | startArtBktEdit vt+36 (0x031B0B), saveArtBktEdit vt+40, endArtBktEdit vt+44 | V |
| Component | Kind 3 = ART BKT: state_start_artbkt_edit 0x608AC506 → state_save_artbkt_edit 0x608AC22A → edit_artbkt_raw_exe_end 0x608AB216 | V |
| Play | api_play_EditArtBktRaw_PlayPicture 0x602FFFC0 → command 0x97 → play_edit_raw_edit_artbkt 0x60AF2DBD: space check for N files (0x60AF6216 counts the On flags), Reserve_Media, play_rec_raw_edit mode 4 → message **0x100A** | V |
| Rec | REC_MAIN develops and writes every frame of the list for 0x100A (0x6052DF38 sets the frame count) | V code; I behaviour |
| Size | ART BKT-only code 3,327 B, plus rec-task branches not sized | V |

The E-PM2 REC_MAIN has no 0x100A / 0x100B branch (no `cmp 4106/4107`). A literal port means new rec-task code. Not
recommended.

## 4. Design for the E-PM2

Loop in the GUI, around the stock [Current] job. Each pass is one complete stock [Current] edit, so each JPEG is
developed, named and written by stock code.

| Part | Change | Size | Label |
|---|---|---|---|
| Row | Copy the 4 items to 5 in free data space: Current, Custom1, Custom2, **ART BKT (710)**, No (the PEN-F order). Descriptor 0x7F00D564 count 4 → 5, 0x7F00D568 → the copy | 60 B data + 8 B | V layout; U whether the box grows (emulator) |
| Dispatch | Hook H1 at 0x7EDF7DF3 (OK handler, segment 3): flag = (row = 3); row 3 → row 0 path, row 4 → the No path | ~30 B | V target |
| Entry list | Call the composer at 0x7E5A75AE with a2 = scratch − 16446 (reads +16446…+17145, writes +17154…): the same list as a capture, with the stock-films hooks. Scratch about 1.3 KB from scheap (0x7E507325 / 0x7E507333) | ~40 B | I (harness can check) |
| Picture Mode | Per frame prm_set(0x9481, value) = 0x7E457CED(d0 tag, a0 0, d1 0, a1 value), the form play_edit_raw_main uses; restore at the end and on any error | ~30 B | V call form; U that nothing resyncs it mid-loop |
| Film name | Per frame call `FILMNAME` (films-look-exif, segment 3 0x7EE53BFE), which reads prm 0x9481 | ~6 B | I |
| Loop | Hook H2 in RawEditProcessCallback 0x7EDF7F60: preview done and flag → call the save API (no Yes/No); save done and frames left → next Picture Mode, previewCurrent (vt+16); last frame → restore, fall through to stock | ~180 B | U: command/status values (desk), API order after a save (camera) |
| Gate | No flag On → the list has frame 0 only → one [Current] edit | 0 B | I |

Total about 300 B code in segment 2 (652 B usable) and 60 B data. H1 and H2 are in segment 3 and jump to segment 2
or 3: the load-order rule allows it; no hookcheck allow entry is expected (I; run `emulator/hookcheck.py`,
`emulator/boot-test`, `emulator/update-path-test`).

Why preview again per frame: the EXIF defaults and maybe the developer's mode byte are taken in the preview step
(section 1.2). A save-only loop is about 100 B smaller and needs P1 to say yes.

## 5. Emulator

- The menu: list 320 drawn (`results/raw-data-edit-list.png`). The new row and the box size can be checked the same
  way. The ART BKT flags screen: MENU, LEFT × 4, OK, DOWN × 12, RIGHT (`results/art-bkt-flags.png`) (V).
- Stock playback of an ORF faults at 0x7E557770 (write to 0x99400004, the image engine, not declared). With
  `scripts/rawedit.mjs` and `PLAIN=99400000,99500000,9a000000` (a scratch stand-in, not a hardware model):

  ```
  cp build/emu/state/stock-p.json /path/to/s.json
  E101_STATE=/path/to/s.json E101_CARD=/path/to/card E101_RTC=2026-11-20T12:00:00 SHOTS=/path/to/shots \
    PLAIN=99400000,99500000,9a000000 emulator/emu-run stock experiments/2026-11-20-raw-edit-art-bkt/scripts/rawedit.mjs \
    w:500 key:PLAY w:1500 key:OK w:800 key:OK w:1500 key:OK w:8000
  ```

  The card holds `DCIM/100OLYMP/PB130001.ORF`. [Current] runs to the RAW load (25,516 card blocks read), then waits
  in play_cic_decode_raw 0x7E93D10F for the CIC interrupt (IRQ 100, ISR 0x7E8F590F), which the emulator never sends
  (V). Development, encode, file write and the return to playback did not run.
- Checkable before a flash: the row, the dispatch up to the RAW load, the composer's list in the function harness, the
  hook checks. Not checkable: the pictures, the per-frame Picture Mode, EXIF, time, card writes.

## 6. Risks

| Risk | Finding | Label |
|---|---|---|
| Freeze at save | One cause found 2026-11-12: code 167 read a stale raw-plane pointer at P+16 after a Grainy Film development (history-dependent); fixed in `seven-fixes-1` and stress-tested. A second restart (another entry, `seven-films-2`) is unexplained and not seen since | V / U |
| Back-to-back entries | A capture ART bracket ran 13 developments in a row with all 12 films without a fault (2026-11-18) | V camera |
| Time | One full development per frame plus a preview | U (P1: file times, Debug Log) |
| Card full | play_save_raw returns 0x3902; the loop must stop and restore the Picture Mode | V code |
| Cancel | No stock cancel during a save; the loop runs to the end | I |
| Memory | No new image buffers; 1.3 KB scratch | I |

## 7. Unknowns and probes

| U | Probe |
|---|---|
| Does a save take the Picture Mode at save time (prm 0x9481) or from the preview step? | P1, camera: in the candidate, log take+16479 and prm 0x9481 at each save (Debug Log); develop PB130001 with 3 entries On; compare pictures and EXIF |
| Command/status values of preview done and save done in 0x7EDF7F60 | Desk, first step of the build |
| previewCurrent accepted after a save | P1 |
| Box with 5 rows | Emulator screenshot of the candidate |
| Time per frame | P1 file times |

Effort: one session (decode 0x7EDF7F60, spec, row, harness check of the composer list, emulator screens and hook
checks), then one camera flash for P1 and the 12-film run; a second flash only if P1 shows the save-only path or a
fault.

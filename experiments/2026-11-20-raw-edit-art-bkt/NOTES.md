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

## 8. Candidate films-look-exif-artbkt (2026-11-20)

Build `data/builds/films-look-exif-artbkt.json`: the pinned `films-look-exif` and `data/specs/raw-edit-art-bkt.json`
(written by `scripts/mkspec_artbkt.py`, assembler source inside). sha256
`09a17d04cb4e26843ac243e35f49d8a95ba54de939d77694263d4e542f012af4`. Not flashed. The build is `first_code`: no
camera-tested code runs yet in its area 0x7EBB2AC4 (reclaim-space row 2, segment 2; all static checks pass).

### 8.1 Decoded (section 7's desk unknowns)

| Item | Finding | Label |
|---|---|---|
| Callback 0x7EDF7F60 | d0 = command, 47 for a RAW edit job. d1 = status: 3 = progress (a1 = percent: 0, 60, 80, 100), 164 = job done (a1 = result: 0, or 0xF0000001 / 0xF000004F, which the stock shows as dialogs 11 / 7). Called from the GUI task's callback queue (0x7E972C6D, from 0x7E96CBD6), not from inside the component | V emulator |
| Stock [Current] | List 320 OK row 0: startCurrent(0, callback) (vt+32), and the page leaves with key 0 to page 611 (0x7EDFA754), which calls previewCurrent(d0 = (0x602BA97C), a1 = (0x602BA978)) (vt+16). startCurrent alone starts no preview | V emulator |
| Then | cb(47, 164, 0) on page 611 → page 616 "Yes / No" with the preview. Yes → page 618 "Busy" (0x7EDFA9C1) → saveCurrent (vt+24) → cb(47, 164, 0) → page 620 "Reset / No". Reset → endCurrent(1) (vt+8), back to the list; No → endCurrent(0), back to playback | V emulator, stock image |
| The page's key | The OK handler's record at (12,sp) (read by 0x7EDCDAAB), byte +5 = the row at the time of the OK; Custom1 / Custom2 set 4 and store it with 0x7EDCDABF. A fifth row must set its own key: without it, ART BKT started the job and stayed on the list (first build of this session) | V emulator |
| Picture Mode | The preview reads prm 0x9481 (twice, from 0x7E941C60); at the preview's rec_art_set_exif_data the take's mode byte (+16479) is the frame's value. The save reads no prm 0x9481. So each frame needs its own preview | V emulator |
| Text | The ART BKT screen's title is id 1699 (re-pointing 1699 in RAM changed it; 710 did not show there) | V emulator |
| ImageDescription | A RAW Data Edit JPEG carries the source RAW's ImageDescription, not the template that FILMNAME writes: the emulator's Velvia frame was saved while the template read "Velvia 50" and its JPEG has "OLYMPUS DIGITAL CAMERA"; the camera log of films-look-exif says the same | V emulator, V camera |

### 8.2 The code (552 B with data, 0x7EBB2AC4-0x7EBB2CEC)

| Part | What it does |
|---|---|
| List 320 | Count 5, items in ITEMS: Current 1760, Custom1 1761, Custom2 1762, ART BKT 1699, No 496 |
| H1 0x7EDF7DF3 → ROWS | Every OK on the list clears the run. Row 3 (ART BKT): SETUP, key 0, then the stock [Current] path (0x7EDF7E14). Row 4 (No): key 3 and the stock No path. Rows 0-2: stock |
| SETUP | Saves prm 0x9481 (PM0). Takes a 16 KB block (0x7E507325), calls the ART bracket composer after its On/Off gate (0x7E5A75AE) with take = block − 16446, copies byte 0 of each 18-byte frame (at most 31) to LIST, frees the block. No block: LIST = the current Picture Mode only |
| H2 0x7EDF812C → CBDONE | A done job (status 164): the displaced call 0x7EDC712F, then STEP if a run is on |
| STEP | Result ≠ 0: STOP (the stock then shows its error). Frame 0's preview: phase 2, the stock asks Yes / No once. Our preview done: saveCurrent, no Yes / No. A save done: next value from LIST; none: STOP (the stock shows Reset / No); else PMSET, endCurrent(1), startCurrent(0, callback), previewCurrent as page 611 calls it; a non-zero return: STOP |
| PMSET / STOP | prm_set(0x9481, value) in play_edit_raw_main's form, then FILMNAME. STOP: PMSET(PM0), the run ends |

Hooks: two, both in segment 3, jumping to segment 2 (`emulator/hookcheck.py`: 15 transfers, 0 FAIL, no allow entry).

### 8.3 Emulator runs (`scripts/artbkt.mjs`, logs and pictures in `results/artbkt-*`)

Stand-ins (STANDIN=1, not hardware models): play_cic_decode_raw is skipped (the CIC interrupt never comes), the
histogram statistics 0x7E575651 return at once (a division by zero on the engine's zero output), and the image-engine
blocks 0x99000000-0x9AF00000 are plain storage. The pictures are empty; the control flow, the EXIF block and the card
writes are the firmware's. Card: `PB130001.ORF`, and `EPM2LOOK.BIN` (ART1 Portra 400, ART2 Velvia 50, ART5 Superia
400, ART11 Gold 200) where a run loads films (Custom Menu J → Load Looks → Load).

| Run | Set-up | Result | Label |
|---|---|---|---|
| List | pinned vs candidate, PLAY, OK, OK, DOWN × 5, MENU | The RAW menu and playback screens equal; the list differs only by the ART BKT row; the box grows to 5 rows (`results/artbkt-list-stock-vs-new.png`, `artbkt-list5.png`) | V |
| flags3 | no films; ART BKT: Soft Focus, Diorama, Watercolor On; mode ART (Picture Mode 100) | LIST [100, 101, 106, 120, 2]: the current value, then the On entries in menu order, then Natural (On in this state). Mode byte per preview 100, 101, 106 | V |
| A | films loaded; all 12 On; P, Natural | LIST [2, 100, 101, 102, 103, 111, 105, 106, 107, 108, 109, 115, 120]: entries 5 and 11 give their hidden values (stock-films hooks). Template at each save: OLYMPUS DIGITAL CAMERA, Portra 400, Velvia 50 | V |
| B | films; only ART 2 (Velvia 50) On; P, Natural | LIST [2, 101]. One Yes / No, "Busy" for both frames, 2 JPEGs, Picture Mode back to 2, the stock "Reset / No"; Reset → the 5-row list. Firmware errors: only the stock pair at 40 ms (`artbkt-yesno.png`, `artbkt-busy.png`, `artbkt-reset-no.png`, `artbkt-after-reset.png`) | V |
| C | films; only ART 3 (no film) On; P | 2 JPEGs. EXIF: frame 0 ArtFilter Off, frame 1 ArtFilter Pale & Light Color; both PictureMode Natural and ImageDescription OLYMPUS DIGITAL CAMERA | V |
| Error stop | A, flags3 | The emulator fails every third RAW save of a playback session with "REC MEDIA abort" (0x1E001002) and result 0xF0000001, also on the stock image (three [Current] edits by hand) and with 20 MB less free space at the same point (Reserve_Media returns 0 each time): an emulator limit, not a full card. The run stops there: STOP, Picture Mode back, the stock error handling | V (stop path); I (cause) |

A run of all 13 frames cannot be shown in the emulator (the third-save limit).

### 8.4 Checks

| Check | Result |
|---|---|
| `uv run epm2mod make films-look-exif-artbkt` (free-space check included) | PASS, FIRST CODE noted; sha256 above |
| `emulator/hookcheck.py data/specs/raw-edit-art-bkt.json` | 15 transfers, 0 FAIL |
| `emulator/boot-test`, `emulator/update-path-test` (in make) | PASS, PASS |
| `gen/run.sh --check` | every generated spec as committed |
| `uv run python -m unittest discover -s cli/tests`, `uv run epm2mod generate --check` | 307 OK; up to date |

### 8.5 Open (U) and what settles it

| U | Probe |
|---|---|
| Each JPEG has its frame's look | Camera run below: compare the pictures |
| The film name in a RAW Data Edit JPEG | Not given by this build (8.1). Needs a change of the RAW edit's EXIF source: owner's decision |
| Full card: what the stock reports, and whether the run stops | Camera run below, part 3 |
| Time per frame | File times and the Debug Log record times |
| Keys during "Busy"; power-off in a run (the camera keeps the frame's Picture Mode, I) | Not tested |
| A 13-frame run | Camera run below, part 1 |
| Code in 0x7EBB2AC4 runs (first code) | Any part of the camera run |

### 8.6 Camera test (one flash)

On this host, before the card trip: nothing to build. On the Mac, card in, mounted at `/Volumes/Untitled`:

1. Delete the photos in `/Volumes/Untitled/DCIM/100OLYMP/`, then copy the test RAW:
   `mkdir -p /Volumes/Untitled/DCIM/100OLYMP && scp USER@HOST:/path/to/epm2-tools/experiments/2026-11-09-film-portra/testraw/PB130001.ORF /Volumes/Untitled/DCIM/100OLYMP/PB130001.ORF`
2. Flash: `epm2flash films-look-exif-artbkt 09a17d04cb4e26843ac243e35f49d8a95ba54de939d77694263d4e542f012af4`
   Go back: `epm2flash films-look-exif af4bcb38df908c3d29b3ef028059a3142cbecc4b66737f7bb2cc2848d6a4bcf4`
3. Card in the camera, camera off. Hold **OK** and **ON/OFF** together; let go when the orange lamp lights. Wait for
   it to blink, then switch off and on.

On the camera:

4. MENU → SETUP → Custom Menu → J → **Debug Log** → **On** → OK.
5. Shooting mode P, Picture Mode Natural: press OK; in the strip, Picture Mode → **Natural** → OK.
6. ART BKT selection, all 12 On: MENU → the mode screen; LEFT × 4 to **ART** → OK; DOWN to **13 ART BKT**; RIGHT →
   screen **ART BKT**. Each of the 12 entries must read On (on an Off entry: RIGHT, DOWN to **On**, OK). The rows
   below Watercolor (i-Enhance, Vivid, ...) must read Off. MENU, MENU.
7. Back to P: MENU → the mode screen; RIGHT × 4 to **P** (the text reads "Sets the Aperture and Shutter Speed
   Automatically") → OK.

Part 1, all 12 entries:

8. Press ▶. Show PB130001 (the RAW). OK → menu **RAW** → **RAW Data Edit** → OK.
9. The list reads Current, Custom1, Custom2, **ART BKT**, No. DOWN × 3 to **ART BKT** → OK.
10. The preview with **Yes / No** → **Yes** → OK. **Busy** shows while each frame is made. At the end **Reset / No**
    → **No** → OK. Note the time from Yes to Reset / No.
11. Press the shutter halfway; press OK: the strip must read Picture Mode **Natural**.

Part 2, three entries: repeat 6 with only **ART 1**, **ART 5** and **ART 12** On (on each other entry: RIGHT, UP to
**Off**, OK), then 7 to 11.

12. Shoot one JPEG in P (the Picture Mode check of the EXIF).

Part 3, full card (on the Mac, card mounted): `df -m /Volumes/Untitled` gives Available in MB; then
`dd if=/dev/zero of=/Volumes/Untitled/FILLER.BIN bs=1048576 count=N` with N = Available − 20. Camera: steps 8 to 11
(three entries still On). Then delete `/Volumes/Untitled/FILLER.BIN`.

13. MENU, then switch off (the log is written). Copy back:
    `mkdir -p /path/to/epm2-tools/build/fw-test/artbkt && scp -r /Volumes/Untitled/DCIM/100OLYMP /Volumes/Untitled/EPM2LOG.BIN USER@HOST:/path/to/epm2-tools/build/fw-test/artbkt/`
14. On this host:
    `exiftool -FileName -DateTimeOriginal -ModifyDate -ArtFilter -PictureMode -ImageDescription build/fw-test/artbkt/100OLYMP/*.JPG`
    and `uv run epm2mod log build/fw-test/artbkt/EPM2LOG.BIN --json > build/fw-test/artbkt/log.json`.

Expected:

| Part | Files | Per file |
|---|---|---|
| 1 | 13 JPEGs, numbered in this order: Natural, then ART 1 to ART 12 in menu order | Natural: ArtFilter Off. An entry with a loaded film: ArtFilter Off and that film's look. An Olympus entry: ArtFilter = its name and its effect. ImageDescription OLYMPUS DIGITAL CAMERA on all (the RAW's) |
| 2 | 4 JPEGs: Natural, ART 1, ART 5, ART 12 | as part 1 |
| 3 | fewer than 4; the camera's card-full message | the written files complete; Picture Mode Natural afterwards |
| 12 | 1 JPEG | PictureMode Natural, ArtFilter Off |
| Log | `film_stage` records: one new art code per ART frame, in the file order | the record times give the time per frame |

Other results: the list has 4 rows or no ART BKT = the old firmware is on the camera; one JPEG only = the run did not
go on after the first save (the callback path); the same look in every file = the Picture Mode does not reach the
development (8.1); Picture Mode other than Natural after the run = the restore failed; a freeze or restart = note the
part and frame, then the Debug Log tells the last event; a list with a frame missing or extra = the composer's list
differs from the ART BKT screen.

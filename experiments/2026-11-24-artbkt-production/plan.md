# RAW Data Edit → ART BKT as a production feature: state, gaps, plan (2026-11-24)

Question (owner): can RAW Data Edit → ART BKT, until now a developer tool in test builds only, become a feature of
the release? This note says what production needs. No build was made and nothing was flashed.

Labels: V = verified (camera, firmware bytes, emulator run or manual, as named), I = inferred, U = unknown (with the
probe that settles it). History and design: `../2026-11-20-raw-edit-art-bkt/NOTES.md` (cited as "NOTES §n").
Emulator screenshots of this note: `shots/` (pinned build peaking-mf, P mode, English, made with
`emulator/mkstate build/peaking-mf.BIN STATE p` and `emulator/emu-run build/peaking-mf.BIN play.mjs`).

## 1. Current state

### 1.1 Builds

| Build | Spec | Camera | Label |
|---|---|---|---|
| films-look-exif-artbkt (`09a17d04…`) | raw-edit-art-bkt (FILMNAME at 0x7EE53BFE, card-looks-6) | Not flashed itself; the base of twelve-region-probe and calib-probe | V camera log |
| twelve-region-probe (`d492e3c8…`) | raw-edit-art-bkt | 2 RAWs × 13 JPEGs, no freeze | V camera log 2026-11-20 |
| calib-probe (`5a575639…`) | raw-edit-art-bkt | 4 look packs × 2 RAWs: 104 JPEGs, frame order as designed, no freeze | V camera log 2026-11-20 |
| films-twelve-off-artbkt (`07217bd9…`) | raw-edit-art-bkt (card-looks-7 has FILMNAME at the same address) | 3 look packs on PB130001: 39 JPEGs, no freeze | V camera log 2026-11-20 |
| films-start-texts-artbkt (`2118fc0a…`) | raw-edit-art-bkt | **Crash** at the step to frame 1 (one JPEG written). card-looks-8 had moved FILMNAME to 0x7EE53C11; the old address is inside other code | V camera log 2026-11-21, V spec bytes (NOTES §9) |
| films-start-texts-artbkt (`71b62c8f…`) | **raw-edit-art-bkt-2** (FILMNAME found by its first bytes: 0x7EE53C11) | **The fix, camera-tested:** 10 site RAWs × 3 look packs and the Tri-X pack, 13 JPEGs per RAW, each in its frame's film simulation in menu order, no crash in 40 runs | V camera log 2026-11-21 |

No build with ART BKT was ever pinned or released (V: `data/pinned-build.json` = peaking-mf, which has no ART BKT
spec). The newest test build (`71b62c8f…`) is the pinned films-start-texts + raw-edit-art-bkt-2. It lacks
peaking-mf (the pinned build) and the spot-af candidate.

### 1.2 What the camera has shown

| Behaviour | Result | Label |
|---|---|---|
| The list RAW Data Edit reads Current, Custom1, Custom2, ART BKT, No | Used in every run above | V camera |
| One Yes / No (with the preview of frame 0), then Busy, then Reset / No | The owner's procedure "ART BKT → Yes → OK; at the end Reset / No → No → OK" (`../2026-11-20-model-calibration/NOTES.md` §2), run more than 50 times | V camera |
| Frames: the current Picture Mode first, then each ART entry that is On, in the order of the ART BKT screen; each JPEG has its entry's film simulation | 13 JPEGs per RAW with all 12 entries On | V camera |
| Loaded film simulations, hidden values (ART 5 and 11) | Each frame its film | V camera |
| Time per frame | About 2.7 s (one work-buffer switch per frame in the Debug Log of earlier runs, NOTES §9): about 35 s for 13 JPEGs | V camera (log) |
| Debug Log On during runs | Works; it recorded the crash | V camera |
| Olympus filters ART 10–12 (Dramatic Tone, Key Line, Watercolor) | "Natural's mean brightness and colour in every scene" (camera log 2026-11-21). Not known if the filter acted | **U** (camera part 5) |
| The source RAW's ImageDescription is copied into every JPEG | A RAW Data Edit JPEG keeps the RAW's text, not the frame's film name (TODO, NOTES §8.1) | V emulator, V camera (films-look-exif log) |

### 1.3 Shown only in the emulator, or not at all

| Behaviour | Label |
|---|---|
| Fewer than 12 entries On (1 entry: 2 JPEGs; 3 entries: 4 JPEGs) | V emulator (NOTES §8.3 runs B, flags3); U camera |
| Picture Mode rows (i-Enhance … Custom) On give frames | V emulator (flags3: Natural); U camera |
| The current Picture Mode is an entry that is also On: it is made once, as frame 0 | V emulator (flags3); U camera |
| No entry On: one JPEG, as Current | I (the composer lists frame 0 only); U |
| The Picture Mode is back after the run | V emulator (normal end and error end); U camera |
| A save error (card full) stops the run and restores the Picture Mode | V emulator for the stop path (the emulator's own save error); U camera for a full card |
| ArtFilter tag per JPEG: an Olympus filter frame records its filter | V emulator (run C) |
| ArtFilter tag of a film frame (Off, as a capture?) | U (emulator, check E3 below) |
| PictureMode tag: Natural on both frames of run C | V emulator; meaning I |
| Power-off or battery out during Busy | U. The run sets the stored Picture Mode per frame; a run cut off leaves it on that frame's entry (I) |
| Keys during Busy; a cancel | U; no stock cancel during a save (I) |
| RAW+JPEG source; an ORF shot in ART mode or with a film | U camera |
| Colour space AdobeRGB: frame 0 gets the `_` file prefix, ART frames sRGB (manual p. 66: ART locks sRGB) | I; U camera |
| The row in other menu languages: stock text 1699, the ART BKT screen's title | I (stock text in every language table); emulator check E5 |

## 2. Production gaps

### 2.1 Reliability

| Item | State | Gap | Blocking? |
|---|---|---|---|
| The FILMNAME crash class | Fixed in raw-edit-art-bkt-2. The fix finds FILMNAME by its first bytes. hookcheck does not catch a call into the middle of a routine; only the loop run in the emulator does | The generator is research code in `experiments/`; the loop run is not in `tools/checks.py` | Yes: a shipped spec needs a generator in `gen/` and the loop run in the checks (NOTES §9 asks for it) |
| Card full | Stop path V emulator | Camera: what the user sees, partial files complete, Picture Mode back | Yes (camera test) |
| Power-off or flat battery during Busy | U | The Picture Mode may stay on the last frame's entry (I). If so: restore it at start (segment 3 constructor entry, as card-looks does) | Yes (camera test; a fix only if it fails) |
| n = 0, 1, 3, 12, and Picture Mode rows | 12 V camera; others V emulator | Camera | Yes (camera test) |
| RAW+JPEG, ORF from ART mode or with a film | U | Camera | Yes (camera test) |
| Olympus filters ART 10–12 | U (see 1.2) | Camera: compare with a capture of the same filter | Yes: a frame without its filter is a wrong picture |
| Keys during Busy | U | Camera: note what each key does | No, if nothing breaks: document |

### 2.2 What the user sees

| Item | State |
|---|---|
| Progress | One Busy screen with a bar for the whole run (V emulator `../2026-11-20-raw-edit-art-bkt/results/artbkt-busy.png`). It does not show which frame is made (V emulator). Acceptable: the stock Busy screen. |
| Duration | About 2.7 s per JPEG (V camera log): 13 JPEGs about 35 s, 20 JPEGs (all 19 rows On) about 55 s (I) |
| File names | The next free numbers, in frame order (V camera: PB220250 … in menu order). The name does not say the entry |
| Exif film name | **Wrong today:** every JPEG carries the source RAW's ImageDescription ("OLYMPUS DIGITAL CAMERA", or the film the RAW was shot with). A RAW shot in Portra 400 gives 13 JPEGs that all say Portra 400. ArtFilter of a film frame: U |
| Settings used | The camera's current settings (white balance, aspect, sharpness …), as RAW Data Edit → Current (manual p. 65, V) |

The film-name gap is the one gap that needs new code. Options: (a) fix the RAW edit's EXIF source so that each JPEG
gets the template FILMNAME writes (also closes the TODO item for a plain Current edit; size U, about 40 B I; checkable
in the emulator with `HEADS=` and exiftool, NOTES §8.3); (b) ship with the limit in the guide. Decision D2.

### 2.3 Interaction with the pinned build

| Feature | Evidence | Label |
|---|---|---|
| Film simulations from the card (card-looks-8) | Every camera run since 2026-11-21 used loaded films; FILMNAME at 0x7EE53C11 in card-looks-8 and in spot-af's card-looks-9 (found by byte search today) | V camera; V bytes |
| Focus peaking | RAW edit goes through the image-work heap setter that the peaking code wraps (pk_heap_mode per frame in the log). The ART BKT test builds had all peaking specs except peaking-mf; peaking-mf adds only live-view code | V camera without peaking-mf; I with it |
| Interval shooting, level gauge, Lowest S/S, spot metering | Shooting-side code; RAW edit is playback | I (no shared code) |
| Debug Log | Records during runs | V camera |
| Byte overlap | raw-edit-art-bkt-2 changes no byte that peaking-mf or spot-af changes (checked today over all their specs' ops) | V |

### 2.4 Code space on top of the pinned build

| Part | Size | Place | Label |
|---|---|---|---|
| Code and data | 552 B | 0x7EBB2AC4–0x7EBB2CEC, segment 2 (reclaim-space row 2, run of 1320 B; 768 B stay free). Code has run there on the camera | V |
| List 320 descriptor | 8 B | 0x7F00D564 | V |
| Hooks H1, H2 | 5 B + 9 B | segment 3 (0x7EDF7DF3, 0x7EDF812C), to segment 2: hookcheck 15 transfers 0 FAIL, no allow entry | V |
| EXIF fix (if D2 = a) | about 40 B | segment 2 or 3 | I |

## 3. The user path, and where each name comes from

**Choose the entries** (manual p. 61–63 "Bracketing" and "ART BKT"; screens and keys from the emulator):

MENU → **SETUP** → OK → **Shooting Menu 2** → **Bracketing** → RIGHT → **ART BKT** → RIGHT → highlight **On**
(do not press OK) → RIGHT → screen **ART BKT**.

| Point | Finding | Source |
|---|---|---|
| Rows | 19 rows: the 12 ART entries (Pop Art … Watercolor, or the loaded film names), then i-Enhance, Vivid, Natural, Muted, Portrait, Monotone, Custom (`shots/art-bkt-list.png`, `shots/art-bkt-list-end.png`) | V emulator; manual p. 63 shows the first rows |
| Marks | No check marks: each row reads **On** or **Off** | V emulator, manual p. 63 |
| Change a row | RIGHT → a panel Off / On → UP or DOWN → OK (`shots/art-bkt-entry.png`, `shots/art-bkt-entry-off.png`) | V emulator |
| Defaults (empty settings store) | The 12 ART entries On, the 7 Picture Mode rows Off | V emulator |
| Capture bracketing stays off | Leaving with MENU without OK on On: Bracketing → ART BKT still reads `--` (`shots/bracketing-after.png`); the row values are kept (`shots/art-bkt-kept.png`) | V emulator; U camera (one glance in the test) |
| Loaded film names on this screen | Shown (`../2026-11-20-raw-edit-art-bkt/results/artbkt-flags-one-on.png`: Gold 200) | V emulator |
| Other way in | ART mode, entry 13 ART BKT, RIGHT (manual p. 28; NOTES §5). It changes the shooting mode: not for the guide | V emulator |
| Tab and screen names | "Shooting Menu 2", "Bracketing", "ART BKT", "AE BKT … HDR BKT" | V emulator screen text, manual p. 61 |

**Start it** (manual p. 39 "Using playback options" and p. 65 "Editing still images"):

▶ → show the RAW → OK → menu **RAW** → **RAW Data Edit** → OK → **ART BKT** → OK → **Yes** → OK → Busy → **Reset / No**.

| Point | Finding | Source |
|---|---|---|
| OK in playback opens a menu with RAW Data Edit | Manual p. 39; the emulator menu is titled **RAW** (`../2026-11-20-raw-edit-art-bkt/results/raw-ok-menu.png`) | V manual, V emulator |
| Other way in | MENU → Playback Menu → Edit → Sel. Image → OK → RAW Data Edit (manual p. 65) | V manual |
| RAW+JPEG: both RAW Data Edit and JPEG Edit are offered | Manual p. 65 | V manual; U with ART BKT |
| The list Current, Custom1, Custom2, ART BKT, No | `../2026-11-20-raw-edit-art-bkt/results/artbkt-list5.png` | V emulator, V camera |
| End: Reset → the list again; No → playback | NOTES §8.1 | V emulator; No V camera |

## 4. Acceptance criteria

User story: "I shot a RAW. In playback I make one JPEG per film simulation I chose, to compare them, without a computer."

| # | Criterion | Check |
|---|---|---|
| A1 | The ART BKT screen is reached from Shooting Menu 2 → Bracketing without turning on capture bracketing; the rows keep their values | Emulator (done, `shots/`); camera glance |
| A2 | RAW Data Edit lists ART BKT; one Yes / No; Busy; Reset / No; No returns to playback | Emulator (screenshot comparison with the pinned build); camera |
| A3 | Frame 0 is the current Picture Mode; then one JPEG per row that is On, in screen order, none twice; n = 0, 1, 3, 12 and a Picture Mode row | Emulator (list); camera (pictures) |
| A4 | Each JPEG has its entry's look: a film simulation, or the Olympus filter as a capture of that filter makes it | Camera |
| A5 | Each JPEG's metadata names its entry: ArtFilter (filter name, or Off for a film) and, if D2 = a, ImageDescription = the film name | Emulator (`HEADS=` + exiftool); camera |
| A6 | The RAW and existing files are unchanged; new files take the next numbers | Camera |
| A7 | After any end (normal, card full, power-off) the Picture Mode is the one set before | Emulator (normal, error); camera (all three) |
| A8 | Card full: the run stops, a message shows, the written JPEGs open, the camera works on | Camera |
| A9 | No crash or freeze across the sheet's runs, with Debug Log On and Off | Camera |
| A10 | Every other feature of the base build is unchanged: start, update path, menus, films, peaking after a run | Emulator (boot-test, update-path-test, crawl); camera (peaking glance) |
| A11 | The row reads ART BKT in other languages | Emulator (`lang-all.sh` or one language by hand) |
| A12 | Time per JPEG about 3 s, as the guide states | Camera (Debug Log, file times) |

## 5. Build steps (after D1)

1. Generator: `gen/raw-edit-art-bkt/` from `../2026-11-20-raw-edit-art-bkt/scripts/mkspec_artbkt.py` (the other
   session's current version), with FILMNAME taken from card-looks's `_symbols` where it has one, else the byte
   search, and an assert that the call target starts with FILMNAME_HEAD. Add it to `gen/run.sh` (shared file; the other
   session has edits in it now: coordinate). The spec for the pinned base is byte-for-byte raw-edit-art-bkt-2 unless
   D2 = a.
2. If D2 = a: desk study of where play_edit_raw_set_exif_default (0x7E94113F) fills ImageDescription; one hook that
   writes FILMNAME's template there; emulator run with `HEADS=` and exiftool on 3 frames.
3. Add the ART BKT loop run (`artbkt.mjs` to frame 2 with `STANDIN=1`, film look pack on the card) to the full tier of
   `tools/checks.py` for every build with this spec. This is the check that would have caught the 2026-11-21 crash.
4. Build `data/builds/<pinned>-artbkt.json` = the build pinned at that time (peaking-mf today; spot-af if the owner pins
   it first) + the spec. `uv run epm2mod make NAME`.
5. Checks, each exit status 0: `uv run python emulator/hookcheck.py data/specs/<spec>.json`,
   `emulator/boot-test data/builds/NAME.json`, `emulator/update-path-test data/builds/NAME.json`,
   `uv run python tools/checks.py data/builds/NAME.json --tier full`.
6. Emulator, by hand: `emulator/boot/shotdiff.sh build/<pinned>.BIN build/NAME.BIN OUT w:500 key:PLAY w:1500 key:OK w:800 key:OK w:800`
   with PB130001.ORF on the card (only the list differs); the loop run of step 3 with 3 entries and with all 12; the
   EXIF of the saved frames (E3: ArtFilter of a film frame); A11 in one other language (E5).
7. Camera log entry before the flash; the sheet of section 6.
8. After a pass (AGENTS.md rule 15): pin the build, `uv run epm2mod generate`, the guide `docs/guide/` from
   `guide-draft.md` with the markers removed and the screenshots in `docs/images/ui/`, one line in the README feature
   table, the camera log, `docs/dev/feasibility.md`, and TODO: delete the "developer tool" item (and the RAW Data Edit
   ImageDescription item if D2 = a). The "dev only" rule in the owner's memory changes with D1.

## 6. Camera test sheet (one flash)

Covers every U above. Fill NAME and SHA from step 4. Debug Log On for the whole test.

On the Mac, card in, mounted at `/Volumes/Untitled`:

1. Delete the photos in `/Volumes/Untitled/DCIM/100OLYMP/`, then copy the test RAW:
   `mkdir -p /Volumes/Untitled/DCIM/100OLYMP && scp USER@HOST:/path/to/epm2-tools/experiments/2026-11-09-film-portra/testraw/PB130001.ORF /Volumes/Untitled/DCIM/100OLYMP/PB130001.ORF`
2. Look pack with films in ART 1, 2, 5 and Olympus's filters elsewhere:
   `cd /path/to/epm2-tools && uv run epm2mod films set --card /Volumes/Untitled --film ART1=portra-400 --film ART2=velvia --film ART5=double-x`
3. Flash: `epm2flash NAME SHA`. Go back: `epm2flash peaking-mf 6a47806dfafce15d281358eae2beffe397132e5999c50b28c69b2a2467efcf39`
4. Card in the camera, camera off. Hold **OK** and **ON/OFF** together; let go when the orange lamp lights. Wait for
   it to blink, then switch off and on.

Set-up on the camera:

5. MENU → SETUP → OK → Custom Menu → J → **Debug Log** → **On** → OK.
6. MENU → SETUP → OK → Custom Menu → J → **Load Looks** → **Load** → OK. The row reads **Loaded**.
7. P mode: MENU, LEFT or RIGHT to **P** (the text reads "Sets the Aperture and Shutter Speed Automatically"), OK.
   Press OK; UP or DOWN to the Picture Mode item; LEFT or RIGHT to **Natural** (the text reads Natural); OK.

Part 1, A1 and 12 entries:

8. MENU → RIGHT to **SETUP** → OK. In the tab column (left), UP or DOWN to the tab whose title reads **Shooting Menu
   2** → RIGHT → DOWN × 2 to **Bracketing** → RIGHT → DOWN × 4 to **ART BKT** → RIGHT → DOWN to **On** (no OK) →
   RIGHT. Screen **ART BKT**: rows 1–12 **On** (an Off row: RIGHT, DOWN to On, OK); rows 13–19 (i-Enhance to Custom)
   **Off**. Rows 1, 2, 5 read Portra 400, Velvia, Double-X. MENU. The Bracketing screen: ART BKT reads `--`. MENU,
   MENU.
9. ▶, show PB130001, OK → **RAW Data Edit** → OK → **ART BKT** → OK → **Yes** → OK. Note the time from Yes to
   **Reset / No**. During Busy press nothing. **No** → OK.
10. Press the shutter halfway, then OK; UP or DOWN to the Picture Mode item: the text reads **Natural**. Press the
    shutter halfway to leave.

Part 2, n = 3 with a Picture Mode row, and keys during Busy:

11. Step 8 with only **Velvia** (row 2), **Pin Hole** (row 6) and **Monotone** (row 18) On.
12. Step 9; during Busy press MENU once, then ▶ once. Note what each did. Then step 10.

Part 3, n = 1 and n = 0:

13. Step 8 with only **Watercolor** On; step 9 and 10.
14. Step 8 with every row Off; step 9 and 10. Note whether a JPEG is made or the list stays.

Part 4, an ORF shot in ART mode as RAW+JPEG (A4 for Olympus filters, RAW+JPEG source):

15. MENU, LEFT to **ART**, OK; in the list choose **12 Watercolor**, OK. Press OK; UP or DOWN to the image quality
    item (it reads LN); LEFT or RIGHT to **LF+RAW** (`shots/quality-lf-raw.png`); OK. Shoot a coloured scene (shot W).
16. MENU, RIGHT to **P**, OK. Picture Mode **Natural** (step 7). Image quality back to **LN**.
17. Step 8 with **Dramatic Tone**, **Key Line**, **Watercolor** On, the rest Off. ▶, shot W's RAW, OK: note the
    menu's rows (RAW Data Edit and JPEG Edit?). RAW Data Edit → ART BKT → Yes → OK → No.
18. Step 10.

Part 5, power-off during Busy (A7):

19. Step 8 with rows 1–12 On. Step 9, and at the 3rd frame (about 8 s after Yes) switch the camera off.
20. Switch on. Press OK: note the Picture Mode. ▶: note the last JPEG; it must open.

Part 6, card full (A8):

21. MENU, then switch off. On the Mac: `df -m /Volumes/Untitled` gives Available in MB; then
    `dd if=/dev/zero of=/Volumes/Untitled/FILLER.BIN bs=1048576 count=N` with N = Available − 20.
22. Camera: step 8 with rows 1–12 On; step 9 on PB130001; note the message and the number of new files; step 10.
23. Peaking glance (A10): MF, turn the focus ring; the lines show; shoot one JPEG.
24. MENU, switch off. On the Mac: `rm /Volumes/Untitled/FILLER.BIN`, then
    `mkdir -p /path/to/epm2-tools/build/fw-test/artbkt-prod && scp -r /Volumes/Untitled/DCIM/100OLYMP /Volumes/Untitled/EPM2LOG.BIN USER@HOST:/path/to/epm2-tools/build/fw-test/artbkt-prod/`
25. On this host: `exiftool -FileName -DateTimeOriginal -ArtFilter -PictureMode -ImageDescription build/fw-test/artbkt-prod/100OLYMP/*.JPG`
    and `uv run epm2mod log build/fw-test/artbkt-prod/EPM2LOG.BIN --json > build/fw-test/artbkt-prod/log.json`.

Expected:

| Part | Files | Other results and what they mean |
|---|---|---|
| 1 | 13 JPEGs in screen order: Natural, Portra 400, Velvia, Pale&Light Color, Light Tone, Double-X, Pin Hole, Diorama, Cross Process, Gentle Sepia, Dramatic Tone, Key Line, Watercolor; Picture Mode Natural after | 4 rows on the list = old firmware; 1 JPEG = the loop did not go on; the same look in all = the Picture Mode does not reach the development; another Picture Mode after = restore failed |
| 2 | 4 JPEGs: Natural, Velvia, Pin Hole, Monotone | Keys: ignored is the expected case; a freeze or an early end: note it, the log has the last event |
| 3 | n = 1: 2 JPEGs (Natural, Watercolor). n = 0: 1 JPEG (Natural), or the list stays | n = 0 either way passes; the guide states what happened |
| 4 | Shot W: ORF + JPEG. 4 JPEGs from the RAW: Natural, Dramatic Tone, Key Line, Watercolor; the Watercolor frame looks like shot W's JPEG | A frame with Natural's look = the filter does not act in RAW Data Edit: blocking (A4) |
| 5 | Picture Mode Natural after the restart; the last JPEG opens | Another Picture Mode = the restore at start is needed (build step, then a second flash) |
| 6 | Fewer than 13 new files; a card-full message; Picture Mode Natural; the camera works | A freeze = blocking |
| EXIF | ArtFilter: the filter name on Olympus frames, Off on film frames. ImageDescription: the film name (D2 = a) or the RAW's (D2 = b) | |
| Log | One work-buffer switch per frame; times give the time per JPEG | |

## 7. Decisions for the owner

- **D1.** Make RAW Data Edit → ART BKT a release feature (it was "developer tool, never in releases")?
- **D2.** Film name per JPEG: (a) new code so that each JPEG records its frame's film name (it also changes a plain
  RAW Data Edit → Current: the JPEG gets the current film's name, not the RAW's), or (b) ship with the limit stated in
  the guide. Recommended: (a). Today a RAW shot in a film gives JPEGs that all name that film.

Not owner questions (the findings answer them): the build goes on top of whatever build is pinned when the work starts;
frame 0 stays (the capture ART BKT makes it too); the Busy screen stays stock.

## 8. The criteria on artbkt 2026.11.29 (2026-11-26)

Build `data/builds/artbkt.json` made again on the pinned film-tables-fix, sha256
`dc1e31898fb0bc0a75c8a54d40a3cd25aa751dc104e1eeee0752ea7ce1afddd0` (`NOTES.md` section 5). E = emulator, C = camera.
Not checked = the camera test of `test-sheet.md` settles it.

| # | E | C |
|---|---|---|
| A1 | Pass: the ART BKT screen through Bracketing without OK; the rows keep their values; MENU leaves ART BKT `--` | Not checked (step 8) |
| A2 | Pass: the RAW Data Edit screens against film-tables-fix, same keys: only the list differs (5 rows); the end screen Reset / No | Not checked (parts 1-3) |
| A3 | Pass: n = 0, 1, 3 (with a Picture Mode row), 12 (frames 0-2), Natural not twice | Not checked (parts 1-3) |
| A4 | Not shown: the emulator has no image engine | Not checked (parts 1, 4) |
| A5 | Pass: ImageDescription per frame (OLYMPUS DIGITAL CAMERA, Portra 400, Velvia); Current takes the film name, Custom1 the RAW's | Not checked (EXIF row) |
| A6 | Pass in part: new files take the next numbers; the RAW's size unchanged | Not checked |
| A7 | Pass: the Picture Mode comes back at the normal end and at the error stop | Not checked (parts 6, 7: power-off, card full) |
| A8 | Not shown: no full card in the emulator | Not checked (part 7) |
| A9 | Pass in the runs above: no fault | Not checked |
| A10 | Pass: boot-test, update-path-test, hookcheck 0 new transfers; menu crawl p-card-shallow 461 of 462 screens equal (the other is the Firmware label) | Not checked (part 7: peaking) |
| A11 | Not run again: the row's text is stock text 1699 and no film-tables-fix spec changes it (inferred from the 2026-11-24 run in four languages) | Not needed |
| A12 | Not shown | Not checked (part 1, the log) |

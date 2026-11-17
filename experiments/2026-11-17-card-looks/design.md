# Interchangeable film looks from the SD card: design (2026-11-17)

Question (owner): can the art-filter looks be made interchangeable, loaded from a file on the SD card through a menu
row, and then stay in the camera (without the card, after power-off) until another file is loaded? And what file
format is easy to copy to a card, easy for the camera to read, small, and easy for a web app to write?

Answer: yes, as far as static analysis, the emulator and two camera probes show. Each part has a known way to do it,
except one: room for about 1 KB of loader code, which the free runs do not have (section 6). Labels: V = read in the
bytes, run in the emulator or seen on the camera; I = inferred; U = unknown.

## 1. What is proven

| Fact | Evidence |
|---|---|
| Our code reads a card file in its own task at a menu change | V camera, probe 1 (NOTES.md section 3) |
| A value written into a look table in RAM changes the next photo and live view | V camera, probe 2 (NOTES.md section 5): the art matrix |
| The other look stages keep a per-job cache and do not see a write at once | V code (agent A trace, section 4) |
| The EEROM settings bank has about 53 KB at its end that no firmware code reads, and the firmware saves the whole 64 KiB itself | V code and emulator (agent B, section 3) |
| A look is a parameter set; the firmware tables are computed from it and the stock default tables | V `src/epm2mod/looks/generate.py` |

## 2. How it works

1. **Menu row "Load Looks"** (Off / Load) in Custom Menu J: a dormant MODE setting (446, tag 0xD781: no code reads
   it, V `experiments/2026-11-17-osd-info/NOTES.md` section 7) with a stock two-value picker, added the way
   `patches/peaking-menu.json` added its row (camera-tested). Its label needs one new string in the 34 language
   tables (the method of `patches/films12-names.json`).
2. **The load** runs when the GUI leaves the menu with the setting at Load: the GUI-state hook sets it back to Off,
   checks `isMediaWriting` (0x7ECD360A) = 0 and starts our task (OlyTaSt 0x7E449541): the camera-tested pattern of
   the log's flush task. The task reads `LOOKS.BIN` from the card root, checks it (section 5.4) and, if it is good,
   (a) copies it into the EEROM tail, (b) applies it to the slot tables (section 4), (c) forces the look stages to
   recompute. Nothing is written when any check fails. The file I/O stays out of the GUI task, which would block on
   FILECLBK (I).
3. **Persistence:** the copy in the EEROM tail is saved to flash by the firmware itself, at power-off, at sleep and
   in the save at every start (V code: the bank API 0x7E680272 and its callers). A power loss during a save leaves the
   older copy, which the firmware loads instead (V emulator). A battery pull between a load and the next power-off
   loses the new looks; calling 0x7E680272 from our task right after the load would close that window (U, probe P5).
4. **At every start** an apply routine copies the stored looks from the EEROM tail into the slot tables at the first
   GUI state (hook 0x7ECDF6E4 in CA_MAIN: segment 2 and the banks are loaded by then, V emulator). It needs no card
   and no file I/O. It checks the stored copy exactly as the loader checks a file. This routine is the one place
   that could stop a start, so it stays in segment 2 or 3, which the update path (OK held) never runs: a bad look
   cannot block the recovery flash (I, `docs/feasibility.md`).
5. **Back to stock looks:** load a file with no looks (count 0), or one that holds the built-in looks. A stored copy
   that fails its checks is ignored and the flashed looks stay.

## 3. Where the looks are kept: the EEROM bank tail

- Bank format (V, 0x7E456370 / 0x7E4563C9 / 0x7E4563E7): u16 id (EEROM 0x0026), u16 checksum (the 16-bit word sum of
  the whole 64 KiB is 0), u32 save counter, data from +8. Two copies in flash, written in turn (EEROM at 0x400E0000
  and 0x40100000); the newer valid one is loaded. The save (0x7E456265) compares RAM with flash over +8..size-4 and
  writes the whole bank to the other copy when they differ.
- Free: RAM 0x603F74B8-0x60404668, 53,680 B (I-strong: the used part ends at +0x2E44 by a model of the ROM default
  lists that matches three known points; no code holds an address in the tail, V). Not 0xFFF4-0xFFFF (not compared).
- The MODE bank has 4,936 B more at its end; not needed.
- Open: is the tail empty on the real camera (U, probe P4 reads it); does Reset or anything else clear it (I: Reset
  sets tags one by one; the update file does not contain the banks).

## 4. Applying a look, and the stage caches

Agent A's trace of the six-stage builder in the IMG library (V code; the effect on the camera is I unless noted):

| Stage | Table | Cached? | Takes effect |
|---|---|---|---|
| Art matrix (e) | 9 x s16 | no, every job | at once (V camera, probe 2) |
| Six-axis (d) | 2 x 6 x s16 | yes, by a key (art code, picture-mode fields, job type); codes 85, 87, 167, 168, 96, 97, 165, 166 recompute every job | after a key change |
| Saturation pair (c) | 2 x u16 | yes | after a key change |
| Chroma curves (f) | 97 B | yes | after a key change |
| Look curve (b) | 256 x u16, by pointer | yes; the pointer, not the values, is compared | U: who reads the table behind the pointer |
| Base gamma (a) | 3 records x 8 tables | rebuilt every job for the still column; the other columns cached | still: next photo (I); live view's column U |

**Forcing a refresh** (I, not tried): store 0 into the two builder words 0xA07500B4 and 0xA07500B8 (what the boot
init 0x7E560AC0 does), so that the next job of each builder clears the stage cache (0x7E56A5A9); and 0xFF into the
art-code byte of the two gamma states (0x60510CD5, 0x60511305). A few instructions after the table writes.

**Tone tables from the stock defaults:** a slot's tone table k is the look's curve read at the stock default table's
value, kept rising: `table[k] = max(table[k-1], curve[default[k]])` (`generate.py` `film_ops`, `pack_table`). The
default tables are intact in RAM at run time (V for what was checked: no spec writes them, their only references
are reads; a write through a pointer is not excluded). Because the default values rise with k, the camera can read
the curve as a stream while it fills the table: no 2 KB work buffer.

## 5. The file format

Goals: one small binary file, read by a short loop on the camera with no parser; written by a web app with a
`DataView` and a CRC-32; the same bytes stored in the EEROM tail, so the camera checks one format in one place.

### 5.1 Why binary, why parameters, why these encodings

- **Binary, fixed layout, little-endian.** A text format (JSON, CSV) would need a parser in MN103 assembly; the code
  space is the tightest resource (section 6). A browser writes a fixed layout as easily as JSON.
- **Look parameters, not firmware tables.** The tables of one slot are 1.7 KB (three tables) or 12 KB (three
  records of eight tables), and making them needs the stock default tables, which a web app must not ship (they are
  the vendor's data). The parameters are what the fits hold, and the camera computes the tables (section 4).
- **Curves as 4-bit steps.** A tone curve has 1,024 points, 10-bit values, and must rise (`pack_table`). In all 17
  colour fits every step between neighbours is 0, 1 or 2 (V, `looks/fits/*.npz`). So a curve is its first value and
  1,023 steps of 4 bits (0-15): 514 B instead of 2 KB, lossless for every fit we have, and still exact for curves
  ten times steeper. Fewer points with interpolation would cost up to 6 levels of error (V: 17 knots) and more code.
- **Integrity: CRC-32** (the zlib polynomial; Python's `zlib.crc32`, and a 10-line function in JavaScript) over
  everything after the header's CRC field, plus a magic, a version and lengths. A bad file is refused whole.

### 5.2 Layout (version 1)

All values little-endian. Offsets in bytes.

Header, 32 B:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | magic `EPLK` |
| 4 | 1 | format version, 1 |
| 5 | 1 | number of look records, 0-12 |
| 6 | 2 | record size, 1,708 for version 1 |
| 8 | 4 | file length (header + records) |
| 12 | 4 | CRC-32 of bytes 16 .. file length |
| 16 | 2 | camera model code, 0x0101 (E-PM2) |
| 18 | 2 | firmware version, 0x0160 (1.6) |
| 20 | 12 | reserved, 0 |

Look record, 1,708 B (version 1):

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | slot: the menu entry 0-11 (the order of the art-filter menu; `looks/films.json`, `looks/more-films.json`) |
| 1 | 1 | kind: 1 = colour look (the parameter set below); 2 = black and white (reserved: matrix, tone curve, grain table) |
| 2 | 2 | flags, 0 |
| 4 | 16 | name: ASCII, NUL-padded (shown by the camera only if names become possible, section 7; always kept) |
| 20 | 2 | saturation gain, u16 (`gain`) |
| 22 | 12 | six-axis saturation, 6 x s16 (`S`) |
| 34 | 12 | six-axis hue, 6 x s16 (`H`) |
| 46 | 18 | art matrix, 9 x s16, rows sum to 256 (`A`) |
| 64 | 97 | chroma curves: x[16], y[16], slope[17] for Cb, then x[16], y[16], slope[16] for Cr, u8 each (`chroma_record`) |
| 161 | 3 | reserved, 0 |
| 164 | 3 x 514 | tone curves R, G, B: u16 first value (0-1023), then 1,023 steps of 4 bits, low nibble first, last nibble 0 |
| 1706 | 2 | reserved, 0 |

Size: 32 + 12 x 1,708 = 20,528 B for all twelve looks; a file may hold fewer (one look: 1,740 B). It fits the
EEROM tail (53,680 B) with room for version 2.

### 5.3 How each side handles it

- **Tools:** the looks in `looks/` stay the source. `epm2mod looks pack` (new) writes `LOOKS.BIN` from a list like
  `looks/more-films.json`; a JSON form of one record (the fields above, curves as 1,024 numbers) is what a web app
  edits and what the tests compare. Test vectors: the twelve looks of the pinned build, and their bytes.
- **Web app:** builds the 1,024-point curves, rounds them, keeps them rising, writes the steps, fills the record
  with a `DataView`, computes the CRC-32, and offers the file for download; the user copies it to the card root.
- **Camera, loading:** read at most 20,528 B; check magic, version, record size, length, count, the CRC, then every
  record (slot 0-11 and no slot twice, kind 1, a curve that ends at 1,023 or less, matrix rows that sum to 256 +/-
  8, chroma x values rising); only then write anything.

### 5.4 Checks before anything is written (on load and at every start)

Magic, version 1, record size 1,708, length = 32 + count x 1,708 <= 20,528, CRC-32, and per record: slot < 12,
slots unique, kind 1, the decoded curve stays in 0..1,023, the matrix rows sum to 256 +/- 8, the chroma x values
rise. A file that fails is not stored; a stored copy that fails is not applied.

## 6. Code space: the open constraint

Estimated loader and apply code (I): file read and checks with a table-less CRC-32 (~250 B), curve decode and table
fill for the two slot shapes (~150 B), the small-value writes and the cache refresh (~100 B), the slot address
table (12 slots x about 40 B = ~500 B), the menu hook and the start hook (~100 B): about 1 KB. The free runs in
segment 2 are 600 B in pieces of 120 B and less (`docs/code-space-map.md`), so they do not hold it. Candidates:
the 7.2 KB 3D-engine area, whose "dead" status is static only (`experiments/2026-11-13-reclaim-space/review-3d-cluster.md`
section 6: not proven; a wrong claim breaks the GPU slideshow, not the start); the `sdk api` shell's 123 KB; or
code loaded from the card into a heap block (EP7, OM3). Each needs its own evidence before it holds this code.

## 7. Names

The menu names are UTF-16 strings in block 1 (the resource block), one per entry in each of 34 language tables, with
fixed room (`patches/films12-names.json`: 1,307 edits). Whether the camera reads them from RAM that our code could
write at run time is U. Until a probe says so, a loaded look keeps the menu name of its slot, and the file carries
its name for the future.

## 8. Probes, in order (one change per flash)

| # | Where | What it settles |
|---|---|---|
| P3 | camera | The stage cache: the card file sets Pro 400H's saturation pair to 0 (grey if it takes effect). Photo A, MENU, MENU, watch live view, photo B, switch film and back, photo C. B grey = no cache problem for stills; only C grey = cached until a key change |
| P3b | camera | Forcing: as P3 plus the refresh stores of section 4: live view and B grey at once |
| P4 | camera | The EEROM tail on the real camera: log 16 bytes and a nonzero count at the first GUI state; then store a look there at a card load, power off, take the card out, power on: the look is back before any menu |
| P5 | emulator, camera | Saving at once: call 0x7E680272 from the loader task; the flash copy changes (emulator); a battery pull after a load keeps the look (camera) |
| P6 | camera | Tone tables rebuilt from the defaults: one channel of one slot, a photo before and after |
| P7 | emulator | The menu row: setting 446 with picker 608 or 610 in Custom Menu J; hookcheck, boot-test, update-path-test |
| P8 | static, then camera | Room for 1 KB of code (section 6) |

## 9. Final plan

### 9.1 Done at the desk (2026-11-17)

- **The probe harness** `builds/debug-log-card-probe.json` (`patches/log-card-probe.json`, `mkspec_log.py
  --card-probe`; sha256 `9005cfcb70c8927348d183c14a46a95b99e1f03b597f0267a1eea3d2e01b4014`). One flash for every
  stage probe: an LKP1 card file (`scripts/mkprobe.py`; `build/card-probe/`) holds records {u32 address, u16 length,
  u16 0, bytes}, each written only inside one of the seven tables of the Pro 400H slot, and a flag that runs the
  boot's cache reset (section 4). Emulator (V): a record is written or refused as it should be; a record at code and
  one that runs 2 bytes past its table are refused; the walk stops at a count larger than the file; the refresh stores
  run without a fault. 452 B of code in five runs of segment 2. Two bugs the emulator caught and the build no longer
  has: a word table at an odd address (a fault on the camera), and a bound kept at (0,sp), which every `call`
  overwrites with its return address.
- **The persistence probe** `builds/debug-log-card-keep.json` (`patches/log-card-keep.json`, `--card-keep`; sha256
  `2771357d4f7debe57fe106209fa65cfeec6d4b8b4cec444d5a36869cb125cefa`). A LOOK file sets the Pro 400H matrix and stores
  a record LKB1 {length, 16-bit sum, the 18 bytes} at 0x603FC000 in the EEROM bank's tail, then calls the bank save
  API; at every start the record is checked and applied at the first GUI state (log-core's T_GUI). Emulator (V),
  two sessions: session 1 found the tail empty (0 nonzero words), stored the look and saved the bank (`card_keep`
  result 0); session 2, with no look file and the RAM images taken out of the state, so that only the firmware's own
  bank load from flash could bring it back, applied it before the first menu (`bank_look` applied, the table grey).
- **Saving at once** (P5, V emulator): the save API 0x7E680272 called from our task erased and rewrote the other
  EEROM copy (counter 3) with the tail's content in 4.4 ms of lab time, result 0, no error entry.
- Both builds: free-space check PASS (code only in segment 2: the segment-3 tail is for data), op check 0 FAIL,
  hookcheck only the allowed remap7b-code entry, boot-test and update-path-test PASS. The persistence probe first
  failed boot-test (time stamps 0.2-0.4 ms late: its 53 KB scan at the first GUI state); the scan moved to the first
  flush, and the start-up hook does only the 18-byte check and copy.

### 9.2 The blocker: three camera sessions on two flashes

| Step | Build, card file | What is read | Decides |
|---|---|---|---|
| 1 | harness, `sat0.bin` | photo A before any menu; MENU, MENU; live view; photo B; another film and back; photo C | is the saturation stage cached for stills (B colour, C grey) or not (B grey) |
| 2 | harness, `sat0-force.bin` | photo A; MENU, MENU; live view; photo B | does the refresh make a cached stage take a write at once, without a crash |
| 3 | harness, `toner0-force.bin` | photo A; MENU, MENU; photo B (cyan if the red table took effect) | do the tone tables take a write (the stage that matters most for a look) |
| 4 | persistence, `grey-look.bin` | MENU, MENU (the look is stored and saved); power off; take EPM2LOOK.BIN off the card; power on; photo before any menu | the tail is free on the camera (`bank_tail`), the look survives without the file (photo grey, `bank_look` applied) |

Outcomes and what follows:
- 2 and 3 work (B changes at once): the loader writes all tables and runs the refresh; no stage needs special handling.
- 1 shows the cache and 2 does not fix it: the loader cannot rely on the refresh; a load then takes effect after a
  film change, which the menu row can do itself (I), or after a restart (the apply at start runs before any job).
- 3 does not work: the tone tables are read elsewhere (U); trace the look curve's pointer reader before the loader.
- 4: `bank_tail` nonzero on the first session means the tail is in use on the camera: stop and find another place.

### 9.2.1 Results of steps 2 and 3 (camera, 2026-11-17)

- **Step 2 passed (V):** with the refresh, the saturation stage, which keeps a per-job cache (section 4), took the
  write at once: photo PB170146 exactly grey (mean colour 0.0 against 28.0 before), live view black and white (owner).
  The refresh stores caused no error. Step 1 (the same without the refresh) was not run: the loader runs the refresh
  in any case.
- **Step 3 passed for stills (V):** the red tone table 0x7F033B7C written with the refresh: PB170148 R/G/B 5/47/45
  against 51/50/46 before. Live view looked normal and greener only with the shutter half pressed: live view reads
  other tables, and at S1 its preview uses the stills tables (I). The flashed films write only the stills tables of
  this slot (`generate.py`, `Tables` slots), so live view behaves today as it did here; the loader keeps that parity.
  A live-view table for each look is a later improvement (which table live view reads for each slot: U).
- So the loader writes every table and then runs the refresh, and a load takes effect at once. Step 4 (persistence)
  is next.

### 9.2.2 Result of step 4 (camera, 2026-11-17)

**Passed (V).** The EEROM bank's unused tail was empty on this camera (0 nonzero words of 13,420). A look loaded
once from the card was stored there, saved at once by the bank save API (result 0), and applied at the first GUI
state of every later start, also with the file removed from the card: the photo before any menu was black and white
(colour spread 1.33 at equal brightness). Two starts that went straight to power-off applied it too, and no error
record appeared. Every open question of sections 1-4 is now answered on the camera, except the code space (section
6) and the names (section 7).

### 9.3 After the probes: the feature

1. **Code space** (section 6), measured this time: the harness's read, checks, record walk and refresh are 452 B; the
   start-up check and apply are 185 B. The full loader adds the curve decode and table fill and the slot addresses.
   The slot address table is data (~500 B) and can sit in the data-only areas (17.5 KB usable, `docs/code-space-map.md`).
   The code (estimate ~700-800 B without the debug log calls) needs the segment-2 runs the probes use (~690 B with the
   small runs) and a little more: the next step is to write it and measure, then claim the few hundred bytes still
   missing (the `sdk api` shell's area, or a dynamic check of the 3D-engine area in the emulator first).
2. **The format in production code:** `docs/look-file-format.md` (section 5 made a spec with test vectors);
   `epm2mod looks pack` writes LOOKS.BIN from `looks/` (unit tests: the bytes of the twelve pinned looks, the CRC, the
   refusals); the web app writes the same bytes.
3. **The firmware specs:** the loader (section 2.2), the start-up apply (section 2.4), the menu row (section 2.1;
   setting 446, picker, label string), generated as the probes are and checked the same way (free space, op check,
   hookcheck, boot-test, update-path-test, the two-session persistence test, the menu screenshots).
4. **One camera flash for the feature:** load a file; restart without the card; load another; a bad file is refused
   whole; no card. Then pin, the guide in `docs/guide/`, the README line (AGENTS.md rule 7).
5. **Names** stay the slots' names until a probe shows that the menu strings can be written at run time (section 7).

Agent reports behind sections 3 and 4: the session of 2026-11-17 (scratch files were not kept in the repository).

### 9.4 The feature build (2026-11-17, desk and emulator)

- **Step 1 done:** `docs/look-file-format.md`, `src/epm2mod/looks/lookfile.py` and `lookpack.py`, `epm2mod looks pack`
  and `show`, `tests/test_lookfile.py`. The 4-bit curves of all 17 colour fits give exactly the tables of the
  built-in looks, for each of the eight default tables (V). `looks/card-looks.json` lists the looks of films-12d.
- **The firmware:** `builds/card-looks.json` = films-12d + `patches/card-looks.json` (`scripts/mkspec_looks.py`;
  sha256 `889dbcaf49b3ee0a00266ac6420d87f3f47031d0f9e81e3af9b99640ebe35949`). It is a normal build: no debug log. It
  takes over the log's camera-tested pieces: the hook on the GUI state setter's trace call 0x7ECDF6E4 (T_GUI) and the
  dormant task USRTEST_A (T_TASK). At the first GUI state the task applies the stored looks; at the first menu or
  playback screen of a session it loads C:\EPM2LOOK.BIN (scratch 0x603FD040 in the bank tail), checks it, copies it
  to the store 0x603F8000 and calls the bank save API when a byte changed, then applies. The trigger is the first
  menu, as in the probes; the menu row (section 2.1) is the next step, one change per flash. 734 B of code in seven
  runs of segment 2 (the persistence probe's runs, superseded, and the free end of 0x7ECB0888-0x7ECB1000); the slot
  table (1,936 B: 12 kinds and operation lists, the CRC-32 nibble table) in two data areas of segment 3. Section 6's
  code-space question is answered: the probes' code (452 + 185 B) was mostly the debug log's, and a build without
  the log has the room.
- **Checks (V emulator):** a Python model of VERIFY and APPLY in the generator: the built-in looks as a file leave
  every byte of films-12d as it is; C200 in 11 slots changes only slot tables. Free space PASS, op check 0 FAIL,
  hookcheck only the allowed remap7b-code entry, boot-test PASS, update-path-test PASS. `scripts/emu_looks.py`, five
  sessions on one flash state: (1) TEST on the card: flashed looks at start, TEST after MENU (verify, bank save,
  apply in 16 ms of lab time); (2) no file, RAM banks dropped from the state: TEST applied at 36 ms, before any key;
  (3) BAD: refused, TEST stays, no save; (4) no card: TEST; (5) DEFAULT: the flashed looks again. No new firmware
  error entry.
- **Camera test (step 4):** `scripts/mktests.py` writes GREY (Pro 400H with saturation gain 0), SWAP (Pro 400H with
  red and blue swapped by the matrix), BAD (GREY with one byte damaged) and DEFAULT into `build/card-looks/test/`.
- **Camera test passed (V, 2026-11-17, `docs/camera-log.md`):** GREY loaded at the first menu (photo grey, live view
  black and white at once); after a power-off with the file deleted the photo before any key was grey; SWAP loaded
  (red and blue swapped); BAD refused (still swapped); DEFAULT brought back the built-in Pro 400H. Pinned; guide
  `docs/guide/card-looks.md`. Next: the menu row (section 2.1), then a web page that writes the file.

### 9.5 Twelve slots alike, and the menu row (2026-11-17, desk and emulator)

The owner's goal is twelve interchangeable slots loaded through a menu option; grain may go. Flashes only where a test
needs one, so both changes are one candidate, `builds/card-looks-2.json`.

- **Twelve colour slots.** Grainy Film gets the colour slot of the films-12 layout again
  (`films12-entry-grainy-film`, value 111, art code 94; camera-used in `debug-log-films-12` on 2026-11-16) and Gentle
  Sepia its own (`films12-entry-gentle-sepia`, value 112). `patches/films12cl-looks.json` (`scripts/mkspec_slots.py`)
  takes the place of `films12-looks`: Double-X and Provia in the first two extra slots, the other three as before (24 of
  40 ops equal), so the menu keeps the films and names of the pinned build (`films12bw-names`). The grain program
  (stock art code 74) is no longer used.
- **Double-X as a colour look** (`looks/fits/doublex3.npz`, `scripts/fit_bw_colour.py`; results/fit-doublex3.txt):
  saturation gain 0, the art matrix sets the grey mix, one tone curve for the three channels. Model error against the
  Double-X target equal to the grain-slot fit (natural 0.07 / 0.06 mean |dL*| / dE2000 against 0.10 / 0.08; 18 % grey
  117.8 against 117.7). Black and white from gain 0 is V on the camera (GREY test, colour spread 0.32). Grain: none.
- **The menu row** `patches/looks-menu.json` (`scripts/mkspec_lmenu.py`): **Load Looks** (Off / Load) in Custom Menu J,
  in the place of Touch Screen Settings (the E-PM2 has no touch screen). An added row is not possible without moving
  the item table or the child list of `peaking-menu`, and every place has bytes that an earlier spec covers and keeps
  (`src/epm2mod/spec.py` refuses those changes). The value is the dormant setting 449 (picker panel 610). The firmware
  writes 1 into setting 449 at every start (emulator: at 11 and 227 ms), so Off is 1 and Load is 0; a low-level prm
  write back to Off was undone by that start write, so T_GUI sets it with the GUI's own setSetting 0x7EE01D4E (d0 =
  setting, d1 = value), as the menu does.
- **The trigger** (`patches/card-looks-2.json`, `mkspec_looks.py --v2`): when the GUI enters a state that is not a menu
  (0x57xx) and not power-off (0x2xxx), T_GUI reads setting 449; at Load (0), and when the card is not being written, it
  sets it to Off and starts the task in mode 1. The load at the first menu is gone. The start-up apply is unchanged.
  750 B of code.
- **Checks (V emulator):** model: the built-in looks give the base's bytes, C200 in all 12 slots changes only slot
  tables; free space PASS, op check 0 FAIL, hookcheck only remap7b-code, boot-test PASS (it failed first: the start
  write of setting 449 made a load at start, which led to Off = 1), update-path-test PASS. `scripts/emu_looks.py
  --v2`, five sessions: menu in and out without Load: no load; Load: C200 in all 12 slots, saved; restart without the
  file: applied at start, the row reads Off; BAD refused; no card; DEFAULT back.

## 10. Acceptance criteria (draft, 2026-11-17, for the owner to confirm)

Written after `card-looks-2` worked on the camera and was not accepted: the menu names did not follow the loaded
looks, and no criteria had been set before the build. A build is pinned only when every agreed criterion passes.

| # | Criterion (what the user does and sees) | Check | card-looks-2 | card-looks-3 (emulator) |
|---|---|---|---|---|
| 1 | MENU -> Custom Menu -> J -> Load Looks -> Load: the looks of EPM2LOOK.BIN replace the current ones | camera | pass | pass (loads at OK, in the menu) |
| 2 | Nothing loads unless the user chooses Load | camera | pass | pass |
| 3 | The looks stay after power-off and without the card, until the next load | camera | pass | pass |
| 4 | Any look goes into any of the 12 entries | emulator, camera | pass | pass (all 12) |
| 5 | Every place that shows a film name shows the loaded look's name | emulator, camera | **fail** | pass: Picture Mode strip, Shooting Menu Picture Mode list, ART list, all 30 string ids, in English and Japanese; playback info: camera |
| 6 | After Load the camera says what happened | emulator, camera | **fail** | pass: the row reads Loading, then Loaded / No file / Bad file / Built-in |
| 7 | The built-in looks come back from the camera, without a file | camera | **fail** | pass: Load Looks -> Built-in |
| 8 | Live view shows the loaded look as the photo will be (tone included) | camera | **fail** | built: member-0 tables for the 10 three-table slots; camera only |
| 9 | A photo records the loaded look's name where it records the film today | camera | not checked | today no film name is recorded (EXIF ArtFilter is the stock number); question for the owner |
| 10 | The row and its messages are readable in the user's menu language | emulator | English only | English texts in every language (Japanese checked) |
| 11 | A bad or missing file never stops a start or a flash | emulator, camera | pass | pass (boot-test, update-path-test, sessions 3 and 7) |
| 12 | Movies show the loaded look as far as they show the built-in looks | camera | not checked | the same tables as the built-in looks (model); camera |
| 13 | No existing menu row is removed or changed (owner, 2026-11-17) | emulator crawl | **fail** (Touch Screen Settings replaced) | card-looks-3 **fail**; card-looks-4 pass (section 10.2) |

### 10.1 card-looks-3 (2026-11-17, desk and emulator)

`builds/card-looks-3.json` = the twelve-slot layout + `patches/looks-menu-2.json` (Off / Load / Built-in, status text
1495; `scripts/mkspec_lmenu.py --v3`) + `patches/card-looks-3.json` (`scripts/mkspec_looks3.py`), sha256
`0ca95da065aefa1cced5cdb30368924a5d133a79e08ae1144ead236f856438f2`, `first_code` (930 B in the reclaimed code area
0x7EE53830 of segment 3).

- Names: the loaded language's text table is in RAM (blob 0xBFF3D000; its first word is the address of the pointer
  array). 30 string ids show the 12 entries' names (the stock English text of each is the entry's name, with or
  without an icon tag). The loader points each at a copy of the language's string with the look's name after the
  tag; empty names keep the language's string. A language change loads the table again: T_GUI sees that id 1498 is
  not our "Load Looks" and runs mode 3.
- Status: id 1495 (the row's text for Off) points at the language's "Off" or at Loading / Loaded / No file / Bad
  file / Built-in. The trigger now runs at every GUI state call (the GUI calls the setter at every key, also in the
  menu), so the load runs at OK and the row shows the result at the next key.
- Built-in: mode 0 copies every table that a look writes (41,652 B) to RAM 0x7E4D0800 before it applies the store;
  Built-in (value 2) empties the store, saves the bank and copies them back; a load starts from them, so the entries
  a file does not list are built-in again.
- Live view: live view reads member 0 of the tone records, the stills member 1 (half-press, photos). The ten
  three-table slots shared the stock member-0 tables; each now gets its own, made from its stills table by linear
  interpolation (exact within 6 of 1023 for all fits; built-in looks too), in RAM 0x7E4DB000-0x7E4ED000, and its
  records point at them. Light Tone and Cross Process have all eight tables of their records written already.
- Start-up: the task's priority is 13 (was 11): the snapshot and the live tables (about 15 ms of work) wait for the
  firmware's tasks; with 11 boot-test failed (time stamps 5.5 ms late).
- RAM gap 0x7E4C9800-0x7E4FE000: zero through start, menus, playback, half-press in the emulator (stock-built code
  never writes it; the debug log's ring at 0x7E4F9000 is camera-tested RAM there).
- Checks (V emulator): free space PASS (first code), op check 0 FAIL, hookcheck only remap7b-code, boot-test PASS,
  update-path-test PASS; `scripts/emu_looks3.py` seven sessions PASS against the model (tables, live tables, records,
  names, row texts, status); shallow crawls P and ART: all screens equal to card-looks-2 (no look stored); screens:
  the row (Loading, Loaded, Bad file, No file, Built-in), the Picture Mode strip and list and the ART list with
  loaded names (16 characters fit), Japanese. Not in the emulator: the picture (live view, photos, movies),
  playback of a photo (stock faults there too).

### 10.2 Camera result of card-looks-3, and card-looks-4 (2026-11-17)

- card-looks-3 on the camera (owner): criteria 3, 4, 5 (menus), 6, 7, 8, 12 pass. The first start applied the look
  file left in the store from the card-looks-2 test (SWAP), with its names (ART 3 "Double-X in 2", ART 5 "Pro 400H in
  4"): the names follow a stored look on the camera. Not accepted: it replaced Touch Screen Settings (criterion 13).
  Open from that test: the playback info name (step 7); the uploaded photos were not the test's.
- card-looks-4 (sha256 `4829e8fa1e3b264647e4f97d82578de2d5f71481484a7d63f0cd87b96cd32431`): `patches/custom-menu-rows.json`
  (`scripts/mkspec_rows.py`) takes the place of `peaking-menu`: all its operations unchanged (the Peaking list, texts
  and code: camera-tested bytes) except the two tables, now 81 rows at 0x7EBF1FF0 (0x7EBF1FF0-0x7EBF2000 is free; the
  table ends where peaking-menu's ended) and 81 entries at 0x7EBF2600, with Load Looks at the end of J; row constants
  from level-adjust-row's 78 / 79 / 158 B to 80 / 81 / 162 B; group sizes A 11 and J 7. A replacement and not a
  delta, so no byte that peaking-menu keeps is changed (src/epm2mod/spec.py). `looks-menu-3` = `looks-menu-2` without
  the row edit; `card-looks-4` = `card-looks-3` with its first run at 0x7EBF2890 (the child list ends there).
- Checks (V emulator): free space PASS, op check 0 FAIL, hookcheck only remap7b-code, boot-test PASS,
  update-path-test PASS, `emu_looks3.py --v4` seven sessions PASS, crawls P and ART against the pinned card-looks:
  378 / 214 units equal, only the J page differs (6 rows -> 7, Touch Screen Settings kept).


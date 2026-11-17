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

Agent reports behind sections 3 and 4: the session of 2026-11-17 (scratch files were not kept in the repository).

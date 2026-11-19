# Review 4: `interval-frames-240.json` (2026-11-13)

Adversarial review of the 6-op data spec, on top of the film set + `interval-timelapse-v2.json`.

- **Labels:** **V** = read in the bytes or the disassembly of stock block 0, or of a scratch-built image. **I** = inferred.
- **Method:** two images built with `tools/emu/patchblock.py` into `/tmp/scratch` only: films + v2 (`base`, sha256 `8992f2c2…`) and films + v2 + this spec (`new`, sha256 `7d460c4c…`, the value the README gives). Nothing written under `build/`. No flash, no commit, no emulator run (all checks are static).
- **Result:** **no blocker found.** Three should-fix items (S1–S3); none is a boot or brick risk. The largest open point is S1: the "number + unit" row kind has no stock precedent in this editor's page class.

## 0. Verdict table

| # | Question | Verdict | Level |
|---|---|---|---|
| 1 | Value list at 0x7E4C9100: loaded, unreferenced, harmless to boot | SAFE; keep this location | V |
| 2 | 128 editor rows at 0x7EBF1100: placement, format, count, index limit | SAFE; 128 is the true maximum | V |
| 2b | Row kind 4 with unit string 0 draws correctly in this editor | NOT PROVEN (S1) | I |
| 3 | Value-list semantics, index against value, neighbours 482 / 486 | SAFE; one constraint (S2) | V |
| 4 | Consumers of 100–240 | No cap found in what was read; movie maker and counter not closed (S3) | V / I |
| 5 | Overlap and containment | SAFE | V |

## 1. The value list at 0x7E4C9100

- **Loaded by the reset stub, unconditionally (V).** 0x7E421216: `a0 = 0x402CF000` (flash), `a1 = 0xBE430000`, size `0x7E4C9800 + 0x81BD0000 = 0x99800`, `call 0x7E4217E6`. Flash and runtime agree with the linear rule (0x7E430000 − 0x7E421020 = 0xEFE0 = 0x402CF000 − 0x402C0020). The only branch before it (0x7E42118A / 0x7E421190) rejoins at 0x7E4211D8, before the copy. The constants 0x402CF000, 0xBE430000 and 0x81BD0000 each occur once in block 0.
- **Every boot path in block 0 passes this copy (V + I).** The firmware updater is segment-1 code (review 1), so an SD update runs after the same reset stub. A separate recovery loader outside block 0, if one exists, does not read block-0 padding (I).
- **Really 0xFF, in stock and in films + v2 (V).** The 0xFF run is 0x7E4C90CA–0x7E4FDFFF in both images. The spec writes 0x7E4C9100–0x7E4C917F; the op's `expect` (136 B with context) matched on both.
- **Unreferenced (V).** No 4-byte window at any alignment into 0x7E4C9000–0x7E4C9800, its uncached alias, or the flash addresses, except the copy-end constant at 0x7E421203. In `new` the only added window is the record pointer at 0x7E84C600. The remaining hits are opcode + immediate noise (for example 0x7E6A2CAB = 0x803682CD).
- **Not reachable by fall-through (V).** The last code before the padding is a fatal handler that ends in `bra 0x7E4C90C8` (branch to itself). 0x7E4C90CA–0x7E4C90FF stays 0xFF.
- **No marker, checksum or pool use found (V for the scan).** The two words the stub stores from these constants (0x604DA480 = 0x7E4C9800, 0x604DA484 = 0x7E8F3114) have no reader by direct address. v2 already changed two bytes in this range (0x7E4C3EB8, 0x7E4C3EC8) and booted, so no boot check covers the kernel range. Limit: v2 edited existing data, not padding; padding use was camera-tested only in segment 1 (`three-films-1`).
- **A wrong byte here cannot affect boot (V).** The list is read only by the mcon scan and step functions (0x7E707147, 0x7E7074B5) and only for info 483.
- **Who reads record 0x7E84C5FC, and when (V).**
  - The record is entry 477 of the 505-entry table 0x7E84A0B8 (20 B each); the hash is built by 0x7E7077D3.
  - **Every getter call for 483** (0x7E6FCC91 → 0x7E6FEA5F → 0x7E70708D) scans the list, then discards the index because the record's GUI-table pointer is 0. So the list is read whenever any code reads the frame count, not only in the menu.
  - No boot-time validation or clamp of saved values against the list was found: the setter 0x7E6FEAE0 → 0x7E7070B4 returns the value unchanged when the GUI-table pointer is 0, then writes the prm.
- **Is the reclaimed segment-2 block a safer home? No.** All 505 stock lists are in segment 1; the readers are segment-1 code that can run before Usr1 loads segment 2. A list in segment 2 would add a load-order dependency that the kernel range does not have. **Recommendation: keep 0x7E4C9100.**

## 2. The 128 editor rows at 0x7EBF1100

- **Placement (V).** 0x7EBF1100–0x7EBF1EFF, inside 0x7EBF1090–0x7EBF3BAC and inside the segment-2 load 0x7E8F5800–0x7ECB1000. No window into 0x7EBF1090–0x7EBF1F20 in films + v2; in `new` only the descriptor pointer at 0x7F00C6F8. The films + v2 image is identical to stock over the whole reclaimed block. The pointer table that ends at 0x7EBF1090 and the first 0x70 bytes of the name list are untouched, so any reader running off that table sees what stock shows.
- **Load order (V).** Usr1 loads segment 2 before segment 3, and the only reader is segment-3 GUI code. The loader 0x7E504AF9–0x7E504DA0 is unchanged by every spec.
- **Row format (V).** Descriptor table 0x7F00BC8C, 180 entries of 16 B `{u16 info, u16 count, u32 wrap-up, u32 wrap, u32 items}`. Items are 28 B.

| Field | Stock frame row (kind 2) | Stock Custom Self-timer row (kind 4) | New row 100–240 |
|---|---|---|---|
| +0 u8 | 0 | 0 | 0 |
| +1 u8 kind | 2 | 4 | 4 |
| +2 u16 | label id (1910 = "99f") | number N (30 … 1) | N (240 … 100) |
| +4 u16 | 0 | unit id 247 ("sec") | **0** |
| +6..+11 | 0 | 0 | 0 |
| +12 u32 | 2000 | 2000 | 2000 |
| +16 u32 value | 99 … 1 | 30 … 1 | 240 … 100 |
| +20, +24 | 0xC0, 0xC5 | 0xC0, 0xC5 | 0xC0, 0xC5 |

  - All 128 rows decoded: values 240, 235 … 100, then 99 … 1; the 99 rows for 1–99 are byte-identical to the stock rows.
  - String 0 is the empty string in all 34 language tables of block 1 (V).
  - Stock kind-4 numbers go up to 14000 (info 107), so three digits are within the formatter's range (I for this editor).
- **Count and terminator (V).** The class uses the descriptor count only; no terminator row. Row 128 (0x7EBF1F00) is old name text and is never indexed.
- **Index 127 and the sign extension (V).** Key handler 0x7EE01767:
  - Up: index 0 stays 0 unless descriptor +8 = 1 (it is 0 for 483); otherwise index − 1.
  - Down: if index = count − 1 it stays (no wrap); otherwise index + 1. With count 128 the index never leaves 0..127.
  - `extb` at 0x7EE017BB / 0x7EE017FC is correct for 0..127 and wrong from 128. **128 rows is the exact maximum; no off-by-one.**
  - Open (0x7EE01699 → 0x7EDC81A8) and confirm (0x7EDC8584) use the index unsigned.
- **Per-row arrays in the page object (V, note N1).** The object is 1,764 B: 40 u16 flags at +88 and 39 row structures of 38 B at +258. 0x7EDC8127 writes both arrays at index k for every row whose value is "unavailable". Stock already has 99 rows in this class, so this is not new. It never fires for 483: the availability test (0x7E7007F4) finds 483 in none of its three tables (0x7E825DA8, 0x7E8266C4, 0x7E818DC8).

### S1 (SHOULD-FIX): kind 4 has no stock precedent in this page class (I)

- **Evidence (V).** Panel factory table: list 638 is built by 0x7EE01678 (vtable 0x7F010D6C, base class 0x7EDC7EAA). Only two stock lists use that class: 148 (info 174, kinds 3 and 8) and 638 (kind 2). The Custom Self-timer editor, list 632, uses a **different class** (0x7EE0142B, base 0x7EDEE169). README §13.2 presents list 632 as the precedent without saying this.
- **What supports the spec (V + I).** The 638 class copies kind and arguments into row 0 of the shared 1,564-byte display record (slot 57), and the common renderer 0x7EDCED5A reads that record. Seven lists of the generic class 0x7EDC7ECB, which has the same base as 638, carry kind-4 rows (for example 498 and 134). So kind 4 is probably a renderer feature, not a class feature. The renderer's kind dispatch was not found, and no stock kind-4 row has unit 0.
- **Failure mode (V).** Cosmetic. Confirm stores the item's **value** field, not the label: 0x7EDC8584 passes `(16,item)` to the setter. A blank or wrong label still sets the right count.
- **Fix.** Make camera test 1 the gate, and add: "if 100–240 show blank or garbage, stop and report; the count is still stored correctly". Correct the README sentence on list 632.

## 3. Value-list semantics

- **Record layout (V).** `{u16 info, u16 key, u32 list, u32 gui_table, u16 total_bytes, u16 elem_size, u8 clamp, u8 type}`; count = total / elem. New record: list 0x7E4C9100, total 128, elem 1, clamp 1, type 1.
- **Nothing stores an index (V).**
  - Editor confirm writes the item value (0x7EDC8584 → 0x7EE01D4E → 0x7E9CA978 mode 0 → 0x7E6FEAE0).
  - The editor cursor is recomputed from the stored value on every open (0x7EDC81A8).
  - prm 0xDE21 holds the raw u8; Myset copies prm bytes.
  - So no saved index can change meaning.
- **Stored value not in the list (V).**
  - The getter returns it unchanged.
  - The editor opens on index 0 = **240** (stock: 99).
  - The settings list shows it as a plain number through the kind-4 row (§4); stock shows nothing.
  - The stepper treats it as the last entry.
- **Neighbours (V).** Records 476 (482) and 478 (486) keep their own pointers (0x7E849F54, 0x7E849FB9) and totals (2, 2). The old 99-byte list is unchanged and now unread.

### S2 (SHOULD-FIX): 128 is the mcon error value; guard the generator (V)

- **Evidence.** 0x7E7072A4 returns 128 for a bad index. 0x7E6FCAD6 and 0x7E9E7727 test `cmp 128` on a candidate value. 0x7E9CAAD3 treats a step result of 128 as failure. These are raw u8 values for a type-1 list.
- **Today:** the list holds 125 and 130, not 128. Safe.
- **Fix.** Add `assert 128 not in VALUES` to `scripts/mkspec_frames240.py` and one README line. A later respacing (for example by 4) would put 128 in the list and break stepping and enumeration silently.

## 4. Consumers of 100–240

- **Settings-list row (V).** 0x7EDE22DE scans the 762-row table 0x7EFF0460 in order.
  - A row of the same info with kind 4 (info ≠ 474) prints the **current value** with that row's unit (0x7EDE2375), whatever the row's own value is.
  - A kind-2 row must match the value (0x7EDE25A2).
  - The 483 rows for 1–98 are kind 2 and come first, so 1–98 keep "Nf". The row for 99 is last and is now kind 4, so 99, 100–240 and any value without a row print as a number with unit 0. This is why 99 changes.
  - Stock uses the same shortcut for info 107 (one kind-4 row, values to 14000).
- **Every `mov 483` site in the function listing (V):**

| Site | Use | With 100–240 |
|---|---|---|
| 0x7EA89F39, 0x7EA8C4AE, 0x7ECDA5C8 | end test 483 == 489, 32-bit | fine |
| 0x7E9841A5 | stores 483 − 489 as u16 (remaining frames) at +316 | fine |
| 0x7E68B69C, 0x7E68B88C | `divu` by (483 − 489) | no cap; divides by zero when equal, as stock |
| 0x7E512B33 | passes 483 as an id | no value use |
| 0x7E5E9D53 | the constant 483 in another table | not the info |

- **No `cmp 99` or `cmp 100` on the frame count** in the mcon range or at the sites above. The `99` at 0x7E703C24–0x7E703CA4 is info id 99.
- **Availability and restriction tables (V).** 483 is in none, so no value is hidden or rewritten.
- **Enumeration (I).** Count getters return u16; the largest stock list has 120 entries, so 128 is a new maximum. Callers with fixed buffers were not all read; those read use fixed info ids (8, 9).

### S3 (SHOULD-FIX): the test plan does not cover 240 with the movie on (I)

- **Not closed by reading.** The movie maker gets 489 at 0x7EA9938E. The allocation 0x7E6D4B82 is 2 × n from pool 98, but n was not traced to the frame count, and pool limits were not read. The on-screen remaining counter and its digit count were not found.
- **Fix.** README §13.7 test 4 uses 120 frames. Add a run of **240 frames with Time Lapse Movie On**, and check that the clip plays to the end. Note the counter above 99 in the same run.

## 5. Overlap and containment

- **Diff (V).** films + v2 against films + v2 + this spec differs only inside the six ops: 128 B at 0x7E4C9100, 4 B in the record, the rows 0x7EBF1100–0x7EBF1EFF, 3 B in the row at 0x7EFF5DA0, 5 B in the descriptor.
- **No overlap (V).** Op ranges, with their 4-byte context, tested against the block-0 byte ops of 59 specs under `patches/`, `patches/history/`, `experiments/` and `tools/emu/specs/`: 0 overlaps. The spec also applies on stock alone.
- **No code touched (V).** The six ranges are 0xFF padding, the mcon record table, debug name text, the option-row table and the descriptor table. Films + v2 leaves the reset stub, the Usr1 loader, the mcon code, the 638 class code, the list-page code and all four tables at stock.
- **Containment (V unless marked).**

| Wrong byte in | Worst effect |
|---|---|
| Value list | Wrong step target for 483; getter and end test use the raw prm, not the list |
| Record pointer or total | Scan of other memory for 483 only; the index is discarded (read-only) |
| Editor rows | Wrong label or wrong value stored for that row |
| Descriptor pointer or count | The Frame editor reads wrong rows; a bad pointer can fault when the editor opens, not at boot (I) |
| Option row | Wrong text in the Time Lapse Settings list |

## 6. Notes

- **N1.** Do not make any frame value "unavailable" in a later patch: 0x7EDC8127 would write past the 39-row arrays (§2). Stock has the same exposure.
- **N2.** A stored value outside the list (0 on a body whose MODE bank predates the v2 defaults) opens the editor on 240. Pressing OK then stores 240 = 240 shutter actuations. Stock does the same with 99.
- **N3.** The list page now shows "0" for a stored 0, where stock shows nothing.
- **N4.** Emulator results in README §13.5 were not re-run here.

# Review 3: `interval-timelapse-v2.json` on the film set (2026-11-13)

Adversarial review before a camera flash. Read-only: nothing was built under `build/`, `tools/build.py` was not run, no flash, no commit.

- **Labels:** **V** = read in the bytes / disassembly or run by me. **I** = inferred.
- **Images (scratch, `tools/emu/patchblock.py`):**
  - stock block 0, sha256 `1b7c4bb1…71468d`;
  - films = remap7b-code + seven-fixes-1 + seven-movie-1 + seven-structure-extra + seven-films-5 + xp-adaptive-hue-off + seven-labels (the `seven-films-6` list in README.md step 3 and in the last row of docs/camera-log.md), `00d4f31f…380398`;
  - films + v2, `8992f2c2…693d28ec` (the same hash with v2 applied first);
  - stock + v2, `d8c35ce3…2c327f69`;
  - E-PL6 1.4 block 0, extracted with `oetool.parse` into scratch.
- **Scratch:** `/tmp/scratch/rev3/` (`ovl.py`, `callers.py`, `d.sh`).

## Verdict

- **No blocker found.** Every displacement, call frame, displaced instruction, table byte and flag access that I checked is correct on both bases.
- **No should-fix item in the bytes.** Four notes (N1–N4) are optional improvements or text fixes.
- **Not proven, as before:** that nothing writes the padding or the flag word through a run-time pointer (I, see §4), and all behaviour on the camera. v2 is still not camera-tested.

## Findings

### N1. NOTE: slot 0 is a slightly safer flag word than slot 1 (V layout, I value)
- **Rows are 1-based (V).** The value switch tests `cmp 3,d0` for the row whose table record is index 2 (param 111). The consumers use `table + 10 × row − 10` (for example `movhu (-6,a1)` at 0x7EDED089). So slot 1 (0x602BE878) belongs to a real row (row 1, no value case), and slot 0 (0x602BE874) belongs to no row.
- **Evidence that slot 1 is safe now:** §4. I found no reader or writer.
- **Optional fix:** use 0x602BE874 in the four trampolines (4 imm32 changes). The .data initial value there is also 0. This is not needed for the first flash.

### N2. NOTE: stale text
- `tools/emu/cases.py`, case `ivl_selector`: the description still says "patched: jmp to T2 0x7F033E40". v2 uses 0x7ECB0DC8.
- The spec has no `expected_sha256` (correct until a camera test).
- The op at 0x7ECB0BA0 starts 4 bytes before the table (4 context bytes of 0xFF). The description's range 0x7ECB0BA4–0x7ECB0EE2 is the content range. Both are correct.

### N3. NOTE: a stuck flag is possible in the same way as on the E-PL6 (V code, I effect)
- **Set:** only after an accepted request (`calls` returned 0). The refused path and the not-mounted path do not set it (V, both bodies).
- **Clear:** only in `receiveEndCreateMovie` and `receiveErrorCreateMovie`, which are entries 0x3000047 / 0x3000048 of one GUI event table (E-PM2 0x7EEE8EA8–0x7EEE8EC8). The 36 words around it (0x7EEE8E48–0x7EEE8ED4) equal the E-PL6's around 0x7EEE9F1C, with each handler pointer at the paired function (V).
- **If neither event arrives** (I: for example the GUI leaves this state), the flag stays 1 until the next boot. The .data copy at reset sets it to 0.
- **Effect of a stuck flag:** `receiveEndMediaMountForEndWait` skips the end check 0x7ECDA7D1. `createTimeLapseMovie` does not test the flag, so **movie creation is never blocked** (V). An interval sequence that ends through the media-mount wait could stay open until a power cycle (I). The E-PL6 has the same behaviour.

### N4. NOTE: items I did not re-verify
- The string ids 1357–1361, 1709–1713, 696 and panel 628 in block 1 (author's `results/strings-timelapse.tsv`). `seven-labels` has only same-length `bytes` ops on art-filter names (V), so it cannot move an id.
- Row-number constants outside the menu class and the 25 formatter call sites (review 2 diffed 0x7EDAA900–0x7EDB2400).
- README §4 rows 8 and 9 (two E-PL6 GUI differences that v2 does not port). My diff of 0x7ECD9F4B–0x7ECDA82E against the E-PL6 shows exactly those two, the four flag sites, and one moved function (V).

## What I checked and found correct

### 1. No overlap (V)
- v2: 48 ops, all `bytes`, all block 0. No two v2 windows overlap.
- Against every op of the 8 specs in `patches/` (expect windows included): 0 overlaps. Nearest: seven-movie-1 ends at 0x7ECB0B9D, v2's window starts at 0x7ECB0BA0. seven-films-5 is 464 bytes away. `pixel-hacking` and `seven-labels` touch block 1 only.
- films + v2 differs from films in **921 bytes, exactly the changed bytes of v2's ops**. The same is true for stock + v2 against stock.
- All v2 `expect` bytes are equal in stock and in the films image.

### 2. The new location 0x7ECB0BA4–0x7ECB0EE2 (V unless marked)
- **0xFF:** 0x7ECB0B9E–0x7ECB0FFF is 0xFF in stock and in the films image.
- **Loaded:** Usr1 0x7E504BF2–0x7E504C18: `d2 = 0x7ECB1000 − 0x7E8F5800`, `a0 = 0xBE8F5800`, `a1 = 0x80794800`, `call 0x7E451306`. The flash source of 0x7ECB0BA4 is 0x80B4FBA4 = file offset 0x88FB84 + 0x402C0020, which agrees with the linear block layout.
- **Unconditional:** Usr1 0x7E504AF9–0x7E504BF2 has only `mov`, `movhu`, `movm`, `add`, `clr`, `exth` and `call`. It has no branch.
- **Unreferenced:** an any-alignment scan of stock for 0x7ECB0800–0x7ECB1100 and the 0xBE alias finds 0x7ECB083C (the segment-2 constructor list: 76 bytes, constant count, ends at 0x7ECB0888) and the copy-end constant 0x7ECB1000. The flash-alias hits (0x40B4FAxx, 0x80B4Fxxx) are all an opcode byte plus another immediate (for example `fa b4 40 01`, `fc dc fe b4 80 7e`).
- **Code runs there:** the films image has code at 0x7ECB0888 (`mov imm,a1; bra`), 0x7ECB0958–0x7ECB0984 and 0x7ECB0B80–0x7ECB0B9D (`mov n,d2; jmp`), reached through pointer tables at 0x7E78C158…, 0x7E7FF00C…, 0x7E807830…, 0x7E854A28. Each stub ends in `jmp`; none falls through into v2's bytes. These builds are logged OK on the camera (docs/camera-log.md, 2026-11-12 and 2026-11-13). That the stubs were executed in those tests is I (the tests were of the entries that use them).
- **Not overwritten (I):** v2's bytes are in the same 0x1000 page as the film code that works on the camera.

### 3. Every pointer, jump and call (V)
- **Seven hooks:** 0x7E98855F → 0x7ECB0DB0, 0x7E997BD9 → 0x7ECB0DC8, 0x7EDEC335 → 0x7ECB0D78, 0x7ECDA56C → 0x7ECB0E80, 0x7ECDA1B2 → 0x7ECB0E98, 0x7ECDA1D5 → 0x7ECB0EB0, 0x7ECDA2A7 → 0x7ECB0EC8. All decode as `jmp` to the intended first byte.
- **Dead bytes:** no branch in stock targets 0x7E988560–64, 0x7E997BDE–C66 (from outside the old body), 0x7ECDA1B3–B8, 0x7ECDA1D6–DB, 0x7ECDA56D–76, 0x7EDEC336–49, or any interior byte of the new code. No data word points at the selector or at the formatters.
- **Call frames against all other callers (patched image):**

  | Callee | Frame in v2 | Other callers |
  |---|---|---|
  | 0x7E6FCC91 getter | `[],4` | 106, all `[],4` |
  | 0x7E997C67 | `[d2],16` | all `[d2],16`; returns `ret [d2],16` |
  | 0x7E997DC9 restore | `[d2,a2],16` | 4, same |
  | 0x7E997E94 hold | `[],4` | 14, same |
  | 0x7E9670E9 print | `[d2,a2],12` | all same |
  | 0x7EE01D38 getSetting | `[d2,a2],12` | 790, same |
  | 0x7ECE631E print | `[a2,a3],12` | 687, same |
  | 0x7ECD50DE | `[],0` | 4, same |

- **Stack:** no trampoline changes sp. Each added `call` is at a point where the host function itself makes calls at the same sp, so (0,sp) is free for the return address.
- **Value-switch cave 0x7ECB0D78:** `cmp 11 / beq / cmp 12 / beq / jmp 0x7EDEC34A`; cases `mov 482|180,d0; mov sp,a0; inc4 a0; call getSetting; mov 11|12,d0; jmp 0x7EDEC432`. Patched 0x7EDEC2C0–0x7EDEC4E0 with the cave equals E-PL6 0x7EDED156 in a normalised diff: only the in-line placement of the new case and a d2/d3 swap differ.
- **Menu class:** patched 0x7EDEB923–0x7EDEC335 and 0x7EDEC4B1–0x7EDED0F6 against the E-PL6: 0 differing instructions (addresses masked). All 22 references to the tab table and the tab counts are inside this class and pair one to one with the E-PL6's.
- **T1 0x7ECB0DB0:** `call hold`, then `clr d0; mov d0,(20,sp); mov sp,a0; add 20,a0` (the 6 displaced bytes, no PC-relative operand), then `jmp 0x7E988565`. E-PL6 0x7E989552 has the same call at the same place, after the same `bne`.
- **T2 0x7ECB0DC8:** 51 instructions side by side with E-PL6 0x7E998C41: every mnemonic, operand and branch target corresponds. Only the assert strings and the line number (721 / 739) differ. All 9 call sites use `[],16`.
- **Helpers:** 0x7E997C67–0x7E997F17 equals E-PL6 0x7E998CE5–0x7E998F95 (206 instructions, 0 differences). **Every entry point in that range has the same number of callers on both bodies after the patch** (hold 16/16, restore 5/5, and 12 more). So no E-PL6 release of the hold is missing.
- **Tables:** the top table at 0x7ECB0BA4 equals E-PL6 0x7EFFF864 (380 B). The page-3 list at 0x7ECB0D24 equals E-PL6 0x7EFFA324 (84 B). Both are 4-aligned. The six imm32 sites decode as `mov imm,a0` / `add imm,dN|aN` with 0x7ECB0BA4. The record at 0x7EFFA4B0 equals the E-PL6 record at 0x7EFFBBD8 apart from the pointer. The old list had one reference (0x7EFFA4B0); the old table had the six loads.

### 4. The movie guard (V unless marked)
- **E-PL6 sites:** 0x602B4B20 occurs 4 times in block 0: set 0x7ECDA8C1 (`mov d2,(abs)`), clear 0x7ECDA4B3 and 0x7ECDA4DD (`clr d0; mov d0,(abs)`), test 0x7ECDA5CA (`mov (abs),a1; cmp 0,a1; bne ret`). The E-PL6's flag is also a .data word with initial value 0.
- **Trampolines against the E-PL6, path by path:**
  - T3: print; `mov 1,d2`; store; `jmp 0x7ECDA5AE` (`cmp 0,d2`). Equal to E-PL6 0x7ECDA8B8–0x7ECDA8C7. The two other paths of `createTimeLapseMovie` are not changed.
  - End / error: print; `clr d0`; store; back to 0x7ECDA1B9 / 0x7ECDA1DC. Equal to the E-PL6. The code after it sets a0, a1 and d0 again.
  - T6: `call 0x7ECD50DE` (d0 = 0 from the `clr` before the hook); load; `cmp 0,a1`; `bne` → 0x7ECDA2B3 (`ret [a2,a3],16`); else 0x7ECDA2AC (`mov a3,a1; mov a2,a0; call 0x7ECDA7D1`). Equal to E-PL6 0x7ECDA5C5–0x7ECDA5DB.
- **Access width:** all four are 32-bit absolute moves (`fc 89`, `fc 81`, `fc 81`, `fc a1`), the same encodings as the E-PL6. They touch 0x602BE878–0x602BE87B only.
- **Initial value:** ROM 0x7E8EED38 = 0 in stock, films and films + v2. The films change no byte of the .data image 0x7E8DA000–0x7E8F3114. v2's .data op starts at slot 11 (ROM 0x7E8EED60).
- **Other users of 0x602BE878:**
  - An any-alignment scan for immediates 0x602BE700–0x602BE97F finds no value in 0x602BE875–0x602BE907. The base 0x602BE874 has 2 uses: `add imm,a2` in the formatters 0x7EE01DDA and 0x7EE01E8C.
  - Both formatters only read the table (`mov (a2),a1; mov (a1),d0`). They never store through a2.
  - They have 13 + 12 callers, no `jmp`, no data word, and no branch into their bodies from outside. 22 sites pass 34, one passes 5, one passes 35. The site 0x7EDEC437 gets d0 from 9 `jmp 0x7EDEC432` sites and one fall-through, with 3, 5, 6, 7, 8, 10, 11, 12, 14 or 33. **No site passes 1 or a computed value.** The row arguments equal the E-PL6's site for site.
  - 0x602A9B40 (the .data start) is used only by the reset copy and as a variable (the `rand` seed). Nothing copies the .data image a second time.
  - **Bulk writes (I):** a `memset` or struct copy over this area would also destroy slots 3–35, and the value column would stop working in stock. A scan cannot exclude a computed pointer.
  - Menu reset and Myset act on the MODE area, not on GUI .data (I).
- **If a row-1 formatter call existed (I):** stock would read address 0. With the flag set it would read address 1. Neither happens.
- **A safer word:** N1. The words next to the E-PM2's sibling flag 0x602B4AF8 (0x602B4AFC, 0x602B4B00, 0x602B4B04) all have code references, so there is no free word there.
- **Emulator:** the author's case `ivl_movie_guard` run on my scratch films + v2 image: 10 rows, 4 changed as described (set, clear, clear, end check skipped), 0 flagged.

### 5. Menu on the combined image (V)
- **The films do not edit any menu data.** films = stock in the top table 0x7EFFE13C (37 records), in 0x7EFF8000–0x7F000000, in the menu class, in 0x7EDE3000–0x7EE03000, and in .data. So the relocated table, built from stock rows, reverts no film edit.
- **Rows:** records 0–9 and 11–36 of the new table equal stock records 0–9 and 10–35. Record 10 (row 11) is `00 00 4d 05 4e 05 02 01 01 00` (label 1357, help 1358), as on the E-PL6. A zero terminator follows.
- **Tab layout:** RAM 0x602BE3CE, 0x8E bytes (6 lists and the counts 6, 6, 6, 10, 3, 6) equal E-PL6 RAM 0x602BE3F6.
- **Value lists:** slots 0–37 against E-PL6 RAM 0x602BE89C: the same slots are non-zero (3, 5, 6, 7, 10, 11, 12, 14, 33, 34, 35), and each pointed list has the same contents.
- **OK target:** the page-3 list has `{628, 482}` in fifth place. Panel 628 code is not changed.
- **Rodata near the lists:** a word diff of 0x7EFF8800–0x7EFFE400 against the E-PL6 shows the page-3 entry, the top table, and 8 entries in other pages' lists (settings 0x926, 0x209, 0x141, 0x8A5, 0x156, 0x101, 0x111, 0x1C3). Those are other E-PL6 features and are not part of this patch.
- **Out-of-range row (I):** an unused tab slot (0xFF) would index 0x7ECB1590, in the unloaded gap after segment 2. The tab counts bound the cursor, as in stock.

### 6. Film set against v2 (V)
- All film ops are in segment 1 (0x7E546161–0x7E880FE4), in the padding 0x7ECB0888–0x7ECB0B9D, and in block 1. v2's ops are in the MODE defaults, .data, 0x7E98855B, 0x7E997BD5, the GUI segment and the padding after 0x7ECB0BA0.
- No 4-byte value in the films' new bytes points into a v2 window.
- No film op touches the value switch, a formatter call site, the tab layout, a page record, the selector or the four GUI handlers.
- **Three specs in `patches/history/` use the same padding.** They are not in the camera build and must not be combined with v2.

## Advice for the first flash (I)
- Build the seven film specs + v2 in the README order. The block-0 hash to expect is `8992f2c2…693d28ec`.
- Check the menu first: tab 1 has 6 rows, row 11 opens Time Lapse Settings, Flash RC Mode shows Off/On, and the rows after it show their old values.
- Keep Time Lapse Movie as the last test. After one movie, run a second sequence to see that the end of sequence still completes (flag cleared).

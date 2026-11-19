# Review 2 (code): `interval-timelapse-insert-awake.json` (2026-11-13)

Adversarial review of the 47-op spec before a camera flash. Nothing was built under `build/`; the patched block 0 was made in scratch with `tools/emu/patchblock.py` (sha256 `92d5e152…fc4b7205`, 818 bytes changed in 73 runs).

- **Labels:** **V** = read in the bytes / disassembly or run by me; **I** = inferred.
- **Addresses:** E-PM2 v1.6 runtime (0x7E421020 + block-0 offset) unless the E-PL6 1.4 is named.
- **Images compared:** stock E-PM2 block 0, the patched block 0, and E-PL6 1.4 block 0 (extracted to scratch with `oetool.parse`).
- **Scratch:** `/tmp/scratch/rev2/` (`d.sh` disassembler wrapper, `norm.py` / `rdiff.py` cross-body diffs, `refs.py` reference scan, `tab.py`, `data.py`, `anc.py`).

## Verdict

- **The bytes do what the author says.** I found no wrong displacement, no wrong call frame, no stack imbalance, no missed table consumer and no missed row constant.
- **One blocker, and it is not in the code:** the spec uses the same padding as the film patches that are on the camera now (B1).
- **Three should-fix items:** a load-order dependency the E-PL6 does not have (S1), a missing E-PL6 guard for the time-lapse movie that the README dismisses with a wrong reason (S2), and a stale description (S3).

## Findings

### B1. BLOCKER: the new tables and code overlap `seven-films-5` (V)
- **What is on the camera:** `docs/camera-log.md` last row is `seven-films-6` = remap7b-code + seven-fixes-1 + seven-movie-1 + seven-structure-extra + **seven-films-5** + xp-adaptive-hue-off + seven-labels.
- **The overlap:** `patches/seven-films-5.json` writes 512 B at 0x7F033B7C and 512 B at 0x7F033D7C. This spec writes 0x7F033C00–0x7F033EF0. **692 changed bytes collide**; 746 film bytes lie inside this spec's `expect` windows.
- **Effect:**
  - Built together, `build.py` stops on an `expect` mismatch (safe, but no image).
  - Built alone on stock, the image is valid but the camera loses all seven films. The README never says so.
- **Free space left after the film set:** 0x7F033F7C–0x7F033FFF (132 B) in this padding, and **0x7ECB0B9E–0x7ECB0FFF (1,122 B)** at the end of the first Usr1 segment (0x7E8F5800–0x7ECB1000).
- **Fix:** move the table (380 B), the page-3 list (84 B), the cave (51 B), T1 (18 B) and T2 (177 B) = 710 B to 0x7ECB0B9E… and regenerate the 6 imm32, the record pointer 0x7EFFA4B0 and the three `jmp` displacements. Then build and emulate with the film specs applied. This also fixes S1.
- **If the user wants a stock-only test first:** the spec is usable as it is, but say in the README that it removes the films.

### S1. SHOULD-FIX: segment-2 code now jumps into segment 3 (V for the layout, I for the risk)
- **Layout (V, 0x7E504AF9 Usr1):** segment 2 (0x7E8F5800–0x7ECB1000) is loaded at 0x7E504C18, its constructors run, and tasks are started (AUD_EXE, PLAY_MAIN, PLAY_LOAD, PLAY_IMAGE, PLAY_SOUND) **before** segment 3 (0x7ECCB800–0x7F034000) is loaded at 0x7E504D6B.
- **The patch:** the selector 0x7E997BD9 and `startIntervalShooting` 0x7E98855F are in segment 2. Both now `jmp` to 0x7F033Exx in segment 3. On the E-PL6 this code is in line in segment 2.
- **Reachability (V for the graph):** the selector is reached only from `startIntervalShooting`, `endIntervalShooting` 0x7E982DF3, `createTimeLapseMovie` 0x7E982691 and the shoot-callback handler 0x7E995C0B (CBS_START/END_SHOOTING_PICTURE, CBS_START/END_INTERVAL_SHOOTING, CBS_END_CREATE_MOVIE). No constructor and no direct pointer reaches it. So a call before segment 3 is loaded needs a picture callback during boot (I: not possible).
- **Evidence gap:** code in the segment-2 padding has run on the camera (`remap7b-code`, 0x7ECB0888). Nothing has ever **executed** from the segment-3 padding; the films only read data there.
- **Fix:** as B1, put T1/T2 (and the cave) in the segment-2 padding.

### S2. SHOULD-FIX: the E-PL6 movie-creation guard is missing, and README §4 rows 10–11 are wrong (V code, I effect)
- **E-PL6 (V):** flag 0x602B4B20 is set to 1 in `executeCreateTimeLapseMovie` (0x7ECDA8C1) after the request is accepted, cleared in `receiveEndCreateMovie` / `receiveErrorCreateMovie` (0x7ECDA4B3, 0x7ECDA4DD), and **read in `receiveEndMediaMountForEndWait`** (0x7ECDA5CA): when it is set, the handler skips the end check.
- **README:** row 10 says the flag's "reader is E-PL6-only code"; row 11 calls it "a NULL check of a RAM pointer". Both describe this one flag. Its reader exists on the E-PM2 (0x7ECDA28D) without the test.
- **E-PM2 effect (I):** with Time Lapse Movie On, a media-mount-end event during movie creation runs 0x7ECDA7D1 again. That requests the movie a second time; the hfw guard 0x7E969ACE refuses, and the GUI then completes the interval sequence while the movie is still being written. Olympus added the flag after the E-PM2 code base, so this is likely a real fault.
- **Fix:** port the four sites (needs a spare RAM word), or keep **Time Lapse Movie Off** in the first tests and make test-plan step 5 the last step, with a card that can be lost.

### S3. SHOULD-FIX: stale text in the spec
- The `description` of the awake spec still contains "Not ported: the E-PL6 sleep/power-off timer hold (0x7E998F12 calls)" and later says it is ported. Remove the first sentence.
- No `expected_sha256`. Add it after the first good flash.

### Notes
- **N1. Value-list table size (V).** The README says the .data pointer table at RAM 0x602BE874 has 40 entries. It has 37 (rows 0–36): 0x602BE908 is another global with about 470 code references, and 0x602BE914 holds 0x7EE09135. Op 3 is still harmless, because the words it "shifts" there are 0 before and after. Row 37 has no entry, on the E-PL6 either; the formatters are only called with rows 3, 5, 6, 7, 8, 10, 11, 12, 14, 33, 34, 35 (all 25 call sites checked).
- **N2. Out-of-range rows (V).** An unused tab slot is 0xFF. Row 255 indexes base + 2,544. From the old table that is rodata; from 0x7F033C00 it is 0x7F0345F0, **outside the loaded segment**. The class bounds the cursor by the tab counts, the same as stock and E-PL6, so this is not reached. Moving the table (B1) removes the point.
- **N3. Defaults ops 0–1 differ from the E-PL6 (V).** The E-PL6 ships 0 for 483 and 485, the same as the E-PM2. The README's "frame burst with zeros" is therefore doubtful (I): the mcon record for 483 gives 1..99. The ops are in range and are data in the boot part (0x7E4C3EB8, 0x7E4C3EC8). They are harmless but not needed for parity.
- **N4. Sleep behaviour changes for every still (V).** CBS_END_SHOOTING_PICTURE calls `restore(0)` then `selector(1)`. With 482 = 0 the patched selector calls `isst(0)` then `restore(0)` again (stock: `isst(0)` only). With 482 = 1 and 489 ≠ 0 or 487 ≠ 0 it calls `hold`. Both are what the E-PL6 does.
- **N5. Not re-verified by me:** the per-mode availability of info 482, the whole SequencePartsBase range (spot check only: no differences inside the window), and overlay or checksum behaviour for segment-3 content.

## What I checked and found correct

### 1. All 47 ops (V)
| Ops | Site | Result |
|---|---|---|
| 0, 1 | MODE defaults 0x7E4C3EB4 / 0x7E4C3EC4 (8-byte records `tag, 0x0001, u32`) | value bytes only; the next records (0xDE34, 0xDE51) are untouched |
| 2 | .data tab layout, ROM 0x7E8EE88E (RAM 0x602BE3CE) | all 0x8E bytes (6 lists, 6 counts, the next table) **equal to E-PL6 0x7E8EE8B6** |
| 3 | .data value-list pointers | non-zero rows 3, 5, 6, 7, 10, 11, 12, 14, 33, 34, 35; the same pattern and the same lists as E-PL6 RAM 0x602BE89C |
| 4 | 0x7E98855F `jmp 0x7F033E20` | replaces `clr d0; mov d0,(20,sp); mov sp,a0; add 20,a0` (6 B); byte 0x7E988564 is dead; no branch targets 0x7E988560–64 |
| 5 | 0x7E997BD9 `jmp 0x7F033E40` | function entry; all 13 branches into 0x7E997BDA–0x7E997C66 are from inside the old body; no data word points into it |
| 6–17, 34–41 | 20 × `mov 33,d0` → 34 | each decoded from its function start: `mov 34,d0` then the call to 0x7EE01DDA / 0x7EE01E8C |
| 18–20, 31–33 | 6 imm32 0x7EFFE13C → 0x7F033C00 | `mov imm32,a0` / `add imm32,dN/aN`; all six decode |
| 21 | 0x7EDEC335 `jmp 0x7F033DE0` | the only branch to the block is `bne` at 0x7EDEC322 to its first byte; 0x7EDEC33A–49 is dead |
| 22–30 | switch constants | 10 one-byte immediates of `cmp` / `mov` |
| 42 | page-3 record pointer 0x7EFFA4B0 | the record is otherwise equal to the E-PL6's |
| 43–46 | padding | all `expect` bytes are 0xFF on stock |

### 2. New code (V)
- **Cave 0x7F033DE0 (51 B).**
  - `cmp 11 / beq / cmp 12 / beq / jmp 0x7EDEC34A`; each case is `mov id,d0; mov sp,a0; inc4 a0; call 0x7EE01D38,[d2,a2],12; mov row,d0; jmp 0x7EDEC432`.
  - d0 is kept on the fall-through; the code at 0x7EDEC34A starts with its own `cmp`. sp does not change.
  - Stock 0x7EDEC2C0 plus the patch equals E-PL6 0x7EDED156 instruction for instruction (normalised diff: only the inserted case, the constants, and a d2/d3 swap).
- **T1 0x7F033E20 (18 B).**
  - `call 0x7E997E94,[],4`, then the 6 displaced bytes, then `jmp 0x7E988565`. The displaced code has no PC-relative operand.
  - 0x7E997E94 ends `ret [],4`; its 14 stock callers use `[],4`.
  - Live after the hook: a2 and d3 (callee-saved), d0 and a0 (set by the displaced code). a1, d1 and d2 are loaded later.
  - The rest of `startIntervalShooting` equals E-PL6 0x7E98948E apart from this one call.
- **T2 0x7F033E40 (177 B).**
  - A 51-instruction walk against E-PL6 0x7E998C41: every mnemonic, operand and branch target index is equal.
  - Callees map getter → 0x7E6FCC91, isst → 0x7E997C67, restore → 0x7E997DC9, hold → 0x7E997E94, print → 0x7E9670E9. The only differences are the assert strings and line 721 (the stock values).
  - Frames match the callees' returns: `ret [d2],16`, `ret [d2,a2],16`, `ret [],4`. T2 ends `ret [],16`; all 9 call sites use `[],16`.
- **Helpers.** 0x7E997C67–0x7E997F17 (isst, the timer setters, both restore copies, hold) equal E-PL6 0x7E998CE5–0x7E998F95 apart from addresses. The callback handler 0x7E995B89–0x7E997BD9 has no difference.
- **Callers.** The 9 selector call sites map one to one onto the E-PL6's, with the same mode arguments.

### 3. Relocated tables (V)
- **Top table:** 37 rows + terminator at 0x7F033C00 = E-PL6 0x7EFFF864 byte for byte (380 B). Rows 1–10 and 12–37 equal stock rows 1–36.
- **Page-3 list:** 0x7F033D80 = E-PL6 0x7EFFA324 byte for byte (84 B).
- **References (any-alignment scan of stock):**
  - 0x7EFFE13C–0x7EFFE2AD: exactly the 6 loads.
  - 0x7EFF8C38–0x7EFF8C7F: only 0x7EFFA4B0.
  - 0x7F033B7C–0x7F033FFF: none.
- **The page-id lists 0x7EFFE2AE / 0x7EFFE2C2** that follow the old table are addressed absolutely and stay in place.
- **Row count:** no code holds one. The menu class 0x7EDEB923–0x7EDED0F6 equals the E-PL6's apart from addresses and the switch.
- **Usr1 copy:** 0x7E504D50 copies 0x368800 bytes to 0xBECCB800, so 0x7F033B7C–0x7F033FFF is loaded. No other loader call targets this range.

### 4. Renumbering (V)
- **Formatter calls:** 14 + 12 on the E-PM2; their row arguments after the patch equal the E-PL6's at every site (34, 35, 5, and the computed one at 0x7EDEC437).
- **Menu state code 0x7EDAA900–0x7EDB2400** (the callers of the tab / row getters): diffed against the E-PL6. It has no row-constant change. Its `11 → 13` and `12 → 14` are GUI state ids (the E-PL6 has two more states).
- **Cursor:** RAM 0x602BE48C (tab) and 0x602BE490 (row within the tab). It is not a global row number, and it is bounded by the tab counts.

### 5. Saved settings (V code, I behaviour)
- With 482 = 0 the only new run-time effect is N4.
- No saved value indexes the new tables.
- Power-up, mode change, dead clock and card paths use GUI code that equals the E-PL6's except README rows 8–11 (confirmed by my own diff of 0x7ECD9EBC–0x7ECDA82E). Of those, only S2 matters.

### 6. Failure containment (V layout, I effect)
- **Boot part:** only ops 0–3 (two default bytes and .data bytes that only the menu class reads). No code on the boot path or the updater path changes.
- **Everything else** is in the two Usr1 segments. A fault there needs the menu, a shot or an interval call.
- **Recovery** (hold OK at power-on) does not use these segments (I). It was proven on this body with modified firmware (camera log, 2026-11-08).

# Review 1: memory assumptions of `interval-timelapse-insert-awake.json` (2026-11-13)

Scope: only the memory assumptions (load, references, execution, `.data`, flash layout, second core). Code logic of the caves and the menu wiring is not reviewed here.

- **Labels:** **V** = read in the bytes of stock block 0 or of a scratch-built patched block 0. **I** = inferred.
- **Method:** patched image built with `tools/emu/patchblock.py` into the scratch folder only. Nothing was written under `build/`. No flash, no commit.
- **Result:** no blocker found. Three residual risks are listed in §7. None of them is a brick risk by itself.

## 0. Facts used by all points (V)

| Fact | Evidence |
|---|---|
| Patch changes 818 bytes in 73 runs. Every changed byte is inside a range that the boot code loads | Diff stock/patched against the load list below: 0 bytes outside. 755 in segment 3, 51 in `.data` image, 10 in segment 2, 2 in the kernel range |
| Block 0 is linear in flash: flash = 0x402C0020 + file offset (cached alias) | Container header: addr 0x402C0000 + 0x20 header. Four independent loads agree: 0x4039D000→0x7E4FE000, 0x40779000→0x7E8DA000, 0x80B6A800→0x7ECCB800, 0x80EFB000→0x7F05C000 all give the same offset |
| 0x8…/0xA…/0xB… addresses are the uncached alias of 0x4…/0x6…/0x7… | Helper 0x7E45DAEF: `(addr & 0x3FFFFFFF) | 0x40000000` for 0x80000000–0x80FFFFFF and 0xA0000000–0xBFFFFFFF; inverse at 0x7E45DB35 |
| Load list | Reset stub 0x7E421216: 0x7E430000–0x7E4C9800. Reset stub 0x7E42123B: `.data` image 0x7E8DA000–0x7E8F3114. Boot task: 0x7E4FE000–0x7E881000. Usr1: 0x7E8F5800–0x7ECB1000 and 0x7ECCB800–0x7F034000 |

Note: the review brief gives the flash source as 0x80D6A800. The bytes say **0x80B6A800** (0x7E504D58). The spec text is correct; the brief has a typo.

## 1. Is 0x7F033C00–0x7F033EF0 in RAM at that address before any code uses it? — SAFE

- **The copy (V).** Usr1 0x7E504D50–0x7E504D6B: `a0 = 0xBECCB800`, `a1 = 0x80B6A800`, `d0 = 0x7F034000 + 0x81334800 = 0x368800`, `d1 = 0x103`, `call 0x7E451306`. Destination end = 0xBF034000 = cached 0x7F034000. The patched range ends at 0x7F033EF0, so it is 0x110 bytes inside the copy.
- **Unconditional (V).** Usr1 0x7E504AF9–0x7E504D6B has no branch instruction at all. Every call up to the segment-3 copy is straight-line.
- **Only one copy site (V).** The constants 0xBECCB800, 0x80B6A800, 0x81334800 and 0x7F034000 each occur once in block 0, all at this site. No second loader re-copies or partially reloads segment 3.
- **Same fate as the GUI code (V + I).** The padding is in the same single read request as the GUI code 0x7ECCB800–0x7EECE318 and its rodata. In every boot mode in which the GUI code is valid, the padding is valid. If a mode skips Usr1, no segment-2 or segment-3 code is in RAM, so no patched code path exists either: the patch changes no byte in segment 1 (USRSTART, firmup, core) (V).
- **Overlays do not touch it (V).** Usr2 loads A to 0xBF05C000 (size 0xF000) and B to 0x7F080000 (size 0x6B800). The third Usr1 load goes to 0x7F100000. All start at or above 0x7F05C000.
- **No pointer into the gap after it (V for the scan, I for the conclusion).** A scan of every 4-byte value at every byte offset finds no real reference to 0x7F034001–0x7F05BFFF or to 0xBF030000–0xBF05BFFF. All hits are an opcode byte followed by another immediate (for example `fc dc 58 03 7f 7e` = `mov 0x7E7F0358,a0`). The one aligned hit, 0x7E438E64 = 0x7F05C000, is a task entry in the CPU0 task table.
- **Checksums (V).** Block 0 has no string for a ROM sum or ROM check. The only checksum code found is: the update container sum (recomputed by the build), the firmup file checks, the MODE bank sum 0x7E451187 (sums the saved bank only, see §4), and HDMI EDID. `[GUI-SelfAdjust] FlashlCheck Error` (0x7EDDCFE9) tests a status flag, not flash contents. The blank test 0x7E4511AC has 4 callers, all in the bank code 0x7E45045A–0x7E450876.
- **Empirical (V, docs/camera-log.md).** `three-films-1` (2026-11-12) put 120 bytes of new code into the 0xFF padding of segment 1 (0x7E880F5C) and booted. So no boot or update check requires padding to stay 0xFF. That test was on segment 1, not on segment 3.
- **Not proven (I):** that nothing writes the range through a computed address (heap, memory test). No constant supports such a write.

## 2. Is the padding really unreferenced? — SAFE

- **Extent (V).** Stock bytes 0x7F033B7C–0x7F033FFF are all 0xFF (0x484 bytes). The patch uses 0x7F033C00–0x7F033EF0 and leaves 0x7F033B7C–0x7F033BFF and 0x7F033EF1–0x7F033FFF as 0xFF.
- **Pointer scan (V).** No 4-byte value in 0x7F033B00–0x7F034100 at any byte offset in stock block 0, except the copy-end constant 0x7F034000 at 0x7E504D5E. Same for the uncached alias 0xBF033B00–0xBF034100 and for the flash addresses 0x80ED2B00–0x80ED3100 and 0x40ED2B00–0x40ED3100 (3 hits, all misaligned opcode + immediate, for example 0x7E9967C8 = `fc cc 3c 03 bf 7e` = `mov 0x7EBF033C,d0`).
- **Constructor walker (V).** 0x7E44B6EA: `mov 180,d2`; `mov 0x7F033AC8,a2`; loop `mov (a2),a0; calls (a0); inc4 a2; add -4,d2; bgt`. It reads exactly 45 words, 0x7F033AC8–0x7F033B7B. It has no terminator test. The last word is 0x7EEC05FF at 0x7F033B78. The count is a constant, so the walker cannot run into the padding.
- **0xFF as a marker (V + I).** The only code that treats 0xFFFF as "blank" is the bank blank test (§1). Nothing found scans code or rodata for 0xFF.
- **Limit of the method (I).** A scan cannot see an address made from a table base plus a run-time index. The last rodata before the constructor table (0x7F033A80–0x7F033AC7) is small-integer data, not a pointer table.

## 3. Can code execute from the range? — SAFE (I, strong)

- **No MMU or protection setup found (V for the scan).** The reset stub 0x7E421020–0x7E430000 writes only 0x8000–0x801C (vectors), 0x8050 (CPU id, read) and 0x8070. The kernel range 0x7E430000–0x7E470000 adds only 0x8040. No string names an MMU, TLB or protection fault.
- **0x8070 is a cache control register (V for the code, I for the meaning).** 0x7E4210FA sets bits 0 and 1 at reset. 0x7E45DA3D / 0x7E45DA9D clear an enable bit, wait on a busy bit, set bit 4 or 5 and enable again. These are global operations. No address-range register exists in this code.
- **Other code already runs from the same load (V).** The CPU0 task 0x69 has its entry at 0x7ECCFEE9. Fourteen CPU1 tasks have entries in segment 3 (0x7EE8FBB1 and others). Overlay code runs above it at 0x7F05C000+. So addresses below and above the padding execute.
- **Instruction cache (I).** The loader writes through the uncached alias and the code runs through the cached alias. This is correct only if no cache line of the range was filled before the load. That holds for the padding as it does for the GUI code: nothing reads or runs it before Usr1 finishes the copy (§2: no reference in stock; the patched references are all inside segment 2/3 code or `.data` consumers that run after the load, but see §7.1).

## 4. The `.data` edits and the settings defaults — SAFE, with one bound to respect

**`.data` image (V).**
- Edited offsets 0x4CD887–0x4CD8E7 and 0x4CDD44–0x4CDDA3 = ROM 0x7E8EE8A7–0x7E8EEDC3, inside the image 0x7E8DA000–0x7E8F3113.
- Reset stub 0x7E4212B8–0x7E4212E0 copies {src 0x7E8DA000, dst 0x602A9B40, size 0x7E8F3114 − 0x7E8DA000} with 0x7E425FA8 / 0x7E426045. That function is a DMA copy with a data-cache flush (0x7E45DA9D). It has no checksum.
- RAM targets: tab table 0x602BE3CE (7 code references), tab counts 0x602BE446 (15 references), value-list pointers 0x602BE874 (2 references: 0x7EE01DE4, 0x7EE01E94). No code or data word points at the ROM copies 0x7E8EE880–0x7E8EEE00. So the RAM copy is what the code reads.
- Tab table shape: 6 records of 20 bytes (12 row bytes + 8 zero bytes). Tab 1 becomes `07 08 09 0a 0b 0c ff…` (6 of 12 slots). Counts become 6, 6, 6, 10, 3, 6 = 37. No record overflows.

**Bound of the value-list pointer array (V).**
- The array is 0x602BE874 + 4 × row. Stock uses 0x602BE874–0x602BE907 (indices 0–36).
- **0x602BE908 is a different variable**: a live object pointer with 92 direct code references (read with `mov (0x602BE908),a0`, written at 0x7EE028E6 and 0x7EE02A66). 0x602BE910 has 379 references.
- The patched array has its last non-zero entry at index 35 (0x602BE900). The patched value switch calls 0x7EE01DDA only with the constants 3, 5, 6, 7, 8, 10, 11, 12, 14, 33, 34, 35. So the patch stays inside the array.
- **Consequence:** the new row 37 has no slot. Index 37 would read the live pointer at 0x602BE908. This is safe only while no caller passes a row number above 36 to 0x7EE01DDA / 0x7EE01E8C. The spec text says "rows 11-38 shifted to 12-39"; the bytes show indices 11–35 shifted to 12–36 in effect. The text is wrong, the bytes are in bounds.

**Settings defaults (V for bytes, I for the effect).**
- 0xA2E98 and 0xA2EA8 = 0x7E4C3EB8 and 0x7E4C3EC8, inside the reset-stub load 0x7E430000–0x7E4C9800.
- Records are `{u16 tag, u16 count, data}`: `21 de 01 00 | 00→0a 00 00 00` and `44 de 01 00 | 00→05 00 00 00`. Tag and count are unchanged, so the MODE RAM layout is unchanged.
- No code or data word points into 0x7E4C3E00–0x7E4C3F00. The list is walked from its head (0x7E4B40C8, registered by 0x7E4573AB).
- Saved bank: 0x7E450C4B reads the whole bank from flash into the MODE RAM area (descriptor 0x600011DC: size, RAM, flash) and sums that buffer with 0x7E451187 (16-bit add over the saved bytes). The ROM defaults are not an input of the sum. So the edit cannot make a saved bank fail its check.
- Effect (I): a valid saved bank overwrites the whole MODE area, so the new defaults appear only after a MODE reset or when both bank copies are bad. The camera in hand keeps 483 = 0 and 485 = 0 until then. The README says the same.

## 5. Flash layout — SAFE

- Patched padding = file offsets 0xC12C00–0xC12ED0 = flash 0x40ED2C20–0x40ED2EF0, inside block 0 (0x402C0020–0x4103FFE0) (V).
- It is inside the flash source of the segment-3 read, 0x80B6A800–0x80ED3000 (V). It is not in the gap 0x7F034000–0x7F05C000 that no loader reads.
- The container checksum is an additive sum over header + decoded payload + trailer. Payload length is unchanged. The build recomputes the sum (V, `tools/oetool.py`).
- Sixteen earlier modified builds were flashed with changed block-0 bytes, one with new code in 0xFF padding (V, camera log). The updater does not need padding to be 0xFF.
- Run-time flash writes (I): the erase unit seen in the bank code is 0x20000. The 0x20000 block that holds the padding holds only GUI rodata, so no run-time writer shares it.

## 6. Second CPU core — SAFE

- CPU1 runs 14 tasks whose entry points are in segment 3, which CPU0 loads at run time (V, task table at file offset 0x1C490). So CPU1 sees the same RAM at the same addresses and can execute from this load.
- The GUI task (0x69, entry 0x7ECCFEE9) is in the CPU0 table (V). The hooked functions are in `OlyHfwOpeShoot` / `OlyHfwPower` (application layer). No CPU1 task entry is application or GUI code (V for the entries, I for "never calls").
- Even if CPU1 ran a cave, the memory is the same.

## 7. Residual risks and what settles them

1. **Boot window between the segment-2 and segment-3 copies — RISK, low (I).**
   - Stock `OlyHfwPower` 0x7E997BD9 calls only segment-1 and segment-2 code. The patch makes its first instruction `jmp 0x7F033E40` (segment 3). `startIntervalShooting` 0x7E98855F gets `jmp 0x7F033E20`.
   - Usr1 loads segment 2 at 0x7E504C18 and segment 3 at 0x7E504D6B. Between them it runs the segment-2 constructors, `play_init` 0x7E93BA6C and starts AUD_EXE, PLAY_MAIN, PLAY_LOAD, PLAY_IMAGE, PLAY_SOUND, TSK_TOUCH and DBG_MESS1.
   - If anything called 0x7E997BD9 in that window, stock would work and the patched build would jump into unloaded RAM.
   - Against it: the only route to 0x7E997BD9 outside the interval functions is the callback dispatcher 0x7E995C0B, reached through the vtable word 0x7EBF06B8. The application start 0x7E966A17 is called after the segment-3 constructors (0x7E504D88).
   - **Settles it:** find the code that registers the object with vtable 0x7EBF06B8 as a callback and show that it runs after 0x7E504D6B; or log in the emulator that 0x7E997BD9 is not entered before the third load.
2. **Value-list array has no slot for row 37 — RISK, low (V for the layout).** See §4. **Settles it:** list every caller of 0x7EE01DDA and 0x7EE01E8C (13 + 12 call sites) in the patched image and confirm each passes a constant ≤ 36. The 4 sites in the value switch are confirmed here; the other 21 were not read one by one.
3. **Writes through computed addresses — UNKNOWN, low (I).** No constant in block 0 can produce an address in 0x7F033B7C–0x7F05BFFF, but a scan cannot exclude a pointer built at run time. **Settles it:** after a boot of the patched build, dump 0x7F033C00–0x7F033EF0 with the `fmem`/memory-dump shell and compare with the file; or the same in the emulator after Usr1.

## 8. Verdict table

| # | Question | Verdict | Level |
|---|---|---|---|
| 1 | Loaded at that address, unconditional, not overwritten, no checksum | SAFE | V (copy, single site, no branch); I (no later write) |
| 2 | Padding unreferenced; constructor walker bounded | SAFE | V |
| 3 | Executable; cache | SAFE | I (strong); V for "other code runs from the same load" |
| 4 | `.data` edits in the copied image, RAM copy is read; defaults table read; no checksum dependency | SAFE; bound noted (§4, §7.2) | V; I for when defaults apply |
| 5 | Flash layout, updater | SAFE | V |
| 6 | Second core | SAFE | V (task tables); I (GUI never on CPU1) |

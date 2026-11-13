# Trace: where to put the 128-byte value list of info 483 (2026-11-13)

Question: the new value list of setting info 483 (prm 0xDE21, frame count; mcon record 0x7E84C5FC) needs 128 bytes. Three homes were proposed. This note completes the traces and gives one recommendation.

- **A:** kernel-area 0xFF padding, 0x7E4C9100–0x7E4C917F (the current `patches/interval-frames-240.json`).
- **B:** the reclaimed `sdk` name text in segment 2, for example 0x7EBF1F00–0x7EBF1F7F (directly after the 128 editor rows).
- **C:** an unreferenced debug string in segment 1. Concrete choice made here: **0x7E81372A–0x7E8137A9**.

Labels: **V** = read in the bytes / disassembly of stock block 0 or of a scratch-built image, or run in the emulator. **I** = inferred.
Method: read-only. Scratch images built with `tools/emu/patchblock.py` into `/tmp/scratch/trace483/` (films + v2 = sha256 `8992f2c2…`, films + v2 + frames = `7d460c4c…`). Scratch scripts (not kept): call-graph closure over `build/map/calls.tsv`, a window scan (every 4-byte window at every byte offset, for the runtime address, the uncached alias +0x40000000 and both flash aliases 0x402C0020 / 0x802C0020 + offset), and an om-emu run with read watchpoints.

**Result: keep A. No new spec was generated.** B is safe for the editor rows (Trace 3) but is the weakest home for the list. C is a sound fallback.

## 1. Trace 1: every reader of the list, and when it can run

### 1.1 The readers (V)

- **One door.** The record table 0x7E84A0B8 (505 × 20 B) has one reference in block 0: the hash builder 0x7E7077D3 (bound `cmp 505`). The hash (RAM 0x605B9750 / 0x605B9950) is read only by 0x7E70782A (first record of an id) and 0x7E707854 (id + variant key), through 0x7E70760A (12 callers) and 0x7E707613 (10 callers). All 22 callers are in the value-list engine 0x7E706FA3–0x7E70787F.
- **Functions that read list bytes (record +4):**

| Function | What it does with the list | Bound read from the code |
|---|---|---|
| 0x7E706FA3 / 0x7E706FDE (by id), 0x7E707018 / 0x7E707053 (id + key) → 0x7E70761C → 0x7E7074B5 (u8), 0x7E7074FD (s8), 0x7E707449 / 0x7E7073FD (s16), 0x7E707547 (u16), 0x7E707591 (type 6) | step to previous / next | scans index 0 … count − 2, reads one entry ≤ count − 1; count = total / element size |
| 0x7E70708D, 0x7E7070FD, 0x7E707115, 0x7E707369 → 0x7E7071D5 → 0x7E707147 | value → index (every `get`) | index < count |
| 0x7E7076C5 / 0x7E7076DE → 0x7E7076F7 → 0x7E707147 | membership test | index < count |
| 0x7E70726D / 0x7E7072EA (copy one item), 0x7E7072A4 / 0x7E707322 (item by index) | item by index | `cmp index, count; ble` (index = count is accepted: one element past the end, as in stock) |
| 0x7E7070B4, 0x7E707397 (GUI → raw) | read the list only when record +8 ≠ 0 | 483 has +8 = 0: **not read** |
| 0x7E707239 / 0x7E707253 (count), 0x7E7073E3 (kind), 0x7E70777F (sign rule) | record fields only | — |

- All 505 stock lists lie in 0x7E83FC40–0x7E84A0B6, segment 1.
- For 483 the `get` path (0x7E6FCC91 → 0x7E6FEA5F → 0x7E70708D) scans the list and then discards the index (record +8 = 0). So a `get` returns the raw prm byte **whatever the list holds**. Only step, item-by-index and membership results depend on the list bytes.

### 1.2 Who can pass id 483 (V unless marked)

304 mcon functions can reach a list reader. Data pointers to mcon code from outside its own tables: only the `mcon` shell command 0x7E6FE1FE (3 command-table copies). So every other entry is a direct call, and `calls.tsv` lists them: 426 call sites in segment 2, **18 in segment 1**, 0 in the kernel range and 0 in segment 3 (segment 3 goes through segment-2 wrappers such as `getSetting` 0x7ECD3975).

| Chain | Where the code is | Id source | Can pass 483? | Earliest run |
|---|---|---|---|---|
| mcon init 0x7E6FE251 (hash build, language 1009, mode 26 / 24, all 92 conflict rules) | segment 1, called once from Usr0 at 0x7E504669 | constants and mcon tables | **No** | boot task, before USTART1 exists |
| USR_FAST_APP 0x7E502926 / 0x7E502A08 / 0x7E502DD6 / 0x7E5037DF / 0x7E50384E (get / set / camera_set / 7 conflict checks) | segment 1, task started in Usr0 at 0x7E504609 | constants 25, 291, 700, 1034, 4014, 618, 617, 544, 104, 2074, 227, 231 | **No** | before or during Usr1's copy |
| Mode load / camera_start / camera_set / camera_end, bank save / restore, presets, hook batches, dependency propagation, mymode / custom | mcon, segment 1 | mcon tables | **No:** in the mcon data 0x7E813F00–0x7E84EE70 the u16 483 occurs 3 times: the record itself and the two reset lists | any time |
| standard_reset / full_reset lists 0x7E84DF32 (300 ids) and 0x7E84D850 (881 ids), both hold 483; first-boot defaults 0x7E706905 (ids 0–700) | mcon, segment 1 | list / loop | passes 483 to 0x7E706AC3 / 0x7E706F04, which write the ROM default raw (0x7E67FD74, 0x7E67FEDA, 0x7E67FC26). **No list read** | reset: menu action; 0x7E706905: in mcon init when 0x7E6802C9 returns non-zero (I: saved bank invalid) |
| `api_rec_Calculate_RecRemain_Ext` 0x7E68B5AA, `…MediaRemain_Ext` 0x7E68B79A: `get(483)` at 0x7E68B69F / 0x7E68B88F, only when info 482 = 1 | segment 1 | constant 483 | **Yes** | callers are only 0x7E983B39 (`OlyHfwOpeShoot::getAvailableShootCount`), 0x7E9E9997, 0x7EB92C8C: all **segment 2**, no data pointer to either function |
| `api_info_Search_Mode_Conflict` 0x7E6803E4 | segment 1 | caller's id | yes | only caller 0x7E96EAAE, segment 2 |
| `mcon` shell: `modeinfo`, `enumlist`, … (0x7E6FD519: loops over ids 0–700, 1000+, 2000+, 3000+, 4000+, 15000+) | segment 1, U_SHELL task (started in Usr0) | loop | **Yes** | only when a command line arrives on the debug UART |
| HFW settings adaptor 0x7E9E7xxx (get 0x7E9E76BE, set 0x7E9E7D6C, step 0x7E9E7DC4 / 0x7E9E7DEF, list 0x7E9E7601 / 0x7E9E7716), camera-info class 0x7EB8C575 / 0x7EB8C5CC, `getLiveGuideLevel` 0x7E984EEE: the GUI data model, Myset and reset screens go through these | segment 2 | caller's id | yes | after the segment-2 copy |
| End tests and remaining count: 0x7EA89F39, 0x7EA8C4AE (CmpSqp), 0x7E9841A5; 0x7ECDA5C8 through 0x7ECD3975 | segments 2 and 3 | constant 483 | yes | after the segment-2 / segment-3 copy |
| Other `mov 483` sites: 0x7E512B33 is a source line number for the `mec_ev.c` error print; 0x7E5E9D53 stores 483 in a focus-movie parameter block next to 1024, 1792, 993 (I: not an info id) | segment 1 | — | no | — |
| Saved-bank validation at boot (bank code 0x7E45045A–0x7E450876, checksum 0x7E451187), prm default load 0x7E67FF81 / 0x7E6801C8 | kernel range / info module | — | never enters mcon (no call edge into the engine) | boot |

### 1.3 Boot order against the copies (V)

1. Reset stub 0x7E421216: flash 0x402CF000 → 0xBE430000, size 0x99800 (**A**). Then `.data`.
2. Boot task 0x7E44A043: flash 0x4039D000 → 0xBE4FE000, size 0x383000 (**C** and all stock lists). Then Usr0.
3. Usr0 0x7E503DD4, in the boot task: starts USR_FAST (0x7E504609), lowers its own priority to 11 (0x7E50463B), runs **mcon init at 0x7E504669**, and starts USTART1 only at 0x7E504AC1. On the firmup-reboot path (`cmp 1,d2` at 0x7E504A59) it starts FIRMUP_CLI instead: **Usr1 never runs, segments 2 and 3 are never loaded**. The id variable of USTART1 (0x7E43EA1C) has this one code reference.
4. Usr1 0x7E504AF9–0x7E504D80 has no branch instruction. Segment-2 copy at 0x7E504C18 (**B**), the first call into segment 2 at 0x7E504C91, segment-3 copy at 0x7E504D6B.

**So mcon init and USR_FAST read value lists before segment 2 is loaded, but never the list of 483.** The earliest read of 483's list in any boot is from segment-2 code (the shot-count call when interval shooting is On, a GUI `get`, or an interval sequence), with the kernel range, segment 1 and segment 2 in RAM. The one exception is an `mcon` debug command typed in the boot window.

- **Wake from sleep:** no segment-1 or kernel caller other than the 18 sites above reaches a list reader, so the resume code cannot read the list either way. Whether RAM is kept or the reset stub runs again does not matter for A or C.
- **SD update:** the reboot takes the FIRMUP_CLI branch. mcon init still runs; nothing passes 483.

### 1.4 Emulator (V; function level, stubs answer for everything outside mcon)

Entry points ran natively in om-emu with read watchpoints on the list of 483, on its record, and on the list of info 26 as a positive control. The 88 external callees and 8 alternate accessor entries were stubs; memcpy / memcmp / string helpers ran natively. The four prm getters returned 0 (seed 0) or pseudo-random small values (seeds 1, 2). With seed 0 every case returned and no code ran outside mcon and the helpers.

| Case | Reads in the list of 483 | Control |
|---|---|---|
| mcon init 0x7E6FE251 | **0** | record of 483 read once (hash build); list of 26 read |
| conflict engine over all rules 0x7E70083F (both planes), mode load 0x7E700993, camera_start / set / end, standard and full reset, mymode load / clear, custom load / save, region defaults, bank save / restore, preset apply, hook batches | **0** in every case | list of 26 read in mode load, camera_start, camera_set |
| `get(483)` 0x7E6FEA5F | 99 (stock), 128 (patched) | positive control for the watch |
| step-next(483) 0x7E6FE8B2 | 297 (stock), 384 (patched) | positive control |

- **Seeds 1 and 2 (stock):** 0 reads in the list of 483 in all 38 runs. 19 of them stopped at the 6,000,000-instruction limit, because the stub getters ignore writes and the conflict loop then does not settle; these runs are partial.
- **Films + v2 + frames image, seed 0:** the same table with the watch on 0x7E4C9100: 0 reads in every case, 128 for `get(483)`.

## 2. Trace 2: each location by the bounded-reader method

### 2.1 A: 0x7E4C9100–0x7E4C917F (V)

- **Bytes:** 0xFF from 0x7E4C90CA to 0x7E4FDFFF in stock and in films + v2.
- **Before:** the fatal-error handler 0x7E4C8E52 (one caller, 0x7E4519C5). It is code and ends in `bra 0x7E4C90C8` (branch to itself). Before it: an empty stub 0x7E4C8E40 (`retf`), a one-word reader 0x7E4C8E49, and the last referenced data, the string `<WDT COMMAND>…` at 0x7E4C8DFA (NUL-terminated, ends at 0x7E4C8E3F; consumers are prints). No data pointer targets 0x7E4C8E40–0x7E4C9800, so nothing can copy or scan forward from there.
- **After:** nothing inside the copy. 0x7E4C9800–0x7E4FDFFF is not loaded.
- **Windows into 0x7E4C9000–0x7E4C9800, all four aliases:** the copy-end operand at 0x7E421203, and one non-operand byte pattern (0x7E6A2CAB). The stored copy end (RAM 0x604DA480) has no reader.
- **Run-time use of that RAM:** the reset code zero-fills only 0x6032CAEC–0x6041A468, 0x60729040–0x607547A4, 0x607547B0–0x60772820 and (one path) 0x60314700–0x6032CAEC (0x7E4213F7, DMA fill). Kernel heaps are 0x6041A470 + 0x80000 (CPU0) and 0x6049A470 + 0x40000 (CPU1). All 22 static task stacks are in 0x604DEB80–0x604E8B40 or SRAM 0x47000800. The "FLSH" calls at 0x7E42137E / 0x7E42138D reach the empty stub. No self-test of this range was found.

### 2.2 B: 0x7EBF1F00–0x7EBF1F7F (V)

- **Overwritten text:** `sdk` method names (`…Frame`, `M20`, `getZoomFrame`, `M21`, `moveZoomFrame`, …).
- **Before:** the 30-entry `sdk` sub-command table 0x7EBF0FA0 (ends 0x7EBF108F). Two readers, both `cmp 30`: lookup 0x7E99BAE5 and help 0x7E99CF3A.
- **After:** the format string `%1s, %d\n` at 0x7EBF3BAD (0x7E99A6DC); readers go forward.
- **Windows into 0x7EBF1090–0x7EBF3BAC:** 4 hits on 0x7EBF22C0, low words of doubles in an overlay table.
- **Which command could print it:** none found. `sdk` and `sdk help` read only the table (emulator, reclaim-space §6: 0 reads in the block).
- **Load:** Usr1 only. Not in RAM on the firmup path and before 0x7E504C18.

### 2.3 C: 0x7E81372A–0x7E8137A9 (V)

- **Overwritten text:** exactly five strings with their NULs: `app_mode_get_zoom_permit`, `app_mode_i_auto_set_scene`, `app_mode_lv_guide_set`, `app_mode_lv_guide_end`, `app_mode_state_set_sleep_on_flag`. They belong to a pool of 105 function-name strings, 0x7E813170–0x7E813ECF (`app_mode_*`, `mcon_if_*: camerainfo locking`), directly before the mcon strings.
- **Before the pool:** the task label `FaceQWC1` at 0x7E813166 (0x7E6FC957, error-label print 0x7E44AD02, NUL-terminated; a second NUL at 0x7E81316F).
- **After the pool:** the jump table 0x7E813ED0, 9 words, reader 0x7E6FCFD2 with `cmp 8; bhi` on info 41.
- **Windows into the pool:** none that is an operand or an aligned data word (3 unaligned byte patterns inside instructions, flash-alias values).
- **Which command could print it:** none found; a print needs a pointer and there is none (I for "no walker").
- **Load:** boot task, with every stock list. No spec in the repository touches the pool.

## 3. Trace 3: the 128 editor rows at 0x7EBF1100 (V)

- The rows are reached only through descriptor 0x7F00C6EC (+12). The descriptor is reached only through the list table 0x7F00D710 (entry `{638, 0x7F00C6EC}` at 0x7F00DD88), whose one reference is the lookup 0x7EDFD9AF (`cmp 312`), **segment-3 code**.
- Callers of the lookup: 18, all in 0x7EDC85E7–0x7EE01C2D. Earliest reader: the panel-638 factory 0x7EE01678 → 0x7EE01699 → 0x7EDC81A8 (`udfu01 28` on the row index), when the Frame editor opens. Segment 3 is loaded after segment 2 in the branch-free Usr1.
- **The rows cannot be read before segment 2 is loaded.** B is the right home for them.

## 4. The other 0xFF gaps in the reset-loaded range (coordinator question)

| Gap | Size | Neighbours (V) | References, all four aliases (V) | Verdict |
|---|---|---|---|---|
| G1 0x7E43F2B0–0x7E43FFFF | 3,408 | before: CPU1 kernel configuration. Its last pointed-to object is the 15-pair limit array 0x7E43F264–0x7E43F29F (reader 0x7E4337A5, `cmp 15`), then 12 unreferenced bytes 0x7E43F2A0. After: 16 zero bytes at 0x7E440000 | no operand, no aligned data word | **free by the scan; I for the 12-byte tail and for base + offset use** |
| G2 0x7E440010–0x7E447FFF | 32,752 | before: the 16 zero bytes (purpose unknown). After: the CPU1 vector page 0x7E448000 | none; no reference to 0x7E440000 or 0x7E448000 themselves | **unknown** |
| G3 0x7E44806A–0x7E448FFF | 3,990 | same 4 KiB page as the CPU1 vectors: reset jump at +8, seven `jmp` stubs at +0x20 … +0x50, a PSW helper up to 0x7E448069 | the 7 vector operands 0x7E448020 … 0x7E448050 at 0x7E426812–0x7E426848 | **unknown: free by the scan, but any CPU-defined entry offset in this page would execute it** |

- **Not written after the copy (V):** the zero-fill ranges, heaps and stacks of §2.1 are all in 0x60…… or SRAM. The per-CPU pointer at 0x8FF00004 + 4 × cpu holds the configuration root (0x7E43EEF8, 0x7E43F084; 0x7E4329AB, 0x7E433893), not a writable block.
- **CPU1 start-up (V):** entry 0x7E4267C9 is written to 0x98D00140 by the reset stub. It sets sp = 0x47001FFC, loads the seven vector words and the base from 0x7E448020 … 0x7E448050, and jumps on. It copies nothing into 0x7E44xxxx; the CPU1 vector page arrives with the reset-stub copy. The CPU0 page 0x7E430000 has the same layout and is followed by kernel code at 0x7E430058, so no entry above +0x58 is in use there (I for CPU1 by symmetry).
- **Better than A? No.** They share A's loader and A's evidence class at best (G1). A has the stronger "before" (code that ends in an endless loop, against a kernel table), nothing after it, and its neighbourhood was already reviewed. Nothing was moved.

## 5. Decision table

| | A 0x7E4C9100 | B 0x7EBF1F00 | C 0x7E81372A |
|---|---|---|---|
| In RAM before any reader of 483's list | **V**, in every boot path (first copy, unconditional) | V on a normal boot; **not loaded** on the firmup path | **V**, same copy as all 505 stock lists |
| No reader of 483 before the load | not needed | V for call graph, tables and emulator; **I** that segment-2 code never runs early, that no stale data-cache line survives the uncached-alias load, and for the `mcon` shell | not needed (loaded before mcon init) |
| Bytes unused | **V** 0xFF, stock and films + v2 | V unreferenced text | V unreferenced text |
| No reader runs into it | **V** code + endless loop before, nothing after | V two `cmp 30` readers, emulator 0 reads | V label string before, 9-entry jump table after; I no string walker |
| RAM not reused at run time | V (zero-fill, heap, stack ranges); I for a computed address | as every segment-2 table | as every segment-1 table |
| Camera evidence for the area | v2 changed 0x7E4C3EB8 / 0x7E4C3EC8 in the same copy and boots (V); padding in this copy not yet tested (I) | films + v2 patches run from segment-2 padding (V) | segment-1 padding and rodata edits are camera-tested (V) |
| Cost | none | `sdk` name text | five debug names |
| If the assumption is wrong | list bytes wrong: `get` and the end test unchanged (raw prm); step / editor order for 483 wrong; no boot effect | the same, and a read before the load sees unloaded RAM | the same, or a garbled debug print |

**Recommendation: A, as in `patches/interval-frames-240.json`.**
- A is the only home that is valid before mcon init, in every boot path, without overwriting anything, and whose "nothing reads into it" rests on code, not on a string-pool rule.
- **B is not recommended for the list.** The traces show no early reader, so it would work, but it adds the only load-order assumption (I) of the three and gains nothing.
- **C is the fallback** if a camera test ever shows a problem with padding in the kernel copy: move only the list (128 B) and the record pointer.
- The current spec applies on stock (block-0 sha256 `b9b5e4f6…`) and on films + v2 (`7d460c4c…`), and its ranges are disjoint from the 1,593 block-0 ops of the other 61 spec files (`patches/`, `patches/history/`, `experiments/*/patches/`, `tools/emu/specs/`).

## 6. Limits

- Static call graph from `build/map/calls.tsv`; indirect calls are covered by the pointer scan, not by execution. A pointer built at run time is invisible to both.
- The emulator ran single functions with stubbed prm values; it does not prove task order. Task order comes from the Usr0 / Usr1 disassembly.
- Not traced: what the 16 bytes at 0x7E440000 are; the CPU's exception entry offsets; whether RAM is kept across sleep.
- The mcon globals (0x605Axxxx–0x605Bxxxx) are outside the reset zero-fill. Whether mcon init clears its 20-entry change log was not read. It matters only for B.

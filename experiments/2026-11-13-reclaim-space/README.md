# Reclaimable space in E-PM2 v1.6 block 0 (2026-11-13)

Question: where can new patch code or tables go, now that the two padding areas are nearly full
(segment 2 0x7ECB0888–0x7ECB1000, segment 3 0x7F033B7C–0x7F034000)? Read-only study of stock block 0
(`build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin`, runtime = 0x7E421020 + offset). Nothing was built or flashed.

Labels: **V** = read in the bytes, the disassembly or an emulator run; **I** = inferred.

## 1. Short answer

- **Strictly dead code is rare: 9.0 KB in all three segments** (V). Almost every function is referenced by
  live code or by a table. 7.3 KB of it is one unreferenced cluster of 3D-engine float helpers in segment 3.
- **Unreferenced debug strings are the large class-A pool: about 51 KB** (V for "no pointer at any byte
  alignment"; the rule is in §2). The best single area is the `sdk` help/name list in segment 2:
  **0x7EBF1090–0x7EBF3BAD, 11,037 B contiguous**.
- **AVCHD is not dead.** Most "AVCHD" code is the shared H.264 engine that MOV uses. See §5.
- **Debug-shell code is 107 KB but is class B** (reachable from UART and from USB ADJ op 0x902B).
- A 108 KB option exists outside the dead-space question: the 0xFF gap between the segment-2 and segment-3
  loads (§7, class C, needs a one-immediate loader change).

## 2. What "provably dead" means here

A byte is class A only if all of these hold:

1. **No direct transfer** reaches it: no `call`/`calls`/`jmp`/`Bcc` target printed by objdump in any live
   instruction, and it is not the fall-through of a live instruction.
2. **No pointer** to it or into it exists: no 4-byte little-endian window, at **every byte alignment**, in
   the whole of block 0 holds an address inside it. This covers code immediates, vtables, task tables,
   shell tables, jump tables, constructor tables and the `.data` image in one test.
3. **Transitive:** references that sit inside dead code do not count; everything else counts.
4. For strings: the run holds only NUL-terminated strings, is not a fixed-width record array, and starts
   after a NUL (so reading a neighbour cannot enter it).

**Live set (`scripts/reach.py`).** Candidates are the instructions of the three loaded code runs
(0x7E4FE000–0x7E731584 and 0x7E8808C0–0x7E880F43 = segment 1, 0x7E8F5800–0x7EBABF8D = segment 2,
0x7ECCB800–0x7EECE317 = segment 3; 2,718,943 instructions). **Everything else is an always-live source**:
the boot/kernel area (reset, vectors, IRQ handlers, both task tables), all rodata, the `.data` image and
overlays A/B. So no root is missed by naming roots; the cost is that a table nobody reads still keeps its
targets alive. An instruction is live when a live source reaches it by the next-instruction rule, a decoded
target, or a window (rule 2). The result is the least fixpoint.

**Checks on the method (V):**
- Window alignment 1, 2 or 4 gives almost the same dead set (9,044 / 9,044 / 9,788 B), so byte noise does
  not hide dead code.
- "Phantom" test: every byte of block 0 read as `call`/`calls`/`jmp` d16/d32 whether or not an instruction
  starts there. 36 phantoms hit the 13 dead runs ≥ 64 B: 33 lie inside a live instruction (displacement
  bytes of soft-float calls), 3 in the kernel area at addresses that are not decoded call sites, 0 at an instruction start of a code run (`results/dead_code_refs.tsv`).
- No relative code pointers: all 958 `jmp (aN)` in the code runs follow a `mov` from memory (absolute
  tables); `mov pc,aN` occurs only in decoded rodata.
- Other blocks: windows into the recommended ranges exist only in high-entropy data of block 3 and the tail
  (2 + 3 hits; block 3 has 8,007 block-0-looking windows in 3.6 MB, the random rate).

**What the method cannot see (I):**
- A pointer built at run time (base + index) from a base outside the candidate. For code this needs
  function-address arithmetic, which the compiler does not emit. For strings it needs a fixed stride
  (excluded by rule 4) or a reader that walks a packed list from a string before the run.
- A string table inside a binary object, read by offsets inside the object. Two such runs (3D shader symbol
  tables 0x7F0229E0, 0x7F019206) passed the automatic rule and were **rejected by hand**. Runs that follow
  binary data are class A only when checked by hand (two are, §4).
- Unreferenced non-string tables (14d) were **not** analysed: without a reference there is no object
  boundary, so an unreferenced table cannot be told apart from the tail of the table before it.

## 3. Loaded ranges (V)

| Range | Loader | Evidence |
|---|---|---|
| 0x7E4FE000–0x7E881000 | boot task | end address loaded at 0x7E44A074 (only window to 0x7E881000) |
| 0x7E8F5800–0x7ECB1000 | Usr1, 0x7E504C18 | `mov 0x7ECB1000,d2` (0x7E504BF2) minus start; dst 0xBE8F5800, src 0x80794800, mode 0x103 |
| 0x7ECCB800–0x7F034000 | Usr1, 0x7E504D6B | dst 0xBECCB800, src 0x80B6A800, size 0x7F034000 − 0x7ECCB800 |
| ctor tables | walker 0x7E44B6B0 | byte counts 24 / 76 / 180, no terminator: the 0xFF after a table is never read |

Flash source and runtime address differ by the same constant for both Usr1 loads (0x80B6A800 − 0x80794800 =
0x7ECCB800 − 0x7E8F5800 = 0x3D6000) (V).

## 4. Ranked table

Class: **A** strictly dead (§2); **B** reachable only from a debug shell or a never-selected value;
**C** shared or uncertain. "Usable" = contiguous bytes. Full lists: `results/class_a.tsv`, `results/class_b.tsv`.

| # | Range | Usable | Seg | What | Evidence | Class |
|---|---|---|---|---|---|---|
| 1 | 0x7EBF1090–0x7EBF3BAD | 11,037 | 2 | `sdk` shell group and method name list (`A**: CameraCommon` … `M71`/`getReleaseSetting` … `t10`), 1,205 strings | no window in block 0 except 4 hits on 0x7EBF22C0, which are the low words of doubles in a float table (0x7F0E5830…, V); the table before it (0x7EBF0FA0) has two readers, both stop at 30 entries (`cmp 30`, 0x7E99BB0B, 0x7E99D01A); emulator run §6 | A |
| 2 | 0x7EBB1F4C–0x7EBB304C | 4,352 | 2 | Bluetooth debug strings (135) | no window; packed, mean length 31; follows the module's pointer table and one string | A |
| 3 | 0x7EE541B3–0x7EE548B1 | 1,790 | 3 | 3D-engine float helpers (16e: "type modules") | called only from #4, #7 and each other | A |
| 4 | 0x7EE40B17–0x7EE411F6 | 1,759 | 3 | same cluster | 0x7EE40B17 ↔ 0x7EE46D27 call each other; no outside caller | A |
| 5 | 0x7EE5382E–0x7EE53D6A | 1,340 | 3 | same cluster | caller 0x7EE40C6D is dead | A |
| 6 | 0x7EE3CBF2–0x7EE3CFE2 | 1,008 | 3 | same cluster | 3 callers, all dead | A |
| 7 | 0x7EE46D27–0x7EE4709D | 886 | 3 | same cluster | — | A |
| 8 | 0x7EE40728–0x7EE40877, 0x7EE46C39–0x7EE46CB0 | 335, 119 | 3 | same cluster | — | A |
| 9 | 0x7E813170–0x7E813ED0, 0x7E79944E–0x7E79A16B, 0x7E805088–0x7E805CE8, 0x7E7D6717–0x7E7D71FD | 3,424, 3,357, 3,168, 2,790 | 1 | string pools: mode-table names, file callbacks, `[AVCHD]` AvmidApi record prints, `api_tft_*` | automatic rule only (run follows a referenced string) | A (auto) |
| 10 | 0x7E50A201–0x7E50A3C2, 0x7E53A55C–0x7E53A700, 0x7E50C46E–0x7E50C517 | 449, 420, 169 | 1 | unreferenced functions | reach.py | A |
| 11 | 0x7E880F5C–0x7E881000 | 164 | 1 | 0xFF tail of the boot copy | only window is the load end 0x7E881000; ctor walker is count-bound | A |
| 12 | 0x7E99BB93 (5,267), 0x7E99A7CF (3,866) and 32 more runs | 12,667 | 2 | handlers of the 30 `sdk` sub-commands | dead when table 0x7EBF0FA0 is cut | B |
| 13 | 248 runs; largest 0x7E6E3D18 (4,961), 0x7E525781 (4,462), 0x7E6C0C53 (4,003), 0x7E9035A8 (3,606, seg 2), 0x7E93A0EB (3,346, seg 2), 0x7ECCC1C8 (2,867, seg 3) | 106,831 total | 1/2/3 | first-level U_SHELL command handlers | dead only when **all three** copies of the 54-entry command table are cut (0x7E7332B4, 0x7E7326A4 `dbgall`, 0x7EBCC2BC); a lower bound, because nested command tables stay live | B |
| 14 | 0x7E6E22BA–0x7E6E2D4C | 2,706 | 1 | AVCHD clip-info parser | §5 | B |
| 15 | 0x7ECB1000–0x7ECCB800 | 108,544 | gap | 0xFF between the two Usr1 loads, not in RAM today | §7 | C |

**Class-A totals** (no overlap with any block-0 byte of the 1,593 patch ops in `patches/`, `patches/history/`,
`experiments/*/patches/`, checked by `scripts/summary.py`):

| Segment | Code | Strings | In runs ≥ 512 B | Other |
|---|---|---|---|---|
| 1 | 1,292 B (7 runs) | 28,583 B (45 runs) | 20,571 B | 164 B 0xFF tail |
| 2 | 0 usable (95 B in pieces < 48 B) | 21,947 B (21 runs) | 16,642 B | — |
| 3 | 7,310 B (8 runs) | 398 B (2 runs) | 6,783 B | — |

Only rows 1–8, 10 and 11 were checked by hand. The other string runs carry the "walker" caveat of §2.

## 5. AVCHD

**Verdict: not dead. Most of it is not even AVCHD.**

- **Recording is shared with MOV (V).** Formats 2 (AVCHD) and 3 (MOV) take the same branch at 0x7E6ED536
  and 0x7E6ED571. The `[MOV_REC_AVCHD]` state machine, MOV_BRIDGE and the MOV_AVCHD task are the H.264
  path for both: the task's `AVCHD_RECORD_INIT` handler 0x7E6D55E8 calls `MovmidApi_cmd_rec_init`
  0x7E6D80B3, the QT path. Removing "AVCHD" code would break MOV recording and H.264 playback.
- **The AVCHD record back end is absent (V strings, I cause).** The parameter builders 0x7E6D81C2–0x7E6D8553 switch
  on quality (5/6/3/4) and never on format. The AVPI plug-in list has `MP4 Mux` and `MP4 Demux` only, no
  transport-stream plug-in. The `[AVCHD] AvmidApi_cmd_rec_*`, `[MOV_REC_AVCHD] add to playlist` and
  `…\CLIPINF\00000.CPI` strings have no reference at any alignment. So the map's "hidden, code complete"
  is **wrong for recording**: format 2 would run the MOV muxer with AVCHD bit rates and a `.MTS` path (I;
  not run).
- **What selects format 2:** setting 26225 (info 405). The info-45 list holds only formats 3 and 1 (10c,
  V there). Writers left: `app Set_CameraInfo 405 2`, `prmdbg`, and USB ADJ op 0x900D (10f), none of them
  a menu path. A retail user cannot select it from the camera; a PC tool speaking ADJ could (I).
- **Exclusively-AVCHD record code (V, cut test):** the format-2 bit-rate arm 0x7E6EE4F9–0x7E6EE563 (107 B),
  plus small arms in 0x7E6EDE08 and the `.MTS` path builder 0x7E5C1164 (not sized). Class B, "never
  selected", not dead.
- **Playback:** `get_info` 0x7E6DEC95 calls the clip-info parser only for a file node with type 4 and
  attribute 32 (0x7E6DECB3–0x7E6DECC4). The parser (0x7E6E22BA + 0x7E6E2323 + 0x7E6E2582, `VideoFormat
  1080i:4 720P:5`) is **2,706 B that nothing else reaches** (V, cut test). It is live by §2, so class B.
  Whether a card with AVCHD clips can create such a node was **not proven**: the extension table in `.data`
  (0x7E8F1FF0: EXE TXT MRK WAV AVI MOV JPG ORF MPO) has no MTS, and the scanner strings
  `dcfscan_exec2 : is_need_avchd(%d)` and `____%04dMTS` are unreferenced, which suggests the AVCHD scan was
  compiled out (I). The writer of attribute bit 32 was not found.
- **AVSCA / demux plug-ins:** `AvmidApi` play (0x7E6E0376–) and the `movplay_com_AVCHD_*` commands drive
  AVSCA for MOV playback too (MP4 Demux is the only demux). Shared, class C.

## 6. Other candidates

- **Photo Surfing, Event View, Collection, IEEE 1394, smile, 3D two-shot:** every function is in the live
  set (tables reference them). No class-A code. Some of their debug strings are in `results/dead_strings.tsv`.
- **Debug shells:** rows 12 and 13. Not dead: S_SHELL starts at every boot and ADJ op 0x902B needs no gate (10f).
- **Duplicate tables:** the U_SHELL command list exists **three** times (0x7E7332B4, 0x7E7326A4,
  0x7EBCC2BC), each with its own name strings and its own reader, so none is dead (B). The touch-table copy
  0x7EFED634 is referenced from `.data` (15a): C.
- **0xFF inside loaded segments:** only the three segment tails are ≥ 128 B. Segment 1's tail (row 11) is free.
- **Emulator check (V, `scripts/emu_sdktable.py`, `results/emu_sdktable.txt`):** the lookup 0x7E99BAE5 ran
  with the 30 table names and 9 other inputs (`M71`, `getReleaseSetting`, `A**:`, empty, near-misses), then
  the help 0x7E99CF3A. Each name reached exactly its own handler, no other input reached any. A logging read
  watch saw 758 reads in the table and **0 reads in 0x7EBF1090–0x7EBF3BAD**.

## 7. Recommendations for the next 5–10 KB

1. **0x7EBF1090–0x7EBF3BAD (11,037 B, segment 2, class A).** One block, larger than the need, loaded by
   Usr1, strongest evidence. If a hidden reader exists after all, the cost is a wrong `sdk` help print.
2. **The 3D-engine cluster (rows 3–8, 7,237 B in 7 pieces, segment 3, class A).** True dead code, so it is
   certainly executable memory; use it for code that fits in 0.9–1.8 KB pieces.
3. **0x7EBB1F4C–0x7EBB304C (4,352 B, segment 2, class A)** as the next table area.

Before first use of rodata for **code**: only the segment tails are known to execute (the existing
patches). That rodata in the same load is executable is I (one flat load, no MPU evidence either way).
Put tables in #1/#3 and code in #2 if in doubt.

**Not recommended yet, but large (C):** the gap 0x7ECB1000–0x7ECCB800 lies between the two Usr1 loads and
flash is contiguous there (§3), so raising the load-end immediate at 0x7E504BF2 would bring up to 108 KB
into RAM next to the current segment-2 patch area. Open points: 104 raw windows point into the gap (1 is
that immediate; the other 84 in code are not instruction operands; 19 in data were not cleared one by one); the
SYSFMEM read size limit and the RAM owner of that range are unknown; the change is in segment 1.

## 8. Reproduce

```sh
python3 experiments/2026-11-13-reclaim-space/scripts/reach.py \
    --pkl /tmp/scratch/reach.pkl          # dead_strict.tsv, dead_decoded.tsv (25 s)
python3 experiments/2026-11-13-reclaim-space/scripts/verify_code.py \
    /tmp/scratch/reach.pkl 64 > experiments/2026-11-13-reclaim-space/results/dead_code_refs.tsv
python3 experiments/2026-11-13-reclaim-space/scripts/deadstr.py 64 \
    > experiments/2026-11-13-reclaim-space/results/dead_strings.tsv
python3 experiments/2026-11-13-reclaim-space/scripts/summary.py      # class_a.tsv + overlap check
python3 experiments/2026-11-13-reclaim-space/scripts/cut.py \
    /tmp/scratch/reach.pkl > experiments/2026-11-13-reclaim-space/results/class_b.tsv
python3 experiments/2026-11-13-reclaim-space/scripts/emu_sdktable.py # needs tools/emu setup
python3 experiments/2026-11-13-reclaim-space/scripts/q.py win 0x7EBF1090 0x7EBF3BAD
```

`dead_strict.tsv` adds the phantom edges to the fixpoint; it under-reports (2.7 KB) and is kept as the
lower bound. `lib.py` holds the pickle loader and `refs()`; `q.py win LO HI` lists every window into a range.

## 9. Limits and one process note

- Static analysis of stock v1.6 only; nothing was run on a camera. The emulator test covers one dispatcher.
- The decode is `build/map/functions.txt`. A desynchronised decode could hide a short `Bcc`; long transfers
  are covered by the phantom test.
- The U_SHELL figure is a lower bound and its runs were not checked one by one.
- Process: one `pip3 download numpy` was run by mistake (network). The file was deleted, nothing was
  installed, and all scripts use the standard library only.

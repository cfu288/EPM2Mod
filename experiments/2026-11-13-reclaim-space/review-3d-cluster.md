# Adversarial review: the "dead" 3D-engine cluster (README rows 3–8)

Date 2026-11-13. Read-only review of stock E-PM2 v1.6 block 0
(`build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin`, runtime = 0x7E421020 + offset). Nothing was built,
flashed or committed. Scratch scripts (not in the repo): `/tmp/scratch/rev3d/`.
Labels: **V** = read in the bytes or run; **I** = inferred.

## 1. Verdict

**The claim holds. All seven pieces are DEAD. No reference of any kind was found.**

| # | Piece | Size | Functions inside | Verdict |
|---|---|---|---|---|
| 3 | 0x7EE541B3–0x7EE548B1 | 1,790 | 541B3, 5424C, 542EE, 5484C | DEAD |
| 4 | 0x7EE40B17–0x7EE411F6 | 1,759 | 40B17, 40C95, 40E4D, 40F80, 410B9 | DEAD |
| 5 | 0x7EE5382E–0x7EE53D6A | 1,340 | 5382E, 53AAB, 53B26 | DEAD |
| 6 | 0x7EE3CBF2–0x7EE3CFE2 | 1,008 | 3CBF2 | DEAD |
| 7 | 0x7EE46D27–0x7EE4709D | 886 | 46D27, 46D87, 46DE7, 46ECB, 46FB3 | DEAD |
| 8a | 0x7EE40728–0x7EE40877 | 335 | 40728 | DEAD |
| 8b | 0x7EE46C39–0x7EE46CB0 | 119 | 46C39 | DEAD |

The same sub-claims carry every piece, so they are listed once (§2). Boundaries are exact (V, §2.5).

**Strongest evidence for (new, not in the study):** none of the 20 functions can be entered through a
pointer. Each starts without `movm` and returns with `ret [regs],N`, so it works only when entered by a
`call` instruction that carries the same register list and frame size (V, §2.2). So vtables, type tables,
callbacks, `.data`, overlay data and scene data cannot reach them, whatever they hold. Only a relative
`call` can, and block 0 has none outside the cluster at any byte position (V, §2.1).

**Strongest evidence against:** nothing in the bytes. What is left is the list in §6. The main items: the
reason the roots are missing is I (no body has them, §4), the scene resource was not read, and the emulator
run covers about 3 % of the engine (§5).

## 2. Sub-claims and their evidence class

### 2.1 No direct transfer from outside (V)
`scan.py` reads **every byte** of block 0 (0x7E421020–0x7F1A0FE0, overlays A and B included) as the first
byte of `call` d16/d32 (CD/DD), `calls` d16/d32 (FA FF / FC FF), `jmp` d16/d32 (CC/DC), `Bcc`/`bra` d8
(C0–CA) and `bvc/bvs/bnc/bns` d8 (F8 E8–EB). This covers every alignment of a linear sweep and code that the
function DB missed or classed as data.

| Kind | Sources inside the cluster | Outside, at an instruction start | Outside, not at an instruction start |
|---|---|---|---|
| `call` d16 / d32 | 26 / 13 | 0 | 8 / 12 |
| `jmp` d16 / d32 | 62 / 0 | 0 | 4 / 3 |
| `calls` d32 | 0 | 0 | 3 |
| `Bcc` d8 | 367 (+1 `bnc`-class) | 0 | 2 |

- The 32 outside hits were each placed in the decode. All lie inside a longer instruction (displacement or
  immediate bytes). The study calls 3 of them "data" (0x7E4542AB, 0x7E45431D, 0x7E4543BA); they are the
  d32 bytes of real `call`s in kernel functions 0x7E4542A2, 0x7E454305 and 0x7E4543B5 (V).
- The 2 `Bcc` hits (0x7EE46BE3, 0x7EE46CBD) are the second bytes of `mov a0,(d0,a1)` and `mov 196,a0` (V).
- **Overlays:** overlay B is linked at its file position. Its calls into resident code are plain relative
  `call`s that decode to function entries (e.g. 0x7F09E183 `call 0x7EE61E4A`; 151 such calls into the C3D
  framework, 0 into the engine core) (V). So the scan sees overlay code correctly.
- **Fall-through:** the instruction before each piece is `ret` or `retf` (0x7EE541B0, 0x7EE40B14,
  0x7EE5382B, 0x7EE3CBEF, 0x7EE46D24, 0x7EE40725, 0x7EE46C36), and each piece ends with `ret` (V).
- **Cross-function jumps:** no `jmp`/`Bcc` in the engine core leaves its own function (V), so no tail call
  enters the cluster.

### 2.2 No indirect entry is possible (V)
- **No absolute pointer:** no 4-byte little-endian window at any byte alignment in block 0 holds an
  address inside the seven pieces (V; reproduces the study), and none holds its 0xBE… alias (Usr1 copies
  segment 3 to 0xBECCB800). This covers rodata, the `.data` image 0x7E8DA000–0x7E8F3113, overlay A/B data
  and every `mov imm32`. With high byte 0xFE or 0x3E there are 29 windows; those inspected are misaligned
  reads (e.g. pointers 0x7EFEE470… in `.data` at 0x7E8EE2C4), and no such alias is known (I).
- **Calling convention:** all 20 functions start with a plain `mov`/`add` (first bytes 47, 43, 46, 42, 93,
  92, 97, FA FE) and return with `ret [d2,d3,a2,a3],N` (`[d2,a2],24` for 0x7EE53AAB). The register save
  and the frame are made by the caller's `call … ,[regs],N`. Every call site in the cluster carries the
  matching list (V). A `calls (An)` or `jmp (An)` entry would return through a frame nobody made.
  In the engine core, 725 of 725 call-only functions start without `movm`, and 107 of 125 pointer-referenced
  functions start with `movm` (the other 18 start with F8, F1 and others; not examined) (V). The linker
  removed the prologues because it saw no address-taken use (I, MN10300 relaxation).
- **Switches:** the compiler emits absolute tables (`mov table,aN; mov (d0,aN),aN; jmp (aN)`). The engine
  core has 3 `jmp (An)` (0x7EE31FE4, 0x7EE497AD, 0x7EE4981F); all read absolute tables (V). The cluster
  itself has no `jmp (An)` and no `calls (An)` (V). Relative jump tables do not occur.
- **Registries (enumerated, V):** type table 0x7F02AA14 (28 rows × 7 words: size, dtor, 4 optional slots,
  slot +20), format-loader table 0x7F027C4C (9 rows `{magic length, probe, load}`), MC chunk-factory table
  0x7F027C00 (13 entries). No entry lies in the cluster. The nearest are 0x7EE415BC (type 10, slot +20)
  and 0x7EE472A9… (type 8), both outside.
- **Base + offset:** ruled out by the calling convention above; it needs no scan.

### 2.3 The call graph, rebuilt independently (V)
- The engine core 0x7EE294B5–0x7EE5B5BB has 949 functions. Outside callers reach 83 of them, with 187 call
  edges, **all from the C3D framework** 0x7EE619C7–0x7EE8F4F3. No other module and no overlay calls the
  core directly.
- Roots = those 83 + every engine function hit by any window anywhere (246, generous). Closure over
  `calls.tsv`: 929 live, **20 not reached = exactly the 20 functions above = 7,237 B**.
- Inside the cluster every caller is in the cluster (the study's "caller 0x7EE40C6D" is the call site of
  0x7EE5382E inside 0x7EE40B17):

| Pair (mutual recursion) | Leaf helpers used only by the pair |
|---|---|
| 40728 ↔ 46C39 | 3CBF2 (also 40B17, 40C95) |
| 40B17 ↔ 46D27 | 5382E → 53AAB |
| 40C95 ↔ 46D87 | 53B26 |
| 40E4D ↔ 46DE7 | 541B3 |
| 40F80 ↔ 46ECB | 5424C |
| 410B9 ↔ 46FB3 | 542EE → 5484C |

### 2.4 Why they are dead (I, with V parts)
- **What they are (V for the code shape, I for the names):** six scene-graph walkers. Each pair is "visit
  node" (0x7EE40xxx) and "visit the node's children" (0x7EE46xxx; loop over a u16 count at +168 of 144-byte
  child records, depth limit 4). A seventh pair of the same shape, 0x7EE40877 ↔ 0x7EE46CB0, **is live**:
  its root is the engine API 0x7EE4FF48, called from the C3D framework thunk 0x7EE6D3D9.
- 40E4D/40F80/410B9 collect node pointers into a caller array with a capacity check after a geometric test:
  541B3 is a point/sphere test (3 × fsub, dot product, compare), 5424C and 542EE larger tests. These are
  query walkers (pick / volume query). 40B17/40C95 use bounds helpers 5382E/53B26. 40728 is a variant of
  the live draw walker 40877.
- **The roots are absent, not hidden (V).** Each pair needs one outside caller to start. No such call exists
  (§2.1). The node and child functions sit in two address groups (0x7EE40xxx and 0x7EE46xxx), next to their
  live siblings. That fits two object files linked whole, while the API objects that start the six walks
  were never pulled from the library (I). The live helper 0x7EE4253C is shared with live code, so the
  cluster's callees prove nothing.

### 2.5 Boundaries (V)
Function starts in the pieces come from `call` targets inside the cluster only, so they were re-checked:
each start follows a `ret`/`retf`, the decode from each start reaches the next start with no left-over
bytes, and the next function after each piece (0x7EE548B1, 0x7EE411F6, 0x7EE53D6A, 0x7EE3CFE2, 0x7EE4709D,
0x7EE40877, 0x7EE46CB0) has live callers. **Do not write one byte past a piece end.**

## 3. Scene data (attack line 4)

- The scene files (`MB`, `MT`, `MCM_/MCA_/MCT_/MCE_`, BMP/GIF/PNG) are not in block 0; 14a infers the
  `RES_MODE_C3D` resource. Their content was **not** read.
- It does not matter for this claim: scene data selects code only through the three tables of §2.2 and
  through the C3D class registry (run-time vtables filled by `mov imm32` in 0x7EE64322, covered by the
  window scan). None can name a cluster address, and a cluster function cannot be entered by pointer (V).

## 4. Other bodies (attack line 5)

`xbody.py` matches each function by its bytes with call/jump displacements and address immediates masked,
then counts raw `call` d16/d32 at every byte of that body's block 0.

| Body / version | Base | 20 functions found | Callers from outside the cluster |
|---|---|---|---|
| E-PM2 `101_1101`, `_1203`, `_1300`, `_1400`, `_1501` | 0x7E421020 | all | 0 |
| E-PL5 `100_1600` | 0x7E421020 | all (e.g. 40728 → 0x7EE40DA8) | 0 |
| E-PL6 `112_1400` | 0x7E421020 | all (40728 → 0x7EE415BC) | 0 |
| `108_1800` | 0x7E101020 | all (40728 → 0x7EB88A03) | 0 |
| `113_1400`, `115_1400`, `118_4100`, `122_3101` | — | none; the live controls are absent too | — |

- In every body that has this engine build, the six cycles have the same shape and no root (V). The live
  control pair has its root in each (e.g. 0x7EE505C8 in E-PL5).
- The four newer bodies keep GL (`glPointSize`) but have no `MCM_` magic and no `C3D_BRG` string: another
  engine, no evidence either way (V).
- So no body shows a feature that uses these functions; the check cannot name the missing feature.

## 5. Emulator (attack line 6)

- **Run (V, `emu3d.py`, om-emu function mode):** each of the 83 engine entries that the C3D framework
  calls was called with synthetic arguments: 3 memory fills (zero, every word a pointer to a filled buffer,
  every word 1) × 2 register sets (d0 = d1 = 0 or 1), 498 calls, limit 30,000 instructions each. The 20
  cluster entries were breakpoints.
- **Result:** 270 calls returned, 228 ended in a fault or the limit. **0 breakpoint hits and 0 executed
  addresses inside the seven pieces.**
- **Coverage, honestly:** 2,922 distinct instruction addresses of the engine core's 86,392 (about
  3 %), in 146 of 949 functions. No real scene was loaded, no object was built by the engine's own
  loaders, and the live walker 0x7EE40877 ↔ 0x7EE46CB0 was not driven through a real node tree. This run is
  a smoke test. It adds almost nothing to §2; it would have caught only a shallow caller.
- Not done: a full slideshow run (needs the scene resource, overlay B tasks, GL and a GPU model).

## 6. What no static method can show

1. **Content of the C3D scene resource.** Not in block 0, not read. Mitigated by §2.2, not eliminated for
   bugs (item 3).
2. **Code outside block 0.** Other blocks, the boot block and anything loaded to RAM from a card (BASIC
   programs, debug-shell commands that call an address) were not decoded. A relative `call` from RAM code
   to 0x7EE4xxxx would need a displacement built for this exact layout. Not plausible (I).
3. **Wild control flow:** a corrupted return address or function pointer in live firmware. Stock code then
   runs a dead walker; patched code runs the new code. Both are failures already.
4. **Decode trust:** "at an instruction start" rests on `build/map/functions.txt`. The every-byte scan
   removes this for long transfers. For `Bcc` d8 it was checked by hand only for the 2 hits found.
5. **Run-time copying** of engine code to another address was not searched for. No window into the
   cluster exists, so no reader of its bytes is visible.
6. **Why the roots are missing** stays I. A proof needs the vendor library.

## 7. If the claim were wrong (attack line 7)

- The only user is the GPU slideshow (GUI 0x7ED081AE → `CapGSld_GpuSlideShow` 0x7EA55350 → overlay B →
  C3D framework → engine). A hidden caller would execute patch bytes inside the C3D task: slideshow hang or
  exception during playback (I).
- **Boot:** segment 3 is copied by Usr1 as one block; the copy does not execute it. The engine's only
  callers are in the C3D framework, whose only callers are in overlay B, which loads on demand (Usr2).
  Nothing in the reset path, the boot task or the constructor walker 0x7E44B6B0 points into the engine
  cluster (no window, V). So a wrong claim cannot stop boot (I from V facts).
- **SD recovery / update:** the update path does not call the 3D stack (no call edge from segments 1 or 2
  into 0x7EE294B5–0x7EE8F4F3 other than overlay B's, V). Not at risk (I).
- **Real risk of using the space:** a write past a piece end corrupts a live engine function (§2.5).

## 8. Notes on the study

- Row 5's evidence ("caller 0x7EE40C6D is dead") names a call site inside 0x7EE40B17, not a function.
- The study's phantom test had no `Bcc` d8 and no overlay statement, and it lists kernel-area sources as
  `data` although they are bytes inside real instructions. All three were checked here; no new hit.
- Side finding, not part of the claim: 0x7EE3D3CA (763 B) has one caller, the dead 0x7EE40728. The study
  keeps all but 73 B live because of one unaligned window, 0x7E872862 → 0x7EE3D470, which was not examined
  here. Possible extra space, **unproven**.
- Reproduce: `python3 scan.py` (40 s), `xbody.py` (needs the other bodies' block-0 images and map DBs),
  `emu3d.py` (needs the om-emu setup of `tools/emu/README.md`), all in `/tmp/scratch/rev3d/`.

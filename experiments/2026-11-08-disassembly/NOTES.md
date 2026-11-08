# Disassembly setup (2026-11-08)

**Goal:** be able to read E-PM2 block 0 as MN103/AM33 instructions, then understand the movie-limit routine (block 0 offset 0x2CCEC0 / 0x2CCF00) properly instead of porting E-P5 bytes blindly.

## Tooling plan

1. **GNU binutils, target mn10300-elf.** Its objdump is the reference disassembler (`-m am33-2`). Build it with `scripts/build-binutils-mn10300.sh` into `~/opt/mn10300` (no sudo; GNU source with a verified signature).
2. `tools/disasm.py` wraps objdump. It takes a block offset or a runtime address and caches the decoded block in `build/blocks/`.
3. Later: Ghidra plus a third-party MN10300 SLEIGH plugin (txt231/GhidraMn10300 or michaelbrandi/ghidra-mn103-extension), for a decompiler and cross-references. Needs a JDK and Ghidra (~1 GB) and runs third-party code. **Decide before installing.**

## Status

- [x] binutils 2.43.1 source downloaded to `~/opt/src`, signature good (Nick Clifton).
- [x] Build. The user ran the build script (needed `MAKEINFO=true`; makeinfo is not installed). GNU objdump 2.43.1 is in `~/opt/mn10300/bin`.
- [x] Sanity check: the movie-limit routine disassembles cleanly with `-m am33-2`. (0x3250xx is `[firmup]` *strings*; the updater code that uses them is not found yet.)
- [x] Verify runtime base 0x7E421020: six `mov imm32,a0` pointers in the movie routine land on string starts (preceding byte 00) whose text matches the branch. See below.

## Facts to check against

- E-M5 II/E-M1 III use `mov 1740, D0` (29×60 s) and `mov 7200, D0` for the movie limits (xdel `firmware-hints.txt`).
- The E-P5 patch site maps to E-PM2 v1.6 block 0 at 0x2CCEC0 / 0x2CCF00 (landscape report).

## Movie-limit routine (v1.6), read from the code

Function 0x7E6EDE08–0x7E6EDF9C (block 0 offset 0x2CCDE8–0x2CCF7C). Starts right after the previous function's `retf`; ends with `ret [d2,d3,a2,a3],44`.

**Base check.** The six string pointers in this function, all at odd addresses, each land on a string start:

| Pointer | Offset | String | Used where |
|---|---|---|---|
| 0x7E80E860 | 0x3ED840 | `Free Secotr : ` | debug print of the free-space argument |
| 0x7E80E86F | 0x3ED84F | `[QT] Parameter Error quality:` | MOV, unknown quality |
| 0x7E80E88D | 0x3ED86D | `[AVCHD] Parameter Error quality:` | AVCHD, unknown quality |
| 0x7E80E8AE | 0x3ED88E | `[QT] Parameter Error Format:` | format neither MOV nor AVCHD |
| 0x7E80E8CB | 0x3ED8AB | `MAX   Time  : ` | debug print of free-space time |
| 0x7E80E8DA | 0x3ED8BA | `Limte Time  : ` | debug print of the clamped time |

**What it does (from the code):**
- Arguments: `d0` = quality (u16, saved to (24,sp)), `d1` = free space (saved to (8,sp)).
- Reads two settings via `call 0x7E457C75`: id 33105/index 7 → `d3` (selects the higher or lower rate), id 26225/index 0 → `d2` (format: 3 = MOV/QuickTime, 2 = AVCHD; the error strings show this).
- Per format: overhead (12,sp) = 375 (MOV) or 47 (AVCHD); reserve `a2` = 832, 2624 (MOV q4) or 400 (AVCHD); file cap (16,sp) = 8388608.
- Per quality: rate (4,sp) and time limit `a3`. MOV q6: 4883/4151; q3: 3174/2442; q4: 977, limit **7200**. AVCHD q5: 5860/4711; q3: 4711/4045. All other modes have limit **1740**.
- Result = min(limit, (filecap − reserve)/(rate+overhead), (free − reserve)/(rate+overhead)). Zero if free ≤ reserve.
- Stores `udfu01 30` of the free-space time at (32,a0) and (36,a0) and of the clamped time at (40,a0); a0 comes from `call 0x7E6ED536`. Returns `udfu01 600` of the free-space time.

**Patch sites (match the handoff):** `27 20 1c` = `mov 7200,a3` at 0x2CCEC0 (MOV q4 only); `27 cc 06` = `mov 1740,a3` at 0x2CCF00 (every other mode).

**Inferred, not verified:**
- Units are 512-byte sectors and sectors/s: 8388608 × 512 = 4 GiB (the FAT32 file limit), and the rates come to 5.5–24 Mb/s.
- `udfu01` (an MN103 user-defined-unit op) looks like a multiply: ×30 fits frames at 30 fps. Not checked.
- Quality codes (q3/q4/q5/q6) and the hi/lo setting are not mapped to menu names.
- Olympus specifies 22 min for Full HD Fine; this arithmetic gives 26.6 min (MOV q6 hi) or 23.7 min (AVCHD q5 hi). That mismatch is unexplained.
- This routine computes the limit. Whether recording actually stops on this value, rather than another check, is not shown.

**Effect of 1740 → 32400, if the above holds:** the 4 GiB cap binds instead. Gains: MOV q6 hi 0, q6 lo +1.9 min, q3 hi +10.4, q3 lo +20.6; AVCHD q5 hi 0, the 19.5 Mb/s modes +0.4, q3 lo +5.2. **7200 → 32400 gains nothing**: MOV q4 is already capped by 4 GiB at 103 min.

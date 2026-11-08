# Disassembly setup (2026-11-08)

**Goal:** be able to read E-PM2 block 0 as MN103/AM33 instructions, then understand the movie-limit routine (block 0 offset 0x2CCEC0 / 0x2CCF00) properly instead of porting E-P5 bytes blindly.

## Tooling plan

1. **GNU binutils, target mn10300-elf.** Its objdump is the reference disassembler (`-m am33-2`). Build it with `scripts/build-binutils-mn10300.sh` into `~/opt/mn10300` (no sudo; GNU source with a verified signature).
2. `tools/disasm.py` wraps objdump. It takes a block offset or a runtime address and caches the decoded block in `build/blocks/`.
3. Later: Ghidra plus a third-party MN10300 SLEIGH plugin (txt231/GhidraMn10300 or michaelbrandi/ghidra-mn103-extension), for a decompiler and cross-references. Needs a JDK and Ghidra (~1 GB) and runs third-party code. **Decide before installing.**

## Status

- [x] binutils 2.43.1 source downloaded to `~/opt/src`, signature good (Nick Clifton).
- [ ] Build. The agent's sandbox blocked compiling downloaded source, so the user runs the build script.
- [ ] Sanity check: disassemble around the `[firmup]` code and the movie-limit site, confirm clean instruction streams.
- [ ] Verify runtime base 0x7E421020 by checking that `mov imm32` string pointers land on string starts.

## Facts to check against

- E-M5 II/E-M1 III use `mov 1740, D0` (29×60 s) and `mov 7200, D0` for the movie limits (xdel `firmware-hints.txt`).
- The E-P5 patch site maps to E-PM2 v1.6 block 0 at 0x2CCEC0 / 0x2CCF00 (landscape report).

# Handoff: E-PM2 custom firmware

## Goal

The user wants GRKit-style custom firmware for their **Olympus PEN E-PM2**: firmware model 1010, TruePic VI, body firmware 1.6, lens 1.1.

The approach is to patch the official firmware file and flash it from an SD card. Recompiling the firmware is not the plan (agreed: unrealistic). The long-term route is to:
1. Understand the firmware in a disassembler or decompiler.
2. Make small, well-understood patches.
3. Later, possibly write C code placed into unused space, the Magic Lantern/CHDK model.

The user cares about **understanding the code**, not just poking bytes.

## Proven on the user's camera (2026-11-08)

See `docs/camera-log.md`.
- **SD flash path:** `DCOLYMP/E1019999.BIN`, then hold OK and power on. The lamp is **solid for about 1–1.5 min while writing**, then **blinks when done** (power off manually).
- **Modified firmware runs.** `patches/pixel-hacking.json` renames a menu label and was confirmed on screen. The camera checks only the container checksums. There is no signature.
- **Recovery from modified back to stock works.**

## Repo map (`/path/to/epm2-tools`, git, branch main)

- `tools/oetool.py`: container unpack/pack/patch, checksums. Round-trips all 6 stock versions byte for byte.
- `tools/build.py`: JSON patch spec → `build/<name>.BIN`. Ops: `bytes` (offset, with expected bytes) and `utf16-replace-all`.
- `tools/disasm.py`: objdump wrapper. Takes a block-0 offset or a runtime address. **objdump is not built yet.**
- `scripts/build-binutils-mn10300.sh`: builds GNU binutils (mn10300-elf) into `~/opt/mn10300`. Source is already downloaded and signature-verified in `~/opt/src`.
- `firmware/`: stock E-PM2 v1.1–v1.6 and an E-PL5 v1.6 reference. The BINs are git-ignored; `SHA256SUMS` is tracked.
- `docs/`: flashing, camera log, firmware format, verification, conventions.
- `experiments/YYYY-MM-DD-slug/NOTES.md`: ad-hoc work. Current one: `2026-11-08-disassembly/`.
- Background research: `../reports/Olympus firmware modding landscape.md` and `../research_notes/Olympus firmware modding landscape/`.

## Next steps

1. **Get objdump built.** The sandbox classifier blocked the agent from compiling downloaded source. Ask the user to run `! /path/to/epm2-tools/scripts/build-binutils-mn10300.sh`, or to add a permission rule. Don't work around the block.
2. **Check the disassembly.** Disassemble the `[firmup]` updater code (block 0 around 0x3250xx) and confirm clean `-m am33-2` output.
3. **Confirm the runtime base address,** estimated at 0x7E421020. `mov imm32` string pointers should land on string starts.
4. **Read the movie-limit routine** at block-0 offsets 0x2CCEC0 / 0x2CCF00. This is the E-P5's camera-tested patch site, which exists once in the E-PM2. It is believed to be the 29-min limit (`mov 1740` / `mov 7200`; the recommended new value is 32400). Confirm it from the code before writing a patch.
5. **Improve build.py, as agreed in principle:**
   - Pattern-based ops that fail unless there is exactly 1 match.
   - Runtime-address input.
   - Typed u16/u32 values.
   - Overlap detection between stacked specs.
6. Write `patches/movie-limit.json`, show the user the exact byte diff and the reasoning, then they flash it and the result goes in the camera log.
7. **Later, with user approval:** Ghidra plus the third-party MN10300 plugin (txt231/GhidraMn10300 or michaelbrandi/ghidra-mn103-extension) for a decompiler. This needs a JDK and runs third-party code, so ask first.

## Working rules and user preferences

- **Commits:** Conventional Commits, enforced by `.githooks/commit-msg`. Types include `exp` for experiments. End each commit message with the session's attribution lines.
- **Camera safety:**
  - Never hand over a build for flashing without first showing the diff and the expected sha256.
  - Log every flash, before and after, in `docs/camera-log.md`.
  - Never put an E-PL5 (`E100…`) file on the card.
- **Copying to the camera's card:** the user copies files with scp to their Mac (`/Volumes/SDCARD/DCOLYMP/E1019999.BIN`) and checks the hash with `shasum -a 256`. Give multi-line commands with `\` continuations, because long lines got truncated when pasted.
- **Accuracy:** the user values accuracy over speed and has caught earlier mistakes. Verify claims against primary sources or the bytes, and label anything inferred.
- **Research:** for "has anyone done X" questions, sweep GitHub directly with `gh search`, sorted by most recently updated.
- **Repo structure:** the user said the current structure feels heavy but chose to keep it for now. Don't add more scaffolding unless it's needed.
- **External code:** don't run code from cloned external repos without asking. Agent-written decoders are fine.

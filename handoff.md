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

## Current focus (updated 2026-11-08, later session)

**The user redirected the work to mapping and learning the firmware, not patching.** Do not write patches or flash builds unless the user asks again.

Done:
- objdump (mn10300) is built in `~/opt/mn10300/bin`. HOME is now `/home/agent`.
- The runtime base 0x7E421020 is verified.
- `tools/fwmap.py` builds a function database of block 0 (`build` takes about 40 s, then `fn`/`str`/`range`/`xref`/`tasks`).
- **The full map is in `docs/firmware-map.md`.** It covers architecture, regions, block contents, the updater's checks, a feature inventory and open questions. Detail is in `experiments/2026-11-08-feature-map/sections/01–08`, and hand spot checks are in that folder's `NOTES.md`.

Possible next steps (ask the user which):
1. Work through the open questions in `docs/firmware-map.md` §6: menu reachability of AVCHD, interval shooting and art filters; how the time limit ends a recording; input 0x1709; USB connection types.
2. Ghidra plus a third-party MN10300 plugin for a decompiler. This needs a JDK and runs third-party code, so ask first.
3. The `build.py` improvements and `patches/movie-limit.json` from the earlier plan, only if the user returns to patching. Facts for that: only `mov 1740,a3` (0x2CCF00) matters, because the 7200 path is already capped by 4 GiB.

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

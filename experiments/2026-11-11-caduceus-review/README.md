# What the Caduceus projects mean for the E-PM2 (2026-11-11)

This review covers four external projects, read but not run:

- **[caduceus-ep7](https://github.com/cakelesscoder/caduceus-ep7):** firmware mods for the PEN E-P7. Apache-2.0.
- **[caduceus-om3](https://github.com/androidfanman/caduceus-om3):** a port of Caduceus to the OM-3. Apache-2.0.
- **[om-emu](https://github.com/flatpanda/om-emu):** an emulator for Olympus/OM firmware. **No licence**, so treat it as all rights reserved.
- **[oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis):** research centred on the PEN-F. Apache-2.0, except its MN103 runner, which is GPL-3.0+.

The four repositories were downloaded on 2026-11-11 as tarballs of their default branch (codeload.github.com/<owner>/<repo>/tar.gz/HEAD). They were kept only in the session scratchpad, not in this repo. The reviewers' own check scripts are in `scripts/`.

Each review checks the external claims against our E-PM2 bytes. Labels: **[V]** read in our bytes, **[X]** stated by the external source, **[I]** inferred.

| Report | Topic |
|---|---|
| [01-methods-safety.md](01-methods-safety.md) | Caduceus build pipeline, hooks, testing, recovery, porting |
| [02-features-portability.md](02-features-portability.md) | Each Caduceus feature and its E-PM2 counterpart |
| [03-emulator.md](03-emulator.md) | om-emu and testing E-PM2 code |
| [04-oly-fw-analysis-crosscheck.md](04-oly-fw-analysis-crosscheck.md) | PEN-F research compared with our map |

## 1. The main point

Caduceus does **not** recompile firmware. It patches the stock image:
- small hand-written MN103 routines placed in proven free space;
- hooks at a few call sites or data words;
- edit lists that check every stock byte they replace;
- packages built for the camera's own SD updater, with a restore file;
- an emulator test of every patch against stock before any camera sees it.

The E-PM2 already does the first and simplest part. `tools/build.py` applies hash-pinned, expect-checked data edits, and two such builds have run on the camera (`docs/camera-log.md`): the Pixel Hacking label and the Portra look tables. What we lack is the rest of the safety apparatus.

## 2. Corrections to our own work (checked by the coordinator in the bytes)

- **The "free space" at 0x7E880F5C–0x7E8D9FFF is not loaded.** The boot task copies block 0 to RAM only up to 0x7E881000 (`mov 0x7E881000,d1` at 0x7E44A074) [V]. Code placed in that 0xFF padding would never run. My earlier suggestion to use it was wrong. The real free space is the 0xFF tails inside the copied range, about 5.3 KB in all (01 §3).
- **`tools/build.py` writes the output file before validating it** [V]. If validation fails it exits 1, but leaves a BIN with a flashable name on disk. Caduceus refuses to write at all.
- **Every full flash also rewrites the stabiliser MCU firmware** (the "OM" tail section) and blocks 1–3 [V, 01 §5]. We have not traced whether the updater accepts a package with only some sections.
- **USB op 0x9122 is a status poll ("CheckStatus")**, not what our map says (04).
- **Our map misses the 0x9C000000/0x9E000000 per-CPU window** in the IMG library (03).
- **`tools/disasm.py` misprints two float helpers** (0x7E5018BC, 0x7E5018CA) as `mcst9`/`mcst48` (03).
- **Independent confirmation:** oly_fw_analysis's hashes for E-PL5 1.6 blocks 1–3 equal ours, and its container description, checksum and error code 0x3211 agree with `oetool.py` (04).

## 3. Safety limits we must write down (docs/flashing.md)

- **Recovery is main-firmware code.** The OK + power card updater is in block 0 and runs from Usr0 after about 56–60 tasks have started [V].
  - A patch to the reset code, the kernel, segment 1 or the `.data` image can stop the camera before recovery runs.
  - Patches confined to segments 2/3 (app and GUI) load after the update decision, so they are probably safe for recovery [I].
  - Recovery is proven only from a text-patch state (camera log, 2026-11-08). Recovery from a bootloop is unproven on the E-PM2.
- **Card files that bypass the normal checks.** `S101????BIN` overwrites the boot area with only a sum check, and `DATE????BIN` writes flash with no check (04 §3). Never leave such files on a card.
- **No version check, and the E-PL5 model id 0x1000 is accepted.** This is already in flashing.md.
- **The failure blink has never been seen,** and we have no zero-write rejection test (01 §6).

## 4. What to adopt

### 4a. Tooling and process (our own code; no approval needed)

| # | Change | From |
|---|---|---|
| 1 | `build.py`: build in memory, validate everything, and only then write. Refuse unknown or duplicate sections and bad checksums. | Caduceus `build_package.py` |
| 2 | `build.py`: a changed-span check (the set of changed bytes equals the union of the edits, block by block) and an overlap check between specs | Caduceus |
| 3 | A build manifest per output: input hashes, each spec's hash, each section's hash and checksum, the output hash. Release builds must match a published hash. | Caduceus, oly_fw_analysis |
| 4 | Generate a stock-restore file next to every build, and print the flash and restore checklist | Caduceus |
| 5 | A code-space table: FF tails inside loaded ranges, each with a proof that nothing reads it (xref, pointer scan) | Caduceus `CODE_SPACE_MAP.md` |
| 6 | A "recovery-critical" range list. `build.py` warns on any edit that touches the reset code, kernel, segment 1 or the `.data` image. | 01 §7, 04 §3 |
| 7 | Pin the block-0 hash (`1b7c4bb1…`) in the map, fwmap and every section | oly_fw_analysis |
| 8 | Split our V label into "read in bytes" and "control flow traced" | oly_fw_analysis |
| 9 | Trace whether the updater accepts a subset of sections (to stop reflashing the stabiliser) | 01 §5 |
| 10 | Fix the map items in §2 | 03, 04 |

### 4b. Features worth trying (each needs your approval to patch and flash)

Ranked by value, risk and effort (02):

1. **Recording limit, a 2-byte test.**
   - The E-P7's patch has an exact E-PM2 counterpart: `mov 1740,a3` at 0x7E6EDF20 and `mov 7200,a3` at 0x7E6EDEE0 [V].
   - The gain is small. 4 GiB per file binds first at 1080 Fine (26.6 min). 1080 Normal would reach 30.9 min, 720p Fine 39.4 and 720p Normal 49.6 [V/I].
   - A second 30-minute cap in the movie library (`ulMaxRecTime` 1,800,000 at 0x7E6D82EF) may also apply. One test clip at 720p Normal past 30:00 decides it.
2. **A movie clip on the Portra slot already flashed.** This needs no flash, and it tests whether art-filter looks apply to movies.
3. **Soft Focus ("bloom") on the Portra slot:** one byte in Cross Process's effect list (`00 02 04 03` at 0x7E849E44 [V]).
4. **Look tables:** a log-like curve in Cross Process II, six-axis hue probes, Blacks/Whites and split toning. All are data-only, using the proven Portra method.
5. **The LCD panel table** (0x7E8DDDBC → RAM 0x602AD8FC), only if a colour cast is seen. Its neutral row is flat, so the E-P7's cause does not apply.
6. **Low or not feasible:** XPan/21:9 (the E-P7 needed 145 edits; our crop tables are unmapped), grain, clarity and halation (new code), 12-colour HSL and COLOR profiles (no E-PM2 stage), true log.

### 4c. Testing (needs your approval)

- **om-emu (JavaScript)** could run single E-PM2 functions with a local E101 model entry (estimated 1–2 days).
  - That is enough to compare stock and patched readers of a table, as the E-P7 tests do.
  - A kernel bring-up would take weeks; the GUI would take months.
  - It needs node ≥ 26 (we have 22) and running their code.
  - **No licence**, so use it locally only, copy no code, and ask the author before reusing anything.
- **oly_fw_analysis's GNU-simulator runner** (GPL-3.0) gets about 300 E-PM2 multiply sites and the float helpers wrong. It is not recommended.
- **Our own minimal MN103 function emulator.** No external code is involved and our own disassembler already decodes the instruction set. It is the cleanest path for data-edit and small-routine tests, at an estimated effort of days.

## 4d. Done 2026-11-12: om-emu runs E-PM2 functions

`tools/emu/` runs single E-PM2 functions in om-emu (at ~/opt/om-emu, Node 26 at ~/opt/node26), stock against patched. See tools/emu/README.md.
- **Recording limit:** the routine 0x7E6EDE08, 48 cases. A 1740 → 3600 edit changes exactly the 6 rows stock clamps at 1740 s; each new value is the 4 GiB cap.
- **Tone-curve selector** 0x7E56E837: `film-portra.json` also changes art codes 9/13/55/129/133, which share Portrait's Contrast-0 table. Trace those before flashing it.

## 5. Proposed order

1. **Now, our own code (no approval):** items 4a.1–4a.4 and 4a.6, which make every future flash safer, and the docs/flashing.md limits in §3. Then 4a.5, 4a.7–4a.10.
2. **Then, your decision:**
   - (a) the recording-limit test build and clip;
   - (b) whether to write our own function emulator or run om-emu locally;
   - (c) whether code patches (not just data edits) are in scope.

   The film-portra work already changed the project from mapping only to data patches.
3. **Camera tests, each one flash, each with a restore file ready:**
   - the zero-write rejection test (a deliberately bad checksum must be refused);
   - the rec-limit test;
   - the Soft Focus byte.

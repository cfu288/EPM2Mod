# 06 — Corrections to our docs, and the ordered probes (2026-11-17)

Companion to [05](05-imaging-pipeline-and-limits.md). Labels as there: [V] read in our bytes or run in the emulator, [C] camera, [I] inferred, [?] needs a camera. Nothing here changes a file outside this folder. The corrections are a list for the owner to apply.

## 1. Corrections

| Where | Says | Should say |
|---|---|---|
| `docs/feasibility.md`, "Real limits" | "No 3D lookup table; the hue stage has six axes" | No 3D LUT [V]. The stock still pipeline also has a **12-region H/S/L stage** (0x7E56E661), used for every still and RAW Data Edit, not in live view or standard movie (05 §4). |
| `docs/feasibility.md`, "Unknowns" | "tables at a RAM address untested" | Right as a test status, but the risks are the firmware's caches, CPU1 coherency and 4-byte alignment, not the address (05 §5). |
| `docs/feasibility.md`, boot loop | no evidence | Add: a forced hang in a Usr1-only function (first function of segment 2, 0x7E8F5800 `80 64` → `ca 00`) hangs the emulator's normal boot while `update-path-test` still passes. Hardware recovery is still unrecorded (§4). |
| `experiments/2026-11-11-caduceus-review/README.md` §4b.6 and `02-features-portability.md` | "12-colour HSL and COLOR profiles (no E-PM2 stage)" | The 12-region engine exists. The COLOR **editor** (wheel, per-sector menu, a path from user values to the builder) does not. |
| `experiments/2026-11-14-feasibility/firmware.md` | row "per-hue stage with more than six axes: no"; fread command 0x10004 | 12-region stage exists; fread posts **0x10005** (0x7E5C536F, `mov 0x10005,d1` at 0x7E5C5380). Add fseek whence 2 = SET, 0 = CUR, 1 = END. |
| `CODE_DIG.md` §3 (mask 0x80) and NOTES §16.2, §37.1, §13a §3.3 | "value pairs", "does not apply to 85", Muted six-axis fits mixed with record 3 | Mask 0x80 is the 12-region stage. Code 85 uses Natural's table A. Muted differs from A only in the mask (0x387, record 3 off) [V]. 0x7E560B40 also builds the i-Enhance table. |
| `docs/code-space-map.md:32` | the two cache-alias helpers | 0x7E45DAEF/DAF1 convert **to cached**; 0x7E45DB35/DB37 convert **to uncached**. |
| `docs/code-space-map.md` §1 | one "copy site" mechanism | Segment 1 is a direct `call 0x7E4217E6` (0x7E44A080). Segments 2/3 and usr1-third go through the mailbox wrapper 0x7E451306 (calls at 0x7E504C18, 0x7E504D6B, 0x7E504FCD). [V, end words re-read] |
| Section 03 §9, 09b, 13f | ART_IMG_CF fed by star pass 5; task id 0x808B; kernels on "MAIN TASK"; CHCTR | Star **pass 10** (0x7E71F7CF → 0x7E722796); ART task id **0x808A**; kernels 1, 3, 4, 6 run in ART_SUB on CPU1 (0x900B), kernels 2 and 5 inline on CPU0; CHCTR is at 0x8070 and there is no ranged flush. Clock 0 = 162 MHz [V]; the core is 162 or 324 MHz [?]. |
| "every film slot is an art code, so a CPU pass can join the art chain" | | True only for codes with a module or with an art effect on. Film codes need the `art_IsSupportType` hook (05 §7). |
| `experiments/2026-11-15-log/NOTES.md` | GUI and T_GUI run in CA_MAIN; 0x7E449605 | CAM_APP **task 0x98** (entry 0x7ECE6952); 0x7ECDF6E4 is a call site inside the setter 0x7ECDF5E9; 0x7E449605 is OlyTaSS (sleep), OlyTaDl is 0x7E449515. |
| `experiments/2026-11-16-films-max/NOTES.md` | §3.1, §3.2, §3.3 | Code 92 is clean. 113's entries are Soft Focus's (nine tables, three hashes). Code 200 gives no live-view anomaly [V]; add the hook sizes and the 31-key rule; add the show-flag table 0x7E826AFC and bound at 0x7E703FD3. cht (130 B) and jpn (234 B) text pools are tighter than kor. |
| Peaking NOTES §17.1 | cost of one access: unknown | About 0.43 µs per uncached word read in live view [C, `pk_stats`]; the 4×2-block loop costs 33–37 ms per frame. |
| Brief to the agents | 248 callback records; +20 a count/item/set callback; 90 and 110 label kinds | 250 records; +20 is a list-variant key; 90 and 110 are info ids. |
| `docs/space-superseded.tsv` | lacks `patches/peaking-direct-3.json` | add it, or `freespace.py area` counts its 65 B as used. |
| `tools/freespace.py check` | prints seven-fixes-1 as 16 B | the op is 17 B (the last byte equals 0xFF in both stock and the patch). |
| `tools/disasm.py --fw` | | leaves an empty cache file in `build/blocks` when given a non-firmware file. |

Not recorded anywhere yet: the 117,760 B blob cap (`cmp 117760` at 0x7E6752EC); the art neutral override (0x7E702D54, `cmp 100` at 0x7E702D5D); the 76 dormant tags and the 11 with no info id.

## 2. Film code 85 with its own 12-region table: three data edits [V emulator]

The change is data only on `films-12d`. An emulator sweep of 446 runs showed only the two code-85 rows change (set 0x7E78BE68, table 0x7E77B058, mask 0x801).

| What | Address | Before | After |
|---|---|---|---|
| Hash slot 15 (key 77 = 85 − 8; slot 13 is used by code 21, slot 14 by 149) | 0x7E78C75C | `00000000 dce5567e` | `4d000000 c1e5567e` (stub 0x7E56E5C1) |
| Set pointer | 0x7E78BE68 | `7432787e` | `58b0777e` |
| New table | 0x7E77B058 (orphan copy of A) | | edit only the changed records and the mask at +3024 |

Stub 0x7E56E5C1 is the Cross Process II stub and is unreachable in `films-12d`. Code 87 needs key 79 in slot 16. Before offering the build, rerun the sweep, and check that 0xA07500B0 is set and that 0x7E5501AF reads table+336.

## 3. Card-read probe (debug build only)

On `debug-log-films-12d`:
- hook at FLUSH entry 0x7EBF2C00: `cf f0 f8 fe c0` → `jmp RDP` (`dc e8 e2 0b 00`);
- RDP at 0x7ECB0EE8, 175 B, in the 281-byte segment-2 run, once per boot (flag byte 0xBE4FD0A8): `fopen("C:\EPM2LOOK.BIN","r")`, `fread` 512 B into 0xBE4FD0C0, `fclose`, CRC-32, `log_put(6, crc, bytes)`, then re-run the displaced instructions and `jmp 0x7EBF2C05`;
- add event 6 `card_read` to `logs/events.json`; keep the old dictionary.

Test: put a 512 B or longer file at the card root, boot, press MENU twice, power off. Expect crc = host CRC-32 and bytes = 512.

## 4. Boot-loop recovery

[V, emulator] With `OM_EMU_NODE` set and `EMU_IMAGES`/`EMU_TMP` in scratch:

| Image | `boot-test` | `update-path-test` |
|---|---|---|
| `builds/films-12d.json` | pass | pass |
| scratch variant, 0x7E8F5800 `80 64` → `ca 00` (sha256 65ae1b85…8562) | **fail**: hangs at 0x7E8F5800 | **pass** |

What it proves: the update path (reset → kernel → boot task → Usr0 → branch 0x7E504A59 → FIRMUP) executes only kernel and segment-1 code. Usr1 and segments 2/3/usr1-third are never copied on that path, so a hang confined to them does not affect it. Every updater function is in the kernel or segment 1.

What it does not prove: the real flash write, a watchdog (a hung normal boot may reset into the same hang until OK is held), or corruption of the kernel, segment 1, `.data` or Usr0.

**Safe for the updater:** a hook in segment 2/3/usr1-third that jumps into code also in those segments, or a hook in kernel/segment-1 code that runs only on the normal-boot application path, to code already loaded.
**Not safe:** a kernel/segment-1 hook on the reset→Usr0 path, especially one jumping into segment 2 (the `peaking-direct-2` failure).

**Do not edit** 0x7E44A076 or 0x7E421203: both run on the update path.

**Load extension [V static].** Raising 0x7E504D5E from 0x7F034000 to at most 0x7F05C000 (+160 KB) is safe in code terms: the reader has no size cap, no checksum and no partition bound (only a fixed remap above 0x2C0000), the extra range ends exactly at overlay-A, and the updater writes all of block 0 including 0xFF gaps. Code placed there loads only on a normal boot. Probe: +4 KiB with a pattern, then +64 KiB, logging the sums.

**Owner's decision.** The one thing static work and the emulator cannot settle: flash a build that loops only in normal-boot code, then recover with OK held at power-on and the stock file. This needs the owner's agreement (`AGENTS.md` rule 3).

## 5. Ordered probes

Static, no camera:
1. Re-run the builder 0x7E56E661 on the pinned build for every film code (done for stock and `films-12d`: 446 runs each).
2. Decode the helper 0x7E56A8B7 (its return value feeds the stage cache keys; not needed for the bank flip).
3. Trace the op-28 constant writer, and which pipe each movie case uses beyond the camoff cases listed.

One flash each, data only:
4. The three edits in §2 for code 85, to start the exact per-film 12-region fits.
5. The Cross Process II hue/saturation/clamp builds in 05 §8, with live view and a short clip in the same session.

One flash each, debug build:
6. The card read (§3), the half-press log, the clock timing probe.
7. A RAM bank for one slot's curve; RAW Data Edit pixel-identical.

Code builds, only after the above:
8. Code 92 as type II of an entry that has types (the 13th look).
9. Card-loaded looks with two banks and the 0xA07500B4 refresh.
10. The art-route hook for grain or halation, if wanted.

Boot-loop recovery on hardware: only with the owner's agreement.

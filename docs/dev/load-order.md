# Load order, space and what they cost

What we know about how the E-PM2 firmware gets into RAM, the rule that follows for patch code, the space that is
left, and the effects on speed and stability. State: 2026-11-25, build `cold-start-fix` (a candidate, not flashed by
the owner).

Labels: **V** verified (bytes, disassembly, an emulator run, a camera log, a stopwatch), **I** inferred, **U**
unknown. Emulator times are lab times, not camera times. History is in the notes that each section links.

## 1. The segments

Block 0 (14,155,712 B, runtime address = 0x7E421020 + file offset) is copied to RAM in steps. All rows: V static,
[code-space-map.md](../reference/code-space-map.md) §1.

| Region | Runtime range | Size (B) | Copied by | When on the camera |
|---|---|---|---|---|
| pre-reset | 0x7E421020–0x7E430000 | 61,408 | the loader outside block 0 | before the reset code runs |
| kernel range | 0x7E430000–0x7E4C9800 | 628,736 | reset code, site 0x7E421228 | just after the timer's zero |
| data image, SRAM image | 0x7E8DA000–0x7E8F3114, 0x7F14B000–0x7F14B820 | 102,676, 2,080 | reset code | after the kernel copy |
| segment 1 | 0x7E4FE000–0x7E881000 | 3,682,304 | boot task (CPU0 task 1), site 0x7E44A080 | before Usr0 |
| segment 2 | 0x7E8F5800–0x7ECB1000 | 3,913,728 | task Usr1 (0x52, priority 11), site 0x7E504C18 | started by Usr0 on a normal start only |
| segment 3 | 0x7ECCB800–0x7F034000 | 3,573,760 | Usr1, site 0x7E504D6B | after segment 2 |
| usr1-third | 0x7F100000–0x7F119000 | 102,400 | Usr1, site 0x7E504FCD | after segment 3 |
| overlays A, B | 0x7F05C000–0x7F06B000, 0x7F080000–0x7F0EB800 | 61,440, 440,320 | Usr2, on demand | not at start |
| not loaded | the rest of block 0 | 1,586,842 | nobody | never in RAM |

"Early-loaded" below means pre-reset, kernel range, the two images and segment 1. "Late-loaded" means segment 2,
segment 3 and usr1-third.

Blocks 1, 2 and 3 (languages and fonts, the Grainy Film texture, the frame pictures:
[firmware-format.md](../reference/firmware-format.md)) are not part of these copies. When the firmware reads them
is U.

Times, from the Debug Log (the timer's zero is the reset code's fourth step, before the kernel copy, V static):

| Event | Time | Label, source |
|---|---|---|
| First firmware error record (T_ERR, hook in the pre-reset range) | 19.5 ms | V log, `experiments/2026-11-15-log/evaluation-1.md` §2.1 |
| `boot` (T_BOOT, at Usr0's entry 0x7E503DD4) | 101 ms | V log, same |
| `pk_heap_mode`, `lv_values` (Usr0) | 209 ms, 215 ms | V log, same |
| `seg_loaded` (first line of T_CTOR, after the segment-3 copy) | 0.33 s body B, 0.362–0.365 s body A | V log, [slow-boot notes](../../experiments/2026-11-24-slow-boot/NOTES.md) §4, `experiments/2026-11-21-firmware-dive/build.md` |
| First colour stage job (`film_stage`) | 1.6–2.9 s | V log, slow-boot notes §8 |
| First GUI state 0x1001, live view 0x5000 | 0.5–2.2 s, 1.8–3.7 s | V log, slow-boot notes §4 |

What runs before each copy ends:

- Before segment 1 is in RAM: the reset code and the kernel. The mod has one hook there, T_ERR (0x7E426D4B, to
  kernel-range code). V static.
- Between segment 1 and the end of Usr1's copies (about 0.1 s to 0.33 s): all of Usr0, and the quick start. Usr0
  sets "Flg-ThroughStart" at 0x7E504A47 before it starts Usr1. The task USR_FAST (priority 6) then starts live view
  and preempts Usr1 (priority 11). Nothing waits for the copies. V static,
  `experiments/2026-11-21-firmware-dive/NOTES.md` §2. So live-view code of segment 1 can run while segments 2 and 3
  are not in RAM. V on a contributor's camera (issue #6).
- After each of its copies Usr1 calls the constructor walker 0x7E44B6B0. The last entry of segment 3's table is the
  first point where code can know that segments 2 and 3 are loaded. V emulator, same notes.

The copy takes about 1 ms in the emulator and about 0.1 to 0.2 s on the camera (I, from `lv_values` at 0.21 s and
`seg_loaded` at 0.33 s). The emulator has no live view. So the emulator cannot show a race in this window. V,
slow-boot notes §3.

A start that kept RAM: after a short power-off the RAM still holds the segments of the last start, so a jump into
a segment that is not yet copied finds the right code. After a long power-off (45 s or more in the issue's report)
it finds noise. V for the log's ring RAM (kept across power-off, bits can turn while off,
[feasibility.md](feasibility.md)); I for the segments. A race in this window therefore shows only on a cold start,
and only on bodies whose live view starts early enough. The owner's two bodies do not show it. U: why bodies differ.

The update path (OK held, update file on the card): the reset code, the kernel, all of Usr0, the updater
(0x7E5434EA–0x7E544A9F, 0x7E8808C0–0x7E880E84) and the file system run. Usr1 does not run, so segments 2 and 3 are
never loaded. V static and V emulator (`emulator/update-path-test`). Mod code that runs there: T_ERR, T_BOOT,
`lv_values`, the heap hooks of peaking. V emulator, slow-boot notes §1. A fault in anything Usr0 runs makes the
updater unreachable, and this body has no recorded recovery from that ([feasibility.md](feasibility.md)).

## 2. The rule

A transfer is a `jmp` or `call`, a word of a jump table, a task's entry word, or any other stored code pointer.
It also covers a data read: early code that reads a table in late-loaded space reads noise in the same window.

| From | To | Verdict |
|---|---|---|
| anywhere | pre-reset, kernel range, segment 1 | **Always safe** for the load order. V static: these are in RAM before any code that can use them |
| segment 2, segment 3 | segment 2, segment 3, or early-loaded space | **Always safe**: late code runs only after its own copy. One limit: segment-2 code that runs from the constructor walk after the segment-2 copy must not use segment 3. I |
| early-loaded | late-loaded, where the code shows that the path starts only from late-loaded code | **Safe by proof.** Example: the entry words of the tasks 0x90 and 0x91 (kernel data) point into segments 3 and 2; only T_GUI in segment 2 starts those tasks. V static |
| early-loaded | late-loaded, where the path needs something the application does (a capture, a movie frame) | **Safe by inference.** The reading of the code can be wrong; say so in the allow list. I |
| early-loaded | late-loaded, on a path that Usr0, the quick start or live view can take | **Unsafe.** It works on a start that kept RAM and on bodies with a late live view, and restarts the camera on others. On a path that Usr0 takes it is a crash at every start and on the update path |
| early-loaded | late-loaded, accepted because the camera's logs show the code runs later | **Safe by timing only.** This is the unsafe row with a measured margin. The margin is from two bodies and from starts in P. Treat each such row as an open risk (§5) |
| anywhere | overlays, not-loaded space | Unsafe unless the code loads the overlay first. No spec does this. V |

How to stay on the safe side: put new code in segment 2 or 3 and hook it from segment 2 or 3. When the hooked
function is early-loaded, put the routine in early-loaded space too. Code that must run at start uses an entry of
segment 3's constructor table. `emulator/hookcheck.py` lists every constant transfer of a build's patched
early-loaded bytes; `emulator/hookcheck-allow.tsv` holds the accepted ones with their evidence.

### Worked example 1: `peaking-direct-2` (withdrawn 2026-11-14)

The hook 0x7E7149B6 is in the heap mode chooser, a segment-1 function. It jumped to 0x7EBF1F74 in segment 2. The
boot task calls that function during Usr0 (first run at 16.4 ms in the emulator, before the segment-2 load call at
25.8 ms). Verdict by the table: unsafe, on a path Usr0 takes. `emulator/boot-test` showed the crash before any
flash. V emulator, [camera log](../camera-log/2026-11-14-peaking-direct-2.md). The fix moved the routine to the
kernel range (`peaking-direct-3`, then `-4`).

### Worked example 2: issue #6, `peaking-mf` (releases 2026.11.20-rc.3 to 2026.11.20)

The chain: 0x7E6ECF91 (segment 1, end of the live-view struct refresh 0x7E6ECCAF) `jmp` T_A (kernel range) →
`call` T_R (kernel range) → `jmp` T_MF 0x7ECB0B81 (segment 2). T_MF is 1,151 B before the end of the segment-2
copy. The refresh runs at each live-view struct refresh, with any Peaking setting. Verdict: unsafe, on a path live
view takes. On a cold start the camera restarted, found its RAM kept, and started: about 10 s. V on a
contributor's camera; not seen on the owner's two bodies. Three checks missed it:

- `emulator/hookcheck.py` decoded each spec's own bytes. `peaking-mf` wrote its jump into the code of an earlier
  spec, so the check saw the earlier spec's bytes. Repaired 2026-11-25: it decodes the built image. V.
- `emulator/boot-test` and `update-path-test` passed, and pass today: the emulator has no live view. V.
- The camera test ran on bodies that do not show it.

The fix `peaking-mf-2` puts T_MF in segment 1 (61 B). Details: slow-boot notes §8.

## 3. Space

Free bytes of `cold-start-fix`. "Proven" means a camera-tested build runs code in the area. "Static" means the
area passes every check of `tools/freespace.py` and no code has run there. Sources: `uv run python
tools/freespace.py check` on the build's specs and `freespace.py area` (V tool, 2026-11-25), slow-boot notes §8,
`experiments/2026-11-21-firmware-dive/NOTES.md` §1, `experiments/2026-11-13-reclaim-space/README.md`.
[code-space-map.md](../reference/code-space-map.md) was generated for an older build: its totals are out of date.

| Region | Area | Size | Used by the mod | Free, proven | Free, static only | Reclaimable, and the cost of a mistake |
|---|---|---|---|---|---|---|
| kernel range | blank run 0x7E4C90CA–0x7E4C9800 | 1,846 | 1,824: `log-menu-3` 751, `peaking-direct-4` 420, `peaking-colours` 292, `peaking-fast` 149, `interval-frames-240` 128, `custom-menu-rows-4` 76, others 8 | **22**, in three pieces | 0 | G2 0x7E440010–0x7E448000, 32,752 B of 0xFF: no access in the emulator (V); it is CPU1's vector page (I). The copy's end word can grow by 26,624 B. A mistake in either can stop every start and the update path |
| segment 1 | exp debug printers 0x7E69E9EA–0x7E69EEAF | 1,221 | 993: `lss-core` 641, `spot-core-2` 291, `peaking-mf-2` 61 | **228** (227 in one run) | 0 | four text runs, 12,739 B, found by the automatic rule only; 238 B of code with one caller each. A mistake shows on the update path too |
| segment 1 | blank tail 0x7E880F5C–0x7E881000 | 164 | 26: `peaking-direct-3` | **138** | 0 | none |
| segment 2 | `sdk` name list 0x7EBF1090–0x7EBF3BAD | 11,037 | 10,061: `interval-frames-240` 3,584, `level-adjust-row` 1,906, `custom-menu-rows-4` 1,525, `log-menu-3` 1,399, `stock-films-structure-3` 980, others 667 | **976**, in small pieces | 0 | the `sdk` shell handlers 0x7E9A171D–0x7E9BFA7E, 123,745 B: dead once their table words point at a stub (V static). A mistake is recovered by a card update |
| segment 2 | blank tail 0x7ECB0888–0x7ECB1000 | 1,912 | 1,832: `interval-timelapse-v2` 831, `stock-films-structure-3` 761, `card-looks-9` 240 | **80** | 0 | |
| segment 2 | Bluetooth strings 0x7EBB1F4C–0x7EBB304C | 4,352 | 3,029: `lss-menu` 2,936, `build-label` 93 | 0 for code | 1,323 (data) | |
| segment 3 | seven runs of dead 3D helpers, and the blank tail 0x7F033B7C–0x7F034000 | 8,274 | 7,149: `card-looks-9` 4,550, `stock-films-structure-3` 1,352, `custom-menu-rows-4` 752, `gauge-info` 335, others 160 | the tool's verdict is "data"; `card-looks-9` runs code in two of them (V camera) | 1,125 | as segment 2 |
| not loaded | 1,586,842 B | | 0 | 0 | 0 | needs a longer load range: U |

The build changes 25,796 bytes of block 0 in all (V, `epm2mod make`).

Bottom line: **the pressure is in early-loaded space.** 22 B are left in the kernel range and 366 B in segment 1
(228 + 138), in three runs. Late-loaded space has about 1 KB proven free in small pieces and 124 KB that one
table edit frees. Every hook into an early-loaded function needs its routine in early-loaded space (§2), so each
such feature spends from the 388 B. A routine in segment 1 for the colour-stage hook 0x7E56C6A5 (§5) needs 219 B of it (`TODO.md`). The next
candidate for early-loaded space is a hand check of one of segment 1's text runs (3,357 B at 0x7E79944E is the
largest), ranked before G2 because a wrong verdict there costs a feature, not the start: I.

## 4. Speed and stability

### Start-up time

- Stock against the mod on the camera: not measured. In the emulator the first GUI state (31.3 ms) and the start
  of live view (293.2 ms) are the same for stock and `peaking-mf`. V emulator, slow-boot notes §3.
- T_CTOR applies the stored film simulations in Usr1 after the copies: 68 ms on the camera (`seg_loaded` 0.362 s to
  `film_applied` 0.430–0.433 s), 17 ms in the emulator. V log, `firmware-dive/build.md`. It is the one measured
  start-up cost of the mod. Live view still starts 1.8–3.7 s after the timer's zero, cold or kept. V log.
- T_ERR, T_BOOT, the heap hooks, `lv_values`, the Lowest S/S hooks: each a few tens of instructions per run; no
  time measured on the camera. With Debug Log Off a probe costs about 25 instructions (I, static estimate,
  `experiments/2026-11-18-log-menu/design.md`).
- `boot-test` reports moved time stamps as `TIMES MOVED`. It found a loader task that delayed the start by 5.5 ms
  (priority changed from 11 to 13). V emulator, `experiments/2026-11-17-card-looks/design.md`.

### Per frame in live view

- Peaking, Red: median 100 ms per frame (85–126), of which the peaking code takes 36 ms; White: 100 ms with 0 ms
  of peaking code. The firmware's plan is 85 ms per frame, so 10 frames per second at most. V log,
  [camera log](../camera-log/2026-11-15-peaking-fast.md), `experiments/2026-11-14-focus-peaking/NOTES.md` §17.
- Peaking in MF the whole time (`peaking-mf`): "smooth enough" (owner). No frame rate was recorded.
- Not measured: the latch T_A per struct refresh (about 30 instructions in the function harness, V emulator), the
  spot window hook of `spot-core-2`, the two colour-stage hooks, the Lowest S/S hooks.

### RAM

All of the mod's RAM is in the gap between the kernel range and segment 1 (0x7E4C9800–0x7E4FE000).

- Film tables: 0x7E4D1000, 0x3200 B per entry, 12 entries (153,600 B). V camera 2026-11-18.
- Log: 0x7E4F9000–0x7E4FD2C0, 17,088 B: two rings of 512 records, the state block PST (128 B), a 512 B block
  buffer. A ring fills in about 100 s of peaking. V static and V log, `experiments/2026-11-15-log/NOTES.md`.
- Heaps: peaking forces image-work heap mode 1 while its latch is set. The save guard holds the old mode while a
  still block is in use. No own heap. V code, focus-peaking notes §12 and §18.
- Tasks 0x90 and 0x91: stack 0x800 B each from the kernel's pool. Stack use: not measured. T_CTOR uses 128 B of
  Usr1's 0x800 B. V static.
- A longer kernel load range (§3) would fill this gap with 0xFF at each reset. V emulator, firmware-dive notes §1.

### Flash, EEROM and card writes

- At start: none by the mod. V specs, slow-boot notes §1.
- EEROM settings bank (the 53,680 B tail holds the look pack): written by Load Looks when a byte changed, through
  the firmware's bank save 0x7E680272, which writes the whole 64 KiB bank to the other of two copies. V code,
  `experiments/2026-11-17-card-looks/design.md`. Wear: not assessed.
- Card: `EPM2LOG.BIN`, only with Debug Log On, at a menu, playback or power-off state. V log.

### Failures seen, and what caught each

| Failure | Cause | Caught by | Would have caught it earlier |
|---|---|---|---|
| `slots7-code`, `slots7-kind`, `remap7-code` (2026-11-12): live view froze in three filters | live view's own art tables disagreed with `art_GetFilterType` | camera | `emulator/filmcheck.py` and `liveview.py`, written after |
| `peaking-direct-1` (2026-11-14): slow, two crashes | heap not in mode 1 | camera | a scenario run (S-series), written after |
| `peaking-direct-2` (2026-11-14): crash at every start | example 1 | `boot-test`, before any flash | |
| `peaking-direct-3` (2026-11-14): crash on one film entry | a spec overwrote one byte of another spec's handler | camera | `emulator/opcheck.py`, written after |
| Restart at a focus-ring turn after a shot (2026-11-16) | heap re-divided under a still block in use | a user report and the log's ring | a scenario with a capture; the emulator takes no pictures |
| ART BKT crash at frame 1 (`films-start-texts-artbkt`, 2026-11-21) | recorded on the branch `feat/artbkt-production`, not on this one | camera | `emulator/artbkt-test` on that branch |
| Slow cold start (issue #6) | example 2 | users, on other bodies | the built-image `hookcheck.py`; a cold start on a body that shows it |
| Wrong menu texts outside English; a wrong look curve on the card path | English-only text patches; a handler that was not the identity | emulator crawls; a camera round | |

No restart loop and no failed update are recorded. V, `docs/camera-log/`.

## 5. Open risks

`emulator/hookcheck.py data/builds/cold-start-fix.json`: 190 transfers leave patched early-loaded code, 87 go to
late-loaded space, 0 FAIL. 2 are safe by proof (the task entries). 85 are from `stock-films-structure-3` and are
in the allow list as safe by timing only. V tool.

| Risk | What is known | Probe |
|---|---|---|
| **25 jump-table words of the hidden art values 111, 112, 114, 115, 118** (0x7E7FF034–0x7E7FF0A4, 0x7E807858–0x7E8078C8, 0x7E854A50–0x7E854A6C) | Result of 2026-11-25, V static: the words are cases of three switches, in 0x7E6CBFD3, 0x7E6DBA95 and `art_GetFilterType` 0x7E71BD94. Each switch takes a picture-mode value of 100 to 120 and does `jmp (a0)` through the table. **0x7E6DBA95 is called at 0x7E6ECD73 by the struct refresh 0x7E6ECCAF, the function whose end ran before segment 2 was loaded in issue #6.** The call is reached when 0x7E6DB43E returns 4 or 5 (meaning U). Film simulations are chosen with Picture Mode in P, A, S and M, and the quick start does not refuse them. So on a body that shows issue #6, a cold start with one of the five entries selected can jump into segment 2 before the copy: I. Whether it does: U. Emulator, `hookhits.mjs` on `cold-start-fix`, quick start off and on: none of the three functions, the colour-matrix step or the latch ran before the last constructor walk at 32.4 ms; the run then faulted (code 6; the run stored in the slow-boot notes did not; cause not looked at), so it says nothing after that. V emulator, and no evidence for the camera | Camera, on a body that shows issue #6, `cold-start-fix`: load a look pack, select the film simulation on Grainy Film in P with Picture Mode, power off 2 min, start. Twice. A start of 8 s or more, or a screen that lights twice: the risk is real. Then the fix is the stubs in segment 1 (space: §3) |
| **48 jump-table words of the colour stage** (0x7E78AEBC–0x7E78CB40) and **the two colour-stage hooks** 0x7E56C6A5, 0x7E546160 | First colour stage 1.6–2.9 s after the start, 1.28 s after the copies, on the owner's bodies in P (V log). Not measured: a start with the shutter held, wake from sleep, a body that shows issue #6. The function harness reaches both hooks' jumps directly (V emulator) | The same camera run: the log's first `film_stage` against `seg_loaded`. No extra flash |
| **10 hooks of the ART BKT frame composer** 0x7E5A75AE | Runs when an ART bracket picture is taken (V static); a capture needs the application (I) | Camera: ART BKT On, shutter held during a cold start. Low priority |
| **4 hooks of `movie-ab`** (not in this build) | movie frames only (I); never on the camera | with that build's camera test |
| The GUI state word before the first GUI state holds noise after a cold start | `peaking-mf-2` reads it: no lines until the first GUI state if it reads 0x5101 (I) | seen or not in the cold-start run above |
| Segments kept in RAM hide a race | a test start after a short power-off proves nothing about the load order (V, issue #6) | every load-order camera test uses 2 min off, or the battery out |
| The emulator's copy takes 1 ms and it has no live view | it cannot show a race between live view and Usr1 (V) | a function harness with late-loaded RAM filled with noise, as `experiments/2026-11-24-slow-boot/scripts/emu_cold.py` |

One more emulator result of 2026-11-25 (V emulator, a trial script, not kept): each of the 70 jumps and calls
that enter changed bytes from early-loaded code was run from its own address, with late-loaded RAM as built, as
0xFF and as random bytes. `cold-start-fix`: no run reached late-loaded space but the 13 that end at an
allow-listed jump; the three fills gave the same result in every run; 42 of 57 ran to a return. `spot-af-2` and
`peaking-mf`: three entries reached 0x7ECB0B81, among them the real hook 0x7E6ECF91. The registers and RAM of
these runs are not the camera's, so a clean run covers one path only.

## 6. What a future check could look for

Ideas only. Nothing here is built.

- **Run the load-order check on every build a branch changes,** not only on the pinned build. `freespace.py check`
  already calls `hookcheck.py`, and `epm2mod make` calls it for a candidate; CI calls it for the pinned build only.
- **A class per allow-list row** (proof, inferred, timing), and a report that prints each timing row a build uses
  with its evidence, so a reviewer reads them in every PR.
- **Jumps through a register and data reads.** `hookcheck.py` sees constant targets and changed stock pointers.
  It does not see a pointer in new early-loaded code or a read of a late-loaded table. A scan of the patched
  early-loaded bytes for any word that is a late-loaded address (in all four aliases) would list both.
- **A cold-RAM run of each hook** in the function harness, as the trial in §5: differences between "copied" and
  "noise" show a use of late-loaded memory that no static scan sees. It needs real state per hook to cover more
  than one path.
- **Callers, not only hooks.** Example 2 and the first row of §5 are both reached from one early function. A list
  of the early-loaded functions that Usr0, USR_FAST and live view can reach before the last constructor walk
  (from the call graph in `build/map/calls.tsv`) would turn "runs when" from a reading into a table.
- **A cold start in the camera test of a build that touches early-loaded code:** 2 min off, and one body that is
  known to show issue #6.
- **Free early-loaded space as a number in the report,** so a PR shows what it spends of the 388 B.

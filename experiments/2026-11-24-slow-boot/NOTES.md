# Slow cold start, GitHub issue #6 (2026-11-24)

The report: on 2026.11.20 (also rc.4 and rc.5) a cold power-on takes 10–12 s until the camera can shoot. Stock is fast.
A start within about 30 s of the last power-off is fast; after 45 s it is slow again. EVF, lens, Load Looks, Debug Log,
the card and its files make no difference.

Labels: V verified (bytes, disassembly, an emulator run, a log or a stopwatch), I inferred, U unknown. Emulator times are
lab times, not camera times.

## Result

- **Leading cause (I): peaking-mf's jump into segment 2 runs before segment 2 is in RAM.** Since rc.3 the peaking latch
  T_A, which runs at every live-view struct refresh, calls T_R in the kernel range, and T_R now starts with
  `jmp 0x7ECB0B81` (peaking-mf's T_MF, segment 2). The quick start begins live view while Usr1 still copies segment 2.
  After a short power-off the RAM still holds segment 2 from the last start, so the jump finds the right code. After a
  long power-off the RAM has decayed, the jump runs garbage, and the camera starts again. The second start finds the
  RAM kept and works. This fits every point of the report. It is not proven on the camera.
- Every complete start in the owner's logs reaches live view 1.8–3.7 s after the timer's zero, cold or kept, on both
  bodies (V). A 10 s start is not inside one logged start.
- On body B every cold power-on in the log is a start that ends at 0.21 s, during the segment copy, followed by a start
  with RAM kept (3 of 3, V log; that each was one press is U).
- The emulator cannot show the fault: it has no live view and its segment copy takes about 1 ms (section 3).
- Probe build `slow-boot-probe` (section 6), sha256 `e783fbe686fc774a17b64590c8bd986ff1259bb84d189b703c5efc478aa675ca`.

## 1. What runs at start-up, and what only a cold start changes

Hooks that ran before live view in the emulator (`scripts/hookhits.mjs`, `results/emu-hook-hits.txt`, V emulator):

| Site | Spec | What it does | Runs before LV (lab ms) |
|---|---|---|---|
| 0x7E426D4B (pre-reset range) | log-menu-3 | T_ERR: logs each firmware error (8 stock records per start on the camera) | 36 |
| 0x7E503DD4 | log-menu-3 | T_BOOT at Usr0's entry: clears the log state block PST, logs `boot` | 1.9 |
| 0x7E7149B6, 0x7E4C9346, 0x7E578C60 | peaking-direct-4, peaking-save-guard, log-menu-3 | heap mode chooser and setter: peaking's heap rule and its guard, `pk_heap_mode` | 16.4, 17 runs |
| 0x7E459A5F (kernel) | log-menu-3 | `lv_values`: the accelerometer table reload | 16.8 |
| 0x7E693D4B, 0x7E694610 | lss-core | Lowest S/S: exposure program | 216, 19 runs |
| 0x7EB7D43B, 0x7EB7D44C | peaking-direct-4, log-menu-3 | MF Assist end, once per start (`pk_mf_end`) | 218 |
| 0x7E995A0B | log-menu-3 | `shoot_cbs` | 240 |
| 0x7EE538D1, 0x7ECDF6E4 | log-menu-3, card-looks-8 | film loader task end; the GUI state hook (from the first GUI state) | 31–38 |
| constructor entry 0x7F033B78 | card-looks-8, log-menu-3 | T_CTOR: `seg_loaded`, the stored film simulations applied (about 60 ms on the camera), `film_applied` | 23 (end of the copies) |

The emulator has no live-view frames, so these camera-only hooks never ran there: the peaking latch T_A (0x7E6ECF91),
the expose setter probe (0x7E6C610B), the other peaking-direct-4 hooks in the mov layer, the film stage probes and the
two film hooks into segment 2 (0x7E56C6A5, 0x7E546160). Full list: `results/hook-sites.txt` (73 hook sites, V static).

What only a cold start changes, item by item:

| Item | Finding | Label |
|---|---|---|
| Log ring | A ring whose check fails is started again: a few stores. Before T_BOOT the log reads its switch byte from PST, garbage on a cold start: at worst records before 101 ms are skipped | V code |
| Film store, card-looks | Applied from the EEROM bank tail in every start, cold or kept; RAM tables written, nothing read from RAM first | V spec, I |
| Peaking heap mode, level gauge | Read firmware state that the reset code fills (.data copy, CPU 1 clear) | I |
| Flash or card writes at start | None by the mod: the store is written only by Load, the log only at a menu, playback or power-off state | V specs |
| Waits | No mod code waits at start; the loader task (priority 13) and the flush task run after the first GUI state | V specs |
| Segment loading | Unchanged copies. **peaking-mf's T_R jumps from the kernel range to T_MF in segment 2** (disassembly below); T_MF is 3,912,577 B into the 3,913,728 B segment-2 copy, so it is among the last bytes copied | V static; copy order I |

The chain (V, `scripts/disasm_ranges.py` on the pinned block): 0x7E6ECF91 (segment 1, end of the struct refresh
0x7E6ECCAF) `jmp 0x7E4C920B` (T_A) → if struct+32 is 0 and 0x605B039C is not 1: `call 0x7E4C93A4` (T_R) →
`jmp 0x7ECB0B81` (T_MF). The jump does not depend on the Peaking setting or the focus mode. The live view starts before
the copy: the quick start's Flg-ThroughStart (16.8 ms) and lss-core's exposure hooks (24.7 ms) come before the
segment-2 load call 0x7E504C18 (25.8 ms) in the emulator with the quick start on (`results/emu-hook-hits-fast.txt`, V
emulator). `experiments/2026-11-21-firmware-dive/NOTES.md` §2 found the same statically; the peaking-mf notes (§3) said
T_R runs "long after" the load.

`emulator/hookcheck.py` did not see this jump: when two specs write the same site, it decodes the first spec's bytes,
not the build's (V: it reports peaking-direct-4's `jmp T_A` at 0x7E6ECF91 for the probe build, whose byte there points
at T_LV). The peaking-mf notes (§4) record "0 transfers" for the same reason.

## 2. Which release first had it

`scripts/release_specs.py` (V git):

| Release | Build | Added at start-up |
|---|---|---|
| 2026.11.18-rc.1 | card-looks-4 | films, peaking-direct-4 and its heap hooks, loader at the first GUI state, the 2 film hooks into segment 2 |
| 2026.11.18-rc.2 | stock-films | log-menu-2 (T_ERR, T_BOOT, ring), card-looks-5 |
| 2026.11.19-rc.1 … rc.4 | lss, epm2mod-2026.11.19, gauge-info-3 | lss-core; data only |
| 2026.11.20-rc.1, rc.2 | films-look-exif, films-twelve-off | film table changes |
| 2026.11.20-rc.3, rc.4, rc.5, 2026.11.20 | peaking-mf (one build) | card-looks-8 (film apply in the constructor table), log-menu-3, **peaking-mf** |

rc.3 to the final release are the same firmware, so "also rc.4 and rc.5" adds nothing. The first bad build is
inferred to be rc.3 (I). `data/builds/films-start-texts.json` (camera-tested 2026-11-21) is the pinned build without
peaking-mf and nothing else: the A/B test of section 7.

## 3. Emulator: cold and warm starts

`scripts/coldwarm.mjs` fills all DRAM (0x60000000–0x80000000, except what the first-stage loader leaves) before reset:
zero, 0xFF, random (2 seeds), and "warm" (the DRAM at the end of an earlier 4 s run). 8000 ms of lab time each.

| Image | zero | 0xFF | random | warm |
|---|---|---|---|---|
| stock | GUI 31.3 ms, LV 293.2 ms | same | same | same |
| pinned (peaking-mf) | same | same | same | same |

V emulator (`results/emu-*.txt`). Random DRAM adds only the stock console line "[damage info]:Not SUCCESS". With the
quick start on (`E101_FAST=1`) stock and the pinned build both fault at 260 ms (an emulator limit). The emulator cannot
show the suspected fault: no live-view frame comes, and its segment copy takes about 1 ms, so segment 2 is always in RAM
before any live-view code could run.

## 4. The owner's logs

`scripts/boot_times.py` (`results/boot-times-*.txt`). "Cold" = the session's first record starts a new ring, as
`epm2mod log` decides.

| Body, build | Kind | Starts | GUI 0x1001 (ms) | Live view 0x5000 (ms) |
|---|---|---|---|---|
| A, all builds (sessions 1–192) | cold | 45 | 1757–1779 | 2111–2315 |
| A, all builds | kept | 82 | 536–2209 | 2109–3718 |
| B, pinned (193–199) | kept | 2 | 530 | 3069–3118 |
| A, pinned, stopwatch test 2026-11-24 (`EPM2LOG-boot-timing.BIN`) | kept | 5 | 1466–1775 | 1822–2151 |

- Cold and kept starts have the same timeline on body A (V).
- Short starts: 69 of 199 sessions end without a record of their own. Most reach GUI 0x1001 at 0.48–0.53 s and go to
  0x2000 (power off). In the stopwatch test of 2026-11-24 three such starts came with no slow start: they are brief wakes
  that are not a power-button start (V stopwatch, owner). Their cause (card door, battery) is U.
- **Body B's three cold starts (193, 196, 198) are another kind:** the records end at `lv_values`, 0.212 s, before
  `seg_loaded` (0.330 s in its kept starts), with no GUI state. The next start has RAM kept. One of them (194, kept)
  ends after `film_applied` at 0.391 s; 195's first GUI state is at 105 s (V log; what the owner did then is U).
- Body B's cold runs reach `pk_heap_mode` and `lv_values` 8–10 ms later than its kept runs (V); the cause is U.
- Firmware errors: the 8 stock DMA records of every start; five 0x2400013E (session 105) and four 0x1400F001 come later
  in a session, none at start (V).
- The stopwatch test (owner, body A, pinned): about 2 s, live view 1.8–2.2 s in the log, so less than about 0.3 s of a
  start is before the timer's zero (V stopwatch, I for the margin). All 8 of its starts kept RAM, also after more than
  60 s off: a true cold start was not timed.
- The timer starts in the reset code's fourth step, before the kernel copy (0x7E421092 → 0x7E4262F0, V static).

Known defect of the decoder (`cli/src/epm2mod/eventlog.py`): the CPU 1 records of a session that was not flushed are
put into the next session with 2^30 µs added. The session lengths 1073.8 s, 2147.6 s and 3221.3 s in the summaries are
this. `boot_times.py` uses CPU 0 only.

## 5. Hypotheses

| # | Cause | For | Against | Label |
|---|---|---|---|---|
| H1 | peaking-mf's T_R → T_MF jump runs while segment 2 is being copied; garbage on a cold start, a restart, then a good start | the chain (V); live view starts before the copy (V static and emulator order); body B's cold runs end inside the copy window (V log); new in rc.3, the reporter's builds; independent of lens, card, looks and log; stock fast | body A's cold starts are fine (its lens set-up delays live view past the copy: GUI at 1.77 s, I); the 7 s restart time the report needs is U | I, leading |
| H2 | a wait before the main firmware (first-stage loader, body controller) on a true cold start | not excluded for a battery-out start | stock is fast; the mod changes nothing there; body A's stopwatch start leaves ≤ 0.3 s outside the log | I, weak |
| H3 | the two film hooks into segment 2 (colour stage, since rc.1) | same pattern | body B's cold runs have no `film_stage` record before they end; the first colour stage is 1.6–2.9 s after the start | I, unlikely |
| H4 | card-looks-8's film apply after the copy | runs at start | body B's cold runs end before `seg_loaded`, which comes first in T_CTOR | I, not the trigger |

A fix for H1 (not built): T_R must not reach segment 2 before the copy ends, for example T_MF and T_MF2 moved into
kernel or segment-1 space, or the jump gated on a flag that T_CTOR sets and T_BOOT clears.

## 6. Probe build `slow-boot-probe`

`data/builds/slow-boot-probe.json` = peaking-mf + `data/specs/slow-boot-probe.json` (made by `scripts/mkspec.py`).

- `lv_first` (id 2560), once per start: the peaking hook 0x7E6ECF91 jumps to T_LV (segment 1, 55 B in the free part of
  lss-core's area), which logs and jumps on to T_A. seg2 = the word 0x7ECB0B84 inside T_MF, seg3 = the word 0x7F033B74 of
  segment 3, both read uncached. seg2 = 0xA0602BE8 means segment 2 was in RAM at the first live-view refresh; any other
  value means the jump of H1 would run garbage in that start. It must be in segment 1: nothing in segments 2 or 3 runs
  before the copy. The flag is PST+104, cleared at every start by T_BOOT.
- `start_kind` (id 2561): segment 3's last constructor entry points at T_PW (segment 2, 42 B in movie-ab's old run),
  which logs the power-on factor, the wake reason and the quick start's state after Usr0 set them, then jumps to T_CTOR.
  It tells the brief wakes from power-button starts.
- Dictionary `afe27672…` → `3bb92179960f6978`; the flashed `8bf70fea…` list is kept as
  `data/logdict/events-8bf70fea0397b1f2.json`. `tools/space-ledger/superseded.tsv`: pana-ring-probe is history (this
  spec reuses its run and the flush task's id words).
- Checks (exit status 0, V): `uv run epm2mod make slow-boot-probe` (free space PASS), `emulator/hookcheck.py` on the
  build's specs and on the spec alone, `emulator/boot-test`, `emulator/update-path-test`, `scripts/emu_tlv.mjs` (T_LV
  logs once with the right words, again after the flag is cleared with 0xFFFFFFFF in T_MF, keeps every register and the
  flags; `start_kind` comes just before `seg_loaded`). `results/*-slow-boot-probe.txt`, `results/emu-tlv.txt`.
- Risk: T_LV is first code in that area of segment 1 (the free-space check says FIRST CODE). Segment 1 is on the update
  path, but T_LV is reached only from live view.

## 7. Camera tests

Body B is the body of sessions 193–199 of `EPM2LOG-slow.BIN`. Run each test on body B, then on body A if time allows.
Debug Log must be On: MENU → SETUP → Custom Menu → J → Debug Log → On → OK (`docs/user/debug-log.md`).

A start, every time: press ON/OFF once. Start the stopwatch at the press. Stop it when live view shows the picture.
Write down the time, and whether the screen lit, went dark and lit again.

The start list, in this order (one line per start in your notes):

1. Off 10 s, then a start. Twice.
2. Off 2 min, then a start. Twice.
3. Battery out for 2 min. Battery in. Wait 10 s. A start. Twice.
4. Battery out for 2 min. Battery in. Wait 10 min. A start. Once.

Then turn the camera off and copy the log (commands per test below).

**Test 1, no flash** (the current release): the start list. H1 predicts a long time for the starts that the log marks
"cold start (new ring)", with a short start (0.2–0.5 s, no `seg_loaded`) before each.

**Test 2, the probe build**: the start list. H1 is shown when a start has `lv_first` with seg2 not 0xA0602BE8 and its
records end there. `start_kind` gives each start's power-on factor.

**Test 3, A/B** (if test 1 or 2 shows slow cold starts): flash `films-start-texts` (the pinned build without
peaking-mf; it has the Debug Log) and run the start list. If its cold starts are fast, peaking-mf is the cause.

Commands, Mac, card at `/Volumes/Untitled`. Before a test, clear the old log:

```sh
rm /Volumes/Untitled/EPM2LOG.BIN
```

Flash, test 2: `epm2flash slow-boot-probe e783fbe686fc774a17b64590c8bd986ff1259bb84d189b703c5efc478aa675ca`

Flash, test 3: `epm2flash films-start-texts d8eef426227be0f7fc4925626f519afe33178e12205fad97d6701a56bcb39ba0`

Go back: `epm2flash peaking-mf 6a47806dfafce15d281358eae2beffe397132e5999c50b28c69b2a2467efcf39`

After each test:

```sh
scp /Volumes/Untitled/EPM2LOG.BIN USER@HOST:/path/to/epm2-tools/.local/spot-af-logs/EPM2LOG-slow-boot-TEST.BIN
```

(TEST = 1, 2 or 3.)

| Result | Meaning |
|---|---|
| Cold starts take 8 s or more, each with a short start before it in the log | a double start on a cold start; test 2 tells whether it is H1 |
| Test 2: `lv_first` seg2 not 0xA0602BE8, then no more records in that start | H1 is the cause (V) |
| Test 2: seg2 0xA0602BE8 in every start, cold starts still slow | H1 is not the cause; look before the timer's zero (H2) |
| Test 3 fast and tests 1 or 2 slow | peaking-mf is the cause |
| All starts about 2 s | the body does not show the issue; the reporter's body is needed |

## Files

- `scripts/release_specs.py`: the specs of each release tag.
- `scripts/boot_times.py`: one line per session of a decoded log.
- `scripts/coldwarm.mjs`: emulator boot with chosen DRAM content at reset.
- `scripts/hookhits.mjs`: first run of each hook site in the emulator.
- `scripts/changed_runs.py`: the byte runs where a build differs from stock, by segment.
- `scripts/disasm_ranges.py`: disassembly of block-0 ranges.
- `scripts/mkspec.py`: writes `data/specs/slow-boot-probe.json`.
- `scripts/emu_tlv.mjs`: check of T_LV and T_PW.
- `scripts/emu_cold.py`: the peaking latch with segments 2 and 3 copied and not copied (section 8).
- `results/`: the outputs named above.

## 8. The fix: build `cold-start-fix` (2026-11-25)

### New evidence

A contributor reproduced the slow start on another E-PM2 (comment on PR #10, 2026-11-25): after 60 s off, about 10 s
until the camera can shoot, also with Peaking Off; after 10 s off, nearly instant. A local build of theirs that moves
the MF test of the peaking latch from segment 2 to segment 1 started at once after 60 s off, also with peaking on
(V camera, the contributor's body; their build is not in this repository). This confirms H1. The owner's two bodies
do not show the slow start today.

### The check that missed it

`emulator/hookcheck.py` decoded each spec's own bytes, only hooks of 8 bytes or less, and no table words. It now makes
the build's block 0 and decodes the built bytes of every op in early-loaded space (overlapping ops as one run), and
lists stock pointers that an op changes. `cli/tests/test_hookcheck.py` holds the pinned build `spot-af-2` to one FAIL,
the jump 0x7E4C93A4 (kernel) → 0x7ECB0B81 (segment 2).

The audit of `spot-af-2` (`results/hookcheck-spot-af-2.txt`; 187 transfers leave patched early-loaded code, 88 of
them into segments 2 or 3):

| Transfers | Spec | Runs when | Before Usr1 ends? | Label |
|---|---|---|---|---|
| `jmp` 0x7E4C93A4 → T_MF 0x7ECB0B81 | peaking-mf | every live-view struct refresh, any Peaking setting, any focus mode | yes: the cause of issue #6 | V static, V the contributor's camera |
| 2 `jmp`: 0x7E56C6A5, 0x7E546160 | stock-films-structure-3 | the colour stage of every image job, live view too | not seen: the first colour stage is 1.6–2.9 s after the start in the owner's logs, `seg_loaded` at 0.33 s; nothing waits for the copy | V log, safe by timing only |
| 10 `jmp` in the ART BKT frame composer 0x7E5A75AE (5 were not seen before: 10-byte hooks) | stock-films-structure-3 | an ART bracket picture is taken | no: a capture needs the application | I |
| 48 table words 0x7E78AEBC–0x7E78CB40: the colour stage's cases (chroma, tone hash, six-axis, saturation, look, 12-region) of the film codes 75, 92, 94, 98, 125, 144, 156, 159 | stock-films-structure-3 | the colour stage runs for a film code: a film simulation of a loaded look pack on the selected ART entry | as the two `jmp` of the colour stage | I, safe by timing only |
| 25 table words 0x7E7FF034–0x7E7FF0A4, 0x7E807858–0x7E8078C8, 0x7E854A50–0x7E854A6C: the mov layer's live-view rows and art_GetFilterType rows of the hidden art values 111, 112, 114, 115, 118 | stock-films-structure-3 | live view is set up with a hidden art value: ART mode with a film simulation on Grainy Film, Gentle Sepia, Dramatic Tone, Key Line or Watercolor | **U**: a live-view set-up could read its row before the copy ends | U |
| 2 table words 0x7E439C80, 0x7E439C9C: the entries of the tasks 0x90 and 0x91 | card-looks-9, log-menu-3 | the task starts; only T_GUI (segment 2) starts it | no (proof from the code) | V static |

All but the first are in `emulator/hookcheck-allow.tsv` with this evidence. Probe for the U row: the start list of
section 7 with a look pack loaded, mode ART, one of the five entries selected. It is not part of this fix: every
build since stock-films (2026-11-18) has these words, and the reports of issue #6 begin with rc.3.

### The options

| | Option | New bytes in early-loaded space | What a mistake costs | Proof of the load order |
|---|---|---|---|---|
| a | T_MF, T_MF2, T_MF3 as one routine in segment 1 | 61 B, in an area where code ran on the camera (lss-core, spot-core-2, pana-ring-probe at this address) | a wrong routine shows in live view only (no lines, or a fault at a refresh); the update path has no live view | static: no transfer from early-loaded code to segment 2 is left; hookcheck 0 FAIL without an allow entry |
| b | T_MF stays in segment 2; T_R tests a "segment 2 is loaded" flag first | about 20 B for the test (T_R's 10 B do not hold it), and a flag that T_CTOR sets and T_BOOT clears: changes in card-looks-9 / log-menu-3, flashed and working code | as (a), and a start that kept RAM reads an old flag unless T_BOOT runs before the first refresh; a mistake there is the same restart | by the order of three hooks, not static: the jump stays, with an allow entry |

Chosen: **(a)**. It is the approach the contributor's camera confirmed, it needs no flag and no change outside
peaking-mf, and the check proves it. Space: the kernel run has 22 B free in three pieces. Segment 1's reclaimed exp
printers have 288 B at 0x7E69EC6B–0x7E69ED8B: the run of `pana-ring-probe`, a DEBUG probe that no later build names
(`tools/space-ledger/superseded.tsv`: history). After the fix 227 B of it are free. The slow-boot probe's T_LV
(section 6, not flashed) used the same run: the two are not for one build.

### What was built

`data/specs/peaking-mf-2.json` (`gen/peaking/mkspec_mf.py`), in place of `peaking-mf` in `spot-af-2`:

- T_MF, 61 B at 0x7E69EC6B (segment 1): the instructions of T_MF, T_MF2 and T_MF3 in one run. R set → T_R's test
  of the Peaking setting. R clear → the focus mode in use (prm 0xC021) with the kernel's settings getter 0x7E457C75;
  MF and the GUI state word not 0x5101 → the test of the Peaking setting; else a1 and d1 restored and T_R's return 0.
- T_R's first 10 B: `jmp T_MF` and 5 nop, as before with the new target. T_R's one caller is the latch T_A, which the
  hook 0x7E6ECF91 in segment 1 reaches, so T_R cannot run before segment 1 is in RAM.
- T_GS (12 B, 0x7EBF2F20, segment 2) and the GUI state setter's hook: unchanged. Their caller is segment-2 code.
- The old runs 0x7ECB0B81 (21 B), 0x7ECB0FD8 (39 B) and 0x7EBF3B94 (23 B) hold stock bytes again.

Before the first GUI state of a start the GUI state word holds what the last start left, or noise after a cold
start. If it reads 0x5101 there are no lines until the first GUI state. `peaking-mf` had the same (I).

At the first refresh of a cold start T_MF now calls the settings getter for prm 0xC021. The live-view code calls the
same getter for the same prm in that phase (0x7E6CAAA7, R), and the contributor's build passed its cold starts (I
that it calls the getter there).

`data/builds/cold-start-fix.json`: `spot-af-2` with `peaking-mf-2`, label 2026.11.25, sha256
`eab0c64ea47d100c73a8b7889ab9ff1b83a91088dfc413073c1adb8268ba83d0`.

### Checks

| Check | Result |
|---|---|
| `uv run epm2mod make cold-start-fix` | free space PASS (0 FAIL), boot-test PASS, update-path-test PASS (`results/make-cold-start-fix.txt`) |
| `uv run python emulator/hookcheck.py data/builds/cold-start-fix.json` | 190 transfers, 0 FAIL, 87 allowed (`results/hookcheck-cold-start-fix.txt`); T_R → T_MF is kernel → segment 1 |
| `scripts/emu_cold.py` (the latch from its hook to its return; R 0 / 1, Peaking Off / White, S-AF / MF / C-AF, GUI 0x5100 / 0x5101) | PASS (`results/emu-cold.txt`). Segments 2 and 3 copied: 24 of 24 cases as `spot-af-2`. Not copied (0xFF, random): `cold-start-fix` 24 of 24 as copied, no fault, 0 instructions in late-loaded space; `spot-af-2` faults at 0x7ECB0B81 in 24 of 24 |
| `tools/checks.py --tier full` | free space, op-check, boot-test, update-path-test PASS; save-guard S24 / S25 PASS for the build (the "FAIL" is the reference's, as for peaking-mf and spot-af); peaking S4 R = 0 at the end, S5 as the reference, S7 PASS (`results/checks-cold-start-fix.txt`); S6 against the pinned `spot-af-2` PASS (`scen_direct4.py s6`, `results/s6-cold-start-fix.txt`) |
| `emulator/boot/shotdiff.sh` against `spot-af-2`, P state: the Custom Menu tab, its groups, A page 1, MF Assist, Peaking and its list; E page 1 and its rows 2 to 8 (Spot Metering is row 4) | 0 of 6 and 0 of 8 differ |
| `gen/run.sh --check`, `uv run python -m unittest discover -s cli/tests` | every generated spec as committed; 280 tests OK (6 skipped: they need the built app page) |

Not checked off the camera: live view itself, the lines, the start time. The Firmware screen of this build was not
drawn in the emulator; the label is written by `epm2mod make` as in every build since 2026-11-19.

The emulator still cannot show the fault in a whole start (section 3): the harness shows the one function.

### Camera test sheet

The owner's bodies do not show the slow start, so this run shows that nothing broke. The contributor and the
reporter of issue #6 can confirm the start time.

Mac, card at `/Volumes/Untitled`. The old log off the card, then the flash:

```sh
rm -f /Volumes/Untitled/EPM2LOG.BIN
epm2flash cold-start-fix eab0c64ea47d100c73a8b7889ab9ff1b83a91088dfc413073c1adb8268ba83d0
```

Go back: `epm2flash spot-af-2 86e8fdcaaeb1ff52410981adef1cb576486adcd14318261a8411079cf256a5be`

1. **The build.** MENU → SETUP → wrench tab → Firmware. Expected: `Body : 1.6  EPM2Mod 2026.11.25`. `2026.11.20`:
   the update did not run; flash again.
2. **Debug Log on.** MENU → SETUP → Custom Menu → J → Debug Log → On → OK.
3. **Peaking in MF.** Press OK, in the right column choose AF Mode → MF. MENU → SETUP → Custom Menu → A → Peaking →
   White → OK. MENU → SETUP → Custom Menu → A → MF Assist → Off → OK. Point the camera at something with edges.
   Expected: white lines in live view the whole time, no zoom. Half-press: the lines stop. Release: they come back.
   Take a photo: the preview has no lines.
4. **MF Assist.** Press OK, AF Mode → S-AF+MF. MENU → SETUP → Custom Menu → A → MF Assist → On → OK. Half-press and
   turn the focus ring. Expected: the view zooms in, with white lines.
5. **S-AF.** Press OK, AF Mode → S-AF. Expected: no lines.
6. **Spot metering.** MENU → SETUP → Custom Menu → E. Exp/▣/ISO → Spot Metering → RIGHT → Spot → RIGHT → On → OK.
   Press OK, in the right column choose the metering item → Spot. Tap a lamp on the screen, then a dark area.
   Expected: the picture gets darker after the tap on the lamp and brighter after the tap on the dark area.
7. **Starts.** Press OK, AF Mode → MF (Peaking stays White). For each start: press ON/OFF once, and count the
   seconds until live view shows the picture. Write down the time, whether the lines show, and whether the screen
   lit, went dark and lit again.
   1. Off 2 min, then a start. Twice.
   2. Battery out for 2 min. Battery in. Wait 10 s. A start. Twice.
8. Turn the camera off. Card into the Mac:

```sh
scp /Volumes/Untitled/EPM2LOG.BIN USER@HOST:/path/to/epm2-tools/.local/spot-af-logs/EPM2LOG-cold-start-fix.BIN
```

| Result | Meaning |
|---|---|
| Steps 3 to 6 as expected, every start of step 7 about 2 s with lines | pass: pin the build; the start time on a body that shows the issue is for the contributor and the reporter |
| No lines in step 3, lines in step 4 | T_MF's MF branch is wrong (the focus mode read or the GUI state word) |
| No lines in steps 3 and 4 | T_MF does not reach T_R's test of the Peaking setting |
| Lines in step 5 | T_MF's return 0 is wrong |
| Live view freezes or the camera starts again when live view begins | a fault in T_MF: go back |
| Step 6 fails | not from this change (spot-core-2 is byte for byte as flashed): go back and repeat step 6 on spot-af-2 |
| A start of step 7 takes 8 s or more, or the screen lights twice | the issue shows on this body with the fix: the log tells whether `seg_loaded` came before the first live-view state; look at the colour-stage rows of the audit |

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
- `results/`: the outputs named above.

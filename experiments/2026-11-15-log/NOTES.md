# A structured log for the E-PM2 mod

Date: 2026-11-15. Status: build `builds/debug-log.json` (the pinned build `peaking-colours` + `patches/log-core.json`
+ `patches/log-probes.json`), sha256 `e74f1aece22a2846b79a3a8b858ade531d3f7a37ef8f25908c34ed52c87bbda8`. Checked in emulation.
**Not flashed.** The pinned build still rebuilds to `4d6b1f26…56f8`. How to use the log and how to add an event:
[docs/logging.md](../../docs/logging.md).

Labels: **V** verified (bytes, or ran in the emulator), **I** inferred, **U** unknown.

## 1. What it is

The camera writes 16-byte binary records into a RAM ring. A task appends the new records to `EPM2LOG.BIN` on the
card at a safe moment. `epm2mod log FILE` prints one JSON object per record. The camera holds no text: the names and
formats are in `logs/events.json`, which the generator and the decoder both read.

This follows the usual practice for small systems: a dictionary of event ids on the host (Pigweed `pw_tokenizer`,
`defmt`, Zephyr dictionary logging), deferred output (the call that logs never does I/O), and a ring that survives a
restart so that the last events before a crash can be read (Memfault's reboot tracking).

## 2. Design, with the evidence

| Question | Answer | Evidence | Label |
|---|---|---|---|
| Record size | 16 bytes: `u16 id, u16 sequence, u32 time, u32 arg0, u32 arg1`. The fields of the brief add up to 16, not 12. A power of two makes the ring index a mask and a shift | `docs/logging.md` | V |
| Time | The raw value of timer channel 9, register 0x98900074. One read, no call. It counts down once per microsecond and wraps after 1,073 s; the decoder turns it round | The stock `now_us` 0x7E4262CD returns `0x3FFFFFFF − (0x98900074)`; the boot marks 0x7E426511 use it. In the emulator the values follow lab time | V for the register, I for the unit on the camera |
| Which contexts log | Tasks of CPU0 (boot task, CA_MAIN, mov task, ART task, the application's tasks), and through the error recorder any task or interrupt handler of either CPU | Task table `build/map/tasks.tsv`: MOV_TASK and ART are CPU0 tasks; the emulator's observer of 0x7E426D4B has a CPU1 case | V |
| Safe from every context | (1) One ring per CPU, chosen by the CPU number register 0x8050, so the two CPUs never write the same words. (2) On its CPU, `log_put` runs with interrupts off (`and 0xF7FF,psw`, then the saved PSW is put back). (3) It calls nothing, waits for nothing, and keeps every register and the flags. Each probe routine also leaves every register and the flags as they were | (1) is what the stock boot marks do (0x7E426511 picks a buffer by 0x8050). (2) is the kernel's own idiom (0x7E43292A, 0x7E4326B5). (3) scenarios S16 and S17 | V |
| Why not one ring with a lock | Each CPU has its own cache, and the firmware turns 0x6… into 0xA… before a record goes to the other CPU (0x7E45DB37). A shared write index needs a lock that both CPUs take; the kernel's own one is the hardware semaphore 0x8FE00000. Two rings need none | focus-peaking NOTES 16.1; platform index 0x7E43347B | V |
| Which RAM | 0x7E4F9000–0x7E4FD2C0 (17,088 bytes), used through the uncached alias 0xBE4F9000: two rings of 32 + 512 × 16 bytes, 128 bytes of state and one 512-byte block buffer. It is the end of the gap 0x7E4C9800–0x7E4FE000 between the kernel and segment 1 | No boot copy loads the gap, no clear loop and no stack is in it (`docs/code-space-map.md` section 2: "Write ranges, other than loads, that overlap block 0's runtime span: none"); `tools/freespace.py area 0x7E4D0000` finds no pointer to the last 20 KiB in the runtime or uncached alias. The copies of the kernel and of segment 1 write their neighbours through the same alias (0xBE430000, 0xBE4FE000). In the emulator the whole gap stays zero through the pinned build's start, menus, playback and power-off | V static and V in the emulator; **U** on the camera (a heap or a buffer with a computed address would not show) |
| Why the uncached alias | A flush on CPU0 reads the ring of CPU1. A write through the cache of CPU1 may not be in RAM yet. An uncached write is also in RAM at once when the camera crashes | as above | I |
| Overwrite and drops | A ring header holds `w` (records written) and `f` (records in the file). A record goes to slot `w & 511`. The flush task sees `w − f > 512`, adds the difference to the drop count and starts at `w − 512`. `log_put` has no drop code | S16; emulator check (e) | V |
| Who writes the file | The dormant task USRTEST_A (id 0x90, priority 11, stack 0x800) gets the flush routine as its entry. Its row in the task table 0x7E438CD0 is in the kernel range. Nothing in stock starts it | Feature map 10f section 6: no code loads its id slot, in 7 bodies. MOVREC_FILE and REC_FILE are stock tasks with the same priority and stack size, and MOVREC_FILE calls the same `fileif` functions (0x7E6F26D1) | V |
| Why a task of its own | The `fileif` calls send a message to the task FILECLBK and wait. FILEFGND cannot be used: its jobs are the completion callbacks of the SD driver, so a waiting job there would wait for itself. The E-M10 project froze the camera with file calls from a GUI callback. A separate task can wait without holding anything | 13f-drivers (FILEFGND, FILECLBK); feasibility notes 3.1 | V for the structure, I for "cannot freeze" |
| When | The hook at the GUI state setter (0x7ECDF6E4, task CA_MAIN) starts the task when the state enters 0x57xx (menus), 0x3xxx (playback) or 0x2xxx (power off, sleep), no flush is running, and the GUI's own `isMediaWriting()` 0x7ECD360A answers 0 | States read from the firmware's own trace in the emulator. Stock calls `isMediaWriting` at the same kind of moment (`startPlaySubAppStateShooting`). These states are not reached during an exposure or while a movie records | V for the states, I for "never during a capture" |
| Never at start-up | The trigger is a GUI hook in segment 3. The GUI runs after Usr1 has loaded segments 2 and 3 and after the card mount (`0x1003` waits for "media mount end") | emulator NOTES 10.5 | V |
| No card, full card, locked card | `fileif_fopen` gives 0: the task ends. A block write that gives 0 is tried 3 times, 100 ms apart (`OlyTaDl` 0x7E449605); then the flush ends and the records stay in RAM for the next one. A write that gives a part of a block ends the flush at once. No other loop waits for the card | Emulator check (d): no card, result 1, no hang. Full and locked cards are not modelled | V for no card, **U** for full and locked |
| Whole 512-byte blocks | Each `fileif_fwrite` call writes one block of 512 bytes at a file offset that is a multiple of 512 | The stock stream writer 0x7E5C9E14 reads a sector before it changes a part of it (0x7E5C9F76, 0x7E5C9F96, 0x7E5C9FCA), and the write gives 0 when that read fails. With appends of 32 + 16 × n bytes about one flush in three failed in the emulator. A whole sector needs no read | V in the emulator (section 5) |
| The file kept the blocks? | `fileif_fclose` gives 0 also when the directory update failed. So a flush stores the size that the file should have, and the next flush reads the size first: if it is smaller, the `f` of each ring goes back to its value before that flush and the records are written again (`flush` shows `not_saved`) | Emulator check (h): 41 flushes in two runs, 2 directory updates failed, all 362 records in the files once and in order | V in the emulator |
| File size | Before each flush `fileif_filesize_get`: at 4 MiB or more the task ends. Delete the file to go on | Emulator: a file of 4 MiB gets no block, a file one block below gets one | V |
| Blocks | A 32-byte header (magic `EPLG`, version, record size, CPU, build id, first record number, count, drop count, restart count), at most 30 records, zeros up to 512 bytes | `docs/logging.md` | V |
| Build identity | The first 8 bytes of a sha256 of the id, name, level and arguments of every event of `logs/events.json`. The generator puts them into the flush code; the decoder computes them from its dictionary and marks a file that has another value. `src/epm2mod` needed the decoder only | `tests/test_eventlog.py` | V |
| Boot reason | The `boot` event carries the power-on factor (u16 0x604154E6, getter 0x7E45D407; the shell prints it as "poweron factor") and the wake byte 0x604154E9 | Feature map 02 line 32. What each value means is not decoded. The emulator gives 0 | V for the variable, **U** for the values |
| Firmware errors | The recorder 0x7E426D4B(d0 = code, then a count and arguments on the stack) is hooked at its entry: `fw_error` (code, caller from MDR) and `fw_error_args` (count, first argument) | The loop at 0x7E426DAF reads the count at (48,sp) and the arguments from (52,sp). The emulator's two start-up errors are in the log with the same code and caller | V |
| Records after a crash | The ring header has a magic word. `log_put` starts a new ring only when the magic is wrong. A start that finds the magic adds 1 to the restart count and goes on in the same ring, so the first flush writes the old session's last records before the new `boot` record. The decoder marks them `recovered` | Emulator check (f) with a ring image put into RAM before the start | V for the code. **U**: does this RAM keep its content when the camera restarts itself? The probe is in section 8 |
| If RAM is cleared | The magic is wrong, the ring starts empty, the session is 0. Nothing else depends on old content: the 128 state bytes are cleared at every start | check (b) | V |
| Release builds | The pinned build lists neither spec. The two specs are deltas: each `expect` is a byte string of the pinned build | `epm2mod make` gives `4d6b1f26…56f8` | V |

A hook in the pre-reset range (the error recorder) jumps into the kernel range. The reset code copies the kernel
before any code that can reach the recorder: none of the 15 calls before the copy at 0x7E421228, and not the flash
read 0x7E4217E6 itself, reaches 0x7E426D4B in the call graph (**V** static). `tools/emu/hookcheck.py`: 72 transfers,
0 FAIL.

## 3. Addresses

| What | Where | Bytes |
|---|---|---|
| `log_chg`, `log_cnt`, `log_put` | 0x7E4C9514, 0x7E4C951F, 0x7E4C9531 (kernel range) | 139 |
| `T_ERR`, `T_BOOT` | 0x7E4C959F, 0x7E4C95C7 | 40, 90 |
| Routines of the probes in segment 1 and the kernel | 0x7E4C9630–0x7E4C97BD | 397 |
| Flush task 0x7EBF2C00, file name 0x7EBF2DFE, `T_GUI` 0x7EBF2E0F (segment 2) | 0x7EBF2C00–0x7EBF2E80 | 640 |
| Routines of the probes in segments 2 and 3 | 0x7EBF3780–0x7EBF38BA | 314 |
| Task table row of id 0x90: entry | 0x7E439C80 | 3 changed |
| 20 hook sites | see `results/log-listing.txt` | 128 |
| Rings | CPU0 0x7E4F9000, CPU1 0x7E4FB020; header `magic, w, f, drops, restarts`, records from +32 | 2 × 8,224 |
| State | 0x7E4FD040: busy, last result, trigger state, last GUI state, frame count, seven gates of 8 bytes, expected file size | 128 |
| Block buffer | 0x7E4FD0C0 | 512 |

New code: 1,620 bytes (kernel range 666, segment 2 954), and 131 bytes changed at the 20 hook sites and in the
task table. `log-core` is 931 bytes, `log-probes` 820. Left free: kernel range 256 bytes, the segment-2 area 2,117
bytes (`tools/freespace.py area`). RAM: 17,088 bytes. A probe uses 48 bytes of the stack of the task that runs it;
the flush task has its own stack (frame 80 bytes).

## 4. Events

| Id | Name | Arguments | Site | Bytes (routine + hook) |
|---|---|---|---|---|
| 1 | `boot` | restart count; power-on factor, wake byte | Usr0 entry 0x7E503DD4 | 90 + 6 |
| 2 | `flush` | GUI state that started it; result of the flush before (ok, no_file, write_failed, file_full, not_saved) | flush task | in the task (510) |
| 3, 4 | `fw_error`, `fw_error_args` | code, caller; count, first argument | recorder 0x7E426D4B | 40 + 8 |
| 5 | `gui_state` | new state, old state | GUI state setter 0x7ECDF6E4 | 113 + 5 (with the trigger) |
| 256 | `pk_mf_start` | L, R, L2, C; state object | entryMfAssistOn 0x7EB7D47D | 40 + 6 |
| 257 | `pk_mf_end` | L, R, L2, C; state object | entryMfAssistOff 0x7EB7D44C | 31 + 5 |
| 258 | `pk_latch` | L, R, L2, C; live-view bytes +4 and +5 (art filter type) | expose setter 0x7E6C610B, when the four bytes change | 43 + 6 |
| 259 | `pk_heap_mode` | mode; caller | heap mode setter 0x7E578C60, when the mode changes | 38 + 6 |
| 260 | `pk_pass9` | picture buffer; first line-image byte and the gain | Key Line pass 9 0x7E72676D, the first 3 after an MF Assist start | 66 + 7 |
| 512 | `art_sixaxis` | art code; handler | six-axis dispatch 0x7E56D2BF, on a new code or after a shooting callback | 40 + 6 |
| 768 | `lv_adjust` | mode (1 Adjust, 2 Reset); rotate | `api_adj_Set_Slope_Adjust` 0x7E676261 | 32 + 10 |
| 769 | `lv_values` | working set entry 0: x, y; z, temperature | table reload 0x7E459A5F | 60 + 5 |
| 1024 | `iv_start` | result; state word | startIntervalShooting 0x7E988670 | 41 + 7 |
| 1025 | `iv_frame` | frame number (counted by the probe); state word | recordingDone_interval 0x7EA997E5 | 47 + 7 |
| 1026 | `iv_end` | result; frames counted | endIntervalShooting 0x7E982E8E | 33 + 7 |
| 1027, 1028 | `iv_state_set`, `iv_state_clear` | bits; state word before | 0x7E969E2F, 0x7E9698FD | 33 + 5 each |
| 1280 | `film_stage` | art code; job flags | colour-matrix stage 0x7E56C68B | 38 + 7 |
| 1281 | `film_matrix` | matrix table; d3 | art matrix apply 0x7E56C764 | 37 + 6 |
| 1282 | `film_curve` | art code; handler (it names the curve set) | curve selector dispatch 0x7E56E860 | 42 + 6 |
| 1536 | `shoot_cbs` | CBS number; result | shooting callback 0x7E995A0B | 56 + 8 |

The pipeline probes (512, 1280–1282) run in every live-view frame. They log when their first argument changes, and
once more after each shooting callback, so a still gets its own records even when live view used the same look.
The end or cancel reason of an interval sequence is the `shoot_cbs` number that comes before `iv_end`
(the firmware's names: CBS_END_INTERVAL_SHOOTING, CBS_REQUEST_END_INTERVAL_SHOOTING, CBS_END_INTERVAL_SHOOTING_TIMER;
the numbers are not decoded yet: **U**, the first camera log gives them).

Not in this set: the level gauge's "Level Adjust opened" as its own event (the `gui_state` records show the menu, and
`lv_adjust` the action), and a hook of the firmware's own trace function 0x7E9670E9 (it would give every trace line of
the application layer as "format string address + first argument"; its rate on the camera is unknown).

## 5. Limits found on the way

- **Appends that are not whole sectors are fragile in the stock file code.** The first version wrote a 32-byte
  header and then the records with two `fileif_fwrite` calls. About one flush in three gave 0 bytes. The stream
  writer 0x7E5C9E14 reads the first and the last sector of a write when the write covers only a part of them
  (0x7E5C9F76, 0x7E5C9F96, 0x7E5C9FCA), and it gives 0 when such a read fails. No stock feature appends to a file
  this way: the stock callers write new files. A whole sector at a sector boundary needs no read. With whole
  512-byte blocks one flush in ten still met a fault (next item). Whether the failed reads of the first version
  were that same fault or a refusal of a sector past the end of the file was not separated (**U**).
- **Card commands fail now and then in the emulator** (the SD driver's error 0x1418 after four tries of CMD24 or
  CMD17 at the same lab time). The card stand-in answers a command at once, and the driver's four tries all run in
  the same instant, so this is taken as a fault of the stand-in (**I**), not followed further. It was useful: it
  showed that `fileif_fclose` gives 0 when the directory update failed, and that `fileif_fopen` and the size read
  can fail. The flush task handles each case (three tries for a block, the size check at the next flush, result
  `no_file`). In 41 flushes with 6 such faults no record was lost or written twice (check h).
- The emulator has no live view. The probes of the mov task and the ART task were run in the scenario rig (S15).
  The film and six-axis probes and the interval probes are in code that neither run reaches. S17 runs each of them
  from its hook site with set registers. That shows that a routine is transparent and what it logs. It does not show
  that the camera takes that path.

## 6. Checks

The emulator outputs are in `~/opt/om-emu-e101-boot-work/log/`; the text ones are copied to `results/emu-*`. The
scripts are in `scripts/log-emu/` (`run-checks.sh a` … `h`, `crawls.sh`). The card is a FAT16 image made from a host
folder; `logplay.mjs` copies the card's files back to that folder after a run.

| Check | Result | Label |
|---|---|---|
| `.venv/bin/epm2mod make builds/debug-log.json` | sha256 `e74f1aec…bda8`; free-space check PASS, 0 FAIL, no `first_code` (`results/freespace-check.txt`) | V |
| `tools/emu/opcheck.py builds/debug-log.json` | 18 specs, 0 FAIL | V |
| `tools/emu/hookcheck.py` on the two specs | 72 transfers, 0 FAIL: every hook in the pre-reset range, the kernel or segment 1 goes to the kernel range (`results/hookcheck.txt`) | V |
| The generator's own checks | each site is on an instruction boundary of the pinned build; no replaced instruction is pc-relative but `call`, which is assembled again; no instruction and no 4-byte word of block 0 names an address inside a replaced range | V |
| (a) Boot, `stage2-boot.mjs 2000` | PASS. Against the pinned report 3 lines differ: the instruction counts (cpu0 +570: the new code; cpu1 −2,982: CPU1 runs no new code, its ring stays empty, and its idle polling follows the timing of CPU0, **I**), the time of the second start-up error (37.6 → 37.7 ms) and the count of idle-loop visits (`results/emu-boot-diff.txt`) | V |
| Update path (`audit/update-boot.mjs`: OK held at power-on), without and with an update file on the card | the same lines as the pinned image but the times; the update file is found and read | V |
| (b) Session with a card: quick menu Natural → Portrait, Custom Menu J → Level Adjust → Reset, Custom Menu A → Peaking → Red, playback | `EPM2LOG.BIN` (3,072 bytes, 6 blocks) is in the host folder. `epm2mod log` gives 61 records in order: boot, lv_values, the GUI states, the two firmware errors, 6 flushes (4 at menu entries, 1 at the quick menu state 0x5705, 1 at playback), `lv_adjust` mode 2 and `lv_values` at the Reset (`results/emu-session-brief.txt`, `emu-session.jsonl`) | V |
| (c) A second run with the same card folder | the file grows to 4,096 bytes; the decoder gives session 1 with 61 records, a `ring_restart` marker and session 2 with 26 | V |
| (d) The same session without a card, pinned and debug | no hang; the flush ends with `no_file`; the 12 screens are byte-equal to the pinned image's. With a card: also 12 of 12 equal | V |
| (e) Ring overflow: 700 `log_put` calls from interrupt context before the first flush, and 3 records put into the CPU1 ring | the file has the newest 512 records of CPU0 (numbers 208 to 719) after a `gap` marker with `lost: 208`, and the 3 records of CPU1 in their own block; the header's drop count is 208 | V |
| (f) A start with the ring of the run before in RAM (the script loads the saved RAM image before the reset) | `boot` has session 1; the 8 records that the first run had not flushed are in the file before it, marked `recovered` (`results/emu-restart-brief.txt`) | V for the code path; the camera's RAM is the open question |
| (g) Firmware errors | the emulator's own observer and the log agree: 2 × 0x2A001001 from 0x7E579DCC, with the argument 0x7102 | V |
| (g) The RAM | on the pinned image the whole gap 0x7E4C9800–0x7E4FE000 is zero after the start and after the session with playback, INFO and power-off | V |
| (h) 41 flushes in two runs (20 menu entries each, one run with playback) | 171 and 191 records, each file complete and in order, no marker. Flush results: 35 ok, 2 `not_saved` (written again by the next flush), 4 `no_file` | V |
| File limit | a file of 4 MiB is not written to (`file_full`, 0 blocks written); a file one block below the limit gets one block and then stops | V |
| Shallow menu crawls of the pinned and the debug image: P without card, iAUTO, ART with card, movie with card | every screen byte-equal (349, 283, 286 and 279 screens), the same notes and firmware errors (`results/emu-crawl-shallow.txt`) | V |
| `python -m unittest discover -s tests`, `mypy`, `black --check` | pass (19 tests for the decoder: truncation, unknown id, wrapped ring, two sessions, recovered records, a block written twice, timer wrap, two CPUs, padding, another dictionary) | V |

A sample of the decoded session (`epm2mod log`, one JSON object per line; here the events of the firmware errors and
of the Level Adjust reset):

```json
{"seq": 5, "cpu": 0, "session": 1, "time_us": 41806, "event": "fw_error", "level": "error", "args": {"code": "0x2A001001", "caller": "0x7E579DCC"}, "build": "d1ddd46b4dac2414"}
{"seq": 6, "cpu": 0, "session": 1, "time_us": 41807, "event": "fw_error_args", "level": "error", "args": {"count": 1, "arg": "0x00007102"}, "build": "d1ddd46b4dac2414"}
{"seq": 26, "cpu": 0, "session": 1, "time_us": 11884832, "event": "lv_adjust", "level": "info", "args": {"mode": 2, "rotate": 11}, "build": "d1ddd46b4dac2414"}
{"seq": 27, "cpu": 0, "session": 1, "time_us": 11884833, "event": "lv_values", "level": "info", "args": {"xy": {"raw": "0x03E80000", "x": 0, "y": 1000}, "zt": {"raw": "0x00FA0000", "z": 0, "temp": 250}}, "build": "d1ddd46b4dac2414"}
```

## 7. Scenario tests

`scripts/scen_log.py all PINNED_BLOCK0 DEBUG_BLOCK0`, output `results/scen-log-s15-s17.txt`. The rig is the one of the
focus-peaking notes section 13 (real mov and ART task code, no image processor).

| Test | Result | Label |
|---|---|---|
| **S15** Live view with the MF Assist request, Natural and Key Line, Peaking White and Red: debug against pinned, 4 frames each | 16 frame comparisons, all the same: memory writes outside the log's RAM (but one word, see below), device accesses in the same order (the debug image adds 0 to 3 reads of the timer per frame), no stock pc lost, the same pass 9 gain and pass 7 `ucExpose`, no anomaly | V |
| The decoded ring after S15 | in each of the four runs: `pk_mf_start`, `pk_heap_mode` 1 (caller 0x7E4C935E, the peaking code), `pk_latch` with L 1, R 1 and C 3 or 2, and three `pk_pass9` with the picture buffer that the heap log gives (0xB596A940) and the gain (512 for White, 0 for Red) | V |
| **S16** `log_put`, `log_chg`, `log_cnt` alone | every register kept; the record as the model; 600 records wrap at 512; `log_chg` logs a new value only, or while its gate has budget; `log_cnt` logs 3 of 5 calls with budget 3; with CPU number 1 the record goes to the CPU1 ring | V |
| **S17** Each of the 20 hooks alone, 29 cases: from the hook site to the first stock instruction after the replaced ones, with set registers and the flags N, Z, C, V set, on both images | the same registers and flags at that instruction (the MDR is left out where a `call` was replaced: it holds that call's return address); the replaced calls are made with the same arguments; the same memory outside the log's RAM; every record as the dictionary describes it, for all 19 probe events. The pipeline probes log a new art code once, and once more after a shooting callback. The GUI hook starts the flush task only at a menu, playback or power-off state while no flush runs and `isMediaWriting` gives 0 | V |
| S1 to S7 of the focus-peaking notes with the debug image (`results/scen-peaking-s1-s5-on-debug.txt`, `scen-direct4-s6-s7-on-debug.txt`) | S2, S3, S4, S5 and S7: the result lines of the pinned build (a picture in every frame, no anomaly in 13 filter changes, R not left set, the same state after Through End, the sleep routine untouched). S6: the six-axis dispatch runs through the new probe for the art codes 9 to 184 with 0 FAULT and the frames' codes reach the same point; the script marks each code as changed because its result text holds the instruction count (13 → 59). S1 is a byte-for-byte compare: it reports the log's RAM and the unset stack word, no stock pc lost but the two instructions named in the next row, no other pc gained | V |
| S12 to S14 of `scen_colours.py` with the debug image in the place of `peaking-colours` (`results/scen-colours-s12-s14-on-debug.txt`) | S12 (the colour loop on a synthetic frame) PASS: all 307,200 pixels as the model for Red, Yellow and Blue. S14 (`T_K` alone) PASS. S13 is a byte-for-byte compare with builds that have no log, so it reports FAIL here, and only for this: the log's RAM (0x7E4F90xx, 0x7E4FD0xx), the unset stack word below, the timer reads, and for Key Line with Peaking Off two stock instructions of pass 9 (0x7E726770, 0x7E726771) that now run as a copy in the probe's routine. The gains and `ucExpose` are as before in all 8 groups. S15 is the version of S13 for this build | V |

The one word that differs in S15, 0x602A4954, is not a fault of the probes. The stock line-job set-up (0x7E6CDA36)
copies a struct from its stack to 0xA02A4940 and never sets the word at +20. On the pinned image this word holds an
address of the test harness's stack in the first frame. A probe leaves its saved registers below the stack pointer, so
later frames copy another stale value. The test checks this and leaves the word out.

## 8. Camera test

Use a card with no photos that you need: this build writes a new file to it while the camera runs. Format the card
in the camera first.

Flash: `epm2flash debug-log e74f1aece22a2846b79a3a8b858ade531d3f7a37ef8f25908c34ed52c87bbda8`.
Go back: `epm2flash peaking-colours 4d6b1f26ed92d66b62b4d7dc32d26168e33fd8b153a7655d6c0d9a58267456f8`.

**Start-up risk.** Four changes are on the start-up path: the hook of the error recorder (pre-reset range), the hook
at the entry of Usr0, the hook of the accelerometer table reload (kernel), and the entry word of task 0x90 in the
task table. Their routines are in the kernel range, which the reset code loads first. In the emulator the debug image
starts like the pinned one, and with OK held it takes the update path, finds the update file and reads it, as the
pinned image does. The other hooks that run at a normal start (GUI state, MF Assist end, shooting callback) are in
segments 2 and 3, which the update path does not load. This body has no record of a recovery from a restart loop
(`docs/feasibility.md`), so all of this is evidence from the emulator only.

To read the log: power the camera off, put the card in the computer, copy `EPM2LOG.BIN` from the top folder of the
card to the machine with the repository, then `uv run epm2mod log /path/to/EPM2LOG.BIN > /tmp/scratch/log.jsonl`.

| Step | Do | Expect | If not |
|---|---|---|---|
| 1 | Power on | The camera starts as the pinned build does | A freeze or a restart loop: one of the hooks on the start-up path (below). Put the pinned file on the card, hold OK and power on |
| 2 | Wait 5 s. Press MENU. Wait 2 s. Press MENU. Power off. Read the card | `EPM2LOG.BIN` is there. The decoder shows `boot`, `gui_state` records (… 0x5100, 0x5700), `flush`, and at power-off 0x2000 with a second block | No file: the task did not start or `C:\EPM2LOG.BIN` is not the card's path; the camera is still usable. A freeze at MENU: file calls from this task are not safe at that moment; go back to the pinned build |
| 3 | Look at `boot`: `args.poweron` | A value for a normal power-on. Write it down | It is the first data on the power-on factor |
| 4 | Power on. Note the time between two MENU presses with a watch (about 10 s). Read `time_us` of the two `gui_state` 0x5700 records | The difference is about 10,000,000 | Another ratio: the timer's unit is not 1 µs on the camera; the decoder gets a factor |
| 5 | Shooting screen, P mode. Press OK (the quick menu opens at the right), select Picture Mode, move right past Custom to a film look, press OK. Half-press, take one photo. Press MENU twice. Do it again with a second look | `art_sixaxis`, `film_stage`, `film_matrix`, `film_curve` with the look's art code after the change and again after the `shoot_cbs` records of the photo. The photos are on the card and open | No pipeline records: the sites are not on the path of this mode. A freeze when the look changes: one of the four pipeline hooks; the last records in the next log (if `recovered` shows) name the last site that ran |
| 6 | MENU → Custom Menu → A → Peaking → Red → OK. MF Assist (the row above) must be On. Leave the menu, set the focus mode to MF, turn the focus ring, wait until the magnified view ends. Press MENU twice | `pk_mf_start`, `pk_latch` with L 1, R 1, C 2, `pk_heap_mode`, up to three `pk_pass9` with gain 0 and a picture address 0xB5……, then `pk_mf_end` | `first_pixel` and the picture address are the data that the colour pass needed |
| 7 | MENU → Custom Menu → J → Level Adjust → Reset → OK | `lv_adjust` mode 2, then `lv_values` | No `lv_values`: the reload is not on this path |
| 8 | The clock must be set. MENU → Shooting Menu 2 → Time Lapse Settings → On, with Frame 3 and Interval Time 5 s. Leave the menu, press the shutter button. After the third frame press MENU twice | `iv_start`, `iv_state_set`, three `iv_frame` (n 1, 2, 3), `iv_end` with frames 3, and `shoot_cbs` records between them | Write down the `shoot_cbs` numbers: they become names in the dictionary |
| 9 | Record a movie of 5 s. Play it. Play the photos | All files play | A damaged file: stop using the build and report which step |
| 10 | Power off, wait 2 s, power on, MENU twice, power off. Read the log | **The RAM probe.** `boot` with `args.session` 1 or more: the ring RAM keeps its content while the camera is off, so it will also keep it over a restart after a crash. Session 0 and a `ring_restart` marker: the RAM was cleared or lost power | Session 0 does not yet say what a crash restart does: the first real crash answers it (`recovered` records, or none) |
| 11 | Take the card out. Power on, MENU, PLAY, power off | Works as the pinned build | A freeze: `fileif_fopen` without a card is not safe on the camera |
| 12 | Put the card in with its lock tab on. Power on, MENU twice, power off | Works; the file did not grow | A freeze or a card error message: report it |

## 9. Unknown, to be settled on the camera

| Unknown | Settled by |
|---|---|
| File calls from the task USRTEST_A at menu, playback and power-off | steps 2, 5, 9 |
| The RAM at 0x7E4F9000 is free on the camera and keeps content over a restart | step 2 (a camera that works for a session), step 10, the first crash |
| `C:` is the card | step 2 |
| The timer unit | step 4 |
| The flush at power-off ends before the power goes | step 2: the block with state 0x2000 is in the file |
| Full card, locked card | step 12; full card not planned |
| The sites of the pipeline, interval and level probes are on the paths that the camera takes | steps 5 to 8 |

## 10. Files

| Path | Contents |
|---|---|
| `logs/events.json` | the dictionary |
| `patches/log-core.json`, `patches/log-probes.json`, `builds/debug-log.json` | the specs and the build |
| `src/epm2mod/eventlog.py`, `tests/test_eventlog.py` | the decoder and its tests |
| `docs/logging.md` | format, how to add an event, how to read a log |
| `scripts/mkspec_log.py` | the generator of both specs |
| `scripts/scen_log.py` | scenario tests S15, S16 and S17 |
| `scripts/log-emu/` | copies of the emulator scripts (they run in the emulator work folder) |
| `results/log-listing.txt` | the assembled code |
| `results/` | outputs of the checks |

## Camera result 1 (2026-11-15): the log works

The owner flashed `debug-log` (sha256 `e74f1aec…bda8`), used the camera outdoors, and sent `EPM2LOG.BIN`
(32,256 bytes, 63 blocks). `epm2mod log` decodes 1,280 records in 2 sessions, with no gap marker and 16
flushes, each with the result ok.

| Finding | Evidence | Label |
|---|---|---|
| File calls from the flush task work on the real card | the file exists; 16 `flush` records with `previous` ok | V |
| The start-up hooks and all 19 probes run on the camera | every event of the dictionary is in the file but `iv_*` of a long sequence | V |
| The firmware records four pairs of its own errors at every start: `0x19000C03` (caller 0x7E4261AF) and `0x19000C02` (caller 0x7E4261D8), one pair on CPU 0 at 19 ms and three on CPU 1 at 46, 92 and 96 ms | both sessions, the same arguments each time (0x602A9B40 / 0x7E8DA000, 0x603B2E38 / 0x7E47D7C4, 0x603F4674 / 0x7FFEA000, 0x60404674 / 0x7FFDA000). The code at 0x7E426197 is stock: it tests bit 31 of a word and reports when the bit is clear | V that they occur. Meaning, from the code (I): the routine 0x7E426045 sets up a transfer for a channel of the table at 0x600012CC (source, destination, count). It tests bit 31 of the source and of the destination address. An address with bit 31 clear is a cached address: the routine records the code and then calls the cache routine 0x7E45DA9D before it starts the transfer. The arguments fit: 0x603F4674 is the RAM image of the settings bank and 0x7FFEA000 its flash copy. So these are four start-up copies with cached addresses, handled by the stock code. They are not from the stabiliser |
| The emulator's two `0x2A001001` errors do not occur on the camera, and the camera's `0x19000C0x` errors do not occur in the emulator | this file against the emulator runs | V |
| The ring RAM keeps its content over a restart without power-off, and loses it at power-off | in both sessions the first four CPU 0 records are `recovered` and `boot` has the count 1; session 2 starts with `ring_restart` | I (it also means that each power-on has two starts of CPU 0) |
| Peaking: Red, Yellow and Blue ran the colour pass (`pk_latch` C = 2, 4, 5; `pk_pass9` with the picture at 0xB596A940 and first line bytes 1 to 255) | session 1 | V |
| Velvia (art 167) went through the six-axis handler 0x7E880FD4 47 times with no fault | `art_sixaxis` | V |
| Level Adjust: the working set at start is x −26, y 1020, z −9 in both sessions, so the calibration stays over power-off. After Adjust in session 2: x −25, y 1018, z −5 | `lv_values`, `lv_adjust` mode 1 | V |
| Interval: one sequence of 2 frames ran to its end (`iv_frame` 1 and 2, `iv_end` frames 2); four other starts ended with 0 frames | session 1 | V; why 0 frames is U (a cancel or the menu) |

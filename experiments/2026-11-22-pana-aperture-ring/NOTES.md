# 2026-11-22: what a Panasonic lens with an aperture ring sends (GitHub issue #3)

Labels: V = verified (firmware bytes, emulator run), I = inferred, U = unknown.

## 1. Purpose

Issue #3 asks that Panasonic lenses with an aperture ring (the tester has a Leica DG 15mm f/1.7) set the aperture on
this body. Before any feature: one camera run with a probe build that records what the body receives from such a lens
while the ring turns. This folder has the probe; the aperture feature is not built.

## 2. What the firmware shows (stock 1.6 block 0, base 0x7E421020)

| Fact | Label | Evidence |
|---|---|---|
| `lens_info_get(0)` 0x7E51FD09 returns the lens state 0x604F657C; `av_effect` (u16, 1/256 EV) at 0x604F658C | V (address), I (unit: `experiments/2026-11-17-osd-info/NOTES.md` 2.2) | disassembly |
| `set_func_flag_pana` 0x7E523495: `movhu d0,(0x604f8888)` (6 B) stores `l_func_flag_pana`; bit 0x01 of the value sets bit 0x01 of the flag byte 0x604F7F64, bit 0x02 sets or clears bit 0x02; a value without bit 0x01 clears both. Ends `retf [],0` at 0x7E5234D4 | V | disassembly |
| Callers of `set_func_flag_pana`: the packet handler 0x7E523480 (called by the lens packet dispatcher 0x7E52E711, value from the packet), 0x7E523511 (value 3 when the maker test gives 1 and the u16 at 0x604F67B2 is 1, 3 or 4, else 0), and the two reset paths 0x7E51CB41, 0x7E51DE3B (value 0) | V | `build/map/calls.tsv`, disassembly |
| `set_stat_pana` 0x7E5234D7: `movhu d0,(0x604f88ce)` (6 B) stores `l_stat_pana`; the next instruction (0x7E5234DD) is `btst 1,(0x604f7f64)`. The firmware uses only bit 0x01 of the value: flag bit 0x04 = stat bit 0x01 when flag bits 0x01 and 0x02 are set | V | disassembly |
| Callers of `set_stat_pana`: the status-packet parsers 0x7E523915 (site 0x7E523A64, command 84) and 0x7E52128F (site 0x7E52134C, command 34), both called from the lens packet dispatcher 0x7E52E711; the reset paths 0x7E51CB47 and 0x7E51DE41 (d0 = 0, a2 whatever their caller left). No caller uses the return value or d1, a0, a1 after the call | V | disassembly of each call site |
| The dispatcher chooses the parser by the command id of the request (u16 at 0x60502654), not by a length: 69 → 0x7E523915 with field mask 0, 75 → mask 1, 81 → mask 2, 84 → mask 6; 34 → 0x7E52128F. The status request builder 0x7E53431F asks 84 when the Panasonic test 0x7E5223DF is true, else 81 when 0x7E52250F is true, else 69; 0x7E533D5A asks 34 in place of 33 for a Panasonic lens. 84 vs 81 vs 69 are command ids: the reply length is not in them | V | disassembly of 0x7E52E711, 0x7E53431F, 0x7E533D5A |
| Command 84 (parser 0x7E523915, d0 = packet, d1 = count, a0 = sub-mask: bytes 16 and 17 of the dispatcher's context; I: they are the request word 0x60502656 that 0x7E53431F writes, 0x0202 with \| 0x0400 and \| 0x0800 by two lens tests, so count 2 and sub-mask 0x02, \| 0x04, \| 0x08). Packet bytes, little endian, into the lens state 0x604F6580 (lens state + 4): 0-3 u32 → +0; 4 → +4; 5 → +5; 6-7 u16 → +8 (× 5, 0xFFFF → -1); 8-9 u16 → +12 = `av_effect`; 10 → +14; 11 → +15; if sub-mask 0x04: 8 × u16 → +16; `count` × u16 → +34 (values -32768 skipped); if sub-mask 0x08: 2 × u16 → +544, +546; then, for field mask 6, the u16 `stat` → `set_stat_pana`, and the parser ends. Stat is at byte 12 + 2·count (+16 with sub-mask 0x04, +4 with 0x08): byte 16, 20, 32 or 36 with count 2 (I). Every byte before stat is stored; nothing after stat is read. For mask 2 (command 81) the Olympus-private part (N u32 at 0x604F888C, N from 0x604F8840, and a u16 at 0x604F88CC) takes stat's place | V (parse), I (count and sub-mask values) | disassembly of 0x7E523915 |
| Command 34 (parser 0x7E52128F, Panasonic only). Packet bytes into 0x604F6580: 0-1 u16 → +0 (bits changed); 2 → +4; 3-4 u16 → +8 (× 5); 5-6 u16 → +12 = `av_effect`; 7-8 u16 → +34; bytes 9-11 skipped (`add 3,a2`); 12-13 `stat` → `set_stat_pana`; nothing after is read | V | disassembly of 0x7E52128F |
| So the Panasonic-specific bytes the firmware does not extract are: command 84, whatever follows stat; command 34, bytes 9-11 and whatever follows stat. How long each reply is (whether bytes follow stat at all) | V (what the parsers read), U (reply length) | the camera run of this probe |
| `av_effect` comes from the same packet as stat, read before it (command 84 bytes 8-9, command 34 bytes 5-6) | V | as above |
| Lens maker test 0x7E522622: 1 when byte 0 of 0x604F67B0 is 2 or 3 and byte 1 is 0. The Panasonic test 0x7E5223DF: maker 1 and flag bit 0x01 | V | disassembly |
| No instruction branches into the replaced bytes of any of the four sites | V | `build/map/linear.txt`, the generator's word search |
| Whether `l_stat_pana` or `l_func_flag_pana` carries the ring position, its encoding, the A position | U | the camera run of this probe |
| Whether the ring acts through the normal aperture report (`av_effect`) | U | the camera run of this probe |
| How often the packets come, on which task and CPU | U | the camera run (record count, CPU of the ring) |

## 3. The probe

Spec `data/specs/pana-ring-probe.json`, written by `scripts/mkspec.py` (listing `results/pana-ring-probe.lst`). A delta
on the pinned build `peaking-mf`: every hook site is stock bytes, every `expect` is a byte string of that build.

| Event | Hook | Record | Arguments |
|---|---|---|---|
| `pana_stat` (2304) | 0x7E5234D7 (6 B: `jmp T_PS` + nop) | when arg0 differs from the last `pana_stat` | arg0 = `stat` (low 16, the new `l_stat_pana`) \| `av_effect` << 16; arg1 = `func` (`l_func_flag_pana`) \| `flags` (0x604F7F64 before this call) << 16 |
| `pana_func` (2305) | 0x7E523495 (6 B: `jmp T_PF` + nop) | when arg0 differs from the last `pana_func` | arg0 = the new `l_func_flag_pana`; arg1 = the lens id word at 0x604F67B0 |
| `pana_pk84_0`, `pana_pk84_1` (2306, 2307) | 0x7E523A5B in parser 0x7E523915 (8 B: `mov a2,a0` / `call 0x7E507F65`, the read of stat; `jmp T_PKA` + 3 nop) | a pair when the 16-byte window changes, at most one pair per 0.5 s | the window = stat (b0-b1) and the 14 bytes after it (b2-b15); each argument 4 bytes, lowest byte first |
| `pana_pk34_0`, `pana_pk34_1` (2308, 2309) | 0x7E521343 in parser 0x7E52128F (8 B: the same two instructions after `add 3,a2`; `jmp T_PKB` + 3 nop) | as above | the window = the 3 skipped bytes (b0-b2), stat (b3-b4) and the 11 bytes after it (b5-b15) |

- T_PS and T_PF do the replaced store, save d0, d1, a0, a1, mdr, lir, lar (and d2 in T_PS) with `movm`, call
  log-menu-3's `log_chg` (which keeps every register and the flags), restore, and jump back to the next stock instruction
  (0x7E5234DD, 0x7E52349B). The flags are not kept; the next stock instruction that reads them sets them first (V).
- T_PKA and T_PKB save d0, d1, a0, a1, mdr, lir, lar, call `pk_core` (frame [d2,d3,a2,a3],28), restore, run the two
  replaced instructions and jump back (0x7E523A63, 0x7E52134B). At both sites a2 is the packet position of stat (V, the
  parsers' own reads), so the window needs no check of a2; `set_stat_pana`'s entry was not used because the reset
  callers pass an arbitrary a2. The replayed call leaves mdr at its return address in T_PKA/T_PKB; the next stock
  instructions (`exthu d0`, `call set_stat_pana`) set mdr again before anything reads it (V).
- `pk_core` reads the 16 bytes with the firmware's byte-wise u32 read 0x7E507F7D (any alignment), makes a key
  ((w0·3 + w1)·3 + w2)·3 + w3 (odd factors: a change of one word always changes it), and writes the pair with `log_put`
  when the key differs from the last logged key and 0.5 s has passed since that pair. A change within 0.5 s keeps the
  old key, so it is written at the next packet after the 0.5 s. A change that goes back within 0.5 s is not seen.
- Fields left out of the window keys, and why: every byte before stat. The parsers store all of them in the lens state
  (focus position, distance, aperture report: U which is which), some change all the time while the lens moves, and
  the aperture report `av_effect` is already in `pana_stat`. The window's own bytes after stat are U: if one of them
  changes with every packet (a counter), the 0.5 s limit keeps the probe to 4 records per second per command.
- Bytes past the end of a reply: the window can read past the last byte the lens sent (reply length U). The buffer is in
  RAM (I), so the read is safe; bytes the reply does not cover keep older content and do not change, so they write
  nothing.
- Changes from the brief, and why:
  - `av_effect` is in arg0 of `pana_stat`, so the gate also writes a record when only the aperture report changes.
    If the ring acts through the normal aperture report, `stat` stays and `av_effect` moves. `func` moved to arg1; it is
    also logged on its own by `pana_func`.
  - `pana_func` uses `log_chg`, not `log_put`: 0x7E523480 is a packet handler, its rate is U, and an ungated record
    per packet could fill the ring (512 records per CPU). A detach and attach still gives records (0 at the reset, the
    lens's value after).
- Gates: {u32 last arg0, u8 budget 0} at PST+104 and PST+112 (0x7E4FD0A8–0x7E4FD0B8, uncached alias 0xBE4FD0A8). The
  log's state block is 128 B, cleared by T_BOOT at each start; log-menu-3 uses PST+0 to PST+100 (V, its generator's
  symbols and a search of the pinned specs for these addresses). A first value of 0 gives no record (the gate starts at 0).
- Window keys at PST+120 and PST+124 (0x7E4FD0B8, 0x7E4FD0BC; cleared at each start, so the first window of a session
  is written). The time of the last pair at 0x7E4FD300 and 0x7E4FD304 (uncached 0xBE4FD300; after the log's block
  buffer, the RAM of log-movie-time before it was made history, the same evidence as the log's RAM, I). Not cleared at
  start: a stale value delays the first pair of a session by at most 0.5 s.
- Routines: 288 B at 0x7E69EC6B–0x7E69ED8B, segment 1, in log-movie-time's former run of lss-core's area
  0x7E69E9EA–0x7E69EEAF (code of lss-core and of log-movie-time has run there on the camera); 292 B of the area stay
  free after it, so no other spec's space was needed. Hooks and routines are in segment 1, `log_chg`, `log_put` in
  the kernel range, 0x7E507F65 and 0x7E507F7D in segment 1: nothing reaches a later segment.
- Stack: 52 B more on the caller's stack in T_PS, 64 B in T_PKA/T_PKB (V, emulator). Which task's stack it is, and its
  margin, is U; the log's other probes use the same pattern.
- Dictionary: `data/logdict/events.json` gets `pana_stat`, `pana_func` and the four window events; build id
  8bf70fea0397b1f2, written into the
  flush task's block header. The pinned build's dictionary is kept as `data/logdict/events-afe27672d672fc95.json`
  (gen/log-menu/mkspec.py reads it from there; it regenerates `log-menu-3.json` byte for byte).
- Build description `data/builds/pana-ring-probe.json`: the 20 pinned specs and this one, label 2026.11.20,
  `first_code: true`.

### 3.1 Free space: two ledger rows

Every free run in the kernel range and segment 1 is claimed by a spec in `data/specs/` (the largest left is 14 B). The
routines take the run of `log-movie-time` (0x7E69EC6B–0x7E69EE0B), a probe that cannot go into a build with
log-menu-3. `epm2mod make` refuses the overlap until the ledger says so. These two rows are in
`tools/space-ledger/superseded.tsv` (added 2026-11-22). With them the check passes, and the pinned build's check and
`freespace.py selftest` also pass:

```
data/specs/log-movie-time.json	history	the timing probe of debug-log-movie-time (camera log 2026-11-19-debug-log-movie-time): a delta on epm2mod-2026.11.19 and log-menu-2, run on the camera; pana-ring-probe reuses its run 0x7E69EC6B in lss-core's area (experiments/2026-11-22-pana-aperture-ring/NOTES.md)
data/specs/movie-ab.json	history	the A/B switch of debug-log-movie-ab (camera log 2026-11-19-debug-log-movie-ab: work stopped): a delta on log-movie-time, run on the camera (experiments/2026-11-22-pana-aperture-ring/NOTES.md)
```

`movie-ab` needs its row too: its build-id edit sits on log-movie-time's, and the tool accepts that stacking only while
log-movie-time is current. The ledger does not change the firmware bytes: the sha256 below is the build either way.

## 4. Checks (exit status 0 = pass)

| Check | Result |
|---|---|
| `uv run python emulator/hookcheck.py data/specs/pana-ring-probe.json` | PASS, 18 transfers, all segment 1 or kernel (`results/hookcheck.txt`) |
| `emulator/hookcheck.py` on the build's 21 specs | PASS, 278 transfers, 0 FAIL (`results/hookcheck-build.txt`) |
| `emulator/boot-test data/builds/pana-ring-probe.json` | PASS (`results/boot-test.txt`; also run by `epm2mod make`) |
| `emulator/update-path-test data/builds/pana-ring-probe.json` | PASS (`results/update-path-test.txt`; also run by `epm2mod make`) |
| `scripts/emu_pana.py`: both setters called as their callers call them, 42 inputs each (6 values × 7 flag bytes); both parser sites run from the site to the next stock instruction, 4 alignments × 4 windows each; pinned build against probe, real `log_chg` and `log_put` | PASS (`results/emu-pana.txt`): the same variables, flag byte and registers as the pinned build (mdr left out at the parser sites, see section 3), no other RAM written; setters: one record per changed arg0, none for a repeat, none with Off; windows: a pair with exactly the input's 16 bytes for a new window, none for the same window, none for a change 20 ms after a pair, the pair for it at 600 ms, none with Off |
| `tools/freespace.py check --first-code` (the build's specs; the pinned build's specs) | PASS, PASS |
| `uv run python -m unittest discover -s cli/tests` | 269 tests OK |
| `uv run epm2mod generate --check` | up to date (untested builds have no row in `data/builds/README.md`) |
| `epm2mod log` on a made-up file with all six events | decodes: `stat`, `av_effect` (decimal), `func`, `flags`, `lens_id`, and the window bytes `b0` … `b15` |

The emulator has no lens: it cannot show that the sites run with a lens attached, or any value a lens sends. Its
timer runs by itself, so the check moves the stored time of the last pair to let time pass.

## 5. Build

- `uv run epm2mod make pana-ring-probe`
- sha256 **f4423ae3dd4659d7b81fc61098b764b694c9e5feef72f93a6670b876e925887a** (the first build of this name,
  ec1765c0…, had only `pana_stat` and `pana_func`; it was not flashed)

## 6. Test sheet (camera run)

**Before the flash**

1. Copy the card's `EPM2LOG.BIN` away and delete it from the card, so the file holds only this session.
2. Flash: `epm2flash pana-ring-probe f4423ae3dd4659d7b81fc61098b764b694c9e5feef72f93a6670b876e925887a`
3. Way back: `epm2flash peaking-mf 6a47806dfafce15d281358eae2beffe397132e5999c50b28c69b2a2467efcf39`

**Set-up** (menu paths from the manual, p. 17, 25, 26, and `docs/user/debug-log.md`)

4. MENU → SETUP → Custom Menu → J → Debug Log → On → OK. (No Custom Menu tab: MENU → SETUP → Setup Menu → Menu Display
   turns it on.)
5. Attach the Panasonic lens with the aperture ring on **A**. Turn the camera on.
6. Press MENU. On the first screen press ◀/▶ to the P/A/S/M column, ▲/▼ to **A**, press OK.

**Steps** (pause about 2 s after each click; each press of ▶ writes the log so far)

7. Turn the aperture ring one click at a time from the widest stop (1.7) to the smallest (16), then back to **A**.
   Press ▶ (playback), then ▶ again to go back.
8. With the ring on **A**: press ▲ (F button), then ▲/▼ through a few apertures. Press ▶, then ▶ again.
9. Press MENU, ◀/▶ to the P/A/S/M column, ▲/▼ to **M**, press OK. Repeat step 7.
10. Turn the camera off. Detach the lens, attach it again, turn the camera on, wait 5 s.
11. Turn the camera off (this writes the log). Copy `EPM2LOG.BIN` from the card.

Read it with `uv run epm2mod log EPM2LOG.BIN` and `uv run epm2mod log EPM2LOG.BIN --json > log.json`.

| Result | Meaning |
|---|---|
| `pana_stat` with a new `stat` at each click of steps 7 and 9, and one value for **A** | the ring position is in `l_stat_pana`: its encoding is in the values; the feature can read it there |
| `stat` constant, `av_effect` changes at each click | the lens reports the ring through its normal aperture value |
| `stat` and `av_effect` change only in step 8, and a `pana_pk84` or `pana_pk34` byte other than stat changes at each click and has one value for **A** | the ring position is in that packet byte (b2-b15 after stat in command 84, b0-b2 or b5-b15 in command 34): its encoding is in the values; the feature can read it from the packet at the parser |
| `stat`, `av_effect` and every window byte change only in step 8 | the ring position is in none of the bytes the body receives in these two replies: the lens may need a request the body never sends (next: the request words 0x60502656 and the other commands of the dispatcher) |
| Window bytes that change at every record pair, also with the ring and the camera still | a counter or a moving value in the reply: leave those bytes out when reading the others (pairs come at most every 0.5 s per command) |
| Only one of `pana_pk84` / `pana_pk34` appears | the body sends only that command to this lens; its bytes are the ones to read |
| No `pana_stat`, no `pana_func` and no window events | the body does not treat the lens as Panasonic (flags 0x01, 0x02 not set) or these parsers do not run with it: the next probe logs the lens packet dispatcher 0x7E52E711 |
| `pana_func` in step 10 with `lens_id` | the lens's id and function flags (flags 0x01 and 0x02 say what the body enabled) |
| A `gap` marker in the log | more records than the ring holds between two writes: the gate's key changes faster than expected (the record count tells the packet rate) |

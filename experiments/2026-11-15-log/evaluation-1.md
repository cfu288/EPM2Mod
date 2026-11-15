# Evaluation 1 of the structured log: the first file from the camera

Date: 2026-11-15. Build on the camera: `debug-log`, sha256 `e74f1aec…bda8`, build id `d1ddd46b4dac2414`.
The file: `EPM2LOG.BIN`, 32,256 bytes, 63 blocks. It is not in the repository.
Decode: `uv run epm2mod log /path/to/EPM2LOG.BIN --summary`, or without `--summary` for JSON lines.

Labels: **V** verified (bytes of the file, or the firmware code), **I** inferred, **U** unknown.
Addresses are those of block 0 of the build. Times are seconds after power-on.

## 1. Short answer

| Question | Answer |
|---|---|
| Is the log right? | Yes for the records, the order and the time. Three faults were in the reading, not in the camera: the decoder's session numbers, its `recovered` marks and one time. They are corrected (section 6) |
| Does each probe report what its name says? | All 20 sites are on the camera's paths, and 18 of the 22 events report what their names say. The four others: `boot` (`poweron` is read too early and is always 0; `session` is not a session number), `iv_start` (it is the arming of the mode), `iv_frame` and `iv_end` (they leave out the last frame) |
| Faults of the mod | None in the records: no firmware error after start-up, each start has its end, each photo has the table of its look |
| What to look at | Live view runs at 3 to 7 frames per second while coloured peaking lines show. Interval Time 1 s gave a frame each 3.2 to 3.4 s |

The file has 1,278 records and 2 markers (the first note said 1,280 records).

## 2. Is the log itself right?

| Check | Result | Label |
|---|---|---|
| Record numbers | Each of the four rings (2 sessions × 2 CPUs) runs from 0 without a step: 579, 584, 79 and 36 records. The 16-bit number in each record agrees. No `gap` marker, drop count 0 in all 63 headers | V |
| Blocks | 63 blocks of 512 bytes. The bytes after the last record of each block are zero | V |
| Time order | In each ring the time never goes back, and no two records have the same time. Bits 30 and 31 of every timer value are 0 | V |
| Timer start | The first record of CPU 0 is at 19,497 µs in session 1 and at 19,480 µs in session 2. CPU 1: 45,688 and 45,666 µs. `boot`: 101,070 and 101,040 µs. So the timer runs before the first record and starts again at each power-on | V |
| Timer unit | `recordingDone_interval` starts a timer of Interval Time × 1,000 ms (0x7EA997E5). The callback at the end of that timer comes 1.011 s and 1.029 s after the two `iv_frame` records. That fits 1 µs per step if Interval Time was 00:00:01 | V for the numbers, I for the setting: ask the owner |
| Timer wrap | The longest session is 278 s. The timer wraps at 1,073 s. The wrap code of the decoder did not run on camera data | U on the camera, V in the unit tests |
| Two records 1 µs apart | Each `fw_error` and its `fw_error_args` are 1 to 2 µs apart: about 25 instructions | V |
| Flush | 16 flushes, each started 6 to 22 ms after the GUI state that asked for it. A flush record holds the result of the flush before it in its session: 14 results, all `ok`. The last flush of a session has no result in the file. 23 states could start a flush; the 7 without one came while a flush ran (0x5701 after 0x5700, 0x2001 after 0x2000). None was refused for a busy card | V |
| Flush at power-off | Both sessions end with the flush record of state 0x2000, and that record is in the file. The write ends before the power goes | V |

### 2.1 What happens at start-up

| Time | CPU | Record | Code |
|---|---|---|---|
| 19.5 ms | 0 | 2 error pairs: the reset code copies `.data` (0x7E421115) | the error hook is in the pre-reset range |
| 46, 92, 96 ms | 1 | 6 error pairs: `prm init` copies CPRAM and loads two settings banks (0x7E4573AB) | |
| 101 ms | 0 | `boot`, argument 1 | hook at the entry of Usr0 |
| 209 ms | 0 | `pk_heap_mode` 2 | |
| 215 ms | 0 | `lv_values` | |
| 1.65 s | 1 | first live-view frame: `film_stage`, `film_matrix`, `art_sixaxis`, `film_curve` | |
| 1.77 to 2.25 s | 0 | GUI states 0x1001, 0x1002, 0x1003, 0x5000, 0x5100 | |

- **There is one start of CPU 0 per power-on, not two (V).** The four CPU 0 records before `boot` are the
  errors at 19.5 ms. `log_put` makes a new ring when it finds no magic word. So the first error record makes
  the ring. The boot hook `T_BOOT` runs 82 ms later, finds the magic word and adds 1 to the restart count.
  The headers show it: the first CPU 0 block of each session has first record 0 and restart count 1.
- **The first note read this as "the ring RAM survives a restart without power-off". The file does not show
  that (V).** It shows only that the RAM was clear at both power-ons: both rings start at record 0 in
  session 2. How long the camera was off is not known.
- **Does the ring survive a restart after a crash? Still U.** No restart without power-off is in the file.
  The sign will be a `boot` record with the argument 2 or more, and records with `recovered: true` before it.
- **The time 1,073,761,304 µs was a decoder fault (V).** The decoder kept the last time of session 1 across
  the ring restart, saw a smaller time and counted a timer wrap.
- **The decoder's session numbers were wrong (V).** It counted a session from the `boot` record, so the four
  early records got the number of the session before, and the mark `recovered`. A session now begins at the
  records that the same start put before `boot`.
- **The argument name `session` was wrong (V).** It is the restart count of the ring. On the camera it is 1
  for a cold start, because of the early error records. In the emulator it is 0, because the emulator's
  errors come after `boot`. The name is now `ring_found`.
- **`poweron` is 0 because the hook reads it too early (V).** The firmware sets the factor (u16 0x604154E6) and
  the wake byte in 0x7E45D1F3, from the system controller register 0x98E00048. Usr0 calls that routine at
  0x7E504090, 700 bytes after its entry, where `T_BOOT` runs. The place is right; the time is wrong.

### 2.2 The eight error records of each start

The first reading was right. Details from the code of 0x7E426045 (V):

- The routine takes a request `{source, destination, byte count, …}`. It writes the source to register +4 and
  the destination to register +8 of a channel of the table 0x600012CC (20 bytes per channel).
- It reads the destination back. Bit 31 clear: error `0x19000C03` with the destination.
- It reads the source back. Bit 31 clear: error `0x19000C02` with the source and the byte count. Then it calls
  the cache routine 0x7E45DA9D with the CPU locked.
- It starts the copy (bit 16 of the control register), waits for bit 24, and calls the cache routine again when
  the destination has bit 31 clear.

| # | CPU, time | Source → destination | What | Label |
|---|---|---|---|---|
| 1 | 0, 19.5 ms | 0x7E8DA000 → 0x602A9B40 | the `.data` section: 102,676 bytes, reset code 0x7E4212B8 | V |
| 2 | 1, 46 ms | 0x7E47D7C4 → 0x603B2E38 | the CPRAM values of the settings store (`prm init`, 0x7E4573B7) | V for the addresses, I for the name |
| 3 | 1, 92 ms | 0x7FFEA000 → 0x603F4674 | the EEROM settings bank, 64 KiB, from flash (it holds the level gauge's working set) | V |
| 4 | 1, 96 ms | 0x7FFDA000 → 0x60404674 | the MODE settings bank, 64 KiB, from flash (it holds setting 458, the peaking colour) | V for the addresses, I for the name |

They are stock, they come at every start, and they are not faults. The decoder now names the eight addresses.

## 3. Each probe

| Event | Count | Values seen | Fits the code? | Label |
|---|---|---|---|---|
| `boot` | 2 | restart count 1, `poweron` 0 | Section 2.1: the count is right, its name was wrong, `poweron` is read too early | V |
| `flush` | 16 | state 0x5705 × 9, 0x5700 × 5, 0x2000 × 2; result `ok` | yes | V |
| `fw_error`, `fw_error_args` | 16 + 16 | section 2.2 | yes | V |
| `gui_state` | 170 | 19 states, table below | yes | V |
| `pk_mf_start` | 3 | R = 1, L = 0; C = 0, 2, 4 | yes; C is the colour of the run before (below) | V |
| `pk_mf_end` | 5 | 2 at start-up with all bytes 0; 3 with L = 1, R = 0, L2 = 1 | yes: R is cleared first | V |
| `pk_latch` | 12 | 4 per MF Assist run | yes (below) | V |
| `pk_heap_mode` | 26 | modes 2, 1, 0 | yes; it is not only a peaking event (below) | V |
| `pk_pass9` | 9 | picture 0xB596A940; gain 0; first pixel 1, 43, 47, 84, 255 | yes (below) | V |
| `art_sixaxis` | 136 | 12 art codes, one handler per code | yes | V |
| `lv_adjust` | 1 | mode 1 (Adjust), rotate 1 | yes | V |
| `lv_values` | 3 | section 3.6 | yes | V |
| `iv_start` | 5 | result 0, state 1 | The site is right. The name misleads (section 3.5) | V |
| `iv_frame` | 2 | n 1 and 2, state 0 | The sequence had 3 frames (section 3.5) | V |
| `iv_end` | 3 | result 0; frames 0, 2, 0 | as `iv_frame` | V |
| `iv_state_set`, `iv_state_clear` | 18 + 17 | bits 1, 2, 4 and 0xFFFFFFFF | yes (section 3.5) | V values, I meanings |
| `film_stage` | 329 | 13 codes; flags 0, 1, 0x3001 | yes; 150 of them are an effect of the gate (section 3.3) | V |
| `film_matrix` | 139 | 7 tables, 3 values of d3 | yes: all 139 have the table of the art code of the stage record before them | V |
| `film_curve` | 151 | one handler per code | yes | V |
| `shoot_cbs` | 199 | 23 numbers | yes; 13 have a name in the firmware | V |

### 3.1 GUI states

The group names are those of the state tables in the firmware (feature map, section 16b). The meaning of a
single state is read from this file: what the camera logged beside it.

| State | Count | Time in it | Screen | Label |
|---|---|---|---|---|
| 0x1001, 0x1002, 0x1003 | 2 each | 0.04, 0.05, 0.36 s | Boot | V group |
| 0x5000 | 50 | 3 to 71 ms | ShootingCommon: live view starts. Each return to shooting goes through it | I |
| 0x5100 | 45 | up to 13.5 s | ShootingStill: live view | I |
| 0x5101 | 10 | 0.3 to 3 s | ShootingStill: the shutter button is down (`CBS_START_READY` comes with it) | I |
| 0x5600 | 16 | 0.18 to 0.29 s | ShootingAssist: the INFO button is held. The group has a handler for the release of INFO. 14 of the 16 are in session 2, after Level Adjust | I |
| 0x5700 | 5 | 7 to 14 ms | ShootingMenu: MENU opens | V (emulator) |
| 0x5701 | 5 | 15 to 75 s | ShootingMenu: the menu | I |
| 0x5705 | 9 | 1.7 to 17.6 s | ShootingMenu: the live control (OK) | V (emulator) |
| 0x5A00 | 3 | 2.0, 5.3, 8.8 s | ShootingLvMagnify: the magnified view. `pk_mf_start` is 1 to 13 ms before it | V |
| 0x5B00 | 5 | 0.1 to 3.9 s | ShootingInterval: armed, waits for the shutter button | I |
| 0x5B01 | 3 | 0.9 to 2.6 s | ShootingInterval: the shutter button is down | I |
| 0x5B02 | 3 | 2.1 to 2.8 s | ShootingInterval: the sequence runs and waits for a frame (`CBS_START_INTERVAL_SHOOTING` comes with it) | I |
| 0x5B03 | 3 | 0.3 to 2.4 s | ShootingInterval: a frame is taken | I |
| 0x5B04 | 1 | 2.4 s | ShootingInterval: the sequence is done; progress 0, 33, 66, 100 | I |
| 0x0002 | 2 | 0.15, 0.21 s | between shooting and power off | U |
| 0x2000, 0x2001 | 2 each | – | Misc: power off | V group |

No state 0x3xxx (Play) is in the file: no playback in these two sessions (V). The decoder prints these names
(`names.state`). The other groups are in the dictionary too: Play 0x30xx, PlayHdmi 0x40xx, ShootingPanorama
0x52xx, ShootingMovie 0x53xx, ShootingLvGuide 0x54xx, ShootingModeDirect 0x58xx, ShootingFuncDirect 0x59xx,
ShootingMvTelecon 0x5Cxx, Pc 0x60xx.

### 3.2 Shooting callbacks, and the number of photos

The callback sender 0x7E995A0B has one caller: the dispatcher 0x7E995C0B. It tests a message number and sends a
CBS number. 13 of the numbers in the file have a trace text at their place in the dispatcher (V). The others
are named from their place in a capture (I).

| CBS | Count | Name | Label |
|---|---|---|---|
| 210, 208, 213 | 15 each | `CBS_START_SHOOTING_PICTURE`, `CBS_START_READY`, `CBS_START_FOCUS`: the shutter button goes down (half-press) | V |
| 214, 209 | 11 each | `CBS_END_FOCUS`, `CBS_END_READY` | V |
| 233 | 17 | `CBS_ENABLE_AFL` | V |
| 211 | 15 | `CBS_END_SHOOTING_PICTURE`: the button is up, or the exposure is done | V |
| 136 | 6 | **the capture starts** (message 26784) | I |
| 21 | 6 | 35 to 85 ms after 136 (message 26757) | I: exposure |
| 93 | 9 | twice per capture (messages 26758, 26791) | U |
| 162 | 6 | 0 to 7 ms after 211 of a capture | U |
| 89, 27 | 6 each | 0.2 to 0.6 s and 0.7 to 1.1 s after 211 | I: the record starts, ends |
| 219 | 6 | the last of a capture; 5 to 13 ms after `iv_frame` | I: the picture is recorded |
| 258 | 15 | `CBS_START_THROUGH_IMAGE_PROCESS`: live view starts again | V |
| 167, 155 | 14 each | a pair, 7 to 24 ms apart, before each menu state | I: live view stops |
| 231 | 2 | sent beside the trace `evTraResShtMfAssistTimeOut`: MF Assist ends by its timer | V |
| 259, 260, 261, 263 | 1, 1, 3, 1 | `CBS_START_INTERVAL_SHOOTING`, `CBS_END_INTERVAL_SHOOTING`, `CBS_END_INTERVAL_SHOOTING_TIMER`, `CBS_END_CREATE_MOVIE` | V |
| 3 | 4 | results 0, 0x21, 0x42, 0x64 = 0, 33, 66, 100 | I: progress in percent |

**Six photos, all in session 1 (I, from callback 136):** Portra at 34.4 s, Ektachrome at 44.1 s, Velvia at
68.1 s, and three interval frames with Superia 400 at 226.3, 229.9 and 233.4 s. Session 2 has a half-press and
no photo. The owner can compare this with the card.

### 3.3 Film looks

| Art code | Look (menu entry) | Six-axis handler | Curve handler | Matrix table | Label |
|---|---|---|---|---|---|
| 70 | Portra (Pop Art) | 0x7E56D566 | 0x7E56E8F3 | 0x7E880FC2 | V |
| 102 | Ektachrome (Soft Focus) | 0x7E56D706 | 0x7E56E94A | 0x7ECB099A | V |
| 71 | Pro 400H (Pale&Light Color) | 0x7E56D575 | 0x7E56E94A | 0x7ECB0988 | V |
| 72 | Kodachrome (Light Tone) | 0x7E56D584 | 0x7E56E905 | 0x7E768F58 | V |
| 145 | Vis 250D (Pin Hole) | 0x7E56D6F7 | 0x7E56E94A | 0x7ECB09AC | V |
| 167 | Velvia (Diorama) | **0x7E880FD4, the mod's handler** | 0x7E56E94A | 0x7ECB09BE | V |
| 85 | Superia 400 (Cross Process) | 0x7E56D5CF | 0x7E56E94A | 0x7E768F46 | V |
| 74, 91, 96, 163, 181 | Grainy Film, Gentle Sepia, Dramatic Tone, Key Line, Watercolor (stock) | 0x7E56D76A (74, 91, 163), 0x7E56D760, 0x7E56D5B1 | own | none | V |
| 3 | no art filter | – | – | none | V |

- The code → table pairs are those of the chooser at 0x7ECB08CD (V). The decoder prints the look
  (`names.art`) and the table (`names.table`).
- **Each of the six photos went through its look (V).** After each callback 136 CPU 0 logs two jobs with code 3
  (at +0.19 and +0.32 s), then the stage, the matrix table, the six-axis handler and the curve handler of the
  look (at +0.46 to +0.85 s). What the two code-3 jobs are is U.
- **`film_stage` with art 3 and 163, flags 0, 75 each:** this is live view while the peaking lines show. Each
  frame has two jobs: the plain picture (code 3, CPU 0) and the line job (code 163, Key Line, CPU 1, 10 ms
  later). The probe's gate holds the last code, and both CPUs use the same gate. So each job sees a new code
  and is logged. 75 pairs = 75 frames (V). It is not a fault of the feature. It is a side effect of the log.
- Flags: 1 in live view and stills; 0 while the shutter button is half down, and in the two peaking jobs;
  0x3001 for Grainy Film. With bit 16 or 17 the stage takes code 3 (0x7E56C692); not seen (V for the values, I
  for the meaning of bit 0).
- **The three d3 values are stack addresses (V).** d3 points to the result matrix in the stack frame of the
  stage (0x7E56C611). 0x604E8984 is always CPU 1 (live view). 0x60481F80 and 0x6047D2E4 are CPU 0 (stills): two
  tasks, or one task at two depths (U which). The argument is now named `stack`.
- **The picture pipeline runs on both CPUs (V).** CPU 1 logged 596 pipeline records. The notes said that only
  CPU 0 tasks log.
- While the Picture Mode list of the live control was open (47.6 to 63.4 s) the camera went through the 12
  entries about three times. Effect filters (91, 96, 163, 181) ran on CPU 0 with heap mode 1; the looks ran on CPU 1.

### 3.4 Peaking

| Run | Colour | `pk_mf_start` | L = 1 after | First pass 9 after | End | L = 0 after the end | Frames | Frame period, median (range) |
|---|---|---|---|---|---|---|---|---|
| 1 | Red | 10.833 s | 22 ms | 246 ms | timer (callback 231), 5.2 s | 290 ms | 30 | 179 ms (145 to 241) |
| 2 | Yellow | 104.171 s | 17 ms | 367 ms | timer, 8.7 s | 270 ms | 36 | 259 ms (151 to 342) |
| 3 | Blue | 132.685 s | 24 ms | 318 ms | not the timer, 2.0 s | 137 ms | 9 | 242 ms (145 to 306) |

- **C = 0 at the first `pk_mf_start` is not a fault (V).** C is not a mirror that follows the menu. `T_R`
  (0x7E4C93A4) reads setting 458 into C only when R is 1, in the mov task, in the call that then sets L. The
  probe at `entryMfAssistOn` runs before the next frame, so it shows the C of the run before: 0, then 2
  (Red), then 4 (Yellow). In all three runs the record that shows L = 1 also shows the new C. The colour pass
  reads C only when L2 is 1, and L2 follows L. **There is no frame with a wrong colour.**
- The order in each run is as designed (V): R = 1, then L = 1 and heap mode 1 in the same millisecond, then
  L2 = 1. At the end: R = 0, then L = 0 and heap mode 2, then L2 = 0.
- `pk_pass9` gain 0 is right for a colour: the loop wrote the lines, and the combine job adds nothing
  (0x7E4C9483). White would give 512. All 9 passes have the picture buffer 0xB596A940, the address that the
  scenario tests gave (V). So the CPU writes this buffer through the 0xB5… alias on the camera with no fault.
- `first_pixel` is one byte of the line image: 1 six times, then 43, 47, 84, 255. The line image is 1, not 0,
  where there is no edge (I). The values 43 and 47 are below the threshold 64: weak edges get no colour. Nine
  bytes are too few to judge the threshold (U).
- **Frame rate (V for the numbers):** 3 to 7 frames per second while coloured lines show. The frame time that
  the build asks for is 85 ms. Which part is the colour loop and which part is Key Line's own passes is U.
- `pk_heap_mode` logs every change of the image-work heap mode. `caller` is always 0x7E4C935E, because the
  peaking code replaced the one stock call of the setter and calls it from there (V). Mode 2: live view without
  art buffers, also at start-up. Mode 1: peaking, and each effect filter in the Picture Mode list. Mode 0: for
  3 ms, twice, when Watercolor ended (I for the meanings).
- `pk_latch.lv.art_type` is 1 while L is 1. With L = 0 it was 1 for Portra and 0 for Velvia (I: the entries
  that were moved to another art code are not art filters for live view).

### 3.5 Interval shooting

`iv_start` is the return of `OlyHfwOpeShoot::startIntervalShooting` (its own trace text, V). The GUI calls it
each time it shows the standby screen 0x5B00 with Time Lapse On. It arms the mode. A sequence starts later, with
callback 259.

| Time | What happened | Records |
|---|---|---|
| 213.7 s | the menu closes with Time Lapse On | `iv_start` 1, state 0x5B00 |
| 215.3, 216.4 s | two half-presses, released | bit 2 set and cleared; `iv_start` 2 and 3 at each release |
| 217.7 s | OK: live control | clear all, `iv_end` frames 0 |
| 221.3 s | back to shooting | `iv_start` 4 |
| 221.7 s | the shutter button | bit 2, focus |
| 224.3 s | **the sequence starts** | callback 259, bit 4, state 0x5B02 |
| 226.3, 229.5, 232.9 s | the timer ends, a frame is taken | callback 261, then 136 … 219 |
| 228.5, 231.9 s | frames 1 and 2 are recorded | `iv_frame` 1, 2 |
| 235.2 s | the sequence ends | callback 260, state 0x5B04, progress, callback 263 |
| 237.7 s | | `iv_end` frames 2, then `iv_start` 5 (armed again) |
| 241.6 s | MENU | `iv_end` frames 0 |

- **The sequence had 3 frames, not 2 (V).** The caller of `recordingDone_interval` compares the frame count
  with the total (0x7EA8C4F7). For the last frame it takes the end path and does not call the routine. So
  `iv_frame` and `iv_end.frames` give the frames less 1. The summary counts callback 261.
- `iv_end` with frames 0 is the mode being disarmed for a menu, not a failed sequence (V).
- **The interval is counted from the end of the recording (V).** `recordingDone_interval` starts the timer
  (485 × 1,000 ms). The timer callbacks are 3.18 s and 3.41 s apart: about 2.3 s for the frame and its file,
  then the timer. With Interval Time 1 s the camera does not take a frame each second.
- A time-lapse movie was made after the last frame: progress in 2.0 s, then `CBS_END_CREATE_MOVIE` with
  result 0 (I).
- State bits: 1 armed; 2 the shutter button was pressed in standby; 4 the timer before a frame runs (I).
  `clear 0xFFFFFFFF` clears all. Bits are set that are set, and cleared that are clear: stock code, no effect.

### 3.6 Level gauge

| Record | x | y | z | Length | temp |
|---|---|---|---|---|---|
| start of session 1 | −26 | 1020 | −9 | 1020 | 305 |
| start of session 2 | −26 | 1020 | −9 | 1020 | 305 |
| session 2, 0.97 s after `lv_adjust` mode 1 | −25 | 1018 | −5 | 1018 | 243 |

- The unit is 1000 = 1 g (level-gauge notes §12.1). The three values are a camera at rest in landscape: the
  length is 1.02 g, and y carries it (V for the numbers).
- The probe reads the working set in the RAM image of the EEROM bank. That bank is loaded at 92 ms (transfer 3),
  and the probe runs at 215 ms (V).
- The same set at two power-ons shows that the set is loaded from flash in the same way each time (V). It
  does not yet show that the Adjust of session 2 was saved: the file ends in that session. The next file's first
  `lv_values` must read −25, 1018, −5.
- Adjust took 0.97 s for its 100 samples (1.7 s in the emulator) (V).
- `temp` 305 and 243: the unit is U (0.1 °C fits: 30.5 and 24.3).

## 4. What the log says about the mod's health

| Item | Evidence | Verdict |
|---|---|---|
| Firmware errors after start-up | none in 278 s and 99 s | good |
| Peaking | 3 starts, 3 ends, the bytes in the designed order, 9 colour passes with gain 0, 75 frames | good |
| Film looks | 139 of 139 matrix records have the right table; 6 of 6 photos have their look | good |
| Velvia's six-axis handler (the mod's code at 0x7E880FD4) | 47 dispatches, live view and one still | good |
| Interval | one sequence of 3 frames ran to its end; the movie was made; the mode armed and disarmed 5 times | good |
| Level Adjust | one Adjust, the values changed by 1 to 4 units | good |
| The log's RAM (0x7E4F9000) | two sessions with rings and state in order: no other code wrote there | good (V for these sessions) |
| Flush | 16 of 16 ok, none slow to start; the time a flush takes is not logged | good, with a gap |

Points that need a decision or a probe:

| # | Point | Evidence | Proposal |
|---|---|---|---|
| 1 | **Live view at 3 to 7 frames per second with coloured peaking** | section 3.4. No White run and no stock Key Line run is in the file, so the cost of the colour loop is U | No flash needed: with the build that is on the camera, turn the ring once with White, once with Red, and once with Picture Mode Key Line and peaking Off. The `film_stage` records give the frame period of each. If Red is slower than White: read the line image through the cached alias, or every second row |
| 2 | **Interval Time is a pause, not a period** | section 3.5 | Say so in the guide: the time between frames is Interval Time plus about 2.3 s. No code change (NOTES §14 of the interval work explains why 0 is not safe) |
| 3 | The gates of `log_chg` are one for both CPUs | section 3.3: 150 of 329 `film_stage` records. With peaking on, each ring gets about 5 records per second, so a ring of 512 records is full after about 100 s without a menu | One gate set per CPU (section 5, probe C) |
| 4 | A capture or a movie start while the lines show; that R is cleared then | not done in this file | a camera step, no probe |
| 5 | The decoder calls a block a `repeat` when its records are byte-equal to the ones read before | Two starts log the same records at nearly the same times. A whole equal block needs equal times to the microsecond for all its records: not seen, very unlikely | none now |

## 5. Coverage: what is answered, and the next probes

| Open question (source) | State after this file |
|---|---|
| File calls from the flush task at menu and power-off (log notes §9) | V: works |
| `C:` is the card | V |
| The RAM at 0x7E4F9000 is free on the camera | V for two sessions |
| The RAM keeps its content over a restart | power-off clears it (V); a restart after a crash is U |
| The timer unit | 1 µs, within 3 %, if Interval Time was 1 s |
| The flush at power-off ends before the power goes | V |
| The probe sites are on the camera's paths | V for all 19; the pipeline also runs on CPU 1 |
| Full card, locked card, no card | not in this file |
| Peaking: CPU access to the buffers through the 0xA… alias (§16.4) | V |
| Peaking: the speed of the loop (§16.4), the frame rate (§13.6) | the frame rate is measured; the loop's part is U (point 1) |
| Peaking: the line image values, the threshold 64 (§16.4) | 9 bytes: 1 to 255; not enough |
| Peaking: R cleared after a capture; a capture while the lines show (§13.6) | not in this file |
| Level gauge: the calibration after power off and on (todo) | the stored set loads the same at two starts (V); the save of a new Adjust needs the next file |
| Level gauge: Reset; after a flash of another build (todo) | not in this file |
| Interval: cancel of a sequence, 240 frames, more than 90 s, a full card (todo) | not in this file. Seen: a full sequence, the movie, arming and disarming |
| Film looks: type II, other languages (todo) | not in this file |

Probes for the next debug build. None is built. Free space: 82 bytes in the two kernel-range areas of the log
(the log notes give 256 bytes for the kernel range in all), 384 and 755 bytes in the two segment-2 areas.

| # | Probe | Site | Cost |
|---|---|---|---|
| A | `poweron`: the factor and the wake byte after the firmware has set them. Take the two reads out of `T_BOOT` | 0x7E504097 in Usr0 (`mov 0x7E733554,a0`, 6 bytes, after the call of 0x7E45D1F3; no branch goes into it). Segment 1, so the routine goes into the kernel range | about 34 bytes + 6; `T_BOOT` gets 14 bytes shorter |
| B | `boot` counts restarts only: `log_put` writes −1 to the count when it makes a ring, so a ring made by early records gives 0 at `boot` | `log_put` and `T_BOOT` | about 10 bytes |
| C | Gates per CPU: `log_chg` and `log_cnt` add 64 × the CPU number to the gate address | `log_chg` (kernel range) | about 14 bytes, 64 bytes of RAM |
| D | With C the free frame clock of point 1 is gone. `pk_stats` at `pk_mf_end`: frames, and the longest time of the colour loop (two timer reads round the loop) | `T_COL` and `T_MFOFF` | about 50 bytes, 12 bytes of RAM. It needs room in the kernel range: move `T_COL`'s part to segment 2 only if the hook check allows it |
| E | `flush_end`: blocks written and the result, so the time of a flush shows | `f_result` in the flush task | about 14 bytes |
| F | `iv_frame` logs the firmware's own count (d0) in place of the probe's count; a record at the last-frame branch | `T_IVFRAME`; 0x7EA8C514 (`mov 6695,d0; mov a3,a1; call`, 9 bytes, segment 2) | 0 bytes for the first; about 35 + 9 for the second. Not needed: callback 261 already gives the frames |

A, B and E are cheap and remove the three known defects of the log. C and D belong together.

## 6. What changed in the tooling

| Change | Where |
|---|---|
| `epm2mod log FILE --summary`: sessions, lost records, errors, flushes, events, screens, and lines for peaking, looks, shooting, interval and level gauge | `src/epm2mod/logsummary.py`, `src/epm2mod/cli.py` |
| Names beside the numbers (`names` in each JSON line): GUI states, shooting callbacks, art codes with the film of `looks/films.json`, matrix tables, the mod's six-axis handler, peaking colour, heap mode, Level Adjust mode, the two error codes, the eight addresses of the start-up copies | `logs/events.json` (`tables`, `names`, `film_entries`), `src/epm2mod/eventlog.py` |
| Sessions: a session begins at the records that its start put before `boot` | `eventlog.py`, test `test_records_before_boot_belong_to_the_start` |
| `recovered`: only records of the session before that the new session wrote; also over more than one block, and for CPU 1 | tests `test_a_restart_that_kept_the_ring`, `test_recovered_records_in_more_than_one_block`, `test_an_old_record_is_not_taken_for_one_of_the_start` |
| Time: starts again at a ring restart and at a session | the same tests |
| Three argument names: `boot.session` → `ring_found`, `iv_end.frames` → `iv_frames`, `film_matrix.d3` → `stack`. Texts of 12 events corrected | `logs/events.json`, build id `bd632fb32c6e7094` |
| The dictionary of the flashed build is kept, and the decoder takes it for blocks with its build id | `logs/events-d1ddd46b4dac2414.json` |

The patch specs are not changed: they are the flashed ones, and `builds/debug-log.json` still gives sha256
`e74f1aec…bda8`. With the new dictionary the generator writes the same code but the 8 bytes of the build id at
0x7EBF2D24 (checked, then put back). The JSON lines of the camera file differ from the first decode in 8
records (session, `recovered`, 4 times) and in the added `names`.

Limits of the decoder that remain: point 5 of section 4; and for CPU 1 after a restart that kept the RAM, the
border between old and new records is the place where the time goes back, so a timer wrap in that one write
(1 in 1,073 s) can move it.

## 7. Unknown

- Does the ring survive a restart after a crash?
- What the power-on factor and the wake byte are on the camera (probe A).
- The cost of the colour loop in a peaking frame (point 1).
- The two code-3 jobs of each capture, and the callbacks 93 and 162.
- State 0x0002, and which button gives 0x5600 (INFO is inferred).
- Whether Interval Time was 00:00:01, and how many photos are on the card (the owner knows both).

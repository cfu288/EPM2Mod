# Anti-Shock 0 s (electronic first curtain) and silent shutter on the E-PM2

Date: 2026-11-16/17. Desk work only. Nothing was built, nothing was flashed. The emulator was not
used: it has no sensor and no shutter (`docs/feasibility.md`), so it cannot answer these questions.

Labels: **V** verified (read in the firmware bytes or a file), **I** inferred, **U** unknown,
**R** reported by others. Addresses are block-0 runtime addresses of E-PM2 1.6, or of E-P5 1.8 where
the text says "E-P5".

## 0. Answer

| Question | Answer | Label |
|---|---|---|
| (a) Can the E-PM2 get an electronic first curtain? | Not by a port of the E-P5 code. Perhaps by a small change of the stock sequence. One fact about the sensor decides it, and one camera build measures that fact (build 2, section 5) | **U** |
| Is the E-P5 a usable donor? | No. Its sensor is driven with another register set, it uses a sensor mode that no E-PM2 program writes, and its shutter driver has two commands that the E-PM2 has not | **V** |
| Is the shutter able to do it? | Yes for the method of section 5: the shutter runs a stock exposure, only longer. No new shutter command and no new order | **V** by design |
| Is the body controller (H8) involved? | No. The main CPU drives the shutter. The H8 is the stabiliser controller | **V** / **I** (section 2.4) |
| (b) Fully electronic shutter? | Live Time already starts and ends exposures with the shutter open, but only in slices of 0.5 s and more. For short times the answer is unknown. A test with the stock firmware (two pictures of a wall) gives the first half of the answer | **U** |

The main new finding: **the bodies fall into two sensor families** (section 2.2). E-M5, E-PM2 and E-PL6
send byte-identical register programs to the sensor. E-P5, E-M10 and E-PL7 send another set. Every
body with Anti-Shock 0 s is in the second family. "Same 16 MP sensor as the E-P5" is a statement of
reviewers (**R**); the firmware does not support it.

## 1. How the E-PM2 exposes a still

All of this code is in segment 1 (code 0x7E4FE000–0x7E731584, tables in its rodata up to 0x7E8808BF).

### 1.1 The layers (**V**)

| Layer | Where | What it does |
|---|---|---|
| TAKE task | 0x7E59xxxx–0x7E5Axxxx | Decides the mode. Anti-shock delay getter 0x7E5A58B3 |
| Still sequence, `cam_still_func.c` | 0x7E656643–0x7E65DA2A | Phases Ready and Take as tables of jobs (1.2) |
| Live Bulb sequence, `cam_still_live_bulb.c` | 0x7E65DA2B–0x7E661D83 | Same design, own tables |
| Sensor set commands, `cam_set.c` | dispatcher 0x7E650607 | Codes 83 EXP_START, 84 EXP_STOP, 88 EXP_STBY, 89 EXP_CANCEL, 87 CONT_EXP_START, 98 LB_CAPTURE, 99 LB_CAPTURE_STOP, 101 LB_EXPOSE_START. Names from the event-object table 0x7E7ADA54 (37-byte records, ids 32–41 and 54–56) |
| Frame commands, `cam_frame.c` | dispatcher 0x7E636AAB | FC50 = EXP_START, FC51 = EXP_STOP, FC52 = EXP_STBY, FC81–85 = Live Bulb |
| Sync generator, `cam_sg.c` | 0x7E652AF3–0x7E6557CD | Commands 129 and 130, events 4 and 5 |
| Sensor driver, `cam_imgdev.c` | filter 0x7E63BE39, program sender 0x7E63EB3F | Sends register programs over the serial port. 21 programs (list: `scripts/sensor_programs.py`) |
| Shutter client, `cam_shutter.c` | filter 0x7E6558AD | Magnet commands (1.3) |
| Charge motor client ("mirror", MI) | filter 0x7E642459 | Motor commands (1.3) |
| MEC layer | submit 0x7E51787B, codes 0–18 | Magnets, motor, power. Driver tables at RAM 0x604F63A4 and 0x604F63FC |

The main CPU drives magnets and motor through the MEC layer and its timing unit (MMIO 0x9A300000,
feature map 13f). No other processor is in this path (**V**: every call ends in the MEC driver).

### 1.2 The sequence

A phase is a record {mask of job bits, table A, table B} at 0x7E7BD3B4–0x7E7BD47F (17 records). Table
A has one row per job bit: {bit, list of step functions, count}. A step function sends one request.
`scripts/still_steps.py` prints all of them. The first Ready record (0x7E7BD3B4) and the first Take
record (0x7E7BD3E4), reduced to the steps that matter:

| Phase | Job bit | Step | Request |
|---|---|---|---|
| Ready | 0x1 | 0x7E657B77 | magnets on (shutter code 147) |
| Ready | 0x2, 0x4 | 0x7E657940, 0x7E657952 | sensor set 17, then 18 (stop live view, sleep) |
| Ready | 0x10 | 0x7E657AF1 | motor OPENRDY (MI code 6): from "open" to "ready" = close and charge (**I** for the meaning) |
| Ready | 0x200 | 0x7E657EF5 | **the Anti-Shock delay**: timer of `delay` ms, or no wait when it is 0 |
| Ready | 0x40000 | 0x7E657985 | sensor EXP_START (set 83) |
| Take | 0x1 | 0x7E657B9B | magnet SET or START (shutter code 7 or 11) with TV and TIME: both curtains run, timed by the MEC unit |
| Take | 0x100, 0x200 | 0x7E6579CD | sensor EXP_STOP (set 84): read-out |
| a later record (0x7E7BD414) | 0x2 | 0x7E657B1D | motor OPENCHG (MI code 5): charge and open for live view |

- **V**: the records, the lists, the step functions and their requests.
- **V**: Ready comes before Take (the test command `cam still` at 0x7E62F6EB sends phase 0, then 1).
- **I**: inside a phase the jobs run in the order of their bits. Table B and the done callbacks hold
  the links and were not decoded. Build 1 (section 7) logs the real order.

So the sensor is started **in the dark, at the end of Ready**, before the first curtain runs. The
first curtain starts the exposure. The second curtain ends it. EXP_STOP reads the sensor in the dark.

What EXP_START does (**V** calls, **I** meaning): frame method 0x7E638A02 sends sync-generator
command 130 and waits for sync event 4 (callback 0x7E638A27). Then, only for 1/10 s and slower
(TV ≤ 853/256, test at 0x7E63E09E), the sensor gets the program {reg 00=04, A2=02, 01=00} ("clock
pause", 0x7E7B0290). EXP_STOP sends {01=04, 06=0A, 07=00} and runs the generator again.

### 1.3 Shutter commands (**V**)

| Client code | MEC code | MEC name (from the monitor 0x7E51256F) |
|---|---|---|
| shutter 147 or 6 | 10 | MAG ON |
| shutter 5 | 11 | MAG OFF |
| shutter 7 | 12 | MAG SET (TV, TIME) |
| shutter 11 | 13 | MAG START (TV, TIME) |
| shutter 12, 146 | 14 | MAG STOP (ends a bulb exposure) |
| shutter 149 | 15 | MG3_CHG |
| MI 6 / 5 | 2 / 3 | MOT OPENRDY / OPENCHG |
| MI 149 / 150 | 7 / 8 | MOT F_READY / F_OPCHG |
| power-on | 5 | MOT INTIAL |

The MEC driver posts events to the client while a MAG START runs. Their names in the monitor:
`SENSOR1`, `SENSOR2`, `BOUND`, `ISEN`, `STB_SYC` (flash sync), `2ND_STR` (second curtain start),
`SHIELD`, `ITVAL`, `STB_CNC`, `.END`.

### 1.4 What Anti-Shock does today (**V**)

- Drive modes with the ♦ mark set prm 0x99E1 (info 166). The menu time is prm 0x8C42 (info 63), in
  ms, from the list at 0x7E849820 (u16): 125, 250, 500, 1000, 2000, 4000, 8000, 15000, 30000.
- TAKE reads both in 0x7E5A58B3. It gives 0 for sequential drive and when the flag is off.
- The value goes into the Ready request (field +4 of the parameter block). The step 0x7E657EF5 waits
  that long **after the shutter has closed and charged and before the sensor start and the first
  curtain**. The test command `cam still` shows the same: "Setting AntiShock Ready" puts 3000 into +4.
- So the stock function removes the shock of the closing and charging. The first curtain still
  starts the exposure, and its own stop falls into the exposure.

## 2. What the E-P5 does for 0 s

### 2.1 The path (**V** unless marked)

| Step | E-P5 1.8 |
|---|---|
| Decision | 0x7E270C3E gives 1 when anti-shock is on, the delay is 0, the time is not bulb and **TV ≤ 2133/256 = 8.33 = 1/320 s or slower**. Result in the TAKE byte 0x60546EBE |
| Request | byte +16 of the still parameter block (no E-PM2 code sets this byte). `cam still` option bit 13: "Setting efs" (0x7E2FFC05) |
| Still sequence | new event objects 65 `STILL_EXPOSE_START_READY`, 71 `STILL_SET_EXPOSE_END`, 72 `STILL_SET_LONG_EXPOSE_END`, 73 `STILL_SHUTTER_1ST_RUN`. Reading (**I**): the first curtain runs first, then the sensor starts the exposure, then a timer releases the second curtain |
| Sensor set | 67 `EFS_SLEEP` (FC89, a set list, FC90), 68 `EFS_EXP_START` (FC92), 69 `EFS_EXP_STOP` (FC94), 70 `EFS_LONG_EXP_START` (FC93). Sequence functions 0x7E323135–0x7E32328E |
| Frame | FC92 method 0x7E309E7B: waits for sync event **5**, sends no command 130. FC50 (normal) sends 130 and waits for event 4 |
| Sensor | new driver commands 160–163. 162 and the EFS sleep send {00=06, A2=00}, then a 19-write program that ends with **reg 01=88**, A2=02 (0x7E4A3EBC). 163 (stop) sends {AA=40} |
| Shutter | two new magnet requests in the shutter client (handlers 0x7E327AC0, 0x7E327B14): MEC codes 22 and 24. The E-P5 MEC layer takes codes 0–33, the E-PM2 0–18 |

### 2.2 Two sensor families (**V**)

`scripts/sensor_families.py` on the main blocks of six update files:

| Body | Programs | Registers written | Values of reg 0x01 | Programs identical with the E-PM2 | Anti-Shock 0 s |
|---|---|---|---|---|---|
| E-M5 2.3 | 21 | 70 | 00, 04 | all | no (**R**) |
| E-PM2 1.6 | 21 | 70 | 00, 04 | — | no |
| E-PL6 1.4 | 21 | 70 | 00, 04 | all | no (no `EFS` string, **V**) |
| E-P5 1.8 | 25 | 92 | 80, 84, 88, 94 | 3 | yes |
| E-M10 1.4 | 27 | 103 | 80, 84, 88, 94 | 3 | yes |
| E-PL7 1.4 | 27 | 103 | 80, 84, 88, 94 | 3 | yes |

- In the second family reg 01 = 80 is "paused", 84 is "running" and **88 is the EFS state**. The E-M10
  recipe is short: {00=04, A2=02, 01=88, D5=7B, D6=02}, then {AA=40} at the stop.
- The E-PM2 writes only 00 and 04 to reg 01. Bit 7 and bit 3 are never set.
- The E-P5 writes 49 registers that the E-PM2 never writes, and the E-PM2 writes 27 that the E-P5
  never writes.
- Reading (**I**): the E-PM2 has an older sensor revision, or the same die run in an older mode. Whether
  it has the EFS state at all is **U**. The E-M5 never got Anti-Shock 0 s (**R**, from memory, not
  checked today), which fits.
- {AA=40} exists in both families. In the E-PM2 it is the program of Live Bulb's `COM_LB_RESET`.

### 2.3 Function pairing (`scripts/moddiff.py`, E-P5 against E-PM2, functions in link order)

| Module | Identical | Changed | Only E-P5 | Only E-PM2 |
|---|---|---|---|---|
| cam_sg (sync generator) | 134 | 0 | 2 | 1 |
| cam_mec_ctrl | 39 | 1 | 2 | 1 |
| MEC layer (0x7E517791–) | 80 | 6 | 15 | 0 |
| MEC driver below it | 281 | 68 | 36 | 9 |
| cam_shutter | 17 | 18 | 7 | 1 |
| charge motor client (MI) | 67 | 9 | 9 | 2 |
| cam_set | 78 | 19 | 30 | 7 |
| cam_imgdev | 124 | 75 | 41 | 8 |
| cam_expcal + cam_frame | 205 | 126 | 59 | 10 |
| cam_still_func | 276 | 185 | 99 | 46 |
| live bulb | 101 | 144 | 23 | 22 |

"Changed" includes functions that differ only in a constant. The picture is still clear: the sync
generator is the same code; everything above it differs in hundreds of places. The E-P5 still module
is 4.1 KB longer. A port would move about 300 functions and a sensor recipe for another sensor
family. That is not a port. Section 5 does not use E-P5 code.

### 2.4 The body controller

- The E-PM2 and E-PL6 update files end with a 65,600-byte `OM` tail: the H8 firmware of the
  stabiliser controller (`docs/firmware-map.md`). The E-P5 1.8, E-M10 1.4 and E-M5 2.3 files have
  **no tail** (`tools/oetool.py info`, **V**). An update file serves every older version, so E-P5 1.4
  added the function without new controller firmware (**I**).
- The release note of E-P5 1.4 says only: "A 0 second setting has been added to Anti-Shock mode"
  (**V**, file `1080_i08.html` of the ep5-fw-reverse notes).
- In both bodies the shutter is commanded by the main CPU (1.1). The controller does not need to know.

## 3. Live Time and Live Bulb: exposure control with the shutter open

| Fact | Label |
|---|---|
| Live Bulb Ready is the still Ready: magnets on, sensor sleep, OPENRDY, EXP_START (step tables 0x7E7BE5F0–0x7E7BE690) | **V** |
| The exposure starts with shutter code 11 (MAG START, step 0x7E65E352) and ends with code 12 (MAG STOP, step 0x7E65E3F7) | **V** |
| While the shutter is open the sequence sends LB_CAPTURE (98), LB_CAPTURE_STOP (99) and **LB_EXPOSE_START (101, step 0x7E65E25C)**, with timer 24 for the interval (setting 436 × 500 ms, feature map 10a) | **V** |
| LB_EXPOSE_START = frame method 0x7E638E78: sensor command 159 `COM_LB_RESET` (program {AA=40}), generator command 130, then command 157 `COM_LB_PAUSE` (program {00=04, A2=02, 01=04, 02=00, 03=00, 06=0A, 07=00}) | **V** |
| LB_CAPTURE_STOP = method 0x7E638D46: command 155 `COM_LB_WAKEUP`, then the generator: a read-out | **V** calls, **I** meaning |
| So each slice of a Live Time exposure is started by a sensor reset and ended by a read-out, both with light on the sensor. The final picture is the sum of the slices | **I** (strong: the manual limits the number of updates by ISO, which fits added read noise) |
| Is `COM_LB_RESET` a reset of all lines at once, or line by line? How long does it take? | **U** |
| How long is the read-out of a slice? 24.3 ms is the figure of sensor mode FULL (hardware notes); the still read-out may be slower | **U** |

Answer to "can the same calls start an exposure with the first curtain already open": **yes at
command level**. The stock firmware does it in every Live Time slice after the first. What the frame
looks like for a short time is the open point. The test in section 6.1 measures the two unknowns
without a build.

## 4. Free space and load order

- `tools/freespace.py area 0x7EBF1090`: the segment-2 area 0x7EBF1090–0x7EBF3BAD is USABLE-CODE.
  With every spec that is in `patches/` today **1,104 bytes are free**, in pieces (largest
  0x7EBF1F4F–0x7EBF2000, 177 bytes; then 149, 148, 120, 116, 112 and 108 bytes). New code must be cut
  into pieces of that size. The pinned build uses fewer specs: count again for the real spec list.
- The still code and its tables are in segment 1. A changed table pointer or a hook there that goes to
  segment-2 code breaks rule 13 of `AGENTS.md` unless there is proof that the site runs only after
  Usr1. Argument (**I**): a still phase runs only on a request of TAKE, and TAKE gets it from the
  application in segments 2 and 3. The power-on shutter move is `COM_READY_ON` in cam_mec_ctrl, not a
  still phase. Proof to collect: `tools/emu/hookcheck.py`, `boot-test` and `update-path-test` on the
  build, and build 1 on the camera (no still record before the boot record). Then one line in
  `tools/emu/hookcheck-allow.tsv`.

## 5. Plan for (a): start the sensor late, leave the shutter alone

Idea: for a picture of time T the shutter runs a **stock exposure of D + T** (D = 30 ms to start
with). The sensor start (EXP_START) moves from the end of Ready to D after the first curtain has
opened. The sensor then starts the exposure and the second curtain ends it. The shutter sees a normal
1/25 s exposure in place of a 1/100 s one.

| # | Step | What | Effort |
|---|---|---|---|
| 0 | Stock tests | Section 6.1 (wall, Live Time) and 6.3 (sharpness with stock Anti-Shock 1/8 s). No build | owner: 15 min |
| 1 | **Build 1: log only** | Probes of section 7 on top of the debug-log build. No change of behaviour. Gives the real job order, the time from EXP_START to sync event 4 and its spread, TV and TIME of the magnet request, the times of `STB_SYC`, `2ND_STR`, `.END` | 3–4 h, 1 flash |
| 2 | **Build 2: late start, the sensor probe** | (i) New step in place of 0x7E657985 in the Ready lists (pointers at 0x7E7BBB88, 0x7E7BBBE8, 0x7E7BBC30, 0x7E7BBC70): in EFCS mode it sends nothing and posts job bit 0x40000 through the poster 0x7E65D41A; else it jumps to the stock step. (ii) Hook in the shutter sender at 0x7E65D30D (`movhu (4,a0),d0; movhu d0,(8,a1)`): in EFCS mode TV comes from a 2-byte table for D + T. (iii) New step in front of 0x7E657B9B in the Take lists: starts cam timer D (0x7E65D3E6 pattern), whose callback sends set 83 with a private copy of the packet 0x6056EBC4 and a done callback that posts nothing. (iv) Gate: anti-shock flag on, delay value 125 ms, TV between 5.0 and 8.33 (1/30 to 1/320 s), no flash. About 300 bytes of code, 4 table words, 1 hook | 8–12 h, 1–2 flashes |
| 3 | Read build 2 | Grey wall at 1/100 s, RAW, stock and EFCS. Table in section 5.1 | owner: 10 min; 1 h |
| 4 | Timing | If the brightness varies from frame to frame: tie the sensor start to a MEC event (`STB_SYC` of the first curtain) in place of a software timer; choose D from the log | 4–6 h, 1 flash |
| 5 | Gradient | Measure the ramp per speed from wall frames. Correct it in the RAW converter, or look for a per-line gain in the shading stage (`rap_shading`, not traced) | 2 h to measure; correction **U** |
| 6 | Menu | Make the 30 s entry "0 s": the u16 at 0x7E849830 (30000 → 0) and the label. Gate on delay 0 as the E-P5 does. Emulator screenshots, guide | 3 h, 1 flash |

**The first build should be build 1.** It changes nothing and it gives the numbers that build 2 needs.

### 5.1 What build 2 tells

| Wall frame at 1/100 s in EFCS mode | Meaning | Next |
|---|---|---|
| As bright as stock, even, or with a smooth ramp of 0.2–0.5 EV along the short side | EXP_START resets all lines at one moment. Method works | steps 4–6 |
| About two stops too bright (the whole D + T) | EXP_START does not clear the charge. Try the Live Bulb reset in its place (set 101 or sensor command 159) | 1 more flash |
| Strong ramp or bands on the scale of 20 ms and more | The reset runs line by line at read-out speed. No use for short times on this sensor without the EFS state | try reg 01=08 (below), else stop |
| Black or broken frame, error in the log | The sensor state does not allow a start in light. Same as above | — |

Second recipe if the stock reset fails: write reg 01=08 in place of 01=00 (the E-PM2 form of the EFS
state of the other family). Nothing says that this sensor knows the bit (**U**).

### 5.2 Expected quality

- **Brightness ramp.** With a reset of all lines at once, line y is exposed for T + (time the second
  curtain needs to reach y). The travel over the frame is below 4 ms (sync speed 1/250 s; **I**: 2.5
  to 4 ms). Ramp from edge to edge: 1/60 s 0.2–0.3 EV, 1/100 s 0.3–0.5 EV, 1/200 s 0.6–0.9 EV. It is
  the same in every frame, so it can be corrected. A real EFCS sensor resets the lines in step with
  the curtain; that is what the EFS state of the other family is for (**I**).
- **Accuracy.** One edge of the exposure is timed by software in build 2. The spread is **U** until
  build 1 gives it. 0.1 ms is 1 % at 1/100 s.
- **Range.** Use it from 1/30 to 1/320 s as the E-P5 does. Outside it the stock sequence runs.
- **Flash.** The MEC fires the sync contact at the first curtain (`STB_SYC`), D before the sensor
  starts. A flash would be lost. EFCS mode must be off when a flash is active.
- **Shutter lag.** D more than stock anti-shock off.

## 6. (b) Fully electronic exposure

### 6.1 Smallest probe: stock firmware, two pictures (owner, 10 minutes)

Purpose: learn whether the Live Time reset is "all lines at once" and how long the read-out is.

1. Mode M, ISO 200, RAW. Evenly lit wall, out of focus, daylight (no lamp flicker). Dim the scene or
   stop down so that 4 s is a correct exposure.
2. MENU → Custom Menu → E → Live TIME → 0.5 sec. (Manual p. 74. Check the screen names in the
   emulator before this goes to the owner.)
3. Shutter speed LIVE TIME (past 60", manual p. 27). Press, count 4 s, press. Picture A.
4. Live TIME → Off. Same exposure. Picture B.
5. Send both ORF files.

Reading: divide A by B line by line, ignore the overall factor.

| Ratio A/B over the frame height | Meaning |
|---|---|
| Flat | No light is lost between slices, or the same amount in every line (reset line by line, in step with the read-out) |
| Linear ramp | Reset of all lines at once, read-out line by line. Ramp size × 0.5 s = read-out time |

### 6.2 Build probe (after build 1)

A debug build in which one Live TIME value (for example 60 sec) means "one slice, electronic end":
after MAG START the sequence waits D, sends LB_EXPOSE_START (step 0x7E65E25C), waits T, sends
LB_CAPTURE_STOP (step 0x7E65E27C), and only then MAG STOP (step 0x7E65E3F7). Log records at each
step and at the error store 0x7E661B1B. Only stock steps, in the stock bulb order for the shutter.
About 200 bytes. T from 1 s down to the shortest time the two requests allow (**U**, from the log).

### 6.3 Expected defects and what comes after

- Read-out line by line: skew of moving subjects over the read-out time (24 ms or more) and bands
  under mains-powered light.
- If the reset is "all at once" and the read-out is line by line, short exposures have a ramp as large
  as the read-out time. Then a silent shutter is of use only for long times, and the family of section
  3 of `mods-and-web.md` (1/16000 s, Pro Capture, Live ND) is closed for this sensor.
- If a line-by-line reset exists (live view uses one in the decimated modes; sensor mode 6 FULL has
  the same fields, **I**), the work after the probe is: a still phase without OPENRDY and magnets, a
  FULL-mode frame routed into the RAW path, exposure by the line counter of `cam_expcal` (0x7E6360FB).
  High effort; no donor body.

## 7. Verification

### 7.1 Log probes for build 1 (describe only; `logs/events.json` and the generator are not touched here)

A probe costs about 45 bytes of routine and 5 or 6 bytes at the site (log notes: 43 + 6). Ten probes:
about 500 bytes. The record has a 1 µs time stamp.

| Event | Site | Arguments |
|---|---|---|
| `sh_req` | still shutter sender 0x7E65D314 (the call of 0x7E6558AD) | code (u16 +0), TV (+8); TIME (+4) |
| `mi_req` | still motor sender 0x7E65D24D | MI code |
| `set_req` | still sensor sender 0x7E65D224 | set code (83, 84, 88 ...) |
| `stl_post` | still poster 0x7E65D41A | job bit, result |
| `exp_started` | frame callback 0x7E638A27 (sync event 4 after EXP_START) | — |
| `sh_event` | shutter event callback 0x7E655A84 | MEC post code (`STB_SYC`, `2ND_STR`, `.END`) |
| `lb_sh_req`, `lb_mi_req`, `lb_set_req` | Live Bulb senders 0x7E6616A7, 0x7E661630, 0x7E661607 | as above |
| `lb_post` | Live Bulb poster 0x7E6617F4 | job bit, result |

`fw_error` of the log core already records errors. `sh_event` may run in interrupt context: `log_put`
does not wait, so this is allowed (logging notes); check it for this site.

Owner session for build 1: 5 frames at 1/100 s, 5 with Anti-Shock 1/8 s, 1 frame at 1 s, one Live
Time of 3 s, then MENU (flush).

### 7.2 Sharpness test (owner, 5 minutes per build)

1. Camera on a table, no hand on it, 2 s self-timer. Longest lens, wide open. Newspaper page or a
   banknote at 1.5 to 2 m, focused once with magnified MF. Stabiliser off.
2. Mode S, 1/100 s, ISO as needed, RAW + JPEG. Then the same at 1/60 and 1/160 s.
3. Five frames each: (A) Anti-Shock off, (B) Anti-Shock 1/4 s (stock delay), (C) the EFCS value.
   Anti-Shock: MENU → Custom Menu → E → Anti-Shock (manual p. 74), and a drive mode with the ♦ mark.
   Check the screen names in the emulator before this goes to the owner.
4. Compare at 100 %. Shutter shock shows as doubled horizontal edges, 1 to 3 pixels, in most frames of
   A. C should look like the best frame of B or better, in all five.

Run A and B on the pinned build today. If B is already as sharp as a 1/1000 s reference frame, the
first curtain adds little on this body and (a) has less value than assumed.

## 8. Risks

### 8.1 Evidence

| Risk | Evidence | Size |
|---|---|---|
| A shutter command in a wrong order | Section 5 sends **no** shutter or motor command that stock does not send, and in the stock order. Only TV changes, inside the range that the shutter uses every day | none by design |
| How the firmware treats a shutter fault | Every motor request has time-outs (cam timers 13–16, feature map 14b). Result codes 0x8807, 0x8809, 0x880A, 0x8903, 0x8904 set the MEC error mode (0x7E518B86), and the layer then uses a second set of handlers (table 0x604F6418). Power-on runs MOT INTIAL (`COM_READY_ON`) | **V** code; effect on the mechanism **I** |
| A step that never posts its job bit | The phase waits. The cam watchdog (0x7E6629A8) reports a time-out. Earlier freezes on this camera ended with a battery pull and a card update | recoverable (**I**) |
| Table pointer from segment 1 to segment 2 | Section 4. A build that fails `boot-test` is not offered | the one risk to handle with care |
| Flash lost | `STB_SYC` belongs to the first curtain | gate it off |
| Sensor register 01=08 (second recipe only) | The init program rewrites 40 registers at every wake (0x7E7AF414), so a wrong value does not stay | low (**I**) |

### 8.2 Worry without evidence

- "The sensor may be harmed by light while it is in sleep": it is in light all the time in live view.
- "The shutter may be harmed by a long open time": Live Time holds it open for minutes.
- "The body controller must agree": it is not in the path (2.4).

## 9. Unknown, with the probe

| Unknown | Probe |
|---|---|
| Does EXP_START (or `COM_LB_RESET`) clear all lines at once? | 6.1 (no build), then build 2 |
| Read-out time of a still frame | 6.1 |
| Time and spread from the EXP_START request to the real start | build 1 |
| Job order inside a phase | build 1 |
| Meaning of TIME in the magnet request; TV values that the MEC accepts | build 1, then the D + T table |
| Does the E-PM2 sensor have the EFS state (reg 01 bit 3)? | second recipe of 5.1 |
| Curtain travel time (size of the ramp) | build 2 wall frames |
| Meaning of E-P5 MEC codes 22 and 24, of sync event 5, of registers 0xAA, 0x32–0x35, 0xD5/0xD6 | not needed for section 5 |
| Menu screen names for the test instructions | emulator screenshots (not made in this task) |

## 10. Scripts

| Script | Use |
|---|---|
| `scripts/moddiff.py` | Align the functions of one module in two bodies, in link order (2.3) |
| `scripts/sensor_programs.py` | List the sensor register programs of a block; compare two bodies |
| `scripts/sensor_families.py` | Table of 2.2 from several unpacked main blocks |
| `scripts/still_steps.py` | Print the job tables of the still sequence (1.2) |

Inputs: `build/map/` for the E-PM2; an E-P5 function database made with
`tools/fwmap.py --fw EP5_BLOCK0 --base 0x7E101020 --out DIR build`; other bodies unpacked with
`tools/oetool.py unpack FILE /tmp/scratch/NAME`.

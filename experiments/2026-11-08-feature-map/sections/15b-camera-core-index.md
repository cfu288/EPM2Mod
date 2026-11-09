# 15b. Camera core and its drivers: function-level index (E-PM2 v1.6, ~0x7E520000–~~0x7E731588~~ 0x7E731584 (L1 2026-11-09))

Round D3 deep dive for coverage round C3 (review 1: F003–F005, F009–F017, F020). It gives roles to function families and table slots, so that a reader can look up a random function in the camera core and find what it does.

- **Labels:** (V) = read in the code or bytes; (I) = inferred from names, order, layout or usage.
- **Index file:** `15b-camera-core-index.tsv` (`addr_or_id`, `kind`, `role`, `evidence`, `V/I`; 1,921 rows). Kinds: `range`/`family`/`function` (boundaries, families); `jumptable`/`hashtable`/`fntable` (every dispatch table of ≥ 8 entries, §6); `slot` (`0xTABLE[i]` = linear slot i, `0xTABLE{key k}` = hash key k); `callback`/`cell` (still/live-bulb step callbacks and state-table cells); plus the mdet/res rows (§4) and the named-module rows (§5).
- **Scratch:** `$S/d3/cam/`: `jt.py` (dispatcher scanner) → `jt.out`; `ptab.py` (pointer-table finder) → `ptab.out`; `cbx.py` (callback extractor) → `stcb.tsv`/`lbcb.tsv`; `fcmds.py` (cam_set slot walker); `gen.py` builds the parent rows; `mdet.md/.tsv` and `cmds.md/.tsv` are the two sub-reports merged here.

## 1. Area and boundaries

**Camera core file map** (V code edges; file names I where marked: they come from alphabetical link order (14b §0) and the E-PL7 `cam dbglog` file list, which also lists cam_imgdev_driver/sensor/serial.c, cam_serial.c, cam_sg.c, cam_siodrv.c, cam_strobe.c and cam_watchdog_timer.c). The error-code module byte is the second byte of the 32-bit `0x0A_MM_xxxx` damage codes.

| Range | File / component | Module byte, anchors |
|---|---|---|
| 0x7E627E9F–… | cam.c … cam_mec_ctrl.c, cam_mem.c: unchanged (03 §3, 14b §1) | |
| 0x7E63B885–0x7E63BAA5 | unplaced helpers after cam_frame_sync.c: 0x7E63B912/0x7E63B955 write a debug image file to the card (`xxxOLYMP`, `File Size`; ← the `cam` shell test sequences 0x7E62F6EB…) | none |
| 0x7E63BAA6–~~0x7E63D0DD~~ 0x7E63D1C0 (it ends with the `cam_imgdev.c` dumper 0x7E63D0DD (L1 2026-11-09)) | cam_imgdev.c command layer: names 0x7E63BAA6, init 0x7E63BC40 (← cam_set init), filter 0x7E63BE39 | 0x17; 16-bit 0x8480/81/85/86 |
| **~~0x7E63D0DE~~ 0x7E63D1C1–0x7E63EC58** (L1 2026-11-09) | imgdev driver: per-command sequencers, `IMGDEV_DRIVER` dump 0x7E63E4B2, queue engine 0x7E63E795–0x7E63E8ED, enqueue 0x7E63EB3F (cam_imgdev_driver.c, I) | 0x0A1720xx to 0x7E63E515; last 0x84xx at 0x7E63EB3F |
| **0x7E63EC59–0x7E6401FF** | imgdev sequence programs, one per command step, using descriptors 0x7E7B03A8–0x7E7B04CC (cam_imgdev_sensor/serial.c, I) | no codes; callers only imgdev |
| **0x7E640200–0x7E640857** | cam_lens.c (`CAMLNS`) | 0x25; 16-bit 0x9211/0x9213/0x9280 |
| 0x7E642325–0x7E643932 | cam_mirror.c (MI_*) | 0x1E |
| 0x7E643933–0x7E64F084 | cam_param/pfp/port/prepro/rap.c (SPRDRV 0x7E64B364): not split here | 0x1B |
| 0x7E64F085–0x7E64F743 | cam_sem.c (dump 0x7E64F2A2 is in the middle; worker 0x7E64F42A …) | 0x27 |
| **0x7E64F744–0x7E650467** | **cam_serial.c** (I): sensor serial-command client of imgdev | none |
| **0x7E65046F–0x7E652AE2** | **cam_set.c**: init 0x7E65046F (I by position), request dispatcher 0x7E650607, set-list engine, dump `cam_set.c` 0x7E6521C9 | **0x11** (0x7E650607–0x7E6529CA) |
| **0x7E652AF3–0x7E6557CD** | **cam_sg.c** (I): sync/timing generator, IRQs 4–6; command filter 0x7E652CEB | **0x00** |
| 0x7E6557CE–**0x7E6561D9** | cam_shutter.c (SH_RES/SH_MEM), with its MEC-client callbacks 0x7E655FC4–0x7E656177 | 0x1A |
| **0x7E6561DA–0x7E65663A** | **cam_siodrv.c** (I): driver of MMIO 0x99900000, IRQ 7 | none |
| **0x7E656643–0x7E656B1C** | still glue (cam_still.c?, I): init, COM_ON/OFF/SET routing to still, live bulb, mec_ctrl | none |
| 0x7E656B1D–0x7E65DA2A | cam_still_func.c | 0x13 |
| 0x7E65DA2B–**0x7E661D83** | cam_still_live_bulb.c (its error store 0x7E661B1B and damage reporter 0x7E661CFF are after the 0x7E6619C5 dump) | 0x13 |
| **0x7E661D84–0x7E66226D** | **cam_strobe.c** (I) | none |
| 0x7E66226E–0x7E6629A7 | cam_timer.c (TM_SEM; dump 0x7E66296B) | 0x24 |
| **0x7E6629A8–0x7E662C26** | **cam_watchdog_timer.c** (I) | 0x24; 16-bit 0x9302 |
| **0x7E662C27–0x7E666C5A** | SDET (iAuto) | 0x32xxxxxx (recorder codes) |
| **0x7E666C5B–0x7E674DF4** | **mdet** library (§4) | 0x31xxxxxx |
| **0x7E674DF5–0x7E675D98** | **res** flash-resource store (`res_read` 0x7E674F44) | 0x1F0000xx |
| 0x7E675D99–0x7E68F07B | api_* (init 0x7E675D99 ← Usr0; names from 0x7E675E64) | |
| **0x7E68F07C–0x7E6A935C** | EXP_MOVIE `exp` module (§5) | |
| **0x7E6A935D →** | HDMI driver (`[HDMI-DRV]`), then display/touch | |

**imgdev vs cam_lens.c (V):** the 0x84xx family ends at 0x7E63EB3F; the 0x92xx family and the 0x0A25xxxx codes start at 0x7E64024C/0x7E6402A9; the imgdev callers of 0x7E63EC59–0x7E64015E are the sequencers 0x7E63D294–0x7E63E3B0. So 14b's "cam_lens.c ~0x7E63E5xx" is wrong; cam_lens.c is 0x7E640200–0x7E640857.

**Why cam_set.c owns the dispatcher (V):** the dispatcher 0x7E650607 uses module byte 0x11, the same byte as the `cam_set.c` dump 0x7E6521C9 and the list code up to 0x7E6529CA; and its hash table 0x7E7BB094 starts right after the last cam_set.c string (`* Max = %d\n`, ends 0x7E7BB093), as the rodata rule (14b §0.3) predicts. The guess `cam_seq.c` (C3 F013) is not needed: E-PL7 has no such file, and cam_serial.c (the only name between cam_sem.c and cam_set.c) is the serial client 0x7E64F744–0x7E650467.

## 2. Components

### 2.1 One command-code space for the whole camera core (V)

The modules share CamCommand's code numbers: 7 = COM_SET and 134 (0x86) = COM_CANCEL_REQUEST in cam.c and imgdev; 9/10 and 145–152 are MI codes; cam_set uses 5–8, 17–19, 83–101. Every module command filter has the same shape (u16 code at packet+0, a bounds check, then a hash or jump table), so a random function that starts `movhu (a0),dN; cmp LO,dN` and ends `mov (4,a1),a1; jmp (a1)` is a module's command filter (§3).

| Module | Filter | Table (codes) |
|---|---|---|
| cam.c | `CamCommand` 0x7E628303 (the name is assigned, I: no firmware string has it) | 0x7E7AC020 (3–147; 03 §1) (A8 2026-11-09) |
| cam_frame.c | 0x7E636AAB | jump 0x7E7AE744 (frame commands 1–85, 33 handled) |
| cam_imgdev.c | 0x7E63BE39 | hash 0x7E7AF048: 1 SLEEP, 7 SET, 9 ACTIVE, 11 START, 12 STOP, 20 WAKEUP, 134 CANCEL_REQUEST, 144 RESET, 145–148 MOVIE_START/STOP/PAUSE/RESTART, 149–154 CLOCK_PAUSE/RESTART/CHANGE_PREPROCESS/HIGH/LOW/CHANGE_RESTART_WAIT, 155–159 LB_WAKEUP/SLEEP/PAUSE/STANDBY/RESET (names from 0x7E63BAA6) |
| cam_mirror.c | 0x7E642459 | hash 0x7E7B18B8: 1, 2, 5, 6, 9, 10, 145–152 (roles 14b §5) |
| cam_set.c | 0x7E650607 | hash 0x7E7BB094 (§2.2) |
| cam_sg.c | 0x7E652CEB | hash 0x7E7BB5D4: 5, 6, 7, 9, 18, 19, 129–133 |
| cam_shutter.c | 0x7E6558AD | hash 0x7E7BBAAC (key = code − 4): 5, 6, 7, 11, 12, 145–149. Codes 5, 6/147 (shared 0x7E655939), 12, 146 and 149 → MEC submit 0x7E51787B of an SH request object; 7 (0x7E655971) and 11 (0x7E6559CB) arm the cam timer 0x7E6623CB twice and then submit; 145 (0x7E655A2E) is `clr d0; retf`, a no-op; 148 (0x7E655A5E) only sets byte +1 of the SH state *(0x6056EB44) to 1, which code 11 clears (A10 2026-11-09) |
| cam_still_func.c / live bulb | 0x7E656EEB / 0x7E65DC34 | only 7 and 80 / only 7 (03 §4) |

### 2.2 cam_set.c: request dispatcher, set lists and frame commands (V)

**API.** A caller fills a 56-byte request (u16 code at +0; bit 15 = keep the packet), then calls open 0x7E6505C5 → dispatch 0x7E650607 → close 0x7E6505F1. Open and close allocate and release a **set list** (20 slots × 12 B at 0x6056DF20, error 0x0A11201E) only for codes 7 and 90. cam.c sends: COM_OFF job 0x7E6287E2 → 5, COM_ON path 0x7E62862B → 6, COM_ABORT 0x7E628ACD → 17, COM_EXECUTE_REQUEST 0x7E628E12 → 7 then 86, COM_ACCEPT_REQUEST 0x7E628E92 → 90, COM_GET 0x7E6288E5 → 8, COM_MOVIE_ENABLE 0x7E628F9E → 95; frame-sync 0x7E63A4BB → 85. Still (0x7E65D1FD) and live bulb (0x7E6615BA) send pre-built packets from RAM tables 0x6056EBB4… / 0x6056ED4C… through 1-line wrappers (0x7E657940–0x7E657AE8, 0x7E65E202–0x7E65E2BA); the live bulb patches code 98.

**Slot index of 0x7E7BB094** (handler; what it does):

| code | handler | action |
|---|---|---|
| 5 / 6 | 0x7E650886 / 0x7E650818 (F013) | start cam_ev sequence 33 (0x7E650DB3: list 16, FC41, FC3) / 32 (0x7E650CFE: FC40, list 10, FC6): power down / up |
| 7 | 0x7E650721 | COM_SET: run set lists of types 57, 58, 59, 62, 63 (builder 0x7E65156C), and of types 61, 64 or a u16 from the packet through 0x7E651520, which runs the list in the same executor 0x7E6513CF without the builder (A10 2026-11-09) |
| 8 | 0x7E650CCD | COM_GET: copy the current setting block (18 + 9 words) to the caller. The getter 0x7E649822 returns X = *(*0x6055E2BC); the sources are **(X) (18 words) and *(*X + 4) (9 words), and the destinations are the two pointers at *(pkt+8) +0 and +4 (A10 2026-11-09) |
| 17, 18, 19 | 0x7E65084F, 0x7E6508BD, 0x7E6508F4 | sequences 41 (0x7E650E6B), 34 (FC1, list 34), 35 (list 35, FC57) |
| 83, 84, 87 | 0x7E650999, 0x7E6509D0, 0x7E650A07 | sequences 38 (FC50), 39 (FC51), 40 (FC54) |
| 85 | 0x7E650A3E | re-enter CamCommand with code 135 (COM_EXECUTE_REQUEST) |
| 86 | 0x7E650A84 | FC60 |
| 88, 89 | 0x7E65092B, 0x7E650962 | sequences 36 (list 36, FC52), 37 (list 37, FC20) |
| 90 | 0x7E650AA7 | list 65, then FC77 |
| 91 | 0x7E650AE5 | FC56 |
| 92 | 0x7E650B1A | CamCommand 136 (COM_ACCEPT_REQUEST) on a heap packet; its done 0x7E650B51 arms cam timer 19 → FC70, FC71 |
| 93–97 | 0x7E650BCB … 0x7E650BFF (13 B each) | FC72, 73, 74, 75, 76 (95 = COM_MOVIE_ENABLE) |
| 98 | 0x7E650C0C | sequence 54 (0x7E651239: list 54, FC85, FC81) |
| 99, 100, 101 | 0x7E650C4E, 0x7E650C85, 0x7E650C96 | sequence 55 (FC82), FC83, sequence 56 (FC84) |

The code names are not in the firmware (cam.c's name table stops at its own codes); the power/abort/get readings come from the cam.c senders above (V).

**Machinery (V).**
- **Sequence functions** 0x7E650CFE–0x7E65137A (13, 85–236 B): event-driven state machines on one cam_ev object each (ids 32–41, 54–56). Each step re-arms its object with itself as callback (0x7E6356C3/0x7E6359B1) and issues the next frame command or set list.
- **Issue frame command** 0x7E651483(d0 FC, a0 owner, a1 done): a 20-byte request {u16 FC, owner ids, done at +12} to the frame dispatcher 0x7E636AAB. FC 7 = "apply set list": it first runs the distributor 0x7E651B7A.
- **Run set list** 0x7E65156C(d0 list type, a0 owner object, a1 done; d1 is passed through) (A8 2026-11-09): the builder 0x7E65210C keeps a0 at list +16 and copies its +8/+12/+24, a1 goes to +20 and d1 to +28; list of FrameType d0 (0x7E65210C), kept in the 20-slot table 0x6055EEF8, executed by 0x7E6513CF, finished by 0x7E651B0E or by FC 7.
- **Distributor 0x7E651B7A** (1426 B) sends the list's FunctionList to the module setters (aperture 0x7E62B513, contrast 0x7E62CBF2, imgdev 0x7E63BE31, lens 0x7E64024C, sg 0x7E652BEA, strobe 0x7E661DA6, 0x7E62BC40, 0x7E64A34A, 0x7E64D5D3). The dump 0x7E6521C9 names the 44 FunctionList flags: `sync_setting_sg/rap/prepro/bright/contrast/aperture/strobe/lens`, `sg_img_setting_*`, `tg_expose_imgdev/strobe`, `sg_composition/vl_point/cycle/intr/tft_sync/ktc_setting`, `lvds_setting`, `rap_vkiz/pdc/psc/line_gain/ob/shading/linear_setting`, `capture/awb/ae/contrast/tg_setting`, `tg_capture`, `tg_gain`, `aperture/strobe/lens_setting` (V strings; which flag drives which setter is I).
- **Callback stubs:** per-module completions 0x7E651839–0x7E6519A2 (10 × ~40 B: decrement the list count +42, call one module's finish, then 0x7E651B0E); list-done 0x7E6515C0–0x7E651644 (7 × 22 B: release the list, then OR flag mask 0x2 or 0x4 into the sequence object through 0x7E63589A); frame-done 0x7E65165A–0x7E65181E (18 functions, not 21: 16 pointer-only 27-B stubs free the request (0x7E641D60) and OR mask 0x2/0x4/0x8 into the flag word of objects 32–40, 54–56 through 0x7E63589A (`or d1,d0` at 0x7E635C75), so 2/4/8 are masks, not bit numbers; 0x7E65179E (11 B) only releases a list (0x7E652171) and is used by COM_SET 0x7E650721; 0x7E6517FA (36 B) frees the request and calls the owner's done at +20, used by the code-100 handler 0x7E650C85). (A9 2026-11-09)
- Set-list FrameTypes (10, 16, 34–37, 54, 57–59, 61–65, plus caller-supplied values through 0x7E651520) are a separate number space from frame commands. As frame-command codes, 13 of the 15 fixed values are default slots of 0x7E7AE744; 54 → 0x7E636B40 and 57 → 0x7E636B63 are handled entries (V). (A8 2026-11-09) (A10 2026-11-09)

**Frame commands** handled by 0x7E636AAB (V): 1, 3–7, 17, 20, 40, 41, 50–57, 60, 70–77, 80–85. All start handlers follow 14b's pattern (120-byte request, done at +112). FC 7 (0x7E636BC5) is set-list apply. cam_set issues 1, 3, 6, 20, 40, 41, 50–52, 54, 56, 57, 60, 70–77, 81–85 (TSV rows give the issuing code). A frame object's work mask is run by 0x7E637C46 (pointer-only): for each set bit i of the mask it calls entry i of the 27-entry table **0x7E7AE898** (V). Entry 0 0x7E637CA4 sends the packet to sg 0x7E652CEB, then 0x7E64D73E and 0x7E64A423; the other entries are 17-B senders 0x7E637D2E… (what each bit means is I).

### 2.3 Serial path, sg, strobe, timers (V code, names I)

- **cam_serial.c 0x7E64F744–0x7E650467:** entries 0x7E64F744 (← imgdev 0x7E63E795), 0x7E64F790/0x7E64F7DC/0x7E64F81D (← the imgdev queue engine); transfer state machines 0x7E64F856–0x7E650315 under the interrupt lock (0x7E44B36F/0x7E44B390). It calls only cam_siodrv.
- **cam_siodrv.c 0x7E6561DA–0x7E65663A:** driver of a block at **MMIO 0x99900000** with **IRQ 7, level 2** (`irq_attach` 0x7E463C8E). Init 0x7E6561DA clears the three callback slots 0x6056EB4C–54. 0x7E656203 registers a callback. 0x7E656210 sets enable bits 0x08000000/0x10000000/0x20000000 (channel 0/1/2) in 0x99900014, and 0x7E65624E clears them. The ISR 0x7E65628B reads status 0x99900004, masks it with the enable word, acknowledges, and calls the callback of each set bit. The other helpers are used only by cam_serial. "Serial" is from the E-PL7 name (I).
- **cam_sg.c 0x7E652AF3–0x7E6557CD** (module byte 0x00): init 0x7E652AF3; 0x7E653AB1 attaches **IRQs 4, 5, 6** (level 2) → ISRs 0x7E655548/0x7E6555C6/0x7E655644; filter 0x7E652CEB (called by the frame fan-outs), set-list setters 0x7E652BEA/0x7E652C6D. "sg" matches the `sg_*` FunctionList flags (sync/timing generator, I).
- **cam_strobe.c 0x7E661D84–0x7E66226D:** init 0x7E661D84, set-list setter 0x7E661DA6, finish 0x7E661E2D, 0x7E661E6F → strobe module 0x7E5E2419.
- **cam_watchdog_timer.c 0x7E6629A8–0x7E662C26:** init 0x7E6629A8 (soft timer 0x7E4650A2), register 0x7E6629C7 (← cam.c init, frame init), start/kick/stop 0x7E662A4A/0x7E662A9D/0x7E662AEE (← cam.c power jobs, frame commands; error 0x9302), tick 0x7E662B43, timeout 0x7E662BA7 → damage reporter 0x7E53A76C.

### 2.4 Mirror callback layer (V; F012)

cam_mirror.c 0x7E642C54–0x7E643378 holds about 23 **{post, done}** pairs:
- **post** (26–36 B): stores the result at req+24 and queues its own `done` on `MI_RES` (or `MI_CLS`) through 0x7E64F10E. Some posts take the interrupt lock (0x7E643005/0x7E643039).
- **done** (33–91 B, e.g. F012 0x7E642E1C): result 1 → client hook +8, result 2 → hook +16 (others call hook +4, or the cam timer 0x7E6623CB), then release with 0x7E64F1A5.
- Each post has a **pointer entry 5 bytes before it** (`movm [a2],(sp); add -4,sp`): 0x7E642DF8 for 0x7E642DFD, etc. MI init 0x7E6433B0 stores it in the MEC request (the immediate at 0x7E64355D), and direct callers (`mirror_dummy_post_*_err` 0x7E6436F1–0x7E6438E9) `call` the inner address. The DB lists these prologues as separate 3–5-byte functions (0x7E642C51, 0x7E642C90, 0x7E642CCF, 0x7E642D14 …).

### 2.5 Still and live-bulb callback layer (V; F014)

- **State × event tables:**
  - still **0x7E7BD480**: 25 status rows × 12 event columns of {handler, u16 next status}. Row = status (u16 0x6056EB58) × 96, column × 8 (0x7E65D6E6). Default handler 0x7E657928.
  - live bulb **0x7E7BF220**: 10 × 11, row = status (0x6056ED14) × 88 (0x7E661AAB). Default 0x7E65E1EA.
  - Every non-default cell is a TSV `cell` row (`0xTABLE[i]`: status, column, handler, u16 +4).
- **Posters:** still 0x7E65D41A(a0 owner, d0 event bit, d1 result); live bulb 0x7E6617F4 (→ check 0x7E661851, record 0x7E661916, run 0x7E6619C5). Error store / damage report: still 0x7E65D756 / 0x7E65D9A6, live bulb 0x7E661B1B / 0x7E661CFF.
- **Callback pattern** (still 198 functions, live bulb 142; each is a TSV `callback` row with its bit and line tag):
  - `movm …; mov d0,d2; mov (16,a0),a2`;
  - if the result ≠ 0: error store, then damage report with `mov LINE,d0` (a source-line tag: 935–11124 in LB, 1637–19505 in still);
  - then `mov BIT,d0; … call poster`.
  - Example: F014 0x7E65EA84 posts bit 0x1000 (line 3517); 0x7E65EAB8 posts 0x100000 (line 3553).
  - The bits are the module's own step events. The still/LB monitor prints phase names (0x7E656B1D), not the cam.c factor names, so the cam factor table (03 §1) does not name them (V).
- Smaller families: 18-B "set event bit N" stubs (0x7E65F945 …: cam_ev 0x7E63589A with ids 44…); 86-B request builders 0x7E660C21–0x7E660DCF (named pool take 0x7E642097); 4–21-B pointer-entry prologues and stubs (40 in LB, 42 in still).

## 3. Patterns for classifying a function by its bytes (V)

| Pattern | Signature | Meaning |
|---|---|---|
| Linear switch | `cmp LO,dN … add -LO,dN; asl2 dN (54); mov TAB,a1 (fc dd ..); mov (dN,a1),a1 (f3 91); jmp (a1) (f0 f5)` | `switch` on a dense code; TAB in the module's rodata after its strings |
| Hash switch | `add -K,d1; mov TAB,a2; mov MASK,d0; and d1,d0; asl 3,d0; … cmp 0,d0 (empty = key 0); add 8,a1; cmp END,a1; bcs; mov a2,a1 …; mov (4,a1),a1 (f8 25 04); jmp (a1) (f0 f5)` | {u32 key, label} open-addressing table, key = code − K. Single-probe variant (BC 0x7E53B456): `bne default` right after the first compare |
| Command filter | `movhu (a0),dN` + one of the two switches; each case is `call HANDLER,[regs],N; bra/jmp end` | module command entry (§2.1) |
| Pointer entry | 3–5-B DB "function" `movm [..],(sp); add -N,sp` directly before a function that has direct callers | the same function, reached through a pointer |
| cam_set sequence | `mov a0,a2; mov ID,d0; clr d1; mov 1,a0; call 0x7E635665; …; mov STEP,a0; call 0x7E6359B1; mov ID,d0; mov 1,d1; call 0x7E63589A` (55 B) | start sequence STEP on cam_ev object ID |
| Frame-command stub | `mov FC,d0; mov 0/CB,a1; call 0x7E651483; exthu d0; ret` (13–17 B) | issue frame command FC |
| Step callback / MI post-done | §2.5 / §2.4 | still, live-bulb or mirror completion |

## 4. mdet, SDET end and res (0x7E662C27–0x7E675D98)

The module prefix of the 32-bit codes passed to the recorder 0x7E426D4B marks each part: SDET 0x32xxxxxx, mdet 0x31xxxxxx, res 0x1Fxxxxxx (V). Every function from 0x7E662C27 to 0x7E675E63 has a TSV row (240 rows).

| Range | Component | Basis (V) |
|---|---|---|
| 0x7E662C27–0x7E666C5A | **SDET** (iAuto), 52 functions | init 0x7E662C27 ← Usr0; task 0x7E662DCB; last function 0x7E666C4A; OS wrappers 0x7E666AD6–0x7E666C49 (queue receive 0x7E666AE9, send 0x7E666B45, event wait 0x7E666BD9) |
| 0x7E666C5B–0x7E674DF4 | **mdet**: motion detection and AF subject tracking on the EMS1/EMS2 motion-estimation units, 160 functions | first function 0x7E666C5B calls EMS2 0x7E4600B0; 0x3100xxxx codes |
| 0x7E674DF5–0x7E675D98 | **res**, the flash-resource store | init 0x7E674DF5 ← Usr0; 0x1F0000xx codes |

**SDET → mdet:** SDET reaches mdet only through `mdet_unit_get_moving_object_status` **0x7E673F91** (from SDET's input builders 0x7E6634F7/0x7E663663). Its result is the u16 0x602AC74C: 255 = not run, else 0/1 (I: 1 = moving object). SDET's two scene switches (0x7E663D68 with table 0x7E7C0254, 0x7E6652D7 with hash 0x7E7C0314) map the scene id to a class byte at 0x6056F141 (V).

**mdet parts (V mechanics; the "tracking" role is I, from TAKE's `tr_post` and `af_type:tracking` strings):**

| Part | Range | Entry points |
|---|---|---|
| EMS2 block reader | 0x7E666C5B–0x7E666EB8 | frame set-up 0x7E666C5B; block value 0x7E666CAA; block record (vector) 0x7E666CD0; status decode 0x7E666D4E |
| `mdet` shell | 0x7E666EB9–0x7E667238 | subcommands (table **0x7E7C053C**): `debug` 0x7E666F44 (sets the flag 0x6056F194, tested by 0x7E6671C3), `reg`, `view_st` 0x7E666FE8 (EMS status bits incl. `block_trust`), `view_cor` 0x7E66711E, `unit_init`/`unit_end`/`unit_status`, `ems` (→ 0x7E461313), `test` |
| MDETDATA log saver | 0x7E66723C–0x7E6673A5 | 0x7E66723C(buf, kind, size) writes `MDETDATA\ST|CO|IA<hhmmss>BIN`. These are **mdet** debug logs, not SDET's |
| AF subject tracking | 0x7E6673A6–0x7E66C500 | open 0x7E6673A6 (← TAKE `tr_post`); start 0x7E667472; per-frame **0x7E6682E6** (← TAKE 0x7E59BBD0/0x7E59BCD9): mode 0 → **F015 0x7E668353** (21-slot × 12-B history 0x6056F1BA, rate 15/30/60, core 0x7E66D66B, post 0x7E66891E / reset 0x7E668A46), mode 1 → EMS2 path 0x7E6685B5; window update 0x7E66C143 → 0x7E668B2D → clamp selector 0x7E66AA4A; getters 0x7E66C28A (TAKE) and 0x7E66C1D4 (FCS_MOVIE 0x7E5E8044) |
| EMS1 AF-area motion | 0x7E66C501–0x7E66CE89 | start 0x7E66C501 (← TAKE `ems_start`); per-frame 0x7E66C72B → 0x7E66C9A8 (EMS1 results 0x7E45FDFA/FE53/FEB5); offset getter 0x7E66CE6E (← FCS_MOVIE 0x7E5E85A0) |
| tracking core | 0x7E66CE8A–0x7E670646 | core **0x7E66D66B** → EMS1 read 0x7E66DA1D, match 0x7E66DB1D (3.6 KB), 5-way step 0x7E66EBB7 |
| `mdet_ems2` job layer | 0x7E670647–0x7E673D52 | open 0x7E670647; chains of start → callback pairs (below) |
| moving-object unit | 0x7E673D53–0x7E674DF4 | `mdet_unit_init` 0x7E673EB2, `_end` 0x7E673F2E, `_get_moving_object_status` 0x7E673F91 (names V from the shell help); per-frame 0x7E673F9A (← TAKE 0x7E59BC7B) |

**Window clamps (F016 family, V constants; aspect I):** 0x7E66AA4A picks a clamp by the image aspect pair. (16,9) → F016 0x7E66B36A (y 60–419); (3,2) → 0x7E66B50E (y 26–453); (6,6) → 0x7E66B6B2 (x 80–559); (3,4) → 0x7E66B84E (x 140–499). The full 640×480 frame is the 4:3 case.

**Byte patterns:**
- *ems2 start* (0x7E670B3C and its 7 callers 0x7E670D5D…0x7E67253F): `mov <callback>,dN`, fill a 188-B job at 0x6059710C, call 0x7E46012D then 0x7E460810. The last start 0x7E67283D does not call 0x7E670B3C; it fills its own job at 0x60597340. (A10 2026-11-09)
- *ems2 callback* (0x7E670FB8, 0x7E671208, 0x7E67132B, 0x7E671506, 0x7E671683): `movm`, 0 callers, a result decoder (0x7E460FC2 in 0x7E670FB8, 0x7E460DB8 in the other four; none calls 0x7E46118C), then a direct call to the next start. **Chain ends (V):** three callbacks end a chain instead. 0x7E671E92 (loaded by start 0x7E671CC3) decodes (0x7E460DB8, 0x7E46118C) and calls 0x7E672308 (not a start: it runs the analysis 0x7E672896 only if byte 0x60598D0C = 0 and byte 0x605970E4 ≠ 0, sets 0x60598D0C = 1 when it was 0, then always calls the user callback *(0x605970F0)). 0x7E6725C6 (loaded by 0x7E67253F) decodes (0x7E460DB8), runs 0x7E672896 only if byte 0x605970E4 ≠ 0, and always calls *(0x605970F4). 0x7E67287A (loaded by the last start 0x7E67283D; 28 B, `add -4,sp`, no `movm`, no decoder) calls 0x7E460109 and 0x7E4600DC, then *(0x605970F8). The open 0x7E670647 stores these three user callbacks from its argument (+4/+8/+12); the tracking open 0x7E6673A6 passes 0x7E6686D0, 0x7E6689F3 and 0x7E66C1AF. (A9 2026-11-09) (A10 2026-11-09)
- *debug logger* (0x7E66827C, 0x7E66C6C3, 0x7E66D60D, 0x7E6727BC): prints `datsz:` and calls 0x7E66723C.

**res.** `res_read`(d0 type, d1 id, a0 dst, a1 size) **0x7E674F44** (name V from caller strings; 18 callers) switches on the type through jump table **0x7E7C10A4**:

- 0 INT_LANG 0x7E67510C; 1 EXT_LANG (returns NULL); 2 SOUND 0x7E67534F; 3 PIC 0x7E6753CC;
- 4 the 16 KiB BASIC block at 0x402A0000 0x7E6755B4; 5 BGM at 0x40180000 (I) 0x7E6754F1; 6/7 `lensfav` sector 0x40120000 parts 0/1, F017 0x7E6755F0;
- 8/9 stubs; 10 FILTER 0x7E675538; 11/12 (not in the shell) 0x7E6751C9/0x7E675291; 13 (returns NULL); 14 ARTEFFECT 0x7E67543D; 15 C3D 0x7E67547B.

The type names 0, 1, 2, 3, 10, 14 and 15 come from the `res` shell. Also in res: `res_get_size` 0x7E6750BA, write/erase 0x7E675700 and the `res` shell 0x7E675B1E.

## 5. Command tables of named modules

Slot rows are in the TSV (346 rows; kinds `slot`, `fn`, `step`, `error`, `cmd`, `struct`, `tag`). This part gives the layout of each layer and how to read a slot.

### 5.1 BC (body stabiliser): three layers
- **Boundary (V).** `dbg` debug-log module 0x7E53A981–0x7E53AEA8 sits between the damage reporter and BC: U_SHELL entry `dbg` 0x7E53A9C8 (table word 0x7E732750), init 0x7E53A981 ← boot 0x7E44A043, logger 0x7E53ABE3 ← error recorder 0x7E426D4B. **BC starts at 0x7E53AEA9** (command-layer init; only caller BC init 0x7E53D90C ← Usr0). It is not at 0x7E53BAAD.
- **BC_MAIN 0x7E53D96D (V).** It receives a 16-byte Oimf message from queue var 0x7E43ECCE. The code is msg+8 (the sender's Oimf d1), the payload pointer is msg+12. It dispatches 0–34 through jump table 0x7E744C90. Reply 0x7E54221A, result reporter 0x7E53E24A (damage report 0x7E53A76C unless 0 or 0x823E). Bad code → 0x8201. Senders: TAKE 0x7E596386 (2), 0x7E5A0370 (5/6), 0x7E59CA05 (7/10), 0x7E5A2043/0x7E5A3D80/0x7E5A3EDB (11), 0x7E5A5A92 (12), api 0x7E689726 + PTP 0x7F08xxxx (13), 0x7F080E7E/0x7F080CA3 (14/15), 0x7E598915… (16–19, 32/33), 0x7E5A2830/0x7E5A2C31 (27); shell `bc exec <code>` sends any code (V sites).
  - Codes 5/6 = ref-counted (0x60503BAA) bc_ssc acquire/release 0x0003/0x0103. 32/33 do the same with a sticky flag 0x60503BA8. Reading: stabiliser on/off (I).
  - 0/1/2 = bc_stab ops 0/1/2 (start/stop/check, I). 7/10 = ssc 0x0004/0x0104. 16–19 = ssc 0x0203/0x0303/0x0204/0x0304. 13 = **EXEC**, the command layer below. 14/15 = SIO transaction sets 0x7E53BAF0/0x7E53BCD6. 3, 27, 28 = `return 0` stubs. 4, 8, 9, 20–26, 30, 31 = no handler.
- **Sync API 0x7E53DACD(a0 req) (V).** It runs in the caller's context, with work on soft-IRQ ring 0. Code = u16 req+0, 2–36, table 0x7E744D1C. Handled: 2, 7, 10, 20, 30 (raw SIO command 0x25), 31, 35, 36. The rest → 0x8201. Callers: MEC 0x7E517207/0x7E5172CE, TAKE 0x7E59B762/0x7E59B83E/0x7E5A201C/0x7E5A3EDB/0x7E5A50EB/0x7E5A5365, shell `aexec`.
- **Command layer 0x7E53AEC5 (V).** Class = u16 req+0; the body starts at req+4. Bad class → 0x8213.
  - class 0: stream read, 0x7E53AF14;
  - class 1: chunked write, SIO command 0x26, ≤ 64 B per chunk, 0x7E53AFBB;
  - class 2: cmds 2–64, table 0x7E7443C8; 13 handled (they map to bc_stab ops 5–13);
  - class 3: hash 0x7E7444C4, 16 slots, key = cmd − 1, single probe. cmd 2 open, 4/5 open/close stream A, 6/7 open/close stream B, 8 stub, 9 set parameter (= shell `setprm`), 10 get parameter (`getprm`), 11 SIO command 0x45, **255 raw serial pass-through 0x7E53B7F3** (= shell `com`).
  - Bad cmd → 0x8214.
- **bc_ssc request 0x7E54024C (V).** u16 code = (variant << 8) | resource. Bit 0x100 = release (ref count 0x60503FC6[resource] − 1); otherwise acquire. **bc_stab 0x7E5410C7** has ops 0–13 in table 0x7E745C74 (3 and 4 empty).
- **Pattern for classifying a function:** a class-2 handler is `call 0x7E5072ED` (scheap alloc), `mov N,d0; movhu d0,(a2)` (N = bc_stab op), `call 0x7E5410C7`, copy reply, `call 0x7E5072FB` (free).

### 5.2 Lens command layer (LENS_MAIN side)
- **Request (V, 0x7E52272C):** 24 B. +0 link, +4 done callback, +10 u16 **class**, +12 byte, +16 pointer to a 68-B payload {+0 u16 mode, +2 u16 value…}. Alloc 0x7E533AB3 (148 call sites) is a general two-pool allocator(size), not a 24-B request allocator: ≤ 128 B from pool 0x6050260C (32 blocks), ≤ 8192 B from pool 0x60502618 (4 blocks) (0x7E533AD2; pools built by 0x7E533A2E); other sizes are used too, e.g. 20 B from `lens askdata` 0x7E525D56; free 0x7E533B84, generic submit 0x7E51F98E (107 callers). (C5 2026-11-09)
- **Sender 0x7E52BD9E (V).** It logs tag `ld0/` `ld1/` `LD2/`…`LD9/` (tag digit = class) and queues to the lens serial layer 0x7E534CEC.
- **Class dispatcher 0x7E52C921**, table 0x7E741240 (V). Class → builder (command bytes the builder writes, V):
  0 0x7E52CA7D/0x7E52CA2B; 1 0x7E52CAC2 (0xA0/0xB0/0xB1); **2 aperture** 0x7E52CB97 (0xB0/0xB1); **3 focus** 0x7E52D2EC (0xB0/0xB1); 4 0x7E52E118 (0xB0); **5 askdata** 0x7E52E3F1 (0xC0/0xC1); 6 0x7E52EAE2 (0xD1); **7 lens firmware** 0x7E52ED80 (0xF0 + 0x60–0x77); 8 0x7E52F08D (0x79/0xF0); **9 lens ROM** 0x7E52F1E0 (0x90).
- **Mode tables (V; names from the lens shell help, which uses the same numbers).**
  Aperture hash 0x7E741268, key = mode + 1, 19 modes (OPEN 0x01, AV_ABS 0x21, AV_ABS_RESET 0x22; STOP 0x50 has no slot). Focus hash 0x7E741368 (64 slots), key = mode + 1, 35 modes 0x0000–0x8007. Askdata linear table 0x7E741568, index = mode 0x00–0x62, 48 modes handled.
- **`Led-` (0x7E52272C) is not an LED command.** It is an **askdata STILLEXP_STATUS** request: mode 0x24, or 0x4B M_STILLEXP_STATUS_LV + 0x0600 on the newer protocol (0x7E52237F = 1). cam_lens.c queues it (0x7E64049A → 0x7E522719 → soft-IRQ ring 0) (V).
- **`lgr+`/`lgr-` (0x7E5229A3)** is a getter, not a command. It returns an s16 for BC 0x7E53D77E: 0x604F904E if bit 0x01 of 0x604F9049 is set, else lens record +38 (V). That this is focal length for the stabiliser is I.
- 0x7E532C3C classifies lens command bytes (hash 0x7E741CF4, key = byte − 95): 0x60, 0x70, 0x80/81, 0x90, 0xA0, 0xB0–B2, 0xC0–C3, 0xD0–D3, 0xE0, 0xF0 (V). Other trace tags (V strings, roles I) are in the TSV: La1/ La2/ cpl/ LPs/ LRs/ LsE/ LPe/ LRe/ lsP/ Ls0–LsC/ Lcs/ CcN/ CcM/ Mi1/ Mi2/ Ma1/ Mr1/.
- **LENS_FLASH (V):** cmd 1 → step chain 0x7E5309A0; cmd 2 → 0x7E530DEF, lens-ROM ops 0–11 (table 0x7E741BA8), each a class-9 request waiting on flag 0x7E43EB9C; cmd 3 → 0x7E531540/0x7E5315FD, a 34-state machine (table 0x7E741BD8, 34 entries; I: lens data cache).

### 5.3 LENS_FIRM_UP step chain (corrects 02 §1.9)
The **command order (V)** is **7 → 0 → 3 → [4 → 5 → compare → 6] × packets → 1**. Type-2 lenses use 0x1000 + cmd. Each step function handles the reply of the previous command and sends the next. The step pointer is at req+4; retry count 0x604F9396: a failed reply is resubmitted while the count is ≤ 3, and the error is reported on the 4th consecutive failure (3 retries). Each success clears the count. (A8 2026-11-09)

| step fn | handles reply of | sends | error on the 4th consecutive failure (3 retries) (A8 2026-11-09) |
|---|---|---|---|
| 0x7E52FE8C | — (start; fw_kind from 0x7E530524: P→2, Q→4, S→1, any other letter byte − 79, e.g. O→0, R→3) | by the two protocol flags 0x7E51FDB4(0)/(1): (1,0) → 7; (0,1) → 0x1007; (0,0) → a probe 0x7E53048E, whose done 0x7E5304BA re-runs the start when a flag is set, else counts failures in **0x604F939A** (not the chain's 0x604F9396) | 0x6610 at once when both flags are 1 (no retry); 0x6610 when the probe count 0x604F939A > 3 (A9 2026-11-09) |
| 0x7E52FFB3 | 7 | 0 | 0x6608 |
| 0x7E530020 | 0 | 3 | 0x6601 |
| 0x7E53008E | 3 | 4 (packet 0) | 0x6604 |
| 0x7E530103 | 4 | 5 | 0x6605 |
| 0x7E530171 | 5 | match → 6; mismatch → 4 again | 0x6606 transport; 0x6609 on the 4th consecutive mismatch (count 0x604F9398 > 3) (A8 2026-11-09) |
| 0x7E53023E | 6 | next packet → 4; last → 1 | 0x6607 |
| 0x7E53030A | 1 | — (done) | 0x6602 |

- Abort 0x7E53043E sends cmd 0 and reports 0x604F943C. Class-7 bytes: cmd n → 0x70 + n (type 1) or 0x60 + n (type 2). The reply handler 0x7E52F025 copies the 128-B read-back of 0x65/0x75 to 0x604F93BC. For 0x67/0x77 it parses id, hw version, version, extension and serial[12] into 0x604F939C (V). So the roles are: cmd 7 = identify, 4 = write a 128-B packet, 5 = read back, 6 = next/commit, 1 = finish (I; the 4/5 roles are firm).
- 0x7E5307C7 skips the compare for lens ids 0x21001–0x21004 with u16 0x1000 (V; reason I). No 0x6603 code exists.

### 5.4 FCS_MOVIE
- **Task messages (V):** hash 0x7E7A896C, 16 slots, key = code − 0x10FF.
  0x1100/0x1200/0x3000 → frame AF step 0x7E6110C3; 0x1202 (if the lens is ready), 0x1400, 0x1700 → C-AF start 0x7E611470 (`FtCafMvAF Start!!`); 0x1600 → 0x7E611515; 0x1800 → tracking update 0x7E611796; 0x1101, 0x1201, 0x1701, 0x1704, 0x1801, 0x3001 are listed but go to the default (no action).
- **Lens requests (V):** each `fcs_lens_*` builder fills a local request {+0 result pointer, +4 done callback, +8 class, +12 mode, value}, submits with 0x7E51F98E and blocks on flag 0x7E43EB7C bit 1 (0x7E611E49). For example, 0x7E60AA5B = class 3 mode 0x1002 DEF2PLS_RE; 0x7E60B1E1 = class 2 aperture 0x22. Twelve builders are in the TSV.
- **Callbacks (V):** **0x7E60B0E1** `FCS MOVIE LENS post` (`sLQ/`, shared by about 20 builders: result → *(req+0), set bit 1); **0x7E60B167** `sync post` (`sLR/`, for the sync request 0x7E60B3B8 `s10/`, sync start 0x7E535A21: result → *(req+4)); **0x7E60B572** `sync post_e` (for 0x7E60B5AF); **0x7E60A7CA** (`sL5/`, for the non-blocking request 0x7E60A921).

### 5.5 External flash (STB_EXTERNAL)
- **Descriptor 0x6054AABC (V):** +0 completion callback, called with d0 = status after a tx-only completion, after rx completion and on error (0x7E5DE8AE in 22 of the 25 set-ups; it logs ` sio time out` only for a non-zero status; 0x7E5DC7FD / 0x7E5DC9F3 in the 0x06/0x0600 paths); +4 owner/context pointer (0 in the handshake set-ups; the caller's request in the 0x06/0x0600 paths 0x7E5DC71A, 0x7E5DC893, 0x7E5DC950, read back by their callbacks as `(4,desc)`); +8 u16 command; +10 u16 tx length; +12 u16 rx length; **+14 inline tx frame** (+14 = tx byte 0 = 0x55 for most frames, not the 1-byte cmd-0 frame; +15 = tx byte 1 = the command low byte for 0x81–0x84/0x7F/6, but a subcode 2/3/4 for command 0x0600); rx data at desc+214. Send 0x7E5DC0F7 (sends u16 +10 bytes from desc+14), wait 0x7E5DE91F. (A8 2026-11-09)
- **Command bytes (V):** 0x00 firmup data stream (STB firmup steps 0x7E5DEC15…, PTP 0x7F08443D); 0x01, 0x7F, 0x81–0x88 detect/handshake sequence 0x7E5DD358 (0x81 rx 4, 0x82 rx 9, 0x86 rx 7 status, 0x87 tx 13); 0x05 video light; 0x06/0x07/0x0600 tx 4, rx 1; **0x89** tx 2, rx 2, checked by rx[1] = rx[0] + 0x89, sent only from event 0x402 of the video-light group (V; meaning unknown, I: a video-light level query).
- **Event codes (V):** codes 0–4, 0x200/0x201, 0x300/0x301, 0x400–0x402, 0x800, 0x900, 0x1000. All three tables use **key = code + 1**:
  pre-check 0x7E5DC4A1 (`stb_external_com_exec`, 0x7E79F9AC), executor 0x7E5DCC5C (`EXT mode_set`, 0x7E79FAAC; 0x1000 → strobe firmware update 0x7E5DF13A, which FIRMUP_SRV's cmd 0x1000 reaches), post-update 0x7E5DC602 (0x7E79FA2C).

### 5.6 ADCONV request 0x7E45BB10
- The "gap" 0x7E45B6BE–0x7E45CE11 (0x7E45B67E is a `per_adc` shell subcommand) (coordinator 2026-11-09, from fixes-D3) is the **ADCONV driver** itself, between the `per_adc` shell and the ADCONV debug shell 0x7E45CE12 (V).
- **Submit 0x7E45BB10(a0 req) (V).** It looks up channel u8 req+0 in the table 0x7E4C4908 (9 × 16 B: channel, mode, mask) and dispatches on the mode (1, 2, 3, 7, 8, 9 → six engines). Unknown channel → log 0x19001401.
- **Request (52 B, V):** +0 channel, +1 type (0xF1 special), +4 and +8 per-request u32 parameters (+4/+8 = 1500/5 in 0x7E45E38D and 0x7E5394B5, 1500/4 in 0x7F080BEC, 750/5 in MEC 0x7E5175C9, 750/2 in ADC-key 0x7E50B1B4, 750/1 in 0x7E4589DC; +4 = 750 in the ADCONV shell 0x7E45CE5B), +12 result buffer, +32 async callback, +40 sync marker. **Completion 0x7E45CCA1 (V):** calls +32 if set; otherwise, only if +40 ≠ 0, copies the request to 0x6041538C and sets event flag 0x7E43EBB2. A request with neither is dropped without a signal. (A8 2026-11-09)
- **Channels (V):** 4 and 13 = battery/power. 15, 34 and 41 = ccd_temp (0x7E45E206 → 0x7E45E27F with builder 0x7E45E38D = 15, 0x7E45E2B5 with builder 0x7E45E3CF = 34, 0x7E45E556 with builder 0x7E45E411 = 41). 34 is shared with the per_acc accelerometer (builder 0x7E4589DC, `mov 34` at 0x7E458A24, request 0x60414908; its I²C check `ACC:I2C NG?`). 22 = ADC key (0x7E50B1B4 copies the channel from table 0x7E7354CC entry 0, byte +4 = 0x16). 38 = MEC layer 0x7E5175C9. 39 = MEC 0x7E51773D (`mov 39,d0; call 0x7E45BADC`: static request 0x60414BA8, type 0xF1). Only channel 21 has no user found. Callbacks: only the ADC-key init 0x7E50B1B4 sets +32 = 0x7E50B2F5. 0x7E50B356 sets 0x7E50B606 when the u16 at its a2 is 4094, else F002 0x7E50B724. 0x7E50B512/0x7E50B576/0x7E50B5DF/0x7E50B877 resubmit requests without setting +32. (A9 2026-11-09)

### 5.7 EXP_MOVIE (live-view AE) range and dispatch (V)

- **Range 0x7E68F07C–0x7E6A935C.** Init `EXP_MOVIE_POST` 0x7E68F07C (← Usr0; queue of 20 × 24-B messages, id var 0x7E43ECEC); task 0x7E68F0DD. `[exp]` strings run to 0x7E6A8C78. The tail 0x7E6A8F41–0x7E6A9354 is a set of small conversion helpers used by exp, `api_rec_Get_Bracket_Information` 0x7E68BD97 and the GUI. The last two exp functions are the `exth d0; retf` stubs 0x7E6A9355/0x7E6A9359 (← api Get_CameraInfo, REC). The HDMI driver starts at **0x7E6A935D** (callers 0x7E6AC4DF; `[HDMI-DRV]` from 0x7E6A93E5).
- **Messages (hash 0x7E7DA1C0, key = code − 0x4FF):** 0x500/0x507/0x700 → 0x7E68F1FE; 0x501/0x701 → 0x7E68F296; 0x503/0x504 → 0x7E68F24B; 0x505 → 0x7E69B03A; 0x90A → 0x7E68F310; 0x502, 0x506, 0x50A, 0x50B, 0x50D, 0x50E, 0x702, 0x801, 0x90B, 0x1402 → 0x7E6904C1.- The same code space is filtered again by 0x7E69AE04 (0x7E7DD0C4), 0x7E69BB13 (0x7E7DFF78), 0x7E6A3221 (0x7E7E0308) and 0x7E6A60F3 (0x7E7E0690). The `exp` shell is 0x7E69C056 (jump 0x7E7E0078, 14 subcommands). Two large switches index metering/AE modes: 0x7E691B7B (0x7E7DADB4, values 3–183) and 0x7E69433B (hash 0x7E7DBC94, 12–183). Code names are not found.

## 6. Dispatch-table index (summary; rows in the TSV)

The scanner (`jt.py`) finds every `jmp (aN)` in 0x7E520000–0x7E731588 and reads its table: **176 linear jump tables and 86 hash tables of ≥ 8 entries** (262 `jumptable`/`hashtable` rows). A table row gives the owner function and module, the index transform (`slot = value − K` or `key = value − K`), the slot count, the number of handled slots and the default label. Linear tables are cut at the first word that is not a label inside the owner. Hash dispatchers that do `inc dN` before the lookup (lens aperture/focus/class 7, the three STB_EXTERNAL tables, the still phase and sensor-mode name lookups, and others) have key = value + 1, and their rows say so. Where the compare bounds and the offset disagree, the row says "check by hand". 7 `jmp (aN)` sites load the table pointer from a register and are not resolved (0x7E52114E, 0x7E56F113, 0x7E5829E8 TAKE_EXPOSE, 0x7E5881D9 TAKE_FOCUS, 0x7E5C39D3, 0x7E6B9DA1, 0x7E6CBEBC; the TAKE ones are 13e §4's hash tables). `ptab.py` adds **176 data function-pointer tables** (`fntable` rows; the record stride is a heuristic, I).

Tables per owner: HDMI/display/touch 40, movie 34, IMG 25, AF (FCS_MOVIE/IAF/contrast) 19, api 17, lens 16, files 14, art 13, strobe 10, TAKE 9, REC 9, Exif 9, EXP_MOVIE 9, mcon 6, cam.c 5, BC 5, WB 3, other camera-core files 1–2 each. Slot rows exist for the camera-core and EXP_MOVIE tables (cam_frame, imgdev, MI, cam_set, sg, shutter, still/LB filters) and for the named-module tables of §5. The pure name lookups (cam.c 0x7E627F1E/0x7E62803B, imgdev 0x7E63BAA6, still 0x7E656B1D/0x7E656C5E, LB 0x7E65DA4A) are named in section 03.

**U_SHELL `face` subcommand table 0x7E8DE4EC (L1 2026-11-09, V).** It is in the `.data` image (RAM copy 0x602AE02C), so the jump-table scanner does not see it. 20 records `{handler, name}`: `start`, `stop`, `get`, `keep`, `reset`, `abort`, `prog`, `get_eye`, `dump`, `setting`, `log`, `pt`, `load`, `set_pos`, `get_pos`, `set_info`, `mdm`, `reg`, `tune_l`, `tune_g` (handlers 0x7E6F4EC2…0x7E6F5B7F, each logs `face_dbg_<name> in`; the TSV row gives all 20). The dispatcher 0x7E6F4D77 is the `face` entry of the 54-family U_SHELL table (word 0x7E7333B8): it compares argv[1] with each name (strcmp 0x7E500DCA) in a loop of 20 and calls the handler. Review C4 (round 4 review 2) listed 17 names; it left out `start`, `stop` and `pt`, and its F021 0x7E6F591D is the `reg` handler (`face reg X Y`), not `mdm` (0x7E6F5840, `face mdm X Y`).

## 7. Corrections

- **14b §1 / §8, modules.tsv:** cam_lens.c is **0x7E640200–0x7E640857**, not "~0x7E63E5xx–0x7E640857". The imgdev code runs to **0x7E6401FF** (command layer, driver and sequence programs, §1).
- **C3 review F013:** the dispatcher table is **0x7E7BB094** (`mov 2122035348,a2`), not 0x7E7B9A94. The dispatcher belongs to **cam_set.c**, not to an unnamed "cam_seq.c": module byte 0x11 and the rodata rule (§1).
- **03 §3:**
  - cam_sem.c is 0x7E64F085–0x7E64F743; 0x7E64F2A2 is its dump, not its end.
  - Add cam_serial.c, cam_sg.c, cam_siodrv.c, the still glue, cam_strobe.c and cam_watchdog_timer.c (§1).
  - cam_still_live_bulb.c ends at 0x7E661D83, not 0x7E6619C5.
  - cam_shutter.c is 0x7E6557CE–0x7E6561D9.
  - cam_timer.c is 0x7E66226E–0x7E6629A7.
- **Regions table:**
  - Row 0x7E621020–0x7E6A1020 → 0x7E621020–**0x7E6A935C**: the exp module (EXP_MOVIE) runs to 0x7E6A935C.
  - Row 0x7E6A1020–0x7E70B000 starts at **0x7E6A935D** with the HDMI driver; the display, touch and HDMI tasks follow, and `mov*.c` starts at 0x7E6C3955. Its label "Movie (`mov*.c`)" first is wrong for 0x7E6A1020–0x7E6C3954.
  - Inside the camera-core row, name mdet 0x7E666C5B–0x7E674DF4 and res 0x7E674DF5–0x7E675D98 (§4).
- **03 overview / §7b:**
  - "EXP_MOVIE … about ~~0x7E68F000–0x7E6A0000~~" (L1 2026-11-09) → 0x7E68F07C–0x7E6A935C. Section 12's 0x7E6A9400 was right to within one HDMI function.
  - The mdet/res corrections are in §4.
- **03 §1 "Event factor bits":** the table names cam.c's AE/AF/MEC factor bits only. The still and live-bulb step-event bits (§2.5) are the modules' own and are not named by it.
- **03 §4 still phases are one too high (V).** The name lookup 0x7E656B1D does `inc d0` before its hash lookup (key = phase + 1). The phase values are therefore 0 READY, 1 TAKE, 2 STOP, 3 ABORT, 4 TERMINATE, 5 CONTINUE_READY, 6 CONTINUE_PAUSE, 7 CONTINUE_RESTART, 8/9 PRE_ACTION_ON/OFF, 10 MIRROR_DOWN, 11 CAPTURE_ENABLE, 12 FORCE_CAPTURE, 13 APERTURE_ENABLE; 0x100–0x10C BULB_*; 0xFFFF PHASE_NONE. This agrees with cam.c's still item 0x7E62952E (phase 0 → STL/RDY; 1 or 11 → STL/TAK; 5 → STL/CRDY).
- **02 table / §1.9 (from §5):**
  - BC is 0x7E53AEA9–~~0x7E542B4E~~ ~0x7E542BA5 (0x7E542B4E is inside `[BC FUP]VERIFY` 0x7E542AFE, which ends at 0x7E542BA5; where BC ends after it was not traced (L1 2026-11-09)); 0x7E53A981–0x7E53AEA8 is the `dbg` debug-log module.
  - The LENS_FIRM_UP chain starts with cmd 7. Each error code belongs to the command whose reply failed (§5.3). There is no 0x6603.
- **C3 F003:** `Led-` is the askdata STILLEXP_STATUS request, not an LED command. **C3 F002 / 13f:** 0x7E45B6BE–0x7E45CE11 (0x7E45B67E is a `per_adc` shell subcommand) (coordinator 2026-11-09, from fixes-D3) is the ADCONV driver, and 0x7E45BB10 is its request submit.
- **03 §7b / 14b §6 (from §4):**
  - ~~0x7E667400–0x7E675000~~ 0x7E666C5B–0x7E675D98 (mdet 0x7E666C5B–0x7E674DF4 and res 0x7E674DF5–0x7E675D98, §4 (L1 2026-11-09)) is the mdet library and res, not SDET's algorithm library.
  - `ST/CO/IA…BIN`/`MDETDATA` are mdet debug logs.
  - "SDET algorithm block 0x7E66C9A8/0x7E66DA1D" is mdet: EMS1 AF-area motion and the tracking core.
  - The loader 0x7E674F44 is `res_read`.
- **Database note (fwmap):** pointer-entry prologues (`movm …; add -N,sp`, 3–5 B) before a directly-called function are listed as separate functions (MI: 0x7E642C51, 0x7E642C90 …; still/LB: many 4–5-B "functions"). They are the same function as the next DB entry.
- **modules.tsv rows to add or change (not edited here):**
  - `7e63d1c1 7e6401ff imgdev driver/sequences` (was 7e63d0de (L1 2026-11-09));
  - `7e640200 7e640844 cam_lens.c`;
  - `7e64f744 7e650467 cam_serial.c inferred`;
  - cam_set.c first_fn `7e65046f`, last `7e652ae2`;
  - `7e652af3 7e6557cd cam_sg.c inferred`;
  - `7e6561da 7e65663a cam_siodrv.c inferred`;
  - `7e661d84 7e66226d cam_strobe.c inferred`;
  - `7e6629a8 7e662c26 cam_watchdog_timer.c inferred`;
  - cam_still_live_bulb.c last `7e661cff`;
  - `7e662c27 7e666c5a SDET`, `7e666c5b 7e674df4 mdet`, `7e674df5 7e675d98 res` (unnamed modules).

## 8. Open questions

1. The names of cam_set codes 18, 19, 83–101 and of the frame commands. Neither cam.c's nor imgdev's name table covers them. E-PL7's camera core is a later generation with other names.
2. The meaning of the 12 still / 11 live-bulb event columns of the state tables, and of the step-event bits. A name table may exist in the status dumps 0x7E656F6F/0x7E65DCAE (rows "Ready, Take, Mirror Down …"); not checked.
3. The split of 0x7E643933–0x7E64F084 into cam_param/pfp/port/prepro/rap.c (cam_sg/serial/siodrv are now placed). Is the imgdev "sequence programs" block the E-PL7 cam_imgdev_sensor.c?
4. What the MMIO block 0x99900000 (IRQ 7, three sources) and sg's IRQs 4–6 are in hardware terms (I: sensor serial / VD-HD sync).
5. From the sub-reports: names of lens classes 0, 1, 4, 6, 8; meanings of the BC_MAIN codes (no strings in E-PM2 or E-PL7); the external-flash 0x8x commands; what SDET does with the moving-object status, what the class byte 0x6056F141 means, and what tracking mode 1 is used for; res types 11/12.
6. The EXP_MOVIE message code names (0x500–0x1402) and the senders: only exp functions load the queue id variable 0x7E43ECEC (V), so other modules must post through an exp function; that entry is not yet found.

# 03 — Camera core, exposure, still recording, art filters, face detection

Scope: block 0, 0x7E621020–0x7E6A1020 (cam*.c, api_*.c, EXP_MOVIE, SDET), 0x7E6E0000–0x7E730000 (rec_*.c, FACE_*, art_*.c), and the tasks named in the brief. Read-only work. Labels: **verified** means I read the code or the bytes and they show this. **inferred** means the claim comes from strings, names or layout only.

## Overview

- The "camera core" (`cam*.c`, 0x7E627E9F–0x7E66296B) is not a task loop. **Verified:** the CAM_MAIN task entry 0x7E62970B is one `retf [],0` instruction, with a 0x40-byte stack. The only reference to it is the task-table row at 0x7E438EF0. Callers call cam.c directly through `CamCommand(packet)` at 0x7E628303 (111 call sites). Slow work goes to named "resource objects" (cam_sem.c). These run their jobs from a software-interrupt-style deferred-call ring (0x7E45F14D…0x7E45F1E6).
- Above the camera core is a large **camera API layer** (`api_<group>_<Function>`, about 640 functions, 0x7E675E64–0x7E68F048). The GUI/app calls it. Asynchronous APIs reserve a packet and call `api_exec_start(funcno, event, packet)` at 0x7E67E493. A 36-entry table gives each funcno a destination queue. Completions come back through `api_eventque.c` (`appevent::Wait_Event`).
- Live-view/movie AE is the **EXP_MOVIE** task (0x7E68F0DD, about 0x7E68F000–0x7E6A0000). Scene detection for iAuto is **SDET** (0x7E662DCB). Still-shot AE (TAKE_EXPOSE, 0x7E5829E8) is outside this range. I name it here only for orientation.
- Still recording uses the REC_* tasks (0x7E70B435…0x7E71B612). Art filters use ART_IMG_CM/CS/CF (0x7E729684…0x7E729AF8) with one source file per filter. Face detection uses FACE_MAIN/FD/PT0. See §8–§10 (summarised from parallel sub-investigations, with their labels kept).

## 1. cam.c command interface (the "CAM_MAIN" logic)

**Entry points (verified)**

| Address | Role |
|---|---|
| 0x7E628161 | cam init. Called from 0x7E503DD4 (USRSTART area). Creates the CAM_PW/CAM_CL objects through 0x7E64F085, sets state 0 and power count 0. |
| 0x7E628303 | `CamCommand(a0=packet)`. Reads u16 `cmd` at packet+0. Accepts 3 ≤ cmd ≤ 147. Looks up `key = cmd−2` in a 32-slot hash table of {key, handler} at **0x7E7AC020**. An unknown cmd calls `cam_damage(0x0A101002, cmd, 14848)` and returns 0x3A00. |
| 0x7E627F1E | name lookup for cmd (same key scheme, table 0x7E7ABE20). Used by the debug monitor. |
| 0x7E62955D | `Status [%02d]` dump: state byte 0x6054C7E5, power count 0x6054C7E4, and the packet list at 0x6054C7F4 ("Set Execute / Cancel Request / Set Cancel"). The `cam dbginfo` shell command calls it (0x7E63213F). |

**Command set (verified from tables 0x7E7AC020 and 0x7E7ABE20; packet code = key + 2)**

| code | name | handler | what the handler does (verified unless marked) |
|---|---|---|---|
| 3 | COM_CLOCK_OFF | 0x7E628D52 | queues the packet callback (+40) on soft-IRQ ring 0 (0x7E45F14D) and returns 0 |
| 4 | COM_CLOCK_ON | 0x7E628D38 | same |
| 5 | COM_OFF | 0x7E62836F | posts job 0x7E6287E2 to object `CAM_PW`. The job decrements the power count. When the count reaches 0, state = 1 (OFF). |
| 6 | COM_ON | 0x7E628361 | posts job 0x7E6285B8 to `CAM_PW`. The job increments the power count (cap 127). The first ON sets state = 2 (ON). |
| 7 | COM_SET | 0x7E628573 | settings list. Packet+36 → 0x7E629373. Packet+32 → item → 0x7E629291 (item id via RAM table 0x602A2758). Otherwise 0x7E6289AE (packet list, then still-func 0x7E6566D9). |
| 8 | COM_GET | 0x7E6288E5 | |
| 13 | COM_READY_ON | 0x7E62889A | |
| 15 / 16 | COM_SETUP / COM_SETDOWN | 0x7E628BAE / 0x7E628C10 | |
| 17 | COM_ABORT | 0x7E628ACD | state = 11 (ABORT) |
| 0x82–0x84 | COM_DEFECT_SEARCH / _SAVE / _UPDATE | 0x7E628391 | **returns 0 and does nothing.** All three share one stub. |
| 0x86 / 0x87 / 0x88 | COM_CANCEL_ / EXECUTE_ / ACCEPT_REQUEST | 0x7E628D6C / 0x7E628E12 / 0x7E628E92 | packet-list control |
| 0x89 | COM_MOVIE_ENABLE | 0x7E628F9E | |
| 0x90 / 0x91 | COM_MEC_POWERON / POWEROFF | 0x7E628FF7 / 0x7E629082 | mechanics power (inferred: shutter) |
| 0x92 / 0x93 | COM_MEC_SETUP/SETDOWN_HIGH_SPEED | 0x7E628C72 / 0x7E628CD5 | |
| 0x80, 0x81, 0x85 | COM_VDINT, COM_GET_SETTING, COM_READY_OFF | — | named in the name table but **not in the dispatch table**. They take the "unknown command" path. |

**State machine (verified: the only writer is 0x7E629554, `movbu d0,(0x6054C7E5)`, with 6 call sites)**

| state | name | set by |
|---|---|---|
| 0 | IDLE | init 0x7E628161 |
| 1 / 2 | OFF / ON | COM_OFF last / COM_ON first |
| 3–7 | HS, HSSC, MSSC, LSSC, HSHR | COM_SET sensor-mode item 0x7E6294E6: value 0–4 |
| 8 | (no name; prints "Unknown") | never set |
| 9 / 10 | CLIP / FULL | sensor-mode value 5 / 6 |
| 11 | ABORT | COM_ABORT |
| 12 / 13 / 14 | STL/RDY, STL/TAK, STL/CRDY | still item 0x7E62952E: phase 0 → 12; 1 or 11 → 13; 5 → 14 |
| 15 | STL/ABT | name exists, no write site found |

Sensor modes (verified table 0x7E7ABDA0, key = mode+1): 0 HS, 1 HSSC, 2 MSSC, 3 LSSC, 4 HSHR, 5 CLIP, 6 FULL, 7 STILL, 0xFFFF MODE_NON. **Inferred:** HS* are live-view/movie readouts at high, mid and low frame rates. CLIP is a cropped readout (magnify). FULL/STILL are full-resolution readouts. The `cam still` help calls mode 7 "Zengaso" (全画素, all pixels).

**Event "factor" bits** (verified table 0x7E7ABF20, printed by the debug monitor): 0x1 AE_BRIGHT, 0x2 AE_START, 0x4 AE_CAPTURE, 0x8/0x10 AE_EXPAND1/2, 0x40 AWB_START, 0x80 AWB_CAPTURE, 0x100 AE_FPN, 0x200 AF_CONTRAST, 0x400 AF_START, 0x800 AF_CAPTURE, 0x2000 PRO_START, 0x4000 PRO_PRECAPTURE, 0x8000 PRO_CAPTURE, 0x10000 PRO_EMS, 0x20000/0x40000 MEC_APERTURE_START/END, 0x100000–0x1000000 MEC_MIRROR_START/END/PRE1-3, 0x10000000 EXPOSE, 0x20000000 EXPOSE_END, 0x40000000 EXPOSE_INTERVAL.

**Callers of CamCommand (verified call sites):** TAKE region 0x7E598281–0x7E5A8xxx, 0x7E5D1FDC/0x7E5E3823, EXP_MOVIE (0x7E68F862, 0x7E698442), REC (0x7E710A84 `rec_cam_get_awb_exec`), the `cam` debug shell (0x7E62F13E…0x7E6326FD), and 0x7F0846AB.

## 2. cam_sem.c resource objects and the deferred-call ring

- **Verified.** `0x7E64F085` creates a named object. It is called once by each module init (17 callers). `0x7E64F10E(d0=tag, a0=name, a1=func, d1=info)` posts a job:
  - It finds the object by name (0x7E64F6D2, a linked list at 0x6055E8B8) and allocates a {func, info, tag} record.
  - If the object is idle (byte +16 = 0), the record goes on a global run list at 0x6055E8BC. Otherwise it waits on the object.
  - When the runner is not active (0x6055E8B4 = 0), it calls 0x7E64F49E, which pushes worker 0x7E64F42A into ring 2 (0x7E45F1B3).
  - The worker pops records and calls `func(d0=0, a0=info, d1=tag)`. `0x7E64F1A5` (58 callers) is the matching release/completion call (inferred from symmetry).
- **Verified.** 0x7E45F14D/80/B3/E6 are four copies of one routine. Each pushes {func, arg, u16} into a 32-entry ring (12-byte entries; `udfu01 12,d1` indexes it) and writes 1 to MMIO 0x9A1000F4/F8/FC/100. **Inferred:** a 4-level software-interrupt trigger. This is also evidence that `udfu01 imm,reg` is a multiply.
- Object names found (verified strings, creator in parentheses): CAM_PW, CAM_CL (cam.c), AE_SEM (0x7E629854), CAMAFD (0x7E62A962), APT_EXE/APT_PST (aperture execute/post, 0x7E62B4DD), EV_SEM (cam_ev.c 0x7E635D50), MI_RES/MI_CLS/MI_MEM (mirror, 0x7E642325), SH_RES/SH_MEM (shutter, 0x7E6557CE), STLSEM (still func, 0x7E656D91), S_LB_M/S_LB_S (live bulb, 0x7E65DAC7), TM_SEM (cam_timer, 0x7E662535), plus CAMLNS, FDRV, FSE1/2, FSA1/2, FSN1, SPRDRV.
- **Inferred:** the mirror code is a stub left over from Olympus DSLR code. It has `mirror_dummy_post_*_err` strings (0x7E6436F1) and STS_MIRROR_DOWN* phases, and the E-PM2 has no mirror.

## 3. Other cam_*.c modules (map)

| File | Range (first string fn) | What (label) |
|---|---|---|
| fcs/AF helpers | 0x7E621020–0x7E627E00 | contrast-AF peak search (`spot_calc_forcus_pos`, VHPF), `fcs mov set` shell. Not cam.c (inferred from strings). |
| cam.c | 0x7E627E9F–0x7E629900 | §1 (verified) |
| AE/aperture | 0x7E629854 AE_SEM, 0x7E62B4DD APT_* | AE resource, aperture execute/post (inferred) |
| cam_contrast.c | 0x7E62D803 | contrast-AF client list: factor/number/update per client (inferred) |
| cam_damage.c | 0x7E62EA55, 0x7E62EAF3 | §5 (verified) |
| `cam` debug shell | 0x7E62EB8E, table 0x7E7AC414 | §6 (verified) |
| cam_debug_monitor.c | 0x7E632EEB–0x7E633CC5 | §6 (verified) |
| cam_ev.c | 0x7E635A08, EV_SEM | event objects ("req post num logic code"), inferred |
| cam_frame.c / cam_frame_sync.c | 0x7E63790D / 0x7E63A4BB | frame (VD) driver FDRV, sync matrix (inferred) |
| cam_imgdev.c | 0x7E63BE39–0x7E63D0DD | image-device (sensor/front-end) driver. Commands at 0x7E63BAA6: COM_SET, ACTIVE, START, STOP, WAKEUP, SLEEP, CANCEL_REQUEST, RESET, MOVIE_START/STOP/PAUSE/RESTART, CLOCK_PAUSE/RESTART/CHANGE_PREPROCESS/HIGH/LOW/CHANGE_RESTART_WAIT, **LB_WAKEUP/SLEEP/PAUSE/STANDBY/RESET** (verified strings) |
| mirror (MI_*) | 0x7E642325–0x7E6437F1 | dummy mirror (inferred) |
| SPRDRV | 0x7E64B364 | dumps MOVIE_HS/HSSC/MSSC/LSSC/HSHR/STILL counts (0x7E64B299) |
| cam_sem.c | 0x7E64F085–0x7E64F2A2 | §2 (verified) |
| cam_set.c | 0x7E6521C9 | COM_SET list storage ("List Number", "list[%d] is used") |
| shutter (SH_*) | 0x7E6557CE | shutter resource (inferred) |
| cam_still_func.c | 0x7E656B1D–0x7E656F6F | §4 (verified tables) |
| cam_still_live_bulb.c | 0x7E65DA2B–0x7E6619C5 | §4 |
| cam_timer.c | 0x7E662535 TM_SEM, 0x7E66296B | timer object |

## 4. Still sequence and Live Bulb (cam_still_func.c, cam_still_live_bulb.c)

- **Still-func command filter (verified, 0x7E656D64):** it takes only cmd 7 (COM_SET) and cmd 80 (COM_MOVIE_EXPOSE). Anything else gives "STL_FUNC_COM NOT SUPPORT". **Live bulb (verified, 0x7E65DA2B)** takes only COM_SET.
- **Still phases (verified hash table 0x7E7BE488):** 1 READY, 2 TAKE, 3 STOP, 4 ABORT, 5 TERMINATE, 6 CONTINUE_READY, 7 CONTINUE_PAUSE, 8 CONTINUE_RESTART, 9/10 PRE_ACTION_ON/OFF, 11 MIRROR_DOWN, 12 CAPTURE_ENABLE, 13 FORCE_CAPTURE, 14 APERTURE_ENABLE. 0x101–0x10D are the same set with a BULB_ prefix (APERTURE_ENABLE has no bulb form). 0x10000 PHASE_NONE.
- **Still status (verified, 0x7E656C5E, linear 0–25):** STS_ERROR, IDLE, MGON, READY, TAKE, TAKE_CHARGE, TAKE_DEADLINE, TAKE_CHARGE_DEADLINE, then 13 MIRROR_DOWN_* variants (CHARGE / MGON / MECEN / DEADLINE / READY combinations), CONTINUE_READY(+CHARGE/DEADLINE). **Live-bulb status (verified, 0x7E65DA4A, 0–10):** BULB_STS_ERROR, IDLE, MGON, READY, TAKE, TAKE_ENABLE, TAKE_END, MIRR_DWN, MIRR_DWN_TAKE_END, MIRR_DWN_TAKE_END_MGON.
- **Status dumps (verified strings):** 0x7E656F6F (still) and 0x7E65DCAE (live bulb) print a table of phase request/post/remain/active. The rows are Ready, Take, Mirror Down, Continue Ready, Terminate, **FPN Origin/Light/Dark** × Ready/Take/MirrDown. **Inferred:** FPN = fixed-pattern-noise frames. The "Dark" take is the long-exposure noise-reduction dark frame, and the `cam still` option "bit1 : fpn" and "Recording FPN Dark" in the LB test agree.
- **Inferred, how Live Bulb/Time works:** the bulb exposure is driven as phases on the S_LB_M/S_LB_S objects. The image device has dedicated LB_WAKEUP/SLEEP/PAUSE/STANDBY/RESET commands. The sensor is woken periodically to read out an intermediate image for the display. The API side has `api_rec_Get_Bulb_Exp_Time` (0x7E68C415) and `api_rec_Get_Bulb_Lv_Count` (0x7E68C440, "Lv count" = number of live updates). I did not trace the update-interval logic.
- `cam still` test help (0x7E62F370, verified strings): Mode 7 = Zengaso. Depth 8/9/10/12/14/16 bit. Option1 bits: dark, pack up, pack down, antishock. Option2 bits: continue, fpn, bulb_manual, bulb_auto, abort_ready, abort_take. Matching sequences: "Still Normal" 0x7E62F6EB, "Still Continue" 0x7E62FC0C, "High (speed)" 0x7E630201, "Bulb" 0x7E6307C0, "LB" 0x7E630C25 (LB turns AWB off: "AWB OFF!!!!!").

## 5. cam_damage.c — internal error reporting (not sensor damage)

- **Verified.** `cam_damage(d0=code, a0=status, d1=line)` at 0x7E62EA55 (120 callers) and the `LINE=` variant at 0x7E62EAF3 (17 callers):
  - If suppression flag 0x6054C8DA is set, it returns at once.
  - The first report also logs "DMG* CODE=" through the debug monitor (0x7E633A1B) and calls 0x7E633D72.
  - Every report calls the system error recorder 0x7E426D4B (1,535 callers firmware-wide), with `(line<<16)|status`.
  - It counts reports in 0x6054C8D8. Above 10 it sets the suppression flag.
- Codes are 32-bit: `0x0A10xxxx` from cam.c (e.g. 0x0A101002 = unknown command) and `0x0A270002` from cam_sem. **Inferred:** "damage" is Olympus's term for a recorded internal fault.

## 6. Debug shell and debug monitor

- **`cam` shell (verified, table 0x7E7AC414, scanned by 0x7E62EB8E/0x7E62F0E3):** poweron, poweroff, still, movie, exp (`cam exp [Tv] [Sv] [Av] [PacketID]`, APEX-style hex), area, tg, test, dbglog, dbgcsv, dbginfo, mem, time_m, readyon, dbgmon, dblcap, dramcap, awb, expcal (`Expcal Still/Movie`: Tv sweeps for calibration).
- **cam_debug_monitor.c (verified):** a log of camera events. Record printers in table 0x7E8DCA38 ({enable, fn} × 13): CAM I/P/E 0x7E632EEB/0x7E632FD8/0x7E63307E, STL I/P/E 0x7E633162/0x7E633271/0x7E633372, BLB I/P/E 0x7E63347E/0x7E633593/0x7E633684, FRM INF 0x7E6337A5, IMG I/P 0x7E6338E1/0x7E6339B7, GENERAL 0x7E633A89. "CAM I" decodes word +8 as {cmd name low16, sensor-mode high16} and word +12 as a set-mask (MODE|EXP|CAP|AWB|STL). `cam dbgmon on/off [1=Top,2=Stl,3=LiveBulb,4=ImgDev,5=General]`, `lv [0,1]`, `sw [0=Local,1=Heap]`. **Inferred:** I = input command, P = post (completion), E = event factor.

## 7. Camera API layer (api_*.c) and api_exec / api_eventque

- **Verified groups (from `api_<grp>_<Fn>` name strings, counted per group):** adj 15, beep 2, calendar 5, comm 12, cube 31 (wireless/BT transfer), disp 31, dps 27 + dpst 8 (PictBridge), event 3, expconv 1, firmup 7 (strobe/lens updates, `F???????BIN`/`L???????BIN`), histogram 11, info 8, language 6, lcd 5, led 8, media 30, movie 31, oldb 31 (picture database), picfile 43, play 72, power 2, rcu 5, **rec 149** (0x7E6874C5–0x7E68C81C), rotate 2, sctime 8, sound 8, tft 40, user 12. The display entries in the region tags (Disp_LayerCustom, Set_Image_Areas, Draw_Image) are api_disp/api_tft. RecView_*, Clear_Skin_*, Record_Media are api_rec.
- **Mechanism (verified):** an async API calls `api_exec_reserve` (0x7E67E3C5), fills the packet, then `api_exec_start(d0=funcno, d1=event, a0=packet)` at 0x7E67E493. That routine fills a 40-byte slot at 0x605A0E5C+40·i and looks up `queue = tbl[funcno]` at **0x7E7C8B9C** (36 u32 entries) and a completion handler at **0x7E7C8C2C** (36 entries). If the queue is the caller's own (0x7E43ECC6), it calls 0x7E67E471 directly. Otherwise it sends with OlyQeWr (0x7E4492B9). Completions return through `api_exec_post` (0x7E67E5BB) and `appevent::Set_Event`/`Wait_Event` (0x7E67D2C7/0x7E67D064, queue "APPEQUE").
- **funcno map (verified: immediate `d0` before each of the 74 `api_exec_start` call sites; queue id from the table):**

| funcno | queue | APIs |
|---|---|---|
| 3 | 0x50 | tft_Draw_Image(_EditRaw/_Multi_Raw), play_Search_Face_Position |
| 6 | 0x6D | rec_Take_Ready, rec_Take_Ready_Ext |
| 11 | 0x6D | rec_Take_Picture |
| 12 | 0x58 | rec_RecView, RecView_MultiExp, RecView_Picture_Bracket, Clear_Skin_Recview |
| 13 | 0x58 | rec_Record_Media, Record_Picture_Bracket, Bayer_MultiExp, Clear_Skin_Ready/Execute |
| 14, 15, 17 | 0x22 | picfile_Output_PrintFile; media_Mount/Format; picfile Erase/Lock/Copy |
| 18 | 0x31 | rec_Control_Lens |
| 21 | 0x50 | play/picfile create/edit/play picture, movie_Load_Play_Movie, cube transfer |
| 25 | 0x71 | movie_Start/Stop_Record_Movie, rec_Start/End_Take_Control, AEAF_Lock, Calculate_Pixelmaping, tft Start/Pause/Restart/Update_Through |
| 30 | 0x58 | rec_Start/Save_Record_Sound |
| 31 | 0x50 | play_Play_Rom, Check_BGM_File |
| 33 / 34 / 35 | 0x03 / 0x09 / 0x9E | adj_Start_Adjust / rec_Control_Anti_Shake / disp_* and histogram_* |

  **Queue → task (verified where marked).** Queue ids are not task cfg ids (cfg 0x6D is PTPCOM). Flash holds a u16 id table where queue N sits at 0x7E43ECBC + 2N:
  - 0x58 is at 0x7E43ED6C, which **REC_MAIN** reads (§8). Verified, so funcno 12/13/30 go to REC_MAIN.
  - 0x71 (0x7E43ED9E) is received with OlyQeRd by **TAKE_FUNC** 0x7E595527 (verified).
  - 0x31 (0x7E43ED1E) by **LENS_MAIN** 0x7E51BF67 (verified).
  - 0x6D (0x7E43ED96) is read by **TAKE_MAIN** 0x7E58204D through 0x7E5A0CC5. Inferred to be its receive, so Take_Ready/Take_Picture go to TAKE_MAIN.
  - 0x05 (0x7E43ECC6) is the queue that `api_exec_start` treats as "local": a direct call, no message. Most unused funcnos point to it.
  - 0x50, 0x22, 0x9E, 0x03, 0x09 are not resolved.
- **Correction to a sub-report:** `0x7E67F822` (1,763 callers, called with 4013 in Record_Media) is a generic helper, not the dispatcher. The route is funcno 13 → queue 0x58.
- `Clear_Skin_*` (funcno 12/13) is **inferred** to be e-Portrait skin smoothing. `Bayer_MultiExp`/`RecView_MultiExp` are multiple exposure. `Get_I_Auto_Scene` (0x7E68A7FE) reads the SDET result (inferred).

## 7b. Exposure: EXP_MOVIE (live-view/movie AE) and SDET

- **EXP_MOVIE task (verified):** entry 0x7E68F0DD → loop 0x7E69AAD4, which receives with OlyQeRd (0x7E449218). Handler 0x7E68F0EA dispatches u16 at msg+12 in 0x500–0x1402 through hash table **0x7E7DA1C0** (key = code − 0x4FF). Codes: 0x500–0x507, 0x50A, 0x50B, 0x50D, 0x50E, 0x700–0x702, 0x801, 0x90A, 0x90B, 0x1402 → handlers 0x7E68F1FE, 0x7E69B03A, 0x7E68F296, 0x7E68F24B, 0x7E68F2C1, 0x7E68F310 (+0x7E6904C1). The names of the codes are not found.
- **What it does (inferred from about 470 `[exp]`/`[exp_debug]` strings, 0x7E68F535–0x7E69F833):**
  - It sends CAM_EXPOSE_SETTING (expose_mode, tv, sv, av), CAM_CAPTURE_MODE and CAM_AE_SETTING (area hs/hdiv/vs/vdiv, OB clip) to cam (0x7E68F9BA).
  - It computes BV from an 18×18 block grid (`*** [EXP] BV_18x18 ***` 0x7E69F0DF).
  - Metering values: `bv_spot, bv_esp, bv_ave, bv_ave2, bv_cntr, bv_arnd, bv_limit_low` (0x7E69C800/0x7E69D58E). These match ESP / centre-weighted / spot (inferred).
  - Face-weighted AE: `face_blk`, `face bv`, `table_calc face pix` (0x7E690B10, 0x7E6913FE).
  - Apical hooks: `[exp]:apical face_bv / af_target` (0x7E69CDA8); inferred to be shadow/DR control.
  - Accelerometer-based AE recalculation: `[exp] ** accel recal **` (0x7E68F6E2).
  - Flicker detection: `50_HZ_FLICKER/60_HZ_FLICKER/NO_FLICKER` 0x7E69D1A5, `exp flick det 50/60` 0x7E69F833.
  - Movie modes CAM_SENSOR_MODE_MOVIE_HS/HSSC… (0x7E69D6F5). 120 fps AF mode: `exp 120fps 1` (0x7E69F0C2).
- **`exp` debug shell (verified strings, 0x7E69C056 and helpers):** info, mode, bvall, logclr, flick, data, ae_setting, capture_mode, ae_y, expose_setting, aeprm, shift, ftbl, clip, farea. Plus `exp still on/off/info`, `exp_cal_still[mode/set/still/bv]`, `exp log start/stop/put`, `exp zoom [0:x4,1:x5…]`, `exp 120fps`.
- **Exposure modes P/A/S/M and metering selection** live in TAKE_EXPOSE (0x7E5829E8, `[TakeExp]…` strings, outside this range) and in the settings store. Not mapped here.
- **SDET (verified entry 0x7E662DCB; content inferred):** iAuto scene detection. Its dump at 0x7E663B54 has state, scene, tone_rev, aozora (blue sky), highsat, near, up_portrait, led, y_data_state, yc422_addr. The debug command at 0x7E6637F2 (`dbgscnmode`) lists the scene types PORTRAIT, SCENERY, SCENERY_PORTRAIT, NIGHT_SHOT, NIGHT_SHOT_PORTRAIT, NIGHT_SHOT_MACRO, EVENING_SUN, SPORTS, MACRO, SPOT_LIGHT, UNDERWATER_SNAP, PROGRAM, and also gyakkou (backlight). It dumps data files `ST/CO/IA%02d%02d%02dBIN`, `MDETDATA` (0x7E6672F3). 0x7E667400–0x7E675000 has about 200 functions without strings. **Inferred:** the detection algorithm library.
- **IMG_PRECON (verified, 0x7E55F9B6, outside range):** a message server with no strings. Command 0–4 goes to 0x7E55FAE8, 0x7E55FE1E, 0x7E55FF91, 0x7E55FFA3, 0x7E580A54(0/1). It replies with OlyQeWr if the message has a reply queue. The handlers read settings (0x7E457C75) and call into the TAKE region. The name suggests image pre-conditioning before capture (inferred).


## 8. Still recording pipeline (REC_*; rec_3d.c, rec_jpeg.c, rec_misc.c, rec_view.c)

**Framework (verified).**
- Each REC task loops on one queue, using OlyQeRd 0x7E7185C6 and OlyQeWr 0x7E7185D8.
- A job is a 228-byte message. Receive is 0x7E70B56B, forward to the next stage is 0x7E70B5BF, and reply is 0x7E70B53E. The reply is 12 bytes `{u16 status, …}` sent to the queue id at msg+12.
- Field names come from the REC_MAIN dump 0x7E70B614: `com, usMode, fnSetPercent, ulHandle[0..5], usMedia, usDst, usSrc, usWhole/Area*, usWideCnt, usCompDir, usMultiNum, usMultiGain[4], usNoRecord, usPicBkt[i], usDst2`.
- Status values 0x1F80–0x1FFF end a loop with "Abnormal Terminate". 0x1F01 means aborted and 0x1F02 means the cancel failed.

| Task | Entry | Queue (id var → id, verified) | Role |
|---|---|---|---|
| REC_MAIN | 0x7E70B435 | 0x7E43ED6C → 0x58 | Router. The `com` jump table is at 0x7E851DC4 (0..26) and the com→mode table at 0x7E851E30. |
| REC_PREPRO | 0x7E718878 | ED70 → 0x5A (still), ED6E → 0x59 (view) | `REC PREPRO make` 0x7E7189AF, multi-exposure Bayer 0x7E718EDA. com 19 → REC_VIEW, else → REC_IMAGE. |
| REC_IMAGE | 0x7E712955 | ED6A → 0x57 | precon (calls the IMG_PRECON code at 0x7E55FA55), bracket, apical, e-portrait, art, make image |
| REC_FILE | 0x7E712270 | ED68 → 0x56 | `REC FILE make` 0x7E712313: entry/open/write/close/leave 0x7E714203/0x7E71472B/0x7E7143C8/0x7E7144CF/0x7E7145EB |
| REC_VIEW | 0x7E71A315 | ED74 → 0x5C | rec-view images, under semaphore 0x7E43EABA |
| REC_SOUND | 0x7E71B612 | ED72 → 0x5B | usMode 0x4001 `REC WAVE START`, 0x4002 `REC WAVE SAVE` (voice memo, inferred) |
| REC_EXT | 0x7E711EB1 | EE24 → 0xB4 | usMode 0x3001: 640×480 Y image from Bayer (`REC MISC BAYER2Y` 0x7E715769). Purpose unknown. |

**REC_MAIN com (verified):**
- 16/17/18: still job to PREPRO / cancel one / cancel all. Record_Media usMode 0x1001, Record_Picture_Bracket 0x100D, AbortAll = 18.
- 19/20/21: view job / cancel one / cancel all (Abort_RecView = 21).
- 22/23/24: EXT.
- 25/26: SOUND / abort.
- 0: reply 0. Any other value: reply 0x1F10.

**One shot, in order (verified unless marked):**
1. The UI calls `api_rec_Take_Ready`/`Take_Picture` (funcno 6/11 → TAKE_MAIN). The exposure happens there and in cam.c (§1, §4).
2. The UI then calls `api_rec_Record_Media` (0x7E6882EC, funcno 13 → queue 0x58). REC_MAIN routes com 16 to REC_PREPRO.
3. REC_PREPRO sends the job to REC_IMAGE.
4. REC_IMAGE:
   - `REC PRECON` 0x7E7188D2 (for handle field +17132 ∈ {1,2,8}).
   - `REC_BRACKET_ENTRY` 0x7E70FFFD (prints "bkt start") and `bracket_update` 0x7E7100D7.
   - `REC IMAGE pre` 0x7E712BB8: REC_APICAL_EXEC 0x7E70D637, CSKIN_PRE 0x7E70ED0D, MULTIEXP 0x7E716E54/0x7E7171EC.
   - Then by usMode: 0x1009 e-portrait 0x7E70EE20/0x7E70F134; 0x1003 0x7E712DF2; 0x100F make + file. Default: art exec 0x7E70E687 (`art_SendRequest`), `rec_make_image_still_view` 0x7E712D8B, `REC_MAKE_IMAGE` 0x7E712D11.
   - It posts app event 0x040800F0 ("rec view ready", inferred) and forwards to REC_FILE.
5. **REC_MAKE_IMAGE** switches on the file type at msg+112:
   - 1 = **JPEG** `REC JPG EXEC` 0x7E712EBF: image 0x7E712F5D, header 0x7E7130F7, prim 0x7E713657, prim small 0x7E713CCE, thumbnail 0x7E719DAF.
   - 3 = **ORF/RAW** 0x7E71945A: buffer = setting 53140/idx 55 + 0x18AE000 bytes, then `REC ORF image` 0x7E7194A9 and `REC ORF header` 0x7E71969F.
   - **Inferred:** RAW+JPEG is take-handle +16386 == 5, giving two outputs (string `REC BRACKET UPDATE RAWJEPG-EXIF` 0x7E710209).
6. REC_FILE writes the file and replies.

**Bracketing (verified).** usMode 0x100D makes REC_BRACKET_ENTRY count the non-zero `usPicBkt[]` (msg+154). One exposure is rendered into several outputs. **Inferred:** this is ART BKT / picture-mode bracketing (`artbkt_cnt` in 0x7E5C69E6). AE/ISO/WB bracketing is in the TAKE/strobe modules (`bktNumMax`, `mode_bracket_iso`), not in REC. `api_rec_Get_Bracket_Information` (0x7E68BD97, 659 instructions) builds the list for the UI.

**3D (rec_3d.c 0x7E70BDF4–0x7E70D55E).**
- **Verified dispatch:** handle +17132 == 12 → 0x7E70BD7F: `rec_3d_lens_art_exec`, then `rec_3d_write_mpo` 0x7E70BF3C, then free. REC_VIEW has `rec_3d_lens_view` 0x7E70BDF4.
- **Inferred from names:** an MPO writer for 3D photo, and a 3D-lens path (two images on one sensor; `rec_cam_convert_3d_lens_offset_x/y`). `api_rec_Start_Take_3d` is at 0x7E68B98A.

**Other rec modules (names verified, roles inferred):**
- REC APICAL 0x7E70D637–0x7E70DA2F (shadow/DR adjustment)
- rec_art_* 0x7E70DC24–0x7E70EC2E
- REC_BEAUTY/CSKIN 0x7E70ED0D–0x7E70FFFD (e-Portrait)
- MULTIEXP 0x7E716E54–0x7E717EA9
- REC NR 0x7E717FE9–0x7E7183CC
- REC MISC YC2YC/YC2VIEW/YC2JPG/BAYER2YC/FD MAKE Y 0x7E714ABC–0x7E71631A
- `rec write/dbginfo/trace/dump` shell 0x7E710EB9

## 9. Art filters and effects (art_*.c, 0x7E71BC93–0x7E72CF39)

**Tasks (verified).**

| Task | Entry | Loop / work |
|---|---|---|
| ART (scheduler) | 0x7E729E25 | Task row at 0x7E438D68: {0x7E729E25, pri 11, stack 0x1CC0, cfg 0x808B}. It is just before the table that tasks.tsv starts from, so **tasks.tsv does not list it**. The loop is `art_get_msg` 0x7E729FB2 / `art_send_msg` 0x7E72A0B0. |
| ART_IMG_CM | 0x7E72985D | queue id at 0x7E43EE1E → 0xB1. `art_img_cm_exec` 0x7E7299E5 → IMG_PARAM/IMG_SAT_PARAM; `art_img_cm_dma_exec` 0x7E729A6F → IMGDMA_CTRL. Image-ASIC worker. |
| ART_IMG_CS | 0x7E729AF8 | queue 0x7E43EE20 → 0xB2. The same structure. `art_img_exec` 0x7E7223B9 picks CS when ctx+84 bit 28 is set, CM otherwise. |
| ART_IMG_CF | 0x7E729684 | `art_img_cf_exec` 0x7E7297FF → CPU kernel 0x7E5475FC (no strings). Only star-light pass 5 sends to it. |
| art_sub (2nd object table id 0x900C) | 0x7E72CC23 | ldata / gainmap / dio_gainmap / whiteedge_gainmap 0x7E72CDD5…0x7E72CF39 |

**Inferred:** CM/CS are the main and sub image-engine lanes. CF is a CPU function.

**Dispatch (verified).**
1. Callers: still `rec_art_set_artmode` 0x7E70E222 (+3D/view variants), and movie `mov_art_exec` 0x7E6CCFD2. Each calls `art_IsSupportType` 0x7E71BC93 and then `art_SendRequest` 0x7E71BD1B.
2. `art_set_filter` 0x7E72A346 builds a chain of at most 4 slots `{state, fn}`:
   - slot 0: `art_stl2ycc` 0x7E72BB61 (or `stl2ycc2` 0x7E72BBC6 for codes 74/104/96/165);
   - then the filter from `art_set_func_filter` 0x7E72A562 (hash table 0x7E85C45C, key = code−72);
   - then effects from `art_set_func_effect` 0x7E72A6B0.
3. `art_call_filterfunc` 0x7E72A997 runs the slots in order.
4. Each module runs its pass table through `art_com_pass_exec` 0x7E7285A4. Records are `{require_mask, done_bit, fn}`; a pass runs when its requirements are done.
5. The menu number goes to an internal code through `art_GetFilterType` 0x7E71BD94 (d0 = 100..120, d1 = variant; jump table 0x7E854A24). The name table is at 0x7E7FE240 (45 × 16 bytes, ends "NOT ART").

| Menu id | Internal code(s) (variant 1/2/3) | Module (top fn) | Name (inferred) |
|---|---|---|---|
| 100 | 70 / 102 | none (ISP params only) | Pop Art I/II |
| 101, 113 | 69 | none (soft-focus effect slot) | Soft Focus |
| 102 | 71 / 145 | none | Pale&Light Color I/II |
| 103 | 72 | none | Light Tone |
| 104 | 74 / 104 | art_filter_06_rough_monochrome 0x7E7229A3 (9 passes) | Grainy Film I/II |
| 105 | 73 / 106 / 108 | art_effect_20_pinhole 0x7E720332 | Pin Hole I/II/**III** |
| 106 | 86 | art_filter_09_diorama 0x7E72385C (9) | Diorama |
| 107 | 85 / 167 | none | Cross Process I/II |
| 108 | 91 | art_filter_0e_gentle_sepia 0x7E7244AE (3) | Gentle Sepia |
| 109 | 96 / 165 | art_filter_14_dramatic_tone 0x7E724786 (12, uses art_nr and ldata) | Dramatic Tone I/II |
| 110 | 145 | none | Tender Light |
| 111 / 112 / 114 / 116 | 75 / 84 / 117 / 119 | **none** | Fish Eye / Drawing / Rock / Watercolor |
| 115 | 118 | art_effect_10_star_light 0x7E71E705 (5 + CF) | Crystal |
| 117 | 151 | art_filter_1c_mirror 0x7E726F53 (2) | Mirror |
| 118 | 153 | art_filter_1d_composite 0x7E727103 (4) | Composite |
| 119 | 163 / 169 | art_filter_19_artclearline 0x7E7259A9 (13) | Key Line I/II ("Ligne Claire") |
| 120 | 181 / 182 | art_filter_21_pastelart 0x7E7275D4 (11) | Pastel I/II |

**Effects (verified, flag index at request +8+2i, chain order star → soft → frame → pinhole → white edge):**

| Flag | Module | Top fn |
|---|---|---|
| 0 | art_effect_10_star_light | 0x7E71E705 |
| 1 | art_effect_40_soft_focus | 0x7E72169C |
| 2 | art_effect_20_pinhole | 0x7E720332 |
| 3 | art_effect_30_frame | 0x7E720964 |
| 4 | art_effect_50_white_edge | 0x7E721EA9 |

- **Verified:** pinhole is dropped when the filter is already 73/106/108.
- **Verified:** the frame effect decodes JPEG frame resources (`art_frame_*` 0x7E721294…, `ART_FRAME_MOVIE_SD/HD/FHD`).

**Present in code but not in the E-PM2 menu (inferred; GUI not traced):**
- Full CPU modules exist for Crystal (118), Mirror (151), Composite (153), Pastel I/II (181/182) and Pin Hole III (108).
- Fish Eye, Drawing, Rock, Watercolor and a stand-alone Tender Light have menu ids and names only.
- `art_chk_type` 0x7E71C0E1 accepts 151/153 for only one mode.

**Debug shell (verified):** `art tsksts/filtlist/temp/debug/switch/frame/disp/dbgall/tout/off/dump` (help at 0x7E854BB4).

## 10. Face detection (FACE_MAIN, FACE_FD, FACE_PT0, DISP_FRAME)

**Objects (verified, created in 0x7E6FC27E):**
- Queues FACE_EXEC (id var 0x7E43ECF2 → 0x1B), FACE_FD (0x7E43ECF4 → 0x1C), FACE_POST and FACE_PT1.
- Semaphore FACE_DATA.
- Event flags FACE_FD, FACE_MOV and FACE_PT (0x7E43EC46).
- The wrappers are named `Face<QR|QW|SE|WE|CE|SS|WS><obj>`, at 0x7E6FC46C–0x7E6FC91A.

| Task | Entry | Loop (verified) | Role |
|---|---|---|---|
| FACE_MAIN | 0x7E6F45B8 | FaceQRMa. State byte 0x605B2A40. In state 0: cmd 1 start (→ FD cmd 0), cmd 4 set image (address + geometry at 0x605B2A28–3C → FD cmd 1), cmd 5 → 0x7E6FBF38, cmd 11 → 0x7E6F4739. In state 1: cmd 2 stop. Error 0x8708. | control |
| FACE_FD | 0x7E6F82C8 | FaceQRFd. cmd 0 → live FD 0x7E6F9DB9; cmd 1 → still-image FD 0x7E6FA248. | detector |
| FACE_PT0 | 0x7E6FC973 | waits for the FACE_PT event, then 0x7E6FC999 / 0x7E6FC9F4 | facial parts (eyes) |
| DISP_FRAME | 0x7E6B3989 | Reads settings 12417/34145/55153. Waits on flag 0x7E43EC24. State 0/1/2 (0x605AFA7C) → 0x7E6B3B66/0x7E6B3BAF/0x7E6B3C11. | AF/face frame overlay |

**Live loop (verified call order in 0x7E6F9DB9):**
1. Re-post the job to its own FD queue (it repeats each pass).
2. Wait for FD done (FaceWEFd).
3. Take FACE_DATA, store results, release it.
4. Set the PT event, which wakes FACE_PT0.
5. 0x7E6B3ACE sets bit 16 on DISP_FRAME's flag when DISP_FRAME is in state 1.
6. 0x7E6C35A7 calls into the movie code.

**Senders (verified):**
- TAKE_FUNC (0x7E5963F9, 0x7E596AB7, 0x7E595AD0) sends start/stop through 0x7E598DED.
- REC CSKIN pre 0x7E70ED0D and `REC FACE get data` 0x7E712137 send cmd 4 (still-image FD for e-Portrait).
- Playback `play_face_detect_face` 0x7E942E34 and red-eye 0x7E94318E also send.

**Consumers (verified):**
- TAKE/AF read face results through 0x7E6FB603.
- The UI reads through `api_rec_Get_Rec_Face_Number`/`Get_Rec_Face_Rect_Area` (0x7E68A726/0x7E68A4E4 → 0x7E5A13A1).
- EXP_MOVIE does face-weighted AE (§7b).

**Inferred:**
- FD is a hardware engine fed by DMA (control block `ulInAddr, ucDmaMode, ucDtMinSize, ucDtDir, ucThreshold` dumped at 0x7E6F97D3).
- PT uses Omron OKAO (`OKAO_DeletePtResult`, `OKAO_FreeWMemoryArea` near 0x7E6FBCB0).
- Per-face results are `center_x/y, size, angle, confidence, pose`. PT adds eye positions; "EYE AF ON/OFF" is at 0x7E6F9A26, so PT supports eye-priority AF.
- `api_rec_dummy_Get_Smile_Face_Detect` exists only as a string, so smile detection is stubbed out.

## Open questions

1. CAM_MAIN is a `retf` stub. Is it ever started (sta_tsk)? Does any code use its 0x40-byte stack?
2. What do the cam.c COM_GET/READY_ON/SETUP/SETDOWN handlers do in detail? What is the full COM_SET item list (RAM table 0x602A2758 maps item → handler class)?
3. What are the EXP_MOVIE message codes 0x500–0x1402 called, and who sends them? Where are P/A/S/M and the metering-mode selection (TAKE_EXPOSE)?
4. Is MMIO 0x9A1000F4–0x100 really a software-interrupt trigger? Which interrupt vector runs the four deferred-call rings?
5. Which tasks own API queues 0x50, 0x22, 0x9E, 0x03, 0x09? What does the second completion table (0x7E7C8C2C) do per funcno?
6. Live Bulb/Live Time: where is the update interval and display-refresh logic (0x7E65E000–0x7E661900, no strings)? Is Live Bulb reachable from the E-PM2 menus? This was not checked against the GUI.
7. REC: what are take-handle fields +17132 (1/2/8/12) and +16386 (5 = RAW+JPEG?), and usModes 0x1002/3/4/7/8? What is REC_EXT's 640×480 Y image for?
8. Art: what do the CPU kernels 0x7E5475FC/0x7E547A7A compute? What is request type 3 (two filters: ART BKT?)? Which menu ids 100–120 does the E-PM2 GUI expose (Pin Hole III, Crystal, Pastel, Mirror, Composite)?
9. Face: what are FACE_MAIN cmds 5/11, FACE_POST/FACE_PT1 and DISP_FRAME states 0/1/2? Who sets the FD-done event (ISR?)?
10. SDET: the algorithm block 0x7E667400–0x7E675000 (about 200 functions without strings), and how the SDET result reaches `api_rec_Get_I_Auto_Scene`.

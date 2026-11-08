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

<!-- REC / ART / FACE sections appended below -->

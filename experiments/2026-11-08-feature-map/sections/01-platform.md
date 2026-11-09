# 01 — Platform: OS, boot, drivers, debug facilities, BASIC, factory adjustment

Scope: 0x7E421020–~~0x7E521020~~ 0x7E521132 (the 1-MB window edge 0x7E521020 falls inside the lens function 0x7E520E2D, which takes the lens event codes such as 0x02001516 and ends with `ret` at 0x7E521130) (L1 2026-11-09), plus BASIC (0x7F05C000–0x7F06B000) and ADJ/ADJSLF (0x7F080000–0x7F087xxx, ~~0x7F0A7Cxx–0x7F0AB000~~ 0x7F0A7CA5–0x7F0D257C, §7 (L1 2026-11-09)).
Labels: **[V]** = verified (I read the code or bytes and they show this). **[I]** = inferred (from strings, names or layout only).
Helper scripts: `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/platform/` (`seq.py`, `cmdtbl.py`, `rstr.py`, `rword.py`, `deep.py`).

## Overview

- Two CPUs run uITRON. A task ID holds the CPU number in bits 12–14 and the index in bits 0–11. Bit 15 marks the tasks that have a static stack. **[V]** (kernel `0x7E4306A6` decodes `id & 0x7000 >> 12` and `id & 0xFFF`, then indexes the per-CPU control blocks at `0x8FF00004 + cpu*4`; the current CPU number is at `(0x8050)`.)
- **Checked against the µITRON 4.0 specification (ERTL, Ver. 4.00.00; `out/specs/mitron-400e.pdf`, text via `scripts/pdf_text.py`) (2026-11-09):**
  - **Task records:** each 28-byte record is {id, then exactly the spec's `T_CTSK` = {tskatr, exinf, task, itskpri, stksz, stk}}, i.e. a static `CRE_TSK(tskid, {…})` configuration table. **[V]** (spec §4.1 packet layout vs. the records at 0x17CB0/0x1C490)
  - **Error codes:** the kernel 0x7E430000–0x7E44B000 returns the spec's codes: E_CTX −25 (83 sites), E_ID −18 (66), E_NOEXS −42 (54), E_PAR −17 (33), E_OBJ −41 (18), E_TMOUT −50 (16), E_NOMEM −33 (12), E_NOID −34 (10), E_DLT −51 (9), E_RSATR −11 (8), E_QOVR −43 (7), E_ILUSE −28 (6), E_SYS −5 (3), E_RLWAI −49 (1), E_NOSPT −9 (1). **[V]** (counts of `mov <code>,dN` in build/map)
  - That the kernel is a µITRON 4.0 implementation (not 3.0) is now **[V]** from both the packet layout and the error-code set. The vendor of the kernel is still unknown.
- Boot runs as a chain. CPU0 task ID 1 is the only CPU0 task with attribute TA_ACT. It loads more code from flash, then runs `Usr0`. `Usr0` starts about 60 tasks in a fixed order. The USRSTART_* tasks start the rest. Some code overlays (BASIC, ADJ/PTP/USB) load from flash only when they are needed. **[V]**
- There are two debug shells. S_SHELL is a system monitor (prompt `:-) `) on a memory-mapped serial port. U_SHELL (prompt `USR> `) has 54 command families in a {name, handler} table. A bare `:` line in S_SHELL toggles pass-through: while it is on, lines that do not start with `:` go to U_SHELL, and a `:cmd` line still runs in S_SHELL (audit 2026-11-09). The same U_SHELL dispatcher is also reachable over USB through the factory-adjustment PTP operation 0x902B. **[V]**
- BASIC ("QBASIC") is a small line-number interpreter. It takes input from the `bas` shell command. Its `api(code,a,b)` function calls the application API executor. Scripts (".RCU", "RelocateCode") can be loaded from the card, rewritten (symbolic `API_IF_*`/`APPEVENT_*` names become hex codes) and stored in flash. They reload into the interpreter at boot. **[V]** for the code path, **[I]** for the purpose.
- ADJ is a PTP (ISO 15740) responder for factory adjustment, with standard opcodes and vendor opcodes 0x9005–0x902B. ADJSLF is an in-camera "self adjust" client of the same operations, driven by files on the card. **[V]** for the tables, **[I]** for the purpose.

## 1. Task tables and IDs

**CPU0 static task table**, block offset 0x17CB0 (runtime 0x7E438CD0). 147 records of 7 words: `{id, attr, exinf, entry, pri, stksz, stk}`. **[V]**

- The rows start with IDs 0x8085–0x808D (bit 15 set, explicit stacks at 0x604DEB80…0x604E2840). Then come IDs 1…0x84 and 0x8E…0x93. A zero record follows at 0x18CC4.
- ID 1 (`entry 0x7E44A043`, pri 1) is the only row with attr = 2 (TA_ACT: auto-start). It is the boot task. **[V]**
- *Coordinator note: resolved. `tasks.tsv` and `fwmap.py tasks` now use this layout (commit a165ec5).* This disagreed with the earlier `tasks.tsv`. That file puts `cfg_id` *after* the entry, so its numbers are one row off from the real IDs. Evidence for the layout above (all **[V]**):
  - The boot code calls `OlyTaSt(60)` with check label "S_SHELL". ID 60 is entry 0x7E44E972, which prints `S_SHELL`/`:-) `. In tasks.tsv, ID 60 would be SC_TTIMER.
  - `OlyTaSt(0x84)` has the label "MOV_EDIT". ID 0x84 is entry 0x7E6D4597, which prints `[MOV_EDIT]`. ~~tasks.tsv calls this entry IMG0_LOCAL.~~ The current tasks.tsv has 0x0084 MOV_EDIT for it, and 04 now uses this layout (coverage C4) (L1 2026-11-09).
  - `OlyTaSt(0x8F)` has the label "CPUCONN0", and entry 0x7E505A22 is CPUCONN on both CPUs.
  - TA_ACT is on 0x7E44A043. That entry runs all of the boot code.
- The entry names in tasks.tsv agree with mine for IDs 1…0x84. The name table (0x4D222) agrees with `names[ID-1]`. The exceptions:
  - ID 0x8085, entry 0x7E5065EF. The name table gives PWR_STANDBY. The boot code labels it **"DBG_OUT"**. Its code writes characters to the debug serial port (`call 0x7E44B051`, see §3) and prints `!!!!!!!!!! 2`, the counterpart of DBG_MESS1 (CPU1 0x9004, `!!!!!!!!!! 1`). **I name it DBG_OUT [V for the code, the table name looks wrong].**
  - ID 0x808D, entry 0x7E575D41 (the "task-1 entry" in the brief) → `names[140]` = **IMG0_LOCAL**. Next to it is `0x7E575C72` with `img_l0` and `IMG_SYSTEM_ERR!!!`. **[V for the table, I for the purpose]**
  - ID 0x8E, entry 0x7E53A4A4 → `names[141]` = BOOT_CPU0. Its code prints `[pwr_standby]`, and its stack is in SRAM (0x47000800). It is probably the standby/resume task. **[I]**
  - ID 1, entry 0x7E44A043 → `names[0]` = "DBG_OUT" in the table. Its code is the boot task. **[V for the code]**
- `ID→var` table at 0x7E43E948 (u16 per object name). The boot code reads task IDs from here: entries 0–24 are 0x8085–0x808D, 0x8058, 0x80AE, 0x8001, 0x8007, 0x80C0–0x80C3, 0x80D9–0x80E0 (not one run) (audit 2026-11-09), and entry 25+ holds 1, 2, 3…. **[V]**

**Second object table, CPU1** (the "0x1C448 table"). At 0x1C408–0x1C487 there is an array of pointers 0xA0767420 + k·0x28. **[I]** These may be control blocks. 7-word task records follow from **0x1C490** (first id 0x9004) (audit 2026-11-09), in the same layout. The IDs have bit 12 set, so they are CPU1 tasks. **[V]**

| ID | entry | pri | stack | name (from the boot check label) |
|---|---|---|---|---|
| 0x9004 | 7E506659 | 12 | 0x604E3440 | DBG_MESS1 (CPU1 debug out) |
| 0x9005 | 7E6FCA3C | 11 | …3C40 | TSK_FACE_PT1 |
| 0x9006 | 7E54875A | 4 | …4740 | IMG_ART_P |
| 0x9007 | 7E6D4E01 | 5 | …4B40 | MOV_AVCHD |
| 0x9008 | 7E6D568F | 5 | …5340 | MOV_AVCHDI |
| 0x9009 / 0x900A | 7E94D72F / 7E94DC4C | 9 / 2 | | audio bridges **[I]** (0x900A has the same entry as CPU0 0x8089) |
| 0x900B | 7E72CC23 | 4 | | ART_SUB |
| 0x900C | 7E6D554A | 5 | | MOV_ENCODE |
| 0x900D / 0x900E | 7F09D0B0 / 7F09D24D | 11 | | C3D_BRG_C0L_C1P / C3D_BRG_C1P_C0L |
| 0x900F | 7E575DB8 | 4 | | CPU1 twin of IMG0_LOCAL **[I]** |
| 0x1001 | 7E42691F | 1 | dyn | **CPU1 boot task** (attr TA_ACT) **[V]** |
| 0x1002 | 7F09DFD4 | 11 | | C3D_EXE |
| 0x1003 | 7E5079DD | 16 | | SCHEAPDBG |
| 0x1010 | 7E505A22 | 11 | | CPUCONN1 (same code as CPUCONN0) |
| 0x1011–0x101B | 7EE8FBB1 ×11 | 5 | | **AVPI threads**: 0x7EE8FBB1 is the AVPI thread trampoline (`rec->fn(rec->arg)`, records created by 0x7EE8FBC9), exinf 0…10 **[V]** (13b §2.4) (D1 2026-11-09) |
| 0x101C–0x101E | 7EEC202E, 7EE8FF18, 7EECC670 | 5 | | 0x101C = **AvScaTask**; 0x101D and 0x101E = AVPI service tasks (0x101E inferred: codec-driver task) **[V entries]** (13b §2.4) (D1 2026-11-09) |

How a task on the other CPU starts: `OlyTaSt` (0x7E449541) checks `id & 0x1000`. If the bit is set, it calls `0x7E44ED7D(0x10001, id)` instead of calling the kernel. That is a request to the other CPU. **[V]** I infer that CPUCONN carries this request out; its strings list proxied services (`tsnd_mbf`, `twai_flg`, `sig_sem` … at 0x7E5060E8). **[I]**

## 2. Boot and startup sequence

**Boot task, CPU0 ID 1, entry 0x7E44A043.** **[V]**
1. Boot trace marks go through `0x7E426511(tag)`. This logs up to 200 (tag, time) pairs, which the `initbuff` command shows. Tags: `OIS/OIE`, `F1S/F1E`, `HIS/HIE`, `RCS/RCE`, `DIS/DIE`, `QIS/QIE`, `SCS/SCE`, `0_1…`, `Pr0…`.
2. `0x7E4217E6(vol 0, src 0x4039D000, dst 0xBE4FE000, size 0x383000)` is a low-level flash read (strings `READ nVol size scts`). It loads runtime **0x7E4FE000–0x7E881000**: USRSTART, UI and the core above. **[V]** That this is the flash→RAM copy is **[I]** (0xBExxxxxx is read as the uncached alias of 0x7Exxxxxx).
3. Prints `K.R.` and a version string. Calls initializers `0x7E44D6EF`, `0x7E44EE0E`, `0x7E45D120`, `0x7E507284`, `0x7E53A981`.
4. Copies 2 KiB from 0x7F14B000 (0xBF14B000) to **SRAM 0x47001000**. The watchdog kick at `0x47001560` lives there (see §6).
5. `0x7E44EE9A` checks the NMI flash-guard requests 12/13/14 (`= FLASH_ACCESS_GARD`), creates objects, then calls **Usr0 = 0x7E503DD4** and exits.

**Order in which tasks start.** `OlyTaSt(id)` is followed by `chk(ret,"LABEL")`. The table lists the labels in order. **[V]**

| Stage (function, task) | Tasks started, in order |
|---|---|
| **Usr0** 0x7E503DD4 (in the boot task) | DBG_OUT(0x8085), S_SHELL, U_SHELL, CPUCONN0, CPUCONN1(0x1010), SYSFMEM, FIRMUP_SRV, PER_IN, PER_WDT, PER_PCONT, BCHK_MAIN, UI_IN, TSK_HDMI, LENS_MAIN, ZOOM_MAIN, UI_OUT, UI_SCREEN, BC_MAIN, SDET, SC_TTIMER, TAKE_FUNC, TAKE_EXPOSE, TAKE_FOCUS, FUNC_CP, FCS_MOVIE, DISPLAY, STROBE_ASSIST_FUNC, STB_CHARGE, STB_EXTERNAL, STB_SEQ, **USR_FAST**, (chg_pri self→11 "USR_PCHG"), SCHEAPDBG(0x1003), EXP_MOVIE, FILECLBK, ART_MAI(0x808A), ART_ICM, ART_ICS, ART_SUB(0x900B), ART_ICF, IMG_ART_P(0x9006), GATEWAY(0x8086), MOV_ART, MOV_SUB, MOV_COL_SUB, MOV_COLOR, MOV_TASK, TSK_FACE_FD, TSK_FACE_MAIN, WB_MOV, REC_PRE, REC_IMA, REC_FIL, REC_VIE, REC_SOU, REC_EXT, REC_MAI, then FIRMUP_CLI (only on the firmup path), then **USTART1** (ID 0x52 = USRSTART_FIRST) |
| **Usr1** 0x7E504AF9 = USRSTART_FIRST | Loads overlays (below). Starts LENS_FLASH, DBG_MESS1(0x9004), AUD_EXE, PLAY_MAIN, PLAY_LOAD, PLAY_IMAGE, PLAY_SOUND, TSK_TOUCH, IMG_PRECON, TSK_FACE_PT0, TSK_FACE_PT1(0x9005), TSK_DISP_FRAME, SERV_MAIN, EFFECT_EXE, EFFECT. Calls `SetPermit(3)` and sets USR_FAST flag 0x08. |
| **Usr2** 0x7E505005, called with a bit mask through 0x7E68CD13 from app code (e.g. `api_adj_Check_Execute_Self_Adjust` 0x7E675F05) | bit 0 → load overlay A, start USTART3; bit 1 → load overlay B, start USTART4; bit 24 → init and start ADJSLF. Each bit runs only once (flags at 0x602A9B48). **D3 (15d §4.4, V):** the three tests are independent (`btst 1,d3`, `btst 2,d3`, `and 16777216`), so a mask of 2 alone loads B and starts DPS_MAIN without A. The callers seen pass 0xFFFFFF (A + B, not bit 24): `api_adj_Check_Execute_Self_Adjust` 0x7E675F05, the firmware-update path 0x7E67EC80 and slot 0 0x7EBA139E of vtable 0x7EC90B30; slots 1–3 (0x7EBA13BE/0x7EBA13DA/0x7EBA13F6) pass 1, 2 and 0x1000000 alone, and their callers are not traced. **PictBridge needs both overlays:** DPS_MAIN 0x7F087807 is in B, the DPS engine 0x7F05E9CE–0x7F0645C0 is in A, and all 297 A → B call edges come from DPS code (08 §1.1) (D3 2026-11-09). |
| **Usr3** 0x7E50518C = USRSTART_THIRD | MOV_BRIDGE(0x8087), MOV_AVCHD(0x9007), MOV_AVCHDI(0x9008), MOVREC_FILE, MOV_ENCODE(0x900C), MOV_REC, MOV_EDIT(0x84), MOV_P_IMG, MOV_PLAY, MOV_SPLY, MOV_DISP, **BAS_MAIN, BAS_RCV**, C3D, C3D_UPDATE, C3D_EXE_BRIDGE, C3D_BRG_*(0x808B/0x808C/0x900D/0x900E), C3D_EXE(0x1002) |
| **Usr4** 0x7E5054F2 = USRSTART_FOURTH | SAICAS, DPS_MAIN, TSK_PTPCOM, TSK_PTPACY, TSK_LANG, TSK_TPC, PC_UAM, LENS_FIRM_UP, LENS_ASKDATA, **TSK_ADJ** |
| USRSTART_FIFTH 0x7E505680, PROCLOG 0x7E506BEC | empty tasks (`retf` only) **[V]** |

**Code loads through SYSFMEM.** `0x7E451306(size, mode, dst, src)` posts a read request to SYSFMEM and waits for it. **[V]**

| Caller | flash src | RAM dst (runtime) | size |
|---|---|---|---|
| Usr1 | 0x80794800 | 0x7E8F5800–0x7ECB1000 | 0x3BB800 (SYSFMEM priority raised to 12 during the read) |
| Usr1 | 0x80B6A800 | 0x7ECCB800–0x7F034000 | 0x368800 |
| Usr1 | 0x80F9F000 | 0x7F100000–0x7F119000 | 0x19000 |
| Usr1 | 0x4005FC00 | data 0x604F2ED8 | 0x400 |
| Usr2 bit 0 (overlay A) | 0x80EFB000 | 0x7F05C000–0x7F06B000 (BASIC, DPS) | 0xF000 |
| Usr2 bit 1 (overlay B) | 0x80F1F000 | 0x7F080000–0x7F0EB800 (ADJ, TPC/PTP, USB, C3D, SPC) | 0x6B800 |

So BAS_MAIN and ADJ code is not in RAM until the app asks for Usr2. **[V]** The trigger conditions are app code (other sections).

**USR_FAST_APP** (ID 0x70, entry 0x7E502140, pri 6). An event-flag loop (flag ID var 0x7E43EC76). Each bit clears itself and runs one step. **[V]**

| bit | log string | handler |
|---|---|---|
| 0x01 | Flg-LensSetupStart | 0x7E50241E |
| 0x02 | Flg-ThroughStart | 0x7E50243C |
| 0x04 | Flg-2ndStart | 0x7E502464 |
| 0x08 | Flg-2ndChk | 0x7E502467 |
| 0x10 | Flg-2ndEnd | 0x7E5024C2 |
| 0x20 | Flg-TakeFunc | 0x7E5024CD |
| 0x80 | Flg-RhpTake | 0x7E502532 |
| 0x40 | Flg-EcecEnd | 0x7E5025B8 |

- `Usr0` first calls `0x7E5436D1`. That function reads the firmup reboot flag (3 = `REBOOT SYSTEM UPDATE`, 4 = `USER UPDATE`). If the result is 1, Usr0 sets bit 0x40 (end the fast path). Otherwise it sets 0x01 (lens setup). **[V]**
- Strings such as `ErrLeBat`, `ErrThrAdj`, `ErrRelNoSD`, `TakePicStart!!`, `StrobeChg!!` and `FastEndCb` suggest this is a quick power-on-to-live-view-to-shoot path that runs before the full UI app. **[I]**
- The log goes through `0x7E503A6E`. The `usr fast log` command (audit 2026-11-09) (0x7E502111/0x7E5023E1) prints it ("UsrFastAppDebug!"). **[V]**

## 3. Debug shells

**Console hardware.** `0x7E44B040` and `0x7E44B0DA` are getc/kbhit, and `0x7E44B051` is putc. They use pointer tables at 0x7E46DEC8 indexed by CPU. **[V]** I infer that this is a UART. **[I]** **Corrected:** the index is a port number (byte 0x8FF00080), not the CPU (10f §1.2). The two ports are SIO logical ch5 (0x9870xxxx) and ch1 (0x9830xxxx), and ch1 is also the EVF and PENPAL/Bluetooth UART **[V]** (13f §2.3) (D1 2026-11-09).
- Port 0 ("CPU0") registers: 0x98700008 RX data, 0x9870000C RX status, 0x98700018 TX data, 0x9870001C TX status.
- Port 1 ("CPU1") registers: 0x98300008 / 0C / 18 / 1C.
- putc also copies output into a 767-byte ring at 0xA0731…. **[V]**
- Debug prints (`0x7E4263E5`, 2,623 callers) go through `OlyQeWr`. **[I]** that the DBG_OUT task drains them to the port.

**S_SHELL** (ID 60, entry 0x7E44E972, pri 12). **[V]**
- Reads a line from the console.
- A line that is only `:` switches mode. In "user" mode, lines go to message buffer **NIKOLQ** (ID var 0x7E43EE3C) for U_SHELL. A line that starts with `:` still runs locally.
- Local lines go to `0x7E44E82F`. That function parses up to 4 arguments and calls `0x7E44DBF5`, a chain of strcmp calls.
- System commands (from the help text and the strcmp strings):
  - `ps`
  - `mdump`/`mdump4`/`mdump2`
  - `mem_get[4|2|1]`, `mem_put[4|2|1]`
  - `od tsk|stk|sem|flg|dtq|mbx|mtx|cnd|mbf|mpf|mpl|cyc|alm [id|all]`, plus `*1` variants for CPU1
  - `oserr`, `cpulog`
  - `OlyTaskDelete/Start/Stop/Wakeup`, `OlyEventDelete/Set/Clear`, `OlySemaphoreDelete/Wait/Signal`
  - `initbuff`, `heaplist`, `usrSample` (sends a message to the USRTEST queue)
  - `dqsdelay`, `busmes` (SDRAM bus measure: set/clr/start/stop/result/setinfo/agentinfo/ses/through/slide), `arbit` (cfg, llfinfo)
  - `help`

**U_SHELL** (ID 77, entry 0x7E503CD0, prompt `USR> `). **[V]**
- Reads lines from NIKOLQ (`0x7E503C6C` → `0x7E44EA5C`).
- `0x7E503B0B` parses the line. `0x7E503C7E` compares argv[0] against **54 entries at 0x7E7332B4** and calls `handler(argc, argv)`.
- An identical copy at 0x7E7326A4 is used by `dbgall` (0x7E501F0D), which runs a list of commands. **[I]** for the source of that list.

| cmd | handler | cmd | handler | cmd | handler |
|---|---|---|---|---|---|
| shell | 7E962FE9 | echo | 7E503BC6 | help | 7E503BFF |
| lens | 7E524C76 (reset/aperture/focus/askdata/confdata/ctrl…) | aud | 7E94F735 (stub) | cam | 7E62EB8E |
| bas | 7F05DC8B (→ QBASIC) | pwr | 7E539672 (vbat, pbhtmp, get_src/set_src 1=AC 2=BAT) | bc | 7E53BE63 (siotx/siorx/setprm/getprm/debug_mode/mask) |
| take | 7E582602 (func/dbginfo/dbgmode/exec) | stbd | 7E5DB015 (strobe: init/coff/cpau/cres/cloop/cset) | **per** | 7E45F09B (table below) |
| res | 7E675B1E (RES_MODE_* read) | app | 7E67811B (`app Get_CameraInfo` etc.) | usb | 7F09ABD1 (core, pipe0–4) |
| **prm** | 7E456928 (below) | **flash** | 7E44F509 (below) | rec | 7E710EB9 (write/dbginfo/trace/dump) |
| file | 7E5C2139 (prologue entry of the FileSystem shell 0x7E5C213E: `movm` then falls through; two-entry rule) (L1 2026-11-09) | sc | 7E506D76 (heapshow, heaplist …, timing show/start/stop/clear) | exp | 7E69B75D (info/movie/still/call/time/120fps) |
| dbg | 7E53A9C8 (start/stop/flush/show) | **ui** | 7E508F82 (below) | mec | 7E510A60 (still, shutter set/on, lsnc…, set flagNo, prmout, test) |
| fcs | 7E5E9A37 | cp | 7E508F11 | dbgall | 7E501F0D |
| sdet | 7E6637F2 | mov | 7E6D15A0 ("mov debug commands") | movp | 7E6E3D18 |
| osd | 7ECCBA39 | mdet | 7E666EB9 | face | 7E6F4D77 |
| img | 7E54D4D9 | play | 7E93EBB5 | movc | 7E6D09DE |
| bt | 7E9035A8 (demo, srv_stt, opp_srv…) | obex | 7E93B9BF | acp | 7E9393BE |
| md3d_dmp | 7F05E951 | md3d_hi | 7F05E8D4 | disp | 7E6B1402 |
| tpc | 7F08910E (info/ctrl/util) | sdk | 7E9672F6 | efct | 7E8F5E9E |
| buff | 7E5776A2 (print/alloc/free) | api | 7E67816E | c3d | 7F09D8DB |
| sync | 7E6C1579 | usr | 7E502111 (fast) | art | 7E71C9D4 |
| damage | 7E53A700 (get) | spc | 7F0A6E59 (FlashAir; dbg_lv) | mcon | 7E6FE1FE (`mcon Get_CameraInfo`) |

Handlers in overlays (`bas`, `usb`, `tpc`, `c3d`, `md3d_*`, `spc`) are only valid after Usr2 has loaded them. **[I]**

**`per` sub-table**, 26 entries at 0x7E4C5534. **[V]**
- Entries: adc, backup (poweron factor, PKEY0–4), gio, pwm, clk, help, pcnt, adconv, timer, dbgsup (DBGS on/off, NMI address watch), usf, rotate, hproc, rtc (settime/gettime/setalrm…), ioe, ioec, acc, acc_adj, slp, water, ccdtemp, wdt (off/on/time N/rbt1/rbt2), dbgport, sio, cpudma.
- An empty string maps to help.

**`ui` sub-table** at 0x7E734DEC: led, beep, key (skey/okey/pwr_fact/pkeyc/gmat/gtbl/gjogtbl/debug), jog (start/stop/mode/count/debug), remo, help. **[V]**

**`prm`** (settings store): getval/getstr `<TagID>`, setval/setstr, getval_def/getstr_def/set_def, getdevice, `clear <1:CSV,2:CPRAM,3:BKRAM,4:FLASH,6:EEROM,7:MODE>`, dump, `psave/pload <bit0 bkram,1 flash,2 eerom,3 mode,4 cflash>`, chkload, erase, `fmem <mode> <adrs> <KB>`. **[V]**

**Remote use over USB.** ADJ PTP op 0x902B, sub-op 15 (`0x7F08433A`), takes a command string of up to 127 characters. It calls the same U_SHELL parser/dispatcher `0x7E503CB7`. If the "system" flag bit 1 (mask 0x02, `btst 2` (audit 2026-11-09)) is set it replies `not support nikomon`, so S_SHELL is not reachable this way. **[V]**

## 4. BASIC interpreter (BAS_MAIN, BAS_RCU_SRV)

- **BAS_MAIN** (ID 6, entry 0x7F05C000, in overlay A). **[V]**
  - Reads 256-byte lines from queue **QBASIC** (`0x7F05DB9C`).
  - A line that starts with a number is stored in the program text (`0x7F05C2F7`, "Text is locked").
  - A line without a number runs immediately (`0x7F05C89B`).
  - The `bas …` shell command joins its arguments, adds CR, and writes the line to QBASIC (ID var 0x7E43EDD4).
- **Statements** (table 0x7F069338, `{name, code, handler}`): bye, run, list, new, end, if, rem, `'`, goto, gosub, return, while, do, print/`?`, for/next, spc, hex, chr, crlf, input. Keyword `to`. **[V]**
- **Functions**, dispatched in `term()` 0x7F05D73C: **[V]**
  - `abs(` — inline
  - `rand(` → 0x7F05DB22 (timer seed)
  - `getkey(` → 0x7F05DBF3 (reads QBASIC)
  - **`api(` → 0x7F05CCE9** → `0x7E67F3E6(code, args[8])`, the app API executor in the api_exec area
  - `sctm(` → 0x7F05CD55 (builds a 6-byte record at 0xA06DD000)
  - Unnamed code 6 → 0x7F05CD39 → 0x7E53A935, which reads settings through 0x7E457C75
- **Symbol rewriting.** `0x7F05C426`/`0x7F05C5CE` look up identifiers that start with `APPEVENT_` and `API_IF_` in a runtime-built name→code table (RAM 0x602C…). They replace each name with `$`+hex. The error strings are `AppeventToCode`/`Api_If_To_Code … ENTRY ERROR`. **[V]** The table contents are not visible statically.
- **RCU = "RelocateCode".**
  - App API wrappers: `api_rcu_Upload_RelocateCode` 0x7E687157, `…Delete…`, `…Get_ProcList(_Media)…`. They are reached from SDK/high-level stubs at 0x7E9C8C3B/0x7E9C8C9C (pointer table 0x7EC0F09C).
  - These wrappers send requests through `0x7F05E43B` to **BAS_RCU_SRV** (ID 7, entry 0x7F05E2FE), which handles commands 0–7.
  - Upload: `rcu_serv_upload` → `bas_rcu_load` 0x7F05DF43. That function mounts the media and reads up to 16 KiB from `RCUOLYMP` / `R0240001.RCU` (8.3 names) into 0xBC61DF00 (audit 2026-11-09). Then `0x7F05DDF0` rewrites the symbols, and `flash_mem` 0x7F05E041 calls `0x7E675700(mode 4, …)`, the resource/flash writer. **[V]** For the call chain, **[I]** that mode 4 is a script area.
  - At start, BAS_RCU_SRV fetches the stored block (`0x7E674F44`) and checks the magic `ucr.`. If it is valid, `0x7F05DD81` feeds it into QBASIC. Stored scripts therefore auto-load. **[V]**

## 5. Peripherals (PER_*), UI input, LEDs

| Task (ID, entry) | What it does |
|---|---|
| PER_IN (0x2F, 7E463B0E) | Generic deferred-callback dispatcher. Waits on flag `E_PER_IN` and runs each registered 12-byte record `{…, u16 mask, fn}` (count 0x604163F8, array 0x604163FC) whose bit is set. Uses `udfu01 12,d2` to index the records, which supports udfu01 = multiply. **[V]** |
| PER_PCONT (0x30, 7E465C77) | Waits on flag and queue `QPERPCONT`. Ring buffer and per-client callbacks (`pcntdbg`: control, wait_flg, tag, callback). **[V]** for the structure. Pulse counter used by MEC_PCNT (shutter) **[I]**. |
| PER_WDT (0x31, 7E46C29B) | Kicks the watchdog through **SRAM code 0x47001560** when enabled (flag 0x6041A464), then waits on its queue with a 3000 ms timeout. Commands: 0 = off, 1 = on (10 s), 2 = change time. Shell: `per wdt off/on/time N`. **[V]** |
| PER_CCD_TEMP_MAIN (0x2E (audit 2026-11-09), 7E45DBB5) | Every 10 s (`dly 10000`) runs a state/event table (0x7E4C4DF8 (audit 2026-11-09)). Result 1 triggers a measurement (`0x7E45DC2C(3)`). Thresholds: lock / warn / attn1. **[V]** for the loop, **[I]** for the threshold meaning. |
| PER_ROTATE (0x6A, 7E4671F9) | Calls the accelerometer module (`per_acc`/`acc_spi` 0x7E45824B–0x7E45A76E: "Who am I?", offset/sensitivity tables) and math helpers. Outputs ROTATE_0/90/180/270. **[V]** for the calls, **[I]** for the purpose. |
| PER_SLOPE (0x6B, 7E469FD2) | Same accelerometer calls. roll/pitch, orientation, `readall adj for digitallevel` (level gauge). **[V]**/**[I]** |
| PER_EYE_SENSOR (0x78, 7E4613DD), PER_SCPU_POLLING (0x7B, 7E467D96) | **Empty tasks (`retf`)** in this firmware. **[V]** |
| HPROC_PROC (0x16, 7E4628E2) | "handler proc" deferred handler queue (test hooks PER_HANDLER_PROC_TEST_*). **[I]** |
| UI_IN (0x4E, 7E508FE8, pri 7) | Event flag 0x7E43EBFC. Bit 0x01 → key matrix scan 0x7E50A15C plus jog dial 0x7E50965C. Bit 0x02, every 10th tick → I/O-expander keys 0x7E50C26B and ADC dial 0x7E50B4C7, plus "edev" keys 0x7E50BAA6. Key sources: power, gio, adc, poll, ext, edev (0x7E50AB0C). Events go to `0x7E509CA3` (APPEVENT trigger, 101 callers). **[V]** |
| UI_OUT (0x4F, 7E50D858), UI_SCREEN (0x50, 7E50DD29), LED_SCREEN (0x19, 7E50D798) | UI output and LED tasks. The shell command `ui led` (7E50D6F0) prints the led number and status. **[I]** |
| SC_TTIMER (0x3E, 7E507115) | Soft timers `ttmr_dd1…5`/`ttmr_ed1…5`. **[V] (D2 2026-11-09):** the loop 0x7E507115 waits 25 ticks per pass and calls the active slots 1–31 (masks 0x604F3658/0x604F365C); register 0x7E506FF6, unregister 0x7E50708F. The scheap allocator is a separate part of the `sc` library 0x7E506CB0–0x7E508DA6: six fixed-block pools (table 0x7E7348E4), and SCHEAPDBG (0x1003, 0x7E5079DD) is its guard checker (14b §2) (D2 2026-11-09) |
| CPUCONN0/1 (0x8F / 0x1010, 7E505A22) | Inter-CPU service proxy (see §1). **[I]** |
| USRTEST_A–D (0x90–0x93) | OS self-tests ("Hello World!!!", queue and flag tests). exinf = 1. Usr0–4 do not start them. **[V]** for that, not searched elsewhere. |

Other drivers in the range have shell hooks only: RTC, IOE/IOEC (I/O expander over SIO), PWM, ADCONV, GIO, USF unit, water detection (`WATERDET`, a waterproof-housing leftover **[I]**), NMI/address-watch `dbgsup`, and the SDRAM arbiter/bus monitor.

**Roles of the unnamed runs in 0x7E421020–0x7E520000 (D3 2026-11-09; 15d §5 has the full list and the TSV rows; anchors re-checked with `fwmap fn`):**
- **BML/STL flash library 0x7E421C93–0x7E425F43**: STL read 0x7E421EC8 (← the traced wrapper 0x7E451D85 and `fmem` 0x7E44F509), write 0x7E421F23; BML erase/write/read; lock pair 0x7E4215A2/0x7E4215B6. The **STL core** (sector map) is 0x7E452343–0x7E455F92 (entries 0x7E4546CA/0x7E4546D4/0x7E4546ED) **[V edges; split I]** (D3 2026-11-09).
- **uITRON 4.0 kernel internals** 0x7E4300D7–0x7E438BF1 (7 runs: object create/delete, task, flag/sem/dtq/mbx/mtx, `ref_*`, CPU lock, dispatch, scheduler 0x7E435FF4) **[V mechanics; names I]**; OSDB object dumpers for S_SHELL up to 0x7E44D6EE (error legend 0x7E44D439 `uITRON Error Code`) **[V]** (D3 2026-11-09).
- **prm settings store** 0x7E455F93–0x7E45824A (`getval` 0x7E457C75, 2,168 call sites; section 07 §1) **[V]** (D3 2026-11-09).
- **Soft-timer API** 0x7E465081–0x7E465582: `tmr_start` 0x7E4650A2 (124 sites), `tmr_stop` 0x7E4650DD (39) **[V]**; **PER_PCONT client side** 0x7E465D10–0x7E466886 (PWM duty 0x7E466435/0x7E466448) **[V edges; I]** (D3 2026-11-09).
- **BT UART adapter** 0x7E46B24E–0x7E46B3D0 (← BT 0x7E9135F2/0x7E9136E5; calls SIO open 0x7E467EED and the UART attach 0x7E46967C) **[V]** (D3 2026-11-09).
- **USR_FAST_APP step handlers** 0x7E5025C3–0x7E503A6D; **CPUCONN remote kernel calls** 0x7E505A93–0x7E505F2F (`needs_remote` 0x7E505A93 is called by the Oly* kernel wrappers 0x7E449030…0x7E4494A1; send-and-wait 0x7E505D91) **[V]** (D3 2026-11-09).
- **UI_SCREEN task** 0x7E50DD29 and the UI_OUT back half to 0x7E50F7F1; the MEC core 0x7E514648–0x7E5167EB (`mec_alloc` 0x7E51470B, 143 sites; update/free 0x7E51483B, 119) and the MEC sequence steps 0x7E518E91–0x7E51BA08 **[V]** (D3 2026-11-09). **MEC layer below the handlers (coverage C4, [V]) (L1 2026-11-09):** the MEC init 0x7E517791 passes RAM 0x604F63FC to 0x7E518FBD, which fills a 12-entry operation table (0x7E51902A, 0x7E5191E5, 0x7E51921D, 0x7E51945B, 0x7E519662 = MAG STOP at slot 4, …, 0x7E519C89); the step timers come from `mec_timer.c` (start 0x7E51BAC5 → soft timer 0x7E4650A2; its error path 0x7E51BE62 logs `mec_timer.c`). Example: step 0x7E519A05 waits for `mec_ev` event 33, then arms MEC timers 16 and 17.
- Still open: the 4-command dispatcher 0x7E463376 (callers camera core 0x7E626C76 and EXP_MOVIE 0x7E6A1021…) **[I, weak]** (D3 2026-11-09).

## 6. Flash memory (SYSFMEM, [flashmem])

- **SYSFMEM** (ID 0x45, entry 0x7E4520F3) serves read and write requests posted by `0x7E451306` (strings `FMEMGID/FMEMWS1/FMEMSS1x`). It calls the BML/STL layer (`0x7E45232A` → `0x7E4217E6` read, erase/write `…gomennasai` errors). **[V]**
- **Modes, hex (D3 2026-11-09, 15d §5, V):** the task 0x7E4520F3 dispatches on `mode & 0xFF00`, then on the full mode: 0x000/0x002 BML_NormalWrite/AdwordWrite (0x7E44F197); 0x101/0x103 BML_NormalRead (`cmp 257/259`, 0x7E44F11B → 0x7E45038D); 0x102 AdwordRead (258); 0x104–0x106 status reads not in the help text (0x105 is a `ret` stub); 0x200 Erase (512, → 0x7E4519C5); 0x300 STL_Write (768, → 0x7E451CDB → 0x7E421F23); **0x400 STL_Read** (1024, 0x7E4505A6 → 0x7E451D85 → 0x7E421EC8); 0x500 STL_Delete (1280); 0x601–0x604 STL_Init/Format/Open/Close (1537–1540, 0x7E450AA1/0x7E450AAC/0x7E450AC0/0x7E450AD3). So 0x103, used by the Usr2 overlay loads, is a NormalRead variant. Earlier text: (D3 2026-11-09)
- Modes (help text): 000 BML_NormalWrite, 002 AdwordWrite, 101 NormalRead, 102 AdwordRead, 200 Erase, 300 STL_Write, 400 STL_Read, 500 STL_Delete, 601–604 STL Init/Format/Open/Close. The code passes 0x101/0x103. ~~**[I]** whether these map one-to-one.~~ **The help-text modes are hexadecimal [V for STL_Read] (C3 2026-11-09):** SYSFMEM 0x7E4520F3 calls 0x7E4505A6, which calls the `STL_READ` wrapper 0x7E451D85 only for mode **0x400** (`cmp 1024`; else `data_read_error. unknown mode!!`). 0x101 = NormalRead fits the same reading; 0x103 (Usr2 overlay loads) is not in the help list, so whether every mode is listed is still open **[I]** (C3 2026-11-09).
- Mode-bank and param-bank checks keep two copies with checksums: `Mode_Bank0 chksum OK/NG`, `Bank0 > Bank1` (0x7E450C4B, 0x7E450E86). **[V]**
- `flash addr` prints the **major ROM map** (constants in 0x7E44FEA8…). **[V]**

| region | addr | region | addr |
|---|---|---|---|
| adj | 0x40060000 | usr | 0x402C0000 |
| mode0 | 0x400A0000 | pict | 0x41040000 |
| mode1 | 0x400C0000 | osd | 0x43C40000 |
| param0 | 0x400E0000 | artfill | 0x45220000 |
| param1 | 0x40100000 | arteffe | 0x45480000 |
| lensfav | 0x40120000 | sound | 0x46200000 |

- Other `flash` subcommands: `fmem`, `oly fmem <addr> <size> <mode>`, `tnan ifread/ifwrite/iferase/ndread/ndwrite/nderase/stlread/stlwrite/stlformat/partinfo/stltbl/stldmp` (Toshiba NAND), `dump`, `log`, `trace`, `running`, `speed dma|nondma`.

## 7. Factory adjustment (ADJ, ADJSLF)

**ADJ** (ID 2, entry 0x7F080000, in overlay B, started by Usr4).
- Waits on flag `ADJ_WaiF` and queue `ADJ_SQR`. Commands 0/3/6/7 → 0x7F0801E6/21F/228/256. **[V]**
- Requests reach the op handler `0x7F080284`. **[V]** That they come from the USB/PTP side through TPC queue `QTPCADJR` is **[I]**.
- ~~The source file is `adj_p15740_p.c` (P15740 = PTP).~~ The file name `adj_p15740_p.c` (P15740 = PTP) is logged only by `get_MediaKind` 0x7F084D3F and `set_MediaKind` 0x7F084EF6 (vendor property 0xD028). **[I] (L1 2026-11-09):** the file is probably only the DeviceProp layer 0x7F084A00–0x7F085286. Its dispatchers 0x7F084A00 (← 0x7F080479), 0x7F084A6C (← 0x7F0804AB), 0x7F084AD8 (← 0x7F0804DD) and 0x7F084B77 (← 0x7F0804FE) switch on properties 0xD023–0xD028, and every function up to 0x7F08526F is called only from this layer. Its rodata (tables 0x7F0D2B88–0x7F0D2CB6, the `[adj_p15740_p.c]` strings 0x7F0D2CB8–0x7F0D2D75, the Set dispatch table 0x7F0D2D78–0x7F0D2DF7) is a separate block after the rodata of 0x7F080000–0x7F084855 (`ADJ_*` and `[adj]` strings 0x7F0D263A–0x7F0D283C, tables 0x7F0D2850–0x7F0D2B4C). The op handler 0x7F080284 logs with the prefix `[adj]`, so the call chain alone does not put it in `adj_p15740_p.c` (modules.tsv row updated). `0x7F080284` checks that the opcode is 0x1002–0x902B. It hashes `(op−0x1001) & 31` into the table at 0x7F0D2850. **[V]**

| opcode | handler | notes |
|---|---|---|
| 0x1002 / 0x1003 | 7F0803EE / 7F080438 | OpenSession / CloseSession (PTP standard numbers) **[I]** |
| 0x1014–0x1017 | 7F080479, 7F0804AB, 7F0804DD, 7F0804FE | Get/Set/Reset DeviceProp **[I]** |
| 0x9005 | 7F080519 → 7F08056A | main adjust executor. Touches keys, ccd-temp, rotate, timers. |
| 0x9006 / 0x9007 | 7F080E0F / 7F080FB8 | |
| 0x900D | 7F081025 | settings get/set (0x7E457C52/62/ED) **[V]** |
| 0x9013 | 7F081089 | `ContAFAE` (`[adj]RP/EP/TP/UR`) |
| 0x9015 | 7F081200 | `ContIAF` (capture mode) |
| 0x901E, 0x9021, 0x9022 | 7F081697, 7F08191D, 7F0819C9 | data transfers |
| 0x9023, 0x9025–0x9027 | 7F081A72, 7F081B24, 7F081B73, 7F081BDA | |
| 0x9029 | 7F081C10 | 24 sub-operations |
| 0x902A | 7F082C09 | 20 sub-operations |
| **0x902B** | 7F083D1C | sub-ops 4–18 via jump table 0x7F0D2B4C. **15 = shell command** (§3), 14 = flash access (0x7E44F197), others are memory/buffer operations. |

- External calls from ADJ reach these subsystems **[V]**: prm settings, flash, mechanical shutter (0x7E518Cxx), lens (0x7E51E…/0x7E532…), level/accelerometer (0x7E469Dxx), rotate, strobe (0x7E5E2xxx, "strobe timeout"), battery check, cam.c, exp, audio (0x7E95Cxxx), and the jog/key event paths. That these are what the factory adjusts is **[I]**.

**ADJSLF** (ID 3, entry 0x7F087004). Started by Usr2 bit 24, ~~called from `api_adj_Check_Execute_Self_Adjust` (0x7E675F05)~~. **[V]** **D3 (V):** 0x7E675F05 calls Usr2 (through 0x7E68CD13) with 0xFFFFFF, which loads overlays A and B but does not set bit 24; the only mask with bit 24 seen is 0x1000000 from slot 3 0x7EBA13F6 of vtable 0x7EC90B30 (caller not traced; 15d §4.4) (D3 2026-11-09).
- Reads queue `ADJSLF_EQR` and calls `0x7F0A7CC1`, the engine at ~~0x7F0A7Cxx–0x7F0AB000~~ **0x7F0A7CA5–0x7F0D257C** (coverage C4 (L1 2026-11-09)). The first function 0x7F0A7CA5 is called by the ADJSLF init 0x7F086FF5 (← Usr2 0x7E505005) and follows SPC's task starter 0x7F0A7C6B. The string users run on to the per-unit sequences `Sense` 0x7F0CB8DD, `SenseMG5`, `Defect`, `Spectra`, `BvCCD`, `BCShake`, `BCCenter`, `AUDIO`, `AFLED` and `Shutter` 0x7F0D23F5, whose `ret` at 0x7F0D257A is the last code in overlay B (0xFF bytes, then rodata from 0x7F0D2580). **[V]** for the two edges, **[I]** that every function between them is ADJSLF. Inside it: the result-CSV identity writer 0x7F0A8E8F and the card-file open 0x7F0A9083 (coverage C4 review 4).
- The engine logs PTP-style calls: OpenSession, Set/ResetDeviceProperty, GetExtDeviceInfo, `GetCalibData/SetCalibData(tag)`, DisposeExposeOnlyCapture, ContTFT/ContAFAE/ContIAF, MDN/MDI/MDO, SetPrePro.
- It uses card files: `/%03dPRM%02d/`, `wb_lv001.csv`, `%sCalib.prm`, `MNF99991.JPG`, `AFBV9311.JPG`, CSV output.
- So it is an in-camera client ("CAPI") that runs adjustment sequences from the card without a PC. **[I]**

## Open questions

1. **Task ID layout disagrees with the coordinator's tasks.tsv.** I find `{id, attr, exinf, entry, …}` starting at 0x17CB0. The evidence is the boot-time `OlyTaSt` labels and TA_ACT on 0x7E44A043 (§1). Under this layout, IDs 0x8085/0x7E5065EF ("DBG_OUT" in the code vs PWR_STANDBY in the name table) and 0x84/0x7E6D4597 (MOV_EDIT, not IMG0_LOCAL) need a decision. **(L1 2026-11-09):** the coordinator's tasks.tsv now uses this layout (0x8087 MOV_BRIDGE, 0x84 MOV_EDIT, 0x808D IMG0_LOCAL), and section 04 was corrected to match (coverage C4 review 1).
2. What sets the USR_FAST_APP flag bits after 0x01/0x08, and when does the app call Usr2 (bits 0, 1, 24) during normal use?
3. Meaning of flash src 0x4039D000 (boot read) compared with the 0x80xxxxxx fmem addresses, and the layout of the 0x40xxxxxx ROM map.
4. The runtime API_IF_/APPEVENT_ name tables used by BASIC (RAM 0x602C…), and which API codes `api()` accepts (0x7E67F3E6).
5. ~~The CPU1 worker pool 0x1011–0x101B (entry 0x7EE8FBB1) and 0x101C–0x101E.~~ Answered: AVPI threads, AvScaTask and two AVPI service tasks (13b §2.4) (D1 2026-11-09).
6. Exact sub-operation meanings for ADJ 0x9029/0x902A/0x902B, and whether TPC really routes PTP vendor ops to ADJ (`QTPCADJR`).
7. Who sets the UI_IN flag (likely a cyclic timer), and the LED_SCREEN/UI_SCREEN internals.
8. Where the `dbgall` command list comes from.

# 10f — Debug and service features: how each is reached and gated (E-PM2 v1.6)

- **Labels:** **verified** = read in code or bytes; **inferred** = from names, order or layout. **External** = product knowledge, used only as support.
- **Addresses:** E-PM2 v1.6 runtime addresses (block-0 offset = address − 0x7E421020). Scratch scripts: `$S/hidden/debug-service/` (`rw.py` word/byte reader, `adjtbl.py` ADJ op-table finder).
- **Scope note:** this section says how things are reached and what gates them. It gives no step-by-step use recipes.
- **"All 7 bodies"** = E-PM2 plus E-PL5, E-P5, E-M10, E-PL7, E-M5 II and PEN-F, string-searched with `fwmap str` (the E-PL6 code was not scanned). **"All 8"** in the label column adds E-PL6, from the `.en.tsv` files.

## Verdict table

| Feature | Prior claim | Verdict | Real status on E-PM2 | Same code on |
|---|---|---|---|---|
| S_SHELL monitor | "serial port, CPU0 regs 0x987000xx" | **CORRECTED** (two UART *ports*, not two CPUs) | Hidden-debug-only. Started every boot; console live after Usr1; needs physical UART access | all 7 bodies (task name, prompt) |
| U_SHELL, 54 families @0x7E7332B4 | 54 commands | **CONFIRMED** | Hidden-debug-only. Fed only by S_SHELL `:` mode and ADJ op 0x902B | all 7 (U_SHELL task) |
| U_SHELL over USB (ADJ 0x902B sub-op 15) | "reachable over USB" | **CONFIRMED, gate added** | Hidden. No model, setting or password gate; gated only by USB connection type (0/5/6) and an ADJ session | E-PL5, E-P5, E-M10 identical strings; E-PL7/E-M5 II/PEN-F lack the `USR> `/`nikomon` strings (sub-op changed, inferred) |
| BASIC interpreter + RCU scripts | load from card, save to flash, autoload with `ucr.` | **CONFIRMED + trigger found** | Hidden. Card load is triggered by `Relocate::registerCode` (GUI debug menu item, or `sdk api`), not at boot. The saved script autoloads at every BAS_RCU_SRV start | all 7 |
| Overlay A (BASIC) loaded in normal use | "on demand" | **CORRECTED (inferred strong)** | Loaded in normal use: Usr2 bit 0 also starts the movie-recording tasks | all 7 (inferred) |
| ADJ (factory PTP) | "16 vendor ops; on demand" | **CONFIRMED + gate traced** | Hidden. Code is in RAM whenever USB/PTP is up. 22 ops accepted | all 7: identical 22-op accept table |
| ADJSLF (self adjust) | "bit 24 starts it" | **CONFIRMED + gate found** | Hidden, gated by the factory flag PRM_MODE_SHIPS_ENABLE (prm 0x0DB1) = 0 and wake reason SELF_ADJUST. Dormant on a shipped camera (inferred: flag set at shipping) | E-P5 same gate (verified); others have the strings |
| SS_DEBUGMENU | entry not found | **PARTLY RESOLVED** | Hidden. Contents found (Life Test, Relocate register/erase code, Color setting/result). **Entry found (13d §4.3) (D1 2026-11-09)**: a key sequence in SS_MENU_MAIN HIDE_MODE, gated by getShippingInfo(4); whether a retail body passes the gate is unknown | all 7 (strings) |
| SS_SELFADJ / self-adjust menu | entry not found | **RESOLVED** | Reached only through the ADJSLF gate above | all 7 |
| Version-check menu (CAM_MISC_VERCHK_MENU) | "hidden menu" | **NOT the Firmware screen; trigger open** | The Firmware item starts CAM_MISC_FIRMUP, not VERCHK (verified chain: PostEventToCA(11 = GUI_END_MENU, 12 = STS_CHG_INFO_FIRMUP) → startShooting → param 13 → event 0x0600000B → `startFirmupSubAppStateMisc` 0x7ECE06C0; only the delivery of the stored sub-app request is inferred). The GUI event of the same name, EVT_REQ_START_VERSION_CHECK 0x9628, opens HIDE_MODE, the hidden debug-menu entry. No trigger of the CA VERCHK sub-app was found. Probably hidden (inferred) (see §4.3) | all 7 (A4 2026-11-09) (C5 2026-11-09) |
| Life test | strings only | **CONFIRMED, entry = debug menu** | Hidden-debug-only | all 7 |
| prmdbg / `app Set_CameraInfo` / `sdk api` / `mov` / `lens` / `cam` | debug shells | **CONFIRMED** (only via U_SHELL) | Hidden-debug-only | all 7 |
| USRTEST_A–D | "Usr0–4 do not start them" | **CONFIRMED, wider search** | Dormant: no code loads their task-id slots | all 7 (strings) |
| Pixel Mapping and other service items | normal menu | **CONFIRMED (strings + chain)** | Active | all 7 (English label) |

## 1. S_SHELL and U_SHELL

### 1.1 Started on every boot (verified)
- Usr0 (0x7E503DD4) starts DBG_OUT, S_SHELL and U_SHELL as its first three `OlyTaSt` calls (0x7E503E4D, 0x7E503E68, 0x7E503E83). This code is straight-line, with no condition before it.

### 1.2 The console gate (verified)
- **Two UART ports, not two CPUs.** The byte at **0x8FF00080 is a port index**, not a CPU id. Pointer tables at 0x7E46DEC8 give TX status / TX data / RX status / RX data for port 0 (0x9870001C/18/0C/08) and port 1 (0x9830001C/18/0C/08). `0x7E44AD97` initialises the 0x9870xxxx port and writes 0 to 0x8FF00080. `0x7E44AE3D` initialises the 0x9830xxxx port and writes 1 (at 0x7E44AF18). Section 01's "CPU0 regs / CPU1 regs" reading is therefore **corrected**.
- **Per-port enable byte at 0x8FF00081+port.** Boot init (0x7E44AD97) sets it to 1.
  - `putc` 0x7E44B051 always copies the character into a 767-byte RAM ring (0xA0731828). It writes to the UART only if the enable byte is **> 1**.
  - `0x7E44B01B` sets the byte to 2. `0x7E44AFC6`/`0x7E44AFB3` set it to 3 and flush the ring to the UART.
- **Usr1 opens the console on a normal boot.** Usr1 calls `0x7E44B00D` (enable = 2) at 0x7E504FAB, in straight-line code.
- **S_SHELL waits for that.** The S_SHELL loop (0x7E44E9AF–0x7E44E9D2) polls every 50 ms. It continues when RX status is non-zero (then it prints the boot trace with `initbuff`) or when the enable byte is > 1. Then it prints `:-) ` and reads lines from RX (0x7E44E8EA).
- **No setting, flag or debug-mode check** gates S_SHELL input (verified for the S_SHELL loop, readline and the 0x7E44DBF5 command chain entry). The only "gate" is physical access to a UART. Which pads or connector carry port 0 was **not found**.
- **External-device re-route (verified code, purpose inferred).** UI_IN's "edev" scan `0x7E50BAA6` reads an ID over the I/O-expander bus (`0x7E464850`, `[IOE]SET_MAKER_ID`). It matches the ID against the table at 0x7E7353F8 (ids 0x0101, 0x0202, 0x0322, 0x0102, 0x0103, 0x0204/0x0205, 0x023E).
  - On attach of ID **0x023E**, `0x7E50BDA0` switches the console to port 1 and enables it.
  - On detach, `0x7E50BD61` re-initialises port 0 and enables it.
  - IDs 0x0204/0x0205 instead call `0x7E461515(179, …)`.
  - Reading (inferred): a service adapter with ID 0x023E takes over the console.

### 1.3 U_SHELL feeders (verified)
- The queue NIKOLQ (0x7E43EE3C) is written only by S_SHELL (0x7E44EA0D, 0x7E44EA47) and read by U_SHELL (0x7E44EA5C).
- The dispatcher `0x7E503C7E` loops over exactly 54 `{name, handler}` entries at 0x7E7332B4 with a plain strcmp. It has no gate.
- Its only other caller is `0x7E503CB7` ← ADJ 0x902B sub-op 15 (`0x7F08433A`).

### 1.4 The USB path and its gate (verified unless marked)
The chain has three steps:
1. The PTP dispatcher `0x7F08ECFD` sends an opcode that is not in its table and is 0x9xxx to `0x7F08CDAC`.
2. That function goes on only if (a) the code runs in the PTPCOM task (`0x7F089321` == 2) and (b) gConnectMode (0xA06DE63A) ≠ 2.
3. Then `ADJ_P15740_COM_OPE_CODECHK` (`0x7F08D080`, ADJ message 6 → `0x7F080228`) looks the op up in a **22-entry accept table at 0x7F0D25A2**. The table holds 0x1002, 0x1003, 0x1014–0x1017, 0x9005–0x9007, 0x900D, 0x9013, 0x9015, 0x901E, 0x9021–0x9023, 0x9025–0x9027, 0x9029, 0x902A and 0x902B (phase 2).

**The ADJ session gate:**
- ADJ's handler `0x7F080284` rejects every op except 0x1002 unless the ADJ session flag (0xA06DD358) is 1.
- That flag is set only by ADJ's own OpenSession (`0x7F0803EE`), which checks no parameters.
- ADJ receives OpenSession/CloseSession (list at 0x7F0D4DBA = {0x1002, 0x1003}) through `0x7F08CE8A` → `ADJ_P15740_COM_VENDOR_OPERATION`. This happens only when the PTPCOM mode (0xA06DECBE) is 2.

**Connection types.** TPC_ON (0x7F089339) sets both values from the connection-type byte:
- PTPCOM mode = 2 for types 0/2/3/5/6, 3 for type 1 and 1 for type 4 (`0x7F08EA4C`).
- gConnectMode = type, with 3 → 2 and unknown → 0 (`0x7F0895AA`).

So **ADJ vendor ops, including the remote shell, work only on connection types 0, 5 and 6.** They do not work on PictBridge (1), X3C (2/3) or MTP (4).

**Which modes these are:**
- `api_comm_Start_Communication_Storage` 0x7E6763A2 sends type **0** to TPC (verified). DPS sends 1 and MTP sends 4.
- `api_comm_Start_Communication(5)` from a fourth link class (vtable 0x7EC91700) sends 5. It is probably LINK_PROTOCOL_PC_LINK (inferred).
- The same function (`0x7F0895AA`) builds the USB IDs: VID bytes 0xB4,0x07 (= 0x07B4, Olympus's vendor ID, external) and PID 0x012E (types 0/5), 0x012F (1/4), 0x0110 (2/3), 0xF102 (other) (verified bytes; descriptor role inferred).
- How PTP ops reach TPC while the camera presents mass storage in type 0 was **not traced** (a vendor SCSI pass-through is likely; external: Olympus's updater uses "Storage" mode).

**Summary of the gate.** There is **no model check, setting check, factory flag or password**. The gates are: USB connection type, overlay B loaded (any USB connection needs it), and an OpenSession. In sub-op 15, the bit in parameter word (8,a2) & 2 only selects the refused "nikomon" (S_SHELL) target. It is a caller option, not a gate. The command output goes to the debug print path. Whether the PTP reply returns it was not traced.

### 1.5 Other bodies
- The 22-op ADJ accept table is **byte-identical in all 7 bodies** (`adjtbl.py`: E-PL5 0x7F0D25A2, E-P5 0x7EEE01CE, E-M10 0x7E88D356, E-PL7 0x7E8888EA, E-M5 II 0x60D825CE, PEN-F 0x60D624A2) (verified).
- `S_SHELL`, `U_SHELL`, `:-) ` and `ADJ_P15740_COM_OPE_CODECHK` exist in all of them.
- `USR> ` (exact) and `not support nikomon` exist in E-PL5, E-P5 and E-M10, but **not** in E-PL7, E-M5 II or PEN-F. Reading (inferred): from 2014 the 0x902B shell bridge was changed or removed. The code was not compared.

## 2. BASIC interpreter and RCU scripts

- **Load from card (verified chain):**
  1. `Relocate::registerCode` is SDK API 0x40301 (handler `0x7E9C8C9C`, table 0x7EC0F09C).
  2. → `0x7E9E0BDE`: set the RCU "disable flag" = 1 (`0x7F05DD5A` → 0xA06DD24C), then `Get_ProcList_Media` and `api_rcu_Upload_RelocateCode` 0x7E687157.
  3. → BAS_RCU_SRV `bas_rcu_load` 0x7F05DF43 (`RCUOLYMP/R0240001.RCU`) → symbol rewrite → `flash_mem` (mode 4).
  - **Nothing at boot reads the card file.** The callers of `api_rcu_Upload` are only this SDK method.
- **Who calls registerCode (verified):** the GUI debug-menu action `0x7EDA057A` (`[GUI App]:registerCode` / `eraseCode`). It reads GUI item data (69, 6): field 1 → register, 0 → erase. So the card load is reached from **SS_DEBUGMENU** (§4.1) or from the `sdk api` shell.
- **Autoload of the saved script (verified):** at task start, BAS_RCU_SRV (0x7F05E2FE) reads the mode-4 block (`0x7E674F44`, 16 KiB). It compares the first 4 bytes with `ucr.` (`0x7E500E40`). If they match, it feeds the script into QBASIC (`0x7F05DD81`). The disable flag is **not** checked on this path.
- **Is overlay A loaded in normal use? Yes (inferred strong).**
  - Usr2 bit 0 loads overlay A and starts USTART3. USTART3 also starts the movie tasks (MOV_REC, MOVREC_FILE, MOV_ENCODE, MOV_AVCHD…) and C3D (section 01), which normal operation needs.
  - Usr2 callers (verified): `0x7E68CD13` ← `api_adj_Check_Execute_Self_Adjust` (0xFFFFFF, then 0x1000000), the strobe and lens card-firmup APIs 0x7E67ECB7/0x7E67EE35 (0xFFFFFF via `0x7E67EC80`), and an object with vtable 0x7EC90B30. Its slots call Usr2 with 0xFFFFFF / 1 / 2 / 0x1000000 (0x7EBA139E/13BE/13DA/13F6).
  - That object is built only through `0x7EBA1370` ← 0x7EBA12F9 ← 0x7EBA12CE ← 0x7EA3C171, in the `CapBoo_BootManager` module (its destructor string is referenced next door). So the boot manager owns the overlay loader (inferred).
  - Consequence: once overlay A is loaded, BAS_MAIN/BAS_RCV run, and any `ucr.` block saved in flash runs on every boot.

## 3. ADJ and ADJSLF

- **ADJ in normal use (verified):** TSK_ADJ is started by Usr4 (Usr2 bit 1), together with the PTP/TPC tasks. Its code is in RAM whenever USB PTP works. It answers only through the gate in §1.4. TPC_ON type 0 also clears the ADJ session (`0x7F080175` at 0x7F089431).
- **ADJSLF gate, `api_adj_Check_Execute_Self_Adjust` 0x7E675F05 (verified):**
  - arg 0: info 4012 must be **0**.
  - arg ≠ 0: info 4012 must be 1 **and** info 4017 must be 1.
  - Both: `0x7E68E9F4(0x02000005)` and `(0x02000006)` must pass.
  - Then Usr2(0xFFFFFF), the language step (info 1009 → `0x7E6804CB`), and **Usr2(0x1000000)**, which starts TSK_ADJSLF.
- **What the info ids are (07-settings.tsv, verified):** info 4012 = prm **0x0DB1 `PRM_MODE_SHIPS_ENABLE`** (FLASH, default 0). Info 4017 = prm 0x5781 (ROM constant, value 0). So the arg ≠ 0 path can never pass on the E-PM2, and the arg 0 path passes only while the ship flag is 0.
- **What calls it (verified):**
  1. At boot, the GUI wake handler `0x7ECDFC0F` reads `getWakeUpIssue`. For **API_WUI_SELF_ADJUST (9)** (enum strings at 0x7EBFB625) it calls `SelfAdjust::readyExecuteSelfAdjust` (SDK 0x40101, `0x7E9C9D62`).
  2. → `0x7E9E245E`. With its argument 0, this also requires `0x7E9979CA()` == 9 (the wake reason).
  3. → `0x7E9E274B` → Check(0). Success puts the GUI into its self-adjust state.
  - Which hardware power-on factor becomes WUI 9 was **not traced**. The raw factor is decoded at 0x7E45D280 from register 0x98E00048 into 0x604154E6.
- **Reading (inferred):** self-adjust is a factory step for unshipped boards (ship flag 0, card files present). On a retail camera the flag is presumably 1. It could be changed only through the debug paths (`prm setval`, ADJ 0x900D settings set).
- **E-P5 has the same gate (verified):** E-P5 0x7E34B59C reads prm 3505 (0x0DB1) and 22401 (0x5781) directly, with the same 0x02000005/6 checks and the same Usr2 masks.
- **ADJSLF step `UnitCodeCam` 0x7F0B8D18 (round-5 review 4, F080; flow V, effect I).** Caller: the ADJSLF sequence dispatcher 0x7F0AAD2B (table word 0x7E8F2124). It opens the CSV block `UnitCodeCam` (0x7F0A8912), writes the identity record 0x7F0A8E8F (test 2140101), logs the firmware version 0x7F0A9C08 = 0x1600 as ` %04X` (test 2140301), then runs test 2140302. If the block opened and 0x7F0A9C46(0) = 1, it reads 1 byte of calib tag **0x5781** with GetCalibData 0x7F0A961B (`mov 22401,d0`), then runs test 2149001. Only if that byte is 1 and the unit code (the step's d0) is 1–10 does it continue: SetCalibData (0x7F0A9626/0x7F0A9631) 0x0DA1 `PRM_MODE_DPS_ENABLE` = 1, **0x0DB1 `PRM_MODE_SHIPS_ENABLE` = 1**, 0x0AA2 `PRM_DESTINATION_AREA` = unit code, 0x0874 `PRM_ADJ_FLAG` = 0, then MDN(9) 0x7F0A9867. A unit code outside 1–10 gives error 3000 (0x7F0A8D96). **Inferred:** this is the factory step that sets the sales region and closes the ADJSLF gate above (ship flag 1). The calib tags written here are prm ids, so tag 0x5781 is most likely prm 0x5781, the ROM constant with value 0 in 07-settings.tsv (info 4017); with that value the write path cannot run on v1.6. (C5 2026-11-09)

## 4. Hidden GUI menus

### 4.1 SS_DEBUGMENU (GUI super-state 10)
- **State ids (verified):** the SS name table at 0x7EFDD2D8 gives 1 COMMON, 2 REC, 3 MENU_MAIN … 9 SELFADJ, **10 DEBUGMENU**, 11 USB, 14 DPS, 15/16 BT. The debug-menu module ~~0x7ED9F800–0x7EDA1400~~ (SS_DEBUGMENU handler code 0x7EDA0410–0x7EDA09AC: 13d §4.2 gives 0x7EDA0410 to the last handler 0x7EDA098D, which ends at 0x7EDA09AC (L1 2026-11-09)) registers with descriptor words 0x000A0004/0x000A0016 (0x7EFD1F94), with handler tables at 0x7EFD1EA4/0x7EFD1EF4. **Corrected (13d §4.1) (D1 2026-11-09):** 0x000A0004/0x000A0016 are the descriptor counts (4 states, 10 events, 22 handlers, 10 events); 0x7EFD1EA4 is the event map and 0x7EFD1EF4 the handler array.
- **What it offers (verified dispatch, labels inferred):** the action dispatcher `0x7EDA05EC` uses the selector `0x7EDA0637`, which reads GUI data (69, 6):
  - **values 245–247, 249–251 → Life Test** (`0x7EDA053B`, `[GUI App]:Life Test Start`, then a LifeTest SDK call). The AF/IS/strobe/shutter/CCD life-test loops are at 0x7E9D7F4F–0x7E9DAF97.
  - **0 → Relocate code register/erase** (BASIC script to/from flash, §2).
  - **26 → Color setting/result** (`0x7EDA0968` area; on the power key it leaves through `0x7EDC5C47(3,0)`, which is a request to the camera app (PostEventToCA), not a GUI state change (D1 2026-11-09)).
  - The gdbDebugMenu draw routine is `0x7ED48BBA` (`usRightMark/usItem/usPrg`).
  - The menu draws no block-1 labels: no debug-menu text exists in any body's English table (all 7 `diff_*` files and the `.en.tsv` checked).
- **Entry: found (13d §4.3, verified code) (D1 2026-11-09).** A Setup dialog method 0x7EDFD665 (inferred: Monitor Adjust) checks key code 4 and `IOlyApiMaintenance` getShippingInfo(4); only if it returns 1 does it post EVT_REQ_START_VERSION_CHECK 0x9628. SS_MENU_MAIN state 4 maps 0x9628 to state 6 `ID_ST_HIDE_MODE`. There a counter at RAM 0x602BC480 steps on Up → Down → Left → Right → shutter half-press → shutter full-press (0→1→2→3→7→8), and OK with counter 8 returns 0x0A01 = SS 10 state 1 (bytes 0x7EDABA14–0x7EDABA54 inside the handler 0x7EDAB9FE (L1 2026-11-09)). Whether a retail body passes the getShippingInfo(4) gate is **not known**.
- **HIDE_MODE entry and a second sequence (14e §4.4) (D2 2026-11-09).** The state-6 entry function 0x7EDABA6F calls `setLongPressKey(8, 2000)` and `(9, 2000)` (0x7ED00B90) before it shows its page (V). In HIDE_MODE, OK held 2 s and MENU held 2 s, in either order, set a second counter 0x602BC482 to 10 (handlers 0x7EDAF544 / 0x7EDAFE4B: 15 → 10 or 14, 14 → 10 or 15); then OK calls `userMenuMainReset::MenuCursorMove` 0x7EDED19A(4,0) and SettingController vt+40 (V). That KeyCtrl keys 8/9 are OK/MENU and that the path is a hidden reset are inferred.
- *Superseded reading:*
  - `0x7EDC5C47(ss, state)` changes the GUI super-state (inferred from the debug-menu exit). Among its 317 call sites none passes the constant 10. **Corrected:** 0x7EDC5C47 is `PostEventToCA` (string `[GUI App]: PostEventToCA`), a request to the camera app; SS changes are handler return values (13d §4.1) (D1 2026-11-09).
  - The descriptor's factories (0x7ED9FFAF/D1/F3) are reached only through pointers.
  - Not ruled out: a table-driven state change, a key-combination handler in SS_REC, or a boot path.

### 4.2 SS_SELFADJ (state 9) and the self-adjust sub-app (verified)
- The misc sub-app state 0x2000 has the descriptor 0x7EED9DBC = {0x2000, **0x7EED93EC**, 11}, followed by {0x2001, 0x7EED949C, 1}, {0x2002, 0x7EED94AC, 5}…. Its 11 rows of 16 B start at 0x7EED93EC, and each row is **`{event, flag, next_state, handler}`** (the old reading started at 0x7EED9400 as `{state, next, handler, event}` and so shifted every id by one row). Event **0x06000009** → `startVersionCheckMenuSubAppStateMisc` 0x7ECE0653 (next 0x2006), **0x0600000A** → `startSelfAdjustMenuSubAppStateMisc` 0x7ECE067B (next 0x2007), and **0x0600000B** → `startFirmupSubAppStateMisc` 0x7ECE06C0 (flag 0x85, next 0x2008). (C5 2026-11-09)
- `setSubAppChgReqInfo` 0x7ECD6574 (after the check 0x7ECD65AA) → `0x7ECD6728` stores {sub-app, event} at req+20. Its jump table 0x7EED4828 is indexed by param − 1: param 11 (CAM_MISC_SELF_ADJUST) → {0x08000005, **0x0600000A**}, 12 (CAM_MISC_VERCHK_MENU) → **0x06000009**, 13 (CAM_MISC_FIRMUP) → **0x0600000B**. The names come from `0x7ECD68D8` (same indexing, table 0x7EED489C). So the param → handler result was right, but every event id was wrong. (C5 2026-11-09)
- Param 11 is passed from `0x7ECE01DB` (the readyExecuteSelfAdjust path). So the self-adjust menu is reached only through the §3 gate.
- Two menu-OK paths (0x7EDA9F47, 0x7EDAAAC5) call `0x7EDC5C47(9,7)` for menu item 598 when a condition holds ((0x602BC48C)==1 and `0x7ED009D6()`==4). What item 598 is was not identified. (0x7EDC5C47 is PostEventToCA, so (9,7) is a CA request, not "go to SS 9 state 7" (D1 2026-11-09).)

### 4.3 Version-check menu
- **Verified:** `startShooting` 0x7ECDCB10 reads rcv_info.info from the **second** word of the CA event (a3 = a1+4) and maps info **11 → param 12 (VERCHK)** and 12 → param 13 (CAM_MISC_FIRMUP). (A4 2026-11-09)
- **Verified:** the main-menu OK handler 0x7EDA9D03 (`doCmd_SsMenuMain_StWizardMenu_EvtKeyOKOn`, SS_MENU_MAIN state 4 WIZARD_MENU_ENTRY) calls PostEventToCA `0x7EDC5C47(11,12)` for item **43**, then logs `[GUI App Version]:OkOn called , F/W Version up start` ("version up" = firmware update). PostEventToCA sends {code 11, param 12} to the appCaller slot vt+4 = 0x7ECE3A9E (vtable 0x7EEEC80C), which maps code 11 to the CA event **0x0400000B** through the `{code, event}` table 0x7EEEBB28 and passes param 12 as the second word. **Code 11 is `GUI_END_MENU`, not GUI_START_SHOOTING_SERVICE (that is code 10):** the `{code, name}` table 0x7EEEFFD0 lists 0x0A GUI_START_SHOOTING_SERVICE, 0x0B GUI_END_MENU, 0x0C GUI_END_LV_CONTROL, and the `appCaller Event Info` debug command 0x7ECE5383 looks names up there and sends the id as the code through the same vt+4. Its info table 0x7EEF05E4 names **info 12 `STS_CHG_INFO_FIRMUP`** (11 = STS_CHG_INFO_VER_MENU, 3 = STS_CHG_INFO_SHOOTING; the same handler posts (11, 3) at 0x7EDAA83E). In the shooting CA state 0x5701 (descriptor 0x7EEE10C0, 58 rows from 0x7EEE08B4), row 0x7EEE0BF4 = {0x0400000B, 1, next 1, `startShooting` 0x7ECDCB10}, so the step to startShooting is verified (the old "0x7ECDCF0D → 0x7ECD27A7" is the handler of the row before it, event 0x04000009). startShooting maps info 12 → param 13 (CAM_MISC_FIRMUP), and 0x7ECD6728 turns param 13 into the misc event 0x0600000B → `startFirmupSubAppStateMisc` 0x7ECE06C0. The info is **12 → CAM_MISC_FIRMUP**, the firmware update, not VERCHK. **Inferred:** how the stored request {0x08000005, 0x0600000B} reaches the misc state 0x2000 table. (A4 2026-11-09) (C5 2026-11-09)
- **Inferred:** item 43 is Setup › **Firmware** (string 134, help 492 "View product's firmware version."), the only firmware item in the top table (record 35, kind 0x100). Its OK path is the firmware-update branch (CAM_MISC_FIRMUP: the card lens/flash updater), so the Firmware screen is **not** the VERCHK menu. The earlier "probably the normal Firmware screen" reading is withdrawn. (A4 2026-11-09)
- **VERCHK trigger (verified absence, as far as checked):** VERCHK needs info 11, and no PostEventToCA call passes the constants (11, 11) (one site, 0x7EDAD0D3, passes a setting value). What starts `startVersionCheckMenuSubAppStateMisc` 0x7ECE0653 is not known. (A4 2026-11-09)
- **The GUI event of the same name is a different path (verified; 13d §4.3).** EVT_REQ_START_VERSION_CHECK 0x9628 is posted only by the GUI itself at 0x7EDFD68D, after the getShippingInfo(4) gate, and only SS_MENU_MAIN state 4 handles it: it goes to state 6 `ID_ST_HIDE_MODE`, the debug-menu entry (§4.1). The CA could deliver it too: GuiCallerImp::sendEvent 0x7ECE6E27 maps CA code 0x75 to 0x9628 (table 0x7EEF3434), but no CA sender of 0x75 was found. **Inferred:** by name, the CA VERCHK sub-app and the hidden HIDE_MODE screen belong together, so the "version-check menu" is most likely hidden. (A4 2026-11-09)

### 4.4 Shipping info
- `Maintenance::getShippingInfo` (`API_SHIPPING_INFO_{DEST_AREA, FLAG, DPS, TIME_ADJUST, MENU_BUTTON}`) is logged by the GUI at 0x7EDFD665. Its use as a menu gate was not traced. (Traced in 13d §4.3: selector 4, inferred API_SHIPPING_INFO_MENU_BUTTON, gates the debug-menu entry (D1 2026-11-09).)
- The one verified ship-flag gate is ADJSLF (§3).

## 5. prmdbg / `app Set_CameraInfo` / `sdk api` / `mov` / `lens` / `cam`

- All of these are entries of the 54-entry U_SHELL table (`prm`, `app`, `sdk`, `mov`/`movp`/`movc`, `lens`, `cam`) (verified).
- **`face`** (L1 2026-11-09, verified) is also a U_SHELL family (word 0x7E7333B8 → dispatcher 0x7E6F4D77). It has 20 subcommands (`start`, `stop`, `get`, `keep`, `reset`, `abort`, `prog`, `get_eye`, `dump`, `setting`, `log`, `pt`, `load`, `set_pos`, `get_pos`, `set_info`, `mdm`, `reg`, `tune_l`, `tune_g`) in the table 0x7E8DE4EC (15b §6). Section 13b cites a face debug command only from the E-P5.
- U_SHELL has exactly two inputs (§1.3): the S_SHELL UART (`:` mode) and ADJ 0x902B sub-op 15 over USB (§1.4).
- **Caveat (verified):** the same *targets* are not shell-only.
  - The `sdk api` handlers wrap the OlyApi/SDK layer, which the GUI also calls (for example SDK 0x40101 and 0x40301 above).
  - ADJ op 0x900D sets prm values directly (0x7F081025 → 0x7E457CED) without U_SHELL.
  - So "settings writable from outside" = UART shell, or USB ADJ (shell or 0x900D).

## 6. USRTEST_A–D

- **Verified:** rows 0x90–0x93 (entries 0x7E501C5B, 0x7E501CE7, 0x7E501E1D, 0x7E501E63, attr 0). Their task-id slots in the ID→var table are 0x7E43EA86/88/8A/8C (values 0x90–0x93). **No code loads those slots** (grep over the whole function listing). So no `OlyTaSt` with a fixed id starts them.
- The only paths left are S_SHELL's generic `OlyTaskStart <id>` (inferred: the command takes an id) and `usrSample`, which only posts to their queue.
- **Status: Dormant.** The strings `USRTEST_A–D`, `Hello World!!!` exist in all 7 bodies.

## 7. Normal-menu service functions (brief)

| Item (string id) | Chain | Status | Bodies (English label) |
|---|---|---|---|
| Pixel Mapping (207; help 476) | `PixelMapping::execute` (SDK class G) → `CmpCst_Function` 0x7EAA8FF9… → `api_rec_Calculate/Save_Pixelmaping` 0x7E688CFF/0x7E688D6C | Active (verified chain from strings; menu record is in Custom Menu J code, not traced here) | all 8 |
| Level Adjust (160; 478) | PER_SLOPE `readall adj for digitallevel` | Active (inf) | all 8 |
| Touch Calibration (1343) | touch-panel task | Active (inf) | all 8 |
| Firmware (134; 492) | top-table record 35; OK → PostEventToCA(11 = GUI_END_MENU, 12 = STS_CHG_INFO_FIRMUP) → startShooting → CAM_MISC_FIRMUP → 0x0600000B `startFirmupSubAppStateMisc` 0x7ECE06C0 (firmware update), not VERCHK (§4.3) | Active | all 8 (A4 2026-11-09) (C5 2026-11-09) |
| Reset/Myset (225), EVF Adjust (126) | normal tables | Active | all 8 |

## Open questions

1. ~~**SS_DEBUGMENU entry.** Find the non-constant `0x7EDC5C47(10, …)` site or a key-sequence handler. Start from the SS_REC key handlers and the factories at 0x7ED9FFAF.~~ Found (13d §4.3); still open: does a retail body pass getShippingInfo(4) (D1 2026-11-09)?
2. **Wake reason 9.** Find which power-on factor (0x604154E6, decoded at 0x7E45D280) becomes API_WUI_SELF_ADJUST. Check also that retail cameras have prm 0x0DB1 = 1 (a camera-side read only).
3. **Storage mode and PTP.** Find how PTP ops reach TPC in connection type 0 (mass storage). Find what selects type 5 and type 6.
4. **Edev ID 0x023E** (console re-route) and 0x0204/0x0205: which accessory or jig they are, and which connector carries UART port 0.
5. **Item 43 / item 598.** Confirm item 43 = Firmware with the panel-id map, and identify item 598. Also: what starts CAM_MISC_VERCHK_MENU (info 11), and does any CA code send GUI code 0x75 (→ 0x9628)? (A4 2026-11-09)
6. **0x902B in E-PL7 and later.** Compare the sub-op 15 code with the E-PM2 code to confirm the shell bridge was removed.
7. **The BootManager call.** Find the call site that invokes slot 0 (Usr2 0xFFFFFF) of the 0x7EC90B30 object, to turn "overlays load at boot" from inferred to verified.

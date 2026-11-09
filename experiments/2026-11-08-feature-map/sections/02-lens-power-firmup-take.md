# 02 — Lens, power, firmware update, shooting control, strobe, files

Scope: block 0 runtime ~~0x7E521020–0x7E621020~~ 0x7E521133–0x7E6211E0 (the 1-MB window on function edges: the lens function 0x7E520E2D ends at 0x7E521132 and the fcs function 0x7E620C6F at 0x7E6211E0) (L1 2026-11-09), plus the code these tasks call elsewhere (FIRMUP_LED at 0x7E880xxx, boot task 0x7E503DD4, lens debug shell 0x7E524xxx). E-PM2 v1.6.

**Labels.** **verified** = I read the disassembly or bytes and they show it. **inferred** = from strings, names, layout or consistency only.

## Overview

| Area | Main code | Tasks (entry) | Notes |
|---|---|---|---|
| Firmware update (card) | 0x7E5434EA–0x7E544A9F (`[firmup]` module) and 0x7E8808C0–0x7E880E84 (result/LED) | FIRMUP_CLI 0x7E54350E, FIRMUP_SRV 0x7E54398B, FIRMUP_LED 0x7E880CDD | Fully traced: file table, package format, descramble, checksum, write order |
| Firmware update (USB / menu) | 0x7E67EBC5–0x7E67EF5A (`api_firmup_*`), 0x7F091DF0, 0x7F092322 (`[TPCFirmup]`) | — | Sends requests to the same FIRMUP_SRV queue |
| Lens | 0x7E51BF67–0x7E538C1D | LENS_MAIN 0x7E51BF67, LENS_ASKDATA 0x7E51F77D, LENS_FIRM_UP 0x7E52FD56, LENS_FLASH 0x7E53086F, LENS_FOCUS_LIMIT 0x7E532218, ZOOM 0x7E538D9B | Server tasks on Oimf queues; big `lens` debug shell names the protocol |
| Battery / power | 0x7E539254–0x7E53A981 | BCHK_MAIN 0x7E53A1D0, BCHK_BATT 0x7E53A3CC, PWR_STANDBY 0x7E53A4A4 | Damage reporting at 0x7E53A76C |
| Body stabilizer ("BC") | ~~0x7E53BAAD~~ ~~**≤0x7E53AEA9**~~ **0x7E53AEA9**–0x7E542B4E (D3 2026-11-09: BC starts exactly at 0x7E53AEA9; 0x7E53A981–0x7E53AEA8 before it is the `dbg` debug-log module: 0x7E53A981 is its init (← boot 0x7E44A043; it takes one 16 KiB `large` heap block 0x7E507325 as the log buffer), 0x7E53A9C8 its `start/stop/flush` shell, and 0x7E53ABE3 is called by the recorder 0x7E426D4B; 15b §7) (BC code starts at or before 0x7E53AEA9: the BC init 0x7E53D90C calls 0x7E53AEA9, and BC_MAIN 0x7E53D96D → 0x7E53DF10 → 0x7E53AEC5 → 0x7E53B456, the command dispatcher (cmds 2–255, table 0x7E7444C4); the `dbg` shell 0x7E53A9C8 (01 §3) lies just before it) (C3 2026-11-09) | BC_MAIN 0x7E53D96D | **Not battery**: BC = stabilizer controller (strings `stab.*`, `bc_stab`) |
| Shooting control | 0x7E58204D–0x7E59A3EC; the TAKE module starts at its init 0x7E581FB0 (only caller Usr0 0x7E503DD4; 14b §1) (D2 2026-11-09) | TAKE_MAIN 0x7E58204D, TAKE_EXPOSE 0x7E5829E8, TAKE_FOCUS 0x7E5881D9, TAKE_FUNC 0x7E595527, TAKE_FUNC_CP 0x7E5996F8 | Command tables decoded |
| Movie AF | 0x7E5ED006–0x7E611F25 | FCS_MOVIE 0x7E610A65 | `fcs_lens_mfts_*` |
| Strobe | 0x7E5D8E94–0x7E5E2419 | STB_SEQ 0x7E5D8E94, STB_EXTERNAL 0x7E5DCA31, STB_CHARGE 0x7E5DFF5E, STB_ASSIST_FUNC 0x7E5E1E94 | |
| Files / DCF / Eye-Fi | 0x7E5ABE5B–0x7E5C8B40 | DCFPROC_SUB 0x7E5B34CE, EYEFI 0x7E5C1981, FILECLBK 0x7E5C1B4E, FILEFGND 0x7E5C4E90 | |
| No strings | 0x7E55F9B6, 0x7E57F914 | IMG_PRECON, WB_MOV | IMG_PRECON = pixel-defect (Pixel Mapping) correction from the PIXELDEFECT prm lists, part of the IMG library (13a §3.2) (D1 2026-11-09); overstated: cmd 4 (0x7E580A54) also computes channel gains, disputed until the D2 deep dive (C2 2026-11-09). **Resolved (D2 2026-11-09):** cmd 0 is pixel-defect correction; cmds 1–4 are WB/colour calibration (0x7E55FE1E/0x7E55FF91/0x7E55FFA3 call the WB module; cmd 4 0x7E580A54 reads prm 0xAA92/0xAAA2/0xAAB2 = `PRM_CAM_SPECTRUM_STL_R/G/B` through table 0x7E78F170; 14b §3). ~~WB_MOV not mapped~~ WB_MOV 0x7E57F914 is the task of the unnamed WB (white balance / colour) module 0x7E579C34–0x7E581FAF (14b §3) (D2 2026-11-09) |

Helpers used below (all **verified** by their own strings or code): 0x7E4263E5 = debug print(a0=str); 0x7E50652F = debug print str + hex value; 0x7E4492B9 = `OlyQeWr` (queue write); 0x7E449218 = `OlyQeRd`; 0x7E4490AF = `OlyEvWt`; 0x7E449030 = `OlyEvSt`; 0x7E449541 = `OlyTaSt` (start task); 0x7E449621 = `OlyTaSE` (exit task); 0x7E449605 = `OlyTaSS` (sleep); 0x7E4262C5 = get time; 0x7E500E40 = `strncmp(a0,a1,d0)`; 0x7E50689F = Oimf message send (d0 = target id, d1 = command; strings `Oimf>>qwrite`); 0x7E44F197 = flash write (`write_flash_*_error` strings), args a0 = dest, a1 = src, d0 = size, d1 = mode.

---

## 1. Firmware update

### 1.1 How card update mode is entered (boot)

- The user start task 0x7E503DD4 (strings `Usr0`, `[usr]firmup`, `USTART1`) calls 0x7E5436D1 at 0x7E5045F4 and keeps the result in d2. At 0x7E504A59: if d2 == 1 it prints `[usr]firmup` and starts task FIRMUP_CLI (id at 0x7E43E9A0). Otherwise it calls 0x7E54374C, 0x7E5437AC and starts USTART1 (normal boot). **verified**
- 0x7E5436D1: calls 0x7E544A1B (SCPU/PWM init; clears 0x6050413C/D). It then reads a "reboot flag" from 0x7E544AA5. **That function is `clr d0; retf`, so it always returns 0.** The `[firmup]REBOOT SYSTEM UPDATE` (flag 3) and `REBOOT USER UPDATE` (flag 4) branches are dead code in v1.6. **verified**
- The real decision is 0x7E544A6F. It returns 1 (card update) when `table[poweron_factor]` is 12, 0x01000002 or 0x01000001 **and** byte 0x602A9B54 == 0; otherwise it returns 2. poweron_factor = u16 at 0x604154E6 (read by 0x7E45D407; the same variable is printed as `poweron factor` by 0x7E45D8C2). The table is at 0x7E73522C (0x7E50B1A7 indexes it). **verified**
- Which physical power-on cause (key combination) those factor values mean is **not decoded**. 0x602A9B54 is cleared by 0x7E505694 when 0x7E509CA3(4) == 0 and byte 0x604154E9 != 9. **verified (code); meaning inferred: a key held at power-on.**

### 1.2 FIRMUP_CLI (0x7E54350E): find and load files

Order of operations, all **verified**:
1. Get start time. File-system init 0x7E5434EA. If it fails: `[firmup]File Init Err.` and fail screen 0x7E880A19(3,3).
2. Mount 0x7E5437B0(0, 1800). If it fails: `[firmup]Mount Err:` and 0x7E8809D5 (exit FIRMUP_CLI, start USTART1 = normal boot).
3. Loop over **9 entries of 28 bytes at 0x7E745E80**. For each entry, 0x7E543755 builds a load request {directory name `"DCOLYMP    "` (0x7E746095, an 11-byte space-padded 8.3 name; where on the card it is looked up — root or elsewhere — is not traced), pattern, timeout 1800, buffer, max size} and calls the loader 0x7E5437F0 for each pattern in turn. Results 0x0E00 and 0x0E0C mean "not found, try next pattern" (**inferred** meaning, verified control flow). The first pattern that loads wins.
4. If a file loaded: `[firmup]...Binary file Hakken !!!!!` ("found") and its size. LED mode 1 (0x7E880BF2(1)). Message to FIRMUP_SRV queue (id at 0x7E43EDC8) {buf, size, flag = entry byte +12 (always 0), reply queue, type}; wait for the reply (`OlyQeRd`). A nonzero reply → fail screen 0x7E880A19(3,3).
5. After all entries: if at least one file was processed → print `[firmup] Time` and success screen 0x7E8808C0(3,2). If none → 0x7E8809D5 (normal boot). The task never returns (tail loop prints `[firmup]Are?.`).

Every file is loaded to the same buffer **0xA0900000** (a3 = 0xA0900000 + entry offset 0). **verified**

**File table** (entry field +16 is a RAM pointer to a list of pattern pointers; field +20 = count; +4 = max size; +24 = type). RAM 0x602AA8B8… maps to the ROM copy at 0x7E8DAD78… (constant offset 0x1E6304C0). **inferred**: every pointer/count pair then lands exactly on the zero-separated groups of the pattern list at 0x7E8DAD78, and 0x602AA910 (a FIRMUP_LED flag) lands on the byte after the list.

| # | Patterns (in search order) | Max size | Type → SRV handler |
|---|---|---|---|
| 0 | `S101????BIN`, `S100????BIN` | 0x60000 | 2 TYPE_FIRMUP_SYS (boot block) |
| 1 | `A101????BIN` | 0x100000 | 0 TYPE_LANG |
| 2 | `M101????BIN`, `M100????BIN` | 0x20000 | 5 TYPE_EXTMOD (stabilizer "BURE") |
| 3 | `V101????BIN`, `V100????BIN` | 0x1900000 | 0xA TYPE_SOUND |
| 4 | `D101????BIN`, `D100????BIN` | 0xA00000 | 0xE TYPE_C3D |
| 5 | `T101????BIN`, `T100????BIN` | 0x2C00000 | 0xF TYPE_PIC |
| 6 | `E101????BIN`, `G101????BIN`, `H101????BIN`, `W101????BIN`, `E100????BIN` | 0x5000000 | 1 TYPE_FIRMUP_SYS_IGAI (main firmware package) |
| 7 | `DATE????BIN`, `PICTURE1JPG` (count 2; `PICTURE2JPG` is in the list but not searched) | 0x4000000 | 0xB TYPE_FIRMUP_DATE |
| 8 | `N101????BIN` | 0x2C40 | 7 → TYPE_DEFAULT (nothing written) |

`E101` = E-PM2 body package (**inferred** from the camera's own firmware name OLY_E_101). Meaning of G/H/W/E100 variants: not known.

### 1.3 FIRMUP_SRV (0x7E54398B): dispatch

Waits on queue 0x7E43EDC8. The message type indexes a 17-entry jump table at **0x7E7469E0**. **verified**

| Type | Handler | Action |
|---|---|---|
| 0 LANG / 0xA SOUND / 0xE C3D / 0xF PIC / 0x10 GPS | 0x7E543B57 / B87 / BB7 / BE6 / C15 | Package worker 0x7E543DDE(buf, size, mode 0) |
| 1 SYS_IGAI | 0x7E543A44 | Worker, mode 0 |
| 2 SYS (boot) | 0x7E543A74 | 0x7E4307CD(0,4); `bml_format_status` = 0x7E451829(0,1) (error → `FIRMUP_SYS_REFORMAT_ERROR`); then 0x7E880B73: checksum type 0 + flash write to **0x80000000**, mode 1 |
| 3 FIRMUP_CHECK | 0x7E543CEF | Worker, mode 2 (descramble + check, **no write**) |
| 4 FIRMUP_USBUP | 0x7E543D1C | Worker, mode 1 (write only, no per-section descramble) |
| 5 EXTMOD | 0x7E543C4E | Only if stab type 0x604F3464 == 1 (else `NON_STAB`): descramble+checksum, then 0x7E5449E7 → stabilizer update 0x7E54238D |
| 8 LENS | 0x7E543AE9 | 0x7E5448FB descramble+checksum, then 0x7E5449CE → Oimf to LENS_FIRM_UP queue (id 0x7E43ED20) |
| 9 STB | 0x7E543B1D | Same, then 0x7E5449B3 → Oimf to strobe module (id 0x7E43ED8E, cmd 0x1000) |
| 0xB DATE | 0x7E543CBA | 0x7E44F197(dest 0x40140000, src buf, size, mode 0). **No descramble, no checksum.** |
| 6, 7, 0xC, 0xD | 0x7E543D5D | `TYPE_DEFAULT` |

After the handler (0x7E543D6A): if message flag == 1 → result screen (success 0x7E8808C0(4,2), fail 0x7E880A19(4,3)), which does not return. If flag == 0 → reply to the sender. FIRMUP_CLI sends flag 0; the menu lens/strobe path (1.7) and USB "UpdateInitiate" send flag 1. **verified**

### 1.4 Package format (64-byte section headers)

The body package is a chain of up to 32 sections. Parser 0x7E506C33: for each section, data size = word +12, section length = size + 64; it stops when the running total reaches the file size or after 32 sections; it writes a zero terminator entry. It returns error 0x3321 only when the total exceeds the file size **and** 32 sections were read. **verified**

Header field names come from the lens dump 0x7E53053F (`maker_code`, `fw_kind`, ...); the offsets are its load instructions. **verified**:

| Off | Size | Name | Body updater use (verified) |
|---|---|---|---|
| 0 | 1 | maker_code | Must equal `"O"` (strncmp, length 1; length 3 if byte 22 == 1) — 0x7E506C83, error 0x3202, print `OLY or O jya Nai` |
| 1 | 1 | fw_kind | `E`,`A`,`V`,`T`,`D`,`L`,`F`,`M`,`Q` (others: `USER_NASHI!`, skipped) |
| 2 | 2 | id | Read big-endian (0x7E506C06). Must be 0x1010; kind `E` also accepts 0x1000. Else error 0x3202 |
| 4 | 2 | hw_version | not read |
| 6 | 2 | fixed | not read |
| 8 | 4 | start_adrs | Flash destination of the section |
| 12 | 4 | size | Payload size |
| 16/17 | 1/1 | minor/major_version | **not read** |
| 18 | 2 | extension | not read |
| 20 | 1 | kind | Sub-type for `E` |
| 21 | 1 | flag | 1 = scrambled |
| 22 | 10 | reserved | byte 22 picks maker compare length |

**No version (downgrade) check exists in the body path**: the worker 0x7E543DDE only calls accessors for bytes 1, 2–3, 8, 12, 20, 22 and the maker compare. **verified for this code path.**

Kinds and the bit each sets in the worker's "found" mask (a duplicate kind → `TOO MANY … FIRM FOUND`, error 0x3321). **verified**:

`E` sub 0 USR(1), 1 OSD(2), 2 PIC(4), 3 WAV(8), 4 FRAME(0x40), 5 ADJSLF(0x20), 6 ARTFIL(0x2000), 7 NOREXE(0x4000), 8 C3D(0x8000), 9 GUIDE(0x400), 10 BEAUTY(0x800), 11 GPS(0x10000). `A` LANG(0x10), `V` WAV(8), `T` PIC(4), `D` C3D(0x8000), `L` LENS(0x100), `F` FLASH/strobe(0x1000), `M` BURE(0x80), `Q` GPS(0x10000).

### 1.5 Descramble and checksum

- **0x7E5448FB** (per section, modes 0 and 2): if header byte 21 == 1 → `[firmup]DeSecramble` → 0x7E54343F. Then checksum 0x7E54337D with type 1. **verified**
- **0x7E54343F(hdr, len)**: error 0x3201 if `len & 0xF` != 0 or len <= 64. It descrambles bytes [hdr+32, hdr+len−32): first 0x7E543478 permutes the bytes of each 16-byte block, then 0x7E543467 inverts (NOT) every 32-bit word. **verified**. Permutation (input bytes b0..b3 of each word → output):

| Word in block | Output bytes |
|---|---|
| 0 | b1 b3 b0 b2 |
| 1 | b2 b0 b3 b1 |
| 2 | b3 b2 b1 b0 |
| 3 | b1 b2 b0 b3 |

- **0x7E54337D(mode, ctx)**: **verified**
  - Type 1 (sections): the 5 words at hdr+0..19 must equal the 5 words at section end − 32 (a header copy in the trailer), else 0x3202. Then the 32-bit sum of all words of the section (size+64 bytes) must be 0 (0x7E506BEF).
  - Type 0 (boot `S` file, via 0x7E880B73): 32-bit word sum over 0x60000 bytes must be 0. Only in mode 2 are 2 bytes at +0x5FFF8 also compared with `"BOOT"` (0x7E746982); FIRMUP_SRV calls it with mode 0, so that compare is skipped.
  - A sum failure returns 0x3210 (`A`), 0x3211 (`E`), 0x3212 (`L`), 0x3213 (`F`), else 0x3203.

### 1.6 Write order (worker 0x7E543DDE, modes 0 and 1 only)

Writes are done after all sections pass, in this fixed order (**verified**): LENS (to LENS_FIRM_UP) → FLASH (to strobe module) → BURE (only if stab type == 1; else `BURE_FUZAI`) → LANG → ADJSLF → FRAME → WAV → GPS → C3D → GUIDE → BEAUTY → PIC → ARTFIL → OSD → USR → NOREXE → `Boot ha yaranai zeyo` ("boot is not done"). Each flash write: dest = 0x7E45DB37(start_adrs) (maps 0x40000000–0x40FFFFFF and 0x60000000–0x7FFFFFFF to `0x80000000 | (a & 0x3FFFFFFF)`), src = the whole section **including its 64-byte header**, size = size+64. Flash mode = 8 for USB writes of non-LANG parts, else 1 (0x7E544954). Then success → 0x7E8808C0(4 if USB else 3, 2); failure → 0x7E880A19(4 or 3, 3).

The USB flow (inferred from order): `[TPCFirmup]FirmwareCheck` sends type 3 (check, descrambles in place, reply) at 0x7F0923E4; then type 4 (write) with flag 1 at 0x7F091EE4. **verified** message bytes; the shared-buffer reasoning is **inferred**.

### 1.7 Menu path for lens and strobe (camera UI)

`update_firmware()` 0x7EAB3195 calls `api_firmup_Check_FirmwareUpdate` (body, 0x7E67EBC5 → 0x7F0890F3), `…_Lens` (0x7E67EDE1) and `…_Strobe` (0x7E67EC2C), then `Execute_…`. The lens execute 0x7E67EE35 loads `DCOLYMP`/`L???????BIN` to 0xA0900000 and sends type 8, flag 1 to FIRMUP_SRV; the strobe execute 0x7E67ECB7 does the same with `F???????BIN`, type 9. **verified**. The body execute 0x7E67EBDF first sends commands 4 and 7 to the BCHK_MAIN queue (0x7E43ECD0; cmd 4 = battery check, cmd 7 = stop polling) and then command 3 to queue 0x7E43EDAE. **verified** message targets; "battery check before update" is **inferred**.

### 1.8 Result screen, LED and power-off

- **LED** 0x7E880BF2(mode) drives **PWM channel 0** (`per_pwm_open/stop/iocontrol/start` 0x7E466887/0x7E46693B/0x7E4668E1/0x7E46690E). **verified**:

| Mode | Value | PWM setup | Use |
|---|---|---|---|
| 1 | 255 | {1, 16065, 100, 0} then start | while each file is written (inferred: steady on) |
| 2 | 250 | {1, (15686/(1000/v))/4 then `udf00 255`, 50, 0} | success |
| 3 | 100 | same formula, 50 % duty | failure |
| 4 | 50 | same formula | not used here |
| 5 | 0 | stop | off before power-off |

  Mode 2 vs 3 gives a different blink period (exact Hz **inferred** unknown; `udf00` semantics unknown).
- **Success** 0x7E8808C0 (`Seikou`/`Saikou`) and **fail** 0x7E880A19 (`Shippai`): arg0 = 3 → LED only; arg0 = 4 → draw images 0x0F01/0x0F02 at 640×480/320×240 via 0x7E940380 (**inferred**: on-screen OK/NG pictures). Fail also calls `subcpu_beep(2)` 0x7E544A35 → 0x7E544A61, **which is an empty `retf` stub: no beep.**
- Both end in 0x7E880B22 (`Owariyade`, "it's over"): wait in 0x7E880DD9 until the switch read by 0x7E45D444 changes (string `SW_ON`; **inferred** power switch), LED off (if 3), then 0x7E880DCD → 0x7E45D390 (**inferred** power off), then an infinite loop at 0x7E880B71. **verified** control flow.
- **FIRMUP_LED task** 0x7E880CDD waits on event flag id 0x7E43EC22: flag pattern 0x1 → GPIO 0 off; 0x2 → toggle GPIO 0 every 250 ms; 0x4 → every 100 ms; 0x8 → on (exact compares of the pattern, bits 0–3) (audit 2026-11-09). **verified**. No code in block 0 loads that flag id except this task, so it looks dormant (**inferred**).

### 1.9 Lens and stabilizer update details

- **LENS_FIRM_UP** 0x7E52FD56: reads queue 0x7E43ED20, runs 0x7E52FDC3 → 0x7E52FE8C, replies. 0x7E52FE8C stores the header pointer at 0x604F9390 and packet count `(size>>7) + (size & 127)` at 0x604F9394 (128-byte packets; the formula is literal). It picks lens protocol type 1 or 2 (0x604F943E, from 0x7E51FDB4) and runs step callbacks 0x7E52FFB3 / 0x7E530020 / 0x7E53008E / 0x7E530103 sending lens commands 0/3/4/5 (or 0x1000/0x1003/0x1004/0x1005 for type 2). ~~Each step retries up to 3 times, then fails with 0x6608/0x6601/0x6604/0x6605.~~ **Order and error codes (D3 2026-11-09, V; 15b §5.3):** the start 0x7E52FE8C sends **cmd 7 first** (0x1007 for type 2; error 0x6610 if the protocol type is unknown), so the order is **7 → 0 → 3 → [4 → 5 → compare → 6] × packets → 1**. Each step function handles the reply of the previous command and then sends the next one. On a failed reply it re-submits the same request (retry count 0x604F9396), and after 3 retries it stores its error code in 0x604F943C and aborts (0x7E53043E). So each code belongs to the command whose reply failed: **0x6608 = cmd 7** (step 0x7E52FFB3), **0x6601 = cmd 0** (0x7E530020), **0x6604 = cmd 3** (0x7E53008E), **0x6605 = cmd 4** (0x7E530103), 0x6606 = cmd 5 (transport) and 0x6609 = three read-back mismatches (0x7E530171, count 0x604F9398), 0x6607 = cmd 6 (0x7E53023E), 0x6602 = cmd 1 (0x7E53030A). There is no 0x6603 (D3 2026-11-09). **The chain does not end at cmd 5 (C3 2026-11-09, V):** cmd 5's next step 0x7E530171 checks the reply (0x7E5303E1); on a match it sends cmd 6 (0x1006, next 0x7E53023E), on a mismatch it re-sends cmd 4 (next 0x7E530103) up to 3 times, then 0x6609 (transport error 0x6606). 0x7E53023E advances the packet index and compares it with the count 0x604F9394: more packets → cmd 4 again (next 0x7E530103), done → cmd 1 (0x1001, next 0x7E53030A); error 0x6607 (= a failed cmd 6 reply (D3 2026-11-09)). 0x7E53030A ends the chain (error 0x6602 = a failed cmd 1 reply (D3 2026-11-09)). So cmd 4 = write packet, cmd 5 = read-back check, cmd 6 = packet accepted, cmd 1 = finish (meanings I) (C3 2026-11-09). **verified** structure; command meanings **inferred**. Globals named by 0x7E53053F: `g_lens_firmup_send_num/ng/compare`, `g_firmup_id/hw_version/version/extension/serial_num[12]/recv_data[128]/err_status/connected_info/total_send`. A `compare` and `version` field exist, so the lens side may check versions (**inferred**, not traced).
- **Stabilizer ("BC FUP")** 0x7E54238D: up to 5 tries, serial speed 57600, then 19200, then 9600 (0x60504118); 0x7E5423E2 init (`ID CHECK..` 0x7E542802), 0x7E542A55 UPDATE → ERASE 0x7E542A86 → WRITE 0x7E542AC3 → VERIFY 0x7E542AFE, END 0x7E542A17. Data = section+32, length size−64 (0x7E5449E7). **verified**
- **Strobe firmup** in the strobe module: 0x7E5DF13A (`STB FIRM UP START/TRANSMIT/END/ABORT`, header dump), 0x7E5DF5C7 (`STB_FIRMUP_FW_VER`), 0x7E5DFBF0 (`firm_version(BCD)`). **inferred** from strings.

---

## 2. Lens communication

- **Tasks** (all **verified** as queue servers: read Oimf queue → handler → reply; LENS_FOCUS_LIMIT does not reply (audit 2026-11-09)): LENS_MAIN 0x7E51BF67 (queue 0x7E43ED1E, handler 0x7E51BFBA), LENS_ASKDATA 0x7E51F77D (0x7E43ED1C → 0x7E51F7C5), LENS_FLASH 0x7E53086F (0x7E43ED22; cmd 1 → 0x7E5308E0, 2 → 0x7E530DEF, 3 → 0x7E531540), LENS_FOCUS_LIMIT 0x7E532218 (0x7E43ED24 → 0x7E532240; also called from TakeFcs `limit:` 0x7E592D75), ZOOM 0x7E538D9B (waits event mask 0x02 = bit 1, `btst 2` (audit 2026-11-09), then queue 0x7E43EDDE → 0x7E538E60 if 0x7E5224F4() else 0x7E538D76).
- **Debug shell** `lens …` dispatcher 0x7E524C76, help 0x7E525348. It names the protocol (**inferred** from strings): `aperture` (modes 0x01 OPEN, 0x21 AV_ABS, 0x22 AV_ABS_RESET, 0x50 STOP; 0x7E525994), `focus` (LENS_FOCUS_MODE_* 0x0000–0x8007: RESET, DEF_AF, PLS_ABS, DST_ABS (value/5 mm), PLS_OFST, LIMIT, CAF_LIMIT_TIME, SET_ACT_LV, LAF_* …; 0x7E525B44), `askdata` (LENS_ASKDATA_MODE_* 0x00–0x62: 43RDSVER, FIRMVER, CONFDATA, SHADING, LENSSTOP, CHANGESPEED, LAF, HIGH_SPEED, …_A for adapter, M_DATA, M_DIST, M_SYNC, M_STATUS_LV, M_WOB_MAG, M_3D, M_EZ, ASK_FUNC_PRIVATE …; 0x7E525DDF), `reset` (LENS_SETUP/SETDOWN/SLEEP_SHIFT/SLEEP_RETURN/COM_PAUSE/COM_RESTART), `sync`, `timing`, `ssc` (command log 0x7E535745), `trouble` (simulated faults: still disable, manual/electric sink, step out, actuator), `ois`, `current`, `firmup`, `flash read [address]` (0x7E52958B: reads lens flash memory — **inferred** LENS_FLASH = lens ROM access, not a flash gun).
- **Data asked from the lens** (`lens data` 0x7E526702 and dumps 0x7E5268F4–0x7E528D01): LENS_INFO_STATE (zoom/focus encoder, object distance, av_effect), CHARACTER (name, focal_length_w/t, serial_number, firm_version), CHARACTER_ZM (per zoom step: focal_length_center, av_official/av_effect min/max), MAKERNOTE, SHADING, DISTORTION (c3/c5/c7), FOURTHIRDS (version, kbps), IS (flact_k*, lat_mag_k*), LAF, SYNC (wobble/aperture speeds), LIFTM, WOB_MAG, 3D, EZ (power zoom encoder), PANA/OLY private flags, LENS_OIS, CURRENT_CONSUMPTION (still/movie, units 100 mA). Adapter variants `_A`. **inferred** (strings only).
- **Power zoom**: `[lens_zoom]` dump 0x7E538B0C prints focal_length_official/effect current/min/max (and `_a` adapter). **inferred**.
- **Movie AF / `fcs_lens_mfts_*`** (FCS_MOVIE area): get_lens_rslt 0x7E5ED006/0x7E5F6C2D/0x7E609DFA, iaf_chg 0x7E609DFA, set_speed 0x7E60A3DE, scan_chg_speed(_multi) 0x7E60BC39/0x7E60B908, stop_lens 0x7E60C919, stop_scan_ft 0x7E60CDE5, stop_lens_wob 0x7E60D20F, stop_lens_force 0x7E60D5B9, scan_lens 0x7E60D90F, scan_only_lens 0x7E60DFF4, scan_lens_wob 0x7E60E308, move_lens 0x7E60E648, move_lens_ofset(_vd/_vd_sim) 0x7E60EAB7–0x7E60EF1E, chk_lens_stop(2) 0x7E60F2DC/0x7E60F7ED. FCS_MOVIE task 0x7E610A65 (`FCS_QUEUE_RECIEVE`, `FCS_RES_QUEUE_WRITE`). **inferred** from strings (functions placed by string refs).
- Lens state events (0x7E520BB3/0x7E520C46): STATE_FOCALLEN, FOCUSRING, LENSDIAL, LENS_TROUBLE, RANGE_FOCUS, LENS_IS_SW, CAMON/OFF_AF_STOP, LENSCUSTOM. **inferred**. **Lens status word 0x604F6580 (coverage C4, verified code) (L1 2026-11-09):** bit 28 is latched into 0x604F8F50 (`and 0x10000000; lsr 28` at 0x7E520422) and returned by the getter 0x7E52233A (only for a new-protocol lens, 0x7E52237F/0x7E52239E); FCS 0x7E6106FD and SDET 0x7E6634F7/0x7E663663 treat a non-zero value as "AF not available" (inferred: an MF-clutch state). Bit 29 (tested at 0x7E520799, together with bit 1 and a mask) sends event 0x02001516 when it sets and 0x02011516 when it clears (the CAMON/CAMOFF_AF_STOP pair) to 0x7E520E2D.

## 3. Battery, power, damage

- **BCHK_MAIN** 0x7E53A1D0: reads queue 0x7E43ECD0 with a **1000 ms timeout**; on timeout, if polling is enabled (0x7E53A37F) → 0x7E53A472 (periodic check). Commands: 3/4/5 → 0x7E53A2E9 (check with a mode byte), 6/7 → enable/disable polling (0x7E53A376(1/0)), 8 → 0x7E53A485. **verified**. Debug shell 0x7E539672 (`vbat`, `vac`, `tmp`, `pbhtmp`, `get_src`/`set_src` ("1=AC, 2=BAT") (audit 2026-11-09), `level`, events `inter_start_rec`, `before-rec`, `before-fat`, …). Event names `EBCHKBATT`, `EBCHKAD`, `EBCHKTIMER` at 0x7E53A049. **inferred**.
- **PWR_STANDBY** 0x7E53A4A4 (`QPWRSTANDBY`): command 1 calls **0x470010DE**, command 2 calls **0x4700118A**: code outside block 0. Sequence: audio off (`AUD_OFF`), Oimf notices, display off (0x7E539FEC `[PwrS]Err>>dis_dsp`), `[pwr_standby]:start`, …, `end`, `AUD_ON`. **verified** calls; "low-power standby run from on-chip RAM at 0x47000000" is **inferred**.
- **Damage reporting** 0x7E53A76C(code): if the code is in the list at **0x7E744084** (69 u16 codes) it reports; if it is also in **0x7E744110** (29 codes) it reports "Damage OFF", else "Damage ON"; then 0x7E53A819 (settings writes). 20 callers incl. BC_MAIN and TakeFcs. Shell `damage` 0x7E53A700. **verified**.
- **BC_MAIN** 0x7E53D96D is the **body stabilizer controller** (strings `stab.standby/detect/correct`, `--bc_main--`, `--bc_stab--`, `--bc_stage--`, `bc_ssc`, `siotx/siorx`, `sc_get_stabtype`), **not** battery. It calls the damage reporter. **inferred** (strings), callee **verified**.

## 4. Shooting control (TAKE_*)

> **Correction (13e, checked by coordinator, 2026-11-09).** The TakeExp/TakeFcs tables (0x7E791478 / 0x7E7928B0) are 32-slot hash tables keyed by **cmd + 1**: the dispatchers do `inc d1` before the lookup (0x7E582A48, 0x7E588321). **Every command number in this section is one too high.** For example, 0x1xx keys are commands 0x100/0x101 (lock_start/lock_end), and F007's 0x401 is `release_ready_end`. Use the corrected list in `13e-mcon-sequencers.md` §4.

- **TAKE_EXPOSE** 0x7E5829E8 and **TAKE_FOCUS** 0x7E5881D9 dispatch commands through 32-slot open-addressing hash tables `{u32 key, ptr handler}` at **0x7E791478** and **0x7E7928B0**; key = cmd + 1, key 0 = empty slot → default handler (0x7E582DFC) (D1 2026-11-09). Each handler prints its name. **verified**:

| Key (= cmd + 1) (D1 2026-11-09) | TakeExp | TakeFcs |
|---|---|---|
| 0x001/2/3 | mode_start / mode_end / – | mode_start / mode_end / mode_update |
| 0x101/102/103 | lock_start / lock_end | lock_start / lock_end / lock_start_end |
| 0x201/202/203 | preview_start/end/update | panorama_start/end |
| 0x301/302 | panorama_start/end | release_ready_start/end |
| 0x401/402 | release_ready_start/end | release_idle_start/end (0x404 idle_ready) |
| 0x501/502/504 | release_idle_start/end/ready | release_take_start/end |
| 0x601/602 | release_take_start/end | take_continue_start/end |
| 0x701/702/703 | 0x702 release_end | lv_start/end/update |
| 0x801/802 | take_continue_start/end | mf_start/end |
| 0x901/902/903 | lv_start/end/update | 0x901 iaf_restart, 0x902 iaf_pause |
| 0xA01/A02/A05 | iaf_start/end/end_post | 0xA01–A04 movie_start/end/update/ready |
| 0xB01/B02 | movie_start/end | – (0xE02 release_end) |

  Reading: 0x1xx = half-press lock (AE/AF), 0x4xx–0x7xx = release sequence, 0x8xx continuous, 0x9xx live view. **inferred**.
- **TAKE_MAIN** 0x7E58204D (`.exec(%d)`, `.post(%d)`, `--takeseq--`); **TAKE_FUNC** 0x7E595527 and **TAKE_FUNC_CP** 0x7E5996F8 (`--take_func--`, job/res_qname/through_*). **verified** strings; roles **inferred**.
- **AF types** (0x7E593187): tracking, clip, t-face, special, face, spot, multi, group. Special AF frame (enable/mag/x/y) 0x7E59356C; fcs packet fields (mode_focus, af_area, saf_mf, release priority S-AF/C-AF, drive, through_zoom) 0x7E594A50; C-AF initial position 0x7E607180. **inferred**.
- Continuous trace (`[TakeExp]continue trace 1st/2nd/af/ae/aeaf`) 0x7E58450A–0x7E584C97; backlight/face logic (`gyako` = backlight, `bv_face_under`) 0x7E585978. **inferred**.

## 5. Strobe

- **STB_CHARGE** 0x7E5DFF5E (`stb_icharge …`): charging of the internally-powered strobe; state dump 0x7E5E0549, A/D check `ERR STOP/OK %3d [A/D]` 0x7E5E0896. **STB_EXTERNAL** 0x7E5DCA31 (`stb_external.c`): hot-shoe flash detect/remove by ID (0x7E5DD174), mode/state events (0x7E5DDEA6–0x7E5DE11A), serial `TX_DATA/RX_DATA` (0x7E5DC0F7), LED video light (0x7E5DDAD8), strobe firmup (1.9). **STB_SEQ** 0x7E5D8E94: firing sequence. **STB_ASSIST_FUNC** 0x7E5E1E94: calls illuminator 0x7E5E0FA4, popup 0x7E5E1B45 (`auto pup status`), charge control 0x7E5E14D8 (`stb internal chrgrge on/off/restart/pause`, low/normal mode) — callees **verified**, roles **inferred**.
- **Red-eye pre-flash (coverage C4, verified code) (L1 2026-11-09):** STB_SEQ 0x7E5D8E94 runs `stb_expose` 0x7E5D0E12 for message type 1 and the pre-flash train 0x7E5D6726 for type 16. The train fires N = prm 0xD4D2 (54482) flashes from the external or internal strobe (0x7E5D67E6 → `strobe_light_exec` 0x7E5E2419); each one waits for a 33-ms soft timer that sets the event `STB_REDEYE` (id at 0x7E43EBDA). Then it waits (900 − 33·N) ms, so the train always lasts about 0.9 s (inferred from the arithmetic).
- Debug: `stb …` (0x7E5DB015: init, con/coff/cpau/cres, cloop, cset (stop/ok A/D thresholds), manual, full, redeye, popup (1 manual, 2 auto, 11/12 via queue), adget, expose …), `stb ext` (EEPROM read/write, RESET, READY_VOLTAGE …), `stbd prm 1|2 val` sets **PRM_STB_TEST_VAL_1/2** (0x7E5DADE1). **inferred**. E-PM2 has no built-in flash; the "internal" path most likely serves the bundled clip-on FL-LM1 (**inferred**).

## 6. Files, DCF numbering, Eye-Fi

- **DCF init** 0x7E5AF0EA: 548 node pool, default folder number 100 with suffix `xxxOLYMP` (0x7E793BDC) and default file name `P1010001JPG` (0x7E793C34); path format `%c:\DCIM\%s\%s` (0x7E5AF8D6). **verified** constants; naming rule P + month (1–C) + day + number is **inferred**.
- **DCFNUM commands** (0x7E5C816A): MOUNT, RECNUM, RECNODE, FORMAT, DELMOUNT, UNMOUNT, RECNUM2, RECCANCEL, CLEARFLASH, RECABORT. Settings `PRM_DCFNUM_FOLDER/FILE` 0x7E5C6065; `dcfnum_exec` 0x7E5C6CB4; shell `dcfnum/resetnum/eyefi` 0x7E5C5750. **inferred**.
- **Tasks**: DCFPROC_SUB 0x7E5B34CE, FILECLBK 0x7E5C1B4E (file callbacks), FILEFGND 0x7E5C4E90 (waits event, runs 0x7E5C4DD3), EYEFI 0x7E5C1981. **verified** entries; roles **inferred**.
- **EYEFI request protocol (coverage C4, verified code) (L1 2026-11-09):** the client stubs 0x7E5C0B07, 0x7E5C0B34, 0x7E5C0B60, 0x7E5C0B8C and 0x7E5C0BB9 send commands 0x200001, 0x200003, 0x200004, 0x200005 and 0x200006 synchronously (`Oimf` 0x7E50689F) to the queue whose id is at 0x7E43ED00. They return the reply word, or 0x9417 when the send fails. 0x200005 (0x7E5C0B8C) is the get-file-status request of `eyefi_get_file_status…` 0x7E5C71A1 and `api_media_Get_Eyefi_File_Status` 0x7E680A84. The receiver 0x7E5C0A7B dispatches 0x200001–0x200007.
- **Eye-Fi**: creates an `EyeFi` directory on the card (0x7E5ABE5B), validates card parameters (`Invalid EyeFiCard parameter...` 0x7E5AC0B8…), reads MAC token, `eyefi_enable_operation`/`wrap_disable` (0x7E5C715F), per-file status (0x7E5C71A1); E_EYEFI/S_EYEFI (0x7E5C0BFF). **inferred**.

## Open questions

1. Which key/power-on factors map to table 0x7E73522C values 12 / 0x01000001 / 0x01000002 (card update entry), and who sets 0x602A9B54?
2. What the `G101`/`H101`/`W101`/`E100` and `x100` variants are, and what the 0x1000 id accepted for kind `E` means.
3. `DATE????BIN` / `PICTURE1JPG` go to flash 0x40140000 with no checksum: what is stored there?
4. Lens firmup command semantics (cmds ~~0/3/4/5~~ 7/0/3/4/5/6/1; 15b §5.3 gives 7 = identify, 4 = write packet, 5 = read back, 6 = next/commit, 1 = finish, I (D3 2026-11-09)) and whether LENS_FIRM_UP compares `g_firmup_version` with the lens (downgrade guard on the lens side?).
5. `udf00 255` in the LED period formula; real blink rates.
6. Code at 0x470010DE/0x4700118A (PWR_STANDBY) lives outside block 0: which block/RAM?
7. IMG_PRECON (0x7E55F9B6) and WB_MOV (0x7E57F914) have no strings in this range; their roles need code reading. IMG_PRECON is answered: pixel-defect correction (13a §3.2) (D1 2026-11-09). Reopened in part: cmd 4 does channel-gain work (13a §3.2) (C2 2026-11-09). Answered: cmds 1–4 are WB/colour calibration, and WB_MOV is the task of the WB module 0x7E579C34–0x7E581FAF (14b §3) (D2 2026-11-09).
8. FIRMUP_LED (0x7E880CDD): is it ever started or signalled (event id 0x7E43EC22)?
9. Meaning of the 69 damage codes at 0x7E744084.

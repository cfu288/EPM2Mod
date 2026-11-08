# 10e — Connectivity re-check: accessory port, PENPAL, EVF, Eye-Fi/FlashAir, USB modes, 1394, CEC, firmware files

Method: the strict method of section 09 (code, reachability, cross-body, external only as support, audit of prior claims).

- **Labels:** **verified** = read in code or bytes; **inferred** = from names, order or layout.
- **Addresses:** E-PM2 v1.6 runtime addresses (block-0 offset = address − 0x7E421020), unless a body is named.
- **Scripts:** `$S/hidden/connectivity/` (`prmdiff.py`, `strdiff.py`, `mdiff.py`, `grp.py`, `findpat.py`). `$S` = the session scratchpad.

## Verdict table

| Feature | Prior claim | Verdict | Real status on E-PM2 | Code / English UI on which bodies |
|---|---|---|---|---|
| Bluetooth / PENPAL ("cube") | Dormant (inf). Gate 0x7E91367A needs I/O-expander input 0x1709 = 0 | **CONFIRMED, CORRECTED detail.** 0x1709 is not a raw pin. It is bit 4 of the decoded "edev" (external-device) byte, named **"Cube"**, and set only when an accessory with ID 0x0103 answers on the accessory bus | **Dormant-complete.** No firmware gate; the body has no device to answer (inf) | Code: E-PL5, E-PL6, E-P5, E-M10, E-PL7. Gone from E-M5 II and PEN-F. The PENPAL menu text is in every body's block 1 up to E-PL7 |
| "E-PM2 has no accessory port" | product knowledge | **UNRESOLVED from firmware.** No model table or config byte marks the port. The E-PM2 and E-PL5 detection code and tables are identical | — | — |
| Accessory-port menu (items 2122–2124) | Dormant (inf) | **CORRECTED.** The menu is not removed on the E-PM2. It is hidden by the **default** of info 394 (prm 0x61B1 = 0), exactly as on the E-PL5 | Hidden by default; user toggle probably in Setup > Menu Display (inf, setter not traced) | Top table byte-identical in E-PL5 |
| EVF (VF-2/VF-3 class), SEMA-1 mic, accessory strobe | Dormant (inf) | **CONFIRMED + mechanism found.** One accessory-ID scan decides all of them | Dormant-complete | Same tables in E-PL5. `EVF_TYPE_VF4` first appears in the E-PL6 |
| Macro arm light MAL-1 | — | **UNRESOLVED.** IDs 0x0104/0x0105 are decoded but have no device record | ? | — |
| Eye-Fi | Active (inf) | **CONFIRMED code. Menu visibility UNRESOLVED** | Active (inf) | All 8 bodies have EYEFI code |
| FlashAir "Connection to Smartphone" (SPC) | Active (inf) | **CONFIRMED.** A Playback-menu row (verified). Show/hide condition not traced | Active (inf) | E-P5 adds built-in Wi-Fi tasks and keeps SPC |
| USB modes / PTP types 0–6 | 4 opcode sets; menu→type and X3C open | **RESOLVED for the menu.** Storage→0, Print→1, MTP→4, generic PTP→5. **Types 2, 3 (X3C) and 6 have no requester found.** X3C identity still UNRESOLVED | Active (Storage, MTP, Print). X3C: Dormant (inf) | USB Mode menu text in all bodies |
| IEEE 1394 tasks | Stub | **CONFIRMED** | Stub | — |
| HDMI CEC | Active | **CONFIRMED code**, reachability partly traced | Active (inf) | — |
| Firmware-update files | 9 card entries (section 02) | **MAPPED.** Card files load only in boot-time card-update mode (trigger partly decoded). From the menu only L/F (lens/flash). Body package also over USB | Card mode: Hidden (service). Lens/flash via menu, body via USB: Active | — |

---

## 1. Bluetooth / PENPAL ("cube")

### 1.1 The gate (verified)

- **`cube_enabled` 0x7E91367A:** `d0 = 0x7E509CA3(0x1709)`; it returns 1 only when the result is 0. It has 22 callers. The E-PL5 has the same bytes at the same address; only the call target differs (0x7E509CC6).
- **What 0x1709 is (verified):** the status-name table at **0x7E8DA174–0x7E8DA330** holds records `{u32 id, char *name}`, e.g. (4, "O  k"), (0x100, "Trg1"). Part of it:

| id | name | id | name |
|---|---|---|---|
| 0x0501 | Hdmi | 0x1709 | **Cube** |
| 0x1705 | Micp | 0x170A | Evf2 |
| 0x1706 | Evf1 | 0x170B | Ef2C |
| 0x1707 | Ef1C | 0x170E | Evf3 |
| 0x1708 | **EMic** | 0x170F / 0x170C / 0x170D | Ef3C / **EStb** / ESbU |

- **Status group 11 = "edev":**
  - Descriptor 0x7E735628 → items 0x7E7353C0. The items are 0x1706, 0x170A, 0x170E, 0x1708, **0x1709**, 0x170C, (0), in bit order 0–6. State byte: 0x604F3BF0.
  - The debug dump 0x7E50AB0C names this byte `key_matrix_edev` (verified string ref).

### 1.2 How the edev bits are set (verified unless marked)

`ui_key_edev_chk` 0x7E50BAA6 (called from the key scan at 0x7E508FE8) works as follows:

1. **Read the accessory ID.** `0x7E464850` is part of PER_IOE_CTRL (string `PerSEFm`). It probes up to 4 bus configs at 0x7E4C7294 (`{1, 0x88}`, `{3, 0x68}`, `{2, 0x12}`, `{2, 0x1C}`). It reads a 2-byte chip ID, then maps it through 10 pairs at 0x7E4C726C (0x101, 0x102, 0x103, 0x104, 0x105, 0x202, 0x204, 0x205→0x204, 0x322, 0x23E). The result is a u16 device ID, or 0 if nothing answered.
2. **Debounce.** It counts samples against thresholds held in each record (3/10, or 50/1).
3. **Match.** It compares the ID with 7 records of 16 bytes at **0x7E7353F8** and sets bit *i* of 0x604F3BF1 when record *i* matches:

| Bit | Status | Name | Accessory IDs |
|---|---|---|---|
| 0 | 0x1706 | Evf1 | 0x0101 |
| 1 | 0x170A | Evf2 | 0x0202 |
| 2 | 0x170E | Evf3 | 0x0322 (debounce 50/1) |
| 3 | 0x1708 | EMic | 0x0102 |
| **4** | **0x1709** | **Cube** | **0x0103** |
| 5 | 0x170C | EStb | 0x0204, 0x0205 |
| 6 | – | – | 0x023E |

4. **Post the change.** It posts the new byte as a group-11 key-matrix event: 0x7E50AA1C → 0x7E50AA27, which writes a ring entry and copies the byte with memcpy 0x7E5081FA. That the consumer copies it into 0x604F3BF0 is **inferred**.

**Reader polarity (verified):**
- 0x7E509CA3 → 0x7E50B0A8 returns 1 when the state bit **differs** from the item's level byte. That byte is 1 for all group-11 items. So a status reads **0 when its device is present**.
- The audio input selector 0x7E95CDCC agrees: when 0x1708 (EMic) reads 0, it picks source 3 (an external mic). The "Micp" status 0x1705 reading 0 ORs in flag 4.
- So `cube_enabled` = "a device with ID 0x0103 (PENPAL) is attached". Calling it "active-low" was a description of this polarity, not of a pin.

### 1.3 E-PM2 vs E-PL5: is there any model difference? (verified)

- **prm ROM defaults** (`prmdiff.py`, all 6 lists). The differences are:
  - model strings 0x5DE2/0x5DF1/0x62F1;
  - 0x6551 `S0043`/`S0042`;
  - display tables 0x7572–0x7642 and 0x76E2;
  - 0x8CC2;
  - CPRAM 0x3421/0x3811/0x3821.

  **No accessory or port flag.**
- **Block-0 strings** (`strdiff.py`): only 11 readable strings differ. The E-PL5 adds the swivel strings (`Set_Disp_TFT_Swivel`, `api_user_Set_Touch_Panel_Swivel`), `key_matrix_dial`, `ErrMoniRot` and `Start_Through mode`.
- **Tables:** the group-11 list, the edev ID records and the chip map are **byte-identical** in the E-PL5 (0x7E73579C, 0x7E7357D4, 0x7E4C6F80).
- **Code** (`mdiff.py`, 0x7E508F00–0x7E50D700, constants normalised): the edev functions 0x7E50B8DE–0x7E50BD60 are identical. The differences are key-matrix/dial code, e.g. the E-PL5-only ADC range classifier 0x7E50BAC2.
- **Conclusion:** the firmware cannot tell an E-PL5 from an E-PM2 on this path. On the E-PM2, PENPAL stays off only because no ID 0x0103 ever answers the probe (**inferred**). The product knowledge that the E-PM2 has no accessory port fits this, but the firmware gives no evidence for it either way.
- **ADJ:** the service op 0x902A (0x7F080B39–0x7F080BC2) reads 0x1706/0x1708/0x1709/0x170A/0x170C and prints `cube is disable` (factory test, verified reads).

### 1.4 Accessory-port menu (verified unless marked)

- **Rows:** 0x7EFFE24A/54/5E, items 2122 PENPAL Share (268/481), 2123 PENPAL Album (270/589) and 2124 Electronic Viewfinder (269/482).
- **Tab visibility:** 0x7EDEBF67 drops the tab unless info 394 ≠ 0. Info 394 = prm 0x61B1 (MODE, u8, **default 0**). It has a mode-controller (mcon) record (#400, 2 values).
- **Reading 394:** the tab-navigation helpers 0x7EDECA27/0x7EDECBF8 and the predicate 0x7E9E91EF (vtable 0x7EC1C3E4) read it.
- **Setting 394:** no constant-id setter was found. Setup > "Menu Display" (str 168; help 491 "Choose whether to display @A00E@ menu or @A000@ menu") is the likely toggle (**inferred**; that screen is built in code and was not traced).
- **E-PL5:** the top table is byte-identical (E-PL5 0x7EFFEA28).
- **So the E-PM2 does not hide this menu by model.** It is off by default as on the E-PL5. If a user turned it on, the PENPAL and EVF pages would open but find no device (**inferred**).

### 1.5 Cross-body (verified counts in each body's block 0)

| Marker | E-PL5 | E-PL6 | E-P5 | E-M10 | E-PL7 | E-M5 II | PEN-F |
|---|---|---|---|---|---|---|---|
| `cube is disable` | 4 | 4 | 4 | 4 | 4 | 0 | 0 |
| `OLYMPUS PENPAL` | 3 | 3 | 3 | 3 | 3 | 0 | 0 |
| `EMic` name | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| `EVF_TYPE_VF4` | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

The E-M10 and E-PL7 also lack an accessory port (product knowledge) but still carry the full PENPAL stack. So **having the code says nothing about having the port**. The stack was shared until 2014 and dropped with the E-M5 II (2015).

## 2. EVF and other accessory-port devices

- **What decides support:** the accessory-ID scan in §1.2 (verified). Evf1/Evf2/Evf3 are three EVF classes (IDs 0x0101/0x0202/0x0322). Mapping them to VF-2/VF-3/(VF-4) is **inferred** from `EVF_TYPE_VF2/VF3` and `vf-2/vf-3 Version:`.
- **Display path:** 0x7E502DD6 has `OUT-EVF!`, `OUT-EVF2!` and `OUT-EVF3!`.
- **SEMA-1:** most likely `EMic` (ID 0x0102), the source-3 branch of 0x7E95CDCC (**inferred**). Value 17/18/19 in prm 0x7671 forces the source (a debug override, verified compares).
- **EStb** (IDs 0x0204/0x0205): an external strobe class on the accessory bus. Which product it is was not resolved.
- **MAL-1:** the IDs 0x0104/0x0105 have chip-map entries but no device record, so the scan ignores them. Whether MAL-1 reports an ID at all is **UNRESOLVED**.
- **No model gate exists for any of these** (§1.3).

## 3. Eye-Fi and FlashAir (SPC)

- **Eye-Fi code (verified entries):**
  - EYEFI task 0x7E5C1981;
  - `api_media_Get_Eyefi_Status` 0x7E680970, `Enable/Disable_Eyefi_Operation` 0x7E680A28/0x7E680A56, `Get_Eyefi_File_Status` 0x7E680A84;
  - an app-layer Eye-Fi manager: mode 0x7E9747B2, `EyeFi restrict:` 0x7E9748A4 with 23 callers that block uploads during operations (inf);
  - info 290 = prm 0x5001 (mcon #348, 3 values).
- **Eye-Fi menu item:** "Eye-Fi" (str 290/479) is in neither menu table, so it is built in code. Whether it shows only when a card is detected was **not traced (UNRESOLVED)**.
- **FlashAir:**
  - "Connection to Smartphone" (1719/1720) is a Playback-menu row at **0x7EFFE1DC**, kind 0x100 (verified).
  - The app side has `FlashAir::isFlashAir/getWifiSetting/connect…` (names 0x7EBDB0A6…) and `OlyHfwOpeFlashAir::*` 0x7E9D5577…; the camera side is SPC_MAIN 0x7F0A7AF7 with `chk_flashair`.
  - Whether the row is hidden or greyed without a FlashAir card was not traced.
- **E-P5 (verified strings):** it keeps EYEFI, SPC_MAIN/SPC_CTRL and BT_CTRL. It adds `WIFI_MNGR`, `WIFI_REMOCON_THROUGH/PROXY/CGI/DATA`, `WIFI_RELEASE_PUSH`, `HTTPD_MAIN` + `HTTPD_SUB1–5` and `WIFI_LINK_KIND_AUTO/PRIVATE/ONETIME/OTHER`, plus block-1 strings 2007 "Wi-Fi Settings" and "FlashAir is running. Can not use the built-in Wi-Fi." (coordinator diff).
  - The E-PM2 has no `WIFI_MNGR`/`HTTPD` strings. Its only `WIFI_LINK_KIND_PRIVATE/ONETIME` strings belong to the FlashAir wrapper (0x7E9BF7D2, 0x7E9D5577).
  - So the built-in Wi-Fi (HTTP server, remote shooting) is new E-P5 code beside the old FlashAir path (**inferred** from task names).

## 4. USB connection modes (verified chain unless marked)

1. **Menu values.** USB Mode = info 82 = prm 0x8951 (MODE, default 255). Its mcon record #186 lists **4 values: 255, 0, 4, 2**. This matches the four labels Auto (1606/1068), Storage (266), MTP (333/1519) and Print (209). The value↔label order is **inferred**.
2. **GUI decode 0x7ECE098E:**

   | Value | GUI state | Meaning |
   |---|---|---|
   | 255 | 0 | Ask at connect (USB select screen) |
   | 0 and other values | 1 | Storage |
   | 4, 5 | 2 | MTP |
   | 3 | 3 | Print path (value 3 is not in the menu) |
   | 2 | 4 | Print path |

   - If the state is 0 and info 4018 (FLASH 0x0DA1 `PRM_MODE_DPS_ENABLE`) = 0, the state becomes 1.
   - `checkPcMode` 0x7ECE0E8A turns the state into GUI events: 0 → 0x9000010 (select), 3/4 → 0x9000012 (print), 5/6 → 0x9000013, otherwise 0x9000011 (PC).
   - `startPc` 0x7ECE09FC passes mode 2 for MTP, otherwise 1, to a DeviceLink connect.
3. **App device links.** The factory 0x7EBA33C0 builds four link objects (vtables 0x7EC916F4/18/3C/60):

   | Link | Calls | TPC type |
   |---|---|---|
   | DPS | `api_comm_Start_Communication_DPS` 0x7E67641C | **1** |
   | MTP | `…_MTP` 0x7E6764D8 | **4** |
   | Storage | `…_Storage` 0x7E6763A2 | **0** |
   | Generic | `api_comm_Start_Communication(5)` 0x7E676581 | **5** |

   Each one sends TPC command 1 (TPC_ON) with the type byte to the TPC queue 0x7E43EDAE.
   - `api_comm_Start_Communication(n)` maps n 0→0, 1→**2**, 2/3→1, 4→4, 5→5. Its **only caller** (0x7EBA36D5) passes 5.
4. **TPC_ON** 0x7F089339 (via `tpc_control` 0x7F089208, com 1, param at +12):

   | Type | Builder / set | Then writes 0x602C1B1C | Then 0x7F08EA4C mode |
   |---|---|---|---|
   | 0, 5, 6 | A: PTP + firmup | 0x80000001 | 2 |
   | 4 | B: MTP | 0x00010001 | 1 |
   | 1 | C: PictBridge | 0x00010001 | 3 |
   | 2, 3 | D: X3C | 0x80000001 | 2 |

   The value 0x602C1B1C is not read by any constant address, so its meaning is unknown. The mode goes to the PTPCOM queue.
5. **Result:**
   - Storage = type 0, which also gets the plain-PTP + firmware-update op set A.
   - MTP = 4; Print/PictBridge = 1; the generic PTP link = 5.
   - **No sender of types 2, 3 or 6 was found.** The other writers to the TPC queue are firmup (com 3, 0x7E67EBDF) and PC_XXX (com 6, 0x7F09A42B).
   - So the **X3C opcode set (D) looks unreachable on the E-PM2 (inferred)**. Its file-script transport (XDISCVRY/HREQUEST/DREQUEST `.X3C` through SAICAS) is complete code.
   - What X3C is remains **UNRESOLVED**. External, unverified recollection, and network was not used: libgphoto2's Olympus "wrapped PTP over mass storage" driver uses an X3C XML scheme. Treat this as a lead only.
   - The firmware-update ops in sets A and D fit the Olympus updater talking to a camera in Storage mode (**inferred**).

## 5. IEEE 1394 (verified)

- PC_I1394 0x7F097DDF and PC_1394PNP 0x7F097E25 (both reached only through data pointers) loop on `OlyQueueRead(-1)` on queues 0x7E43ED46/0x7E43ED3A. On error they log 0x19800005 and exit (0x7E449621).
- The only other use of queue id 0x7E43ED46 is a sender-id compare at 0x7F096C60. No writer was found. **Stub.**

## 6. HDMI CEC (verified code, partial reachability)

- `api_tft_Enable/Disable_CEC_Protocol` 0x7E68DEC4/0x7E68DEF7 each have one caller: the vtable method 0x7EBA1652 (`setCec(bool)`, vtable word 0x7EC90B9C).
- The HDMI component 0x7EA4143F reads info 306 before logging `io cec: %d`. Info 306 = prm 0x6721 has mcon record #356 with values {0, 1}; that it is the "HDMI Control" (700) on/off is **inferred**.
- TV-remote events `EV_PUSH_CEC_*` and `isCecConnect` (GUI 0x7ECE2177) are present.
- **Active (inferred).** The menu row was not traced, because the Custom Menu D lists are built in code.

## 7. Firmware-update file types: what a user can reach

| Path | Files | How it is reached | Status |
|---|---|---|---|
| Card update mode (FIRMUP_CLI) | All 9 entries: S, A, M, V, D, T, E/G/H/W/E100, DATE/PICTURE1JPG, N | Boot only. 0x7E544A6F needs a power-on factor of 12 / 0x01000002 / 0x01000001 **and** 0x602A9B54 = 0. 0x7E505694 clears that byte when status 4 reads 0 and 0x7E45D893() ≠ 9. Status 4 is **"O  k"** in the name table (verified), so this is probably the OK key held at power-on (**inferred**). The power-on factor values are not decoded | Hidden / service |
| Setup > Firmware (menu) | `L???????BIN` (lens), `F???????BIN` (flash) from the card (section 02 §1.7) | `update_firmware()` 0x7EAB3195 | Active (not re-traced here) |
| USB (TPCFirmup) | Body package via ops 0x9119–0x9125 → FIRMUP_SRV; `api_firmup_Execute_FirmwareUpdate` 0x7E67EBDF | Op sets A/D: Storage (type 0) and generic PTP (5) | Active (inf: Olympus updater) |

- Every card pattern also accepts the E-PL5 code `…100` (S100, M100, V100, D100, T100, E100), so the card path shares the E-PL5 files (verified pattern list, section 02).
- N files are loaded but nothing is written.
- Product knowledge, label only: Olympus shipped body updates through its PC updater, not as card files.

---

## Open questions

1. Which hardware sits at accessory-bus configs `{1, 0x88}`, `{3, 0x68}`, `{2, 0x12}`, `{2, 0x1C}`, and is any of them populated on an E-PM2 board? This is the true answer to "does the E-PM2 have a port".
2. The device names for IDs 0x0104/0x0105 (MAL-1?), 0x023E (bit 6) and EStb 0x0204/0x0205. Is Evf3 the VF-4, or does Evf1/2/3 = VF-2/VF-3/other?
3. The Setup > Menu Display screen: confirm that it writes info 394 on the E-PM2, and what the PENPAL/EVF pages do with no device.
4. The show/hide rules for the Eye-Fi item and the "Connection to Smartphone" row. They are in the code-built menu lists (big item switch 0x7EDCBE97).
5. X3C: find any requester of TPC types 2/3/6 (for example a vendor SCSI command in PC_HOSTCOM), and the meaning of 0x602C1B1C = 0x80000001/0x00010001.
6. The order of the USB-mode menu values 255/0/4/2 against the labels (needs the code-built Custom D list). Also where GUI state 5/6 could come from: no writer was found.
7. The power-on factor values that start card-update mode, and the polarity of status 4 (OK pressed = 0?).

# 08 — Connectivity, libraries and the non-main blocks

Scope: USB/PTP/MTP/PictBridge, firmware update over USB, HDMI/CEC, display/touch/EVF, Eye-Fi/FlashAir,
C3D/SPC, the low-string region 0x7EE21020–0x7F021020, and blocks 2, 3 and the 'OM' tail.

Labels: **verified** = read in the code or bytes; **inferred** = from strings, names or layout only.
All addresses are runtime addresses (block-0 offset = address − 0x7E421020). Helper scripts are in the session
scratchpad (`conn/ptptab.py`, `conn/adjtab.py`, `conn/sigscan.py`, `conn/libprof*.py`), and decoded blocks are in `conn/unpack/`.

## Overview (most important findings)

1. **The PTP stack registers handlers in code.** For each connection mode, one of four builder functions
   calls `ptp_register(op=d0, phase=d1, no_session=a1, handler=a0)` at 0x7F08E975. There are 4 opcode sets:
   plain PTP + firmware update, MTP, PictBridge, and "X3C". **No InitiateCapture (0x100E) in any table**, so there is no standard PTP tethering. (verified)
2. **Vendor ops 0x9xxx that are not in the table go to the ADJ (factory-adjustment) task** through
   `ADJ_P15740_COM_VENDOR_OPERATION`. ADJ handles 16 vendor ops (0x9005–0x902B). One of them, 0x902B, ends in the `USR>` debug shell, so it is a remote shell over USB. (dispatch verified; shell inferred)
3. **Firmware update over USB** uses ops 0x9117, 0x9119, 0x911C and 0x9120–0x9125 (0x911A/0x911B/0x911D–0x911F are not registered) (audit 2026-11-09). FirmwareCheck posts the received image to the **FIRMUP_SRV** task queue. (verified)
4. **IEEE 1394 tasks are stubs.** PC_I1394 and PC_1394PNP only drain their message queue and then exit. (verified)
5. **Block 2 (kind 0x106) = "ARTFIL"**: a 2.25 MiB noise texture of 6-bit values. Only the Grainy Film
   (`art_filter_06_rough_monochrome`) art filter reads it. **Block 3 (kind 0x104) = "FRAME"/"arteffe"**: 8 JFIF
   frame overlays, one per aspect ratio. (verified)
6. **The 'OM' tail is the H8 firmware of the "BC" image-stabiliser controller.** (BC = *bure correction*; *bure* is the Japanese word for camera shake.)
   It uses the same scrambling and checksum as the OE blocks. Main code talks to it over SIO through the BC_MAIN module, and updates it with `[BC FUP]`. PER_SCPU_POLLING is an empty task. (decode verified; role inferred, strong)
7. **The "library" region is two things.** 0x7EE2–0x7EEE (0.8 MB) is code: the C3D 3D engine, **libpng 1.2.37**,
   **zlib 1.2.3 inflate**, and the AV middleware (MP4 mux/demux plug-ins). **0x7EEE1020–0x7F021020 is rodata, not code**:
   strings and vtables of the CA/GUI C++ layer, plus the libpng/zlib tables and the GL/DMP names. The function DB's ~1,500 "functions" there are spurious. (verified)
8. **There is a DMP (Digital Media Professionals) OpenGL-ES-class GPU driver** (`glBeginQueryDMP`, `gl_PVLightAmbDMP`, …)
   at about 0x7EE15060 (**corrected (D2 2026-11-09):** 0x7EE15060 is only its uniform-table builder; the library is 0x7EE02095–0x7EE294B4, 14a §2.1). C3D renders with it. The firmware is dual-core: the same block-0 code runs on CPU0 and CPU1 (it checks a CPU id at 0x8050), and C3D talks across through the C3D_BRIDGE_* tasks. (verified / inferred, see C3D)

---

## 1. USB / PC connection

### 1.1 Tasks and layers (region 0x7F061020–0x7F0A1020)

| Task | Entry | Role | Evidence |
|---|---|---|---|
| PC_USB | 0x7F098DE5 | USB device-controller driver: `[USB]CMD/DATA ALIGN ERROR`, bulk/CBW phases, DMA (`usb_dma_atc_mode_on`), USB 2.0 test modes `TEST_J/K/SE0_NAK/PACKET` | strings (inferred) |
| PC_USBPNP | 0x7F09CDCA | plug-and-play / attach queue (`usbpnp_que_read`) | strings (inferred) |
| PC_USBSRV | 0x7F097F43 | USB interrupt-event server (`USB Intr Event Wait/Set`) | strings |
| PC_HOSTCOM | 0x7F096DB8 | **Mass storage (BOT/SCSI)**: `Unsupport SCSI Command`, `read_exec`/`write_exec`, `format_unit`, `LBA ERROR`, `Media UnMount/Not Ready`, `USB NewMedia` | strings (inferred) |
| PC_PTP | 0x7F098010 | OLPTP queue (`olptp_que_read`, `olptp_c0_idle_vender_queue_write`) | strings |
| PC_EVENT | 0x7F0969C3 | USB async queue/post (`USB:async_que_read`) | strings |
| PC_UAM | 0x7F098BDA | "UAM" with `UAM_ON_TIMER`/`UAM_ON_TIMEOUT` (probably USB auto-mode selection) | inferred |
| PC_XXX | 0x7F09A66F | `usb_dc4_*` queue, `usb_dc4_vender_request` (vendor control requests to TPC) | strings |
| PC_I1394, PC_1394PNP | 0x7F097DDF, 0x7F097E25 | **stubs** | **verified**, see 1.5 |
| TPC | 0x7F088F64 | "Transfer to PC" controller: `TPC_ON connection=0x`, `tpc_control:unknown com`, globals gConnectMode/gConnectState | verified (below) |
| TPC_DATA | 0x7F089E59 | the record side feeding PTP objects (`TPC_DATA_COM_OPEN/GET_IMAGE/DELETE_IMAGE/…`, DCIM, AUTPRINTMRK, `PHOTO EDB` / `DB BIN` = camera picture database) | strings |
| TPC_LANG | 0x7F08AF19 | language-code list for the updater (`tpc_lang_get_lang_list_post`) | strings |
| PTPCOM | 0x7F08E88C | PTP transaction engine (`[TPC_COM] Phase Miss Match`, payload/sequence checks, XML-ish debug dump `<command>/<response>/<data>`) | verified dispatcher |
| PTPASYNC | 0x7F08E6FE | PTP async events (`tpc_ptp_com_SendEvent`) | strings |
| SAICAS | 0x7F0870D7 | script-file transport for DPS and X3C: `handle_SAICAS_OP_COM_OPEN_SESSION/WRITE_INFO/READ/DELETE…`, file names `HREQUEST.DPS` etc. | **verified**: SAICAS reads queue 0x7E43EE0A, which both the PictBridge and the X3C SendObject handlers write |
| DPS_MAIN | 0x7F087807 | PictBridge application (`DREQUEST.DPS`, `dpsw_set_date_info`) with a DPS XML library ~~at 0x7F061020–0x7F068F9C~~ in overlay A, ending at 0x7F0645C0; 0x7F0645C1–0x7F0691C5 is the red-eye library (13b §1) (C3 2026-11-09). The DPS engine is **0x7F05E9CE–0x7F0645C0** (dispatcher 0x7F05E9CE ← DPS_MAIN; session layer, XML encoder 0x7F060BFF, argument checks, XML decoder 0x7F062B89; 15d §4). Before it, 0x7F05E590–0x7F05E8D3 is playback-calendar code (each function the only callee of an `api_calendar_*` wrapper 0x7E6762DC–0x7E67636E) and the `md3d_*_dbg` shells (D3 2026-11-09) (`http://www.cipa.jp/dps/schema/`, `paperSize`, `pictbridge`) | strings |
| ADJ, ADJSLF | 0x7F080000, 0x7F087004 | factory adjustment over PTP (`adj_p15740_p.c`) and self-adjustment/calibration | verified dispatch, see 1.3 |

USB descriptors at 0x7F0D7AF8 (**verified bytes**):
- Device descriptor: USB 2.0, EP0 64 bytes, **VID/PID = 0 in the template**, strings 1/2/3, 1 configuration. VID/PID are patched at run time. The source was not found: the constant 0x07B4 is not in code.
- Two config templates, both `class 08 / subclass 06 / proto 0x50` (mass storage, SCSI, bulk-only). The full-speed one has 2 × 64-byte bulk endpoints. The high-speed one has 2 × 512-byte bulk endpoints plus interrupt EP 0x83. The interrupt EP and the PTP class (06/01/01) are probably patched in for PTP/MTP mode. (inferred)
- LANGID 0x0409, a device-qualifier descriptor, and at 0x7F0D7C58 the 53-byte USB 2.0 `TEST_PACKET` pattern (00…AA…EE…FE FF… 7F BF DF…; the last byte is E7 where the spec has 7E). (verified (audit 2026-11-09))
- GetDeviceInfo handler 0x7F0934AB uses the strings `OLYMPUS` and `1.00`. (strings referenced)

### 1.2 PTP opcode tables (verified)

`TPC_ON` (0x7F089339) switches on the connection-type byte. The type selects one table builder.
Each builder calls 0x7F08E975, which stores `{u16 op, u16 phase, u16 no_session, ptr handler}` in a node list:

| Connection type | Builder | Set (name inferred from contents) |
|---|---|---|
| 0, 5, 6 | 0x7F089754 | **A: plain PTP + firmware update** |
| 4 | 0x7F08993C | **B: MTP** (0x98xx) |
| 1 | 0x7F089AB3 | **C: PictBridge** (SendObject → DPS files) |
| 2, 3 | 0x7F089BFA | **D: X3C** (SendObject → X3C files) + firmware update |

Phase: 0 = no data, 1 = R2I (camera → host), 2 = I2R (host → camera). This matches the strings
`tpc_olptpl_data_phase_none/R2I/I2R`. "no_session" = 1 only for 0x1001 and 0x1002.

| Op | Name | Phase | A | B | C | D | Handler |
|---|---|---|---|---|---|---|---|
| 0x1001 | GetDeviceInfo | R2I | x | x | x | x | 0x7F0934AB |
| 0x1002 | OpenSession | – | x | x | x | x | 0x7F09368A |
| 0x1003 | CloseSession | – | x | x | x | x | 0x7F0937BE |
| 0x1004 | GetStorageIDs | R2I | x | x | x | x | 0x7F093825 |
| 0x1005 | GetStorageInfo | R2I | x | x | x | x | 0x7F0938D7 |
| 0x1006 | GetNumObjects | – | x | x | x | x* | 0x7F093A3B (*D: 0x7F096538 x3c) |
| 0x1007 | GetObjectHandles | R2I | x | x | x | x | 0x7F093B30 |
| 0x1008 | GetObjectInfo | R2I | x | x | x | x | 0x7F093CE8 |
| 0x1009 | GetObject | R2I | x | x | x | x | 0x7F093D7D |
| 0x100A | GetThumb | R2I | x | x | x | x | 0x7F093F45 |
| 0x100B | DeleteObject | – | x | x | x | x* | 0x7F0940BA (*D: 0x7F096828) |
| 0x100C | SendObjectInfo | I2R | | | x | x | C 0x7F092F34 / D 0x7F0962D8 |
| 0x100D | SendObject | I2R | | | x | x | C 0x7F0930B5 / D 0x7F0964A2 |
| 0x100F | FormatStore | – | x | x | x | x | 0x7F0940EC |
| 0x1014 | GetDevicePropDesc | R2I | x | x | x | x | 0x7F0941D2 |
| 0x1015 | GetDevicePropValue | R2I | x | x | x | x | 0x7F0942DA |
| 0x1016 | SetDevicePropValue | I2R | x | x | x | x | 0x7F0943E2 |
| 0x1017 | ResetDevicePropValue | – | x | | | x | 0x7F094512 |
| 0x101B | GetPartialObject | R2I | x | x | x | x | 0x7F094680 |
| 0x9801 | MTP GetObjectPropsSupported | R2I | | x | | | 0x7F08B102 |
| 0x9802 | MTP GetObjectPropDesc | R2I | | x | | | 0x7F08B195 |
| 0x9803 | MTP GetObjectPropValue | R2I | | x | | | 0x7F08B267 |
| 0x9805 | MTP GetObjectPropList | R2I | | x | | | 0x7F08B315 |
| 0x911C | Firmup: GetFirmwareUpdateMode (stub, returns OK) | – | x | | | x | 0x7F09205A |
| 0x9122 | Firmup: GetFirmwareUpdateMode OK/NG | – | x | | | x | 0x7F09207E |
| 0x9120 | Firmup: GetVersions | R2I | x | | | x | 0x7F09210B |
| 0x9124 | Firmup: GetLanguageCode | R2I | x | | | x | 0x7F092180 |
| 0x9125 | Firmup: SendFirmDataInfo | I2R | x | | | x | 0x7F0924FB |
| 0x9119 | Firmup: SendObjectSplit (image chunks) | I2R | x | | | x | 0x7F092274 |
| 0x9121 | Firmup: FirmwareCheck | – | x | | | x | 0x7F092322 |
| 0x9123, 0x9117 | Firmup: UpdateInitiate | – | x | | | x | 0x7F092453 |

The firmware-op names come from the `[TPCFirmup]` string at each handler's start (verified by site address).
The MTP object-property code (`tpc_mtp_opl_*`) knows JPEG, MPO, ORF (RAW), AVI, WAV and MOV formats.

**Dispatcher 0x7F08ECFD (verified).** It looks the opcode up in the node list (0x7F08F467).
- Opcode found: it checks the session (it replies **0x2003 SessionNotOpen** if needed) and calls the handler.
- Opcode not found and `(op & 0xF000) == 0x9000`: it calls 0x7F08EE9C → 0x7F08CDAC. That checks two state getters
  (0x7F089321 == 2 and gConnectMode at 0xA06DE63A != 2), then sends `ADJ_P15740_COM_OPE_CODECHK` (0x7F08D080, message 6
  via 0x7E50689F) to ADJ. If ADJ accepts, the op runs through `tpc_olptp_op` (0x7F08CDD5). This is the "OLPTP" (Olympus PTP) path.

### 1.3 ADJ vendor operations (OLPTP, factory/service)

The ADJ handler 0x7F080284 (`[adj] opData is NULL`) uses a hashed switch table at **0x7F0D2850**: 32 × {key = op − 0x1001, case}. (verified)
It covers 0x1002, 0x1003, 0x1014–0x1017 and these vendor ops. The names are not in the firmware; the hints come from strings 2 call levels down (inferred):

| Op | Handler | Hint |
|---|---|---|
| 0x9005 | 0x7F080519 | `api_rotate_dummy_Get_TFT_Position`, active/inactive |
| 0x9006, 0x9007 | 0x7F080E0F, 0x7F080FB8 | ADJ_EXQR/EXWR (sends to the exec queue) |
| 0x900D | 0x7F081025 | – |
| 0x9013 | 0x7F081089 | `[adj] AFAE PARAM ERR`, EP/RP/TP/UR (AF/AE control) |
| 0x9015 | 0x7F081200 | `ContIAF PARAM ERR capture mode` |
| 0x901E, 0x9021–0x9023, 0x9025 | 0x7F081697 … 0x7F081B24 | – |
| 0x9026, 0x9027 | 0x7F081B73, 0x7F081BDA | ADJ_EXQR/EXWR |
| 0x9029 | 0x7F081C10 (70 callees) | `ADJ_UIQWR`, `strobe timeout`, ADJ_SFLG: drives UI/capture/flash |
| 0x902A | 0x7F082C09 | `cube is disable` |
| 0x902B | 0x7F083D1C → 0x7F08433A | **`USR> `, `:-) `, `not support nikomon`**: runs a command line in the U_SHELL debug shell |

The format strings in 0x7F0A93C4–0x7F0A9AA3 match this command set: `OpenSession`, `SetDeviceProperty`,
`GetExtDeviceInfo`, `GetCalibData(tag)`/`SetCalibData`, `DisposeExposeOnlyCapture`, `ContTFT`, `ContAFAE`, `ContIAF`, `MDN/MDI/MDO`,
`SetPrePro`. So the PC side is the factory **adjustment / calibration tool** (ADJSLF writes `…Calib.prm` and `DSCPRM%02d\…PRMDT.CSV`). (inferred)

### 1.4 Firmware update over USB (TPCFirmup)

Flow, reconstructed from the handlers (verified where marked):
1. The host reads the mode and versions: 0x9122 reads the state at 0xA06E0300 (0/1/2 → reply word 2/3/4) (verified), then 0x9120 GetVersions and 0x9124 GetLanguageCode (with TPC_LANG).
2. The host sends 0x9125 SendFirmDataInfo (size/format), then the image in chunks with 0x9119 SendObjectSplit.
3. 0x9121 FirmwareCheck (verified): allocates 2 buffers (0x7E507325), then writes a message `{cmd = 3, buffer, size, …}` to the queue at 0x7E43EDC8 (0x7E4492B9). It replies 0x2001 OK or 0x2002 GeneralError.
   **FIRMUP_SRV (entry 0x7E54398B) reads that queue at 0x7E5439BA.** (verified) Its request types include `TYPE_FIRMUP_CHECK` / `FIRMUP_USBCHK_ERROR` and `TYPE_FIRMUP_USBUP` / `FIRMUP_USB_ERROR`.
4. 0x9123 or 0x9117 UpdateInitiate: writes setting id 40977 = 1 (0x7E457CED) and starts the update. The camera then reboots (`[firmup]SUCCESS_REBOOT`). (partly verified)

The updater checks the container header (verified in 0x7E543DDE): byte 1 = 'E', u16 at 2 = 0x1010 or 0x1000 (model),
**byte 20 = sub-kind**: 0 USR, 1 OSD, 2 PIC, 3 WAV, 4 FRAME, 5 ADJSLF, 6 ARTFIL, 7 NOREXE, 8 C3D, 9 GUIDE, 10 BEAUTY, 11 GPS.
It also knows LENS, STB (flash), BURE (stabiliser), LANG, SOUND and EXTMOD. Each kind has a `TOO MANY … FIRM FOUND` check.

### 1.5 IEEE 1394 (PC_I1394, PC_1394PNP)

**Verified stubs.** Both entries (70 bytes each) loop on `OlyQueueRead(timeout −1)` (0x7E449218). On error they log (0x7E426D4B) and exit (0x7E449621). There is no other code.
They are leftovers of a generic "PC connection" framework. That framework has slots for several link types (`OBJ_NAME_P_PC_1394PNP`, `…_I1394`, `PC_XXX`, `PC_UAM`) and is shared across Olympus bodies.
The E-PM2 has no FireWire hardware. The 1394 slot exists only so the shared task/queue table stays the same. (inferred)

### 1.6 Connection modes (inferred)

- **PictBridge** (type 1): the PTP host (printer) writes `HDISCVRY.DPS` / `HREQUEST.DPS`. SAICAS turns these into DPS sessions for DPS_MAIN (CIPA DC-001 XML).
- **X3C** (types 2 and 3): the same file-script scheme (`XDISCVRY.X3C`, `HREQUEST.X3C`, `DREQUEST.X3C`). It goes through the same SAICAS queue, and its table also has the firmware-update ops. What X3C is (a kiosk or PC-app protocol) is **unknown**.
- **MTP** (type 4) and **plain PTP** (types 0/5/6) for Windows/Mac.
- **Mass storage** goes through PC_HOSTCOM (SCSI), not TPC.
- The 7 type codes are not yet tied to the "USB Mode" menu items (Auto/Storage/MTP/Print).

## 2. HDMI, display, touch panel, EVF / accessory port

- **HDMI task** (0x7E6BAF18, region 0x7E6A–0x7E6C): it creates `E_HDMI`, `E_HDMI_INTR`, `E_HDMI_SEMA`, `E_HDMI_I2C_END` (0x7E6BAF5E), and also `EVF_SSC`/`EVF_SEMA`.
  The transmitter is an **Analog Devices** part on I2C: `ADI_CEC`, the debug `[i2c] To Tx/Rx HDMI IC Serial I/O`, and `CEC Addr(0xE1)`. **Register-level evidence (D3 2026-11-09, 15d §3):** the driver writes main map 0x72 through the field writer 0x7E6AC903 (168 callers); the CEC library uses a second map 0x78, whose I²C address lives in main register 0xE1 (the CEC init 0x7E6ADE80 writes main registers 0xE2 and 0xE1 through 0x7E6B9B2A → the SIO ch2 write 0x7E6BA448, then reads back CEC-map registers through 0x7E6B9B19 → the ch2 read 0x7E6BA39B); the register numbers used (0x41 power, 0x42 HPD, 0x94–0x97 interrupts, 0xC4/0xC8/0xC9 EDID, 0x55–0x61 AVI InfoFrame, 0xAF HDMI/DVI …) fit the ADV7511 family (numbers V, family I) (D3 2026-11-09).
  The `[HDMI-DRV]` code parses EDID (checksum, CEA data blocks, block map), picks a VIC and colour space, and has modes 1080i 60/50, 720p 60/50, 480p and 576p. (strings, inferred)
- **CEC**: `api_tft_Enable/Disable_CEC_Protocol`, `Get_CEC_ConnectStatus`. The TV remote reaches the GUI as `EV_PUSH_CEC_UP/DOWN/LEFT/RIGHT/OK/RED/GREEN/BLUE/YELLOW`, and TV power-off as `EV_CEC_POWEROFF`. (strings)
- **DISPLAY task** (0x7E6AEAD2): output routing `0:IDLE/1:TFT/2:NTSC/3:PAL/4:HDMI/5:EVF`, two OSD layers + image layer (`I43DM_*` modes), gamma, backlight duty (`[duty] OLED/EVF`), and panel SIO.
  Also `DISP_ADJ_EXT_PORT` / `adj_ext_port_tmds_exe`: the accessory-port EVF video appears to use a TMDS-type link with its own calibration (`outevf_tmds_measurement`). (inferred)
- **TOUCHPANEL task** (0x7E6BCF84): gestures TOUCH/LPRESS/LIFT-OFF/TAP/SLIDE/DTAP are sent to "HLS". It has swivel parameters and a **touch-controller firmware bootloader** (`Initiate Bootload`, `Write Block`, `Please 12sec wait`). **D2 (D2 2026-11-09):** this is the host side of a Cypress TTSP-style bootloader (I, strong). 0x7E6BD8B6 sends the 470-record image 0x7E7F0F78 over SIO ch2 (I²C mode, I) to address 0x24. It runs only for the debug command **`disp tp boot_on`** (U_SHELL, or ADJ op 0x902B over USB): its one caller is the `tp` handler 0x7E6B27C4 after strcmp(`boot_on`) (V). The image is the same in E-PM2 1.1–1.6, E-PL5 1.6 and E-PL6 1.4 (V, byte search) (14d §3.1). Factory touch calibration goes through ADJSLF (`PCODE_TP_CALIB`, `TPVercheck`). (strings)
- **Accessory port / EVF**: `EVF_TYPE_VF2`/`EVF_TYPE_VF3` (with version reads `vf-2 Version:`/`vf-3 Version:`), `EV_EVF_CONNECTED`, the eye sensor (PER_EYE_SENSOR task over IIC; **but that task is an empty `retf`** (section 01), so no driver activity comes from it (D1 2026-11-09)), and `api_rec_Get_Acce_DeviceInformation`.
  **PENPAL** (PP-1) is a Bluetooth/iAP device (`OLYMPUS PENPAL`, `iap_get_acc_inf`), covered by the BT section.
  No macro-arm-light-specific strings were found. Note: `ACC_SPI` / `PRM_PER_ACC_X/Y/Z` is the **accelerometer** (level gauge), not the accessory port. (verified by strings)

## 3. Eye-Fi and FlashAir

- **Eye-Fi** (EYEFI task 0x7E5C1981, code ~0x7E5AB–0x7E5C7): it makes the `EyeFi` directory on the card, reads `EYEFI_CARD_TOKEN_MAC_ADDRESS`, and uses `eyefi_get_status`, `eyefi_enable_operation` and `eyefi_get_file_status(_array)`.
  These are Eye-Fi's control-file protocol over normal FAT I/O. The GUI side is `api_media_*_Eyefi_*` and `EV_EYEFI_STATUS`. (strings)
- **FlashAir = the "SPC" module** (SPC_MAIN 0x7F0A7AF7, SPC_TIMER 0x7F0A7BF7, code 0x7F0A4A–0x7F0A7C):
  - the iSDIO register/command layer (`isdio_read_register`, `isdio_write_command` with com_id/seq_id/res_status, `num_of_res_sts_queue_supp`, `establish_info`, `vendor_info`);
  - `chk_flashair`;
  - edits `\SD_WLAN\CONFIG` (`APPSSID=`, `APPNETWORKKEY=`, `APPMODE=`, `LOCK=`, `MASTERCODE=`, `CIPATH=`) and recreates or recovers it;
  - a state machine `SPC_CTRL_STATE_PRIVATE_/ONTIME_CONNECTING/DISCONNECTING` and `WIRELESS_CONNECTED_INF/DIR`, `STANDBY_*`.
  "Private" and "One-Time" are the OI.Share smartphone-connection modes, so **SPC most likely means "SmartPhone Connect"** (inferred). `SPC_APE` = the SPC app-event bridge to the GUI (`APPEVENT_STATE_SPC_END_CONNECT` …).
  The GUI wrapper is `FlashAir::setWifiSSID/getOneTimePassword/connect`.
- **`dB_Gain_Sv` is not SPC.** It sits in the ADJSLF calibration code that follows from 0x7F0A7E41: sensor gain/ISO, gyro gain/drift, IS-stage stroke, spectral (`SpectraChart.CSV`, `ADJ_BPF_*`) and dark/defect calibration. Results are logged to files such as `BCDT9710.JPG`, `CSAT9101.JPG`, `wb_lv001.csv`. (strings)

## 4. C3D (3D animation engine; ~~on CPU1~~ tasks on both cores, see "Dual core" below (C3 2026-11-09))

- **What it is (inferred, strong):** a 3D animation/rendering service. The feature is **the playback GPU slideshow**: the GUI start 0x7ED081AE calls `startSlideShowGpu` when Effect ≠ 1 and the slideshow is not 3D; the controller is `CapGSld_GpuSlideShow` (14a §3) (D2 2026-11-09).
  - The play side calls `api_play_Exec_C3d_Anime_Logo`, `Exec_C3d_Anime_Main`, `Skip/End/Abort_C3d_Anime`, and `Notify_C3d_Img_Load_Finish` with each photo's size, aspect and date (0x7E685AA3–0x7E685F4B).
  - The scene objects are named `P3D_Room`, `Gr_Room_A/B/C`, `P3D_Photo_%02d`, `P3D_Photo_Focus_%c`, `Gr_Photo_%c`, `TA_Camera_%02d`, `Act_Photo_Turn_%c`, `TA_Bar_In/Out`, `TA_Logo_In`, `P2D_Logo`, `TA_FadeIn/Out` (0x7F09E31F–0x7F0A30A9).
  - So this is a photo "room" slideshow/animation with a logo intro and title bars. `RES_MODE_C3D` is a resource type.
- **Tasks:** C3D 0x7F0A3E60, C3D_UPDATE 0x7F0A406C (reads its queue, forwards message 18 to queue 0x7E43EDF8, calls a hook at 0xA06E12D0), C3D_EXE_BRIDGE 0x7F09ECDC, C3D_BRIDGE_CPU0P_TO_CPU1 0x7F09CE52 and C3D_BRIDGE_CPU1L_TO_CPU0 0x7F09CF7B (from the corrected task table).
  Queue names include `C3D_BRG_C0P_C1L`, `C3D_BRG_C1L_C0P`, `C3D_BRG_C0L_C1P`, `C3D_BRG_C1P_C0L` (P/L = physical/logical endpoints). A `c3d_dbg` shell loads `Pho%02d.bmp`.
- **Dual core (verified part):** the fatal/NMI handler 0x7E463CD9 reads a CPU id at absolute address 0x8050 and prints `Genba Ha CPU0/CPU1` ("the failure is on CPU0/CPU1"). The object-name table has a CPU1 set (`BOOT_CPU1`, `CPUCONN_CPU1`, `MOV_ENC_VIDEO_CPU1`, `CPU1_MOV_AVCHD`, `IMG_CPU0_TO_CPU1`).
  So block 0 is one image that both cores run. ~~C3D (and the movie encoder) run on CPU1 and are reached through the bridge tasks. (inferred from these)~~ **Corrected (C3 2026-11-09):** the task tables (tasks.tsv, `fwmap.py tasks`) put the C3D task 0x0071 (0x7F0A3E60), C3D_UPDATE, C3D_EXE_BRIDGE and C3D_BRIDGE_CPU0P_TO_CPU1 / CPU1L_TO_CPU0 on **CPU0**; only C3D_EXE 0x1002 (0x7F09DFD4) and the bridges C3D_BRG_C0L_C1P / C3D_BRG_C1P_C0L are on CPU1. The CPU0 C3D task replies into queue `C3D_BRG_CPU0P` (0x7F0A3F5A → OlyQeWr, var 0x7E43EE2C). Which core renders is open (C3 2026-11-09).
- **Engine code** = ~~~0x7EE294B5–0x7EE5B (inferred)~~ the 3D engine core **0x7EE294B5–0x7EE5B5BB** (verified layer edges), then its image decoders 0x7EE5B5BC–0x7EE5D00C (14a §2.2) (D2 2026-11-09). 0x7EE21020–0x7EE294B4 is still the DMP GL library (§5); the `MCM_/MCA_/MCT_` module starts at 0x7EE294B5 (C2 2026-11-09):
  - float-heavy: thousands of calls to the single-float helpers at 0x7E5018BC–0x7E501972, which use AM33-2 FPU ops. The full float-helper set is 0x7E500F62–0x7E501AAB (13a §2.2). Do not assume names by order: 0x7E5018BC is **fsub** and 0x7E5018C3 **fadd** (inferred, strong), 0x7E5018E8 is fmul (D1 2026-11-09);
  - 89 functions call the C3D helper 0x7F0A3819; **corrected (D2 2026-11-09):** 0x7F0A3819 is the C3D port's free() (193 callers), and 0x7F0A3804 is malloc (14a §5);
  - vtable-like pointers at 0x7F027C80; **corrected (D2 2026-11-09):** these are part of the format-loader table 0x7F027C4C–0x7F027CBF (MB, MT, BMP, MCM/MCA/MCT/MCE, GIF, PNG) (14a §2.2);
  - tags `MCA_/MCT_/MCE_` with `$Revision: #88 $`, and a `GIF89a` loader;
  - it is driven from the C3D scene code (151 incoming calls into 0x7EE61020–0x7EE81020). **Not reproduced (D2 2026-11-09):** the overlay calls 25 distinct C3D targets (16 API entries and 9 object methods; 14a §2.4).
- The firmware updater has a C3D type (`TYPE_FIRMUP_WRITE_C3D`), but **the E-PM2 container has no C3D block**. The C3D code is in block 0, and **block 2 is not CPU1 code** (see 6.1).

## 5. Libraries in 0x7EE21020–0x7F021020 (and nearby)

| Range | What | Evidence |
|---|---|---|
| ~~~0x7EDE–0x7EE29~~ **0x7EE02095–0x7EE294B4** (D2 2026-11-09) (not 0x7EE21020: the `{name, fn}` table ~~0x7F023C74~~ 0x7F023B8C–0x7F024283 (223 slots: 29 `egl*`, then 194 `gl*` with `glDeleteQueriesDMP` twice; 14a §5 item 3 (D2 2026-11-09)) has 194 `gl*` entries, 89 of them at or above 0x7EE21020, up to glPointSize 0x7EE29468 (C2 2026-11-09); 0x7EDE–0x7EE01 is GUI menu-page code, 13d §1 (D1 2026-11-09)) | **DMP GPU GL driver**: uniform table builder 0x7EE15060 (`gl_ModelViewMatrix`, `gl_TextureMatrix[0..2]`, `gl_PVLightAmbDMP`, `gl_SilhScaleDMP`, `gl_SubdLevelDMP`, …). Names at 0x7F01938E/0x7F026D08. Extension entry names `glBeginQueryDMP`, `glLineStippleDMP`, `glBlendColorDMP`, `glSetErrorFuncDMP` at 0x7F023ACB | **verified** strings + refs. The `*DMP` suffix is the Digital Media Professionals (PICA-family) extension style (inferred vendor) |
| ~~~0x7EE294B5–0x7EE5B (C2 2026-11-09)~~ **0x7EE294B5–0x7EE5B5BB** (D2 2026-11-09) | 3D engine core: MC* format loaders, GL render back end 0x7EE2FF5E–0x7EE32698 (the only engine code that calls GL), 28-type object runtime, maths (`$Revision: #88 $` 0x7F027CC4) (14a §1) | verified layer edges (14a) |
| 0x7EE5B5BC–0x7EE5D00C (D2 2026-11-09) | Engine image decoders: BMP, GIF89a, PNG glue (14a §1) | verified (magic checkers, loader table) |
| ~~0x7EE5BB–0x7EE5F~~ **0x7EE5D00D–0x7EE5F5F2** (D2 2026-11-09) | **libpng 1.2.37** ("libpng version 1.2.37 - June 4, 2009", 0x7F02B404; all png_* error strings; read side only) | **verified** |
| 0x7EE5F5F3–0x7EE619C6 (C2 2026-11-09) | **zlib 1.2.3 inflate** ("inflate 1.2.3 Copyright 1995-2005 Mark Adler", 0x7F02E999). Inflate 0x7EE5FE61, CRC-32 0x7EE5F5F3 with table 0x7F02BE7C, code-length order 0x7F02E702, dist base 0x7F02EA44. Called from libpng (0x7EE5DA3F, 0x7EE5EE73). The last zlib function is `zmemcpy` 0x7EE619AC–0x7EE619BE (callers inflate 0x7EE5FD73/0x7EE5FE61), then the stubs 0x7EE619BF/0x7EE619C4; no zlib or libpng function calls 0x7EE619C7 or later (C2 2026-11-09) | **verified** |
| ~~0x7EE619C7–0x7EE63004 (C2 2026-11-09)~~ **0x7EE619C7–0x7EE8F4F3: the C3D framework, one module** (D2 2026-11-09) (overlay-called API 0x7EE619C7–0x7EE61E54; class code from 0x7EE62C10; class registry and ~55 classes; 14a §1, §2.4) | C3D-facing API (called by the scene code 0x7F09E31F, 0x7F09DFD4). It starts with the 44-byte object init 0x7EE619C7 (caller chain 0x7EE61A59 → 0x7EE61A4F → 0x7F0A13F9 → 0x7F09DFD4), not zlib (C2 2026-11-09). Its last function 0x7EE62F80 runs to 0x7EE63004, and it and 16 other API functions are called from 0x7EE63000–0x7EE8F4F3, so the API and that code are one C3D library (A5 2026-11-09) | refs |
| 0x7EEA–0x7EEE (**0x7EE8F4F4–0x7EECE318**, where block-0 code ends; rodata follows. 0x7EE63000–0x7EE8F4F3 before it is C3D-side code; 13b §1 (D1 2026-11-09)) | **AV middleware ("AVPI")**: `CAvpiAsoAudioSource.cpp`, `Video Source Plug-in`, `MP4 Mux Plug-in`, `MP4 Demux Plug-in`, box writers `ftyp/moov/mvhd/trak/…/avc1/avcC/stts/stsc/stsz/stco/stss`, `sowt` PCM, `AvScaTask: AVSCA_*`. Called from the movie code (`AVMIDDLE CALL`, `[QT] MovmidApi_cmd_rec_init/start/end`) | strings + calls |
| **0x7EEE1020–0x7F021020** | **rodata, not code**: strings of the CA/GUI C++ layer (`ShootingCommon`, `[S-AppShot ]:`, `AppVer: 2010Apr06 CheckIn`), vtables, the GL name pools, libpng/zlib tables. Entropy 3.4–4.5 bits/byte. The "calls" decoded there go to addresses like 0xAE6D05EC, so the ~1,500 DB "functions" are false positives | **verified** |

Also:
- **JPEG:** no zig-zag, quant or IDCT tables exist anywhere in block 0. Only the standard DHT tables (DC/AC luma Huffman bits/values) appear, twice, at 0x7E74A6E8 and 0x7E74A89D. Function 0x7E5576C2 reads them, presumably to write JPEG headers. So JPEG coding is done by the image ASIC; the CPU only builds headers. (verified absence; role inferred)
- **No crypto tables**: no AES, SHA or MD5 constants. The iPod authentication (`cp_ValidateCertData`) is probably done by the Apple CP chip.
- The BASIC-like interpreter (BAS_MAIN, `expr_222`, `do_for2`) is in overlay A at ~0x7F05C000 (`expr_222` user 0x7F05CDD6), not at 0x7F021020; see section 01 (coordinator 2026-11-09).

## 6. Non-main blocks

Load addresses are **verified** by the `fmem` debug printout in 0x7E44F509 (labels `pict_addr`/`osd_addr`/`artfill_addr`/`arteffe_addr`/`sound_addr` at 0x7E475120):
pict 0x41040000, **OSD 0x43C40000 (block 1)**, **artfill 0x45220000 (block 2)**, **arteffe 0x45480000 (block 3)**, sound 0x46200000.
At start-up, 0x7E674E60 reads the directory header of each region into RAM with 0x7E6756B5: OSD 2048 bytes, ARTFIL 1024, arteffe 1024, and 0x45800000 4096. The flash copy keeps the 32-byte OE header, so the directory pointer is the header pointer + 32.

### 6.1 Block 2, kind 0x106 = ARTFIL: Grainy Film noise texture (verified)

- Payload: directory `{u32 size = 0x240000, u32 addr = 0x45220400}`, then 0xFF fill, then **0x240000 bytes at payload offset 0x3E0**. That offset is 0x45220400 = load address + 32-byte header + 0x3E0. (verified)
- Every byte is 0–63 (6-bit). The value 60 never occurs. Autocorrelation is ≈ 0 at every lag tested (1…2048), and the bigram entropy equals the unigram entropy (5.83 bits). So the symbols are i.i.d. noise.
  Each value v occurs with probability almost exactly m_v/256 (m_0 = 10, m_1 = 8, m_2 = 12, …), as if `T[random byte]` with a fixed 256→64 map. It is a **precomputed grain-noise field**, about 2048 × 1152 or 1536 × 1536. (stats verified; the dimensions are a guess)
- **User (verified):** `art_filter_06_rough_monochrome.c` pass 2 (0x7E722B38) calls the resource loader 0x7E674F44 with type **10**. The jump table at 0x7E7C10A4 sends case 10 to 0x7E675538. That reader takes an 8-byte entry `{size, addr}` from the artfill directory (0x6059CCE8) and reads a window of it. "Rough monochrome" is the internal name of **Grainy Film**.

### 6.2 Block 3, kind 0x104 = FRAME / "arteffe": art-effect frame overlays (verified)

The directory has 16-byte entries `{u32 flash addr, u32 len, 0, 0}`. Each item = a 16-byte header (date stamp `2011-11-17 13:47`, 3 id bytes) + a baseline JFIF JPEG:

| # | Size | id bytes | Pixels |
|---|---|---|---|
| 0 | 0x8DA00 | 02 03 02 | 4608 × 3072 (3:2) |
| 1 | 0x63E00 | 03 03 04 | 2592 × 3456 (3:4) |
| 2 | 0x9C800 | 06 04 03 | 4608 × 3456 (4:3) |
| 3 | 0x83400 | 08 06 06 | 3456 × 3456 (1:1) |
| 4 | 0x08600 | 0a 04 03 | 640 × 480 |
| 5 | 0x13800 | 0a 10 09 | 1280 × 720 |
| 6 | 0x89600 | 0a 10 09 | 4608 × 2592 (16:9) |
| 7 | 0x23E00 | 0a 10 09 | 1920 × 1080 |

The id bytes appear to be (index, aspect w, aspect h). The users are the `art_frame_*` functions (`art_frame_decord_jpeg`, `art_frame_disp_jpeg_revision` 0x7E721552 → loader type 14, `[GetFrameData]` 0x7E6F1910 for movie).
These are the "Frame" art-effect borders at each still and movie size. (inferred use; format verified)

### 6.3 Tail 'OM' = H8 firmware of the BC image-stabiliser controller

- **Container:** header `OM 10 10 … 00 01 00 00 93 13 …`, a 64 KiB payload, then a trailer. The payload uses **the same lane permutation + XOR 0xFF as the OE blocks, and the same checksum**: the LE word sum of header + decoded payload + trailer = 0. (verified)
- **Decoded image:**
  - big-endian 32-bit vector table of 80 entries (H8S / H8-300H advanced mode);
  - reset → 0x056E; default handler 0x05C0;
  - active vectors 18, 22, 23 (IRQ2/6/7 in the H8S numbering) and 34–37 (peripheral; the chip variant is not identified);
  - vectors 13–14 hold the ASCII **"E. Munch"**;
  - 927 `rts` (0x5470) and 7 `rte` in 0xF7AB bytes of code/data. (verified)
- **Role (inferred, strong):** the main code holds the same tag at 0x7E745CC0 (`E. Munch` + `e101`), followed by `[BC FUP]INIT/ERASE/WRITE/VERIFY` and `ID CHECK..`. So the BC firmware-update module (0x7E542A17–0x7E542AFE) checks this ID and flashes this image.
  The BC module (BC_MAIN 0x7E53D96D) talks to the MCU over SIO with handshake lines `RST/CS/RDY/RQ/TRG` (`siotx`/`siorx`, `tx_data[%d]`, `bps:`) and reports `stab.standby/detect/correct`, gyro `HPF1/HPF2`, `X_COUNT/Y_COUNT`, `bc_stage` and `sc_get_stabtype`.
  The firmware updater calls the image "BURE" (`TYPE_FIRMUP_WRITE_BURE`, `BURE USBFUP ERR`). So the H8 is the **sensor-shift IS controller** (gyro + stage), not the power/key MCU.
- **PER_SCPU_POLLING** (0x7E467D96) is a bare `retf [],0`, an empty task on this body. (verified) `SCPU`/`SCPU_FIRMUP` exist only as object names. `[firmup]SCPU Init Err` and `subcpu_led/subcpu_beep` are in FIRMUP_CLI.
  Power and keys go through PER_PCONT/HPROC (another section).

---

## Open questions

1. What are connection types 0–6? Which menu item ("Auto/Storage/MTP/Print") sets each, and who sends `TPC_ON`?
2. What is **X3C**? It has its own discovery/request files, shares the SAICAS transport, and its table includes the firmware-update ops.
3. Where are the USB VID/PID and the PTP model string patched in (a parameter-flash id?). Is the PTP-class interface descriptor built at run time?
4. Names and arguments of the 16 ADJ vendor ops. Is OLPTP enabled only in a service/adjust state (the 0x7F089321 == 2 gate)?
5. The exact firmware-update handshake: the meaning of state 0xA06E0300, the chunk format of 0x9119, and what 0x911C really returns.
6. The C3D/CPU1 split: does CPU1 boot from the same block-0 image at another entry (BOOT_CPU1)? Which tasks run on CPU1?
7. Block 2: the true width/height of the noise field, and how the Grainy Film pass samples it (offset/tiling).
8. The H8 MCU part number (vector layout 34–37), and the SIO command set of the BC protocol.
9. The DMP GPU: which core, and whether the GUI (`gl_*` in 0x7EDE) also renders through it or only C3D does. Answered in part: the GUI never calls GL; the only callers are the engine's GL back end 0x7EE2FF5E–0x7EE32698 and the overlay port and scene functions (14a §5 item 4) (D2 2026-11-09).
10. The HDMI transmitter model (ADV75xx?) and which CEC opcodes are handled beyond the remote keys and power-off.

# E-PM2 v1.6 firmware map

A map of what the main firmware contains and where. This is for learning only: nothing here was patched or flashed.

- **Labels:** **verified** = read in the code or bytes; **inferred** = from strings, names or layout only. Every claim keeps the label from the section it came from.
- **Second pass:** every hidden/dormant/stub/unknown feature was re-checked against the code, the menu value tables and 8 bodies (section 10, `10-hidden-features.md`). The table rows below carry those verdicts.
- **Sources:** the eight subsystem sections in `experiments/2026-11-08-feature-map/sections/` hold the detail and addresses. Hand spot checks are in that folder's `NOTES.md`.
- **Addresses:** runtime addresses. Block-0 offset = address − 0x7E421020 (base verified).
- **Tools:** `tools/fwmap.py build` builds the function database (about 66k functions). Then use `fn`, `str`, `range`, `xref` and `tasks`. `tools/disasm.py` disassembles any range.

## 1. Architecture at a glance

- **Two CPU cores, both running uITRON** (verified, section 01).
  - A task id holds the CPU number in bits 12–14. CPU0 has 147 tasks (table at block offset 0x17CB0) and CPU1 has 30 (table at 0x1C490).
  - `OlyTaSt` (0x7E449541) passes a CPU1 id to the other core. The same block-0 code runs on both cores; the crash handler reads the CPU id at address 0x8050.
  - CPU1 runs AVCHD encoding, art processing, the C3D 3D engine and the AVPI AV middleware: tasks 0x1011–0x101B are AVPI threads (trampoline 0x7EE8FBB1), 0x101C is AvScaTask, and 0x101D/0x101E are AVPI service tasks (section 13b) (D1 2026-11-09).
- **Layers, from bottom to top:**
  1. **Kernel wrappers.** `Oly*` names for tasks, event flags, queues and semaphores.
  2. **Drivers and peripheral tasks** (0x7E42–0x7E52).
  3. **Service tasks.** Lens, firmware update, TAKE_* (shooting control), strobe, files, REC_* (still recording), MOV_* (movie), PLAY_* (playback), AUD_* (audio), ART (art filters), FACE (face detection) and the PC/PTP connection tasks.
  4. **C camera API.** About 640 `api_*` functions at 0x7E675E64–0x7E68F048. Asynchronous calls go through `api_exec_start`, which uses a 36-entry funcno→queue table (section 03).
  5. **C++ application.** Statecharts on IBM Rhapsody's OXF runtime (inferred, strong): one event loop in HIGHLEVEL_MAIN and 1,273 event classes with 1,268 ids (section 13c; section 06 counted about 930) (D1 2026-11-09).
  6. **GUI** (`GUI App`, CA_MAIN, ~~~0x7ECC8000–0x7EE01FF5~~ 0x7ECCB800–0x7EE02094 (D2 2026-11-09); the rest of 0x7ECA–0x7EE2 is data and a C3D GL library, section 13d (D1 2026-11-09)). It reads and writes settings through an API object, then Get/Set_CameraInfo, then the prm store (section 07).
- **Link order is preserved.** The code of each source file is contiguous, and its strings follow in the same order (verified). `experiments/2026-11-08-feature-map/modules.tsv` places all 152 source-file names. Round D2 added 11 `cam_*.c` rows placed by link order and the E-PL7 file list (placement `inferred-14b`) and 2 unnamed modules (`sc`, `wb`), and moved 22 `first_fn` values to the true file start (getInstance, ctor or init) (D2 2026-11-09). Round D3 added 6 more camera-core rows placed the same way (`cam_serial.c`, `cam_sg.c`, `cam_siodrv.c`, `cam_strobe.c`, `cam_watchdog_timer.c`, the unnamed imgdev driver/sequences 0x7E63D1C1–) and 3 unnamed modules (SDET, mdet, res; placement `inferred-15b`), set cam_lens.c, cam_set.c and cam_still_live_bulb.c to their full ranges, and moved the `Cmp_PlayComponentBase` and `CmpPEvV` rows to their class-index ranges (15b §7, 15c §1) (D3 2026-11-09).
- **Overlays.** Part of block 0 is copied from flash at boot (Usr1). The BASIC/DPS and ADJ/PTP/USB ranges load only on demand (verified, section 01). The reset code also copies the `.data` init image 0x7E8DA000–0x7E8F3113 to RAM 0x602A9B40–0x602C2C53 (0x7E4212B8–0x7E4212E0 → 0x7E425FA8; ROM = RAM + 0x1E6304C0), and the walker 0x7E44B6B0(segment id) runs one static-constructor table per segment (14d §1, verified) (D2 2026-11-09).

### Address regions of block 0

| Range | Contents | Section |
|---|---|---|
| 0x7E421020–0x7E4A0000 | Kernel wrappers, debug output, S_SHELL, flash memory, peripheral tasks (PER_*), interrupt and watchdog code, task tables (data). Reset code 0x7E421020–0x7E4262xx; kernel 0x7E426xxx–0x7E44Axxx; drivers proper 0x7E45824B–0x7E46C308; then data (the ROM driver tables 0x7E4C5534–0x7E4C8A88 lie beyond this row) (D1 2026-11-09); after them, FLSH flash-helper code from 0x7E4C8E40 to the padding at 0x7E4C90CA (code, not table data; 13f) (D4 2026-11-09) | 01, 13f |
| 0x7E4E0000–~~0x7E521020~~ 0x7E521132 (L1 2026-11-09) | 0x7E4C90CA–0x7E4FDFFF is 0xFF padding. **C runtime 0x7E4FE000–0x7E501C5A** (libm, stdio, stdlib, string, float helpers). Then startup tasks (USRSTART_*), U_SHELL, the **`sc` library 0x7E506CB0–0x7E508DA6** (sc shell, SC_TTIMER soft timers, scheap fixed-block pools + SCHEAPDBG guard checker, memcpy 0x7E5081FA / memset 0x7E5082B6 / strlen 0x7E508346 and string helpers, RTC/calendar) (D2 2026-11-09), UI input (from 0x7E508DA7) (D2 2026-11-09), LEDs, timers, lens communication helpers (D1 2026-11-09) | 01, 02, 13a, 14b |
| ~~0x7E521020–0x7E621020~~ 0x7E521133–0x7E6211E0 (L1 2026-11-09) | Firmware update, lens, battery, body stabiliser (BC), **IMG image-job library 0x7E544AA9–~0x7E576D58** (incl. IMG_PRECON: pixel-defect correction (cmd 0) and WB/colour calibration (cmds 1–4) (D2 2026-11-09)), `buff` manager ~0x7E576D59–0x7E579C33 (D1 2026-11-09) (D2 2026-11-09), **WB module 0x7E579C34–0x7E581FAF** (WB_MOV task 0x7E57F914) (D2 2026-11-09), TAKE_* shooting control from the TAKE init 0x7E581FB0 (D2 2026-11-09), strobe (to 0x7E5E2987), files/DCF, Eye-Fi (from its device/request layer 0x7E5AB878), DPOF (from 0x7E5BE823, I), AF/FCS from its init 0x7E5E2988 (← Usr0) incl. movie AF (D4 2026-11-09); the AF/FCS code runs on past this row to 0x7E627E9E (D7 2026-11-09) | 02, 13a |
| ~~0x7E621020~~ 0x7E6211E1–~~0x7E6A1020~~ 0x7E6A935C (D3 2026-11-09) (L1 2026-11-09) | ~~Camera core (`cam*.c`)~~ the **AF/FCS code tail 0x7E6211E1–0x7E627E9E** (fcs/AF helpers that continue the AF/FCS code of the row above: e.g. 0x7E6212B5 logs `fcs_sub_iaf_set_lens_pos_info`, the AF trace init 0x7E626BE3 is called only by the AF/FCS init 0x7E5E2988; the last functions are the setters 0x7E627E8D/0x7E627E96, called by fcs code; 03 §3 table, 16d), then the camera core (`cam*.c`) from 0x7E627E9F (round 8 review 1) (D7 2026-11-09), the C camera API (`api_*`), EXP_MOVIE (AE; the `exp` module ~~0x7E68F0DD–~0x7E6A93E4 runs past this row~~ 0x7E68F07C–0x7E6A935C ends this row, 12 §1, 15b §5.7) (C3 2026-11-09) (D3 2026-11-09), SDET (scene detection), then the **mdet motion-detection / AF-tracking library ~~0x7E666EB9–~0x7E675000~~ 0x7E666C5B–0x7E674DF4** (called by TAKE AF and FCS_MOVIE; SDET reaches only 0x7E673F91; 03 §7b) (C3 2026-11-09) (D3 2026-11-09). Order inside (15b §1, §4): SDET 0x7E662C27–0x7E666C5A, mdet 0x7E666C5B–0x7E674DF4 (first function 0x7E666C5B ~~calls EMS2 0x7E4600B0~~ reads the **EMS1** unit 0x99E00000 through the field helpers 0x7E460030/0x7E460084 → 0x7E45FF3C; 0x7E4600B0 is only `add 32,a0; retf`; per coverage/round9-review1.md) (C9 2026-11-09), the **res** flash-resource store 0x7E674DF5–0x7E675D98 (`res_read` 0x7E674F44), then `api_*` from 0x7E675D99 (D3 2026-11-09) | 03, 15b |
| ~~0x7E6A1020~~ 0x7E6A935D–~~0x7E70B000~~ 0x7E70B3F7 (D3 2026-11-09) (L1 2026-11-09) | ~~Movie~~ ~~The tail of the `exp` (EXP_MOVIE) module to ~0x7E6A93E4 (`[exp]:` strings to 0x7E6A8D7A; the first `[HDMI-DRV]` function is 0x7E6A93E5) (C3 2026-11-09), then movie (`mov*.c`), plus the display, HDMI and touch-panel tasks.~~ The ADI HDMI transmitter driver `[HDMI-DRV]` from 0x7E6A935D (its first function; only caller 0x7E6AC4DF in the driver) and the ADI CEC library, then the display, HDMI and touch-panel tasks, then movie (`mov*.c`) from 0x7E6C3955 (15b §1, 15d §1) (D3 2026-11-09). Inside it: face detection FACE_* (tasks from 0x7E6F45B8, code up to 0x7E6FCA5F) and the mode controller **mcon 0x7E6FCA60–0x7E70787F** (D1 2026-11-09). Then the **IMGDMA add-job module 0x7E707880–0x7E707A9C** (not the Exif writer: dispatcher + 3-builder table 0x7E84EE68, `IMGDMA_ADD_YC/BAYER/RGB`), unnamed IMG-library helpers 0x7E707A9D–0x7E708311, and the PrintIM/Exif/MakerNote writer 0x7E708312–0x7E70B3F7 (tag templates from 0x7E84EF20; 03 scope line) (coverage C4 (L1 2026-11-09)) | 04, 08, 13b, 13e |
| ~~0x7E70B000–0x7E730000~~ 0x7E70B3F8–0x7E731584 (L1 2026-11-09) | Still recording (`rec_*.c`; from the rec init 0x7E70B3F8 (inferred) and the REC_MAIN task 0x7E70B435) (L1 2026-11-09), art filters and effects; then the **Omron OKAO PT library 0x7E72CFA1–0x7E731584** (no strings; ~~it runs past this row~~ it ends code segment 1 (L1 2026-11-09)) (D1 2026-11-09) | 03, 13b |
| ~~0x7E730000~~ 0x7E731585–0x7E8E0000 (L1 2026-11-09) | Mostly read-only data (64% of pages): strings and tables for the modules above. **Segment-1 rodata 0x7E731588–0x7E8808BF** in the link order of the code 0x7E4FE000–0x7E731584 (14d §2); inside it the OKAO PT models 0x7E85CEFC–0x7E86DD5F and the **ORF CMIO blob 0x7E86DD80–0x7E8808BF** (76,608 B, copied by 0x7E5586B9 for the ORF header) (D2 2026-11-09). Some code: ~~the firmware-update result screen and LED at 0x7E8808C0–0x7E880E84~~ the code block 0x7E8808C0–0x7E880F43 (firmware-update result messages, LED helpers and the app-event poster 0x7E880EFF/0x7E880F0C), then the segment-1 constructor table 0x7E880F44–0x7E880F5B (6 pointers), then 0xFF 0x7E880F5C–0x7E8D9FFF; the **`.data` init image** starts at 0x7E8DA000 (D2 2026-11-09). **Touch-panel controller firmware image 0x7E7F0F78–0x7E7FAB85**: 470 records of 85 B (`00 FF 39` + key 00..07 + block number 0x1E–0x1FF + 64 data bytes + 2-byte checksum), then the enter/exit packets 0x7E7FAB9F–0x7E7FABB4 (`FF 38` / `FF 3B` + key). The TP bootloader 0x7E6BD8B6 (`[TP]bootloader start`) loads the packets and walks the records (`add 0x7E7F0F78`), writing to I2C address 72 (verified). Cypress TrueTouch bootloader format (inferred). The DB's "functions" inside it are spurious (C2 2026-11-09) | 02, 08 |
| 0x7E8E1020–0x7E8F5800 | ~~Data (method-name pointer tables, padding)~~ The rest of the **`.data` init image 0x7E8DA000–0x7E8F3113 → RAM 0x602A9B40** (it holds the method-name pointer table 0x7E8E13B0, RAM 0x602B0EF0), then 0xFF from 0x7E8F3114 (14d §1, §3.8, verified) (D2 2026-11-09) | 05, 14d |
| 0x7E8F5800–~~0x7E966000~~ 0x7E965FD0 (L1 2026-11-09) | Playback transitions, SERV_MAIN, Bluetooth/PENPAL stack, OBEX, playback engine (`play_*.c`), audio | 05 |
| ~~0x7E966000–0x7EBA1020~~ 0x7E965FD1–0x7EBA0AA8 (L1 2026-11-09) | C++ app layer: Cap*/Cmp* components, `sdk api` shell, picture database (stubbed). Inside it (13c §1): user-shell support 0x7E965FD1–0x7E966A16 (A5 2026-11-09); statechart to 0x7EB84344; Com_ framework 0x7EB84345–~~0x7EB8C265~~ 0x7EB8C264 (L1 2026-11-09); `Dev*` part 1 0x7EB8C265–0x7EB93422; categories from 0x7EB93423 (function-mode category, then `Ctg_ComponentSwitcher`) to 0x7EBA0AA8 (C2 2026-11-09) (ends verified, 14c §1) (D2 2026-11-09) | 06, 13c, 14c |
| ~~0x7EBA1020–0x7ECA0000~~ 0x7EBA0AA9–0x7ECB083B (L1 2026-11-09) | `Dev*` device classes (incl. DevBlu) 0x7EBA0AA9–0x7EBA48BB; **OXF runtime 0x7EBA48BC–0x7EBA7BC0** (A5 2026-11-09); **OKAO Smart Skin 0x7EBA7BC1–0x7EBABF8D**; data from ~~about 0x7EBAC000~~ 0x7EBABF90: **segment-2 rodata 0x7EBABF90–0x7ECB083B** (vtables and app data; its tail 0x7EC92318–0x7ECB083B is the Smart Skin LUTs, not GUI data) (D2 2026-11-09) (D1 2026-11-09) | 05, 06, 13b, 13c, 14d |
| ~~0x7ECA1020–0x7EE21020~~ 0x7ECB083C–0x7EE294B4 (L1 2026-11-09) | ~~0x7ECA1020–~0x7ECC8000 is mostly data. ~0x7ECC8000–0x7EE01FF5~~ ~~Smart Skin LUTs to 0x7ECB083B,~~ the segment-2 constructor table 0x7ECB083C–0x7ECB0887 (19 pointers), 0xFF to 0x7ECCB7FF (with one `retf` at 0x7ECB1000) (D2 2026-11-09). **0x7ECCB800–0x7EE02094: GUI** (segment-3 code; first function 0x7ECCB800 `[OSD_CONTROL]`) (D2 2026-11-09), menus, live view and control-panel UI. **0x7EE02095–0x7EE294B4: DMP EGL/GL library** (OpenGL ES 1.1 + extensions), not GUI; ~~it runs past this row~~ (D1 2026-11-09) (C2 2026-11-09) (D2 2026-11-09) | 07, 13d, 14a, 14e |
| ~~0x7EE21020~~ 0x7EE294B5–0x7EEE1020 (L1 2026-11-09) | ~~GL library tail to 0x7EE294B4;~~ **3D engine core 0x7EE294B5–0x7EE5B5BB** (format loaders, GL render back end 0x7EE2FF5E–0x7EE32698, object runtime, maths) and its image decoders 0x7EE5B5BC–0x7EE5D00C; **libpng 1.2.37 0x7EE5D00D–0x7EE5F5F2** (D2 2026-11-09); **zlib 1.2.3 inflate 0x7EE5F5F3–0x7EE619C6**; ~~**C3D API 0x7EE619C7–0x7EE63004** and the C3D-side code after it to 0x7EE8F4F3 (one library) (C2 2026-11-09)~~ **C3D framework 0x7EE619C7–0x7EE8F4F3**, one module (API 0x7EE619C7–0x7EE61E54, class code from 0x7EE62C10) (D2 2026-11-09); **AVPI AV middleware (MP4 mux/demux, codec driver) 0x7EE8F4F4–0x7EECE318**, where block-0 code ends; rodata after it (D1 2026-11-09) | 08, 13b, 14a |
| 0x7EEE1020–0x7F021020 | Read-only data (menu tables at 0x7EFFE13C / 0x7EFEF4FC (D1 2026-11-09), Custom Menu table 0x7EFF7E80 (D1 2026-11-09), GUI strings, vtables) | 07, 08, 13d |
| 0x7F021020–0x7F034000 | Rodata (not BASIC) (D1 2026-11-09): 0x7F021020–0x7F0229AF is the tail of an unreferenced table from 0x7F01F7F4 (not graphics); **GL rodata 0x7F0229D0–~0x7F027BFF** (`{name, fn}` table 0x7F023B8C, 223 slots); **3D engine 0x7F027C00–0x7F02B24A**; libpng and zlib to 0x7F02EB67; **C3D rodata 0x7F02EB68–0x7F02F683**; then AVPI plug-in names, vtables and codec tables from ~~0x7F02F600~~ **0x7F02F684**; the segment-3 constructor table 0x7F033AC8–0x7F033B7B (45 pointers) (D2 2026-11-09) | 13b, 14a, 14d |
| 0x7F034000–0x7F05C000 | Padding (zeros, then erased flash) | — |
| 0x7F05C000–0x7F06B000 | Overlay A: BASIC interpreter and DPS (PictBridge, up to 0x7F0645C0); **red-eye library 0x7F0645C1–0x7F0691C5** (FACE cmd 5); BASIC keyword table at 0x7F0691C8 (D1 2026-11-09) — on-demand overlay. DPS calls overlay-B helpers (malloc 0x7F0879CD, memset 0x7F087BE5, strlen 0x7F087BD1, 0x7F087BF9; 26/18/28/14 callers in overlay A), so DPS needs overlay B loaded too (load order not traced) (C3 2026-11-09). **D3 (15d §4):** the DPS engine is 0x7F05E9CE–0x7F0645C0 (0x7F05E590–0x7F05E8D3 before it is playback-calendar code); all 297 A → B call edges come from DPS code; DPS_MAIN 0x7F087807 itself is in overlay B and feeds A's dispatcher 0x7F05E9CE, so PictBridge needs both overlays. Usr2's A and B masks are independent (01 §2) (D3 2026-11-09) | 01, 08, 13b, 15d |
| ~~0x7F06B000–0x7F0AB000~~ 0x7F06B000–0x7F07FFFF, 0x7F080000–0x7F0EB800 (C3 2026-11-09) | 0x7F06B000–0x7F07FFFF is 0xFF padding. **Overlay B 0x7F080000–0x7F0EB800** (Usr2 bit 1 copies 0x6B800 bytes from flash 0x80F1F000; 01 §2; its rodata, e.g. `C3D_BRG_CPU0P` 0x7F0D8B78, lies past 0x7F0AB000) (C3 2026-11-09): ADJ / ADJSLF factory adjustment, PTP/MTP/USB stack, TPC, C3D bridges, SPC (FlashAir) | 01, 08 |

**Boundaries from round D1 (2026-11-09; sections 13a–13f).** These replace the coverage-round C1 corrections and are already in the table above.
- **C runtime 0x7E4FE000–0x7E501C5A** (not 0x7E4F8000; 0x7E4C90CA–0x7E4FDFFF is padding). The next function, 0x7E501C5B, is USRTEST task A (13a, verified).
- **IMG image-job library 0x7E544AA9–~0x7E576D58** (not ~~~0x7E54D000–0x7E578000~~ (L1 2026-11-09)). It holds the job API, IMG_PRECON (pixel-defect correction (cmd 0) plus WB/colour calibration (cmds 1–4: they call the WB module 0x7E579C34–0x7E581FAF; cmd 4 reads `PRM_CAM_SPECTRUM_STL_R/G/B`; 14b §3) (D2 2026-11-09)), IMG_ART_P, IMG0_LOCAL and art CPU kernels. The `buff` manager ~0x7E576D59–0x7E579C33 (D2 2026-11-09) is a separate module (13a; anchors verified, whole-range membership inferred from the call graph).
- **Face FACE_* code (to 0x7E6FCA5F) and mcon 0x7E6FCA60–0x7E70787F** sit inside the "movie" row, not in the still-recording row (~~0x7E70B000–0x7E730000~~ 0x7E70B3F8–0x7E731584 (L1 2026-11-09)) (13e, verified).
- **OKAO PT 0x7E72CFA1–0x7E731584** (ends at the `ret` at 0x7E731582; libc `_ctype` follows at 0x7E731588; not ~0x7E732000) (13b, verified).
- **Statechart / Com_ / Dev / Ctg (C2 2026-11-09):** the `CmpSts_SingleStillShootingSequence_NEW` statechart ends at 0x7EB84344; the Com_ framework starts at 0x7EB84345 (`Com_EvSenderManager` module); `Dev*` part 1 ends at 0x7EB93422 (last string user `DevSor::stop()` 0x7EB93362) and the categories start at 0x7EB93423 (function-mode category getInstance; 14c §1 (D2 2026-11-09)), not ~0x7EB93A80 (13c §1, verified call edges).
- **OXF runtime 0x7EBA48BC–0x7EBA7BC0** (not "on to ~0x7EBA9xxx"; the first 84 bytes 0x7EBA4868–0x7EBA48BB are picture-file-creation helpers of `Dev*` part 2, and 0x7EBA7BB5 is the start of OXF's last function, which ends at 0x7EBA7BC0) (A5 2026-11-09). **OKAO Smart Skin 0x7EBA7BC1–0x7EBABF8D** follows it; it is not OXF (13b, 13c, verified bounds; the Smart Skin name comes from E-P5 strings).
- **C3D GL (DMP) library 0x7EE02095–0x7EE294B4** (the ~~194-entry~~ `{name, fn}` table ~~0x7F023C74~~ 0x7F023B8C, 223 slots (29 `egl*`, 194 `gl*`) (D2 2026-11-09), reaches glPointSize 0x7EE29468; 0x7EE21020 was only a round offset): not GUI; its only callers are ~~C3D~~ the 3D engine's GL back end 0x7EE2FF5E–0x7EE32698 (D2 2026-11-09) and the overlay C3D bridges. The GUI region 0x7ECA1020–~~~0x7ECC8000~~ 0x7ECCB7FF is data and padding, and GUI code starts at 0x7ECCB800 (D2 2026-11-09) (13d, verified call edges and bytes) (C2 2026-11-09).
- **zlib 0x7EE5F5F3–0x7EE619C6** (ends after `zmemcpy` 0x7EE619AC and two stubs) and ~~**C3D API from 0x7EE619C7**~~ the **C3D framework 0x7EE619C7–0x7EE8F4F3** (one module) (D2 2026-11-09); the old ranges "0x7EE5F5F3–0x7EE61F" and "0x7EE61C–0x7EE63" overlapped (08 §5, verified) (C2 2026-11-09).
- **AVPI 0x7EE8F4F4–0x7EECE318** (not ~~~0x7EE8F000–0x7EEA0000~~). ~~0x7EE63000–0x7EE8F4F3 before it is C3D-side code, one library with the C3D API (0x7EE63000 falls inside fn 0x7EE62F80) (A5 2026-11-09):~~ Before it is the C3D framework 0x7EE619C7–0x7EE8F4F3 (D2 2026-11-09) (L1 2026-11-09); block-0 code ends at 0x7EECE318 (13b, verified).
- 0x7F021020–0x7F034000 is not BASIC: GL name pools, libpng/zlib strings, then AVPI from ~~0x7F02F600~~ 0x7F02F684 (13b; layers in the regions table, 14a §1) (D2 2026-11-09).

**Boundaries from round D2 (2026-11-09; sections 14a–14e).** Also in the table above.
- **Load segments (14d §1, verified):** each code segment has its rodata after its code and ends with its own static-constructor table, which the walker 0x7E44B6B0 runs. Segment 1: code 0x7E4FE000–0x7E731584 (+ 0x7E8808C0–0x7E880F43), rodata 0x7E731588–0x7E8808BF, constructors 0x7E880F44 (24 B). Segment 2: code 0x7E8F5800–0x7EBABF8D, rodata 0x7EBABF90–0x7ECB083B, constructors 0x7ECB083C (76 B). Segment 3: code from 0x7ECCB800 (GUI first), constructors 0x7F033AC8 (180 B). The tables for segments 4/5 (0x7F06ADC4, 0x7F0EB484) are empty.
- **`.data` init image 0x7E8DA000–0x7E8F3113 → RAM 0x602A9B40–0x602C2C53** (102,676 B; the reset code copies it, constants at 0x7E4212B8–0x7E4212E0, checked). To find the users of a `.data` item, subtract 0x1E6304C0 and search for the RAM address (14d §3.8).
- **3D stack (14a §1, verified layer edges):** DMP EGL/GL 0x7EE02095–0x7EE294B4 → 3D engine core 0x7EE294B5–0x7EE5B5BB → image decoders 0x7EE5B5BC–0x7EE5D00C → libpng 0x7EE5D00D–0x7EE5F5F2 → zlib 0x7EE5F5F3–0x7EE619C6 → C3D framework 0x7EE619C7–0x7EE8F4F3 → AVPI. Only overlay B calls into C3D; the GUI never calls GL.
- **GUI code starts at 0x7ECCB800** (14d); CCommon starts at its ctor 0x7ECFF983, not 0x7ED00000 (14e §1).
- **CMIO blob 0x7E86DD80–0x7E8808BF** (header `CMIO` + 0xDC090001, 76,608 B, high entropy): the static ORF ImageProcessing block (inferred: UnknownBlock2), copied by 0x7E5586B9 from the ORF header builder 0x7E71969F. It ends where the code block 0x7E8808C0 starts (14d §3.2).
- **Overlay A:** DPS runs up to 0x7F0645C0; **0x7F0645C1–0x7F0691C5 is the red-eye correction library** (FACE cmd 5, from `play_face_redeye_adjust`), not a face-scoring library; the BASIC keyword table is at 0x7F0691C8 (13b, verified).

**Row edges from round L1 (2026-11-09; boundary lint).** The 1-MB window offsets (0x7E521020, 0x7E621020, 0x7E966000, 0x7EBA1020, 0x7EE21020) fall inside functions, so the rows above now start and end on function edges: the lens function 0x7E520E2D ends at 0x7E521132; the fcs function 0x7E620C6F ends at 0x7E6211E0; the PrintIM/Exif/MakerNote writer ends at 0x7E70B3F7 (0x7E70B3F8 is a rec init, inferred); code segment 1 ends with OKAO PT at 0x7E731584; the user-shell support code starts at 0x7E965FD1; the categories end at 0x7EBA0AA8; segment-2 rodata ends at 0x7ECB083B; the GL library ends at 0x7EE294B4. Four code ranges end where the function database runs on into data or padding: OKAO PT 0x7E731584, the code block 0x7E880F43, Smart Skin 0x7EBABF8D and AVPI 0x7EECE318. There the end is the last `ret` (checked in the bytes), and the database function goes on to the next page.

## 2. Firmware package and blocks

| Part | What it is | Basis |
|---|---|---|
| Block 0 (kind 0x100) | Main code for both cores | verified |
| Block 1 (kind 0x101) | 34 languages × 1,970 string ids, fonts and glyph data. A string id is an index into each language's pointer array; blobs load at 0xBFF3D000 | verified (e.g. id 207 = `Pixel Mapping`) |
| Block 2 (kind 0x106, "ARTFIL") | 2.25 MiB 6-bit noise texture, read only by Grainy Film (`art_filter_06_rough_monochrome`) | verified |
| Block 3 (kind 0x104, "FRAME") | 8 JPEG frame overlays, one per aspect and size | verified |
| `OM` tail | H8 firmware of the in-body image-stabiliser controller ("BC", from *bure*, Japanese for camera shake). Same scrambling and checksum as the OE blocks | verified format; role inferred, strong |

**What the updater checks** (section 02, verified):
- The card files it searches for are S (boot block), A (language), M (stabiliser), V (sound), D (C3D), T (pictures), E/G/H/W/E100 (main package), DATE/PICTURE1JPG and N.
- **Main package sections:** a maker byte `O`, a known type letter, the model id, a copy of the header in the trailer, and a 32-bit word sum of 0.
- **The model id for 'E' packages may be 0x1010 (E-PM2) or 0x1000 (E-PL5).** Hand-checked at 0x7E543ED8 / 0x7E543EE9. So the updater would **not** stop an E-PL5 main package; keep E-PL5 files off the card.
- **There is no version or downgrade check.**
- A `DATE????BIN` file is written to flash 0x40140000 with no checksum.
- Lens (`L???????BIN`) and strobe (`F???????BIN`) firmware come from the menu or over USB; the lens is updated in 128-byte packets.

## 3. Feature inventory

**Status:**
- **Active**: reachable in normal use on the E-PM2.
- **Hidden**: works, but only through debug or service paths.
- **Dormant**: complete code with no known way in on this body.
- **Stub**: the entry point exists but does nothing.

"(inf)" after a status means the status itself is inferred.

### Shooting

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| Camera core command interface | Active | `CamCommand` 0x7E628303, hash table 0x7E7AC020 | CAM_MAIN task is an empty `retf` (hand-checked); callers call cam.c directly | 03 |
| Shooting control (lock, release, live view) | Active | TAKE_MAIN/EXPOSE/FOCUS/FUNC; tables 0x7E791478, 0x7E7928B0 (32-slot hash tables keyed by **cmd + 1**) | e.g. 0x1xx lock, 0x4xx–0x7xx release, 0x9xx live view. The table keys are cmd + 1, so section 02's numbers are one too high (e.g. TakeExp 0x401 = `release_ready_end`) (D1 2026-11-09) | 02, 13e |
| AE in live view/movie | Active | EXP_MOVIE 0x7E68F0DD | 18×18 BV grid, face weighting, flicker detection (inf) | 03 |
| iAuto scene detection | Active (inf) | SDET 0x7E662DCB; decision 0x7E663EC4 | 12 scene types; ids (V, `dbgscnmode` help): 3 PROGRAM, 8 SPORTS, 9 PORTRAIT, 11 SCENERY, 12 NIGHT_SHOT, 17 SCENERY_PORTRAIT, 18 NIGHT_SHOT_PORTRAIT, 21 EVENING_SUN, 23 MACRO, 50 UNDERWATER_SNAP, 156 NIGHT_SHOT_MACRO, 157 SPOT_LIGHT (D2 2026-11-09) | 03, 14b |
| AF, 8 AF types, movie AF | Active | TAKE_FOCUS, FCS_MOVIE 0x7E610A65 | AF types from strings (inf) | 02 |
| Face and eye detection | Active | FACE_MAIN/FD/PT0, DISP_FRAME; FD = a hardware engine (registers 0x99600000, inf) | The eye step (PT) uses Omron OKAO (verified call flow (D1 2026-11-09)). Smile detection is **absent** (orphan name string only); the eye-retouch and contour modules are linked as stubs (D1 2026-11-09) | 03, 10b, 13b |
| Live Bulb / Live Time | Active | `cam_still_live_bulb.c` | Phase tables verified; update-interval code not found | 03 |
| Still pipeline | Active | REC_MAIN → REC_PREPRO → REC_IMAGE → REC_FILE | JPEG = 1, ORF = 3; bracketing over one exposure | 03 |
| Pixel Mapping (pixel-defect correction) | Active | IMG_PRECON 0x7E55F9B6, cmd 0 0x7E55FAE8 → kernels 0x7E55ECD8–0x7E55F959 | Lists from prm 0x7044/0x7052/0x7144 (`PRM_CCD_FIRST_PIXELDEFECT_*`); it is the CPU half of the menu item "Pixel Mapping" (207; link inferred from the prm names). IMG_PRECON is not generic pre-conditioning (D1 2026-11-09), but it is not only defect correction either: cmd 4 (0x7E580A54) computes channel gains from 65-point prm tables (disputed, deep dive pending) (C2 2026-11-09). **Resolved:** cmd 0 = defect correction; cmds 1–4 = WB/colour calibration (cmd 4: per-illuminant WB gains and colour matrices from `PRM_CAM_SPECTRUM_STL_R/G/B`) (D2 2026-11-09) | 13a, 03, 14b |
| Multi exposure | Active | SequencePartsMultiExposure; `api_rec_Bayer_MultiExp` | One stub call, but the real function is used | 06 |
| e-Portrait | Active | SequencePartsEportrait, CmpSts_EPortraitShootingEditer; FACE cmd 11 → OKAO Smart Skin 0x7EBA7BC1 | Beauty-preview helpers are stubbed. REC uses only the Smart Skin module (mask 1) (D1 2026-11-09) | 06, 13b |
| Art filters (12 in the E-PM2 menu: stored picture modes 100–109, 119 Key Line, 120 Watercolor) | Active | ART task 0x7E729E25; GUI↔stored tables 0x7E83F70C/0x7E844CC0; `art_GetFilterType` 0x7E71BD94 | Watercolor = `art_filter_21_pastel_art` (internal name "pastel"), Exif 33/34. Pop Art, Pale&Light, Light Tone, Cross Process use no code module (ISP only) | 09, 03 |
| Hidden art menu ids 110–118: Olympus compact "Magic Filters" (Fish Eye, Drawing, Soft Focus 2, Punk, Sparkle, compact Watercolor, Reflection, Fragmented) | Dormant | ids 111/115/117/118 named by the E-PL7 Exif writer (12/23/28/29); modules: Sparkle = star_light (its own image-engine cases load only values other codes share; no special tone curve, inferred) (A11 2026-11-09), Reflection = mirror (empty), Fragmented = composite (works: random tile scatter) | No GUI value, no colorTone name, no Exif value in E-PM2; reachable only via debug shells. Never in any PEN/OM-D menu checked (8 bodies) | 09, 09a, 09b |
| Art effects (star light, pin hole, frame, soft focus, white edge) | Active (inf) | `art_effect_10…50` | Frame effect uses block 3 | 03, 08 |
| Panorama (PC-stitched assist) | Active | SCN 14; SequencePartsPanorama | In-camera stitching absent (stub/no code) on all 8 bodies | 06, 10b |
| 3D Photo (MPO) | **Hardware-gated** | SCN 115 (selectable); `checkConnect3DLens` 0x7ECD7899 | Complete with a 3D lens; two-shot mode is a stub (three empty functions) | 10b |
| Interval shooting / time-lapse movie | **Dormant-complete** | Guard 0x7E969C11 (info 482), time-lapse builder 0x7E6D4597 | All code present; only the top-menu row is missing (E-PL6 inserts "Time Lapse Settings" after Multiple Exposure). Shipped on E-PL6, E-P5, E-M10, E-PL7 | 10a |
| HDR bracketing (HDR BKT, info 476) | Probably Active (inf) | Bracketing panel (group 15) | No code hides the row; exposures only, no HDR merge. Check on camera | 10a |
| Built-in and external flash | Active | STB_SEQ/EXTERNAL/CHARGE/ASSIST | Mapped from strings mostly (inf) | 02 |

### Movie

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| MOV (H.264) 1080/720, Fine/Normal | Active | settings 26225 = 3, 34145 = 6 / 3, 33105[7] | 20/17 and 13/10 Mb/s | 04 |
| Motion JPEG AVI 720p/VGA (also 320×240, 160×120 in code) | Active | `mov_rec_MJPEG.c` | 2 GiB cap; duration from setting 25812 | 04 |
| AVCHD (1080) | **Hidden (debug-only)** | Full record/playback path; CPU1 MOV_AVCHD/AVCHDI | Not in the movie-quality list (info 45: 6 entries, MOV/MJPEG only) on any of the 8 bodies | 04, 10c |
| Time limit 29 min / 4 GiB | Active | Computed at 0x7E6EDE08 (frame count); checked every frame at 0x7E6EE006 → event `RECMOVIE_TIME_LIMIT` | Hand-checked; fires 15 frames after the limit. Units: 512-byte sectors/s; audio overhead = 48 kHz stereo PCM. No file splitting | 04 |
| Movie effects: multi echo, one-shot echo, art fade | Active (inf for menu) | "KDG" engine, commands 70001–70003 | Fade 500 ms / 2000 ms | 04 |
| Movie art filters | Active | Picture modes 100–120 → art codes 70–183 | | 04 |
| "PSP" multi-window live view | Dormant (inf) | `mov_func_PSP.c`; API 0x7E988CDB | Background layer of a 4-window live view; reachable from `sdk api` only; probably the precursor of Photo Story (E-PL7+) | 10c |
| Movie cut/trim, still-from-movie | Absent | — | Only the time-lapse builder exists. (Movie tele-converter code does exist; reachability not traced, 10c) | 04, 10c |

### Playback and editing

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| Playback engine | Active | PLAY_MAIN 0x7E93BABF → LOAD/IMAGE/SOUND (table 0x7EBB6510) | | 05 |
| 23 edit modes (mono/sepia, trim, red-eye, shadow adjust, rotate, resize, image overlay, aspect, e-Portrait, RAW edit…) | Active (most) | Edit table 0x7EBB8D88; Edit*Component classes | Visibility per mode in section 06 table. Red-eye = FACE cmd 5 from `play_face_redeye_adjust` 0x7E94318E → overlay-A red-eye library 0x7F0645C1 (D1 2026-11-09) | 05, 06, 13b |
| 3D (MPO) playback | Partial (likely Active on a 3D HDMI TV) | `play_load_mpo.c`, 3D slideshow type, HDMI 3D query, "3D Show" panel | | 10d |
| GPU slideshow (photo "room" animation with logo intro) = **C3D** | Active (inf) | GUI start 0x7ED081AE → `startSlideShowGpu` → `CapGSld_GpuSlideShow` 0x7EA55350 → `api_play_Exec_C3d_Anime_*` → C3D tasks and scene code in overlay B → C3D framework 0x7EE619C7 → GL | Chosen when Effect ≠ 1 and the slideshow is not 3D (verified chain; which Effect label is 1 is open). Not C3D: `play_gpu.c` resize/rotate and the 3D-overlap transition (D2 2026-11-09) | 08, 14a, 14c |
| Slideshow with BGM, BGM import | Active | `:\BGM\*.WAV`, ≤ 14 files; `play_regist_bgm` | Import needs an Olympus authentication chunk (`IKEY`) | 05 |
| Playback transitions | Active | EFFECT/EFFECT_EXE | index zoom, fade, touch scroll… | 05 |
| Photo Surfing, Event View, Collage, person/GPS search | Stub | 46 `api_oldb_dummy_*` | Stub backend and no GUI path; no real backend on any of the 8 bodies | 06, 10d |
| Light box, opening-screen registration | Light box Active; opening screen Stub | `StDispLightBox*` (23 GUI calls); `api_play_dummy_Regist_Play_Rom` | | 10d |
| Calendar, light box, index, select, reserve print (DPOF), protect, erase | Active (inf) | Play*/Edit* components | | 06 |

### Audio

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| Codec WM8946, record/play, speaker | Active | AUD_MAIN 0x7E95BB4F | Shares a serial bus with the HDMI chip. Confirmed: SIO ch2 also carries the touch panel and the display VSC, with a GIO mux (D1 2026-11-09) | 05, 13f |
| DSP: wind cut, 32-coefficient ReTune, 5-band EQ, DRC, notches (incl. lens-zoom notch) | Active (inf for use) | coefficients from settings 29858–30354 etc. | Notches probably cut lens/stabiliser noise (inf) | 05 |
| Wind noise reduction | Active | Custom Menu I (table 0x7EFF7E80 (D1 2026-11-09)), info 434 → prm 0x7871 | Selects wind cut 0x7E951BDE or a plain high-pass filter | 10d |
| Audio watchdog | Active | AUD_WATCH_DOG | Force-stops on stalled audio DMA | 05 |

### Connectivity

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| USB mass storage, PTP, MTP, PictBridge | Active | PC_* tasks; `ptp_register` 0x7F08E975, 4 opcode sets | No InitiateCapture: no standard tethering | 08 |
| Firmware update over USB | Active | ops 0x9117, 0x9119, 0x911C, 0x9120–0x9125 (audit 2026-11-09) → FIRMUP_SRV | | 02, 08 |
| HDMI with CEC remote | Active | HDMI task 0x7E6BAF18 | Analog Devices transmitter, EDID | 08 |
| Touch panel (and its own firmware update) | Active; panel reflash **Hidden** (D2 2026-11-09) | TOUCHPANEL 0x7E6BCF84; reflash 0x7E6BD8B6 | The 470-record controller image is sent **only** by the debug command `disp tp boot_on` (U_SHELL, or ADJ 0x902B over USB); no automatic version check or update path (14d §3.1) (D2 2026-11-09) | 08, 14d |
| Eye-Fi | Active (inf) | EYEFI task, card control files | | 02, 08 |
| FlashAir "SmartPhone Connection" (SPC) | Active (inf) | SPC_MAIN 0x7F0A7AF7 | Edits `\SD_WLAN\CONFIG` | 07, 08 |
| Bluetooth via PENPAL ("cube") | **Active with the accessory attached** | BT_CTRL 0x7E8FF96E, gate 0x7E91367A | Gate = the "Cube" bit of the external-device byte, set when accessory ID 0x0103 answers on the accessory port. The E-PM2 **has** an accessory port: Olympus's v1.2 release notes add VF-4 EVF support. The earlier "no accessory port" was a product-knowledge error | 05, 10e, 11 |
| EVF (VF-2/VF-3/VF-4), SEMA-1, accessory-port menu | **Active with the accessory attached**; menu hidden by setting default | Accessory-ID scan 0x7E464850; info 394 = 0 hides the menu | VF-4 support was added in v1.2 (official release notes) | 10e, 11 |
| IEEE 1394 | Stub | PC_I1394, PC_1394PNP | Drain their queue and exit | 08 |

### Platform, debug and service

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| Boot sequence | Active | Boot task 0x7E44A043 → Usr0 (≈60 tasks) → USRSTART_* | Firmware-update boot path at 0x7E503DD4 / 0x7E544A6F | 01, 02 |
| S_SHELL system monitor | Hidden | 0x7E44E972; serial ports 0x9870/0x9830 = SIO logical ch5/ch1 (chosen by config byte 0x8FF00080); ch1 is also the EVF and PENPAL UART (D1 2026-11-09) | Started every boot; needs physical UART access | 01, 10f, 13f |
| U_SHELL (54 command families) | Hidden | table 0x7E7332B4; a second list 0x7E7326A4 with the same 54 handlers (own name-string copies) is used by `dbgall` 0x7E5020C8 (D4 2026-11-09) | Also over USB via ADJ op 0x902B: no model/setting/password gate, only a Storage/PTP connection and an ADJ session | 01, 10f |
| `mov`, `movp`, `movc`, `lens`, `cam`, `prmdbg`, `GUI Debug`, `sdk api` (635 commands) shells | Hidden | sections list each table | `prmdbg` can read/write any setting and save or erase banks | 01, 03, 04, 06, 07 |
| GUI debug menu (SS_DEBUGMENU) | **Hidden, gated** | SS 10, descriptor 0x7EFD1F94; entry 0x7EDABA14 | Entry found: Setup dialog 0x7EDFD665 posts 0x9628 only if getShippingInfo(4) = 1 → SS_MENU_MAIN HIDE_MODE; Up, Down, Left, Right, half-press, full-press, OK → SS 10. Whether a retail body passes the gate is unknown (D1 2026-11-09). Second HIDE_MODE sequence: OK held 2 s and MENU held 2 s (either order), then OK → `userMenuMainReset` path (inferred: a hidden reset); the 2 s long-press times are set by the HIDE_MODE entry 0x7EDABA6F (D2 2026-11-09) | 10f, 13d, 14e |
| BASIC interpreter | Hidden | BAS_MAIN 0x7F05C000 | Card scripts load only via the GUI debug menu or `sdk api`; a script saved to flash with the `ucr.` header runs at every BAS_RCU_SRV start | 01, 10f |
| Factory adjustment over PTP (ADJ) | Hidden | `adj_p15740_p.c`, 16 vendor ops 0x9005–0x902B | | 01, 08 |
| Self-adjust from card files (ADJSLF) | Dormant on shipped cameras (inf) | ADJSLF 0x7F087004 | Gated by PRM_MODE_SHIPS_ENABLE (prm 0x0DB1) = 0 plus wake reason SELF_ADJUST. The ADJSLF step `UnitCodeCam` 0x7F0B8D18 would set that flag to 1 (and the destination area), but only when calib tag 0x5781 reads 1; prm 0x5781 is a ROM constant 0 (10f §3, I) (C5 2026-11-09) | 01, 10f |
| Settings store | Active | getter 0x7E457C75, setter 0x7E457CED | 1,800 prm tags in 6 storage classes; table in `07-settings.tsv` | 07 |
| Level gauge, rotation | Active | PER_SLOPE, PER_ROTATE | SPI accelerometer | 01 |
| Developer test tasks | Dormant | USRTEST_A–D (`Hello World!!!`) | | 01 |

## 4. Fixed points

| What | Where |
|---|---|
| Runtime base of block 0 | 0x7E421020 |
| Task names (147) | block offset 0x4D222, `{u16 id, char[24]}`; name = `names[(id & 0x7FFF) − 1]` |
| CPU0 / CPU1 task tables | block offsets 0x17CB0 / 0x1C490, `{id, attr, exinf, entry, pri, stksz, stk}` |
| Settings getter / setter | 0x7E457C75 / 0x7E457CED (prm tags); Get/Set_CameraInfo 0x7E67F822 / 0x7E67F882 (info ids) |
| Movie format / quality / Fine-Normal | prm 26225 / 34145 / 33105[7] |
| Debug print | 0x7E4263E5 (a0 = string) |
| Firmware-update worker | 0x7E543DDE (model check at 0x7E543ED8) |
| Movie time limit | 0x7E6EDE08 (compute), 0x7E6EE006 (per-frame stop) |
| Menu tables | 0x7EFFE13C (top level), 0x7EFEF4FC (196 sub-item records; first read as 0x7EFEF50C, 114 items), Custom Menu A–J 0x7EFF7E80 (78 rows) (D1 2026-11-09) |
| English strings | block-1 offset 0x3781E0, pointer array 0x38B758 |

## 5. Corrections made during mapping

- **Task table.** First read one field off, and the last rows were renamed from their strings. Section 01 found the real `{id, …, entry, …}` layout from the boot code's labels. Checked in the bytes: the only TA_ACT row is the boot task.
- **Function database.** Pointer and integer tables in 0x7EEE–0x7F02 gave about 1,300 false functions. Offset-aligned pages hid the BASIC overlay. Both fixed: data pages now include tables, and pages are aligned to runtime addresses.
- **PENPAL / accessory port.** The first brief said the E-PM2 supports PENPAL; a correction then said it has no accessory port, so the code was dormant. **That correction was itself wrong:** Olympus's v1.2 release notes add VF-4 EVF support, which needs the accessory port. The PENPAL/EVF code is active when the accessory is attached.
- **Movie limit units.** "Inferred" in the first analysis; now settled as 512-byte sectors (section 04).

## 6. Main open questions

1. Answered in sections 09/10: art filters, AVCHD (no menu value) and interval shooting (no menu row). Still open: whether HDR BKT shows on the camera, and whether a retail body passes the SS_DEBUGMENU gate (the entry itself is found, section 13d (D1 2026-11-09)).
2. How the app ends a recording after `RECMOVIE_TIME_LIMIT`, and why Olympus specifies 22 min for Full HD Fine when the code's figure is 26.6 min.
3. The level of input 0x1709 on an E-PM2 board (would the Bluetooth stack ever start?).
4. The EXP_MOVIE message codes and Live Bulb timing. ~~WB_MOV (no strings)~~ WB_MOV is the task of the WB module 0x7E579C34–0x7E581FAF (14b §3) (D2 2026-11-09). IMG_PRECON is answered: pixel-defect correction (13a) (D1 2026-11-09) plus WB/colour calibration in cmds 1–4 (14b) (D2 2026-11-09).
5. Which USB menu setting selects PTP connection types 0–6, what "X3C" is, and the names of the 16 ADJ vendor ops.
6. Whether a retail body passes the debug-menu gate getShippingInfo(4) (the key sequence is found, 13d (D1 2026-11-09)), and which UART pads the shells use on the board. The self-adjust menu is reached only through the ADJSLF gate (10f).
7. What `udfu01` does exactly. It behaves as multiply-by-N in four places (sections 03 and 04), but that is not proven.

Each section ends with its own longer list.

# E-PM2 v1.6 firmware map

A map of what the main firmware contains and where. This is for learning only: nothing here was patched or flashed.

- **Labels:** **verified** = read in the code or bytes; **inferred** = from strings, names or layout only. Every claim keeps the label from the section it came from.
- **Sources:** the eight subsystem sections in `experiments/2026-11-08-feature-map/sections/` hold the detail and addresses. Hand spot checks are in that folder's `NOTES.md`.
- **Addresses:** runtime addresses. Block-0 offset = address − 0x7E421020 (base verified).
- **Tools:** `tools/fwmap.py build` builds the function database (about 66k functions). Then use `fn`, `str`, `range`, `xref` and `tasks`. `tools/disasm.py` disassembles any range.

## 1. Architecture at a glance

- **Two CPU cores, both running uITRON** (verified, section 01).
  - A task id holds the CPU number in bits 12–14. CPU0 has 147 tasks (table at block offset 0x17CB0) and CPU1 has 30 (table at 0x1C490).
  - `OlyTaSt` (0x7E449541) passes a CPU1 id to the other core. The same block-0 code runs on both cores; the crash handler reads the CPU id at address 0x8050.
  - CPU1 runs AVCHD encoding, art processing, the C3D 3D engine and an 11-task worker pool.
- **Layers, from bottom to top:**
  1. **Kernel wrappers.** `Oly*` names for tasks, event flags, queues and semaphores.
  2. **Drivers and peripheral tasks** (0x7E42–0x7E52).
  3. **Service tasks.** Lens, firmware update, TAKE_* (shooting control), strobe, files, REC_* (still recording), MOV_* (movie), PLAY_* (playback), AUD_* (audio), ART (art filters), FACE (face detection) and the PC/PTP connection tasks.
  4. **C camera API.** About 640 `api_*` functions at 0x7E675E64–0x7E68F048. Asynchronous calls go through `api_exec_start`, which uses a 36-entry funcno→queue table (section 03).
  5. **C++ application.** Statecharts on IBM Rhapsody's OXF runtime (inferred, strong): one event loop in HIGHLEVEL_MAIN and about 930 event classes (section 06).
  6. **GUI** (`GUI App`, CA_MAIN, 0x7ECA–0x7EE2). It reads and writes settings through an API object, then Get/Set_CameraInfo, then the prm store (section 07).
- **Link order is preserved.** The code of each source file is contiguous, and its strings follow in the same order (verified). `experiments/2026-11-08-feature-map/modules.tsv` places all 152 source-file names.
- **Overlays.** Part of block 0 is copied from flash at boot (Usr1). The BASIC/DPS and ADJ/PTP/USB ranges load only on demand (verified, section 01).

### Address regions of block 0

| Range | Contents | Section |
|---|---|---|
| 0x7E421020–0x7E4A0000 | Kernel wrappers, debug output, S_SHELL, flash memory, peripheral tasks (PER_*), interrupt and watchdog code, task tables (data) | 01 |
| 0x7E4E0000–0x7E521020 | Startup tasks (USRSTART_*), U_SHELL, UI input, LEDs, timers, lens communication helpers | 01, 02 |
| 0x7E521020–0x7E621020 | Firmware update, lens, battery, body stabiliser (BC), TAKE_* shooting control, strobe, files/DCF, Eye-Fi, movie AF | 02 |
| 0x7E621020–0x7E6A1020 | Camera core (`cam*.c`), the C camera API (`api_*`), EXP_MOVIE (AE), SDET (scene detection) | 03 |
| 0x7E6A1020–0x7E70B000 | Movie (`mov*.c`), plus the display, HDMI and touch-panel tasks | 04, 08 |
| 0x7E70B000–0x7E730000 | Still recording (`rec_*.c`), face detection, art filters and effects | 03 |
| 0x7E730000–0x7E8E0000 | Mostly read-only data (64% of pages): strings and tables for the modules above. Some code, e.g. the firmware-update result screen and LED at 0x7E8808C0–0x7E880E84 | 02 |
| 0x7E8E1020–0x7E8F5800 | Data (method-name pointer tables, padding) | 05 |
| 0x7E8F5800–0x7E966000 | Playback transitions, SERV_MAIN, Bluetooth/PENPAL stack, OBEX, playback engine (`play_*.c`), audio | 05 |
| 0x7E966000–0x7EBA1020 | C++ app layer: Cap*/Cmp* components, `sdk api` shell, picture database (stubbed) | 06 |
| 0x7EBA1020–0x7ECA0000 | OXF runtime, DevBlu device class; then vtables and app data | 05, 06 |
| 0x7ECA1020–0x7EE21020 | GUI, menus, live view and control-panel UI | 07 |
| 0x7EE21020–0x7EEE1020 | C3D engine, libpng 1.2.37, zlib 1.2.3 inflate, MP4 mux/demux | 08 |
| 0x7EEE1020–0x7F021020 | Read-only data (menu tables at 0x7EFFE13C / 0x7EFEF50C, GUI strings, vtables) | 07, 08 |
| 0x7F034000–0x7F05C000 | Padding (zeros, then erased flash) | — |
| 0x7F05C000–0x7F06B000 | BASIC interpreter and DPS (PictBridge) — on-demand overlay | 01, 08 |
| 0x7F06B000–0x7F0AB000 | ADJ / ADJSLF factory adjustment, PTP/MTP/USB stack, TPC, C3D bridges, SPC (FlashAir) | 01, 08 |

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
| Shooting control (lock, release, live view) | Active | TAKE_MAIN/EXPOSE/FOCUS/FUNC; tables 0x7E791478, 0x7E7928B0 | e.g. 0x1xx lock, 0x4xx–0x7xx release, 0x9xx live view | 02 |
| AE in live view/movie | Active | EXP_MOVIE 0x7E68F0DD | 18×18 BV grid, face weighting, flicker detection (inf) | 03 |
| iAuto scene detection | Active (inf) | SDET 0x7E662DCB | 12 scene types (inf) | 03 |
| AF, 8 AF types, movie AF | Active | TAKE_FOCUS, FCS_MOVIE 0x7E610A65 | AF types from strings (inf) | 02 |
| Face and eye detection | Active | FACE_MAIN/FD/PT0, DISP_FRAME | Eye step probably uses Omron OKAO (inf); smile detection is stubbed | 03 |
| Live Bulb / Live Time | Active | `cam_still_live_bulb.c` | Phase tables verified; update-interval code not found | 03 |
| Still pipeline | Active | REC_MAIN → REC_PREPRO → REC_IMAGE → REC_FILE | JPEG = 1, ORF = 3; bracketing over one exposure | 03 |
| Multi exposure | Active | SequencePartsMultiExposure; `api_rec_Bayer_MultiExp` | One stub call, but the real function is used | 06 |
| e-Portrait | Active | SequencePartsEportrait, CmpSts_EPortraitShootingEditer | Beauty-preview helpers are stubbed | 06 |
| Art filters (12 in the E-PM2 menu) | Active | ART task 0x7E729E25; filter-code table maps 21 menu ids | Pop Art, Pale&Light Color, Light Tone and Cross Process use no code module (inf: done by image-processor settings) | 03, 07 |
| Art filter code not in the E-PM2 menu: modules `art_effect_10_star_light` (menu id 115), `art_filter_1c_mirror` (117), `art_filter_1d_composite` (118), `art_filter_21_pastel_art` (120, two variants), and a third Pin Hole variant (code 108) | Dormant (inf) | Dispatch switch at 0x7E72A635 loads each entry; Mirror has its own pass table 0x7E85A56C (`art_mirror_pass1/2`) | Module names verified from strings. User-facing names (section 03 says Crystal, Mirror, Composite, Pastel) are **inferred**: no name table exists in block 0, and English block 1 has no such labels. The E-PM2 menu lists 12 filters (section 07) | 03, 07 |
| Art effects (star light, pin hole, frame, soft focus, white edge) | Active (inf) | `art_effect_10…50` | Frame effect uses block 3 | 03, 08 |
| Panorama (PC-stitched assist) | Active (inf) | SequencePartsPanorama | In-camera stitching is stubbed | 06 |
| 3D photo (MPO) | Dormant (inf) | rec_3d.c, CmpSts_3dImageController | Combine step stubbed | 03, 06 |
| Interval shooting / time-lapse movie | Dormant (inf) | Guard 0x7E969C11 (info 482), `startIntervalShooting` 0x7E98849B, time-lapse builder (MOV_EDIT task 0x7E6D4597) | Complete code. No menu record sets 482; every constant write of 482 stores 0. Myset and PTP paths not traced | 04, 06, 07 |
| Built-in and external flash | Active | STB_SEQ/EXTERNAL/CHARGE/ASSIST | Mapped from strings mostly (inf) | 02 |

### Movie

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| MOV (H.264) 1080/720, Fine/Normal | Active | settings 26225 = 3, 34145 = 6 / 3, 33105[7] | 20/17 and 13/10 Mb/s | 04 |
| Motion JPEG AVI 720p/VGA (also 320×240, 160×120 in code) | Active | `mov_rec_MJPEG.c` | 2 GiB cap; duration from setting 25812 | 04 |
| AVCHD (1080) | Unknown | Full record and playback path; CPU1 tasks MOV_AVCHD/AVCHDI | Whether the E-PM2 menu offers it is open | 04 |
| Time limit 29 min / 4 GiB | Active | Computed at 0x7E6EDE08 (frame count); checked every frame at 0x7E6EE006 → event `RECMOVIE_TIME_LIMIT` | Hand-checked; fires 15 frames after the limit. Units: 512-byte sectors/s; audio overhead = 48 kHz stereo PCM. No file splitting | 04 |
| Movie effects: multi echo, one-shot echo, art fade | Active (inf for menu) | "KDG" engine, commands 70001–70003 | Fade 500 ms / 2000 ms | 04 |
| Movie art filters | Active | Picture modes 100–120 → art codes 70–183 | | 04 |
| "PSP" multi-window live-view composite | Unknown | `mov_func_PSP.c` | Meaning of PSP unknown | 04 |
| Movie cut/trim, still-from-movie | Absent | — | Only the time-lapse builder exists | 04 |

### Playback and editing

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| Playback engine | Active | PLAY_MAIN 0x7E93BABF → LOAD/IMAGE/SOUND (table 0x7EBB6510) | | 05 |
| 23 edit modes (mono/sepia, trim, red-eye, shadow adjust, rotate, resize, image overlay, aspect, e-Portrait, RAW edit…) | Active (most) | Edit table 0x7EBB8D88; Edit*Component classes | Visibility per mode in section 06 table | 05, 06 |
| 3D (MPO) playback | Dormant (inf) | `play_load_mpo.c` | | 05 |
| Slideshow with BGM, BGM import | Active | `:\BGM\*.WAV`, ≤ 14 files; `play_regist_bgm` | Import needs an Olympus authentication chunk (`IKEY`) | 05 |
| Playback transitions | Active | EFFECT/EFFECT_EXE | index zoom, fade, touch scroll… | 05 |
| Photo Surfing, Event View, Collage, person/GPS search | Stub | 46 `api_oldb_dummy_*` | Hand-checked: log and return 1 | 06 |
| Calendar, light box, index, select, reserve print (DPOF), protect, erase | Active (inf) | Play*/Edit* components | | 06 |

### Audio

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| Codec WM8946, record/play, speaker | Active | AUD_MAIN 0x7E95BB4F | Shares a serial bus with the HDMI chip | 05 |
| DSP: wind cut, 32-coefficient ReTune, 5-band EQ, DRC, notches (incl. lens-zoom notch) | Active (inf for use) | coefficients from settings 29858–30354 etc. | Notches probably cut lens/stabiliser noise (inf) | 05 |
| Audio watchdog | Active | AUD_WATCH_DOG | Force-stops on stalled audio DMA | 05 |

### Connectivity

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| USB mass storage, PTP, MTP, PictBridge | Active | PC_* tasks; `ptp_register` 0x7F08E975, 4 opcode sets | No InitiateCapture: no standard tethering | 08 |
| Firmware update over USB | Active | ops 0x9117, 0x9119–0x9125 → FIRMUP_SRV | | 02, 08 |
| HDMI with CEC remote | Active | HDMI task 0x7E6BAF18 | Analog Devices transmitter, EDID | 08 |
| Touch panel (and its own firmware update) | Active | TOUCHPANEL 0x7E6BCF84 | | 08 |
| Eye-Fi | Active (inf) | EYEFI task, card control files | | 02, 08 |
| FlashAir "SmartPhone Connection" (SPC) | Active (inf) | SPC_MAIN 0x7F0A7AF7 | Edits `\SD_WLAN\CONFIG` | 07, 08 |
| Bluetooth via PENPAL ("cube") | Dormant (inf) | BT_CTRL 0x7E8FF96E, BlueSDK stack, OBEX/OBEX_ACP | Gate 0x7E91367A needs active-low input 0x1709 (hand-checked). The E-PM2 has no accessory port (product knowledge). The stack would load a Broadcom patch, support BIP/OPP/FTP and Apple iAP with an MFi chip | 05 |
| EVF VF-2/VF-3, accessory-port menu | Dormant (inf) | Accessory-port menu in the top-level table | No port on this body | 07, 08 |
| IEEE 1394 | Stub | PC_I1394, PC_1394PNP | Drain their queue and exit | 08 |

### Platform, debug and service

| Feature | Status | Where | Notes | § |
|---|---|---|---|---|
| Boot sequence | Active | Boot task 0x7E44A043 → Usr0 (≈60 tasks) → USRSTART_* | Firmware-update boot path at 0x7E503DD4 / 0x7E544A6F | 01, 02 |
| S_SHELL system monitor | Hidden | 0x7E44E972, serial port at 0x987000xx | ps, memory dump/put, OS objects, bus/DRAM tools | 01 |
| U_SHELL (54 command families) | Hidden | table 0x7E7332B4 | Also reachable over USB via ADJ op 0x902B | 01, 08 |
| `mov`, `movp`, `movc`, `lens`, `cam`, `prmdbg`, `GUI Debug`, `sdk api` (635 commands) shells | Hidden | sections list each table | `prmdbg` can read/write any setting and save or erase banks | 01, 03, 04, 06, 07 |
| BASIC interpreter | Hidden | BAS_MAIN 0x7F05C000 | Line-number BASIC; `api(code,a,b)` calls the camera API. `RCUOLYMP/*.RCU` scripts load from card, can be saved to flash and reload at boot | 01 |
| Factory adjustment over PTP (ADJ) | Hidden | `adj_p15740_p.c`, 16 vendor ops 0x9005–0x902B | | 01, 08 |
| Self-adjust from card files (ADJSLF) | Hidden | ADJSLF 0x7F087004 | `/NNNPRMnn/`, `wb_lv001.csv`, `*Calib.prm` | 01 |
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
| Menu tables | 0x7EFFE13C (top level), 0x7EFEF50C (114 sub-items) |
| English strings | block-1 offset 0x3781E0, pointer array 0x38B758 |

## 5. Corrections made during mapping

- **Task table.** First read one field off, and the last rows were renamed from their strings. Section 01 found the real `{id, …, entry, …}` layout from the boot code's labels. Checked in the bytes: the only TA_ACT row is the boot task.
- **Function database.** Pointer and integer tables in 0x7EEE–0x7F02 gave about 1,300 false functions. Offset-aligned pages hid the BASIC overlay. Both fixed: data pages now include tables, and pages are aligned to runtime addresses.
- **PENPAL.** The first brief assumed the E-PM2 supports PENPAL. It has no accessory port, so that code is dormant.
- **Movie limit units.** "Inferred" in the first analysis; now settled as 512-byte sectors (section 04).

## 6. Main open questions

1. Which E-PM2 menu items exist for AVCHD, interval shooting (info 482 via Myset or PTP), and each art filter id. The Custom Menu A–J item lists are built in code and not yet recovered.
2. How the app ends a recording after `RECMOVIE_TIME_LIMIT`, and why Olympus specifies 22 min for Full HD Fine when the code's figure is 26.6 min.
3. The level of input 0x1709 on an E-PM2 board (would the Bluetooth stack ever start?).
4. The EXP_MOVIE message codes, Live Bulb timing, IMG_PRECON and WB_MOV (no strings).
5. Which USB menu setting selects PTP connection types 0–6, what "X3C" is, and the names of the 16 ADJ vendor ops.
6. How the hidden debug menu and self-adjust menu are entered, and which UART the shells use on the board.
7. What `udfu01` does exactly. It behaves as multiply-by-N in four places (sections 03 and 04), but that is not proven.

Each section ends with its own longer list.

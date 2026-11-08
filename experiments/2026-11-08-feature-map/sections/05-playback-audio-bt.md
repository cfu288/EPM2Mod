# 05 — Playback engine, audio, Bluetooth (PENPAL), OBEX, effects

Scope: block 0, runtime 0x7E8E1020–0x7E966000, plus the string/rodata area 0x7EBA1020–0x7EBE1020.
Labels: **verified** = read in the code or bytes; **inferred** = from strings, names or layout only.

## Overview

| Range | Contents | Basis |
|---|---|---|
| 0x7E8E1020–0x7E8F57FF | Data, not code: a table of C++ method-name pointers (e.g. 0x7E8E1584 → `OpeningScreen::regist`, 0x7E8E156C → `SoundCtrl::registImportSound`), more pointer tables, 0xFF padding (0x7E8F3298…). The "functions" the database finds here call wild targets (0x5C49DBCC…). | verified (bytes) |
| 0x7E8F5800–0x7E8F5CE8 | CIC driver (`CIC_MUTEX`, `CIC_END`). It is used by `play_cic_decode_raw` 0x7E93D10F (`CicCtrl->ulCompAddr / ulRawAddr`). | inferred: RAW decompression codec |
| 0x7E8F5CE9–0x7E8F904E | EFFECT / EFFECT_EXE: transitions in playback | verified |
| 0x7E8F904F–0x7E8F926E | SERV_MAIN: a service that broadcasts state notices | verified |
| 0x7E8F926F–0x7E9035A7 | BT_CTRL ("btc"): connection control, OPP/BIP, pairing database, Apple CP access | verified |
| 0x7E9035A8–0x7E91367A | BT debug shell (`demo`), Broadcom patch-RAM download, HCI vendor commands, UART transport | verified |
| 0x7E913984–0x7E91CFFF | Stack callbacks, iAP (BTIAP task, `cp_*`, IDPS) | verified |
| 0x7E91D000–0x7E937FFF | iAnywhere-style "Blue SDK" stack (`OLYMPUS BlueSDK a4`), RFCOMM, tasks BTSTK/BTTIM/BTEVU/BTAPL | inferred stack identity; task entries verified |
| 0x7E938594–0x7E93BA6B | OBEX_ACP and OBEX tasks | verified |
| 0x7E93BA6C–0x7E94D2FF | Playback engine `play_*.c`, `playbuff.c` (PLAY_MAIN/IMAGE/LOAD/SOUND) | verified |
| 0x7E94D8A8–0x7E961C5A | Audio: bridge, control, WM8946 codec driver, DSP, FSC DMA, sequences, WAV/AC3 tools, AUD_* tasks | verified |
| 0x7E961C5B–0x7E966000 | `fsc_drv` (audio DMA), then the user shell (`User Shell Help Command`, memory dump/fill/verify) | inferred, not examined |
| 0x7EBA1020–0x7EBA6B03 | C++ device class `DevBlu_Bluetooth` (vtable 0x7EC91628), OS shims `BSE_*`/`BMQ_*`/`BEF_*`/`BTM_*`/`BMT_*`, state-machine runtime (`OMREactive`) | verified (vtable); class role inferred |
| 0x7EBA6B03–0x7EBE1020 | Strings and rodata for all of the above (e.g. `play_apical.c` at 0x7EBB66D7) | verified |

**Key result.** In this firmware, **"cube" is the code name of the Bluetooth/PENPAL feature** (verified).
The BT API refuses with `cube is disable\n` when the I/O-expander input 0x1709 is in its "active" state (see §3.0).
**Probably dormant on the E-PM2:** this body has no accessory port (coordinator note). The BT code is shared with the E-PL5. Nothing here shows it running on this body. The EXP-layer wrappers are named `api_cube_*_BT_*` (0x7E676693–0x7E676DA6) and call the `[btc api]` functions. The playback edit `play_cube_bt_resize` makes the image that is sent.

---

## 1. Playback engine (PLAY_MAIN, PLAY_IMAGE, PLAY_LOAD, PLAY_SOUND)

### 1.1 Task structure (verified)

| Task | Entry | Queue (id variable) | Role |
|---|---|---|---|
| PLAY_MAIN | 0x7E93BABF | 0x7E43ED5C | Receives requests and forwards them. Forwards each "execute end" reply to the caller. |
| PLAY_IMAGE | 0x7E9442E3 | 0x7E43ED5E | Draw / Edit / Mov Edit |
| PLAY_LOAD | 0x7E9456C5 | 0x7E43ED60 | Decodes files (JPEG, RAW, MPO, movie thumbnails, WAV); ROM/flash resources |
| PLAY_SOUND | 0x7E94B817 | 0x7E43ED64 | Plays sound; registers BGM |

Messages are 16 bytes: `{reply_queue, ?, cmd, param_ptr}`. They are read with 0x7E9485E2 (→ OlyQeRd) and sent with 0x7E9485F4 (→ OlyQeWr).
PLAY_MAIN uses a hash table at 0x7EBB6510 (16 × {key=cmd+1, handler}):

| cmd | Handler | Forwarded to |
|---|---|---|
| 0, 5 | 0x7E93BB2A | PLAY_LOAD (`receive Load request`); in PLAY_LOAD, cmd 5 = ROM load |
| 1, 2, 7, 8 | 0x7E93BB50 | PLAY_IMAGE (`receive Image request`) |
| 3 | 0x7E93BB7A | Done in PLAY_MAIN: it calls 0x7E6DDE3E (MOV code) and replies (`receive MOV request`) |
| 4 | 0x7E93BB65 | PLAY_SOUND (`receive Sound request`) |
| 10000 | 0x7E93BBAE | Completion from a sub-task. It is forwarded as a 12-byte reply to the original requester's queue. |
| other | 0x7E93BBC4 | Error 0x1B000001 via 0x7E426D4B |

Each sub-task posts `cmd=10000` back to PLAY_MAIN when it finishes. 0x7E93BC07 clears a per-task abort flag at 0x605D9204+4·n.

### 1.2 PLAY_IMAGE requests (verified)
`(12,msg)`: **1 = Draw** → `play_draw_main_exec` 0x7E9402E1; **2 = Edit** → `play_edit_main` 0x7E940D7C; **8 = Mov Edit** → `play_mov_edit` 0x7E9481DD. Value 7 is accepted by PLAY_MAIN, but PLAY_IMAGE only replies to it.

**Draw modes** (`u16 (38,req)`, 0x7E9402E1):

| Mode | Function | Source |
|---|---|---|
| 0 | `play_draw_normal` 0x7E940605 (2-step resize, rotate) | play_draw_normal.c |
| 0x91 | `play_draw_normal2` 0x7E940901 | play_draw_normal.c |
| 0x80 / 0x81 | `play_dig_wide_make_prim` 0x7E93FDBF / `_make_thumb` 0x7E93FFBE | play_dig_wide.c |
| 0x82 | `play_face_recog_draw_main` 0x7E943394 (`make recognition picture`) | play_face_recog.c |
| 0x83, 0x8E | `play_multi_raw_make_preview` 0x7E94832D | play_multi_raw.c |
| 0x90 | `play_gpu_draw` 0x7E943DDE (resize/resize2/rotate) | play_gpu.c |

**Edit modes** (`u16 (6,req)`; hash table 0x7EBB8D88, verified):

| Mode | Function | Feature (the GUI component name is inferred from the CmpE* strings) |
|---|---|---|
| 0x01 / 0x02 / 0x0C | `play_color_edit` 0x7E93D213 → `play_img_make_monochrome` / `_make_sepia` / `_adjust_vivid` (verified: 1 → monochrome, 12 → vivid) | Black & white / Sepia / Saturation |
| 0x07 | `play_trimming_edit` 0x7E94BE0B | Trimming (CmpETri) |
| 0x08 | `play_redeye_edit_main` 0x7E94920B (face recognition, then `play_redeye_redeye_adjust`) | Red-eye fix (CmpERed) |
| 0x10 | `play_apical_edit_main` 0x7E93BCCA (separate "wide" and "normal" paths, `make_lum`, face detection) | Shadow Adjust. Inferred: Apical is the vendor of the "iridix"-type tone mapping (CmpESha) |
| 0x80 | `play_rotate_edit_exec` 0x7E94AA5A (JPEG: round-mode tag; RAW: rewrite) | Rotate (CmpERot) |
| 0x81 | `play_resize_main` 0x7E949CA9 | Resize (CmpERes) |
| 0x84 | `play_pocket_main` 0x7E94873B (new prim + thumb + EXIF) | Unknown ("pocket"); inferred: a small-copy export |
| 0x85 | `play_regist_regist_pic` 0x7E949741 (resize → JPEG → flash, resource kind 5) | Register a picture. Inferred: the opening (startup) screen, from `OpeningScreen::regist` |
| 0x86 | `play_multi_raw_edit` 0x7E948237 | Image Overlay of RAW files (CmpEImg) |
| 0x87 | `play_change_aspect_edit_main` 0x7E93CE46 | Aspect (CmpEAsp) |
| 0x88 | `play_beauty_edit_main` 0x7E93C80D (calls FACE via `play_face_send_request` 0x7E943256 → 0x7E6FB5D2) | e-Portrait (CmpEBea) |
| 0x89 | `play_cube_bt_resize` 0x7E93D770 | Resize for Bluetooth sending |
| 0x8A | `play_cube_resize_save` 0x7E93D9F5 | Save the resized copy |
| 0x8B / 0x8C | `play_cube_set_jpeg` 0x7E93DC56 / `play_cube_jpeg_save` 0x7E93DDAA (`EXIF analyze`) | Inferred: store a JPEG that BT received |
| 0x8F | `play_sns_main` 0x7E94B6B5 → `play_sns_edit_upflag` (`update snsflag`) | Inferred: share-order flag (cf. `CBC_TRANSFER_IMAGE`) |
| 0x90 | `play_save` 0x7E94AE4B, or `play_save_raw` 0x7E94B011 when the buffer mode is 0x500 | Save the edited image |
| 0x91 | `play_multi_raw_save` 0x7E948591 | Save the Image Overlay result |
| 0x92–0x94 | `play_edit_raw_main` 0x7E940F1A | RAW data edit (CmpERaw) |

Each edit follows the same pattern: `*_check_edit_enable`, then size check, `make prim` (resize), JPEG encode (`play_img_encode_jpeg` 0x7E944DB9), `make thumb`, `*_make_exif_prm`, then `play_file_create_file` 0x7E9436E8. Progress goes through 0x7E948E05 (10–100 %) (verified in several of these functions).

**Mov Edit** (0x7E9481DD): sub-command 0 = start 0x7E947EEA, 1 = end 0x7E947F1C, 2 = record 0x7E947F4C. Record resizes YC frames (0x7E94470C) and gives them to 0x7E6D4524. Inferred: frames are fed to the MOV_EDIT encoder.

### 1.3 PLAY_LOAD kinds (verified, jump table 0x7EBBBEDC on `u16 (4,req)`)

| Kind | Handler |
|---|---|
| 0, 13 | `play_load_prim_exec` 0x7E946041 (full-size JPEG) |
| 1, 8, 14 | `play_load_thumb_exec` 0x7E945F3F. If the DCF node type byte (88) is 4 or 6 (movie), `play_load_movie_load_thum` 0x7E946975 is used instead. |
| 2 | `play_load_header_exec` 0x7E945D7D |
| 3, 9, 15 | `play_load_playpic_exec` 0x7E945DD7 (screen-size JPEG), or `play_load_movie_load_playpic` for movies. QT/MJPEG helpers: 0x7E9473BA, 0x7E9466BD. |
| 4 | `play_load_raw_raw_header_check` 0x7E94764F |
| 6, 7 | `play_load_raw_load_prim_raw` 0x7E947719 (ORF; WB data, packing method) |
| 10 | `play_sound_load` 0x7E94B8B3 (WAV attached to a picture). Inferred: voice memo |
| 11 | `play_load_mpo_exec` 0x7E946CC4 → `_analyze_header` (`Get APP2`, the MPO index) → `play_load_mpo_jpeg` | 
| 5, 12 | invalid (error 0x1809) |

**MPO = the 3D photo format** (inferred from the file name and the APP2 MP-index parse; `Notify_C3d_Img_Load_Finish` is in the EXP layer).

**cmd 5, ROM load** → `play_rom_main_exec` 0x7E94A33D (verified):

| Command / kind | Action |
|---|---|
| command 0, kind 0/1/5/6 | `play_rom_load_pic` 0x7E94A4F5: `play_res_read` 0x7E949A49 → JPEG decode (`load ROM image`, `load CONST or REGIST image`) |
| command 0, kind 8 | `play_rom_chk_bgm` 0x7E94A62D: scans `:\BGM\*.WAV` on the card |
| command 0, kind 7 | `play_rom_load_bgm` 0x7E94A8A5: loads one BGM WAV from `:\BGM\` |
| command 1, kind 1 | `play_rom_erase_resist_pic` → `play_res_erase_resist` 0x7E949BF0 (`erase registed image`) |

The flash-resource back end is 0x7E675700. 0x7E52220B and 0x7E522287 in the firmware-update region also call it (verified). Inferred: a writable resource area in flash.

### 1.4 PLAY_SOUND and BGM registration (verified)
`u16 (4,req)`: 1, 2, 4 → `play_sound_start` 0x7E94BA71. It takes a semaphore, initializes the device, starts playing, then waits for end / abort / stop / progress events. 3 → `play_regist_bgm` 0x7E9499A6.
`play_regist_bgm` writes the WAV with `play_res_write` (kind 2, index from the request) (`write to FLASH`). On success it copies a 32-byte entry into the blob setting **0xE001** with 0x7E457D34. 0x7E457D34 is the settings-blob writer: it looks up the ID with 0x7E45726D and copies the bytes.
So "import BGM" copies a card WAV into the camera's flash, and its name/info goes into setting 0xE001 (inferred meaning: `api_play_Regist_BGM_Sound`, `SoundCtrl::registImportSound`).

**BGM file rules** (in `play_rom_chk_bgm`, verified): at most **14** entries; directories are skipped; file size ≤ **6,145,024** bytes; the header check 0x7E95BF44 → 0x7E960B7B → `aud_tool_wav_judge_OLYMPUS_authentication` 0x7E960C93 must return **2**.
The legend string says `rinf(0:NG 1:OK(auh.NG) 2:OK(auh.OK)`. The check reads an EXIF `ecor` (maker) string and an `IKEY` chunk from the WAV, and compares them with `OLYMPUS IMAGING CORP.` / `OLYMPUS CORPORATION`.
So **only Olympus-authenticated WAVs can be imported as BGM** (the comparison with 2 is verified; the meaning comes from the legend string).

### 1.5 Support modules (inferred from names, entry/exit strings read)
`play_img.c` (0x7E94439F–0x7E9452AA): JPEG/EXIF header parse, decode, encode, resize_yc (33 callers), rotate, EditYC, BMP/RGBX/luminance/face formats.
`play_exif*` (0x7E941224–0x7E942D5C): EXIF tags, PIM (PRINT Image Matching) copy and defaults.
`playbuff.c` (0x7E94C398–0x7E94D261): buffer pool: `playbuff_alloc`, `_free`, `_get_yc` (49 callers), `_get_header`, `_get_aud`, `_get_work`, `_get_take_handle`.
`play_file_*` (0x7E9435B4–0x7E943D30): read / create / copy / update a file, with a "media full" check.
`play_take_get_*` (0x7E94BDAE–0x7E94BDF0): hand-off of buffers from shooting (rec view).
Debug dumpers 0x7E93ED45–0x7E93FD5D (`PLAY_DRAW`, `PLAY_EDIT`, `PLAY_SOUND`, `MOV_EDIT_INFO`, `bgm find list`) belong to a `play [com]` shell command.

---

## 2. Audio

### 2.1 Codec: Wolfson **WM8946** (verified from the function names `aud_dev_wm8946_*` 0x7E9568BF–0x7E95B3DD)
Register-level control: power, clock/FLL, sampling rate, ADC/DAC paths, input PGA, `mono_stereo` for the input and ADC path, mixers (MIXOUT L/R, MIXSPK L/R), speaker output and gain, LDO, video buffer (composite output), DSP mode, SE1 (LHPF, 3D, notch, DF1), SE2 (ReTune, 5-band EQ), DRC/ALC.
The register write `[reg]adr|dat` 0x7E95B361 has 200 callers. The serial bus is shared with the HDMI chip: `[ser-debug]SIOIIC_SEL > audio` 0x7E94F5C5 and `> HDMI` 0x7E94F64F (verified strings; the select line is driven by 0x7E461433).

### 2.2 Tasks

| Task | Entry | Pri | What it does |
|---|---|---|---|
| AUD_BRIDGE | 0x7E94D880 | 9 | Reads packets from queue 0x7E43E966 (via 0x7E95FF4C) into the buffer at 0xA07542D8, then runs `aud_bridge_recv_packet_analysis` 0x7E94D8A8 → `aud_bridge_exec_message` 0x7E94D968 or `aud_bridge_post_message` 0x7E94DACD (verified). Inferred: the packet entry point for other tasks (`res_qname` = reply queue). |
| AUD_BRIDGE_LITE_CPU0 | 0x7E94DC4C | 9 | Reads the word at 0x8050 (0 or 1; inferred: CPU number) and selects one of two 40-byte blocks at 0xA0754304 + 40·n. Waits on an event flag (OlyEv-style 0x7E960015) for a mask of 0x0F0F or 0x00F0. Bits 0–3 are passed on to another flag (0x7E960055). Bits 4–7 and 8–11 run and then clear one-shot `{fn, arg}` callbacks from the two blocks (0x7E94DDAA) (verified). Inferred: a lightweight cross-CPU callback relay; 0xA07… looks like uncached shared RAM. |
| AUD_MAIN | 0x7E95BB4F | 9 | Initializes (0x7E95BAC1), reads packets from queue 0x7E43ECCC, dispatches on the packet's first byte (hash 0x7EBC2664, verified), replies when the packet is synchronous (type 1) |
| AUD_COPY_DATA | 0x7E94E4D8 | 9 | Waits on flags 0x33. Bits 0x30 → `aud_copy_data_main_play_copy` 0x7E94EBF3; bits 0x03 → `_rec_copy` 0x7E94E729. Copies PCM between the file buffer and the DMA ring (verified). |
| AUD_WATCH_DOG | 0x7E96188B | 11 | Every 500 ms (verified): if FSC status = 2 (playing) or 3 (recording) and `aud_dev_fsc_ctrl_check_intr_stop` reports more than 1 missed interval, it logs error 0x06106001/2 and forces a stop (0x7E961A1C play / 0x7E961A42 rec). It also runs repeat play/rec tests in debug mode. Debug modes: `0:WD OFF 1:WD ON 2:WD ON(2s video command stop)`. |
| AUD_LATE_RISER | 0x7E9502CE | 11 | Debug test: reads setting **10442** index 0/1/2 (action, wait_time, work_info), sleeps, then plays `HOGE.WAV`, records, or changes the volume (verified). Inferred: a "start late after boot" test hook; no effect on normal use. |
| PLAY_SOUND | see §1.4 | | |

**AUD_MAIN command classes** (verified table): 0x02/0x03 → `aud_seq_qplay` 0x7E95E558 (power on/off). 0x24–0x26 → `aud_seq_io` 0x7E95D097 (volume, output device, video on/off). 0x41/0x45/0x46/0x49 → `aud_seq_play` 0x7E95D654 (init/start/stop/end). 0x82–0x86 → `aud_seq_rec` 0x7E95E676 (init/start/stop/wav_style/get_wav_info).
Other layers: `aud_bridge_*` 0x7E94D8A8 (packet interface for other tasks), `aud_con_*` 0x7E94DDDC (power, init/end play, output device, volume), `aud_dev_fsc_*` 0x7E955882 (FSC = the audio DMA/interface block: AI = input, AO = output interrupts).

Output devices (debug usage string): `0:SPK+LINE 1:SPK 2:LINE 4:HDMI`. Debug playback/recording: channel 1/2, 8–24 bit, 8000–48000 Hz.
`aud_ikey_to_wavetype_*` 0x7E95CAE4 maps a WAV's `IKEY` string to a "wave type" (UI sound, short sound, etc.). Inferred: each sound type has its own volume and route (`aud_seq_io_get_wave_type`, `force_spk_flag`).

### 2.3 DSP filters (verified structure; the meaning of each parameter is inferred)
`cmd_set_dsp_param_on` 0x7E9510BE (inputs: on_off, `ims_active_pattern`, input/output device, `rec_or_play`) calls these sub-blocks. With `param_read=1` each sub-block reads coefficients from camera settings through 0x7E457C75. Otherwise it uses defaults in ROM (e.g. windcut defaults at 0x7EBC1192).

| Sub-block | Function | Setting IDs read |
|---|---|---|
| DF1 (digital filter) | 0x7E9516F8 | 30290, 30306, 30338 |
| 3D (stereo widening) | 0x7E9518DD | 30034 |
| LHPF | 0x7E951ADF | 30018 |
| **Wind cut** (an LHPF in SE1) | 0x7E951BDE | **56004** (3 values per entry) |
| **ReTune** (32 coefficients `re_tune_cxx[0..31]`, SE2) | 0x7E951CF0 | 30162 |
| DRC/ALC | 0x7E952119 | 13393, 13409, 29858–29970 |
| **5-band EQ** | 0x7E9526BE | 30194–30274 |
| **Notch filters** (`notch_a[0..3]`, `notch_m[0..3]`, several banks) | 0x7E952D1A (5,000 bytes) | 30050–30130 |
| **Lens-drive noise reduction**: `noisereduction_for_lens_sub_zoom_drive_notch` (`moving_pattern`) | 0x7E9540A2 / 0x7E954162 | 30050, 30114, 30130, 30354 |
| Notch for playback "user sound", per wave type | 0x7E95464F | 30050–30130 |

Inferred meanings: ReTune and the 5-band EQ correct the small speaker. The notch filters remove the tonal noise of the lens motors and the stabilizer during movie recording. This is why the notch block has a "zoom drive" variant chosen by `moving_pattern`.
`aud_ims_active_pattern_get_ims_active_pattern` 0x7E95CD13 (verified logic): during movie recording (wav_mode 0 or 2) it reads setting **34145** (`mode_quality_movie`). Quality 3 or 6 → pattern 5; qualities 0/1/2/4/5 → pattern 1.

### 2.4 Formats
WAV read/write: `aud_tool_wav_*` 0x7E960B7B–0x7E9614C1 (RIFF / LIST INFO INAM ICRD / `exif ever0221 erel etim ecor emdl` chunks). Recording writes these chunks (`aud_seq_rec_command_rec_wav_style`).
**AC-3**: `aud_tool_ac3_*` 0x7E95F036–0x7E95F3CE (sync-info parse, decode). Inferred: the Dolby audio of AVCHD playback (`SDRAM_AC3_ADR`).

---

## 3. Bluetooth (PENPAL PP-1, code name "cube"); probably dormant on the E-PM2

### 3.0 What enables it (verified code path; hardware meaning inferred)
- Every BT entry point (22 callers: all `[btc api]` functions, module power-up 0x7E8FE4B0, deinit 0x7E8FE5A9, the stack-event handler 0x7E8FFB15, the UART receive path 0x7E912F55) first calls **`cube_enabled` 0x7E91367A**.
  That function returns 1 only when `0x7E509CA3(0x1709) == 0`. If it returns 0, the caller prints `cube is disable` and returns.
- 0x7E509CA3 is the generic status-signal reader (it is also used for `APPEVENT_TRIG1 STATUS`). ID **0x1709** is entry 4 of status group 11 (descriptor 0x7E735628 → list 0x7E7353C0; IDs 0x1706/0x1708/0x1709/0x170A/0x170C/0x170E; state bytes in RAM at 0x604F3BF0).
  The other IDs of this group are read by `per_gio_ioe_read` 0x7E50C517, so group 11 holds **I/O-expander (IOE) input pins**. The software override 0x7E50A6F2 only acts on status IDs 2 and 12, not on 0x1709.
  So the gate is a **hardware input line, not a model check or a menu setting** (verified as far as the IOE table). Inferred: the PENPAL detect line of the accessory port.
- The BT tasks are in the static task table (139 rows), so they exist at boot. But the module is only brought up on request: `bt_comm_start` 0x7E8FD075 → 0x7E901260 → 0x7E8FE4B0.
  0x7E8FE4B0 checks `cube_enabled` **before** the HCI reset, the patch-RAM download (0x7E8FE226 → `bt_config_set`) and the BD_ADDR write (verified branch at 0x7E8FE506).
  Not verified: what level IOE pin 0x1709 has on an E-PM2 board, and whether the E-PM2 GUI ever offers the BT menu. No model-ID check was found on this path.


### 3.1 Layers (verified call chain)
`DevBlu_Bluetooth` C++ methods (0x7EBA29E3–0x7EBA3243, vtable 0x7EC91628: sendImage, searchDevice, requestPairing, sendPinCode, receiveImage, getPairingDeviceList, setMyDeviceName, …)
→ EXP layer `api_cube_*` (0x7E676693–0x7E676DA6)
→ `[btc api]` 0x7E8FD075–0x7E8FD82A
→ BT_CTRL task → Blue SDK → HCI over UART → Broadcom controller in the accessory (on bodies that have an accessory port).
Each API function also has a second caller, the debug shell `demo` 0x7E9035A8 (`bluetooth feature's demo`).

**api_cube functions** (names verified): Start/End_BT_Communication; Start_BT_Communication_Send/Recive/Pairing; Abort; Set_BT_PIN_CODE; Start_BT_Data_Send / Data_Receive; Accept_BT_Data_Receive; Get_BT_Transfer_Progress; Get/Delete/Change_Name of the pairing information; Get_BT_Pairing_Regist_Number; Delete_All_BT_Infomation; Get/Set_BT_MySelf_Name; Get_BT_Search_Device_Number/Info; Stop_BT_Search_Device; Regist_BT_Pairing_Device; Calculate_Transfer_PictureSize (0x7E676E9F → `play_cube_resize_judge` 0x7E93D5D1).

### 3.2 Tasks (entries verified)

| Task | Entry | Function |
|---|---|---|
| BT_CTRL | 0x7E8FF96E | Waits on flag 0x7E43EC4E, mask 0x1F. 0x10 → timer `bt_ctrl_timer_timeout` 0x7E901462. 0x08 → stack-event queue 0x7E43EDF0 → 0x7E8FFB15 (inquiry results, ACL connect, service query, pairing mode, HCI errors). 0x01 → iAP response 0x7E91B4F5 / 0x7E91CD59. 0x02/0x04 → request queue 0x7E43EDEE → 0x7E900560 (API requests, OPP/BIP). |
| BTSTK_TSKID | 0x7E92F5F7 | Stack loop: calls 0x7E915C4A, then waits on flag 0x7E43EC48 (10 s timeout) while the run flag 0x602AEEBD = 1 |
| BTTIM_TSKID | 0x7E92F345 | Stack tick: counter at 0x7DAF2F5C, one-shot callback, health check 0x7E9014C6 every 100 ticks |
| BTEVU_TSKID | 0x7E9375B4 | Waits on flag 0x7E43EC4A (mask 14, 1 s); runs HCI/transport events (0x7E913984) |
| BTAPL_TSKID | 0x7E923FD2 | One shot: if bit 1 of 0x602AEE98 → 0x7E923B0F (a Blue SDK test client: `OLYMPUS BlueSDK a4`, BIP put of `OLYMPUS_TST_OBJ`); bit 2 → an empty stub. Inferred: a vendor sample/test application. |
| BTIAP_TSKID | 0x7E91A0C2 | iAP transfer: flag 0x7E43EC54, mask 0xFF; retry `DevDataTransfer`, `DevDataTransfer timeout!!!` |
| OBEX / OBEX_ACP | 0x7E93ADFD / 0x7E938DF2 | §4 |

### 3.3 Controller bring-up (verified from HCI bytes)
- `bt_dev_hci_reset` 0x7E9132B2 sends `01 03 0C 00` (HCI_Reset).
- `bt_config_set` 0x7E9126CC calls 27 functions (0x7E904B2E–0x7E911EFD). Each one stores bytes into the TX buffer at 0x605CD215 and sends it with 0x7E912E84. The first is `01 4C FC 8B 58 75 08 00 …` = **HCI vendor 0xFC4C Write_RAM** at 0x00087558. The last (0x7E912680) is `01 4E FC 04 FF FF FF FF` = **0xFC4E Launch_RAM**. This is the **Broadcom patch-RAM** format, so the PENPAL controller is a Broadcom chip and the camera stores its patch (inferred vendor; the opcodes are verified).
- `bt_dev_wrt_addr` 0x7E913335: `01 01 FC 06 <6 bytes>` = Broadcom Write_BD_ADDR. The camera writes the BD address into the module (`send bd_addr to module` 0x7E8FE4B0).
- `bt_dev_upd_baud` 0x7E91343D: `01 18 FC 06 00 00 <u32>` = Update_UART_Baud_Rate, with 3,000,000 (0x2DC6C0) or 1,500,000 (0x16E360); other branches test 1,000,000 and 230,400.
- 0x7E8FEDBB checks that a BD address is `00:01:13:13:xx:xx` or `00:01:13:14:xx:xx` (`… isn't olympus bd address`; 00-01-13 is the Olympus OUI). It is called from the address validator 0x7E8FDF21.

### 3.4 Profiles (SDP records verified in rodata)

| Record | Address | Content |
|---|---|---|
| BIP Imaging Responder | 0x7EBAD290 | UUID 0x111B, L2CAP/RFCOMM/OBEX, profile 0x111A v1.0, name "Imaging" |
| OBEX Object Push | 0x7EBB4D08 | 0x1105, "OBEX Object Push" (next to the string `BtServerGeneral`) |
| OBEX File Transfer | 0x7EBB1340 | 0x1106, "OBEX File Transfer" |
| iAP | 0x7EBB5651 | 128-bit UUID `00000000-DECA-FADE-DECA-DEAFDECACAFF` (Apple iAP). Just before it (from 0x7EBB55EC) are SPP 0x1101, DUN 0x1103, LAN "LAN Access using PPP" and others from a stock table. |

Whether the FTP and LAN records are registered at run time is not traced.
In use (verified strings in BT_CTRL): `bluetooth OPP/BIP server start`. OPP push 0x7E901EF1 (`opp_push start`, `send to %02x:…`); vObject check 0x7E902561 (rejects vMessage and vCard).
BIP 0x7E8F9AC4 / 0x7E8FB4D7 (`x-bt/img-img`, `img-thm`, `img-capabilities`, `img-listing`, `img-properties`, `img-monitoring`); `Initiator put image` 0x7E8FB9F5. The capability XML (`<imaging-capabilities … encoding="JPEG" …>`) is built by 0x7E90261D and parsed for the remote's pixel sizes (0x7E9032C3, `can't pasrse pixel width`).
So the camera **sends JPEGs by OBEX Object Push or BIP Image Push, and can receive images** (`api_cube_Start_BT_Data_Receive`, `acp_recv_info`, `play_cube_set_jpeg`). Search results record per device whether it has OBEX and serial service (`… %s obex %d serial %d`).

### 3.5 Pairing and the device database (verified strings and structure)
- Security: SSP is turned on or off by `BT_SetSecurity` (0x7E925B4F / 0x7E926620). Numeric comparison: `Numeric = %06d`, `SEC_UserConfirm`. Legacy PIN: `sec_req_callback(SECEVT_PIN_REQ)`; `api_cube_Set_BT_PIN_CODE` 0x7E6769A4 → 0x7E8FD120 (`pin:%02x %02x %02x %02x`).
- Link keys: DDB add/delete 0x7E8FDDD5 / 0x7E8FDE76 and the record merge 0x7E8FD899 (`match search info and add record`, `reregist link key`, `add record after missing key`). Each record has a BD address, a 16-byte key and a name (dump 0x7E8FE953: `idx cre srv1 srv2 key adr name`).
- The pairing list is in a file (`bt_info_file_t`, `file read error`). Its maximum number of entries is not found.

### 3.6 Apple iAP and the authentication coprocessor (verified register access; identification inferred)
`cp_*` functions 0x7E8FC5E3–0x7E8FCF2F read registers through 0x7E8FC496. That function takes a semaphore, selects I2C channel 2 (0x7E6BAF45; the same helper is used by HDMI code), and does a write-then-read at device byte **0x22** (7-bit 0x11). 0x7E8FCE28 reads registers 0x00–0x03 into `cp_ver`, `cp_fwver`, `cp_ap_mjrver`, `cp_ap_mnrver`.
That matches the Apple authentication coprocessor 2.0 (address 0x11: device version, firmware version, protocol major/minor). Other strings name the certificate pages, challenge, signature and `cp_auth_stat`.
IDPS (accessory identification) 0x7E91C69D sends: name `OLYMPUS PENPAL`, maker `OLYMPUS IMAGING CORP.`, External-Accessory protocol **`jp.co.olympus.acp`**, and `YL62NBMG6M` (inferred: the bundle-seed ID of the matching iOS app).
So **the camera with the PENPAL is an MFi iAP accessory over Bluetooth**, for an Olympus iOS app (inferred). Where the CP chip sits (camera board or PENPAL) is not shown.

---

## 4. OBEX and OBEX_ACP (verified strings; protocol meaning inferred)
- **OBEX** task 0x7E93ADFD (`OBEX`, states IDLE / SERV / CLIE / ERR 0x7E93B700, `[OBEX]D2P` 0x7E93B267, `[OBEX]P2D` 0x7E93B2C2). It reports errors to iAP (`[OBEX]iAP NotifyERR` 0x7E93AF19, called from the iAP handler 0x7E91CD59).
  Operation tables 0x7E93AA8E / 0x7E93ABC5: `connect`, `disconnect`, `confirm`, `getnamelist`, `put00acp`…`put03acp`, `get00acp`…`get03acp`, `putpic`.
- **OBEX_ACP** task 0x7E938DF2 (`OACP`): server operations 0x7E939461; client operations `obex_acpl_cli_op_send_picture_info` 0x7E938624 and `_send_picture` 0x7E938731; init sequence 0x7E93915B.
- Inferred: "ACP" is an Olympus application protocol carried as OBEX inside the iAP session (`jp.co.olympus.acp`). The camera sends picture info, then the picture, to the phone app. The debug shell also has `acp_send` / `acp_recv`.

---

## 5. SERV_MAIN (verified)
Entry 0x7E8F904F. It waits on flag 0x7E43ECA8 for bits 0x01 or 0x10.
- 0x10: control queue 0x7E43EE68 → `serv_stateinfo_ctrl` 0x7E8F912F. com 1 adds a queue ID to a subscriber list (at most 8, at 0x605C1CF8, count at 0x605C2318) (0x7E8F915E). com 2 removes one (0x7E8F9187). Sender `SERV_S2` 0x7E8F9226 is called from 0x7F0862F2 (PC/USB region).
- 0x01: notice queue 0x7E43EE66 (8-byte notices) → 0x7E8F90EC (`SERV_OLW`) writes each notice to every subscriber queue (OlyQeWr 0x7E4492B9). Sender `SERV_S1` 0x7E8F91DD is called through 0x7E68CCBD from the REC (0x7E701D27), HIGHLEVEL (0x7E995C0B) and GUI (0x7EA1F7BF…) code.

So SERV is a small **publish/subscribe service for camera state changes**. Which states it carries is not decoded.

---

## 6. EFFECT / EFFECT_EXE: playback transitions (verified)
- **EFFECT** 0x7E8F5D04 reads queue 0x7E43EDFA. cmd 0 → 0x7E8F6B37 (set/prepare), 1 → 0x7E8F6E64 (start), 2 → no-op, 3 → 0x7E8F6F39 (stop), 4 → 0x7E8F6FE3 (set "continue"; `[EFCT_EXE]TP SCROLL CONTINUE IMGBUFF MAX`), 5 → 0x7E8F7090 (start continue).
  The senders are the EXP functions `api_play_Set_Effect` 0x7E685F6E, `Start_Effect` 0x7E686011 (cmd 1), `Stop_Effect` 0x7E686034 (cmd 3), `Set_Effect_Continue` 0x7E686057, and `Start_Effect_Continue` 0x7E6860FD (cmd 5).
- 0x7E8F6B37 chooses the output frame size for the display device and TV setting 49953: 720×480, 800×600, 1024×768, 640×480, 640×436, 640×524, 720×576, 1280×720, 1920×1080 (table also at 0x7E80E2AC).
- **EFFECT_EXE** 0x7E8F6A60 waits on flag 0x7E43EC62 and runs one frame step for each bit: 0x8, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200 (the 0x100 and 0x200 bits have two variants each, chosen by flags at 0x605C22D8). 0x80000000 = finish.
- Effect types (from the EXP setters `set_effect_*`): **index_zoom, slideshow_fade, 3d_overlap, osd_slide, tp_slide, tp_scroll**, plus common parameters. The debug shell `effect` (0x7E8F5EF1) has `slide`, `overlap`, `index`, `tpsl/tpslc` (touch-panel slide, continue) and `tpsc/tpscc` (touch-panel scroll, continue).
  "TP SCROLL" is the touch-panel scroll of playback images. Which bit runs which effect is not mapped.

---

## Open questions
0. Does IOE input 0x1709 exist on the E-PM2 board, and at what level? Does any E-PM2 GUI path reach `api_cube_*`? (This would confirm that BT is dormant.)
1. `play_pocket_*` (edit 0x84): which menu item is it? And edit 0x8F "sns flag": is it share-order or an Eye-Fi/FlashAir flag?
2. What `play_dig_wide` (draw 0x80/0x81) and the "wide" paths of the Apical and other edits handle (panorama? 16:9?). `play_util_chk_wide` 0x7E93D0DD has 16 callers.
3. The image sizes for BT sending: the size tables are in RAM (0x602AB98C/B4/DC, three aspect groups), and the modes use 1536 and 1024. Find where these tables are initialized.
4. Where the Apple CP chip is (camera I2C channel 2 vs. the accessory), and whether iAP runs over RFCOMM through the DECA-FADE SDP record (the registration call is not traced).
5. Maximum paired devices, and where `bt_info_file_t` is stored (a file on internal flash?).
6. The meaning of the DSP setting IDs (29858–30354, 13393/13409, 56004): factory-adjusted or fixed? And the meaning of movie quality 3/6 for `ims_active_pattern`.
7. PLAY_SOUND sub-commands 1, 2, 4 (voice memo vs. BGM vs. preview), and what PLAY_MAIN cmd 3 (0x7E6DDE3E) does in the MOV code.
8. The 0x7E8E3E3C–0x7E8F57FF block: what the data is (it may include the 0xFF-padded BT or CIC tables).
9. The mapping of EFFECT_EXE bits to the six effect types.

# 04 — Movie subsystem (record, formats, effects, playback, edit)

Scope: block 0 runtime 0x7E6C33B5–0x7E6F4518 (mov.c … mov_sub.c), plus the movie API shims at 0x7E681D87/0x7E686E96 and the time-limit chain into 0x7E5B38BC.
Labels: **verified** = read in the code or bytes; **inferred** = from strings, names, layout or arithmetic only.
`udfu01 N,dX` / `udf01 dY,dX` are treated as multiply. This is **inferred but strong**: `index × 3003` (90 kHz ticks per 29.97 fps frame, 0x7E6EE9EE), `index × 28` as a struct stride (0x7E6EE9D8), `seconds × fps / 600` (0x7E6F06F7) and `secs × 600` (QuickTime-style 1/600 s) all make sense only as multiplies.

## Overview

- **Two encoder paths.** (1) H.264 through an "AV middle" library (`AVSCA_*`, `MovmidApi_*`, SCA_TASK/MP4LIB) that writes either QuickTime MOV (`[QT]`, `MOOV`, `QT_FILE`) or AVCHD (`MOV_AVCHD`, `MOV_REC_AVCHD`, `MOV_FILE`). (2) Motion JPEG in AVI, written by the firmware's own code (`mov_rec_MJPEG.c`). **Verified.**
- **The format is setting 26225** (3 = MOV, 2 = AVCHD, anything else = MJPEG). **Verified** at 0x7E6ED536 and 0x7E6ED571.
- **The quality is setting 34145** (3 = 1280×720, 4 = 640×480, 5 = 1920×1080 AVCHD, 6 = 1920×1080 MOV). **Verified** at 0x7E6ED021 and 0x7E6D8317.
- **Fine/Normal is setting 33105, index 7** (1 = the higher bitrate). **Verified.**
- **Time limit.** It is computed once at record start (0x7E6EDE08) as a frame count. Each frame is checked against it (0x7E6EE006). Reaching it posts app event 0x04070026 `RECMOVIE_TIME_LIMIT`. The app layer then ends the recording. **Verified** up to the event post; who issues RECORD_END is **inferred**.

## 1. Movie modes, bitrates and limits

### 1.1 Quality code to mode (all verified unless marked)

| Format (26225) | Quality (34145) | Size (code) | Fine / Normal bitrate (0x7E6EE4A2) | Time-limit rate, sectors/s, Fine/Normal (0x7E6EDE08) | Cap `a3` (s) | QT ulMaxRecTime (0x7E6D82EF) |
|---|---|---|---|---|---|---|
| 3 MOV | 6 | 1920×1080 | 20,000,000 / 17,000,000 | 4883 / 4151 (= 20.0 / 17.0 Mb/s) | 1740 | 1,800,000 |
| 3 MOV | 3 | 1280×720 | 13,000,000 / 10,000,000 | 3174 / 2442 (13.0 / 10.0 Mb/s) | 1740 | 1,800,000 |
| 3 MOV | 4 | 640×480 | 4,000,000 (one rate) | 977 (4.0 Mb/s) | **7200** | 7,200,000 |
| 3 MOV | 5 | 1920×1080 in the QT setup only | — | *rejected* (`[QT] Parameter Error quality`); result 0 | — | 1,800,000 |
| 2 AVCHD | 5 | 1920×1080 | peak 24,000,000 / 19,293,799; avg 20 Mi / 17 Mi bit | 5860 / 4711 (24.0 / 19.3 Mb/s) | 1740 | n/a |
| 2 AVCHD | 3 | 1280×720 | peak 19,293,799 / 16,567,501; avg 17 Mi / 13 Mi bit | 4711 / 4045 (19.3 / 16.6 Mb/s) | 1740 | n/a |
| MJPEG | 3 | 1280×720 | per-frame JPEG size from setting 60356[q] | own formula (§1.3) | setting 25812 | n/a |
| MJPEG | 2 or 4 | 640×480 | " | " | " | n/a |
| MJPEG | 1 | 320×240 | " | " | " | n/a |
| MJPEG | other | 160×120 | " | " | " | n/a |

Notes:
- The MJPEG sizes are set in `mov_rec_capture_start` 0x7E6F0009 (0x7E6F00B2…). They match the `mov` debug help: "QUALITY 1: QVGA 2: VGA 3: HD; FPS 15/30/60". **Verified.**
- AVCHD writes two fields: 0xA0753564 = peak (24 M / 19.29 M / 16.57 M) and 0xA0753568 = average (20,971,520 = 20 Mi; 17,825,792; 13,631,488). Their names (`ulMaxBitrate`/`ulBitRate`, printed by 0x7E6D8FB8) are **inferred**. MOV writes the same value to both fields.
- The time-limit rates are exactly the encoder peak bitrates divided by 4096 (512-byte sectors × 8 bits). So the routine is in **sectors/s**. **Verified** arithmetic; the sector unit is **inferred**.
- MOV frame rate: the QT setup writes 2997 (29.97 fps) for every quality (0x7E6D8355). **Verified.**
- AVCHD frame rate: the AVCHD clip parser knows `VideoFormat 1080i:4 720P:5` and `FrameRate 29.97:4 59.94:7` (0x7E6E2582). So AVCHD 1080 is 60i and 720 is 60p. **Inferred** from those strings; the AVCHD encoder frame-rate setup was not traced.
- QT AV parameters (0x7E6D822C, struct at 0x60730694). **Verified values; field names inferred** from the print order in 0x7E6D8FB8:
  - eTimeUnit=1, eTargetData=1, eHeaderMode=5.
  - ulUpper=0, ulLower=0xFFFFFFFF. This looks like a 64-bit max file size of 4 GiB−1 (**inferred**).
  - ulEndCutTime=500, ulWriteSize=1 MiB.
  - ftyp brand `qt  `, minor version 0x20110700.
- **AVCHD on the E-PM2.** The whole AVCHD record and play path exists. Whether the E-PM2 menu can select format 2 was not checked. See Open questions.

### 1.2 The time-limit computation (builds on ../2026-11-08-disassembly/NOTES.md)

Call chain at record start (**verified** call edges):
1. MOVREC_TASK reaches the state `state_aud_wait` 0x7E6EE106. `record_start` 0x7E6ED5FC sets it when message 16 = MOV_CMD_RECORD_START arrives: it writes 0x7E6EE106 into the state word 0x605B1F48.
2. → `0x7E6EEE0C`: zeroes the context 0x605B1D1C (139 words) and fills it. +22 = quality, +24 = setting 60370[q], +30 = fps, +26/+28 = settings 33073/33057.
3. → `0x7E5B3795(d0 = setting 33378, d1 = quality, a0 = 4, a1 = 3)` → 0x7E5B38BC. This function computes free space as clusters × sectors-per-cluster minus reserves (`udf01 d2,d1` at 0x7E5B392C).
4. → `0x7E6ED571(quality, free)`. It dispatches on format: 2/3 → **0x7E6EDE08**; else → 0x7E6EF27C (MJPEG).

0x7E6EDE08 writes into the context returned by 0x7E6ED536. That is 0x605B1D1C for MOV/AVCHD and 0x605B1FA4 for MJPEG (**verified**):
- (32) and (36) = free-space time × 30. Both get the same value: `d0` is stored twice; `mov d3,d1` does not change it.
- (40) = min(limit, 4 GiB-cap time, free-space time) × 30 = **max frames**.
- Return value = free-space seconds × 600.
- Unknown quality → `a3` keeps its initial 0 → (40) = 0.

Then:
- `state_aud_wait` checks `(40,ctx) == 0`. If so it sets 0x602ADFF4 = 3 and posts an error/limit event: RECMOVIE_BUFFER_LIMIT 0x04070027 or RECMOVIE_ERROR. Both are posted from this function (0x7E6EE181…); which one goes with which condition was not traced. It also sets the check-enable flag 0x605B1FA2 = 1 (0x7E6EE160). **Verified.**
- Per frame, `0x7E6EE9BC` (called from the QT/AVCHD encode loop 0x7E6EDB8D) does four things. **Verified.**
  - Calls the check **0x7E6EE006**.
  - Builds the YC frame descriptor for the encoder. Y plane width 1920/1280/640; UV offset +2088960 (1920×1088), +921600 or +307200; PTS = index × 3003.
  - Sends it with command 0x1105 to the encoder queue (0x7E6EECA6).
  - Increments the frame count (96,ctx).
- **0x7E6EE006 is where the time limit stops recording.** If the flag 0x605B1FA2 == 1, the count (96) ≥ 30 and (40) ≤ count − 15, it does three things. **Verified.**
  - Sets 0x602ADFF4 = 5 and clears the flags 0x605B1FA2 and 0x605B1D19.
  - Prints `[AVCHD] APPEVENT RECMOVIE_TIME_LIMIT`.
  - Calls `0x7E880EFF(0x04070026, 0)`.
- **The 4 GiB cap has no separate check in the H.264 path.** The term (filecap 8388608 − reserve)/(rate + overhead) is folded into (40). The library's own `AVSCA_INF_REC_FILESIZE` / `DIV_FILESIZE` / `BITRATE_OVER` callbacks are only logged in the QT callback (0x7E6D8C9C…0x7E6D8CB6: print, then return). **Verified.** The library's ulMaxRecTime (30 min / 120 min, units **inferred** ms) is a backstop above 1740 s.
- **Display.** `api_movie_CalculateQualityTime_Record_Movie` 0x7E681D87 returns (40) × 600 / fps(30,ctx). `api_movie_Get_Time_Record_Movie` 0x7E681DC7 returns elapsed (552,ctx). `0x7E6EDF9D`, only when byte 0x605B1FA2 == 1, adds 600 to (552) (or sets (552) = (96)/fps × 600 when mode byte (3) == 106) and posts `RECMOVIE_UPDATE` 0x04070100. **Verified.** "Each second" is **inferred** from the units (600 = 1 s); the function is an AVCHD callback (slot +52) (audit 2026-11-09).
- **App side.** The four events 0x04070026/27/28/0x04070100 are also loaded as constants in 0x7EA42F9B. That function constructs a set of listeners, so it is probably the app subscriber (**inferred**). The step from the event to MOV_CMD_RECORD_END was not traced.

Overheads (**verified** constants; meaning **inferred**):
- MOV: 375 sectors/s = 192,000 B/s. That is exactly LPCM 48 kHz × 2 ch × 16 bit. The QT audio parameters (0x7E6D84EC) confirm it: 48000 Hz, 2 ch, 16 bit, 1,536,000 b/s.
- AVCHD: 47 sectors/s ≈ 192 kb/s. This fits an AC-3 2-ch audio track (**inferred**).
- Reserves: MOV 832 sectors (2624 for VGA), AVCHD 400.

**22 min (spec) vs 26.6 min (code), Full HD Fine MOV.**
- The code gives (8388608 − 832)/(4883 + 375) = 1595 s = 26.6 min, below the 1740 s cap.
- One hypothesis fits the spec: 4 GiB / (24 Mb/s + 1.536 Mb/s) = 1345 s = 22.4 min. 24 Mb/s is the AVCHD Fine peak. The spec may assume a worst-case peak rate for both formats.
- Nothing in the MOV code uses 24 Mb/s. So on MOV the code's estimate and stop point are 26.6 min, unless the encoder's real VBR output fills 4 GiB first. If it does, the stop comes from somewhere the code here does not show. **Unresolved.**

### 1.3 MJPEG (AVI) limits — verified

- `0x7E6F0808(quality, fps)` returns min((0x80000000 − header)/bytes_per_s, setting 25812[idx]) × 600. That is a **2 GiB AVI cap**, plus a duration taken from settings. If the setting is 0, the default is 51,840,000/600 = 86,400 s.
- The index is 0 for q3/q4. q2 gives 0 at 30 fps, else 1. q1 gives 2 at 30 fps, else 3. If setting 33378 == 4, +4/+8/+12 is added, chosen by (80) of 0x7E5B6463.
- `bytes_per_s` (0x7E6F08A8) = round512(frame + 8) × fps + 192,008 (when audio flag 0x605B21DA == 2) + an index term. The per-frame size is setting 60356[q]. Art code 83 multiplies it by 3 (q3) or by 2 (others) (0x7E6EF1FB).
- `capture_start` sets max_sample 0x605B1FC4 = min(free time, limit) × fps / 600 (0x7E6F06E6). Zero → "max_sample=0 ERROR!!! DISKFULL".
- `mov_rec_MJPEG_update` 0x7E6F0C38 writes each `00dc` chunk (constant 0x30306463). When the frame count 0x605B2004 ≥ max_sample it returns 0x3800. `record_normal` 0x7E6EF5E7 then posts TIME_LIMIT 0x04070026 through 0x7E6F0399. "Video buff FULL" returns 0xFF03 → BUFFER_LIMIT 0x04070027. Both move the state to `errorstop` 0x7E6EFA79; 0xFF06 moves it to `fullstop` 0x7E6EFA99.
- The default values of the settings tables (25812, 60356, …) live in RAM tables (0x603A0E38/0x603A8E38) filled at boot by 0x7E457152. They are not in this region.

## 2. Recording pipeline

| Task / thread | Entry | Role (evidence) |
|---|---|---|
| MOV_TASK | 0x7E6C33B5 | Command loop 0x7E6C3A0B, jump table 0x7E7FDA70 (cmd 1..65). **Verified** |
| MOVREC_TASK | 0x7E6ED0E6 | Recording state machine. The state pointer is stored as an immediate (0x605B1F48 for MOV/AVCHD); idle 0x7E6ED43A. **Verified** |
| MOVREC_FILE | 0x7E6F21D1 | `[MOV_FILE]` MEDIA_OPEN/WRITE/FILE_CLOSE (0x7E6F227D). Also dispatches `[QT_FILE]` stream commands 0x7E6D6B40 (OPEN/READ/WRITE/SEEK/GET_FILE_PATH/SET_USRDATA). **Verified** |
| MOV_AVCHD (2nd table, entry 0x7E6D4E01) | 0x7E6D4F1C | AVCHD record + play commands to AVSCA. **Verified** strings |
| MOOV (2nd table, 0x7E6D568F) | 0x7E6D56FA | QT moov/stream writer: DFS_Stream*, ring buffer. **Verified** strings |
| QT ENCODE (2nd table, 0x7E6D554A) | — | "[QT] ENCODE Abort Packet". **Verified** string |
| MOV_BRIDGE (cfg ~~0x8088~~ 0x8087, pri 4: record 0x7E438D08 = {0x8087, 0, 0, 0x7E6CE4AC, 4, 0x400, 0x604DF780}, and Usr3 starts it with the id at 0x7E43E94C (coverage C4 (L1 2026-11-09))) | 0x7E6CE4AC | The loop reads its DTQ (0x7E6DDB14) and calls the handler 0x7E6CE517, which routes AVCHD_RECORD_*/MEDIA_WRITE/FILE_OPEN/CLOSE and PLAY_* between app, MOV_AVCHD and file. "task terminate" is printed in 0x7E6CE47B. **Verified** |
| MOV_SUB_TASK | 0x7E6F43E2 | Runs `img_exec_sub` jobs (0x7E6DAC97). **Verified** |
| MOVART_TASK | 0x7E6CBEBC | img_exec + `mov_kdg_exec` (movie effects). **Verified** |
| MOVCOLOR / MOVCOLOR_SUB | 0x7E6D0906 / 0x7E6D11EB | Colour calc with hysteresis (§3.4). **Verified** strings |
| ~~"IMG0_LOCAL" (cfg 0x8E, pri 11)~~ MOV_EDIT (cfg 0x84, pri 11) (L1 2026-11-09) | 0x7E6D4597 | ~~The config table names this task IMG0_LOCAL, but its code prints `[MOV_EDIT]`.~~ Its code prints `[MOV_EDIT]`. It is the time-lapse AVI builder (§5.3). ~~MOV_EDIT has no config row of its own; "MOV_EDIT" appears only as a queue name (0x7E50518C).~~ Its record 0x7E439C20 is {0x84, 0, 0, 0x7E6D4597, 11, 0x400, 0}, and Usr3 starts id 0x84 with the label `MOV_EDIT` (0x7E505289). 0x8E is the id of the next record: the {entry, pri, size, stack, id} layout puts every id one record too late. IMG0_LOCAL is task 0x808D at 0x7E575D41 (IMG library) (tasks.tsv) (coverage C4 (L1 2026-11-09)). **Verified** |

The second-table entries come from 28-byte records at 0x7E43D4BC…; the IDs ~~0x9008/0x9009/0x900D assume the main table's `{entry, pri, size, stack, id, …}` layout (**inferred**)~~ are 0x9007 (0x7E6D4E01), 0x9008 (0x7E6D568F) and 0x900C (0x7E6D554A): the records are {id, 0, 0, entry, pri, size, stack}, and Usr3 labels these ids MOV_AVCHD, MOV_AVCHDI and MOV_ENCODE (**verified** bytes, coverage C4 (L1 2026-11-09)). The queue names (MOV_BRIDGE, MOV_AVCHD, MOV_AVCHDI, MOVREC_FILE, MOV_ENCODE, MOV_REC, MOV_EDIT, MOV_P_IMG, MOV_PLAY, MOV_SPLY, MOV_DISP) are created at 0x7E50518C. **Verified** strings.

**MOV_CMD numbers** (MOV_TASK table, **verified**; names from the `[MOV] CMD …` strings and the `mov exec` names):

| Cmd | Name | Handler |
|---|---|---|
| 1, 3 | THROUGH_START | 0x7E6C3F53 → 0x7E6C40F5 (live view for movie) |
| 2 | THROUGH_END | 0x7E6C3F6A |
| 5 / 6 / 7 | THROUGH_MULTI_START / END / ROTATE | 0x7E6C3CED / 0x7E6C3E14 / 0x7E6C3E05 |
| 16 | RECORD_START | 0x7E6C3F85 → 0x7E6C40F5 + param copy 0x7E6ECF9A |
| 17 | RECORD_END | 0x7E6C3F9A |
| 18 | PARAM_UPDATE | 0x7E6C3E22 |
| 19 / 20 / 21 / 22 | KDG_START / END / STOP / READY | 0x7E6CB0FB / 0x7E6DB2D6 / 0x7E6DB375 / 0x7E6DB034 |
| 32, 33, 34 | (unnamed) mov_buff YUV keep/free | 0x7E6C5934, 0x7E6C3FA8, 0x7E6CF60F |
| 64 / 65 | BUFFERING_START / END | mov_buff_yuv_buffering_start/end 0x7E6CF7B7/0x7E6CF837 |
| other | `[MOV]->[TAKE]MOV_CMD_UNDEF` → reply 0x3803 | |

**Record parameter snapshot.** 0x7E6ECCAF copies about 30 settings into 0x605B1CC0…:
- 26225 → +0x1E; 34145 → +0x10; 33105[7] → +0x2C; 38017/49169 → art mode/variant.
- The anti-shake flag 0x605B10AC → +0x34.
- The short record descriptor 0x605B1CC4 = {format, quality, fine} is filled by 0x7E6ED021. **Verified.**

**H.264 files.**
- `MovmidApi_cmd_rec_init/start/end/free` are at 0x7E6D80B3/0x7E6D8554/0x7E6D860B/0x7E6D8668. The QT callback `USR_ScaCallback` (**0x7E6D8900**) handles AVSCA_RSLT_* and AVSCA_ERR_*; 0x7E6D886A is `MovmidApi_SetMakersInfoPrivateData` (AVSCA message 0x10C), not the callback (D1 2026-11-09).
- QT user data (0x7E6D5F55) writes an `OLYM` atom with `prms` (ArtFilterMode, ExposureMode, PictureMode, Scene, WB shift, iAuto). A `thmb` thumbnail and a `scrn` screennail come from 0x7E6D6438 (JPEG encode of a frame). **Verified** 4CC constants and strings.
- Path format `%c:\DCIM\%s\%s` (0x7E6D7370). **Verified.**

**MJPEG files.** The AVI is written by the firmware itself:
- States: `mov_rec_write_start` 0x7E6F0E25, `build_header` 0x7E6F11E3, `00dc` chunk writes 0x7E6F0D88/0x7E6F0C38, `build_footer` 0x7E6F1ED2, `chainwrite` control 0x7E6F20D7.
- Names: `make_file_name` 0x7E6F071B (`xxxOLYMP`), `last_file_delete` 0x7E6F1129.
- States (fnNext pointers): MJPEG idle 0x7E6EF3D3, aud_wait 0x7E6EF3ED, first_frame 0x7E6EF507, record_normal 0x7E6EF5E2, userstop 0x7E6EF7F2, userstop_for_edit 0x7E6EF89E, finish_1 0x7E6EF958, do_nothing 0x7E6EF9A7, finish_2 0x7E6EF9BD, errorstop 0x7E6EFA79, fullstop 0x7E6EFA99 (audit 2026-11-09). **Verified** strings and state pointers.

**File split.** No code that splits files into several parts was found. When a limit is reached the recording stops (TIME_LIMIT event); it does not continue in a new file. **Verified for the paths read; absence elsewhere is inferred.**

## 3. Movie art filters and effects

### 3.1 Art filters in movie (MOV_ART, mov.c) — 0x7E6CBFD3…0x7E6CDB83
- `0x7E6CBFD3(variant, src)` maps the picture mode (100–120 = Art Filters) to an internal art code. It uses two jump tables, 0x7E7FF05C (variant 0) and 0x7E7FF008 (variant 1). Examples: 100→70/79, 104→74/83, 106→86/88, 110→145/146, 120→181/183. 101 and 113 share a code. **Verified.** The art-code names are not in this region.
- Per-filter helpers. **Verified** strings; product names **inferred**:
  - colour tone (`MODE_COLORTONE`)
  - dramatic tone buffer (0x7E6CC6EE)
  - line-YC buffers for `ligneclair` (= Key Line, **inferred**) and `pastelart` (0x7E6CD4B7/0x7E6CD6B8)
  - `mov_art_set_color_yc_param`, `set_line_yc_param`, `set_artpacket` (skip CLIP / SIMPLE_1ST)
- `mov_image_process` 0x7E6C6853 prints "Effect OFF", "toyphoto ON for 1st", "filter ON for 1st" and "simple & Frame ON for 1st". **Verified** strings. "toyphoto" is chosen when the art code at 0xA07507CC is 73 or 82 (73 is a Pin Hole code in section 09; 82 is not identified); "filter" vs "simple & Frame" depends on the word 0x605B0394. **Inferred:** these are the art effects (Pin Hole/Toy, filter, Frame); "1st" more likely names a first pass (compare `SIMPLE_1ST` at 0x7E6CCBE1) than the first frame (audit 2026-11-09).
- Art code 88 clears 0x605B1F80 in the QT path (0x7E6EDDE9). Art code 83 inflates the MJPEG frame budget (§1.3). **Verified**; meaning **inferred**.
- `mov_apical.c` 0x7E6CB9B8: `[MOV_APICAL] THM2LUM img_exec`. A luminance map from the thumbnail, probably Apical iridix-style tone mapping (**inferred**).

### 3.2 Movie effects (MOV_KDG, mov_kdg.c 0x7E6DAF9A–0x7E6DCB0D)
KDG is the effect engine for echo and fade. The abbreviation is not expanded anywhere; "KDG" is undecoded.
- `mov_kdg_exec` 0x7E6DB6D1 (in MOVART_TASK) dispatches. **Verified:**
  - 70001 → `mov_kdg_multi_echo` 0x7E6DC059
  - 71002 → `oneshot_init` 0x7E6DC2BA, 70002 → `mov_kdg_oneshot_echo` 0x7E6DC2E9
  - 70003 → `mov_kdg_transition` 0x7E6DC555 (art fade, **inferred**)
- Effect type (the KDG_START argument, from `mov exec 10 <n>`): 0 ONESHOT → 2, 1 TRANSITION → 3, 2 MULTIECHO → 1. **Verified.**
- `mov_kdg_get_effect_type` 0x7E6DC934 takes fade times from 0x7E550CDF/CE5/D18/D30: type 1 = 500 ms, type 2 = 500 ms, type 3 = 2000 ms, type 5 = 2000 ms. **Verified**; what type 5 is remains unknown.
- Memory comes in two modes, "through" (live view) and "movie" (recording): `mov_kdg_memory_alloc/free` 0x7E6DBC3C/0x7E6DBE25.
- **No movie tele-converter code** was found in this range. The only "digitaltele" string is a field in the i-Finish parameter dump 0x7E6D3EA6. **Verified absence by string search.**

### 3.3 Anti-shake for movie (`ansh`)
- `mov ansh <flag> <x> <y>` parses three numbers. Only the flag is stored: 0x7E6CFFDB writes 0x605B10AC. It then prints "shift_x,shift_y:unsupported.(please define MOV_TRACE_BC.)". **Verified.**
- The same flag is written by 0x7E6CFCCF, with a second value going to 0xA07511DC. That function is called from the stabiliser module at 0x7E5965B9…0x7E5994A8. 0x7E6ECF8A copies the flag into the record params. **Verified.** The IS behaviour itself is outside this range.

### 3.4 Colour (MOVCOLOR) and other image steps
- MOVCOLOR runs `MOV_COLOR_CALC1/2/3` and `MOV_COLOR_HYST` (0x7E6D0E51/0x7E6D10E7) on a timer, with a hysteresis time set by `movc timer`. It dumps `IMG_IFINISH_CALC_IN`/`HYSTERESIS` parameters. So it computes **i-Finish** colour for movie (**inferred** from the parameter-dump names).
- `mov_fnr` (0x7E6D4A7B–0x7E6D4BD5) allocates a frame noise-reduction buffer. **Verified** strings.
- `mov_paint.c` (0x7E6DDBE5/0x7E6DDD15) fills black rectangles in the sub and main images (`rectangle_*_img_pro Black`). Probably aspect/letterbox masking (**inferred**).
- A crop table at 0x7E7FD1A8 (10-byte records) gives the 640-wide live-view crops: 4:3, 640×426 (3:2), 640×360 (16:9), 480×480, 600×480, 560×480, 576×480, 640×456, 360×480. **Verified bytes.**

### 3.5 "PSP" / multi-window (mov_func_PSP.c 0x7E6D75F5–0x7E6D7F01)
- Background types JPEG/FILL/black come from a resource (`mov_image_decode_background` 0x7E6D7AE4). `mov_multi_top_left/step` lay out areas with per-area WB (`usMwbId`, `ucAWBFlag`). **Verified** strings.
- It is reached from the MOV sequence selector 0x7E6F417B → 0x7E6F42D1/0x7E6F4373 (sequence types 8/9) and pairs with MOV_CMD 5/6/7 THROUGH_MULTI_*. The SDK help has "MultiWindow BackGround Jpeg" (0x7E9A6CB3).
- So PSP is a **multi-window live-view composite**. What "PSP" stands for is unknown (**inferred**).

## 4. `mov` debug shell (command table at 0x7E732784: "mov" → 0x7E6D15A0)

All rows are **verified** from the strcmp chain in 0x7E6D15A0. Help text: 0x7E8008B6.

| Command | Handler | What it does |
|---|---|---|
| `debug [MODE OPT]` | 0x7E6D19C7 | Sets mov_debug_flag. The help 0x7E800BC1 lists 31 categories (FUNC_CALL, MAIN, THROUGH, RECORD, ART, REC_AVCHD, ART_KDG, EDIT, …) |
| `exec <hex>` | 0x7E6D1A9B | Sends a MOV_CMD: 1 REC_START, 2 REC_END, 4/5/6 THROUGH_MULTI START/END/ROTATE, 7/8 BUFFERING START/END, 9 PARAM_UPDATE (fixed area 800×600/720×480…), 10 KDG_START `<0 oneshot,1 transition,2 multiecho>`, 11 KDG_END, 12 KDG_STOP, 13 KDG_READY |
| `get` | 0x7E6D1D2A | Prints MOVIE_KIND, QUALITY_MOVIE, CMP, FRAME_RATE |
| `w` | — | **No-op** (returns right after the compare) |
| `ansh f x y` | 0x7E6CFFDB | Movie anti-shake flag (§3.3) |
| `os` | 0x7E6DDA75 | mov_os.c dump (queue/event/semaphore wrappers MOV_Q_R/W, MOV_E_*, DTQ_*) |
| `dump <mode>` | 0x7E6D1E11→0x7E6D1E50 | 0 RAW, 1 current video buffer, 2 all video buffers, 3 AWB, 4 all three, 5/6 dump/file-write for movie (MJPEG YCC420), 7/8 the same over all buffers (not art), 9 HDMI buffers, 10 AVCHD record YUV |
| `dbginfo` | 0x7E6D2747 | Module status / history |
| `img <n>` | 0x7E6CA889 | Sets 0x602ADC71 (IMG_CTRL dump selector) |
| `kdg <1/2/3>` | 0x7E6DD107 | Sets mask 0x01/0x02/0x04 (bits 0/1/2; `bset 1/2/4` (audit 2026-11-09)) of 0x602ADFB8 (KDG Param/Log/Img output) |
| `effect <n>` | 0x7E6D18EE | Parses a number only (no visible effect) |
| `mf ...` | 0x7E6D1909 | Prints the "mov mf switch/zoom 100–400/area" help only |
| `gdisp` / `sdisp <0/1>` | 0x7E6D1936 / 0x7E6D194D | Get/set DispThroughState |
| `face <n>` | 0x7E6CA892 | Sets 0x602ADC72 (FACE_INFO dump) |
| `through` | 0x7E6CA89B | Prints ucStateThroughStart/Normal |
| `fps` | 0x7E6D1992 | Prints "fps ctrl TRUE/FALSE" (0x7E6C35B4) |
| `bit <n>` | 0x7E6D80AA | Writes byte 0xA0751F8C. Also called from 0x7E6ED5E2 in the record path |
| `interval <n>` | 0x7E6EF0C2 | Writes byte 0x602ADFF5, which is read in the audio-encode loop 0x7E6EDC53… |
| `time start/stop/print` | 0x7E6F4479 | MOV time counter (mov_sub.c) |
| `print` | 0x7E6D27C3 | dbginfo detail |
| (other) | 0x7E6D19B7 | Help |

- **The help advertises `set QUALITY FPS` and `ansh … <x> <y>`. Neither is implemented in v1.6**: there is no "set" compare, and x/y are "unsupported". **Verified.**
- Related shells:
  - `movc` → 0x7E6D09DE (`timer <ms>`, `exec 1|2`).
  - `movp` → 0x7E6E3D18, the playback shell. Help at 0x7E80AD01 lists debug/history/info/meminfo/geti/thum/thums/prim/one1/abort/resume/step/load/clear/vol/area/video/aspect/dump and the AVCHD `ap ab asf asb astp asbt asc ae` commands. The code also has `first`, `play`, `apset`, `ar`, `aa`, `dbg0-4[m]`, `dbga[m]`, `dbridge`, `dplay`, `davchd`, `davchdi`, `dfile`, `dall`. **Verified.**

## 5. Playback and editing

### 5.1 Playback engine
- **MOV_PLAY** 0x7E6DE931 is the main loop. `movplay_m0if` 0x7E6DDEAD covers aspect/area setup. MOVDISP_TASK 0x7E6E6011 runs the display state machine (`mov_dsi` 0x7E6E62A8).
- **MOVSUPPLY_TASK** 0x7E6E8366 is the data-supply state machine (`m0_e5s1p`…`m0e8s6p`, `send_playpost_packet`).
- **H.264** goes through AvmidApi → AVSCA (0x7E6E0671–0x7E6E0E58): init/run/stop/pause/restart/PlayFrame/trickplay/Step. Callbacks are `P>O Api_OutVFCb/OutAFCb` (0x7E6E134D/0x7E6E16C0). The AVCHD command set is `movplay_com_AVCHD_*` 0x7E6DF20B–0x7E6DF9FB (first_frame, prim, abort, resume, step_f/b/top/bottom, exit).
- **QT parsing:** `analyze QT` 0x7E6D975B, `analyze_header_mov` 0x7E6D99C0 ("moov not found", size checks), `analyze_play_atoms` 0x7E6DA33F, resolution check 0x7E6E2D4C. **Verified** strings.
- **AVCHD parsing:** `movplay_get_clipinfo` 0x7E6E22BA opens the CLPI file. `analyze CLIP` 0x7E6E2323 reads the SequenceInfo/ProgramInfo/CPI/ExtensionData start addresses. `analyze CLIPb` 0x7E6E2582 checks the format codes (§1.1) and the Olympus `MakersPrivateData`. **Verified** strings.
- **AVI (MJPEG):** `analyze_chunk` 0x7E6E9981 checks RIFF, avih, strh vids/MJPG, strf compression, FPS and "FILE SIZE OVER". Also `analyze_chunk_simplicity` 0x7E6EA940, `search_chunk` 0x7E6EA5A4, and audio format checks 0x7E6EADA3/0x7E6EAE7D (wFormatTag, nChannels, SamplesPerSec, BitsPerSample). Thumbnails come from `search_thum` 0x7E6E97C4 and `thum_read`/`PTHS` 0x7E6EB6D7. **Verified** strings.
- **Task names vs content.** The entry named MOV_PLAY_AVF (0x7E6E324B) prints `[MOV_PLAY_AVCHD_FILE]`, and MOV_PLAY_AVI (0x7E6E38AC) prints `[MOV_PLAY_AVCHD_IMG]`. These names still hold in the corrected tasks.tsv, so they look like internal abbreviations: AVF = AVCHD file reader, AVI = AVCHD image/decode. That reading is **inferred**; the strings are **verified**.
- Still JPEG playback inside the movie engine handles "JPG:720P/VGA, aspect 16:9/3:2/4:3" (0x7E6EC4B2) for slideshow/movie-of-stills. **Verified** strings.

### 5.2 Audio in movie
- Recording audio is LPCM 48 kHz, 2 ch, 16 bit, 1.536 Mb/s for QT (0x7E6D84EC). **Verified** values.
- Audio is encoded per second in `[QT] Audio Enc Run/Pass` (0x7E6ED7E1/0x7E6EDB8D; "Not 1FPS m_ulAudioCount1FPS"). The sound buffer helpers are `[MOV_SOUND]` 0x7E6F3B9E and `sound_chunk_int` 0x7E6F3E9B. The record audio flag is 0x605B21DA. **Verified.**
- Playback sound: `init/start/abort/close_sound1/2` and `..._avchd1/2` (0x7E6E77AC–0x7E6E7DC5), `is_sound_play` (App mute mode) 0x7E6E7981, `mov_play_audio_set_volume` 0x7E6E82CE. **Verified** strings.
- **Not found in this range:** wind-noise reduction or a recording-level setting. ALC attack/decay strings (`*alc_atk`, `*alc_dcy`) exist in the audio module at 0x7E952119, outside this scope. **Verified absence by string search here.**

### 5.3 MOV_EDIT = time-lapse movie builder
- It runs in ~~the task the config table names IMG0_LOCAL (entry 0x7E6D4597, cfg 0x8E)~~ task 0x84 MOV_EDIT (entry 0x7E6D4597; §2 table) (coverage C4 (L1 2026-11-09)). **Verified.**
- `mov_edit_check_param` 0x7E6D493D accepts only quality 3 (720p), sound disabled (`MOVREC_SOUND_DISABLE`), kind MJPEG and fps ∈ {1,2,3,5,6,10,15,30}. Otherwise it returns 0xFF01. **Verified.**
- Flow: `record_start` 0x7E6D46BE → `record_make` 0x7E6D47BC (per YC frame) → `record_end` 0x7E6D4839. It uses the MJPEG `userstop_for_edit` state. **Verified.**
- The app API `api_play_Create_TimeLapseMovie` 0x7E686E96 logs exactly these fields (quality, record_sound, movie_kind, fps, compression). It reaches MOV_EDIT through the generic `api_exec` queue (**inferred** link).
- `mov_edit_movie_size` 0x7E6D465E is called from the remaining-space calculations 0x7E5B37D8/0x7E5B3862. **Verified.**
- **No movie cut or trim editor and no "still from movie" function** was found in the mov* modules. mov_buff (MOV_CMD 32–34/64/65, KEEP/FREE of YUV frames) is the only frame-hold mechanism. Its user-facing purpose is unknown.

## Open questions
1. Is AVCHD (format 2, quality 5/3) reachable from the E-PM2 menu, or is it dead code shared with the E-P3/E-PL5 generation? Check the menu/setting writers of 26225.
2. Why MOV quality 4 (VGA, 4 Mb/s, 7200 s cap) exists, and which UI mode selects it.
3. 22-min spec vs the 26.6-min code estimate (§1.2). Does the AVSCA library end the file by itself at ulUpper:ulLower = 4 GiB−1? `INF_REC_FILESIZE` is only logged.
4. App reaction to 0x04070026/27/28 (0x7EA42F9B and its callees) and the path back to MOV_CMD_RECORD_END.
5. Defaults of the MJPEG duration table (setting 25812) and the frame-size table (60356): they need the settings blob loaded by 0x7E457152.
6. Meaning of the setting 33378 == 4 index offset in 0x7E6F0808 and of the (80) field of 0x7E5B6463 (media type?).
7. Names of the internal art codes (70–183) and why codes 83 and 88 get special treatment.
8. The meaning of "KDG" and "PSP", and of KDG effect type 5 (2000 ms fade).
9. Who writes the TAKE→MOV commands, and what mov_buff (cmd 32–34, 64/65) is for: still-during-movie, or pre-buffering for edit?

# Better 1080p movie sampling: desk checks and the first probe (2026-11-19)

Labels: **V** = read in the code or bytes, or run in om-emu; **I** = inferred; **U** = unknown. Addresses are block-0
runtime addresses of stock v1.6. Background: [03-sensor-pipeline-memory.md](../2026-11-12-hardware/03-sensor-pipeline-memory.md).

## 1. The plan and the result in short

The owner's plan: keep sensor mode HSHR and 30 fps as stock. Change only the processing side, so that the Bayer frame
is 1920 wide (2304 ÷ 1.2, Q16 78643) and 1080 needs no horizontal upscale. Use it only for MOV 1080 with a non-art
picture mode and Movie IS off. Everything else stays stock. This folder does not build that mode.

| Question | Answer | Label |
|---|---|---|
| Width limit in IMG | None near 1938 px. The engine works in stripes of 440 px for lines below 3840 px; stills use the same code at 4640 px | V code, I meaning |
| Width limit in the camera-core unit 0x99900000 | 15-bit size fields, 128-byte aligned buffers; no 2048 limit | V |
| Width limit of the pre-processor's resizer (PRO) | Not found. No body of this family writes a wider HSHR frame | **U**: the biggest risk |
| Sensor readout for the new mode | The same window: calc_r gives 2326 px for 1662 × 1.4 and for 1938 × 1.2 | V (om-emu) |
| Memory | The new frame (1960 stride, packed, 2,938,880 B) fits in the stock Bayer slot of 3,673,600 B. The YUV ring and the noise-reduction frame keep their size | V sizes, I packing |
| Movie IS | An electronic crop (1414 × 1114 of 1646 × 1296) moved per frame by the stabiliser unit's shift. No code shifts the sensor while recording | V crop, I no sensor shift |
| Where to make it conditional | The movie request builder 0x7E6C7656 has the movie size and the IS flag at hand; TAKE 0x7E59EE0A and the AE set (built once at start-up) need their own change | V |
| Time per frame | Unknown. The probe build of section 5 measures it | U |

**The plan still looks viable.** The biggest risk is the PRO resizer's largest output width (U). Only a camera run with
the 1920 geometry can show it. The second risk is the time per frame: the develop job gets 17 % more input pixels
(1938 / 1662). The probe of section 5 measures today's time against the 33.4 ms frame period.

## 2. Desk check 1: width limits

| Finding | Address | Label |
|---|---|---|
| The IMG engine processes a frame in vertical stripes. The stripe width follows the line width: 440 px below 3840, 384 px from 3840 to 4095, 1572864/width from 4096. Stills (4640 wide) use the same code, so a 1938-px line is not a width problem for IMG | 0x7E54BE55 (`cmp 4096` / `cmp 3840`, then `mov 440` / `mov 384`) | V code; I meaning (strong) |
| The camera-core unit 0x99900000 has 15-bit size fields (`and 32767` before the writes to 0x999000BC–0x999000E0). Its three buffer addresses are aligned to 128 B (`lsr 7` / `asl 7` before the writes to 0x99900008/0C/10). No 2048 limit | 0x7E6540F8, 0x7E653AB1 | V. The unit's identity is still open |
| Whole sensor lines (4624 px, stride 4640) pass the pre-processor in FULL and STILL. The PRO line path carries at least 4624 px | sensor-mode table 0x7E7BA370 | V |
| The PRO resizer's largest output width was not found. Stock HSHR writes 1662 px; the target writes 1938 px from the same 2326-px input. No register write of a 1.4 ratio was found: 91750 is only in EXP, in Movie IS and in one art routine (0x7F0646A0). So the ratio comes from the sizes, or from a PRO register block not yet traced | — | **U** |
| Op builder slot 7 adds op 14 when `P+62 ≥ 1792` (0x7E57360C). Slot 25 tests `P+62 < 1536` (0x7E5621E1); for HSHR, P+97 = 5 decides that one first. P+62 is copied from art field +148 (0x7E728C8C). Its meaning in movies is unknown. If it is the input width, 1938 crosses 1792 and 1646 does not | 0x7E5735A9, 0x7E5621B5 | V code; meaning U |
| The E-P5 (1.8) and the E-PL5 (1.6) have the same 1662 / 1312 / 91750 constants (`scripts/geom_otherbody.py`) | — | V |

**Smallest probe for the PRO unknown:** a geometry-only build: the TAKE and movie sizes at 1938 / 1960 and the new
resize, the IMG settings unchanged. A limit shows as a frozen or garbled picture while recording, or as a camera-core
error record in the Debug Log.

## 3. Desk check 2: every site of the HSHR geometry, the choice, memory

### 3.1 Sites

| # | Site | What it sets | Change for 1920 | Label |
|---|---|---|---|---|
| G1 | TAKE request builder 0x7E59EE0A, HSHR case 0x7E59EE72–0x7E59EEB4 (mode codes 516 and 517), sent to the camera core | +2 = 44, +4 = 11, **+6 = 1662 (0x7E59EE7E)**, +8 = 1312, **+10 = 1646 (0x7E59EE8A)**, +12 = 1296, +88 = 1, IS limits +34 = 323, +36 = 181 | width 1938, effective 1920; heights stay | V |
| G2 | Movie mode table, built by 0x7E6C410A (`through_start`): 30-byte records at 0x605B0828 + 30·i; HSHR is i = 3 at 0x605B0882 | **stride 1680 (0x7E6C4304), width 1662 (0x7E6C430D)**, height 1312, **effective 1646 (0x7E6C431F) × 1296**, centre 831 + x/2 and 656 + y/2, IS crop 1414 × 1114 (+18/+20), decimation 2/2 (+22/+23), IS limits 323/181 (+26/+28) | stride 1960, width 1938, effective 1920 | V |
| G3 | Movie request builders 0x7E6C7656, 0x7E6C78C9 (also 0x7E6CA8DF): copy the G2 record into the IMG job (+106 stride, +108 width, +110 height, +116/+118 effective size or crop, +120/+122 centre, +136/+138 shift in 1/16 px) | their only constant is the IS crop 1414 × 1114 (0x7E6CB8B3, 0x7E6CB8B9) | the place for the conditional change | V |
| G4 | IMG resize sub-builders 0x7E54A0D0 and 0x7E54A468: for IMG mode P+97 = 5 the full-readout divisor is **1646 × 1296** | `mov 1646` at 0x7E54A2CE and 0x7E54A5E9, `mov 1296` at 0x7E54A2D3; steps ((in−1)<<12)/(out−1) at block+368/+372 | 1920 | V constants; formula I |
| G5 | AE parameter set for HSHR 0x7E698658: use area 1662 × 1312, windows 241/241/245/245, skip 6/8 and 18/14, 44/11, **resize 91750 (0x7E698694)** | built once at EXP_MOVIE start-up (0x7E68F07C → 0x7E69ABBE → 0x7E697C05 → 0x7E698615) | 1938 / 78643; a per-clip choice needs a rebuild at run time, not a fixed byte | V |
| G6 | `art_get_bayer_size` table 0x7E85B38C, entry 5 = {1680, 1662, 1312, 0, 1646, 1296, 831, 656} | art filters only | unchanged (art filters are excluded) | V |
| G7 | Movie IS shift 0x7E6CB90B: for HSHR it divides the shift by **91750 (0x7E6CB981)** | IS on only | unchanged (IS off) | V |
| G8 | Movie raw dump 0x7E6D1E50: HSHR = 1680 × 1312, 2,519,040 B (0x7E6D1F2A) | debug only | optional | V |

Hits with no effect: 0x7E69DA98, 0x7E69DB22 (debug prints); 0x7E6C395D, 0x7E63CA6A, 0x7EEA1876, 0x7EEBD36D (source
line numbers, not sizes) (V).

- **calc_r 0x7E698AC6** (run in om-emu by `scripts/geom_calc_r.py`, V) returns (use width × resize) >> 16, made even.
  1662 × 91750 and 1938 × 78643 both give 2326: the sensor window stays the same. 1920 gives 2304 and 1936 gives 2324,
  so the target width is 1938 (1920 plus the 18-px margin of stock). The AE set's resize field is read only here
  (`mov (24,a3),d1` at 0x7E6989A8): it maps the AE window to sensor coordinates; it is not PRO's own ratio (V read, I
  meaning).
- **Stride and packing (I, strong).** HSHR, HS, MSSC and LSSC dump at width × height × 8/7 (2,519,040 = 1680 × 1312 ×
  8/7); CLIP and mode 6 at 2 bytes per pixel. So HSHR is stored packed, 7 pixels in 8 bytes, and each stride is a
  multiple of 56 px. Target stride 1960 px = 2240 B per line, 2,938,880 B per frame.

### 3.2 Where HSHR is chosen

- **TAKE (V).** Bits 8–15 of the request word pick the readout through table 0x7E792F00 (0x7E59CC38): 0x01 → 516 and
  0x0A → 517 (both HSHR), 0x02 → 513 (HS), 0x0B → 519 (MSSC), 0x0C → 520 (LSSC). 0x7E5A8DD6 maps 517 to sensor mode 4.
  0x7E59EE0A gives 516 and 517 the same geometry; it reads the movie format (prm 0x8561) at 0x7E59EFB1.
- **Movie module (V).** The mode index comes from 0x7E6CFF23: field +4 of the current camera record (0x605B0FF4 + 136
  × [0x605B10A4]); 4 = HSHR = index 3. The camera core fills that record each frame (0x7E6CFFED), so the index reports
  the readout and does not choose it (I).
- **The three conditions.** In 0x7E6C7656 the movie size is `(36,a0)` (6 = MOV 1080, 3 = 720, 5 = AVCHD 1080, 4 = VGA)
  and the IS crop flag is 0x605B1CF4 (section 4). The art code is the byte 0xA07507CC (0x7E6C6E46 reads it and branches on
  0, V; I: 0 = no art filter). **720p uses the same HSHR record**, so the condition must test size 6 (V).
- **Places to change:** 0x7E6C7656 after the record copy (+106, +108, +116 when size = 6, IS flag = 0, art = 0); the
  HSHR case of 0x7E59EE0A under the same condition; a rebuild of the AE set 0x7E698658 with 1938 / 78643 at record
  start; the two `mov 1646` of G4 (or a hook on P+97 = 5).

### 3.3 Memory

- **The movie Bayer frames are not in the movie recording pool** (simple allocator 0x7E6F2B6E, "Movrec Memory Over!";
  0xA52B2400 + 316,790,208 B, or 0xA52B2200 + 219,690,944 B in the other mode, 0x7E6F287B). None of its allocations has
  a Bayer size (V).
- **Three fixed Bayer slots (V).** 0x7E6CFCE7 writes three records whose +8 = 0xBC60A340 + i × **3,673,600** (1600 ×
  1148 × 2 B, movie table record 6). The slots end at 0xBD08CD40, where four buffers of 52,224 B start. The movie code
  names them BAYER_NEWEST, BAYER_1ST, BAYER_2ND (strings used at 0x7E6F9A26).
- **The new frame fits** (V arithmetic, I format): 2,938,880 B packed in a 3,673,600 B slot. No new allocation.
- **Unchanged buffers** (V sizes; I that nothing in them depends on the Bayer width): the 19-frame YUV ring (id 82,
  59,535,360 B, 0x7E6F3722) and the noise-reduction reference (id 98, 2 × 4,147,200 B): both hold 1920 × 1080 output.
- U: whether anything else uses 0xBC60A340–0xBD08CD40 while recording. The new frame stays inside the stock slot.

### 3.4 What the emulator cannot show

It has no sensor, no pre-processor and no IMG engine. Here it ran calc_r and the probe's routines (section 5.3). It
cannot show the PRO output limit, P+62 in a movie frame, the slot contents, or any timing.

## 4. Desk check 3: Movie IS

**Answer.** Movie IS crops the Bayer frame and moves the crop in every frame by a shift that the stabiliser unit (BC,
the H8 MCU) reports (V for the crop and the data path; I for the meaning of the shift). No code was found that makes
the sensor-shift unit correct while recording (I; U as a fact).

- **Gate (V).** 0x7E598763 returns 1 only if the lens-IS byte 0x60516226 != 1 (I: a lens with its own IS active turns
  the body crop off; 0x7E598A7B sets the byte from the lens record and prm 0xDEB1), the camera is in movie mode
  (0x7E5AB75F: byte 0x60517D56 or prm 34129 == 1) and prm 0x9981 (Movie IS) == 1. 0x7E5963F9 (and four more callers)
  passes the result to 0x7E6CFCCF, which writes 0x605B10AC. 0x7E6ECCAF copies it into the movie parameters:
  **0x605B1CF4 = Movie IS active**, 0x605B1CF0 = movie mode (0x7E6ECF7D–0x7E6ECF91).
- **Crop (V).** When 0x605B1CF0 == 1 and 0x605B1CF4 != 0, 0x7E6C7656 calls 0x7E6CB860. For HSHR and movie size 6, 5
  or 3 it sets the crop to **1414 × 1114** (hard-coded at 0x7E6CB8B3 and 0x7E6CB8B9). That is 86 % of 1646 × 1296,
  which fits the manual (p. 48: "the recorded image is enlarged slightly"). 1080 with IS then comes from 1414 px (H ×1.36),
  softer than IS off (I).
- **Shift (V).** 0x7E6CB90B reads x = (+34) and y = (+36) of the frame-info record at frame +44, clamps them to
  ±323 / ±181, and converts them (`(x<<4)/xStep`, and for HSHR `(x<<16)/91750`, 0x7E6CB981) into job +136/+138.
  Check: 323/2/1.4 = 115 px against (1646 − 1414)/2 = 116; 181/2 = 90.5 against 91 (V arithmetic).
- **Source of the shift (V chain, I meaning).** TAKE 0x7E59B665 sends BC request 20 (0x7E59B762) or 31 (0x7E59B83E)
  to the BC API 0x7E53DACD each frame; the reply callback 0x7E59B798 copies reply +14/+16, and 0x7E59B379 writes it
  into frame info +34/+36 (it repeats the last values when no new data comes). No EMS code reaches 0x7E6CB90B.
- **No sensor shift (I).** The movie code 0x7E6C0000–0x7E6F6000 makes no call into the BC module (V, calls.tsv);
  api_rec_Notify_Audio_Record_Start 0x7E68C4AC calls BC entry 0x7E53E124, a bare `retf` (V); the
  api_rec_dummy_Control_Liveview_Anti_Shake strings have no code reference (V); `mov ansh` prints "shift_x,shift_y:
  unsupported" (V). U: which BC mode runs while recording.
- **Open (U):** the manual lists two Movie IS options, M-IS1 (Movie-I.S.) and M-IS2 (Auto). Which one sets
  prm 0x9981 = 1 is not known. The test sheet (section 6) compares the field of view of both: a crop shows as a
  narrower view.
- **For the plan.** Gate the new mode on 0x605B1CF4 (or 0x605B10AC), not on prm 0x9981: with a lens whose own IS is on,
  the crop is off although the menu says on (I). With IS on, the stock path stays, so the 91750 at 0x7E6CB981 and the
  1414 × 1114 crop are never used with a 1920 frame. A later IS-on version would need 1650 and 78643 there (I).

## 5. The probe build `debug-log-movie-time`

### 5.1 What it records

| Event | CPU | When | Arguments |
|---|---|---|---|
| `mv_frame` (2048) | 0 (MOV_TASK) | at the end of each run of mov_image_process for recording, 0x7E6C6E46 (one movie frame, I) | `total_us`: entry to end; `develop_us`: time in the develop job (the img_exec call at 0x7E6C7490, Bayer → YC), 65535 = 65.5 ms or more, 0 = no develop call; `ret`: the return value (0x38FB = a skip path) |
| `mv_enc` (2049) | 1 (MOV_ENCODE) | after each packet handler of MOV_ENCODE 0x7E6D554A | `us` in the handler, `kind` (0 = command 256, 1 = other); `art_us`: time of the ART_SUB task (CPU 1) in its handler 0x7E72CD3E since the last mv_enc |

- The record time is the end of the frame's processing; the start is time − total_us. The time between two mv_frame
  records is the frame period.
- Why these sites (V): 0x7E6C6E46 prints "[mov]mov_image_process Record TIMEOUT!!" and "skip"; its callers are the
  MOV_TASK record handlers 0x7E6C4C41–0x7E6C5542. It calls 0x7E6C8841, which calls 0x7E6C7225. 0x7E6C7225 builds the job
  at 0x605B0248 (+106/+108/+110 = stride, width, height) and runs it with the movie img_exec wrapper 0x7E6DABAF (line
  5921), or posts it to another task (0x7E6DD86E). img_exec 0x7E544BB5 returns only when the job is done (it returns
  the job's result code; V). The live-view variant is 0x7E6C6853. ART_SUB (0x900B), MOV_ENCODE (0x900C), MOV_AVCHD and
  the img_exec twin run on CPU 1 (task tables, V).
- I: that 0x7E6C6E46 runs once per recorded frame and that the develop job of the frame is the call at 0x7E6C7490.
  The camera run settles it: about 300 mv_frame records per 10 s clip.
- CPU 1 load: the probe measures two CPU 1 tasks, not the whole CPU. The H.264 encoder itself is hardware; what
  MOV_ENCODE's packets are is U.
- Volume: one mv_frame per frame, 300 per 10 s, in a ring of 512 per CPU. The flush runs at each entry to a menu or
  playback. Clips of 15 s or less, with playback after each, lose nothing (I, ring arithmetic).

### 5.2 The build

- Spec `data/specs/log-movie-time.json`, written by `scripts/mkspec_movtime.py` (listing:
  `results/log-movie-time.lst`). Five hook sites, all in stock bytes of segment 1: 0x7E6C6E46 (5 B), 0x7E6C721D (5 B),
  0x7E6C7490 (7 B, a replaced `call`), 0x7E72CC54 (6 B), 0x7E6D55A7 and 0x7E6D55AF (6 B each). Routines: 416 B at
  0x7E69EC6B–0x7E69EE0B (segment 1, the free part of lss-core's area). RAM: 32 B at 0x7E4FD300 (after the log's block
  buffer; the same evidence as the log's RAM, I). It changes the build id in the block header to 34775ddcf8f5f0af.
- Dictionary: `data/logdict/events.json` gets `mv_frame` and `mv_enc`. The pinned build's dictionary is kept as
  `data/logdict/events-33ca8d15f4f1c877.json`.
- Build description `data/builds/debug-log-movie-time.json`: the 17 pinned specs and this one, label 2026.11.19,
  `first_code: true`.
- sha256 **c5fcf7142451c97186f846ad4aa4baf302f1d2a7f11ed9d3239bc66b6e58d6fc**.

### 5.3 Checks (exit status 0 = pass)

| Check | Result |
|---|---|
| `emulator/hookcheck.py` (the build's specs, with the allow list of `emulator/hookcheck-allow.tsv`) | PASS, 273 transfers, 0 FAIL (`results/hookcheck.txt`). All new transfers stay in segment 1 and the kernel |
| `emulator/boot-test data/builds/debug-log-movie-time.json` | PASS (`results/boot-test.txt`) |
| `emulator/update-path-test data/builds/debug-log-movie-time.json` | PASS (`results/update-path-test.txt`) |
| `tools/freespace.py check --first-code` (the build's specs) | PASS (`results/freespace.txt`). Without `--first-code` it fails: the ledger does not count lss-core as code in this area, although lss-core's code there is camera-tested (2026-11-19) |
| `emulator/opcheck.py` | PASS, 518 byte ops (`results/opcheck.txt`) |
| `scripts/scen_movtime.py` (each hook from its site to the next stock instruction, both images, as S17 of the log) | PASS (`results/scen-movtime.txt`): registers as the pinned build, the replaced calls with the same arguments, no write outside the log's RAM, the records as the dictionary says |
| Test suite (`uv run python -m unittest discover -s cli/tests`) | 307 tests OK |
| `epm2mod log` on a made-up file with the new events, and `scripts/movtime_report.py` on its JSON | decodes; the report works |

The emulator does not run movie recording: it cannot show that the sites run while recording, or any time value.

## 6. Test sheet (camera run)

One session. The probe changes no picture processing (it only reads the timer around stock calls), so the clips of
step 3 are also the stock baseline for later comparison (I, from the code). No stock flash is needed.

**Before the flash**

1. Copy the card's `EPM2LOG.BIN` away and delete it from the card, so the file holds only this session.
2. Flash: `epm2flash debug-log-movie-time c5fcf7142451c97186f846ad4aa4baf302f1d2a7f11ed9d3239bc66b6e58d6fc`
3. Way back if anything goes wrong: `epm2flash epm2mod-2026.11.19 6441130e9cc6cd5f06dc70e35950e05b0401f9a3f606694cf2c806a0bc209f62`

**Set-up (menu paths from the manual, pp. 17, 45–48, 52, and from `docs/user/debug-log.md`)**

4. MENU → SETUP → Custom Menu → J → Debug Log → On → OK. (No Custom Menu tab: MENU → SETUP → Setup Menu → Menu Display
   turns it on.)
5. Press MENU. On the first screen press ◀/▶ to the movie mode icon (the movie camera). Press OK.
6. Press OK for the live control. Press ▲/▼ to the shooting mode item and ◀/▶ to **P**. Press OK.
7. Live control → record mode item → **Full HD Fine** → OK.
8. Use a card that the camera does not limit (SD speed class 6 or above, manual p. 48).

**Clips.** Each clip: press the movie button (red dot), count 10 seconds, press it again. Wait until the card lamp is off. Then press
▶ (playback; this writes the log), look at the clip once, and press ▶ again to go back. Change the settings in the live
control (OK, ▲/▼ to the item, ◀/▶ to the value, OK).

| Clip | Picture Mode | Image Stabilizer | Subject |
|---|---|---|---|
| 1 | Natural | OFF | a chart or a page of fine text, filling the frame, camera on a table |
| 2 | Natural | OFF | brick or fabric (moiré) |
| 3 | Natural | OFF | trees or water (fine moving detail) |
| 4 | Natural | M-IS1 | the chart of clip 1, from the same place |
| 5 | Natural | M-IS2 | the chart of clip 1, from the same place |
| 6 | Dramatic Tone | OFF | the trees or water of clip 3 |
| 7 | the art-filter entry that shows the name of a loaded film simulation (if all show Olympus names: MENU → SETUP → Custom Menu → J → Load Looks → Load → OK first) | OFF | the trees or water of clip 3 |

9. After clip 7: press MENU once, then turn the camera off. Copy `EPM2LOG.BIN` and the seven MOV files from the card.

**What each result means.** Read with `uv run epm2mod log EPM2LOG.BIN --json > log.json` and
`uv run python experiments/2026-11-19-movie-sampling/scripts/movtime_report.py log.json`.

| Result | Meaning |
|---|---|
| About 300 `mv_frame` per clip, period about 33,367 µs | the site runs once per frame (section 5.1 confirmed) |
| No `mv_frame` at all | 0x7E6C6E46 is not the recording path: the probe needs new sites. The pictures are not affected |
| `develop_us` p95 × 1.17 below about 30,000 in clips 1–3 | the develop job has room for the 1938-px frame (I: time grows with input width) |
| `develop_us` p95 × 1.17 at or above 33,367 | the 1920 mode would drop frames: the plan needs a faster path or a smaller width |
| `develop_us` 0 in every frame | the develop job goes to another task (0x7E6DD86E); `total_us` is then the time to measure |
| Many `ret` 0x38FB, or periods of 2 frames | frames are skipped (expected for Dramatic Tone; a fault in Natural) |
| Clip 4 or 5 shows a narrower view of the chart than clip 1 | that M-IS option is the electronic crop (prm 0x9981 = 1). Same view in both: the other mechanism (sensor shift) or no crop in this mode |
| `mv_enc` about 1 per frame | MOV_ENCODE handles one packet per frame; `us` is its CPU 1 time per frame. None: MOV_ENCODE is not on the MOV path |
| `art_us` per second in clips 6 and 7 | the CPU 1 art-filter load; 0 in clips 1–5 is expected |
| A `gap` marker | records were lost (clip too long, or no playback between clips): repeat that clip shorter |
| The camera freezes or restarts while recording | a probe site is wrong: flash the way back (step 3) and report which clip |

The camera-log entry before the flash: `docs/camera-log/2026-11-19-debug-log-movie-time.md`.

## 7. Next steps (not done here)

1. The camera run of section 6.
2. A geometry-only build for the PRO limit (section 2), with the conditional change in 0x7E6C7656 and TAKE.
3. With it, a probe of P+62 and the job fields +106/+108/+116 of the job at 0x605B0248 in a movie frame (the op 14
   question of section 2).

## 8. Files

- `scripts/mkspec_movtime.py`: writes `data/specs/log-movie-time.json`.
- `scripts/scen_movtime.py`: the hook check of section 5.3.
- `scripts/movtime_report.py`: the per-clip report.
- `scripts/mkspec_wide.py`, `scripts/scen_wide.py`: the 1920-wide frame spec and its rig check (section 12).
- `scripts/geom_scan.py`, `scripts/geom_otherbody.py`, `scripts/geom_calc_r.py`: the desk-check scripts of sections 2
  and 3.
- `results/`: the check outputs and the listing.

## 9. Camera run, 2026-11-19

The owner flashed `debug-log-movie-time` (sha256 `c5fcf714…`) and recorded six clips, all handheld. There was no
Dramatic Tone entry (the ART menu holds film simulations), so the six clips are sheet clips 1, 2, 3, 4, 5 and 7.
The clips were matched to the log by their start times: the gaps between log segments (33.9 s, 28.0 s) equal the
gaps between `PB190003`, `PB190004` and `PB190005` (34 s, 28 s). Files: `results/camera-log.json` (decoded log),
`results/camera-report.txt` (`scripts/movtime_report.py`), `results/camera-qp.txt` (QP per clip,
`../2026-11-12-hardware/scripts/qp.py`), `results/camera-clips.txt` (duration, bit rate),
`results/camera-fov-clips-1-4-5.png`. The MOV files stay on this host, not in git.

| MOV | Sheet clip | Settings | In the log | Bit rate | P-frame QP |
|---|---|---|---|---|---|
| PB190001 | 1 | Natural, IS off, chart (a screen) | lost | 15.6 Mb/s | 20 (all) |
| PB190002 | 2 | Natural, IS off, brick or fabric | last 98 frames | 20.5 Mb/s | 20–38, mostly 22–28 |
| PB190003 | 3 | Natural, IS off, trees or water | 349 frames | 20.2 Mb/s | 20–30, mostly 22–26 |
| PB190004 | 4 | Natural, M-IS1, chart | 336 frames | 13.2 Mb/s | 20–24, mostly 20 |
| PB190005 | 5 | Natural, M-IS2, chart | 336 frames | 11.8 Mb/s | 20–23, mostly 20 |
| PB190006 | 7 | film simulation, IS off, trees or water | lost | 15.2 Mb/s | 20 or 26 |

**Records were lost** (cpu 0: 709, cpu 1: 1464). The log has no playback state between clips, so the ring was not
flushed and overflowed (about 100 s per ring, §5). The CPU 1 art-filter load of a film simulation (clip 7) is
therefore not measured.

### 9.1 Timing (V, camera)

| Clips | Frames | `total_us` median | p95 | Frames over 33,367 µs | `develop_us` |
|---|---|---|---|---|---|
| 2, 3 (IS off) | 447 | 22,139–22,149 | 23,083–23,168 | 0 | 0 in every frame |
| 4, 5 (M-IS1, M-IS2) | 672 | 20,585–20,593 | 21,434–21,713 | 1 each (41 ms, one frame) | 0 in every frame |

- One `mv_frame` per frame, period 33,5xx µs mean: the probe site runs once per recorded frame (§5.1 confirmed, V).
- `develop_us` is 0 in every frame: the develop job is not the img_exec call at 0x7E6C7490 on this path. By the
  sheet, `total_us` is the time to use (I: it holds the wait for the develop job on another task).
- The frame rate held: 29.8 per second, `ret` 0 for every frame, two long periods per clip (start and end).
- MOV_ENCODE on CPU 1: 0.2–0.3 ms per packet, 0.7–0.8 packets per frame. ART_SUB: 0 in the Natural clips.
- **IS on is faster, by 1.5 ms per frame.** Both M-IS1 and M-IS2 give the lower time. The E-PM2's movie IS crops
  1414×1114 from 1646×1296 (§4), 74 % of the pixels, so the time falls with the processed area (I).

### 9.2 Headroom for the 1938-px frame (I)

A line through the two points (2.133 Mpx → 22.1 ms, 1.575 Mpx → 20.6 ms, medians) gives about 16.4 ms fixed and
2.7 ms per million pixels. A 1938×1296 frame (2.512 Mpx, IS off) would take about 23.1 ms median and about 24 ms at
p95: 70 % of the 33.4 ms frame, about 9 ms to spare at 30 fps. Two points and the meaning of `total_us` are the
weak parts. The plan of §1 stays viable; the open risk stays the PRO resizer's output width (§2).

### 9.3 Movie IS mode (U)

Both IS modes show the same lower time, so both seem to crop (I). The field of view (`results/camera-fov-clips-1-4-5.png`)
cannot separate them: the clips are handheld, at slightly different distances.

### 9.4 Bit rate (V, camera; answers `../2026-11-12-hardware/README.md`)

The handheld busy clips 2 and 3 used the whole budget (20.5 and 20.2 Mb/s) and their QP rose above the floor of 20 in
most frames (22–28). The still subjects stayed at the floor (11.8–15.6 Mb/s, QP 20). So for busy handheld scenes the
20 Mb/s target is the binding limit, and a higher bit rate (`patches/movie-bitrate-32.json`) would lower QP there.
For calm scenes only the QP floor binds.

### 9.5 Next

1. The geometry build of §7 step 2, with the `P+62` probe of step 3. With IS off as the condition, the measured time
   leaves room.
2. If the art-filter load matters for the condition: one more clip with a film simulation, with playback after it.

## 10. Bit-rate build `debug-log-movie-bitrate` (2026-11-19, not flashed)

Asked by the owner after §9.4. The build is `debug-log-movie-time` plus `data/specs/movie-bitrate-32.json`: the
9 ops of `../2026-11-12-hardware/patches/movie-bitrate-32.json` (1080 Fine 32 Mb/s, 1080 Normal 24, 720 Fine 20,
720 Normal 16, encoder cap 24 → 50 Mb/s, time-limit rates in step; analysis in `../2026-11-12-hardware/06-bitrate-and-limit.md`)
and one more op for in-camera playback.

**The playback check (V, read for this section).** 0x7EEB9359 checks a decoder parameter block: height 64–1088,
frame rate 1.00–60.00 fps (`cmp 6000`), type 1–3, and the declared bit rate at most 20,000,000 (`cmp 20000000` at
0x7EEB93DA), which passes when the field is −1 (unknown). Whether playback fills the field from the clip's HRD
(32.77 Mb/s) is not traced; raising the constant to 50,000,000 makes it pass either way. Whether the decoder keeps up
with 32 Mb/s is **U**: the camera test plays each clip.

sha256 `09dd21ca6aa8a100a0b43b9a9d336a8f5523c262e06bb9c0be285c55c7e61375`. Checks: `tools/freespace.py check
--first-code` PASS (load order 0 FAIL), `emulator/opcheck.py` 0 FAIL, `emulator/boot-test` PASS,
`emulator/update-path-test` PASS. No hook or code is added.

Acceptance criteria: busy handheld 1080 Fine clips near 32 Mb/s with QP mostly at 20–22 (against 22–28 in §9.4);
1080 Normal near 24 Mb/s; a 60 s busy clip records to the end; every clip plays in the camera and decodes on a
computer without errors; stills, film simulations and peaking work as before.

## 11. Camera run of `debug-log-movie-bitrate`, 2026-11-19

The owner flashed it, recorded the three clips of §10 handheld, played each in the camera, and took one photo with a
film simulation. Everything worked: no stop, no freeze, every clip played in the camera. The owner's view: "doesn't
look incredible, similar to pre mod". Files: `results/bitrate/camera-report.txt`, `camera-qp.txt`, `camera-log.json`.

| Clip | Mode | Declared HRD | Video bit rate | P-frame QP | Compare (§9.4, 20 Mb/s target) |
|---|---|---|---|---|---|
| PB190001, 21 s, trees | Full HD Fine | 32.77 Mb/s | 18.7 Mb/s | 20–25, mostly 22 | trees: 20.2 Mb/s, QP mostly 22–26 |
| PB190002, 21 s, same scene | Full HD Normal | 24.58 Mb/s | 20.6 Mb/s | 20–25, mostly 21–22 | – |
| PB190003, 61 s, slow pan | Full HD Fine | 32.77 Mb/s | 9.5 Mb/s | 20 (floor) | – |

- **The patch took effect (V):** the SPS declares 32,768,000 and 24,576,000 b/s, and the encoder accepted both.
- **The encoder did not use the new budget (V):** Fine stayed below 20 Mb/s, at QP 21–22 instead of falling to the
  floor. Normal (24 M) came out at the same QP and a similar rate. So on this scene the hardware rate control settles
  near QP 22 whatever the target above 20 M (I); why is not known.
- **Gain:** busy frames moved from QP 22–26 to 21–22 (fewer frames at 26). That is a small step, consistent with
  the owner's view.
- **Calm content stays at the floor:** the pan clip used 9.5 Mb/s at QP 20.
- **Timing (V):** 22.1 ms per frame as in §9, 29.8 fps, no drops; the encoder's CPU 1 time is unchanged.
- Records were lost again (the log ring overflows during clips of 20 s and more); each clip still has about 450 frames.

Conclusion: the bit rate is no longer the limit; the QP behaviour of the encoder and, more, the stretched 1646-px
frame are. The visible lever left is the 1920-wide frame (§1, §7).

## 12. The 1920-wide frame: build `debug-log-movie-wide` (2026-11-19, not flashed)

Asked by the owner after §11. Step 2 of §7, unconditional for the HSHR frame. The build is `debug-log-movie-bitrate`
(§10, the camera's current firmware) plus `data/specs/movie-wide-frame.json` (written by `scripts/mkspec_wide.py`).
The timing probe and the bit-rate spec stay, so the only change against the camera's build is the frame size.

### 12.1 What changes

The HSHR (1080 and 720 movie) Bayer frame becomes 1938 × 1296 (effective 1920 × 1296, stride 1960) in place of
1662 × 1296 (effective 1646, stride 1680). The sensor window stays 2326 px: calc_r(1938, 78643) = calc_r(1662, 91750)
(§3.1, V in om-emu). The pre-processor should then shrink by 1.2 in place of 1.4 (I). 14 immediates, each in stock
bytes; no code, no hook.

| Site | Stock | New | What |
|---|---|---|---|
| 0x7E59EE7E, 0x7E59EE8A | 1662, 1646 | 1938, 1920 | TAKE request builder, HSHR case: width, effective width |
| 0x7E6C4304, 0x7E6C430D, 0x7E6C431F, 0x7E6C42F7 | 1680, 1662, 1646, 831 | 1960, 1938, 1920, 969 | movie mode table, HSHR record: stride, width, effective width, centre x |
| 0x7E54A2CE, 0x7E54A5E9 | 1646 | 1920 | IMG resize builders, IMG mode 5 divisor |
| 0x7E698658, 0x7E698694 | 1662, 91750 | 1938, 78643 | AE parameter set HSHR (its sensor window stays 2326 px, so the AE output is the same) |
| 0x7E85B3DC | {1680, 1662, …, 1646, 1296, 831, 656} | {1960, 1938, …, 1920, 1296, 969, 656} | `art_get_bayer_size` entry 5 |
| 0x7E6C435A, 0x7E6CB8B3 | 1414 | 1650 | Movie IS crop width (table and code) |
| 0x7E6CB981 | 91750 | 78643 | Movie IS shift divisor |

Read for this section (V):
- The only other uses of 1662 and 1646 in block 0 are debug prints and source line numbers (0x7E69DA98, 0x7E6C395D,
  0x7EEA1876, 0x7EEBD36D). The only data copy of the geometry is the `art_get_bayer_size` table.
- The camera core has no constant derived from 1662, 1646, 1680 or the packed frame size: a scan for 1920, 2240,
  2519040 and 2938880 in 0x7E5F0000–0x7E720000 finds only source line numbers and the debug dump 0x7E6D1E50.
  So the camera core takes the frame from the TAKE request at run time (I). The debug dump keeps 1680 × 1312.
- The IMG divisor branch (1646) runs only for the Dramatic Tone art codes 96/97/165/166 (0x7E54A1B5–0x7E54A23D).
  The normal develop path reads the crop from the job (+116/+118), which 0x7E6C7656 copies from the movie mode
  table (V).
- The two 91750 in overlay A (0x7F064ECA, 0x7F064F51) belong to the face detector (caller 0x7E6FBFB4), next to
  101581, a constant step of the detector, not the HSHR ratio. They stay (I).

### 12.2 What is and is not tested

- **1080, Natural, Movie IS off:** the target of the camera test.
- **720p:** it uses the same HSHR record, so it is 1920 → 1280 (H ×0.667) in place of 1646 → 1280. Keeping 720 stock
  would need a condition at four sites, so this build does not do it. **720 is untested in this build.**
- **Movie IS on:** the crop is scaled to 1650 × 1114 and the shift divisor to 1.2. The field of view stays the same
  (1650 × 1.2 = 1414 × 1.4), and the largest shift fits the margin (323/2/1.2 = 135 px against (1920 − 1650)/2 = 135)
  (I, arithmetic). Without these two changes, IS on would have given a picture squeezed by 1.2/1.4 and a shift too
  small by that factor. **Untested; out of the acceptance test.**
- **Art filters and film simulations in movies:** `art_get_bayer_size` and the Dramatic Tone divisor change with
  the frame. **Untested.**
- **Photos:** the STILL and FULL modes and their tables are not touched (V). Playback is not touched (V).

### 12.3 Checks (exit status 0 = pass)

| Check | Result |
|---|---|
| `uv run epm2mod make debug-log-movie-wide` | sha256 **9fbc9436d0271b2421069689cd6570dab9eb9dab8d4f0a764e4219ff096037a1**; it runs the checks below in its own pipeline too |
| `tools/freespace.py check --first-code` (the build's specs) | PASS; `movie-wide-frame`: 14 edits of existing content, no free-area byte (`results/wide/freespace.txt`) |
| `emulator/opcheck.py` | PASS, 20 specs, 542 byte ops (`results/wide/opcheck.txt`) |
| `emulator/hookcheck.py` (with the allow list) | PASS, 273 transfers, 0 FAIL; this spec adds no hook (`results/wide/hookcheck.txt`) |
| `emulator/boot-test`, `emulator/update-path-test` | PASS, PASS (`results/wide/`) |
| `scripts/scen_wide.py` (the live-view rig: mov layer start, Through Start, Natural, 1080, three frames with the camera record set to HSHR; both images) | PASS (`results/wide/scen-wide.txt`). The HSHR record that the firmware's own through-start handler 0x7E6C410A builds is as the model in both images: 1680/1662/1312/1646/1296, centre 831, IS crop 1414 (stock) and 1960/1938/1312/1920/1296, centre 969, IS crop 1650 (wide); no fault |
| Test suite | 307 tests OK |

The rig does not reach the IMG resize builders. They run inside img_exec on the camera core's develop path (the
P+97 byte comes from the camera record, 0x7E6CFFED), and the rig has no camera core. The model for 1080 is an H step
of ((1920 − 1) << 12)/(1920 − 1) = 4096 (no scaling) in place of 3511, and a V step of 4915 in both (I). Neither the
rig nor any static check can show the sensor, the pre-processor, pixel data or timing.

No log probe was added. The question that matters, whether the pre-processor writes a 1938-px line, shows in the
picture itself. The job fields +106/+108/+116 are the values this spec writes, so logging them would prove nothing.
P+62 (§2) lives in a struct whose address is not known for the develop job, so a probe would need a new hook site
that no run has tested.

### 12.4 Acceptance criteria

1. 1080 Fine clips record at 30 fps (`mv_frame` period about 33.4 ms, `ret` 0) to the end, with no corrupt frames and
   no early stop.
2. Fine horizontal detail is measurably higher than with the 1646 frame: a chart or text clip, compared frame by
   frame with `results/PB190001.MOV` (§9, the same screen chart, stock frame). Round objects stay round (a wrong
   scale shows as a stretch).
3. Frame time under 33 ms in the log (`total_us` p95; §9.2 predicts about 24 ms). Record clips of 15 s or less and
   open playback after each, or the ring overflows (§9, §11).
4. Photos and playback work as before. 720p is untested in this build; one 720 clip is information, not a criterion.

### 12.5 The biggest remaining risk, and what each failure looks like

The biggest risk is still the pre-processor: whether it writes a 1938-px line, and with which stride (U, §2).

| Fault | Cause (I) | What the camera shows |
|---|---|---|
| The pre-processor cannot output 1938 px | its resizer limit (§2) | a black, frozen or garbled picture in the movie live view or the clip; a recording that stops at once; `fw_error` records in the log |
| The camera core writes another stride than 1960 (e.g. 1952, if it rounds to 16 px and not to 64 bytes) | the stride is computed at run time (§12.1) | a picture slanted to one side, with colour stripes; each line shifted a little more than the one before |
| The frame needs more than the 3,673,600-byte Bayer slot | only if the frame is stored at more than 1.43 bytes per pixel; the dump code says 8/7 (§3.1) | bands of another frame or garbage in the picture; a freeze or restart while recording |
| The develop job is slower than the frame | 17 % more input pixels | `total_us` over 33,367 µs, `ret` 0x38FB (skips), jerky motion |
| Op 14 (P+62 ≥ 1792, §2) changes the IMG processing | the meaning of P+62 is unknown | a visible difference in tone, noise or sharpness that is not resolution |
| The horizontal scale is wrong | a site that keeps the 1.4 ratio and was not found | round objects become ovals; the field of view differs from the stock clip |

If the movie mode live view uses the HSHR frame (I: the through-start handler builds the record), most of these show
on the screen before recording starts. The way back is the camera's current build, `debug-log-movie-bitrate`
(sha256 `09dd21ca6aa8a100a0b43b9a9d336a8f5523c262e06bb9c0be285c55c7e61375`), or the pinned build.

## 13. Camera run of `debug-log-movie-wide`, 2026-11-19

The owner flashed it and stopped after the first clip: pink bands across the live view. `PB190001.MOV` (10.5 s,
1920×1080, 25 Mb/s) and the log are in `results/wide/` (frame: `results/wide/camera-frame-1s.png`).

What the frame shows (V, measured on the frame at 1 s):

- The scene is there, curved and stretched, with fine horizontal line structure.
- Magenta vertical bands repeat every 275–309 px (centres 105, 414, 694, 982, 1257, 1550, 1854).
- The picture ends at y ≈ 870–930; below it is a band of high-frequency garbage.

Reading (I, strong): **the reader uses the new layout, the writer still the stock one.** A reader with stride 1960
over rows written at stride 1680 starts each row 280 px further into the written data (the band period, about 280
px before the distortion warp), and reads 1296 × 1960 / 1680 = 1512 written rows where only 1312 exist: the good
part ends at 1312 / 1512 × 1080 ≈ 937 rows. So the develop job read a 1938/1960 frame, but the pre-processor's DMA
still wrote 1662 px at stride 1680 and 1312 rows. A writer-side geometry source was not changed (candidates: the
sensor-mode records 0x7E7BA370 and the table 0x7E85B3FC with the HSHR record 1680/1662×1312, see
`../2026-11-12-hardware/03-sensor-pipeline-memory.md` §1).

The rest held (V, log): 344 frames, 29.8 per s, `ret` 0 throughout, no new firmware error; `total_us` 23.5 ms median,
24.7 ms p95 (22.1 / 23.1 before), close to the 23.1 ms the model of §9.2 predicted for the larger frame. The
encoder took the 1920 output at 25 Mb/s.

Not yet answered: whether the pre-processor can write 1938-px lines. Next build: find the writer's geometry source and
change it in step with the reader.

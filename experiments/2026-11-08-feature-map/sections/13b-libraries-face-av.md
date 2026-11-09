# 13b. String-less libraries: Omron OKAO (PT + Smart Skin), red-eye library, AVPI AV middleware

Round D1 deep dive. E-PM2 v1.6, block 0, runtime = 0x7E421020 + offset.

- **Labels:** **verified** = read in the code or bytes. **inferred** = from names, layout or call order. **external** = product or API knowledge, not from this firmware.
- **MN103:** `btst imm` takes a mask. `udf00`/`udfu01` are read as multiply (inferred).
- **Scratch scripts:** `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/d1/libraries-face-av/`. They are `rng.py` (callers into a range and callees out of it), `tree.py` (call tree), `summ.py` (per-function features), `imm.py` (immediates), `vt.py`/`vt2.py` (vtables).
- **Database:** the improved one (`--out $S/map-test`).

## 1. Areas and verified boundaries

| Component | Code | Rodata / data | Basis |
|---|---|---|---|
| **OKAO core + PT** (facial parts) | **0x7E72CFA1–0x7E731584**. After the `ret` at 0x7E731582 come 3 bytes of 0xFF, then the libc `_ctype` table at 0x7E731588 (bytes 0x10/0x30/0xA0/0xC0/0x8C/0x89/0x81). Not ~0x7E732000. | Models and tables 0x7E85CEFC–~~~0x7E86DCxx~~ **0x7E86DD5F** (the end of the atan LUT 0x7E86DC5F, reader 0x7E7310FE; 0xFF to 0x7E86DD7F; then the ORF CMIO blob 0x7E86DD80–0x7E8808BF, which is not OKAO) (14d §3.6, V) (D2 2026-11-09). RAM: pool descriptors 0x602AE508 (W) and 0x602AE518 (B) | verified |
| **OKAO SS "Smart Skin"** (beauty) | **0x7EBA7BC1–0x7EBABF8D**. It starts right after the last OXF code: the destructor 0x7EBA7B98 (stores vtable 0x7EBCDB0C, calls 0x7EBA7BB5, then the base destructor 0x7EBA7B13) and its 12-byte helper **0x7EBA7BB5–0x7EBA7BC0** (`add 16,a0`; if the word at this+16 is non-zero, store 0; `retf`; only caller 0x7EBA7B98). It ends at the `ret` at 0x7EBABF8B, followed by the strings `CIC_MUTEX`/`CIC_EN…` | LUTs 0x7EC92318–~~0x7ECAFF3C~~ 0x7ECB083B (cosine table, 255·x and max(1, a·b/255) tables, ease curves; 14d §3.5) (D2 2026-11-09) | verified bounds. Name: see §2.2 (A4 2026-11-09) |
| **Red-eye library** (overlay A) | **0x7F0645C1–0x7F0691C5**. It includes the maths helpers 0x7F068F66–0x7F0691C5. The DB marks the page 0x7F069000 as data, but 0x7F069020/0x7F0690A0/0x7F06910C/0x7F069171 are code with callers. After the `ret` at 0x7F0691C3 come `ff ff` and the BASIC keyword table (`list run new bye next…`) at 0x7F0691C8 | 3-byte constants at 0x7F06AD94/97; eight direction-offset tables 0x7F06ACD4–0x7F06AD93 (loads of 0x7F06ACD4/F4, AD14/24/34/44/54/74); a u16 quarter-sine table 0x7F06AD9C–0x7F06ADC1 (19 values 0…256, loaded 7 times at 0x7F068FB6–0x7F069093 by the angle helpers 0x7F068F9C/0x7F069020) (A5 2026-11-09) | verified |
| **DPS in overlay A** | It ends at 0x7F0645C0. The last DPS function is 0x7F064584, which calls the string helpers 0x7F087BD1/0x7F087BF9/0x7F087C03 in overlay B | — | verified |
| **AVPI AV middleware** | **0x7EE8F4F4–0x7EECE318**. Everything from 0x7EE63000 to 0x7EE8F4F3 has callers only in the C3D API (functions 0x7EE61A0A–0x7EE62F80) and the overlay-B C3D bridges (0x7F09E31F–0x7F0A30A9). 0x7EE63000 is a page number, not a function boundary: it falls inside 0x7EE62F80 (to 0x7EE63004), and 0x7EE62F80 and 16 other "API" functions are themselves called from inside 0x7EE63000–0x7EE8F4F3, so the C3D API and the code after it are one library (A5 2026-11-09). That library is the C3D framework 0x7EE619C7–0x7EE8F4F3 (class registry and ~55 classes); its outside callers are only overlay-B functions (14a §1, §2.4) (D2 2026-11-09). The first AVPI function, 0x7EE8F4F4, calls the kernel. After the `ret` at 0x7EECE316 come OSD-debug strings (`OSD DBG get`, `osddraw…`), so rodata starts at about 0x7EECE319 | Plug-in names, vtables and codec tables ~~0x7F02F600~~ 0x7F02F684–~0x7F033xxx (14a §1: the first words point to AVPI OSAL 0x7EE8FFC8…) (D2 2026-11-09). Plug-in registry 0x7E8EFA18 (data image). Codec tables: code loads 0x7F031DEC (first at 0x7EEC5BD4)–0x7F033AC0; no code loads 0x7F0327DA directly, so "0x7F0327DA–" is inferred (item 12) (A5 2026-11-09) | verified (caller scan, bytes). Ranges inside AVPI: §2.4 |

**What 0x7F021020–0x7F034000 holds** (verified strings):
- 0x7F021020–0x7F0229AF is not graphics: the tail of an unreferenced 1,061-row `{u32 id, u32 0/3, u32 0}` table that starts at 0x7F01F7F4 (14a §1) (D2 2026-11-09);
- the GL rodata 0x7F0229D0–~0x7F027BFF, with the name pools (`gl_SilhScaleDMP` 0x7F022DCF, `glScalef` 0x7F023644) and the `{name, fn}` table 0x7F023B8C–0x7F024283 (D2 2026-11-09);
- the 3D-engine rodata 0x7F027C00–0x7F02B24A (format-loader table 0x7F027C4C, type table 0x7F02AA14) (D2 2026-11-09);
- libpng (0x7F02B404) and zlib (0x7F02E947–0x7F02EB24) strings, to 0x7F02EB67;
- the C3D framework rodata 0x7F02EB68–0x7F02F683 (D2 2026-11-09);
- then AVPI from ~~0x7F02F600~~ 0x7F02F684 (D2 2026-11-09).

So it is not "AVPI only", and it is not BASIC.

## 2. Components

### 2.1 OKAO core and PT (facial-parts detection)

**Role** (verified flow; "PT" = OKAO Facial Parts, external):
- The library finds the parts of a face that the **hardware** face detector has already found.
- **It contains no face detector.** The FACE_* code calls into it only for memory pools, PT and the shared geometry helpers. All external callers are FACE code, SS or the red-eye library (`rng.py`, verified).
- **It never touches MMIO** (immediate scan, verified).
- The FD hardware is programmed by the FACE code itself: 0x7E6F8062–0x7E6F82C7 writes 0x99600000–0x9960401C. That these are the FD engine registers is inferred.

**API surface** (addresses verified; OKAO names inferred unless a string names them):

| Address | Role | Notes |
|---|---|---|
| 0x7E72CFA1 / 0x7E72CFBE | `OKAO_SetWMemoryArea` / `OKAO_SetBMemoryArea`(ptr, size) | They init pool 0x602AE508 / 0x602AE518 through 0x7E72CFED/0x7E72D003 → 0x7E72D01D. Return −3 for NULL/0, and −1 if the pool is already initialised (descriptor word ≠ 0) or too small (< 4 units of 8 B) (verified) (A4 2026-11-09) |
| 0x7E72CFDB / 0x7E72CFE4 | `OKAO_FreeWMemoryArea` / `OKAO_FreeBMemoryArea` | They clear the 16-byte pool descriptors (0x602AE508–514 / 0x602AE518–524) and **always return 0** (`call clear; clr d0`), so they cannot fail. The names come from the order of the failure strings in 0x7E6FBCB0 next to the call order (inferred from order, strong). Those prints are dead code, and the FreeB print re-tests the FreeW result in d2 (0x7E6FBE1F) (A4 2026-11-09) |
| 0x7E72D0BA / 0x7E72D169 | W-pool malloc / free | First-fit allocator 0x7E72D0F2 with 8-byte units; free 0x7E72D199 coalesces. **Also used by SS and the red-eye library** |
| 0x7E72D0D6 / 0x7E72D181 | B-pool malloc / free | Used for handles |
| 0x7E72D932 / 0x7E72D94C / 0x7E72D95E | handle create (B-alloc, zero, store magic) / magic check / delete | The handle pattern (§3) |
| 0x7E72D995 | normalise the error code: 0, −2, −3, −4 pass; anything else → −1 | |
| 0x7E72D9AE / 0x7E72DA05 | `OKAO_CreatePointer` / `OKAO_DeletePointer` | 96-byte handle, magic 0xECBC5054. Create copies 48 default bytes from 0x7E85D08F. The delete name is verified by string |
| 0x7E72DA3E / 0x7E72DA57 | `OKAO_CreatePtResult` / `OKAO_DeletePtResult` | 632-byte handle, magic 0xECBC7074. The delete name is verified by string |
| 0x7E72DA7F | set the face position(h, x, y, size, …, pose value, 10200) | Uses the angle units of §3 (±402/±804). Calls the geometry helpers 0x7E72D293/0x7E72D779 |
| 0x7E72DDBB | detect points(h, w, h, image, result) | FACE passes 640×480. Calls 0x7E72E0E2 |
| 0x7E72DEB8 | get points(result, n ≤ 12, xy[], conf[]) | Points come from result+8 (8 bytes each), confidences from +104. Returns −2 if the result is not valid |
| 0x7E72DF29 | get the face direction(result, &a, &b, &c) | Reads result +152/+156/+160. Inferred: up-down, left-right, roll |
| 0x7E72DF72 / 0x7E72DFA2 | set mode (0–2) / set confidence mode (0–1) | FACE sets 0 and 1 |
| 0x7E72D249, 0x7E72D293, 0x7E72D779 | geometry in double-precision soft-float | 0x7E72D249 = √(dx²+dy²) through 0x7E50198D (int→double) and 0x7E4FE9D7 (sqrt, inferred). 0x7E72D293 calls atan2-like 0x7E4FE19F (inferred). **SS also calls these** |

**Internal pipeline** (call tree from 0x7E72DDBB, verified edges; roles inferred from constants):

| Function | Role |
|---|---|
| 0x7E72E0E2 | Builds the face ROI from the position: angle classes ±45/±90, divides |
| 0x7E72E04C | Allocates work memory, runs the fit, frees |
| 0x7E72E3EE / 0x7E72E4DA | Allocate / free the work buffers: 376, 1008, 26,244 (= 162²) and 46,664 bytes (0x7E72E71A) |
| 0x7E72F00C | **Main fit**, 1,486 bytes |
| 0x7E72E79F | Samples the face into an **80×80 patch**: constants 80, 81, 162, 324, 6400 |
| 0x7E73039B / 0x7E730800 / 0x7E72FA4D | Patch resampling and the affine transform: many multiplies |
| 0x7E72E547 / 0x7E72E5DC / 0x7E72E65B / 0x7E72FE5B / 0x7E72FFAA | Byte feature maps, clamped to ±127 |
| 0x7E72E8E3 / 0x7E72E9B4 / 0x7E72EF58 / 0x7E730A4A | Pose-model search over 940-element descriptors (940 = 47 × 20) |
| **F024** 0x7E730BB9 / 0x7E730C34 | Pick one of 6 pose dictionaries: five 6-entry pointer tables at 0x7E86D994… |
| 0x7E731532 | Masked SSD between two signed-byte vectors; mask bits from a byte array, 0x80 shifted right. It ends at 0x7E731584; the DB size 2,766 is wrong (14d §5) (D2 2026-11-09) |
| ~~0x7E731288~~ 0x7E73121F / 0x7E731394 | Byte multiply-accumulate (projections). 0x7E731288 is not a function: it lies inside 0x7E73121F (the `jmp 0x7E731356` at 0x7E731262 crosses it), and its only DB caller is a false decode in the lens float tables (14d §5) (D2 2026-11-09) |
| 0x7E72F79C → 0x7E72F5EC / 0x7E72F6C5 | Two refinement passes (loop bounds 6 and 7) |
| 0x7E72F7B5 / 0x7E72F9FB | Direction estimate: clamp ±17157 (= π/3·2¹⁴) and the 999 sentinel |
| **F025** 0x7E730FE5 → 0x7E730CBD | Mirrors the **47 landmarks** for the other side, then refits |
| 0x7E72EB16 | Final 12 points and angles. Uses atan2 0x7E7310FE (π·2¹⁴ = 51471) and the angle wrap 0x7E72E88F (−180..179) |
| 0x7E73101F / 0x7E73109A | sin/cos from the table 0x7E86DACC |
| 0x7E7311E9 | isqrt (§3) |
| 0x7E72FC82 | Power-of-4 compares; probably a log or sqrt step |

**Callers outside the library:** the FACE wrappers at 0x7E6FB750–0x7E6FBF38 (§2.5), SS, and the red-eye library.

### 2.2 OKAO SS ("Smart Skin", e-Portrait skin smoothing)

**Name** (verified in another body):
- E-P5 v1.8 has the debug command `face okao` with `-pt - pattern detection` and `-ss - smart skin(beauty)`.
- The handlers `face_dbg_okao_pt_version` and `face_dbg_okao_ss_version` (0x7E3D3A29/0x7E3D3A60 in its map) print PT v3.1 and SS v2.5. The getters are E-P5 0x7E41C2CF/0x7E891A92.
- E-PM2 has neither these strings nor that getter byte pattern (verified absence). The E-PM2 SS is matched by its role: §2.5, cmd 11.

| Address | Role (verified) |
|---|---|
| 0x7EBA7BC1 | Maps internal error codes to OKAO codes: −2→−3, −1→−4, 1→3, −8 and 0 kept, otherwise −1 |
| 0x7EBA7BE8 | **Create(maxFaces 1..140).** 56-byte handle, magic **0x0CA00080**. Face table of maxFaces×32 bytes in the B pool. Defaults: p1 = p2 = 100 |
| 0x7EBA7C4C | Delete |
| 0x7EBA7CA6 | **AddFace**(h, x, y, size 20..8192, angle 0..359°). Converts degrees to 1/256 rad (×−1143>>8), uses the sine LUT 0x7EC92318 and the PT geometry helpers |
| 0x7EBA7FE7 | **SetParams**(h, p1, p2), each 0..200. REC e-Portrait passes 120 and 0 (struct +28/+30, see cmd 11) |
| 0x7EBA8021 | **Execute**(h, w, h, image, format, &abort, &progress, …). Format must be 2; w and h 64..8192, w even. If `*abort == 1` it returns 3 (= cancelled). Then it calls the main routine 0x7EBA8164 |
| 0x7EBA811B / 0x7EBA8128 / 0x7EBA8130 | Abort-flag poll / store progress / isqrt |
| 0x7EBA8164 → 0x7EBA86A6, 0x7EBA8F7F (3,735 bytes), 0x7EBAB7D2 → 0x7EBAA3DA / 0x7EBAAD91 | Per-face skin statistics, the core filter (double soft-float, 64-KiB-spaced LUTs 0x7EC9FD3B/0x7ECAFD3B), and the line passes plus blend. These roles are inferred |

### 2.3 Red-eye library (overlay A)

**Role: red-eye correction in playback** (not skin tone, recognition or a beauty helper). Verified chain:
- `play_face_redeye_adjust` 0x7E94318E posts **cmd 5** to FACE_EXEC (queue id var 0x7E43ECF2) through 0x7E50689F. The parameter is {image, width rounded up to 32, height}.
- FACE_MAIN → 0x7E6FBF38 → 0x7E6FBFB4 → **0x7F0645C1**.
- The beauty path (cmd 11) never enters this library.

| Address | Role |
|---|---|
| 0x7F0645C1 | **Entry**(image, w, h, faces[32 B each], n ≤ 8, &count, out0..3). Checks w and h in 10..8192 and w even; returns −3 otherwise (OKAO convention). Clears the outputs (0x7F064641), then calls 0x7F0646A0 |
| 0x7F0646A0 | Per-face driver. Builds eye windows (isqrt 0x7F068F66) and rotates them by the face angle (0x7F065147: 402/804/1206 = 90/180/270°). Crops the eye region (0x7F065291) and converts it to BGR (0x7F065587 → 0x7F0654BF). Then: histogram 0x7F065055, candidate search 0x7F066493 (→ 0x7F065E65 → 0x7F065A3B, 0x7F0657E7), distance 0x7F0667A6, **F076** choice, pupil refinement 0x7F067D3B (→ 0x7F066BDF, 0x7F067013, 0x7F067562, 0x7F067718, and 0x7F0678C8 with 8 directions 45°…360°), and **correction 0x7F0687C4**. Refinement and correction run once per eye |
| 0x7F0654BF | **YCbYCr 4:2:2 → BGR**, BT.601: R = Y + 1.402·Cr (91881), G = Y − 0.344·Cb − 0.714·Cr (22544, 46793), B = Y + 1.772·Cb (116130). Writes {B, G, R} (verified) |
| 0x7F066812 | Dominant colour of a region. Luma = (19595·p[2] + 38470·p[1] + 7471·p[0])>>16, so p = {B, G, R}. 101-bin **B-ratio** histogram of {ΣB, ΣG, ΣR, n}: the bin index is 100·p[0]/(p0+p1+p2) (0x7F0669EE–0x7F066A07), not luma. Luma is only a filter: a pixel whose luma is at or above a threshold (sp+52) is skipped (0x7F06696E–0x7F066986), and a second filter compares the pixel's 100·p[2]/Σ ratio with that of a second colour at sp+84…86 (0x7F066995–0x7F0669DE) (A5 2026-11-09). Returns the mean of the strongest bin. 1,616-byte buffer from the W pool |
| **F076** 0x7F066AD5 | Gets the region colour of each of two eye candidates through 0x7F066812, scores each as 100·c0/(c0+c1+c2), keeps the higher score, and on a tie compares byte 2. **Correction to C1:** c0 is **B**, not R, if the buffer comes from 0x7F0654BF (verified layout). So it picks the candidate with the higher blue ratio, with red as the tie-break. Inferred purpose: choose the less-red "reference" eye |
| 0x7F0683A4 / 0x7F068510 / 0x7F068309 / 0x7F068605 | Pixel recolouring that keeps luma (luma weights, 65280, 4096) and colour-space helpers. Inferred: they desaturate and darken the red pupil |
| 0x7F068F66, 0x7F068F9C, 0x7F069020–0x7F0691C5 | isqrt, angle normalise (90/180/270/360), sin/cos/atan helpers |

**Data** (verified): face descriptors 0x605B3FF0 (8 × 32 B), and outputs 0x605B40F0, 0x605B4130, 0x605B4170, 0x605B4190. **No other code reads the outputs** (grep). So the visible effect must be the in-place edit of the image (inferred).

### 2.4 AVPI AV middleware (CPU1)

**Tasks** (verified entries; this answers section 01's "not identified" row):

| Task | Entry | Role |
|---|---|---|
| CPU1 0x1011–0x101B | 0x7EE8FBB1 | **AVPI thread trampoline.** It gets its 20-byte thread record (0x7EE8FD07), calls `rec->fn(rec->arg)`, then exits (0x7EE8FCEC). Threads are created by 0x7EE8FBC9: the task id is the record index plus the base id var 0x7E43EEAE |
| CPU1 0x101C | 0x7EEC202E | **AvScaTask** (strings `AvScaTask: AVSCA_Recv_Message() …`) |
| CPU1 0x101D | 0x7EE8FF18 → 0x7EE9AFE7 | AVPI service task; role not read |
| CPU1 0x101E | 0x7EECC670 → 0x7EECC6E3 | Loop on messages 0x101/0x107… (stack 0x3800). Inferred: the codec-driver task |

**Layers inside 0x7EE8F4F4–0x7EECE318:**

| Range | Layer | Key points (verified unless marked) |
|---|---|---|
| 0x7EE8F4F4–~0x7EE90235 | **OSAL** | Kernel-object helpers (0x7EE8F4F4, 0x7EE8F516). Semaphore create/delete 0x7EE8F7B0/0x7EE8F818 (inferred kind). Wait/signal on the 1,024 × 12-byte object table 0x6078AC40 (0x7EE8F887/0x7EE8F9A3/0x7EE8FA91 = F071's callee). Thin wrappers 0x7EE8FB8E/99/A1/A9. **malloc/free 0x7EE8FEED/0x7EE8FEFA** (116 callers) → 0x7EEC5F4A/0x7EEC6009. **CMutex** (vtable 0x7F02F690, type 0x0D01): ctor 0x7EE90005, dtor 0x7EE90035 (pointer entry `movm`; the DB start is 0x7EE9003A), **Unlock 0x7EE9005B = F071**, Lock 0x7EE90088. **CAutoLock** (vtable 0x7F02F688, type 0x0D02): lock 0x7EE905AF (59 callers), unlock-dtor 0x7EE8FFD4 (137 callers). System singleton at 0x602BF550 (56 B, vtable 0x7F02F684): init 0x7EE900BB, term 0x7EE90111, is-init 0x7EE90138. Error reporters 0x7EE901D1 (91 callers) and 0x7EE94C18 |
| ~0x7EE90235–0x7EE9C331 | **Framework classes** | Plug-in base methods shared by all plug-in vtables: 0x7EE94564, 0x7EE94569 (type 0x0802), 0x7EE94A14, 0x7EE94B70–0x7EE94F47, 0x7EE9D9F6–0x7EE9E477. Media-format descriptor base 0x7EE971D4 and **merge = F072 0x7EE9724C** (type group 0x05). Thread creation from 0x7EE999D2. Individual class roles are not mapped |
| 0x7EE9C332–~0x7EEC1B71 | **12 plug-ins** | See the registry table below. Each plug-in has a name string, then its vtables, then the next name: "Audio Encode Plug-in" 0x7F02FBBB → vtable 0x7F02FBD4, … "MP4 Demux Plug-in" 0x7F031684 → 0x7F03169C. The H.264 engine object (vtables 0x7F0302D4/0x7F0307E8, ctors 0x7EEA36A9/0x7EEA4D84, code 0x7EEA36A9–0x7EEA7B6C) sits between AFile Sink and Video Encode. MP4 Demux code continues past its last vtable slot (0x7EEBEA70): its ctor 0x7EEBC9BB calls 0x7EEBF4D3–0x7EEC09FF, so its end near 0x7EEC1B71 is inferred. MP4 Mux has track-writer subclasses 0x7F030DBC (video: `trak…avc1/avcC…stss`, 0x7EEAED11–) and 0x7F030F04 (audio: `soun`, `sowt`, 0x7EEB13FE–) |
| ~0x7EEC1B72–0x7EEC5F31 | **SCA** (session control) | **AVSCA API** 0x7EEC1BEA–0x7EEC1FC3, AvScaTask 0x7EEC202E, message send 0x7EEC2253 → 0x7EEC62B9 (kernel calls), receive 0x7EEC22A1 → 0x7EEC652C |
| 0x7EEC5F32–0x7EEC62B8 | C++ support | operator new/delete 0x7EEC5F3A/0x7EEC5F42, heap 0x7EEC5F4A/0x7EEC6009, array helpers 0x7EEC6271 and 0x7EEC628F. The GUI also calls 0x7EEC628F (0x7ED97FA5, 0x7EDC2BBE) |
| 0x7EEC673F–0x7EECC66F | **Codec hardware driver** (no strings) | MMIO 0x99400000/0x99404000 (217 refs), 0x99500000, 0x98100000, 0x98B00000. Tables 0x7F031xxx–0x7F033xxx. Called by the H.264 engine object (0x7EEA3xxx–0x7EEA4xxx), Video Sink (0x7EEBA2FB…) and MP4 Mux (0x7EEACD20/0x7EEACE08) |
| 0x7EECC670–0x7EECE318 | Task 0x101E and the **DFS glue** | 0x7EECE2B9/C7/D1/FE/30E call the movie module's `[MOOV] DFS_Open/Close/Read/Seek/GetPos` |

**Plug-in registry** (verified bytes):
- 13 records of 272 bytes at 0x7E8EFA18 + 0x110·k (in the `.data` init image; the code uses the RAM copy **0x602BF558**, e.g. `add 0x602BF558,d0` at 0x7EE99822; 14d §3.8) (D2 2026-11-09): {+0 id, +4 factory, +12 category (1 = sink, 2 = source, 4 = transform), +16 `"staticlink.lib"`}.
- The library name suggests a framework built for DLL plug-ins, linked statically here (inferred).

| ID | Category | Plug-in | Factory → vtable |
|---|---|---|---|
| 0x01010001 | source | File Source | 0x7EEB6EE2 → 0x7F03123C |
| 0x01010002 | source | Video Source | 0x7EEA973E → 0x7F0309D0 |
| 0x01010003 | source | Audio Source (`CAvpiAsoAudioSource.cpp`, asserts 0x7EEA132E–0x7EEA1A23) | 0x7EEA0E95 → 0x7F02FF28 |
| 0x01020002 | sink | Video Sink | 0x7EEBA640 → 0x7F03152C |
| 0x01020003 | sink | Audio Sink | 0x7EEB3788 → 0x7F030F44 |
| 0x01020005 | sink | **AFile Sink** (file writer: DFS_Write 0x7E6D5A31, DFS_StreamSeek 0x7E6D5901) | 0x7EEA2154 → 0x7F0300B4 |
| 0x01030001 | transform | Video Encode (424 B, ctor 0x7EEA7B6D) | 0x7EEA2FEC → 0x7F030860 |
| 0x01030002 | transform | Audio Encode | 0x7EE9C332 → 0x7F02FBD4 |
| 0x01030003 | transform | Video Decode | 0x7EEB7431 → 0x7F031314 |
| 0x01030004 | transform | Audio Decode | 0x7EEB4FC1 → 0x7F0310B0 |
| 0x0103000A | transform | MP4 Mux | 0x7EEAA6CA → 0x7F030B28 |
| 0x0103000B | transform | MP4 Demux (652 B, ctor 0x7EEBC784) | 0x7EEBC70F → 0x7F03169C |

**How the movie code uses AVPI** (verified):
- **API dispatcher.** CPU0 code calls the AVSCA API, which copies the arguments into a message and posts it to AvScaTask. 0x7E6E2E20 (`AVMIDDLE CALL`) dispatches commands 0–10 through the jump table 0x7E80A348.
- **Command to function and message code:**

  | Cmd | Function | Address | Message |
  |---|---|---|---|
  | 0 | Init | 0x7EEC1BEA | 0x101 |
  | 1 | Free | 0x7EEC1C9F | 0x102 |
  | 2 | Run | 0x7EEC1CE1 | (0x103, inferred) |
  | 3 | Stop | 0x7EEC1D5D | 0x104 |
  | 4 | Pause | 0x7EEC1D9F | 0x105 |
  | 5 | Restart | 0x7EEC1DE1 | 0x106 |
  | 6 | PlayFrame | 0x7EEC1E23 | 0x107 |
  | 7 | TrickPlay | 0x7EEC1E86 | 0x108 |
  | 8 | Step | 0x7EEC1EE9 | 0x109 |
  | 9 | SetVideoParam | 0x7EEC1F4C | none: local call 0x7EEC258F |
  | 10 | GetPlayTime | 0x7EEC1F79 | none: local call 0x7EEC25A0 |

- **The names are matched two ways:** by the name list in 0x7E6E59CB, and by the recording wrappers. `MovmidApi_cmd_rec_init/start/end/free` (0x7E6D80B3/0x7E6D8554/0x7E6D860B/0x7E6D8668) call Init, Run, Stop and Free.
- **Message 0x10C** (0x7EEC1FC3) is `MovmidApi_SetMakersInfoPrivateData` (0x7E6D886A).
- **Init** takes a session type: 1/2/4/6 → a 212-byte context, 3/5/7 → 164 bytes. Errors are 0x80000001 (bad parameter) and 0x80000004 (no memory). The QT callback `USR_ScaCallback` **0x7E6D8900** is passed in the Init parameters (address load at 0x7E6D81B3).
- **File I/O goes back to CPU0.** AVPI calls `[MOOV] DFS_*` in the movie module (0x7E6D5901–0x7E6D5AA6). Those post through 0x7E6D5DEF → 0x7E6D5AD1 (`ContextSwitchQueue`, `psnd_dtq`), inferred to reach the file system's CPU0 task.

### 2.5 FACE-side wrappers (callers of these libraries)

**Handle table** (verified):

| Address | Holds |
|---|---|
| 0x605B3FC0 / 0x605B3FC4 | PT handle / PT result |
| 0x605B3FC8 | "contour" module (38 points; the name is inferred); a stub, always NULL (A4 2026-11-09) |
| 0x605B3FCC | SS handle |
| 0x605B3FD0 / 0x605B3FD4 | module 2 / module 4 ("eye-retouch" is an inferred label); stubs (A4 2026-11-09) |
| 0x605B3FD8 | abort flag |
| 0x605B3FDC / 0x605B3FE0 / 0x605B3FE4 | progress of modules 1/2/4 |

**Live eye path.** FACE_PT0 (0x7E6FC9F4/0x7E6FCA3C) → **0x7E6FBCB0** (verified):
1. W = 153,600 bytes at 0xBDBD5900 and B = 5,120 bytes at 0xBDBD4500. Addresses pass through 0x7E45DAF1 (inferred: cached→uncached).
2. Create PT and its result.
3. SetMode 0 and SetConfMode 1.
4. Set the position from the face record: coordinates halved; the angle comes from table 0x7E812FCC.
5. Detect on 640×480.
6. 0x7E6FBE4E stores points 5, 6, 3 and 4 (+ face offset), the three direction values and the 999 sentinels at +32…+58 of the face record. Inferred: the eye corners for eye-AF.
7. Delete everything and free the pools. On failure the `OKAO_*` strings are printed; the two Free prints can never fire (both Free functions return 0). (A4 2026-11-09)

**Command 11** (0x7E6F4739): e-Portrait / beauty processing (verified):
- **Senders:** `REC_BEAUTY_CSKIN_EXEC` 0x7E70F134 and `play_face_beauty_revise` 0x7E9431DA. REC posts {reply 0x7E43ED78, cmd 11, &param} to FACE_EXEC through 0x7E7185D8, then polls progress (0x7E6FB5D2 → 0x7E6F49B4) and abort (0x7E6FB5EF → 0x7E6F49E8, which sets 0x605B3FD8 = 1).
- **Parameter:** +0 module mask, +4/+8 W area (REC: 0xB35BA200, 32,487,552 B), +12 image, +16/+18 size, +28/+30 SS p1/p2. REC sets the mask to **1**: Smart Skin only.
- **Mask & 6** creates PT plus the contour module. The contour create is a stub that returns NULL, so this path always returns 0x8707. **Modules 2 and 4 are therefore dead** (verified: the stubs are 0x7E6FB6E3 and 0x7E6FB71E). The labels "contour" and "eye-retouch" are inferred. (A4 2026-11-09)
- **Mask 1:** for each face 0x7E6FBBCD calls SS AddFace; then 0x7E6FBC17 calls SetParams and Execute.

**Command 5** = red-eye (§2.3). W = 30,720 bytes at 0xBDBB5000.

**Return mapping** 0x7E6FBF12: 0 → 0; 3 → 0x8709 (aborted); 0x8705 passes; anything else → 0x8707.

## 3. Recurring patterns (how to classify a new function by its bytes)

- **OKAO handle check** (PT and SS). The function opens with `fc cc <magic>` (`mov magic,d0`) and `call 0x7E72D94C`. On a mismatch it returns `80 f9` (`mov -7,d0`).
  - PT magic 0xECBC5054: `fc cc 54 50 bc ec`.
  - PT-result magic 0xECBC7074: `fc cc 74 70 bc ec`.
  - SS magic 0x0CA00080: `fc cc 80 00 a0 0c`.
- **OKAO error values** (verified values; names external): 0 OK, −1 various, −2 not ready, −3 bad parameter, −4 no memory, −7 bad handle, 3 aborted (SS). The red-eye library uses the same −3/−4. Its use of the OKAO W pool and the shared isqrt make it **Omron code too** (inferred, strong).
- **Shared isqrt** (3 copies: 0x7E7311E9, 0x7EBA8130, 0x7F068F66). Seed `mov 0xC000,dN` (`fc ce 00 c0 00 00`) and mask 0xC0000000. Then two Newton steps `(x/y + y) >> 1`.
- **Angle units.** 1/256 rad: 402 = π/2, 804 = π, 1206, 1608. Q14 rad: 51471 = π, 17157 = π/3. Degrees: 90, 180, 270, 359. They mark OKAO/red-eye geometry.
- **FACE module stubs.** `fc cc 07 87 00 00 de 00 00` (`mov 0x8707,d0; retf`) means "module not linked". `90 00 de 00 00` (`mov 0,a0; retf`) is a create stub that returns NULL. There are 18 of them at 0x7E6FB6BA–0x7E6FB74D.
- **AVPI `GetTypeId`** = vtable slot 1. Byte form `2c LL GG de 00 00` (`mov 0xGGLL,d0; retf`). Groups found:
  - 0x01–0x0D overall;
  - 0x04xx at 0x7EE905D8–0x7EE90602;
  - 0x05xx = format descriptors (0x0505 = AFile Sink format, vtable 0x7F0301B8);
  - 0x08xx = plug-ins (0x0802; File Source 0x0803);
  - 0x0Dxx = OSAL objects.
- **AVPI errors.** 0xCA0000xx comes from OS-layer objects (…02 semaphore, …03 memory). 0xCB0000xx is reported through 0x7EE94C18. 0x8000000x comes from the AVSCA API.
- **AVPI destructor signature** (the destructor role is inferred). It ends with `mov 0x7EE8FEF7,a0` (`fc dc f7 fe e8 7e`) before `ret`.

## 4. Corrections to the map and earlier sections

1. **OKAO end:** the code ends at 0x7E731584, not ~0x7E732000. 0x7E731585+ is rodata (`_ctype` first). Verified.
2. **A second OKAO block:** 0x7EBA7BC1–0x7EBABF8D is OKAO **Smart Skin**, not OXF. The C1 note "OXF runs on to ~0x7EBA9xxx" is wrong: OXF ends at **0x7EBA7BC0**, the last byte of the destructor helper 0x7EBA7BB5 (§1). Verified. (A4 2026-11-09)
3. **The review said** "alloc/free 0x7E72D0BA/0x7E72D169 are also used by art-filter code 0x7E72E3EE, 0x7E7314D4". **This is wrong.** Those two functions are PT internals, under 0x7E72E04C. The external users are SS and the red-eye library. Verified.
4. **The overlay-A face library is red-eye correction**, with cmd 5 sent by `play_face_redeye_adjust`. It is not "face scoring". **F076's score is the blue ratio** (byte 0 = B). Overlay-A code ends at **0x7F0691C5**, not 0x7F069000. Verified.
5. **§09b open question 1** ("0x7F0687C4 writes the art composite descriptor +284") is wrong. 0x7F0687C4 is the red-eye pixel correction, reached only from FACE cmd 5. Verified reachability; role inferred.
6. **Smile:** confirmed absent. In addition, **the eye-retouch modules 2 and 4 of cmd 11 and the 38-point contour module are linked as stubs**. Verified.
7. **§03 "PT uses OKAO":** confirmed and extended. FD itself is a hardware engine; the 0x99600000 registers are written by 0x7E6F8062–0x7E6F82C7 (verified addresses; that this unit is the FD engine is inferred). OKAO is used **only** for PT (live eyes), for Smart Skin (cmd 11) and, inferred, for red-eye (cmd 5). **FACE_MAIN cmds 5/11 are now named** (§03 open question 9). (A4 2026-11-09)
8. **AVPI bounds:**
   - It starts at **0x7EE8F4F4**, not 0x7EE8F000. Before that, 0x7EE63000–0x7EE8F4F3 is C3D-side code.
   - It ends at **0x7EECE318**, which is also where block-0 .text ends; rodata follows.
   - §08's "0x7EEA–0x7EEE" and the regions table must change accordingly.

   Verified.
9. **F073/F074 (review 4)** belong to **AFile Sink**, not to the Audio Source class. Their vtables 0x7F0300B4/0x7F0301B8 follow `AFile Sink Plug-in` (0x7F03009B). Verified by the string order and the registry factory 0x7EEA2154 → ctor 0x7EEA2190 → vtable 0x7F0300B4.
10. **§04:** 0x7E6D886A is `MovmidApi_SetMakersInfoPrivateData` (AVSCA message 0x10C), not `USR_ScaCallback`. The QT `USR_ScaCallback` is **0x7E6D8900**. Verified strings.
11. **§01 CPU1 tasks:**
    - 0x1011–0x101B are AVPI threads;
    - 0x101C is AvScaTask;
    - 0x101D and 0x101E are AVPI service tasks.

    Verified entries.
12. **§08 "no quant tables"** is not contradicted. The tables at 0x7F0327DA+ are read by the codec driver, not by JPEG code (inferred).

## 5. Open questions

1. **Overlay A load.** Red-eye needs overlay A in RAM. Usr2 bit 0 is requested by the vtable method 0x7EBA13BE (vtable slot 0x7EC90B34), and that method has no static caller. Which component calls it before red-eye fix? If none does, cmd 5 would run unloaded code.
2. **SS details:** what p1/p2 mean (REC passes 120/0), image format 2 (assumed YCbCr 4:2:2), and the exact filter in 0x7EBA8F7F.
3. **PT details:** the meaning of the 12 points (indices 3–6 are stored as eye data), the 10200 argument of 0x7E72DA7F, and the pose table 0x7E812FCC.
4. **AVPI framework classes** in 0x7EE90235–0x7EE9C331 are not individually mapped (pins, buffers, graph). Also open: how SCA builds a graph per session type 1–7, and how the registry in the data image (0x7E8EFA18) is reached (no direct immediate found; probably through the RAM copy near 0x602BF4xx). Answered: through RAM 0x602BF558 (14d §3.8) (D2 2026-11-09).
5. **AVCHD.** It does not call the AVSCA API (no caller in MOV_AVCHD). Its `USR_ScaCallback` 0x7E6D25BE has no immediate reference. Which library does AVCHD use?
6. **Task bodies:** the roles of tasks 0x101D (0x7EE9AFE7) and 0x101E (0x7EECC6E3), and the codec MMIO map at 0x994xxxxx.

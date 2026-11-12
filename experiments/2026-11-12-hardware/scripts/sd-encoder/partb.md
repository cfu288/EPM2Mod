Part B was traced by a helper pass. The cap compare 0x7EEA33CB, GOP 15 (0x7E6D8491), GOP ≤ 60 (0x7EEA4E6A) and QP 51 (0x7EEA5A1A) were re-read in the bytes.
Its working files are in `.../scratchpad/hw02/b/`.

### B1. How the bitrate reaches the encoder

1. **0x7E6EE4A2** writes peak → 0xA0753564 and average → 0xA0753568, in a request block at 0xA0753560 (+0 format, +1 quality). **V**
   MOV writes the same value to both (20/17 M at 1080, 13/10 M at 720, 4 M at VGA). AVCHD writes peak 24 M / 19.29 M / 16.57 M and average 20/17/13 Mi. **V**
2. 0x7E6EE64D–0x7E6EE68B builds the message {cmd **0x1101**, param 0xA0753560} at 0xA0753550 and sends it through 0x7E6EECA6. **V**
   0x7E6D55E8 → `MovmidApi_cmd_rec_init` 0x7E6D80B3 with a2 = the param block. The dispatch step is **I**.
3. 0x7E6D8317 stores ulMaxBitrate = (4,a2) → 0x607306DC and ulBitRate = (8,a2) → 0x607306D8 in the staging block 0x60730694. **V**
   0x7E6D81D9 copies the staging block into the real `SAvScaInit` at **0x607305A8**; the video params land at +0x5C (0x60730604). **V**
   The names come from the `SAvScaEncVideoParam` print at 0x7E6D8FB8. **V**
4. AVSCA Init 0x7EEC1BEA(a0 = 0x607305A8) (call at 0x7E6D8139) → 0x7EEC530D. That function sets property 0x01000201 (52 B: ulBitRate +0, ulMaxBitrate +4)
   on the **Video Source** plug-in 0x01010002. **V**
5. Video Source 0x7EEA98F2 copies the rates into the media-format descriptor: fmt+72 = average, fmt+68 = peak, fmt+80 = fps ×100, fmt+60/64 = width/height. **V**
6. Video Encode 0x7EEA85B2 → engine 0x7EEA32CA: obj+28 = obj+72 = average, obj+88 = peak. **V**
7. Engine frame setup **0x7EEA57D4** converts the rate:
   - +60 = ulBitRate / 1000 (kb/s). **V**
   - Two fields = ulBitRate/1000 − 1 (0x7EEA5BC2–0x7EEA5BE1). **V** They are probably HRD `bit_rate_value_minus1` and `cpb_size_value_minus1`. If so the CPB holds 1 s of the average rate. **I**
   - A field = 6 if ulBitRate ≥ 15,500,000, else 2 (0x7EEA5B4A). **V** Its meaning is unknown.
   - The struct goes to the codec-driver object (obj+68, made by 0x7EEA3062) through vtable+20. **V**
   - The step from there to the codec MMIO (0x9940xxxx, driver 0x7EEC673F–0x7EECC66F) is **not traced**.

### B2. Encoder parameters besides the bitrate

| Parameter | Value | Where | Label |
|---|---|---|---|
| Codec | eEncCodec = 1. An engine is built only for codec 1 | 0x7E6D8317, 0x7EEA3028 | V |
| Frame rate | in = out = 2997 (29.97); maximum 6000 | 0x7E6D8317 | V |
| Max size | 1920×1080; interlace 0; full range 1; colour 6/6/6 (SMPTE 170M) | 0x7E6D8317 | V (meaning of 6: I) |
| Slices | eTransSlice = 1, usSplitSliceNum = 1 | 0x7E6D8317 | V |
| **GOP** | ulIvopInterval = **15** (I-frame every 15 frames = 0.5 s); the engine rejects > 60 | 0x7E6D8491; 0x7EEA4E6A | V (unit: I) |
| **B-frames** | none. The MOV track boxes (0x7F030D40) are stsd/avc1/avcC/stts/stsc/stsz/stco/stss, with no `ctts` (and no `co64`) | 0x7F030D40 | V boxes, I conclusion |
| **QP** | max QP 51; a second QP byte = 20 (min or initial?). The software rate control 0x7EEA6B37/0x7EEA726B clamps QP to 51 | 0x7EEA5A1A, 0x7EEA725A | V (role of 20: I) |
| Frame size limit | ulMaxCodeSize = 777,600 / 345,600 / 115,200 B (= W·H·3/8); the engine allows up to 0x7FFFFFF | 0x7E6D8317 | V (formula I) |
| CPB/VBV | probably 1 s at the average rate (see B1 step 7); no explicit buffer-size constant was found | 0x7EEA5BC2 | I |
| Timing | time_scale 60000 / 120000 / 48000, chosen by the progressive flag | 0x7EEA5B6A | V (VUI reading: I) |
| Buffers | ucVideoBufNum / ulOverflowNum / ulReturnNum / ulMaxDestroyNum = 15/8/9/1, 3/1/2/1 or 30/1/2/1 (by the halfword 0x605B1FA0) | 0x7EEC00xx | V |
| Profile, level, CABAC/CAVLC | **not found**: block 0 holds no SPS/PPS template. The avcC builder 0x7EEAE6B2 only sets the constraint flags to 0xE0 when profile_idc = 66 | 0x7EEAE6B2 | V (absence); I: the SPS is written by the hardware or a bit-writer |
| Encoder clock | rec_init calls 0x7E46A84B(0,27,1), (0,28,1) and (5,2,1) (clock/power enables, I); rates unknown. IRQs 101/104/109 at level 5 → 0x7EECC621/642/600 | 0x7E6D80B3 | V calls, I role |

### B3. Caps on the bitrate

- **Hard cap (V):** 0x7EEA338C (called from Video Encode 0x7EEA8D18) rejects the stream with 0xAB010002 if:
  - **peak > 24,000,000 b/s** (`cmp 24000000` at **0x7EEA33CB**);
  - peak < average;
  - fps < 1.00 or fps > the maximum;
  - width or height < 64 or above the maximum.
- AVCHD 1080 Fine (24 M peak) sits exactly on the cap. MOV 1080 Fine (20 M) has 4 Mb/s of headroom below it. **V**
- **Other limits (V):** GOP ≤ 60 and code size ≤ 0x7FFFFFF. No level-based clamp was found.
- The QT callback 0x7E6D8900 only logs `AVSCA_INF_BITRATE_OVER` / `CODESIZE_OVER`. It does not act on them. **V**
- Raising MOV above 20 Mb/s would need: the 0x7E6EE4A2 table, the time-limit rate (04-movie §1.2), and staying ≤ 24 M at 0x7EEA33CB or changing that compare. **I** (mapping note, not a patch)

### B4. Output buffer and what a full buffer does

- **Allocations** (0x7E6F36BD, **V**):
  - id 89 "AV middle Work" = **20 MiB**, the AVSCA library heap (SAvScaMemInfo). That the bitstream buffers live in it is **I**.
  - id 90 "AV middle Encode Work" = 3,295,744 B. It is ulWorkAddress, the codec driver's work area.
  - id 82 "Record YC" = 59,535,360 B = 19 × 1920×1088×1.5 (19 input frames ≈ 0.63 s at 29.97 fps; arithmetic V).
  - id 91 audio = 2,304,000 B.
- **Card writes:** ulWriteSize = 1 MiB. DFS_Write 0x7E6D5A31 is synchronous: it posts cmd 0xE00 and polls in 1 ms sleeps (0x7E6D5DEF). The MOOV packet ring has 32 slots and prints "RingBuff OverWrite" when full (0x7E6D6B08). **V**
- **Overflow path (V):**
  1. The callback maps `AVSCA_INF_OVERFLOW` → code 0x2001 and sets 0x60730810 = 1.
  2. MOVREC handler table 0x7E80F054 sends key 0x1001 to 0x7E6EED7D, which sets state 0x602ADFF4 = 4.
  3. That posts **RECMOVIE_BUFFER_LIMIT 0x04070027** (0x7E880EFF). The app string is "buffer full in movie recording!" (0x7EA43CF3; link I).
- **Errors (V):** every `AVSCA_ERR_*` 0x1001–0x100C (including ERR_BUFFER 0x1007 and ERR_FILE 0x100B) → state 3, 500 ms wait, then the same BUFFER_LIMIT event.
  The exception is ERR_SEVERE 0x1004 → 0x7E6EED41: 3000 ms wait, then lock the CPU and loop forever.
- **A card too slow:** the synchronous 1 MiB fwrite stalls, the encoder's frame/stream queues fill, and the overflow produces **BUFFER_LIMIT, so recording stops**. A failed write instead gives RECMOVIE_ERROR (A4). The chain is V; that a slow card is the trigger is I.
  Rough tolerance: at 2.7 MB/s (MOV Fine) about 0.6 s of queued input frames, plus whatever compressed data the 20 MiB heap holds (unknown share). Card stalls longer than a few seconds will stop the recording. **I**

### B5. Open items

- Profile, level, entropy mode, the real CPB size and the codec clock rate: these need the codec driver → MMIO 0x9940xxxx trace. They could also be read from a camera MOV's avcC/SPS (one file would settle profile, level and CABAC).
- The meaning of the 6/2 field (0x7EEA5B4A) and of QP byte 20. Whether AVCHD uses the same 0x1101 → rec_init path.
- The SD source clock rate (A2), which needs the SYSCLK divider for gate 30.

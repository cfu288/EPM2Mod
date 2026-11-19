# Movie bitrate and recording limit: specs (a) and (b) (2026-11-12)

Labels: **V** = read in the code or bytes, or run in the emulator; **I** = inferred. Runtime = block-0 offset + 0x7E421020.
Specs: `experiments/2026-11-12-hardware/patches/movie-bitrate-32.json` (a), `experiments/2026-11-12-hardware/patches/movie-rec-limit.json` (b), with `experiments/2026-11-12-hardware/patches/movie-qp-floor-16.json` (QP).
**Nothing was built.** tools/build.py was not run; nothing was written under build/. The patched block images are in
`/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/br/` (a, b, abq, qba, neg).

## 1. Where the table values go

The table 0x7E6EE4A2 writes one value per MOV mode to both peak 0xA0753564 and average 0xA0753568 (V, `rate_table`).

| Consumer | Uses | Formula / threshold | Follows the table? |
|---|---|---|---|
| QT staging 0x7E6D8317 → SAvScaInit+0x5C → Video Source fmt+68/+72 (02 B1) | peak, avg | plain copies | yes (V, read) |
| Parameter check 0x7EEA338C (struct from Video Encode 0x7EEA8D4B: fps, w, h, avg, flag, **peak = fmt+68**, mode) | peak | peak ≤ 24,000,000 and peak ≥ avg; **not scaled** | the cap is fixed: patched (V) |
| Engine 0x7EEA32CA | both | obj+28 = obj+72 = avg, obj+88 = peak | yes (V) |
| Set-ups 0x7EEA57D4 / 0x7EEA5C4C | avg | target **kb/s = avg/1000** (struct+32 / +40) → hardware | yes (V, `enc_rate_fields`) |
| same | avg | two fields **kb − 1** (+184/+188, +252/+256): HRD bit_rate and cpb_size; the clip has bsc 4, csc 6, so ×1024: 20,480,000 for 20 M | yes (V fields; scales V in the clip; their writer not found, I) |
| same | avg | class **6 if avg ≥ 15,500,000, else 2** (+112 / +92). The clip's cpb_size_scale is 6, so this is probably csc | changes for 720 (I meaning) |
| External-RC path (ctx+120 ≠ 0) 0x7EEA5871, 0x7EEA50E7, 0x7EEA535B | avg | kb << 10 | yes; path probably unused (I) |
| Stream start 0x7EEA5147 (only when ctx+280 = 1) | avg | ≥ 20 M → 4, < 14 M → 1, else 3 → driver vtable+8 | changes for 3 modes (V; meaning I) |
| Rate control twin 0x7EEA726B, at 0x7EEA7645 | avg | ≥ 15.5 M → table 0x7F030448, ≥ 11.5 M → 0x7F0304A8, else 0x7F030508 | changes for 720 (V; used only when ctx+164 = 1, I) |
| Frame-done 0x7EEA64A0 | **peak** | a byte counter ×8 > peak − (fps/100 − 1)·496 → ctx+984 = 1 (first-frame set-up re-run) | yes, it scales with the peak (V; the window is about 1 s, I) |
| Time-limit routine 0x7E6EDE08 | none | its **own imm16 rates**, ceil(peak/4096) in every mode (V, `rate_in_step` true on stock for all 9) | **no**: a separate copy. Patched in step |
| Remaining time 0x7E681D87 | ctx+40 | (40)·600/fps (04-movie §1.2) | yes, from 0x7E6EDE08 (V) |
| Per-frame size limit ulMaxCodeSize 0x7E6D8383 | — | 777,600 / 345,600 / 115,200 B by size | not rate-based (V) |

- **No other copy of the MOV rates (V):** a sweep of 0x7E421020–0x7EF10000 for these values and for 1740/1800000 as
  `mov`/`cmp` immediates finds only the sites above. The other `mov 1740` sites (0x7EDC7F33 …) are struct offsets (V for the 4 checked).
- **No bitrate field in the file (V):** the clip's boxes are ftyp/moov(mvhd, 2 trak, udta)/free/mdat; there is no `btrt`. The only rate the file declares is the SPS HRD.
- **Rate-keyed code outside the encoder (V code; role I):**
  - **Video Decode plug-in 0x7EEB9359:** it rejects fmt+72 > **20,000,000** unless the field is −1 (`cmp` at 0x7EEB93DA, offset 0xA983BA).
    If playback fills fmt+72 from the clip, 24/32 Mb/s clips may not play in the camera (I). Not traced, and not in spec (a).
  - **0x7E6C264F / 0x7E6C2E12:** thresholds 20,480,000 / 17,408,000 / 13,312,000 / 10,240,000, i.e. kb×1024 of the four modes.
    Any rate ≥ 20,480,000 takes the 1080 Fine branch. The caller is near the `[disp_sync]` code; the role is unknown (I).
  - **0x7E6E0734:** an AVCHD 24,000,000 store (V); MOV does not use it.

## 2. Spec (a) `movie-bitrate-32.json`: 9 ops, 24 bytes (V: applied, disassembled)

| Offset | Runtime | Instruction | Old bytes | New bytes |
|---|---|---|---|---|
| 0x2CD563 | 0x7E6EE583 | MOV 1080 Fine `mov imm32,d0` | `fccc 002d3101` (20,000,000) | `fccc 0048e801` (32,000,000) |
| 0x2CD56B | 0x7E6EE58B | 1080 Normal | `fccc 40660301` (17,000,000) | `fccc 00366e01` (24,000,000) |
| 0x2CD57A | 0x7E6EE59A | 720 Fine | `fccc 405dc600` (13,000,000) | `fccc 002d3101` (20,000,000) |
| 0x2CD582 | 0x7E6EE5A2 | 720 Normal | `fccc 80969800` (10,000,000) | `fccc 0024f400` (16,000,000) |
| 0xA823AB | 0x7EEA33CB | peak cap `cmp imm32,d0` | `fcc8 00366e01` (24,000,000) | `fcc8 80f0fa02` (50,000,000) |
| 0x2CCE99 | 0x7E6EDEB9 | 1080 Fine sectors/s `mov imm16,d0` | `2c 1313` (4883) | `2c 851e` (7813) |
| 0x2CCEA3 | 0x7E6EDEC3 | 1080 Normal | `2c 3710` (4151) | `2c e416` (5860) |
| 0x2CCEAA | 0x7E6EDECA | 720 Fine | `2c 660c` (3174) | `2c 1313` (4883) |
| 0x2CCEB4 | 0x7E6EDED4 | 720 Normal | `2c 8a09` (2442) | `2c 430f` (3907) |

- The new rates use the stock rule, ceil(bitrate/4096) (V). They are all < 32768, so the sign extension of `mov imm16,d0` does not matter (V).
- VGA (4 M, 977) and AVCHD are unchanged (V).
- **Derived fields under (a)** (V, `enc_rate_fields`):

  | Mode | kb/s | HRD rate = CPB (1.0 s) | 6/2 class | ≥20/14 M class | RC table (726B) |
  |---|---|---|---|---|---|
  | 1080 Fine | 32,000 | 32,768,000 | 6 (same) | 4 (same) | 0448 (same) |
  | 1080 Normal | 24,000 | 24,576,000 | 6 (same) | 3 → **4** | 0448 (same) |
  | 720 Fine | 20,000 | 20,480,000 | 2 → **6** | 1 → **4** | 04A8 → **0448** |
  | 720 Normal | 16,000 | 16,384,000 | 2 → **6** | 1 → **3** | 0508 → **0448** |

## 3. Spec (b) `movie-rec-limit.json`: 3 ops, 6 bytes (V: applied, disassembled)

| Offset | Runtime | Instruction | Old bytes | New bytes |
|---|---|---|---|---|
| 0x2CCF00 | 0x7E6EDF20 | cap `mov imm16,a3` (all modes but VGA) | `27 cc06` (1740) | `27 201c` (7200) |
| 0x2CCE4B | 0x7E6EDE6B | MOV q6/q3 reserve `mov imm16,a2` | `26 4003` (832) | `26 400a` (2624) |
| 0x2B72CF | 0x7E6D82EF | QT ulMaxRecTime q5/q6/q3 (ms) | `fccc 40771b00` (1,800,000) | `fccc 00dd6d00` (7,200,000) |

- **Encoding:** opcode 0x27 is `mov imm16,a3`, **zero-extended** (V twice: objdump shows `27 00 80` as 32768 and
  `2c 00 80` as −32768; om-emu gives a3 = 0x9000 and d0 = 0xFFFF9000 for the same immediate). The ceiling is therefore 65535.
- **Why 7200, not 65535:**
  - The result is min(cap, 4 GiB time, free-space time) (V). The 4 GiB time is below 7200 s in every mode (at most 6202 s for VGA), so any cap ≥ 2977 s gives the same stop (V).
  - 7200 is also the only value stock pairs with a larger header (VGA). Going above it would also need an ulMaxRecTime and a reserve that stock never uses (I).
- **Overflow (V arithmetic on the routine):**
  - ctx+40 = t·30 ≤ 216,000.
  - The display (40)·600 ≤ 1.3·10⁸.
  - The return value = free time·600 uses no cap; even 2³² free sectors at 977+375 gives 1.9·10⁹ < 2³².
  - Nothing overflows.
- **The reserve is the header area (V):** in PB120161.MOV, ftyp 24 + moov 95,226 + free 330,726 + mdat header 8 = 425,984 B = **832 × 512**.
  The moov is pre-allocated at the front and holds the sample tables, which grow with duration (stsz is 4 B per frame).
  - **Estimate (I), from the clip's box sizes:** the growing tables (stsz, stco ×2, stss, audio stsc) take 149–173 B/s, and the fixed part is about 93 KB (mostly udta 91.5 KB).
  - 832 sectors therefore last for about 1900–2240 s, and VGA's 2624 sectors for 7200–8400 s. Both match the 1800 s / 7200 s design limits.
  - **Without op 2,** 720 Fine (2362 s) and 720 Normal (2976 s) would overflow the header (I). Op 2 costs at most 1 s of recording time.
- **ulMaxRecTime (I):** no reader was found in the AV library (searched the MP4 Mux and the info-event paths).
  It is the only per-quality library parameter that splits q4 from q6/q3 the way the reserve does. So it probably sizes the header (I, strong).
- **Shared instruction (V):** the 1740 instruction is also AVCHD's cap, so AVCHD q5/q3 go to their 4 GiB times (1762/2049 s). AVCHD is not offered on the E-PM2 (X, 01).

## 4. Emulator results (V)

- **Cases:**
  - `rec_limit`: the model now reads all rates, reserves and limits from the image. It adds `peak`, `rate_in_step` and `fill_4g`: the file size at the stop if video ran at the table peak, + 375 sectors/s + reserve, as a share of 4 GiB.
  - New: `rate_table`, `enc_param_check` and `enc_rate_fields` (tools/emu/cases.py, README).
- **Stock:** all five cases match their models (48 / 8 / 18 / 23 / 22 rows, 0 failing).

| Diff vs stock | rec_limit | rate_table | enc_param_check | enc_rate_fields | qp_setup |
|---|---|---|---|---|---|
| (a) | 8 changed (MOV q6/q3, 1 GiB and 64 GiB) | 4 (MOV q6/q3 peak = avg → 32/24/20/16 M) | 5 (peaks 24,000,001…50,000,000 now accepted, incl. avg 20 M / peak 32 M) | 0 | 0 |
| (b) | 11 (8 MOV q6/q3 + 3 AVCHD; VGA unchanged) | 0 | 0 | 0 | 0 |
| (a)+(b)+QP | 11 | 4 | 5 | 0 | 8 (min QP 20 → 16) |

- **Flags:** 0 flagged and no model mismatch in any diff. Applying the three specs in either order gives the same image (sha256 `7e0a322f…`, 32 bytes in 14 runs).
- **4 GiB consistency:** with (a), (b) and all three, every row has `rate_in_step` = true and `fits_4g` = true; `fill_4g` is 0.9992–0.9998 on 64 GiB.
- **Negative control:** a table-only image (ops 1–5) gives 1080 Fine `fill_4g` **1.557**. It also overruns a 1 GiB card's free-space estimate by about 1.56×. So the sector rates must move with the table.
- **Not checked by the emulator:** the hardware, the AV library's header sizing and the actual recording.

## 5. Expected clip length (stop point, large card; V from `rec_limit`, s and min:s)

| Mode | Stock | (a) | (b) | (a)+(b)+QP |
|---|---|---|---|---|
| 1080 Fine | 1595 (26:35, 4 GiB) | 1024 (17:04) | 1594 (26:34) | 1024 (17:04) |
| 1080 Normal | 1740 (29:00, cap) | 1345 (22:25) | 1852 (30:52) | 1344 (22:24) |
| 720 Fine | 1740 (cap) | 1595 (26:35) | 2362 (39:22) | 1594 (26:34) |
| 720 Normal | 1740 (cap) | 1740 (cap; 4 GiB 1958) | 2976 (49:36) | 1958 (32:38) |
| VGA | 6202 (103:22) | 6202 | 6202 | 6202 |

- **Real time:** the stop is a frame count at 30/s and the clip is 29.97 fps, so real time is 0.1 % longer (V arithmetic).
- **QP:** the QP spec changes no length (V: QP bytes are not read by the routine).
- **VBR:** files are smaller than 4 GiB at the stop when the encoder averages below the table rate. The clip in 04 averaged 41 % (V).

## 6. Risks

1. **Encoder throughput above 24 Mb/s is unknown (I).** The cap is software, but the codec hardware (0x9940xxxx) may not sustain 32 Mb/s.
   The failure modes are AVSCA_INF_OVERFLOW → RECMOVIE_BUFFER_LIMIT (recording stops, 02 B4, V) or ERR_SEVERE (CPU lock, 02 B4, V).
   A camera ladder is needed (e.g. table 24 → 28 → 32).
2. **HRD over the nominal rate (I).** The HRD declares kb×1024 (32.77 Mb/s for 32 M), 2.4 % above the time-limit rate.
   If the encoder averaged the HRD rate, the file would reach 4 GiB about 2 % before the stop. Stock 1080 Fine has the same gap (fill 0.9998 at nominal).
   The peak guard at 0x7EEA64A0 compares with the table peak, not ×1024 (V), which should bound it if it acts (I). What happens at 4 GiB is not traced.
   Rates 8000/6000/5000/4000 (ceil(kb·1024/4096)) would remove the gap at about −2 % length.
3. **H.264 Level 4.1 (I).** High@4.1 allows 62.5 Mb/s (VCL) and 62.5 Mbit of CPB; 32.77 Mb/s with a 1 s CPB fits.
   The 50 M cap still fits the level (51.2 Mb/s HRD), with no margin for the 1.024 factor beyond 61 M. The level byte (41) comes from the hardware (I) and stays the same.
4. **Per-frame size limit 777,600 B.**
   - (I) At 32 Mb/s the mean frame is 133 KB. With the clip's I/P ratio (74.8/32 KB) and peak I/mean I (1.73), the largest I-frames are about 500 KB.
   - That is below the limit but 2–3× closer than today.
   - With QP 16, busy scenes push frames toward it. Overrun only logs CODESIZE_OVER (V); the hardware's behaviour is unknown.
5. **Class changes for 720 and 1080 Normal (I):** the 6/2 field (probably cpb_size_scale), the ≥ 20/14 M class, and the RC table.
   They take values 1080 Fine already uses, but at 720 the combination is untested.
6. **In-camera playback:** the Video Decode check ≤ 20,000,000 (0x7EEB93DA) may refuse 24/32 Mb/s clips (I).
   Recording is not affected. To check: play a clip in the camera after a test build.
7. **(b) header sizing (I):** if ulMaxRecTime does not size the moov area, clips longer than about 1800 s may end with a moov that does not fit.
   **Cheap check:** after a (b) build, a 10 s MOV's ftyp+moov+free+8 should be 1,343,488 B (2624 sectors) instead of 425,984 B.
8. **Card (V/I):** 32 + 1.536 Mb/s = 4.2 MB/s against about 28 MB/s sustained (X, E-M5) and SDR50 (V): no issue.
   A card with long write stalls can still stop recording (02 B4).
9. **AVCHD:** its cap rises with (b), untested; AVCHD is not on the menu (X).

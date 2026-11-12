# 03 — Sensor readout, movie image path and memory (E-PM2 v1.6)

Labels: **V** = read in the bytes or code (or run in om-emu); **I** = inferred; **X** = external source (file:line,
paths under `ext/` = the scratchpad `ext/` tree; `01:` = `01-public-sources.md` in this folder).
All addresses are block-0 runtime (0x7E421020 + offset). Scratch scripts: `scratchpad/hw03/`.

## 0. Summary

- **V** The camera core has **8 sensor-mode records** (68 B, table 0x7E7BA370). Movie and live view use
  decimated readouts: HS/HSSC/MSSC/LSSC = 1/3 H × 1/5, 1/10, 1/20 V; HSHR = 1/2 × 1/2 over a 16:9 band; CLIP/FULL/STILL = 1:1.
- **V** No record runs HSHR (the only mode with 1080 lines) above 30 fps. A 9th name, `MOVIE_HSMR`, has no record.
  The movie code knows only 29.97 fps (QT rate 2997, PTS step 3003); there is no 23.976 or 59.94 constant.
- **V** The 1080 Bayer frame is **1646 × 1296 effective** (1662 × 1312 with margins, stride 1680). It is
  stretched to 1920 wide and shrunk to 1080 high. **I** The horizontal 2304 → 1646 step (÷1.4) happens before the IMG engine.
- **V** The encoder input is a **19-frame ring of 1920 × 1088 4:2:0 frames** (3,133,440 B each, 59.5 MB).
  Temporal NR (FNR) keeps one reference frame at 16 bits per sample (8.3 MB for 1080).
- **V** The DRAM window 0x60000000–0x7FFFFFFF (512 MiB, uncached alias +0x40000000) is used up to its top.
  **I** The SDRAM bus is 64 bits wide (64 DQ and 8 DM delay registers). The DRAM clock is not in block 0.

## 1. Sensor-mode records (table 0x7E7BA370, lookup 0x7E64B325)

Lookup 0x7E64B325(d0 = id) scans 8 × 68-B records. A missing id → error 0x0A1B2001 through 0x7E62EA55 (**V**).
Names come from table 0x7E7ABDA0 and the `cam` shell help 0x7E7426DC–0x7E742872 (**V**).

| id | name | fps (+6) | H, V decimation (+8, +10×+12) | line period (+32) | lines/frame at fps (I) | readout lines (+42) | readout time (I) | Bayer geometry used later (V) |
|---|---|---|---|---|---|---|---|---|
| 0 | HS | 30 | 3, 5 | 13.89 µs | 2400 | 700 | 9.7 ms | 1548×700 (eff 1536×691), stride 1568 |
| 1 | HSSC | 60 | 3, 5 | 13.89 µs | 1200 | 700 | 9.7 ms | as HS |
| 2 | MSSC | 120 | 3, 5×2 | 13.89 µs | 600 | 350 | 4.9 ms | 1544×350 (eff 1536×345) |
| 3 | LSSC | 240 | 3, 5×4 | 13.89 µs | 300 | 174 | 2.4 ms | eff 1536×171 |
| 4 | HSHR | 30 | 2, 2 | 6.94 µs | 4800 | 1314 | 9.1 ms | 1662×1312 (eff 1646×1296), stride 1680 |
| 5 | CLIP | 30 | 1, 1 | 6.94 µs | 4800 | 1176 | 8.2 ms | 988×742 (eff 922×691) |
| 6 | FULL | 10 | 1, 1 | 6.94 µs | 14400 | 3504 | 24.3 ms | 4624×3472 (eff 4608×3456), stride 4640 |
| 7 | STILL | 1 | 1, 1 | 6.94 µs | 144000 | 3504 | 24.3 ms | as FULL |

Record fields (**V** bytes; the meaning of each field is given with its own label):
- +0 id (u32); +6 fps.
- +8 horizontal factor (3/2/1); +10 vertical factor (5/2/1); +12 extra vertical factor (1/1/2/4/1/1/1/1).
  **V** 0x7E628422 and 0x7E6297E1 divide prm values (0x2F9A, 0xD4F4) by +8. 0x7E628443 and 0x7E62980D divide prm
  0x2FAA and 0xD504 by (+10 × +12). Their callers are TAKE 0x7E59A66F, movie 0x7E6C7656, REC 0x7E710B5A and EXP 0x7E69A287.
  So these fields are the sensor→readout coordinate divisors.
- +16 = 9216, +20 = 7111 in every record (meaning not traced).
- **+28 = lines per ms × 256** (18432 = 72.0 and 36864 = 144.0) and **+32 = µs per line × 256** (0xDE3 = 13.887 and 0x6F1 = 6.941).
  The two fields are reciprocal (**V** arithmetic). **V (om-emu):** 0x7E640FFB(mode, lines) returns lines × (+32)/256/1000.
  It returns 2400 lines in mode 0 → 33 ms, 4800 lines in mode 4 → 33 ms, 1314 lines in mode 4 → 9 ms and 3504 lines in mode 6 → 24 ms.
  So +32 is the line period, and 2400/4800 line periods make one 30-fps frame (**I**).
- +24 (548/177/269) and +36 (1096/708/1076; equal to 2×+24 or 4×+24) are line offsets added in the exposure maths
  0x7E6360A1/0x7E636206 (**V** use; **I** shutter-delay or overhead lines).
- **+40 = 10 or 18** and **+42 = readout lines**. **V** imgdev 0x7E63E515 computes `+40 + +42/2` lines. It converts
  lines to time through 0x7E63E675/6AD/6E1, which take the current mode from bits 20–23 of word +4 of *(0x605552E0).
  **I:** the mid-frame time from the vertical start. The +42 values match 3456/5 = 691, 2592/2 = 1296 and 3456,
  plus margins.
- **+56/+58** feed the shutter-line calculation (0x7E6360FB/0x7E636178).
- **+60/+62 and +64/+66 are not sizes** (correction to 14b §4, which reads them as "4:3 sizes 3072×2304").
  **V** 0x7E636240 clamps the request's sensitivity, (req+20)→+6 plus ctx+108, to [+62, +60] and stores it at ctx+42.
  0x7E636656 compares ctx+40 with +64 and indexes a gain table by (+64 − +66) >> 8.
  **I:** these are APEX Sv × 256 limits: +60 = 3072 (Sv 12 ≈ ISO 12800 on the standard scale),
  +62 = 1194/1280/1024 (the floor), +64 = 2304 (Sv 9, the knee into the gain table), +66 = base.
  14b's "line offset rec+6" also reads the request, not the record.

Other names (**V** strings):
- The PREPRO mode-mask dump 0x7E64B299 prints `MOVIE_HSMR` as bit/id 9. No record has id 9.
- The default live view is `CAM_SENSOR_MODE_MOVIE_HSSC(default,60fps)` (0x7E742D6D).
- MSSC and LSSC have "AB Field" and "A Field" variants (0x7E7DEB20–0x7E7DEBC2). **I:** field-split readout for 120/240-fps contrast AF
  (`exp 120fps 1 : 120fps AF ON`, 0x7E7DFEF1).
- The EXP AE-parameter sets 0x7E69A522 cover HSHR, HS, HS3D, MSSC, LSSC, CLIP×4/5/7/10/14 and STILL. The CLIP base area
  922×691 is scaled by the magnification (0x7E698815 → 0x7E69941C). **I:** CLIP is the 1:1 window for MF-assist zoom.

## 2. Skipping or binning, the serial interface and the sensor clock

- **Skipping or binning: not decided by the bytes.** The firmware stores only the factors (3/5, 2/2, 1/1). It has no
  "bin", "add" or "mix" readout string. The `skip_x/skip_y` lines of `[exp_debug]` (0x7E69DA7B) print fields of the AE
  parameter block (HSHR 6/8, HS 8/6, STILL 16/14), not the sensor factors (**V**).
  **I:** odd factors (3 H × 5 V) are typical of Sony-style addition plus thinning.
  The 2×2 HSHR could be either mode.
  **X:** reviews describe E-M5 1080 as binned with strong moiré and rolling shutter (01:147–152).
- **Serial path (V):** imgdev → cam_serial.c 0x7E64F744–0x7E650467 → cam_siodrv.c 0x7E6561DA–0x7E65663A
  → MMIO **0x99900000**, IRQ 7, three channels (enable bits 0x08/0x10/0x20000000 in 0x99900014).
  The same unit carries the cam_sg IRQs 4–6.
  The bus-measure text `Measure Cycle (us) : 1VD(VSSG)` (0x7E46D506) ties VD to the agent SSG.
  **I:** 0x99900000 is SSG, the sensor sync generator plus the sensor serial port.
- **Command lists (V bytes, I meaning):** descriptors 0x7E7B0380–0x7E7B04CC hold 8-B entries `{0x18000000, 02 RR VV VV}`.
  The register bytes are 0x00, 0x01, 0x02, 0x03, 0x06, 0x07, 0xA2 and 0xAA, with small values (e.g. 06→0x0002/0x000A, AA→0x0040).
  They look like start, standby and wake writes. **No per-mode register table was found.** **I:** the mode registers are built by code or come from prm.
- **Clock:**
  - **V:** the line rates are exactly 72 kHz (modes 0–3) and 144 kHz (modes 4–7), a 2:1 ratio. imgdev has commands
    `CLOCK_CHANGE_PREPROCESS/HIGH/LOW/CHANGE_RESTART_WAIT` (codes 151–154, name table 0x7E63BAA6).
    **I:** the sensor and pre-process clock has two states, and the decimated modes run at half clock.
  - **Not found:** the sensor master-clock frequency. The clk_rate bases are 24 MHz and 32.768 kHz (0x7E46AB96), set by
    PLL registers at run time. Timer clock 0 = 162 MHz (13f §2.5, I).
  - **I:** the full line (4624 px) in 6.94 µs means ≥ 666 Mpx/s from the sensor, so the output is multi-lane.

## 3. Which mode each movie format uses; why there is no 1080p60 or 24p

| Format (setting 34145) | Encoder size, rate (V) | Sensor mode | Source → output scale (I) |
|---|---|---|---|
| 6 MOV 1920×1080 | 0x7E6D8317: 1920×1080, rate 2997, buffer 777,600 | HSHR (I) | 1646×1296 → 1920×1080: H ×1.167 (up), V ×0.833 |
| 3 MOV 1280×720 | 1280×720, 2997, 345,600 | HSHR (I) | 1646×1296 → 1280×720: H ×0.778, V ×0.556 |
| 4 MOV 640×480 | 640×480, 2997, 115,200 | HS (I) | 1536×691 (4:3) → 640×480 |
| 5 AVCHD 1080 (60i), 3 AVCHD 720 (60p) | strings only, see below | — | — |

- **Mode choice (I, strong):**
  - A lens-sync shell help (0x7E740E58) offers `[capture] 0 : CAM_SENSOR_MODE_MOVIE_HSHR(HD) / 1 : CAM_SENSOR_MODE_MOVIE_HS(SD)`.
  - The IMG resize builder (§4) and `art_get_bayer_size` (0x7E7290B5) carry the HSHR geometry 1646×1296.
  - The direct movie → COM_SET write was not traced.
- **29.97 only (V):**
  - The QT init sets 2997 for all three sizes.
  - The per-frame descriptor 0x7E6EE9BC uses PTS = index × 3003 (90 kHz) for MOV and AVCHD.
  - A scan of the movie code 0x7E6C0000–0x7E6F6000 finds 3003 ×11 and 2997 ×5, but **no 3754 (23.976 step), 5994, 23976 or 59940**.
  - The QT init also stores 6000 at 0x607306E4 next to the 1920×1080 maximum (**I:** an encoder capability field, 60.00 fps).
- **AVCHD (V):** the strings `[AVCHD] Video 1080i` / `720p`, `REC INIT` and `Parameter Error ucQuality` (0x7E80509F–0x7E8050E9)
  have **no code reference**. Only the clip parser (`VideoFormat 1080i:4 720P:5`, 04 §1) and the `fInterlace` print
  0x7E6D8FB8 remain. **X:** the E-PM1 had AVCHD 1080 60i and 720 60p; the E-PM2 has no AVCHD (01:36, 01:46–49).
  **I:** 60i/60p came from the E-PM1 platform and the E-PM2 dropped them. On this sensor table, 60i would have to be 30p frames split into fields.
- **Why no 1080p60 (I, from V facts):**
  1. **No record:** HSHR exists only at 30 fps. The 60-fps record (HSSC) is 1536×691 4:3, and a 16:9 crop of it has about 518 lines.
     The name HSMR (probably "high-speed mid-resolution") is listed but has no record. A lookup of id 9 fails.
  2. **Not the line rate alone:** the HSHR window is read in 9.1 ms, which fits in a 16.7-ms frame
     (HSSC reads 700 of 1200 lines). A 60-fps HSHR record is plausible for the sensor but was never written.
  3. **Encoder and engine:** 1080p30 = 8160 MB × 30 = 244,800 MB/s, just under the H.264 Level 4.0 limit
     (245,760). 60p needs Level 4.2 and twice the IMG throughput (1646×1296×60 = 128 Mpx/s). No 59.94 code path exists.
  4. Memory demand doubles (§5.4).
  - **X:** caduceus-ep7 says a new high-speed FHD mode "needs a new readout and encoder setup"
    (ext/caduceus-ep7/README.md:291). OM-5 notes warn that a menu value does not prove sensor readout at 60 fps
    (ext/oly_fw_analysis/docs/features/om-5/BURST.md:25).
- **Why no 24p (V/I):** no record has 24 fps, and the movie code has no 24p PTS step.
  **I:** 23.976 fps would need a new HSHR record with about 6009 lines per frame at 6.94 µs, a 3754 PTS step and a QT rate of 2397.

## 4. Movie image path

- **Bayer input (V, `art_get_bayer_size` table 0x7E85B38C):** 16-B records `{stride, w, h, 0, eff_w, eff_h, cx, cy}`.
  The records are idx0 full 4640/4624×3472, idx3 HS, idx4 MSSC, idx5 HSHR 1680/1662×1312 (eff 1646×1296, centre 831,656)
  and idx6 CLIP (values in §1). A second table, 0x7E85B3FC, holds 12-B records `{96,64,82,64,…}`.
- **Horizontal ÷1.4 in HSHR (V/I):**
  - **V:** the HSHR AE set (0x7E698658) has `resize` = 91750 = 1.39999 in Q16. Every other set has 65536 (HS 0x7E6986AF,
    MSSC 0x7E698769, LSSC 0x7E6987BF, STILL 0x7E698922). Its use area is 1662×1312.
  - **Arithmetic:** 4608/2 = 2304 and 2304/1.4 = 1646.
  - **I:** the pre-processor (agent PRO) shrinks HSHR lines 2304 → 1646 before the Bayer frame reaches DRAM.
  - **Quality effect (I):** 1080 output has at most about 1646 independent horizontal samples, below 1920, from a 2:1-decimated
    Bayer line. This fits the "soft, moiré" reviews (01:147–150, 01:172–175).
- **Resize/scaler (V, 0x7E54A0D0 = block-builder-A sub-builder for job flag 0x40; F009 in coverage round9-review1):**
  - It picks a "full readout" divisor pair by P+97, the IMG mode code: 0 → 4608×3456 (or 1824 when P+96 = 1),
    4 → 1536×345, 7 → 1536×171, **5 → 1646×1296**, default → 1536×691 (P+96 = 1 → 608×205, the 3D case, I).
  - It scales the crop by (crop × size)/divisor. It stores **Q12 steps ((in−1)<<12)/(out−1)** at block+368/+372, and Q11 phases.
  - For a full HSHR crop: 1080 → H 3511 (0.857, upscale), V 4915 (1.200). 720p → H 5268, V 7377 (**I**, arithmetic on the V formula).
  - Art codes 96/97/165/166 (Dramatic Tone) take their own branch.
- **Noise reduction (V names and sizes):**
  - Temporal frame NR has its own bus master `IMG_FNR` (0x7E46D23B).
  - Movie record allocates one FNR reference (0x7E6D49E0 → 0x7E6D4B82, movrec id 98) of 2 × {614,400 VGA / 1,843,200 720p / 4,147,200 1080}.
    Y is at the base and C at base + half (0x605B12F8/0x605B12FC). **I:** 2 bytes per Y sample and 4:2:2 C at output size.
  - Live view uses 2 × 614,400 (0x7E6D4B22).
  - The per-frame movie image parameters (dump 0x7E6D3BB8) are rgbgamma, ygamma, nv, spc, cb/cr gain, **nr_coring_th_y,
    nr_gain_nr_y, nr_gain_org_y, kedge** (edge gain) and the chroma knee.
  - The IMG_CTRL dump 0x7E6D2908 adds `chSharp`, `ucNoisesprsIndex` and `ulFnrYAddr/CAddr`.
  - **I:** movie NR is spatial Y coring/blend plus a recursive temporal FNR. Sharpening is one `kedge` gain per frame.
  - The values are computed at run time and were not evaluated.
- **YUV handed to the encoder (V):**
  - 0x7E6EE9BC fills a 28-B slot (base 0xA0753590): Y address, width 1920/1280/640, UV address = Y + 2,088,960/921,600/307,200,
    width, PTS. It posts message 0x1105 to the encoder queue (0x7E6EECA6).
  - The Y addresses come from a **19-slot ring** (0xA0753B40, 12-B entries; indices 0xA0753C24–2A wrap at 18, `div 19` at 0x7E6F2F4A).
    Init 0x7E6F3B16 strides 3,133,440 B = 1920 × 1088 × 1.5 from movrec buffer 82 (59,535,360 B = 19 × 3,133,440; 0x7E6F3722).
  - **I:** NV12-style 4:2:0 frames: Y 1920 × 1088 then interleaved CbCr. 1088 = 68 macroblock rows. The 19 frames (0.63 s)
    smooth over encoder and card stalls.
- **Debug capture (V strings):** `cam dramcap [DEPTH] [HW] [VW]`, `Movie Dram Capture Start` (0x7E7AD422, 0x7E7ACFF5).

## 5. Memory

### 5.1 DRAM size and address use
- **V:** the cached window is 0x6xxxxxxx–0x7xxxxxxx, with an uncached alias at +0x40000000 (e.g. ring 0xA0753B40 ↔ 0x60753B40).
- **V** use across the window:
  - lowest: 0x60000000 (`mov` immediates);
  - code 0x7E421020–0x7F1A0FE0;
  - movie pool 0xA52B2400 + 316,790,208 B (302 MiB) → 0xB80CF9C0, or 0xA52B2200 + 209.5 MiB in the other mode (0x7E6F287B);
  - near the top: 0xBFFFA000 (24 KiB copied from flash 0x400F0000 at 0x7E44F473), 0xBFFEA000, 0xBFFDA000, 0xBFF9A000 (0x7E45762D) and 0xBFF7A000 (0x7E5B216B).
- **I (strong):** physical DRAM = **512 MiB**, mapped 0x60000000–0x7FFFFFFF. The block-0 image sits 26 MiB below the top.
  om-emu's E101 entry uses 512 MiB for the same reason (tools/emu/README.md).

### 5.2 SDRAM controller (0x98A00000 / 0x98B00000)
- **V** (driver 0x7E449823–0x7E44B11E, `busmes`/`dqsdelay` shell 0x7E44DBF5):
  - Arbitration config 0x98B00800–0x98B00824: `LLF_PRIORITYGRP25_0/1, REQ_PRIORITY0/1, REQ_MASK0/1, LUMP_REQ_MASK,
    REQ_STATE0/1, ABT_DEBUG`.
  - Per-agent LLF quadruples `LATNUM CYCNUM EMGINNUM EMGOUTNUM`: 37 agents × 16 B at 0x98B00840–0x98B00A8C (MEC2, FSC,
    CACH0/1 hi/lo, SSG, PRO, AE, AF, VSC, FMI, USB, SMCF, SD, EMS1, IMG_TCPL, IMG_YC1/2, CDU_M/Y/C, TS, IMG_RW2/RW3/FNR/
    R4/W4/R1/W1/JRA, OSD, CIC, FD, EMS2, GPU, TXC).
  - Bus-measure counters read/write/refresh: 0x98B00B50–0x98B00B5C (0x7E44A3CD). The window is 1 VD or a CPU time.
  - DQS-rise, DQS-fall and DQ-write delay arrays [0..63] at 0x98B000C0/1C0/2C0, DM-write [0..7] at 0x98B003C0, in units of 1/(128 × DRAMCLK).
  - The SRAM self-refresh code touches 0x98B00014–1C, 0x98B0009C–A4 and 0x98B00818.
- **I:**
  - 64 DQ and 8 DM lanes → a **64-bit data bus**. "1 Count = 64 Byte/Burst" = 8 beats × 8 B (BL8).
  - The printed formula `(Read + Write) x 8Burst / cycle` [MB/s] counts 8 B per count, not 64. One of the two strings is loose.
  - Block 0 writes no SDRAM timing or mode register, so the boot loader sets them up. **DRAM type and clock: not found.**

### 5.3 Movie buffers (V allocations from the movrec pool, 0x7E6F36BD–0x7E6F38DD and 0x7E6F3A0A–0x7E6F3AE9)
- id 82: 59,535,360 (YUV ring).
- id 89: 20,971,520 (20 MiB; **I:** encoded-stream buffer).
- id 91: 2,304,000; id 1: 4,147,200; ids 84/85/86: 614,400 each; ids 87/88: 4,147,200 each.
- ids 99/100/101: 102,400, prm 0xCF94-derived, 77,132.
- id 98: FNR (§4); id 83: 554,496.
- mov_buff "BASE YUV" keep/free: 4 × 614,400 (0x7E6CF8A4).
- Raw Bayer frames are managed by the camera core and IMG buffer code. Their count was not traced.

### 5.4 Bandwidth (I — demand only; the capacity is unknown without DRAMCLK)
1080p30, rounded:
- Bayer write and read: 1680 × 1312 × 2 B × 30 = 132 + 132 MB/s;
- YUV write: 94;
- encoder (current frame, references, reconstruction): about 300;
- FNR read and write: 249 + 249;
- display and statistics: about 50.

That is **about 1.2 GB/s**, so 60p needs about 2.4 GB/s. A 64-bit DDR2-667 bus peaks at 5.3 GB/s and
DDR-400 at 3.2 GB/s, with 50–70 % usable. Bandwidth is therefore likely tight but probably not the first limit for 60p.
The missing record and encoder path (§3) are firmer limits.

## 6. External references (X) and how they compare

| External statement | E-PM2 bytes | Match |
|---|---|---|
| OM-1 board: DRAM 384 MiB, from where the first OSD bank ends (ext/om-emu/emu/src/fw/board.mjs:149–151). Other bodies 256/384/512 MiB (ports.mjs:8951–8968) | 512 MiB window in use (§5.1) | Same method; different size |
| Cached 0x6…/uncached alias 0xA… (ext/om-emu/emu/src/core/mem.mjs:52). OM-3: cached 0x60000000–0x77FFFFFF, uncached 0xA0000000–0xB7FFFFFF (ext/caduceus-om3/research/NOTES.md:418) | +0x40000000 alias, top 0x7FFFFFFF / 0xBFFFFFFF | Same scheme |
| OM-1 frame record +4 word holds a sensor readout-mode id that selects the EMS geometry (ext/om-emu/docs/om1-subject-spec.md:1343–1351) | Mode id in bits 20–23 of word +4 of *(0x605552E0) selects the record (§1) | Same design, older form |
| E-P7: new readout plus encoder set-up needed for a new FHD high-speed mode (ext/caduceus-ep7/README.md:289–291) | No 60-fps HSHR record; HSMR name only | Consistent |
| Menu values ≠ sensor capability; TruePic branding ≠ same memory or sensor wiring (ext/oly_fw_analysis/docs/features/om-5/BURST.md:25, :56) | — | Caution applied |
| Emulators model no sensor or ISP (ext/oly_fw_analysis/docs/tooling/EMULATOR.md:121) | Only pure maths was run (0x7E640FFB) | — |
| E-PL5/E-PM2 share the E-M5 sensor; Sony-made; part number not public (01:134–143) | 4608×3456 effective, 4624×3472 read | Consistent |

No file in ext/ covers E-M5, E-PL5 or PEN-F sensor modes or DRAM. grep for HSHR/HSSC/sensor mode/SDRAM/DDR finds only
OM-1/OM-3/E-P7 material (**V**). The om-emu E118 family shares the E-PM2's INTC and timer layout (tools/emu/README.md:20).

## 7. Corrections and open questions

- **Corrections:**
  - 14b §4: record +60..+66 are sensitivity limits, not "4:3 sizes".
  - 14b §4: in 0x7E636240, "+6" is the request's field, not the record's.
  - 14b §4: "line time (+12/+14/+16)" are request fields; the record's line period is +32 and its line rate is +28.
- **Open:**
  - The movie → COM_SET sensor-mode write, to confirm HSHR for 720p.
  - Where the ÷1.4 horizontal resize is programmed (PRO registers).
  - The sensor serial register map.
  - The DRAM clock and type (they need a boot-loader block or a hardware read).
  - The FNR and kedge values per ISO.
  - The raw Bayer buffer count.

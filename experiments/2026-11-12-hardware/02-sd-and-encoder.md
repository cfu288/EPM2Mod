# E-PM2 v1.6: SD card interface and H.264 encoder limits (2026-11-12)

Block 0 runtime addresses (0x7E421020 + offset). Labels: **V** = read in the bytes or code,
**I** = inferred, **X** = external fact (source named; no page was fetched in this session).
`udf01`/`udfu01` = multiply (map convention). Scratch work: `/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/hw02/`.

## Summary

- **SD bus:** 4-bit, DMA, one multi-block command (CMD25) per contiguous run of up to 65,535 sectors.
  UHS-I is done: S18R in ACMD41, CMD11, a 1.8 V switch, then CMD6 to **SDR50**. With no 1.8 V
  the driver selects **High Speed** (50 MHz) or Default Speed. It has no SDR104, no DDR50 and
  no tuning (CMD19). **V**
- **Bus ceiling:** SDR50 runs SDCLK = source clock / 1. If the source is 100 MHz (**I**), the bus
  peak is 50 MB/s at 1.8 V, 25 MB/s in High Speed and 12.5 MB/s at Default Speed.
- **No card-speed check:** no "slow card" string exists. The speed class is read (ACMD13) but no reader of it was found.
- **Encoder:** GOP 15 (≤ 60), no B-frames (no `ctts`), QP ≤ 51, rate in kb/s with HRD-style fields (a 1 s CPB is I).
  The **hard cap is 24,000,000 b/s peak** (0x7EEA33CB), so AVCHD Fine is at the limit. A slow card ends recording with RECMOVIE_BUFFER_LIMIT.

---

## Part A. SD card interface

### A1. Host controller and register map

- **MMIO:** a two-bank block at 0x99000000. Its `regchk` dump 0x7E5CC42F prints a name for each register (strings 0x7E79A6CB–0x7E79AA0B). **V**
  - Bank 0 (DMA wrapper): DMAMODE +0x00, DMATRG +0x04, DMAHALT +0x08, DMACANCEL +0x0C, DMAENDCLR +0x10,
    DMASTATUS +0x14, DMA_START_ADR +0x18, DMACNT +0x1C, DMABLK +0x20, DMAADR +0x24, DMAREMAIN +0x28,
    IRQ02_STATUS +0x2C, IRQ02_MASK_CLR +0x34, MIC_CONFIG0/1 +0x38/+0x3C, DMA_CONFIG0 +0x40, SDCORE +0x44.
    +0x4C is written but not dumped. The debug help calls it `sdclksel`. **V**
  - Bank 1 (+0x2000, SD core): CMD +0x00, PORTSEL +0x04, ARG0/ARG1 +0x08/+0x0C, STOP +0x10, SECCNT +0x14,
    RSP0–7 +0x18…+0x34, INFO1/INFO2 +0x38/+0x3C, masks +0x40/+0x44, CLK_CTRL +0x48, SIZE +0x4C,
    OPTION +0x50, ERR_STS1/2 +0x58/+0x5C, data port +0x60, CC_EXT_MODE +0x1B0, SOFT_RST +0x1C0,
    VERSION +0x1C4, POWER_CONTROL +0x1E4, EXT_* +0x1E8…+0x1FC. **V**
- **Controller family:** these names and offsets are the Toshiba/Panasonic "TMIO" SD core
  with 4-byte register spacing, as used by Socionext UniPhier. **X** (Linux `drivers/mmc/host/tmio_mmc.h`, U-Boot
  `drivers/mmc/tmio-common.h`; recalled, not fetched). The bit meanings below marked **X** come from those headers.
- **Ports:** the driver keeps 3 port records. Device ids map to ports 0→0, 7→2 and others→1 (0x7E5CCB73, 0x7E5CDF06). **V**
  Port 0 has pads 0x9A101444–0x9A1014E4 and port 1 has pads 0x9A101384–0x9A101424 (0x7E5CC87C/0x7E5CC8D6). **V**
  Port 0 is the card slot. Ports 1 and 2 are other SDIO or internal uses. **I**
- **IRQs:** 93 → 0x7E5CC3A4 and 95 → 0x7E5CC069 (`SDERR`) (0x7E5CBD83). Clock gate id 30 is used by enable 0x7E5CBDB6 and disable 0x7E5CBE0B. **V**
- **Layers:** FAT 0x7E5B7F11 → logsec 0x7E5CBA12/0x7E5CBA48 → request entry 0x7E5CD4D4 (4-deep queue at 0x60547C7C)
  → command builders 0x7E5CD934 (read/write) and 0x7E5CD406/0x7E5CD434 (control) → sdphy queue 0x7E5CE3E1 (4 per port)
  → op dispatch 0x7E5CE457 → hardware issue 0x7E5CBF89 (DMA) and 0x7E5CBFF0 (CMD). **V**

### A2. Clock: divider table and modes

- `clk_set` 0x7E5CBE99(en, div, div1, sel):
  - It waits for INFO2 bit 0x2000 (**X**: SCLKDIVEN).
  - It writes CLK_CTRL = `div | div1<<10`. If `en` ≠ 0, it also writes `sel` to 0x9900004C and then CLK_CTRL = `en<<8 | div1<<10 | div`. **V**
  - Bit meanings (**X**, TMIO/UniPhier): bit 8 SCLKEN, bit 9 OFFEN (auto-stop), bit 10 DIV1 (SDCLK = source).
    Bits 7:0 hold the divider: 0x40 = /256, 0x02 = /8, 0x01 = /4, 0x00 = /2.
- The speed index comes from byte 0 of a 4-byte per-port record at 0x60547CDC + 4·port (byte 1 = bus width, byte 3 = active). The table at **0x7E79AD24** has 8 × 8 bytes:
  `{u8 div, u8 div1, u8 timeout_base, u8 0, u32 sel}`. Bytes are V. The columns from "divisor" on are I.

  | idx | div | DIV1 | sel | SDCLK = src × | Mode, chosen by (V) | At src = 100 MHz (I) |
  |---|---|---|---|---|---|---|
  | 0 | 0x40 | 0 | 0x00 | 1/256 | card init (op 17 ← 0, 0x7E5CCD55) | 391 kHz |
  | 1 | 0x02 | 0 | 0x00 | 1/8 | port 1 only (0x7E5CD248) | 12.5 MHz |
  | 2 | 0x01 | 0 | 0x00 | 1/4 | default after init (0x7E5CD250) | 25 MHz, Default Speed |
  | 3 | 0x00 | 0 | 0x02 | 1/2 | CMD6 HS switch OK, 3.3 V (0x7E5CD35C) | 50 MHz, High Speed |
  | 4 | 0x40 | 0 | 0x01 | 1/256 | right after the 1.8 V switch (0x7E5CD022) | 391 kHz |
  | 5 | 0x01 | 0 | 0x01 | 1/4 | 1.8 V, no SDR25/50 support (0x7E5CD319) | 25 MHz, SDR12 |
  | 6 | 0x00 | 0 | 0x11 | 1/2 | 1.8 V + function 1 (0x7E5CD2F3) | 50 MHz, SDR25 |
  | 7 | 0x00 | 1 | 0x21 | 1/1 | 1.8 V + function 2 (0x7E5CD2C9) | **100 MHz, SDR50** |

- `sel` (0x9900004C) has low nibble 0 = 3.3 V, 1 = 1.8 V and 2 = HS. Its high nibble rises with speed.
  That it sets the sample or drive timing is **I**. The firmware never calls `clk_rate` from the SD driver. So the source rate is
  not in the SD code (**V**). The 100 MHz figure is **I**: it is the only round value at which idx 2 gives the 25 MHz
  Default Speed maximum and idx 7 gives the 100 MHz SDR50 maximum (**X**, SD Physical Layer spec limits).
- **Shared clock:** 0x7E5CE67F uses the lowest index over the active ports, with en = 1. If no port is active it uses en = 3 (SCLKEN|OFFEN). **V**
- **Retry downshift:** a read or write has 4 tries ((24)/(22) counters = 4, 0x7E5CD913). On the last try it sets
  request byte 17 = 1 (0x7E5CDC81, 0x7E5CDD07, 0x7E5CDDE7). Then 0x7E5CE79B stores idx 6 over idx 7 in the port record, so the port stays at half clock (100 → 50 MHz, I) until it is set up again. **V**
- **Data timeout:** OPTION[7:0] = (timeout_base[idx] + n) << 4 (0x7E5CE74A → 0x7E5CBF2E). **V**

### A3. Card init and bus-mode negotiation (0x7E5CCD1C → 0x7E5CCF69 → 0x7E5CD130 → 0x7E5CD239)

Command words are TMIO CMD values (**X**: bits 5:0 index, 6 ACMD, 10:8 response, 11 data, 12 read, 13 multi).
Bit 31 is a firmware flag that keeps the response bits; without it 0x7E5CBFF0 masks the word to `& 0xFF`. **V**

1. Port 0: GPIO 39 ← 1 (0x7E5CCD28), 1 ms delay, idx 0, 1-bit bus, clock on. Then CMD0 (0x300) and CMD8 (0x80000408, arg 0x1AA).
   The driver checks for the 0xAA echo. **V** (GPIO 39 = 3.3 V card I/O supply select: **I**)
2. ACMD41 (0x769): first 0x10000000 or 0x51000000, then a polled loop with **0x51300000** for SD 2.0 cards (0x7E5CCF75/0x7E5CCFA1).
   That is HCS | XPC | **S18R** | 3.2–3.4 V. **V** (bit names **X**)
3. If the OCR has S18A (bit 24) **and** the port is 0 (0x7E5CCFC1/0x7E5CCFD8), the driver switches to 1.8 V:
   - 10 ms delay, **CMD11** (word 0x80001C0B, index 11), then op 18 ← 3 (clock stop);
   - pad 0x9A101444 ← 0x100000, **GPIO 39 ← 0**, 30 ms delay;
   - idx 4, clock on, 1 ms delay. **V** (the steps are V; "GPIO 39 = 1.8 V select" is **I**)
4. CMD2, CMD3 (up to 4 tries), CMD9, CMD7, CMD13 (state must be `tran`). **V**
5. 0x7E5CD130: ACMD51 (SCR, 8 B), then **ACMD6 arg 2 = 4-bit bus**. Op 16 ← 1 clears OPTION bit 15 (0x7E5CBED5); bit 15 = 1-bit width (**X**). **V**
6. If SCR SD_SPEC ≥ 1, 0x7E5CD239 sends CMD6 check (0x80001C06, arg 0x00FFFFF1, 64 B). **V** The support bits it tests,
   0x400 and 0x200 of the LE half-word at status+12, are function 2 (SDR50) and function 1 (HS/SDR25) of group 1. **I**: big-endian status read little-endian.
   - 1.8 V and SDR50 → CMD6 set **0x80FFFFF2**, idx 7. 1.8 V and SDR25 → 0x80FFFFF1, idx 6. 1.8 V and neither → idx 5. **V**
   - 3.3 V and HS → 0x80FFFFF1. If the group-1 result nibble = 1, idx 3, else idx 2. **V**
7. For idx 7 the driver first runs at idx 6. It sends ACMD13 (SD status, 64 B, to card+48), ACMD42 (DAT3 pull-up off) and CMD16 (512), then sets idx 7 (0x7E5CD213). **V**
- **Absent (V):** no 0x80FFFFF3 (SDR104) or 0x80FFFFF4 (DDR50) word appears anywhere in block 0. The SD range has no CMD19 tuning word.
  IF_MODE (+0x1CC, DDR bit, **X**) is never accessed. POWER_CONTROL (+0x1E4) is only read in the dump; the 1.8 V switch is GPIO plus pad.
- This matches the manual's "supports UHS-I" (**X**, 01-public-sources.md §1). It also explains why UHS-I cards stay below
  SDR104 speeds. The E-M5 II test in that file blames missing SDR104. **I** for the E-PM2.

### A4. Data path: width, DMA, block size, batching

- **Bus width:** 4 bit after ACMD6 (above). **V**
- **DMA:** CC_EXT_MODE ← 2 when request byte 52 = 0 (0x7E5CBF99). That is TMIO EXTMODE_DMA_EN (**X**). All read/write builders
  set byte 52 = 0 (0x7E5CD9D8, 0x7E5CDAE4). Bank 0 gets DMA_START_ADR = buffer, DMACNT = SECCNT = count, DMABLK = SIZE = 512,
  and DMAMODE = 1 for reads, 0 for writes (0x7E5CBF89). **V**
- **Commands:** count 1 → CMD17/CMD24 (0x411/0x418); count > 1 → **CMD18/CMD25** (0x412/0x419). For data words 0x7E5CBFF0 adds
  read 0x1000 and multi 0x2000. A 2-sector read is sent as 1 sector at a time (0x7E5CD947). **V**
  STOP ← 0x100 at enable (0x7E5CBDED) is TMIO STOP_SEC: SECCNT-driven auto-CMD12 (**X**). Byte vs block addressing follows card type (0x7E5CD9B8). **V**
- **Request size:** the FAT engine caps each request at the device field (16) (0x7E5B8134 → min in 0x7E5B8291). The SD
  attach writes **65,535** there (0x7E5CDFE2), so the cap is 32 MiB − 512 B. Otherwise a request covers one contiguous cluster run. **V**
  0x7E5B7F11 keeps up to **2 requests in flight** through logsec tickets (loop bound 2, 0x7E5B7F34). The SD layer runs one at a time and queues 4. **V**
- **Movie batching:**
  - AVPI's AFile Sink calls `[MOOV] DFS_StreamWrite` 0x7E6D580C. That queues a 20-byte entry in a 32-slot ring (0x60730314 index) and posts it to the MOOV task (0x7E6D5AD1). **V**
  - MOOV `STREAM_WRITE` 0x7E6D5BB0 sends command 0x1126 on queue 0x7E43E960 (**V**). That queue reaches the MOVREC_FILE `[QT_FILE]` handler 0x7E6D6B40 (**I**).
  - `[QT_FILE] stream_write` 0x7E6D6F07 calls 0x7E6D70A0 → `fileif_fwrite` 0x7E5C5339(buf, size, 1). That is a **synchronous** FILECLBK command 0x10003 → 0x7E5C9DCC → FAT. **V**
  - It then returns the packet (0x110A) with up to 5 × 20 ms retries if the return queue is full (0x7E6D6FE8). **V**
  - A short write → `APPEVENT RECMOVIE_ERROR fwrite error`: event 0x04070028, code 0xFF02 (0x7E6D70E2). **V**
  - The packet size is set by AVPI. The QT params give ulWriteSize = 1 MiB (04-movie §1.1). Each MOV write is therefore about 1 MiB = 2048 sectors,
    one CMD25 when the clusters are contiguous. **I**
- **Speed checks:** no string mentions a slow card or a speed class (regex sweep, **V**). ACMD13 stores the SD status at card+48 (0x7E5CD1F2),
  so the speed class sits at card+56 (0x60547A18 for port 0). **I**
  The 8 callers of the card-info getter 0x7E5CCB73 do not read it. One, 0x7E5CE20A, reads +52 (protected-area size). No reader was found (**I**; not exhaustive).
  The only "too slow" outcome is the movie buffer-full stop (Part B).

### A5. Maximum sustained write rate (estimate, I)

| Bus mode reached | SDCLK (I) | Bus peak (4 bit) | Notes |
|---|---|---|---|
| SDR50 (UHS-I card, 1.8 V) | 100 MHz | 50 MB/s | best case; the last retry drops to 50 MHz |
| High Speed (3.3 V card) | 50 MHz | 25 MB/s | |
| Default Speed | 25 MHz | 12.5 MB/s | |

- Overheads per 1 MiB write: 1 command plus busy, a FAT/cluster update, two in-flight requests, and a synchronous fwrite that waits for completion.
  At SDR50 the camera can drive roughly **20–40 MB/s** if the card keeps up. A UHS-I card is then limited by its own write speed, not the bus. **I**
- Demand: the highest stream is AVCHD 24 Mb/s peak + about 0.2 Mb/s audio ≈ 3.1 MB/s. MOV is 20 + 1.536 Mb/s ≈ 2.7 MB/s (04-movie). **V** (constants)
  So even Default Speed (12.5 MB/s) has about 4× headroom. The SD bus does not cap the bitrate in practice. A card with long write stalls
  (Class 2/4 cards; the official advice is Class 6+, **X** 01 §1) can still overflow the encoder buffer (Part B). **I**
- The emulator was not used. The clock calculation is a byte-table lookup, and `clk_set` polls INFO2, MMIO that the function-only E101 model does not serve. **I**

---

## Part B. H.264 encoder

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
| Buffers | ucVideoBufNum / ulOverflowNum / ulReturnNum / ulMaxDestroyNum = 15/8/9/1, 3/1/2/1 or 30/1/2/1 (by the halfword 0x605B1FA0) | 0x605B1FA0 is read at 0x7E6EE5FB/0x7E6EE60E, inside the request builder (site match: I) | V values |
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

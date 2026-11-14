# Olympus PEN E-PM2 (E101 / model 1010, TruePic VI, body fw 1.6): real hardware limits

Compiled 2026-11-14. Read-only research; nothing under `epm2-tools` was changed.

Confidence labels:
- **VERIFIED** = read in the firmware bytes / official manual or spec / a stream we parsed.
- **REPORTED** = a credible external source says it (named).
- **INFERRED** = deduced from verified facts; could be wrong.
- **UNKNOWN** = could not be established.

Path shorthand: `HW/` = `experiments/2026-11-12-hardware/`,
`FM/` = `experiments/2026-11-08-feature-map/sections/`,
`REPOS/` = `REPOS/`.
Firmware addresses are block-0 runtime (offset + 0x7E421020), fw 1.6.
String offsets quoted as `str@0x…` are block-0 file offsets in
`build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin`.

No board-level teardown of the E-PM2, E-PL5, E-PL6, E-M5 or E-P5 exists in public (web and GitHub swept again
today; see §8). Every chip identity below therefore comes from firmware, not from a photo of the board.

---

## 1. Processor / SoC

| Item | Finding | Confidence | Evidence |
|---|---|---|---|
| CPU architecture | Panasonic/Matsushita MN103 (MN10300 / AM33 family), little-endian | VERIFIED | The whole image disassembles as MN103 (`tools/disasm.py`); lightsnowdev names the E-M5 CPU "Matshi-MN103" (HW/01-public-sources.md §2) |
| Core count | **2 cores**, both running uITRON. CPU0 147 tasks, CPU1 30 tasks; one interrupt controller per core (0x99200000 / 0x99300000) plus inter-CPU doorbells | VERIFIED | docs/firmware-map.md §1; FM/13f-drivers.md MMIO table; task tables at block offsets 0x17CB0 / 0x1C490 |
| "TruePic VI is dual-core" as an Olympus claim | Only a journalist's phrase; but the firmware confirms two cores | VERIFIED (firmware) | HW/01-public-sources.md item 9 |
| What CPU1 does | AVCHD/H.264 middleware (AVPI), art-filter processing, C3D 3D engine | VERIFIED | docs/firmware-map.md §1 |
| Chip part number, die, process, vendor marking | **UNKNOWN**. No teardown. "Panasonic-made SoC" is INFERRED from: MN103 ISA + uITRON; the SD host register layout matches Panasonic TMIO/UniPhier (HW/02 §A2); E-M10 kernel record carries ITRON maker code 0x000B = Matsushita (REPOS/cmdada_em10-fw/notes/rtos.md) | INFERRED / UNKNOWN | — |
| Clocks | Reference inputs 24 MHz and 32.768 kHz, PLL/divider regs 0x98800004–0x98800060 (VERIFIED). Timer prescaler implies clock 0 = **162 MHz** (INFERRED, FM/13f §2.5). CPU core clock: UNKNOWN. A debug list `99MHz / 96MHz / 48MHz / 33KHz` exists at str@0x7ab106 (meaning not traced) | mixed | FM/13f-drivers.md:252–256 |
| Later generations for scale | TruePic VII (E-M10) = 3 MN103S cores; TruePic VIII/IX = 3–4 cores | REPORTED | REPOS/cmdada_em10-fw/README.md; REPOS/nsud-dev_olympus-firmware-notes/docs/hardware/soc-overview.md |

### Hardware blocks on the SoC (VERIFIED names from the SDRAM-arbiter bus-master list, strings of 0x7E44A595, and the MMIO map in FM/13f-drivers.md:84–125)

| Block | MMIO | What it is | Confidence of role |
|---|---|---|---|
| SSG / camera-core unit | 0x99900000 | sensor sync generator + sensor serial port (3 channels) | INFERRED role |
| PRO | — | Bayer pre-processor (does the ÷1.4 horizontal shrink in HSHR video mode) | INFERRED role |
| AE, AF | 0x99B00000, 0x99C00000 | AE statistics, contrast-AF evaluation | VERIFIED |
| IMG engine (IMG_YC1/2, IMG_TCPL, IMG_RW1–4, IMG_FNR, IMG_JRA) | 0x99400000 (+0x99500000) | demosaic/YC, resize (Q12 scaler), temporal frame NR, JPEG; also holds the H.264 codec registers (0x9940xxxx, QP floor reg 0x994043A8) | VERIFIED existence; sub-block roles INFERRED |
| CDU_M / CDU_Y / CDU_C | — | bus masters, role not traced (I: codec/compress unit) | UNKNOWN |
| MEC2, TS | — | I: movie encode and AVCHD transport-stream units | INFERRED |
| EMS1 / EMS2 | 0x99E00000 / 0x99F00000 | motion-estimation / motion-detect units (`per_ems`, `mdet_ems2`) | VERIFIED names |
| FD | 0x99600000 | **hardware face detector**; Omron OKAO PT + Smart Skin libraries run on top | VERIFIED |
| VSC, OSD, CIC | 0x9A900000, 0x9AA00000, 0x9A000000 | display scaler/controller, OSD plane, image compositor (playback effects) | VERIFIED |
| GPU + TXC | 0x9AB00000, 0x9AC00000 | DMP OpenGL ES 1.1 GPU (used only by the C3D menu/3D engine) | VERIFIED |
| SD, USB, SIO×6, ADC, PWM, GIO, timers×10, MEC timing, strobe, lens I/F, jog counters, audio serial | see FM/13f | peripherals | VERIFIED |

Colour pipeline: matrix + per-hue (6 ranges) saturation/hue + R/G/B curves + luma curve + chroma curves
(VERIFIED by the project, `docs/film-emulation.md:166–173`). **No 3D-LUT stage has been found**
(INFERRED absent: nothing in the traced still pipeline; the IMG register set itself is not fully mapped).
Lens distortion and shading correction: the lens protocol delivers `LENS_INFO_DISTORTION` / `LENS_INFO_SHADING`
(str@0x31e2dc, 0x31e2b8) and JPEGs are corrected in camera, so a geometric-remap stage exists (INFERRED which block).

Off-SoC chips named by drivers (VERIFIED strings, identity of the physical part INFERRED):
- Audio codec **Wolfson WM8946** (`aud_dev_wm8946_*`).
- **ADI HDMI transmitter** (`[HDMI-DRV]`, I²C device 0x72 + CEC map 0x78; FM/13f-drivers.md:205) and a **second 0x72 transmitter** on SIO ch3 used for the accessory-port EVF TMDS link.
- **3-axis accelerometer** on SPI/I²C (`per_acc`, `ACC: Who am I?` str@0xa3187; x/y/z offset tables).
- **H8 microcontroller "BC"** running the sensor-shift IS (own firmware in the `OM` tail of the update file; docs/firmware-map.md §2).
- I/O expander, touch-panel controller, **Toshiba NAND** (`tnan` shell).

## 2. Memory

| Item | Finding | Confidence | Evidence |
|---|---|---|---|
| DRAM size | **512 MiB**, cached window 0x60000000–0x7FFFFFFF, uncached alias +0x40000000; addresses in use from 0x60000000 up to 0xBFFFA000 | INFERRED (strong) | HW/03 §5.1; om-emu's E101 entry also uses 512 MiB |
| DRAM bus | 64-bit data bus (64 DQ + 8 DM delay registers at 0x98B000C0…) | INFERRED | HW/03 §5.2 |
| DRAM type / clock | UNKNOWN (set by the boot loader, not block 0) | UNKNOWN | HW/03 §5.2 |
| Run-time headroom | The movie recorder alone takes a **302 MiB pool** (0xA52B2400 + 316,790,208 B) in one mode, 209.5 MiB in the other; code+rodata image occupies 0x7E421020–0x7F1A0FE0 (~13.5 MiB). So hundreds of MiB are free when not recording; a measured free-heap figure does not exist | VERIFIED allocations; free figure UNKNOWN | HW/03 §5.1, §5.3 |
| Still buffer | 16 RAW / 16 JPEG at 8 fps (IR), 12–14 by others | REPORTED | HW/01 §1 |
| Flash type | NAND (Toshiba; BML/STL layers; bad-block management) | VERIFIED strings | FM/01-platform.md:220–240 |
| Flash size | Mapped regions run from 0x40060000 (adj) to at least 0x46200000 (sound) → ≥ 98 MiB of address space; code also loads from an 0x80xxxxxx window. **128 MiB is the likely part size** | INFERRED | `flash addr` map, FM/01-platform.md:230–238; E-M10 flash data ends at 0x47980000 (REPOS/cmdada_em10-fw/notes/system.md:88) |
| Free code space in block 0 | Small padding runs only; tracked in `docs/code-space-map.md` | VERIFIED | that file |

## 3. Sensor

| Item | Finding | Confidence | Evidence |
|---|---|---|---|
| Maker | Sony | REPORTED (official statement by Olympus's president about the E-M5; IR lists Sony for the E-PM2) | HW/01 §4; https://dc.watch.impress.co.jp/docs/news/544400.html |
| Part number (often quoted "IMX109") | **UNKNOWN**. No page I could reach names it (web searches 2026-11-14; Wikipedia "Exmor" has no such row; no GitHub hit) | UNKNOWN | — |
| Geometry | 4/3", 17.2 M total, 16.05 M effective, 4608×3456 output, 4624×3472 read, 3.75 µm, 12-bit ORF | VERIFIED | E-PM2 manual p.116 (specs); HW/03 §1 table idx0 |
| Same sensor as | E-M5, E-PL5, E-PL6 (same body hardware), E-P5 ("same 16MP sensor as the E-M5", dpreview); E-M10/E-PL7 are described by reviewers as "the same 16MP sensor as the E-M5" | REPORTED | dpreview E-P5 and E-M10 reviews; DxOMark E-PL5 page |
| Sensor modes in firmware (8 records, table 0x7E7BA370) | HS 30 fps 1/3H×1/5V (1536×691); HSSC 60 fps same; MSSC 120 fps (1536×345); LSSC 240 fps (1536×171); **HSHR 30 fps 1/2×1/2 16:9 band (1646×1296 after ÷1.4)**; CLIP 30 fps 1:1 window (922×691, MF zoom); FULL 10 fps 1:1 (4624×3472); STILL | VERIFIED | HW/03 §1 |
| Line timing | 13.89 µs/line (72 kHz) decimated modes, 6.94 µs/line (144 kHz) full-width modes; full frame read = **24.3 ms**; HSHR window = 9.1 ms | VERIFIED fields, INFERRED meaning | HW/03 §1 |
| Max sensor frame rate used | 240 fps (C-AF), 120 fps (S-AF), at heavily decimated resolution; full-res 10 fps record (the 8 fps burst) | VERIFIED + REPORTED (IR) | HW/03 §1; HW/01 §4 |
| Skipping vs binning | Not decidable from firmware; reviewers report heavy moiré and aliasing in video | UNKNOWN | HW/03 §2 |
| E-P5 firmware has the same 8 sensor-mode strings | No extra `CAM_SENSOR_MODE_*` name appears only in E-P5 1.8 | VERIFIED (string diff today: `REPOS/thrains0220-byte_ep5-fw-reverse/decoded/00_0100_402c0020.decoded.bin` vs E-PM2 block 0) | scratch `feas/ep5_only.txt` |
| Electronic first curtain (EFCS) | The **E-P5 got "Anti-Shock 0 s" by firmware 1.4** (May 2014) on the same sensor and same SoC generation; Olympus's 0 s anti-shock is described as electronic first curtain below 1/320 s. So the sensor supports an electronic exposure start. The E-PM2 firmware has anti-shock only as a delay (`cam still` option bit 3) and no EFCS string | Sensor capability INFERRED (strong); E-PM2 code path absent VERIFIED | Olympus E-P5 release notes (`REPOS/thrains0220-byte_ep5-fw-reverse/firmware/notes/release_notes/1080_i08.html`); diglloyd 2014-03-31; FM/10a |
| Fully electronic (silent) shutter | No body with this sensor + TruePic VI/VII ever shipped it (E-M5, E-PL5/6, E-PM2, E-P5, E-M10, E-PL7). Live Bulb/Live Time prove the sensor can be read with the mechanical shutter open, so electronic exposure end is physically possible, with a **24.3 ms (~1/40 s) rolling scan** | INFERRED possible at sensor level; no firmware path; rolling-shutter figure from VERIFIED line timing | HW/03 §1; E-PM2 manual p.27, p.74 |
| 1080p60 | No sensor record: HSHR exists at 30 fps only; `MOVIE_HSMR` is a name without a record. The HSHR window reads in 9.1 ms so 60 fps is plausible for the sensor, but it needs a new sensor register set that nobody has (register map not in firmware), 2× ISP throughput, H.264 Level 4.2 and ~2.4 GB/s DRAM traffic | Sensor: INFERRED plausible; whole chain: UNKNOWN, no body of this generation did it | HW/03 §3, §5.4 |
| 720p60 | A 60 fps record (HSSC) exists but is 1536×691 anisotropic (3H×5V) full 4:3; a 16:9 crop has ~518 lines. Encoder load for 720p60 (216,000 MB/s) is below 1080p30 (244,800 MB/s). The older TruePic VI E-P3 recorded AVCHD 720/60p from 30 fps sensor output. The movie code here has only 29.97 fps timing constants | Hardware: INFERRED feasible at low vertical resolution; firmware path absent (VERIFIED) | HW/03 §3; HW/01 §1 |
| 24p / 25p | No record, no PTS constants; would need a new HSHR record (longer frame), plausible for the sensor | INFERRED | HW/03 §3 |
| 4K video | **Not possible**: no 3840-wide readout faster than 10 fps, encoder designed for ≤1080 (per-frame cap 1920×1088, Level 4.x), no code | INFERRED (strong) | HW/03, HW/02 |
| Better 1080 sampling | The 1080 frame comes from 1646×1296 Bayer, upscaled to 1920. A 1:1 crop mode (CLIP, 30 fps) exists only as a 922×691 window. A better readout needs new sensor registers | VERIFIED cause; fix UNKNOWN | HW/03 §3–4 |
| Focus peaking | In the E-P5 it is an **art-filter-style live-view effect** (`ART_EXPOSE_PEAKING_BLACK/WHITE`, `[CapThr]execUpdateThrough() set Peaking`), i.e. it runs on the same art/IMG engine the E-PM2 has (Key Line etc.) | Hardware present: INFERRED (strong); code absent in E-PM2: VERIFIED | E-P5 string diff (today) |
| Live Bulb / Live Time | Present and active on the E-PM2 | VERIFIED | E-PM2 manual p.27, p.74; FM/10-hidden-features.md |
| Live Composite | Only orphan `dummy` names in E-PM2 firmware; shipped first on TruePic VII (E-M10). Needs shutter-open repeated readout (which Live Time already does) plus a lighten-blend of RAW frames in DRAM | Hardware sufficient: INFERRED; code: absent VERIFIED | FM/10-hidden-features.md |
| High-res shot | Needs sub-pixel sensor positioning (VCM IS of the E-M5 II) and an 8-frame merge. The E-PM2's 2-axis unit and its H8 controller firmware were not built for it | INFERRED not feasible | §4 |

## 4. Shutter, mechanics, I/O

| Item | Finding | Confidence | Evidence |
|---|---|---|---|
| Shutter | "Computerized focal-plane shutter", 60 s – **1/4000**, bulb, time; flash sync **1/250 s or slower** (1/160 in RC mode) | VERIFIED (official) | E-PM2 manual p.116–117, p.109 (`feas/manual/epm2.txt` lines 5750–5752, 5790, 5461) |
| 1/8000 | Shutter-speed display tables contain 1/5000…1/12800 strings (str@0x3bfdae…, shared code), but the mechanical unit is a 1/4000 unit; the E-P5 has a different 1/8000 shutter | HARD limit for the mechanical shutter: INFERRED (strong) | manual; dpreview E-P5 |
| Image stabiliser | Sensor-shift, **2-axis (pitch/yaw)**: modes S-IS1 Auto, S-IS2 "vertical (Y)" only, S-IS3 "horizontal (Z)" only. No roll: the v1.5 release note for E-PM2/E-PL5 omits the "rolling stabilization from the body" line that the E-M5/E-P5/E-M10 notes carry; firmware BC records carry gyro x/y only | VERIFIED modes (manual p.46); "2-axis" REPORTED (photographyblog, apotelyt) and consistent with firmware | manual lines 2182–2199; release notes `…/release_notes/1010_i06.html` vs `0970_i23.html`; str@0x385a67 `gyro->x/y`; FM/08:273 |
| IS in movies | Sensor-shift is not used for movies; digital (cropped) IS | REPORTED (IR) + manual p.48 ("image is enlarged slightly") | HW/01 §1 |
| IS controller | Separate H8 MCU with its own firmware image (`OM` tail, "BURE") | VERIFIED format, INFERRED role (strong) | docs/firmware-map.md §2 |
| Accelerometer | **Present**: 3-axis, tasks PER_ROTATE and PER_SLOPE, API `api_user_Get_Slope_Roll_Pitch` (str@0x3b8d95), factory "digitallevel" adjust (str@0xa75e6). Used for image rotation on the stock body | VERIFIED driver; populated chip INFERRED (EXIF orientation works; E-PL6 on the same board has a level gauge) | FM/01-platform.md:201–202 |
| EVF | None built in; VF-2/VF-3 (and VF-4 from fw 1.2) on AP2 | VERIFIED (official) | Olympus E-PM2 Q&A; release notes |
| Accessory Port 2 | Carries: a TMDS video link for the EVF (second HDMI-type transmitter), a UART (shared with console port 1; used by EVF and PENPAL Bluetooth), audio for SEMA-1, power, accessory-ID lines. Supported: VF-2/3/4, SEMA-1 mic adapter, PENPAL PP-1, MAL-1, FL-LM1 | VERIFIED accessory list (official) and driver channels; pin-level wiring INFERRED | FM/13f-drivers.md:205–223; Olympus Q&A table |
| Microphone | Built-in stereo; external mic only through SEMA-1 on AP2 (no 3.5 mm jack) | VERIFIED (official list; IR "Microphone Jack: No") | IR spec sheet |
| Touch screen | 3.0" 460k-dot 16:9 TFT, touch | VERIFIED | manual p.116 |
| Wi-Fi / BT / GPS | None built in. FlashAir (menu "Connection to Smartphone") and Eye-Fi cards supported; Bluetooth only via PENPAL. The E-P5/E-M10 Wi-Fi is an extra radio module with its own tasks (`WIFI_MNGR`, `HTTPD_*`) | VERIFIED | manual p.68, p.103; FM/10e-connectivity.md:128–132 |
| USB | USB 2.0 High-Speed **device only** (core at 0x98F00000). Modes: Storage, MTP, Print (PictBridge), plus PTP. **No PTP InitiateCapture** in any table → no stock tethering. A factory "ADJ" vendor channel (op 0x902B = debug shell over USB) is reachable without a password | VERIFIED | FM/08-connectivity-libs-blocks.md:14; FM/10-hidden-features.md (10f rows); manual p.73 |
| Multi-connector | USB + composite AV out + RM-UC1 wired remote | VERIFIED (official) | manual p.117, p.120 |
| HDMI | Micro (type D), 1080i/720p/480p-576p playback output, HDMI-CEC control, 3D (MPO) output. **"You cannot shoot pictures or movies when the HDMI cable is connected."** So no live view over HDMI on the stock firmware | VERIFIED (official) | manual p.81 (`feas/manual/epm2.txt` line 4053) |
| Clean / live HDMI in hardware | The display controller (VSC) feeds both LCD and the HDMI transmitter; whether it can scale live view to HDMI while the sensor runs was not traced. The 2012 "E-M5 has clean 4:2:2 HDMI, locked" claim was never verified | UNKNOWN | HW/01 §3 |
| Battery / heat | BLS-5, 7.2 V 1150 mAh (8.3 Wh), CIPA ~360 shots. Sensor-temperature warning and automatic shut-off (`ccdtemp` shell exists). Small unsealed body, no heat path: long live-view/video sessions are thermally limited | VERIFIED (official) | manual p.117, p.10, p.48 |

## 5. Video encoder

| Item | Finding | Confidence | Evidence |
|---|---|---|---|
| Stock modes | MOV H.264 1080p30 20/17 Mb/s, 720p30 13/10 Mb/s; AVI MJPEG 720p30 and VGA; all 29.97 fps | VERIFIED (official table + firmware table 0x7E6EE4A2) | HW/01 §1; HW/06 §1 |
| Stream format | High profile @ Level 4.1, **CAVLC**, no 8×8 transform, custom 4×4 scaling lists, I+P only, GOP 15, 1 ref frame, 1 slice | VERIFIED (own clip parsed) | HW/04-mov-clip-analysis.md |
| Real bitrate | 8.4 Mb/s average on the test clip (41 % of budget) because **QP is floored at 20** (reg 0x994043A8, set twice, at block offsets 0xA84A00 and 0xA84E9C) | VERIFIED | HW/04, HW/05-qp-floor.md |
| Limits that are software | Rate table; peak-bitrate check `cmp 24000000` at 0x7EEA33CB; QP floor; 29 min timer and its per-mode rates (0x7E6EDE08); in-camera playback rejects > 20 Mb/s (0x7EEB93DA) | VERIFIED | HW/06 |
| Limits that are format/physics | 4 GiB per file (FAT32 / 32-bit MOV offsets); per-frame code-size cap W·H·3/8 | VERIFIED | HW/06, HW/02 |
| Encoder hardware ceiling (max MB/s, CABAC, B-frames, 8×8) | **UNKNOWN**. The firmware's own capability field says 1920×1080 and "6000" (I: 60.00 fps); AVCHD 1080/60i and 720/60p code is complete but unreachable. CAVLC/no-8×8/I+P look like fixed design choices of the hardware or its microcode | UNKNOWN / INFERRED | HW/03 §3; HW/README.md |
| Patches prepared, **not built or flashed** | QP floor 20→16; rates 32/24/20/16 Mb/s + check raised to 50 M; 29-min cap → 7200 s | emulator-checked only | HW/README.md "Patch specs prepared" |
| How solid | The software limits and stream facts are solid (bytes + a parsed clip). What the encoder does above 24 Mb/s or below QP 20 is untested on a camera | — | — |

## 6. SD interface

| Item | Finding | Confidence | Evidence |
|---|---|---|---|
| Bus | 4-bit, DMA, **UHS-I up to SDR50** (CMD11 1.8 V switch + CMD6); no SDR104, no DDR50, no tuning (CMD19) in the driver | VERIFIED | HW/02 Part A |
| Official | "SD/SDHC/SDXC (UHS-I compatible)" | VERIFIED (official) | manual p.116; Olympus Q&A |
| Clock | SDR50 = source clock ÷1; 100 MHz source is INFERRED → 50 MB/s bus peak | INFERRED | HW/02 §A2 |
| Measured write speed | No E-PM2 test exists. E-M5 (same generation): **~28 MB/s** max with any fast card. E-PM2 buffer-full RAW rate 1.78 fps × ~15 MB ≈ 25–27 MB/s | REPORTED (other body) + INFERRED | HW/01 §5 |
| SDR104 by firmware? | Would need tuning support in the host block; nothing in the driver uses it. Treat ~28 MB/s (≈ 224 Mb/s) as the practical ceiling | INFERRED hard-ish | HW/02 |
| Implications | H.264 at any plausible bitrate: no problem (stream ≤ 3 MB/s today). Sustained RAW burst ≈ 1.8 fps. **RAW video is not feasible**: 16 MP 12-bit ≈ 15–24 MB/frame; even a 1646×1296 12-bit Bayer stream at 30 fps is ~96 MB/s uncompressed, 3–4× the card path | INFERRED (arithmetic on VERIFIED/REPORTED figures) | — |

## 7. Sister bodies and firmware-only differences

Platform groups:
- **Same SoC generation and same sensor (TruePic VI + Sony 16 MP):** E-M5 (2012), E-PL5, E-PM2 (2012), E-PL6 (2013), E-P5 (2013). REPORTED same sensor/processor (IR, dpreview); VERIFIED that E-PL5 1.6 code is byte-identical to E-PM2 in the compared tables and that E-PL6 differs by added menu rows (FM/10-hidden-features.md).
- **One generation earlier (TruePic VI + Panasonic 12 MP):** E-P3, E-PL3, E-PM1 (2011). Same SoC family, different sensor; AVCHD 1080/60i, 720/60p.
- **One generation later (TruePic VII, 3 cores, 16 MP):** E-M10, E-PL7 (2014). Different SoC; features there prove nothing about TruePic VI hardware.

The **E-PL6 is the key witness**: Olympus's own E-PL6-vs-E-PL5 table (https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epl6/)
lists only firmware-type additions: ISO LOW (≈100), level gauge, small AF target, interval shooting (1 s–24 h, 99 frames),
time-lapse movie (AVI MJPEG 1280×720 10 fps), short release-lag mode. Same dimensions, weight, sensor, monitor.
The E-M5 got small AF target + ISO LOW by firmware 2.0; the E-P5 got 0 s anti-shock by firmware 1.4.

| Feature | Which sister has it | E-PM2 hardware present? | Confidence | Note |
|---|---|---|---|---|
| Interval shooting | E-PL6, E-P5, E-M10, E-PL7 | Yes (done by this project) | VERIFIED | code was dormant-complete |
| Time-lapse movie (MJPEG 720p 10 fps) | E-PL6, E-P5 | Yes | INFERRED (strong) | same board as E-PL6; FM/10 lists it with interval as dormant-complete |
| Level gauge | E-PL6, E-M5, E-P5, E-PL7 | **Yes** — 3-axis accelerometer + PER_SLOPE roll/pitch API already in firmware | VERIFIED driver/API; GUI missing | not in E-PM2 manual |
| ISO LOW (≈100) | E-PL6, E-M5 fw 2.0, E-P5 | Yes (same sensor; it is a pull setting) | INFERRED (strong) | |
| Small AF target | E-PL6, E-M5 fw 2.0, E-P5 | Yes (contrast-AF window size is software) | INFERRED (strong) | spot-area setup 0x7E5E6063 exists |
| Short release-lag mode | E-PL6, E-P5 | Yes (same shutter/sensor as E-PL6); costs battery | INFERRED | |
| 0 s anti-shock (EFCS) | E-P5 fw 1.4, E-M10 fw 1.1 | Sensor: yes (E-P5 same sensor). Shutter unit must allow "open first curtain, then wait": the E-PM2 already does this for live view → yes | INFERRED | needs new exposure-sequence code; no code present |
| Focus peaking | E-P5, E-M10, E-PL7 (never E-M5) | Yes — implemented as an art-type live-view effect on the same engine | INFERRED (strong) | code absent in E-PM2 |
| Live Bulb / Live Time | all | Yes, active | VERIFIED | |
| HDR bracketing (HDR BKT) | all | Yes, **active on stock E-PM2** (manual p.63) | VERIFIED | resolves the project's open question in FM/10 |
| In-camera HDR merge (HDR1/HDR2) | E-M10, E-PL7 (TruePic VII) | CPU/DRAM adequate in principle; in the E-P5 the HDR-combine API is still `api_rec_dummy_*` | INFERRED possible, large new code | E-P5 string diff |
| Live Composite | E-M10, E-PL7 | Sensor/DRAM adequate (see §3) | INFERRED | large new code; only `dummy` names |
| Photo Story | E-P5, E-PL7 | Yes (4-window "PSP" multi-through precursor is in E-PM2 firmware, dormant) | INFERRED | FM/10 movie table |
| More art filters / Art BKT | later bodies | Yes (software on the art engine; some hidden Magic Filter modules exist) | VERIFIED modules exist | docs/firmware-map.md:116 |
| Color Creator | E-M1, E-M10, E-PL7 | Hue/saturation controls exist in the pipeline (per-hue table, saturation) | INFERRED | whether E-PL7 has it not confirmed today |
| Movie 1080/60i, AVCHD | E-M5 (60i MOV), E-P3 generation | Encoder: yes (AVCHD code complete, debug-only) | VERIFIED code; unreachable | 60i is 30p split into fields |
| 1/8000 s, 1/320 sync | E-P5 | **No** — different shutter unit | INFERRED (strong) | hard |
| 5-axis IS, IS in live view at half-press, roll correction | E-M5, E-P5 | **No** — 2-axis unit, separate H8 controller | VERIFIED modes / INFERRED hard | hard |
| 3-axis VCM IS | E-M10, E-PL7 | No | — | hard |
| Built-in Wi-Fi + phone remote with live view | E-P5, E-M10, E-PL7 | **No radio.** FlashAir card gives transfer only (card-side Wi-Fi) | VERIFIED | hard, short of a FlashAir |
| Built-in EVF, eye sensor | E-M5, E-M10 | No (external VF via AP2 works) | VERIFIED | hard |
| Tilting screen | E-PL5/6/7, E-M5, E-P5 | No | VERIFIED | hard |
| Mode dial, second dial, extra Fn buttons | E-PL5, E-P5, E-M5 | No (1 dial, few keys; touch screen can stand in) | VERIFIED | hard (UI can remap) |
| Built-in flash | E-P5, E-M10 | No (FL-LM1 clip-on) | VERIFIED | hard |
| 9–10 fps burst | E-M5 (9), E-P5 (9) | 8 fps; sensor FULL record is 10 fps; mechanical limit of this shutter unknown | UNKNOWN | |
| Electronic/silent shutter, 1080p60 | none of TruePic VI/VII with this sensor | see §3 | UNKNOWN / INFERRED | no shipped precedent |
| USB tethering (Olympus Capture) | E-M1, E-M5 II and later only | USB device hardware yes; no capture protocol in firmware, though the ADJ/debug channel exists | VERIFIED absent in firmware | large new code |
| Live view over HDMI | not on this generation's PENs | UNKNOWN (stock firmware blocks shooting with HDMI attached) | UNKNOWN | |

## 8. HARD limits vs firmware choices (summary)

**Hard (no firmware can change):**
1. Mechanical shutter: 1/4000 s top speed, 1/250 s flash sync (a fully electronic exposure could in theory go shorter, with a ~1/40 s rolling scan and no flash).
2. 2-axis sensor-shift IS with its own H8 controller; no 5-axis, no high-res shot.
3. No radio (Wi-Fi/BT/GPS), no EVF, no built-in flash, no mic jack, fixed screen, one dial.
4. Sensor: 16 MP, 12-bit, 10 fps at full resolution, 24.3 ms full-frame readout; fast modes are heavily decimated.
5. Card path: UHS-I SDR50, ~25–28 MB/s sustained → no RAW video, RAW burst drains at ~1.8 fps.
6. No 4K: neither readout nor encoder.
7. H.264 encoder design (CAVLC, 4×4 only, I+P) — probably fixed in silicon/microcode (INFERRED).
8. DRAM 512 MiB, two MN103 cores at ~160 MHz-class clocks (no heavy computational photography in real time).
9. Battery 8.3 Wh and thermal shut-off.

**Firmware-only choices (hardware is there):**
1. Interval shooting [done], time-lapse movie, level gauge, ISO LOW, small AF target, short release lag — all shipped on the hardware-identical E-PL6.
2. Focus peaking (art-engine live-view effect, as on the E-P5).
3. 0 s anti-shock / EFCS (E-P5 got it by firmware on the same sensor).
4. Video: bitrate table, 24 Mb/s check, QP floor 20, 29-min limit, in-camera playback bitrate check; hidden AVCHD/60i path.
5. "No shooting while HDMI is connected" rule; USB mode list; accessory-port menu hidden by a default.
6. Live Composite, in-camera HDR merge, Photo Story, extra art filters: hardware adequate, but large new code.

**Unknown, needs an experiment or a teardown:** SoC/DRAM/sensor part numbers; encoder behaviour above 24 Mb/s and below QP 20; any new sensor readout (1080p60, 24p, 1:1 crop video, full e-shutter) — the sensor register map is not in the firmware as a table; live view over HDMI.

## 9. Sources

Local (project):
- `experiments/2026-11-12-hardware/README.md`, `01-public-sources.md`, `02-sd-and-encoder.md`, `03-sensor-pipeline-memory.md`, `04-mov-clip-analysis.md`, `05-qp-floor.md`, `06-bitrate-and-limit.md`
- `docs/firmware-map.md` (§1 architecture, §2 blocks), `docs/code-space-map.md`, `docs/film-emulation.md:160–176`
- `experiments/2026-11-08-feature-map/sections/01-platform.md:73–89, 198–240`, `08-connectivity-libs-blocks.md:14, 181–194, 273–274`, `10-hidden-features.md`, `10a-shooting-timed.md:140–143`, `10e-connectivity.md:128–132`, `13f-drivers.md:20–42, 84–125, 205–223, 252–256`
- Firmware strings (block 0, fw 1.6; file offsets): accelerometer 0xa3170–0xa33ae; slope/level 0xa7464–0xa761a, 0x3b8d48–0x3b8e4a; gyro x/y 0x385a67; shutter-speed labels 0x3bfd66–0x3bfdce; sensor-mode names (see HW/03); WM8946; `[HDMI-DRV]`.

Local (third-party checkouts):
- `REPOS/thrains0220-byte_ep5-fw-reverse/firmware/notes/release_notes/0970_i23.html` (E-M5), `1000_i06.html` (E-PL5), `1010_i06.html` (E-PM2), `1080_i08.html` (E-P5), `1130_i04.html` (E-M10): Olympus release notes
- `REPOS/thrains0220-byte_ep5-fw-reverse/decoded/00_0100_402c0020.decoded.bin`: E-P5 1.8 main block (string diff → `feas/ep5_only.txt`)
- `REPOS/cmdada_em10-fw/README.md`, `notes/system.md:8–19, 35–99`, `notes/rtos.md`: E-M10 = three MN103S cores, NAND with Denali controller, flash map
- `REPOS/nsud-dev_olympus-firmware-notes/docs/hardware/soc-overview.md`, `mn103-cpu.md`
- `REPOS/flatpanda_om-emu` (E101 512 MiB entry, per HW/03 §5.1)

Web (fetched 2026-11-14 unless marked "via HW/01"):
- Olympus E-PM2 instruction manual: https://download.omsystem.com/pages/inst/epm2/manual_epm2_ENU.pdf (text extract: `/tmp/scratch/feas/manual/epm2.txt`)
- Olympus E-PM2 Q&A / E-PM1 comparison: https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epm2/
- Olympus E-PL6 Q&A / E-PL5 comparison: https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/products/epl6/
- Imaging Resource E-PM2 spec sheet: https://www.imaging-resource.com/PRODS/olympus-epm2/olympus-epm2DAT.HTM ; review https://www.imaging-resource.com/cameras/olympus-e-pm2-review/ (via HW/01)
- dpreview E-P5 review: https://www.dpreview.com/reviews/olympus-pen-e-p5/2 ; E-M10 review: https://www.dpreview.com/reviews/olympus-om-d-e-m10 ; E-PL7: https://www.dpreview.com/previews/olympus-pen-e-pl7 (search-result summaries only)
- EFCS on Olympus 0 s anti-shock: https://diglloyd.com/blog/2014/20140331_1-Olympus-EM1-EFC.html ; https://imaging-resource.com/news/2014/04/01/olympus-e-m1-firmware-update-takes-aim-at-shutter-slap-blur (search-result summaries only)
- 2-axis IS: https://www.photographyblog.com/reviews/olympus_epm2_review/specifications ; https://apotelyt.com/compare-camera/olympus-e-pl5-vs-olympus-e-pm2 (search-result summaries only)
- Sensor maker: https://dc.watch.impress.co.jp/docs/news/544400.html (via HW/01)
- E-M5 card speed: https://cameramemoryspeed.com/olympus-e-m5/fastest-sd-card-tests (via HW/01)

GitHub sweep 2026-11-14 (`gh search repos`, `gh search code`): queries "olympus firmware", "olympus camera firmware", "truepic", "E-PM2", "olympus E-PL3/E-PL5/E-P5/E-M5", "mn10300 camera", "olympus mn103", code `CAM_SENSOR_MODE_MOVIE_HSHR`, `IMX109 olympus`, `OLY_E_101`. Hits: nsud-dev/olympus-firmware-notes, nivag8899/olympus-em1m3-research, flatpanda/om-emu, sympho-ru/olympus-e-pl3-research (all already checked out locally) and the project's own repo. **No new repo covers E-PM2/E-PL5/E-M5 hardware.** Several queries were cut short by the search rate limit; none returned an unknown relevant repo.

Not established / caveats:
- Items marked "search-result summaries only" were not read on the page itself.
- "E-M5 outputs live view over HDMI" and "E-PL7/E-M10 feature lists" beyond what is cited are from general knowledge and were not page-checked; they are not used as evidence above.
- E-PL6 "hardware-identical to E-PL5" rests on Olympus's comparison table (identical size/weight/sensor/monitor, feature rows only) and the firmware comparison, not on a teardown.

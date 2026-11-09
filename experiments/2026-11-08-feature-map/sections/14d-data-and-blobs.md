# 14d. Block-0 data regions and embedded payloads (round D2)

Scope: block 0 (runtime = 0x7E421020 + offset), data from the end of OKAO PT (0x7E731585) to the start of the GUI code (0x7ECCB800), except the code segment 0x7E8F5800–~~0x7EBABF8F~~ 0x7EBABF8D (its last `ret` ends there; 0x7EBABF8E–0x7EBABF8F are 0xFF) (L1 2026-11-09). The brief's two regions are 0x7E730000–0x7E8F0000 and 0x7EBB0000–0x7ECA1020. I extended them to the next real code on each side. Read-only work: no firmware was changed and no extracted code was run. Only headers and table shapes were decoded.

**Labels:** **V** = verified (read in the code or bytes); **I** = inferred.

**Method.**
- I classified every 256-byte chunk by its bytes: strings, pointer table, 8- or 16-bit monotone LUT, all zero, all 0xFF, high entropy, other table.
- For each chunk I listed its readers:
  - every `mov`/`add`/`cmp imm32` in a real function whose value falls in the chunk;
  - every RAM reference into the `.data` copy (§1);
  - every data word that points into the chunk.
- Scripts and dumps are in `$S/d2/data/` (`scripts/segment.py`, `who.py`, `tp.py`, `rule.py`; `runs.txt`, `chunks.txt`, `imms.tsv`, `ramrefs.tsv`).
- The function database is the current build/map (74,554 functions).

## 1. Area and boundaries

The data falls into load segments. Each code segment has its rodata after its code, in link order. Each segment ends with its own static-constructor table.

| Range | Contents | Basis |
|---|---|---|
| 0x7E72CFA1–0x7E731584 | OKAO PT code (13b). It ends with the `ret` at 0x7E731582 and 3 bytes of 0xFF. | V |
| **0x7E731588–0x7E8808BF** | **Segment-1 rodata** (1.25 MB). It is in the link order of the code 0x7E4FE000–0x7E731584: libc, USRSTART/U_SHELL, UI, mec, lens, BC, firmup, IMG, buff, TAKE, files, strobe, AF, cam, api, EXP_MOVIE, display/TP, movie, FACE, mcon, Exif, rec, art, then OKAO. After that come the CMIO blob and the code block below. | V (readers per row, §2) |
| 0x7E8808C0–0x7E880F43 | **A code block after the rodata.** It holds the firmware-update result messages. Japanese romaji strings: `Seikou` ("success") 0x7E7460A3, `Shippai` ("failure") 0x7E7460C1, `Owariyade` ("it's over"). It also holds the LED helpers and the **app-event poster 0x7E880EFF → 0x7E880F0C**: 118 call sites in 76 functions, which pass the event through to 0x7E67DAAB/0x7E67DD54 (api event queue, I). The last function, 0x7E880F39, ends at the `ret` at 0x7E880F40; its DB size of 199 runs into the next table. | V |
| 0x7E880F44–0x7E880F5B | Segment-1 static-constructor table: 6 pointers, 0x7E577D43…0x7E5792E9 (buff). | V (walker below) |
| 0x7E880F5C–0x7E8D9FFF | 0xFF, 356 KB. The flash→RAM copy of section 01 ends at 0x7E881000; the boot task 0x7E44A043 loads that end address (at 0x7E44A074). | V |
| **0x7E8DA000–0x7E8F3113** | **`.data` init image, 102,676 bytes.** The reset code first loads it from flash 0x40779000 to 0xBE8DA000 (call at 0x7E42124D; 0x7E421247 is its size `add` (A6 2026-11-09)). Then it copies it to **RAM 0x602A9B40–0x602C2C53** with {src 0x7E8DA000, dst 0x602A9B40, size 0x7E8F3114−0x7E8DA000} → 0x7E425FA8 (0x7E4212B8–0x7E4212E0). **ROM = RAM + 0x1E6304C0.** Code never loads these ROM addresses; only the reset code does. | V |
| 0x7E8F3114–0x7E8F57FF | 0xFF | V |
| 0x7E8F5800–0x7EBABF8D | Segment-2 code. It is loaded by Usr1 (load range 0x7E8F5800–0x7ECB1000, section 01). | 01 |
| **0x7EBABF90–0x7ECB083B** | **Segment-2 rodata** (1.06 MB). It starts after 2 bytes of 0xFF after the last Smart Skin `ret` 0x7EBABF8B, not "about 0x7EBAC000". | V |
| 0x7ECB083C–0x7ECB0887 | Segment-2 static-constructor table (19 pointers). | V |
| 0x7ECB0888–0x7ECCB7FF | 0xFF: the gap between the two Usr1 loads (01: 0x7ECCB800–0x7F034000). | V |
| 0x7ECCB800 | Segment-3 code: the first GUI function (0x7ECCB800, `[OSD_CONTROL]`). | V |

**Constructor walker 0x7E44B6B0(d0 = segment id).** Its callers are Usr0 0x7E503DD4, Usr1 0x7E504AF9 and 0x7E505005. It calls each word of the segment's table with `calls (a0)`:
- id 1: 0x7E880F44, 24 bytes;
- id 2: 0x7ECB083C, 76 bytes;
- id 3: 0x7F033AC8, 180 bytes;
- id 4: 0x7F06ADC4, 0 bytes;
- id 5: 0x7F0EB484, 0 bytes.

So these tables mark the end of each segment's rodata. **V**

## 2. Data map (every run of 1 KB or more)

- **Mix** = shares of 256-byte chunk classes (str, tab = other table, ptr, lut8/lut16, zero, ff, hent = high entropy).
- **Readers** = real functions that load an address in the run (n), with the two most frequent.
- All boundaries are exact where a table is named; otherwise they are ±256 bytes.
- Row contents are **V** for the readers and the byte classes. A row's module name comes from its readers' module (I where the reader module is itself inferred).

| Start–end | KB | What | Mix | Readers |
|---|---|---|---|---|
| 0x7E731588–0x7E7323FF | 3.6 | libc rodata: `_ctype` 0x7E731588, libm double coefficients, a jump table 0x7E731714 (40 words) whose case targets 0x7E4FEB34–0x7E4FEC8F lie inside the libc function 0x7E4FEA8D (printf format switch, I; (L1 2026-11-09)), powers-of-ten doubles 0x7E7319F0… | tab, hent 33 % | 15: 0x7E4FF9E6, 0x7E500BD5 |
| 0x7E732400–0x7E7343FF | 8.0 | FLSH and Usr strings; **U_SHELL command table 0x7E7332B4** and the dbgall copy 0x7E7326A4 (01) | str 68 % | 78: 0x7E503DD4, 0x7E504AF9 |
| 0x7E734400–0x7E7378FF | 13.2 | ttmr, UI key/jog-dial, PWM/LED and mec (motor) strings and tables | str 70 % | ≈170: 0x7E511C8F, 0x7E506D76 |
| 0x7E737A60–0x7E73B48B | 14.5 | **Per-lens float32 tables.** The index at 0x7E73B258 has 19 × {u32 lens id, u32 n, ptr, ptr} (ids 0x15, 0x17, 2, 3, 7, 6, 5, 1, 0x18, 0x20, 0x22–0x24, 0x105–0x107…). 0x7E521BD4 matches the first word against a key built from bytes 0x604F67B0–B3 (the lens id, I) and copies the selected floats to RAM. Records 0x7E737AE0–0x7E73B257. The role (lens-specific correction) is I. | tab 100 % | 2: 0x7E521BD4, 0x7E51F669 |
| 0x7E73B48C–0x7E7430FF | 31.1 | Lens strings and the lens debug-shell keyword pools (dbgmode/option/command/value) | str 87 % | 175 |
| 0x7E743100–0x7E7461FF | 12.2 | BCHK battery tables, damage-info, BC firmware-update tables (`E. Munch` tag 0x7E745CC0, 08) | tab 65 % | 120: 0x7E539672 |
| 0x7E746200–0x7E746CFF | 2.8 | firmup strings (`DCOLYMP` 0x7E746095, `BOOT` 0x7E746982), message jump table 0x7E7469E0 (02) | str 81 % | 18: 0x7E543DDE |
| **0x7E746D00–0x7E78E7FF** | 286.8 | **IMG library rodata** (13a, 09b). It holds: JPEG DHT 0x7E74A6E8/0x7E74A89D; dispatch tables 0x7E74A3C8 (34) and 0x7E789604 (34); the aspect table 0x7E74A518; art masks 0x7E74C1F0…; **about 90 KB of 16-bit tone curves 0x7E74E000–0x7E763FFF** (readers 0x7E56E837, 0x7E56EB95); engine coefficient and parameter blocks 0x7E764000–0x7E7885FF (0x7E56D1C3, 0x7E566C94, 0x7E559BE5); pixel-defect tables 0x7E789230–0x7E7892B0; the mode-table pointer area 0x7E789600–0x7E78E7FF | tab 60 %, lut16 29 % | 211: 0x7E56D1C3, 0x7E5662D9 |
| 0x7E78E800–0x7E790BFF | 9.0 | buff / buff_recfile tables | ptr 52 % | 42: 0x7E5776A2 |
| 0x7E790C00–0x7E795BFF | 20.0 | TAKE strings, 32-slot hash tables 0x7E791478/0x7E7928B0 (13e), AF 16-bit tables | str 51 %, lut16 28 % | 185: 0x7E594677 |
| 0x7E795C00–0x7E79F1FF | 37.5 | JOB/DCF and ERR LOG strings, debug-prm and charge commands | str 84 % | 229 |
| 0x7E79F200–0x7E7A60FF | 27.8 | Strobe (STB_*) tables, FCS_DBG strings | str 72 % | 146 |
| 0x7E7A6100–0x7E7AAFFF | 19.8 | AF/AE trace-tag pools (`TE`, `CnF`, `Eav`, `EXP_E`…) | str 72 % | 206: 0x7E5F41B1, 0x7E612316 |
| 0x7E7AB000–0x7E7C10FF | 88.2 | Camera-core rodata (03): cam hash tables 0x7E7ABDA0–0x7E7AC414; cam_damage; **cam_imgdev sensor-mode records 0x7E7AEE00–0x7E7BA6FF** (with 8.9 KB of all-zero records 0x7E7B5F00–0x7E7B81FF); cam_set; still phases 0x7E7BE488; live bulb; cam_timer | tab 47 % | 752 |
| 0x7E7C1100–0x7E7DA1FF | 100.2 | `api_*` strings; api_exec tables 0x7E7C8B9C/0x7E7C8C2C; info-id tables 0x7E7C95B4–0x7E7CA6B8 (07) | str 92 % | 687 |
| 0x7E7DA200–0x7E7E1FFF | 31.5 | EXP_MOVIE/SDET (hash table 0x7E7DA1C0) and exp_debug strings | str 65 % | 220 |
| 0x7E7E2000–0x7E7E494F | 10.3 | Display/HDMI/TP strings, `disp` debug-shell keywords | str 73 % | 63: 0x7E6B14DF, 0x7E6B27C4 |
| **0x7E7E4950–0x7E7EFD4F** | 45.0 | **Display gamma LUTs**: 180 × 256-byte non-decreasing 8-bit curves (§3.3) | lut8 99 % | through the set table only |
| 0x7E7EFD50–0x7E7F023F | 1.2 | Gamma set table: {u32 idx, R*, G*, B*} × 4 blocks (15 used + 4 empty slots) | ptr 83 % | 0x7E6B721B (`add 0x7E7EFD50,d2`) |
| 0x7E7F0240–0x7E7F0F77 | 3.3 | VSC/display strings and tables | ptr 57 % | 51: 0x7E6B63FA |
| **0x7E7F0F78–0x7E7FAB33** | 38.9 | **Touch-controller firmware image** (§3.1) | tab | 1: 0x7E6BD8B6 |
| 0x7E7FAB34–0x7E7FD5FF | 10.7 | TP strings, enter/exit packets 0x7E7FAB9F/0x7E7FABAA (11 bytes each, with the offset byte), disp_sync strings | str 83 % | 64 |
| 0x7E7FD600–0x7E8104FF | 75.8 | Movie (mov_*, MOV_ART name table 0x7E7FE240, KDG, AVCHD, QT, AVI, MOVSUPPLY) | str 82 % | 521 |
| 0x7E810500–0x7E813F21 | 14.5 | MOV_FILE and FACE strings | str 91 % | 102 |
| **0x7E813F22–0x7E84EE67** | 235.8 | **mcon** (13e): value lists 0x7E814864, conflict table 0x7E825DA8, 505 × 20-byte records 0x7E84A0B8. The descriptors at 0x7E84A0D0 (stride 20, reader 0x7E7077D3) point to sparse, mostly-zero per-mode records 0x7E83FD00–0x7E8491FF. These are tables, not padding. | tab 76 %, zero 15 % | 60: 0x7E6FDCAE |
| 0x7E84EE68–0x7E84EF1F | 0.2 | ~~Exif/MakerNote/ORF IFD templates 0x7E84EF20 and tag lists (12)~~ **IMGDMA add-job builder table 0x7E84EE68–0x7E84EE73**: 3 code pointers {0x7E70795C, 0x7E7079EA, 0x7E707A1B} = IMGDMA_ADD_YC/BAYER/RGB for req+37 = 0/1/2, read by the dispatcher 0x7E707880 (13e). Then small value tables of 0x7E707Fxx–0x7E7081xx, the 8-entry jump table 0x7E84EEAC (cases 0x7E708270–0x7E708307) and the PrintIM header bytes (L1 2026-11-09) | ptr/tab | 0x7E70788F (`mov 0x7E84EE68,a1`), 0x7E707B4D, 0x7E707F5D, 0x7E7080A9 |
| 0x7E84EF20–0x7E851DFF | 11.7 | Exif/MakerNote/ORF IFD templates 0x7E84EF20 and tag lists (12) | ptr/tab | 19: 0x7E7085D2, 0x7E7096DC, 0x7E708F24 |
| 0x7E851E00–0x7E8554FF | 13.8 | rec_* tables (com jump table 0x7E851DC4) and strings | str 52 % | 193 |
| 0x7E855500–0x7E85CEFB | 30.5 | art strings and tables (hash table 0x7E85C45C, help 0x7E854BB4). Build stamp `10/23 17:15` at 0x7E85CEF0; its only pointer is in `.data` at 0x7E8DE9C4, next to the OKAO pool descriptors (owner I) | str 79 % | 287 |
| **0x7E85CEFC–0x7E86DD5F** | 67.6 | **OKAO PT models and tables** (13b). The last one is the atan LUT 0x7E86DC5F–0x7E86DD5F; then 0x7E86DD60–0x7E86DD7F is 0xFF. | tab 86 %, hent 11 % | 20: 0x7E72DA7F, 0x7E72F5EC |
| **0x7E86DD80–0x7E8808BF** | 74.8 | **CMIO blob**: the ORF ImageProcessing "UnknownBlock" (§3.2) | hent 99 % | 1: 0x7E5586B9 |
| 0x7E880F5C–0x7E8D9FFF | 356.2 | 0xFF | ff | — |
| **0x7E8DA000–0x7E8F3113** | 100.3 | **`.data` init image** (§3.8) | tab 48 %, ptr 29 % | 5,150 functions through RAM 0x602A9B40+ |
| 0x7E8F3114–0x7E8F57FF | 9.7 | 0xFF | ff | — |
| 0x7EBABF90–0x7EBB11FF | 20.6 | EFFECT debug shell (`CIC_MUTEX`, `help`, `set`…), EFCT_EXE tables, BTC/OPP strings | str 57 % | 149 |
| 0x7EBB1200–0x7EBB58FF | 17.8 | Blue SDK stack (STK_CB) strings and tables | str 57 %, ptr 29 % | 116 |
| 0x7EBB5900–0x7EBBE3FF | 34.8 | ACP/OBEX and play_* (play_draw_normal tables) | str 74 % | 333 |
| 0x7EBBE400–0x7EBC39CF | 21.5 | Audio driver strings (`ser`, `cmd_*`, `dac_volume_from_param`, `reg`), AC3 errors; the audio shell table includes 0x7EBBECEC | str 83 % | 214 |
| **0x7EBC39D0–0x7EBCAABF** | 28.2 | **55 test-tone WAV templates** (§3.4) | tab, hent 21 % | 1: 0x7E95F662 |
| 0x7EBCAAC0–0x7EBCDAFF | 12.1 | Audio command tables, Command Window, fsc_drv strings | tab 51 % | 159 |
| 0x7EBCDB00–0x7EBD03FF | 10.2 | HLS and TraShareTakeStatus strings and vtables | ptr 60 % | 164 |
| 0x7EBD0400–0x7EC204FF | 320.2 | C++ Ope/OlyApi rodata: class strings, vtables, OlyHfwPower, the `sdk api` name pools (`type`/`option` tags), the Class::method names (06) | str 68 %, ptr 25 % | 2,179 |
| 0x7EC20500–0x7EC590FF | 227.0 | Cap* and the shooting Cmp*/CmpSqp_* strings and vtables | str 58 %, ptr 38 % | 2,582 |
| 0x7EC59100–0x7EC918FF | 226.0 | Play/edit Cmp* strings and vtables, CmpSts_MfAssist | str 70 %, ptr 28 % | 2,306 |
| 0x7EC91900–0x7EC92317 | 2.5 | OXF strings (`BSE_*`/`BMQ_*`/`BEF_*`); Smart Skin pointer tables 0x7EC92210–0x7EC92317 | ptr 63 % | 69: 0x7EBA5A17 |
| **0x7EC92318–0x7ECB083B** | 121.3 | **OKAO Smart Skin LUTs** (§3.5) | tab 48 %, lut8 39 % | 4: 0x7EBA8F7F, 0x7EBA8E30, 0x7EBA9F3F, 0x7EBA7CA6 |
| 0x7ECB0888–0x7ECCB7FF | 107.9 | 0xFF | ff | — |

## 3. Embedded payloads

### 3.1 Touch-controller firmware image 0x7E7F0F78–0x7E7FAB33 (V, controller identity I)

**Record format (V, all 470 checked by `tp.py`).** Each record is 85 bytes: five I²C write chunks plus 2 bytes of 00 padding.
- The chunks are 17+17+17+17+15 bytes. Each chunk starts with a register-offset byte: 0x00, 0x10, 0x20, 0x30, 0x40.
- Without the offset bytes, the 78-byte payload is `FF 39 | 00 01 02 03 04 05 06 07 | blk_hi blk_lo | 64 data bytes | ck_data | ck_packet`.
- **ck_data** = low byte of the sum of the 64 data bytes (470/470 match).
- **ck_packet** = low byte of the sum of payload bytes 0..76, which includes ck_data (470/470 match).

**Order and range (V).**
- The records write 64-byte flash blocks 0x2C–0x1FF in order, then **0x1E and 0x1F last**.
- Blocks 0x20–0x2B are not written. The bootloader is presumably in blocks 0x00–0x1D, which are never written.
- So the image covers flash 0x0780–0x7FFF of a 32 KB part. 48 blocks are all 0x30 fill.

**CPU (I, strong).** The data is Cypress PSoC1 / M8C code:
- block 0x2C starts with an M8C interrupt-vector table: 4-byte slots of `7D hi lo` (LJMP) or `7E` (RETI), padded with 0x30 (HALT);
- unused flash is filled with 0x30.

Block 0x1E holds `01 0B 13 00 01 14 01 14 02 17 00` (version or ID bytes, I). Block 0x1F ends with `74 7A 8B 85`.

**Protocol (V for the bytes, Cypress TrueTouch bootloader I).**
- The enter packet at 0x7E7FAB9F is `00 FF 38` + key 00..07, and the exit packet at 0x7E7FABAA is `00 FF 3B` + key.
- Bit 0x10 of status byte 1 is polled before entering. This matches the Cypress TTSP bootloader: commands 0x38/0x39/0x3B, default key 0..7, bootloader-running bit 0x10.
- The target address byte is 72 (0x48), which is the 7-bit address 0x24, the TTSP default.

**Sequence in 0x7E6BD8B6 (V).**
1. Set flag 0x602ADC18 and call the GIO op 0x7E4614D6(30).
2. Repeat until bit 0x10 of the read-back is set: write 1 byte `01` (soft reset, I) with 0x7E6BD775(72, …), wait 100 (0x7E6BDDC9), read 31 bytes with 0x7E6BD6C2.
3. Send the enter packet and wait 12,000 ms (`Please 12sec wait`).
4. For r = 0..469, write the 5 chunks at 0x7E7F0F78 + 85·r, then wait 100.
5. Send the exit packet and call 0x7E4614BB(30).

**Bus (V).** 0x7E6BD775 opens SIO logical channel 2 (`sio_request` 0x7E469961 with d0 = 2, retried every 20 ms) and uses the I²C-mode transfer helpers 0x7E463185/0x7E463275. The accelerometer, I/O expander and HDMI paths use the same helpers (13f table: TP on ch2).

**When the camera reflashes the panel (V).** Only on a debug command:
- 0x7E6BD8B6 has one caller, the `tp` handler 0x7E6B27C4, and only after strcmp(arg, `boot_on`) at 0x7E6B2BB6;
- no pointer to 0x7E6BD8B6 exists;
- `tp` is entry 14 of the display shell table in `.data` at 0x7E8DD1B8 (RAM 0x602ACCF8; 21 entries `info duty gamma lpf get bg layer sio i2c histogram crot hd buffer tp alc open close ContEvf nora swivel EndOfDebug`);
- that table is used by the `disp` dispatcher 0x7E6B1402, which is the U_SHELL entry `disp` (words 0x7E7327F0 / 0x7E733400).

So the command is **`disp tp boot_on`**. U_SHELL is also reachable over USB through ADJ op 0x902B (01). There is no automatic version check or update path (no other caller).

**Across bodies (V, byte compare).** The 39,950-byte image is identical in E-PM2 1.1–1.6, E-PL5 1.6 and E-PL6 1.4, and absent from E-P5, E-M10, E-PL7, E-M5 II and PEN-F.

### 3.2 CMIO blob 0x7E86DD80–0x7E8808BF (V layout, tag I)

- **Header:** `43 4D 49 4F 01 00 09 DC` = "CMIO", u32 0xDC090001.
- **Contents:** 76,600 bytes at 7.95 bits/byte. Not zlib (§3.9). It looks encrypted or compressed, and I did not decode it.
- **Size:** 76,608 = 0x12B40 bytes, the value 0x7E55871C returns. The blob ends exactly where the code block at 0x7E8808C0 starts.

**Consumer (V).**
- 0x7E5586B9 sets source a1 = 0x7E86DD80 and fills an IMG job with geometry fields 64/1197 and 32/598 and mode bytes 8 and 27.
- It submits the job with 0x7E544BB5. Its only caller is the ORF header builder 0x7E71969F (`REC ORF header`, 03/12).
- That the job is a plain copy is I.

**Tag (I, strong).**
- ExifTool lists ImageProcessing 0x0635/0x0636 "UnknownBlock1/2: data starts with `CMIO\x01\0`, large, ORF only".
- The ORF ImageProcessing list at 0x7E851380 points to the templates 0x0635 (type 7, 5,764 bytes at struct+10420) and 0x0636 (length 0: filled separately).
- Three runtime builders, 0x7E55885E/0x7E5588FC/0x7E558995 (all called from 0x7E55866A), write `CMIO` + 0xDC090001/0xDC090002/0xDC090003 headers into caller buffers.
- So the static blob is most likely UnknownBlock2.

**Across bodies:** identical in E-PL5 and E-PL6; E-P5 shares only the prefix.

### 3.3 Display gamma LUTs 0x7E7E4950–0x7E7EFD4F (V)

- There are 180 consecutive 256-byte curves, each non-decreasing from about 0x00 to about 0xFF. Their high byte entropy (8.0) comes from the full value range, not from compression.
- The set table at 0x7E7EFD50 holds {u32 index, R LUT, G LUT, B LUT}: 4 blocks, each with 15 used rows (index 0–14), plus empty rows 16–19. That makes 60 RGB triples (= 180 LUTs).
- 0x7E6B721B (`[display gamma]prm error`) indexes the table and copies the curves.
- 4 × 15 per panel or colour mode is I.

### 3.4 Test-tone WAV templates 0x7EBC39D0–0x7EBCAABF (V)

- There are 55 records. Each is a 44-byte RIFF/WAVE PCM header followed by short one-period tone tables.
- The headers cover 8,000/11,025/12,000/16,000/22,050/24,000/32,000/44,100/48,000 Hz, mono or stereo, at 8, 16 or 24 bits.
- The `data` size is 4 s of audio, for example 16 kHz 8-bit mono = 64,000 bytes. Only the periods are stored.
- The first record has 6 period tables of 64/32/20/16/8/4 bytes. At 16 kHz these are 250/500/800/1000/2000/4000 Hz (the sizes are V; the frequencies are I).

**Writer:** 0x7E95F662 (`xxxOLYMP` DCF name). Its caller 0x7E95F5A7 is called by:
- the audio-shell command 0x7E94FA89 (`ARG1:channel(1/2) ARG2:bit(8-24) ARG3:sampling(8000-48000) ARG4:TIME(sec)`, table word 0x7EBBECEC);
- the overlay-B ADJ code 0x7F082681.

So this is a test-recording generator for factory and debug use. The F034 card-file creator 0x7E95FC44 is part of it.

### 3.5 OKAO Smart Skin LUTs 0x7EC92318–0x7ECB083B (V)

All readers are in Smart Skin (0x7EBA7BC1–0x7EBABF8D):

| Table | Size | Shape |
|---|---|---|
| 0x7EC92318–0x7EC924AB | 404 | Falling ramp: 0xFF × 26, then 0xFE … 0x00 |
| 0x7EC924AC / 0x7EC924B8 | 12 + 12 | Zero (two small parameter records) |
| **0x7EC924C4–0x7EC9FD3A** | 55,415 | Rising curve, f(i) for i = 0…55414; inputs above 55414 → 255 (0x7EBA9BC8 `cmp 55414`). f(0) = 0, f(30000) = 20, f(50000) = 148, f(55414) = 255: an exponential-like falloff of a squared distance (shape I) |
| **0x7EC9FD3B–0x7ECAFD3A** | 65,536 | 2-D table T[a][b] = **max(1, ⌊a·b/255⌋)** (all 65,536 entries match). Indexed `(a<<8) + b` at 0x7EBA9D65 |
| 0x7ECAFD3B, 0x7ECAFE3B, 0x7ECAFF3C… | 256 each, to 0x7ECB083B | Ease curves (0→254 rising; 255→2 falling) |

These tables explain the 0x7ECABB20 high-entropy window and the 12 spurious functions here. They are identical in all 8 bodies checked.

### 3.6 OKAO PT model tables 0x7E85CEFC–0x7E86DD5F (V bounds)

13b gives the contents (defaults 0x7E85D08F, pose dictionaries 0x7E86D994, sin/cos 0x7E86DACC). The only change is the end: **0x7E86DD5F**, the end of the atan LUT that starts at 0x7E86DC5F (reader 0x7E7310FE). It is not "~0x7E86DCxx". What follows (0x7E86DD80) is the CMIO blob, which is not OKAO.

### 3.7 Per-lens float tables 0x7E737A60–0x7E73B48B

See the row in §2. The records are float32. Many values are near 115.9 (0x42E7xxxx) or small coefficients. The format is V; the meaning is I.

### 3.8 `.data` init image 0x7E8DA000–0x7E8F3113 (V)

- It is in link order of all code, so each module's initialised globals sit together. Examples:
  - ui_jogdial 0x7E8DA200;
  - the IMG pointer tables 0x7E8DAE00;
  - the display shell table 0x7E8DD1B8;
  - the TP state 0x7E8DE000;
  - EFCT_EXE 0x7E8DEA00;
  - the BT stack 0x7E8DF000;
  - OXF/GUI 0x7E8E4F00–0x7E8EED00;
  - C3D GL state 0x7E8EED00;
  - the AVPI plug-in registry 0x7E8EFA18 (= RAM **0x602BF558**, answering 13b's open question);
  - BASIC/DPS 0x7E8F1200;
  - ADJ/PTP 0x7E8F1800;
  - CAPI 0x7E8F2100.
- The 969-entry `Class::method` name-pointer table 0x7E8E13B0–0x7E8E22D3 (06 §Q8, 05) is at RAM 0x602B0EF0.
- To find the users of any `.data` item, subtract 0x1E6304C0 and search for the RAM address. 18,068 such references in 5,150 functions (`ramrefs.tsv`).

### 3.9 What block 0 does not contain (V scans)

- **Compressed streams:**
  - Every 0x78 xx header with a valid FCHECK was tried with zlib: none decodes, anywhere in block 0.
  - zlib inflate 0x7EE5FE61 has two callers, both in libpng (0x7EE5DA3F row read, 0x7EE5EE73 finish).
  - libpng's only caller is the C3D PNG loader 0x7EE3306E, which is reached through the C3D table word 0x7F027CB4. So PNG input comes from outside block 0 (I: C3D data or card).
  - No gzip, bzip2, xz or PK headers.
- **Bitmaps and fonts:** no BMP (checked header fields), PNG, GIF or JPEG file in these regions. The only `FF D8 FF` is inside a 16-bit ramp at 0x7E795887. No standard 8×8 or 8×16 glyph patterns occur in block 0. Fonts are in block 1 and the frame JPEGs in block 3 (map §2).
- **Other firmware images:** none besides the TP image. The BC stabiliser H8 firmware is in the package `OM` tail; lens and strobe firmware come from card files (02).

## 4. Patterns: classifying an address in these regions by its bytes

| If the bytes at the address… | then it is |
|---|---|
| lie in 0x7E7F0F78 + 85·r and `00 FF 39 00 01 02 … 07` repeats every 85 bytes | TP record r; the chunk-offset bytes 0x10/0x20/0x30/0x40 are at +17/+34/+51/+68 |
| form 256-byte runs climbing from about 00 to about FF | gamma LUT (0x7E7E49xx–0x7E7EFDxx) or Smart Skin curve (0x7ECAFxxx) |
| look random and lie between 0x7E86DD80 and 0x7E8808BF | CMIO blob |
| start `RIFF ?? ?? ?? ?? WAVEfmt ` | WAV template (0x7EBC39D0–0x7EBCAAxx) |
| are float32 words 0x3x/0x4x in the high byte, 16-byte aligned | lens float records 0x7E737AE0–0x7E73B257 |
| contain pointers into 0x7E4xxxxx–0x7F0xxxxx and RAM, inside 0x7E8DA000–0x7E8F3113 | `.data` init values; the code uses the RAM copy at addr − 0x1E6304C0 |
| are u16 values climbing in steps of 0–0x400 | IMG tone curves (0x7E74E000–0x7E763FFF) or mcon/TAKE u16 tables |
| alternate NUL-terminated ASCII with `ptr`/`u32` | the rodata of the module whose readers are named in §2 |

## 5. Spurious functions in these runs

**List:** `sections/14d-false-functions.tsv` (601 rows; columns `addr`, `containing_data_run`, `reason`).

The 591 database entries with data_page = 0 that start inside the runs above: IMG rodata 233, CMIO 128, OKAO PT models 102 (the brief said 103), TP image 28 (the brief said 29; both counts are from the current DB), WAV templates 26, gamma LUTs 24, mcon 13, Smart Skin 12, others 25.

The TSV adds 10 **false starts inside real code** whose only DB caller is a decode inside a data run:
- 0x7E641F48: cuts 0x7E641F0F mid-instruction;
- **0x7E731288**: inside 0x7E73121F (see 13b correction);
- 0x7E880957 and 0x7E880E47: inside 0x7E880DD9's block;
- 0x7E8FAC5B;
- 0x7EB64BD2/0x7EB64C13/0x7EB64C55/0x7EB64C99;
- 0x7E8F9F46, which follows a `ret` and is probably a real pointer-reached function.

0x7E735B1E has a "real" caller only because the DB body of 0x7E731532 runs 2.7 KB past its `ret` at 0x7E731582, through `_ctype` and the libm tables.

**Why the current test misses them (V).**
- The data-page test needs ≥ 50 % strings or > 60 % "table-like" words. Binary tables (LUTs, floats, M8C code, the CMIO bytes) score low on both.
- Calls decoded inside such pages then create starts. The rodata pages here have code-like word statistics but no strings.

**Rule D (proposed), measured with `scripts/rule.py`:**
1. **Seed:** the decoded body contains at least one anomaly instruction:
   - `break` (0xFF);
   - `unknown`;
   - a `udf*`/`udfu*` other than `udf00`, `udf01` or `udfu01`;
   - a register list with `exreg`/`exother`/`other` in `movm`/`call`/`ret`.
2. **Fixpoint:**
   - un-flag a function if any caller is an un-flagged function (self-calls ignored);
   - flag a `call`-only start whose callers are all flagged, unless the start directly follows `ret`/`retf`/`rets`/`rti`.
3. **Also flag** a `call`-only start with no recorded caller that does not follow a return.

**Results.**
- **Recall:** 586 of 591 (99.2 %). The misses are 0x7E735B1E (above) and four small starts that happen to follow a return byte or call only themselves.
- **On known code** (71,435 functions in 0x7E421020–0x7E4C5533, 0x7E4FE000–0x7E731584, 0x7E8808C0–0x7E880F43, 0x7E8F5800–0x7EBABF8D, 0x7ECCB800–0x7EECE318), rule D flags 31:
  - 9 are the code false starts above (correct rejections);
  - 21 are data inside those ranges: the reset-code string pool 0x7E426704, and 0x7E46C458 plus 19 starts in 0x7E47C3A5–0x7E47ED42, after the drivers end at 0x7E46C308;
  - 1 is unclear: 0x7E4325CE, 21 bytes in the kernel, 0 callers, with a `break` at +0x14.
- **False-positive rate: at most 1 / 71,435 (0.0014 %)**, or 31 / 71,435 (0.043 %) if every hit outside the studied runs is counted as an error.
- In real code the anomaly share is 0 at the 99.9th percentile; in the spurious set the median is 1.6 % of instructions.

**Byte statistics alone do not work.** "No callers and > 30 % 0x00/0xFF" catches 12 of 591 and flags 620 real functions, because 30 % of real functions are reached only through pointers and many have zero-heavy literals.

**Page-level complement (I, not measured):** treat a 4 KiB page as data if it has ≥ 2 rule-D seeds and no start with a caller outside the page. That would also drop the calls decoded in these pages before they make starts.

## 6. Corrections

**Regions table (docs/firmware-map.md):**

| Row | Correction |
|---|---|
| "~~0x7E730000–0x7E8E0000~~ (L1 2026-11-09) Mostly read-only data … code 0x7E8808C0–0x7E880E84" | The OKAO PT code ends at 0x7E731584. The table should list: segment-1 rodata 0x7E731588–0x7E8808BF (link order, §2); a code block 0x7E8808C0–**0x7E880F43** (firmup result messages/LED **and the app-event poster 0x7E880EFF/0x7E880F0C**, 76 callers); the constructor table 0x7E880F44; 0xFF 0x7E880F5C–0x7E8D9FFF; **`.data` image 0x7E8DA000–0x7E8F3113 → RAM 0x602A9B40** (V) |
| "0x7E8E1020–0x7E8F5800 Data (method-name pointer tables, padding)" (05) | This is the second part of the `.data` init image, not stand-alone tables; 0xFF from 0x7E8F3114 (V) |
| "~~0x7EBA1020–0x7ECA0000~~ (L1 2026-11-09) … data from about 0x7EBAC000" | Rodata starts at **0x7EBABF90**. The tail 0x7EC92318–0x7ECB083B is the OKAO Smart Skin LUTs, not GUI data (V) |
| "~~0x7ECA1020–~0x7ECC8000~~ (L1 2026-11-09) is mostly data. ~0x7ECC8000–… GUI" (13d) | Smart Skin LUTs to 0x7ECB083B, constructor table 0x7ECB083C–0x7ECB0887, 0xFF to 0x7ECCB7FF; **GUI code starts at 0x7ECCB800** (V) |
| Map §1 "Overlays: part of block 0 is copied from flash at boot" | Add the `.data` image copy by the reset code (§1) and the constructor walker 0x7E44B6B0 with one table per segment (V) |

**Section 13b:**
- The OKAO PT models end at 0x7E86DD5F (§3.6). 0x7E86DD80–0x7E8808BF is the ORF CMIO blob (V).
- **0x7E731288 is not a function entry.** It sits inside 0x7E73121F (the `jmp 0x7E731356` at 0x7E731262 crosses it). Its only DB caller is a bogus decode at 0x7E738CFC in the lens float tables. The "byte multiply-accumulate" row should read 0x7E73121F / 0x7E731394 (V).
- The DB size of 0x7E731532 (2,766) is wrong. The function ends at 0x7E731584 (V).
- AVPI registry: RAM 0x602BF558, the `.data` copy of 0x7E8EFA18 (V).
- Smart Skin uses the LUTs in §3.5 (V).
- The "103 functions in 0x7E85CEFC–0x7E86DCFF" are 102 in the current DB.

**Section 08:**
- The TOUCHPANEL "touch-controller firmware bootloader" is the Cypress TTSP-style bootloader host (I, strong). It sends a 470-record image (§3.1) over SIO ch2 (I²C mode, I) to address 0x24. It runs only for `disp tp boot_on` (U_SHELL, or ADJ 0x902B over USB) (V).
- The image is the same in E-PM2/E-PL5/E-PL6 (V).

**Section 03:**
- The ORF path (0x7E71969F) also copies the static CMIO blob through 0x7E5586B9 (V).
- The scope line "0x7E6E0000–0x7E730000 (rec_*, FACE_*, art_*)" should also name mcon 0x7E6FCA60–0x7E70787F, ~~the Exif/MakerNote writer 0x7E707880–0x7E70B434 (12)~~ the IMGDMA add-job builders 0x7E707880–0x7E707A9C (dispatcher + 3 builders through table 0x7E84EE68; callers `[MOV]imgdma_exec` 0x7E6DADB9, `REC MULTIEXP ADD EXEC` 0x7E7172B4, art 0x7E71C7BE), unnamed helpers 0x7E707A9D–0x7E708311, the Exif/MakerNote writer 0x7E708312–~~0x7E70B434~~ 0x7E70B3F7 (12; its last `ret` is at 0x7E70B3F5, and 0x7E70B3F8, called only by Usr0 0x7E503DD4, is a rec init) (L1 2026-11-09) and OKAO PT 0x7E72CFA1–0x7E731584.
- The camera-core rodata is at 0x7E7AB000–0x7E7C10FF (§2).

**Section 07:** I found no error in my regions. Additions:
- the info-id tables 0x7E7C95B4–0x7E7CA6B8 sit inside the api rodata row;
- the 505-record table 0x7E84A0B8 is followed by its 20-byte descriptors 0x7E84A0D0 into the sparse per-mode records 0x7E83FD00–0x7E8491FF (§2).

**Section 05 Q8** is answered by §3.8: the block is the `.data` init image.

**Section 06 Q8:** the name table 0x7E8E15FC… lives in RAM at 0x602B0EF0+ (§3.8).

## 7. Open questions

1. The CMIO payload: is it encrypted, and is it really UnknownBlock2 (0x0636)? The IMG job mode 27 and the 64 × 1197 shape suggest a plain DMA copy; check against a real E-PM2 ORF.
2. What the per-lens float tables (19 lens ids) hold, and why only these ids.
3. The role of the 4 gamma blocks (LCD, EVF types, colour modes?) and of the selector 0x7E6B721B's index.
4. What the TP version bytes in block 0x1E mean (`01 0B 13 00 01 14 01 14 02 17`), and whether ADJSLF `TPVercheck` reads them. No code path compares them with the panel today.
5. GIO pin 30 around the TP session (0x7E4614D6/0x7E4614BB): is it the TP reset line or its interrupt?
6. 0x7E4325CE in the kernel: code or data?
7. Who reads the 969-entry method-name table in `.data`? No reference to its first RAM entry 0x602B0EF0 was found; there are references to 0x602B0E94–0x602B0EB4 just before it (0x7E96C6D5, 0x7E96D54A).

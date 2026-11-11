# 02. Caduceus features: how each works, and whether it could exist on the E-PM2

Date 2026-11-11. Static work only: nothing was run from the external repos, nothing was built or flashed,
and no map file was changed. E-PM2 = v1.6 block 0, runtime = 0x7E421020 + offset.

Labels: **[V]** read in our E-PM2 bytes or our map (bytes re-read for this report unless a map section is
cited); **[X]** stated by an external source (`EP7:` = caduceus-ep7, `OM3:` = caduceus-om3, `FISHCU:` =
oly_fw_analysis; path:line); **[I]** my inference.

Related: `/path/to/research_notes/caduceus-om3-ep7.md` (earlier overview that read no E-PM2
bytes) and `experiments/2026-11-09-film-portra/NOTES.md` (the E-PM2 look work). This report re-checks
their E-PM2 claims against the bytes and adds the movie-limit, LCD, effect-list, aspect and log findings.

**State of our project.** The brief says "nothing flashed". `docs/camera-log.md` records four flashes
on the user's body: stock, `pixel-hacking`, stock again, and on 2026-11-11 `film-portra-xp-labelled`
(24 base-gamma tables, one look curve, one saturation pair, one label) [V]. The ratings below assume
that data-only edits to block-0 tables are a proven class on this body.

## 1. What the source is and how it works

- **Caduceus E-P7** (PEN E-P7 1.1, TruePic VIII, cakelesscoder): about 60 patch folders (MN103 stubs and
  data edits) merged into one edit list. A builder downloads OM's firmware, checks every `expect` byte
  and writes the update file plus a stock restore file. Looks and state are on the SD card (`EP7MOD/`),
  loaded on the first half-press [X `EP7:README.md:306-321`, `:334-340`].
- **Caduceus OM-3** (OM-3 1.1, TruePic X, androidfanman): a separate code base (one big `editor.s`
  plus a code block loaded from the card) that shares the look format and the Control Panel [X
  `OM3:README.md:141-143`, `OM3:NOTICE`].
- On both bodies the colour features are built on the **COLOR-profile engine**: a 12-sector table, the
  COLOR 1–4 editor and their settings. Each feature is a hook on a stage that the stock firmware already
  has. Nothing is new image-processing hardware.

## 2. What applies to the E-PM2

### 2.1 Feature by feature

Feasibility: **high** = data-only, the address class is proven on our body; **medium** = data-only but
the site or its effect is not proven, or a small code hook; **low** = new code on a capture or display
path, or many unknown tables; **not possible** = the stage does not exist on the E-PM2.

| Feature | Their mechanism | E-PM2 counterpart | Feasibility |
|---|---|---|---|
| **Film simulations** (EP7 29, OM3 20) | 64-byte look records from the card. Picking a look writes stock settings and fills the slot that the HSL/tone/WB hooks read [X `EP7:README.md:38`; `research_notes` §2.1] | A look is written into the tables of one art slot. **Done and camera-tested:** Cross Process I = Portra 400. Tables: base gammas R/G/B (24 tables), look curve 0x7E75F2F0, saturation pair 0x7E7696B4 (stock 281/281) [V `camera-log.md`; bytes re-read] | **High.** One look per slot. Second slot: Cross Process II, records 0x7E78B49C/B4BC/B4DC [V NOTES §14.1] |
| **Per-colour HSL** (12 sectors) | Hook at 0x603b02d9 after the COLOR builder 0x603b0068 (key 11 only). The hook writes hue +18 and lightness +22 into 12 output records [X `EP7:docs/FIRMWARE_GUIDE.md:370-372`]. OM3: same hook at 0x60518615 [X `OM3:research/NOTES.md:15-17`] | No COLOR/Color Creator/profile strings in block 0 (regex search) [V]. Closest stage: **six-axis records** (R,G,B,C,M,Y: one saturation record and one hue record per mode), copied by 0x7E56D1C3. Vivid (18,7,24,0,8,8) occurs 8× in 0x7E768FBE–0x7E76940E, Pop Art I (53,79,100,56,−1,48) at 0x7E769486 [V] | 12-sector H/S/L: **not possible** (no stage). 6-axis hue+sat per slot: **medium** (data-only; units and the G/C/M axes are approximate, NOTES §16.2) |
| **Tone per look; Blacks/Whites** | H/M/S are stock COLOR settings. Blacks/Whites: hook at 0x603b14ff that remaps the 256×u16 luma LUT [X `FIRMWARE_GUIDE.md:373-374`] | The same LUT design: base gamma, then a luma look curve (0x7E56E837; offset bytes 0,0,−1,0,0 at 0x7E763F14) [V NOTES §11.1, §16.1]. The end points are table data | **High** (already part of the Portra fit) |
| **Split toning** (OM3) | Code that bends the job's R/G/B gamma copies [X `OM3:docs/DEVELOPER_NOTES.md:454`; research_notes §2.1] | Per-channel base gammas exist as **data** for Cross Process I/II [V NOTES §14] | **High** (done by data) |
| **WB shift per look** | 14 `call` sites to WB getters retargeted to a stub [X `EP7:docs/WB_PATCH.md`] | No per-look WB stage. A fixed tint can be folded into the slot's per-channel base gammas [I] | **High** inside the slot [I]; per-look WB shift as on the E-P7: low (code) |
| **Film grain on colour** | CPU grain: map the developed buffer 0x1000 through the bus window and add noise to Y, ~15 instructions/pixel [X `FIRMWARE_GUIDE.md:411-436`]. OM3 "fast grain": attach Grainy Film's texture to a COLOR job [X research_notes §2.1] | Grain only in Grainy Film (codes 74/104: `stl2ycc2` + `art_filter_06_rough_monochrome`, block-2 texture), which is monochrome [V 03 §9, 09 §2]. The ART chain has a CPU lane (ART_IMG_CF) [V 03 §9] | **Low**: a new CPU pass or a job re-key on the capture path |
| **Bloom (glow)** | Soft Focus passes (reduce to 160×120, upscale, blend in combiner 11/12) on COLOR jobs by setting job flag 0x80 [X `FIRMWARE_GUIDE.md:383-391`] | Stock **Soft Focus art effect** (`art_effect_40_soft_focus` 0x7E72169C, 6 passes) runs in the ART chain, so only on art-filter shots [V 03 §9]. The effect list for Cross Process is `00 02 04 03` (Off, Pin-Hole, White Edge, Frame) at **0x7E849E44**. I decoded the 48 bytes 0x7E849E2B–0x7E849E5A as 12 packed lists in info order 371–381, 471, and every list length matches 10b §6 [V] | **Medium**: change one byte 02→01 at 0x7E849E45 to offer Soft Focus instead of Pin-Hole on the Portra slot (same length, data only). Whether the effect then runs on code 85 is [I]: in stock, Pop Art and Pale&Light (also ISP-only) accept it. The effect strength is fixed; its blend weight was not located |
| **Clarity** | Combiner 11 with weight > 1024 = unsharp mask [X `FIRMWARE_GUIDE.md:387`] | No blend weight found in the Soft Focus passes (0x7E7218C0/0x7E721A55 load only sizes and ids) [V partial] | **Low** |
| **Tinted halation** | CPU colour pass on the reduced buffer, because combiner 11 is diagonal in YCbCr [X `FIRMWARE_GUIDE.md:385`; `EP7:docs/HALATION_RED.md`] | Nothing similar | **Low** |
| **Sharpening off / NR / vignette per profile** | Getter redirects (`sh_get`, `nr_get`, `sc_get`) [X research_notes §2.1] | Stock per-mode Sharpness; Noise Filter and Shading Comp. are global menu items [I]. What sharpening the art slot uses was not traced | **Medium** for the art slot (trace needed); not needed for normal modes |
| **True log video** | Hidden effect ids 2000/2001 with their own gamma tables 0x604f4278/0x604f4478. Effect id 2001 is selected by settings byte +925 = 2 (hook at 0x6030df3d) [X `EP7:docs/VIDEO_LOG.md:14-30`, `:162`, `:206`] | **No hidden log mode on the E-PM2.** I scored every 256-entry curve in 0x7E74E5BC–0x7E763714 (158 runs) by output per stop from −1 to −6 EV, and counted pointer references to each. No curve is flat in log space: the flattest, Light Tone 0x7E74F5BC, has 0.075–0.19 per stop, against 0.124 ± 0.008 for EP7's 2001. Only 3 runs have no reference, and all 3 are off the 512-byte stride and not log-shaped [V]. `COLORTONE_FLAT` is only the SDK enum entry between NATURAL and PORTRAIT, i.e. Muted [V string; meaning I] | Hidden mode: **not possible.** A **log-like curve written into a free art slot** (Cross Process II: base gammas + identity look curve): **medium**, data-only. Movie art codes share the record (Cross Process I 85/87 → same R/G/B records) [V NOTES §14.1]. Value is modest: 8-bit, 20 Mb/s H.264 |
| **XPan 65:24 and 21:9** | Repurpose hidden aspect ids 6/7: new validator list (record 0x604cec14), 5+ UI lists, crop tables, AF and icon fixes. 145 edits, 2,082 bytes [X `EP7:docs/ASPECT.md:13-40`, `FIRMWARE_GUIDE.md:184`] | **The same nine aspect codes.** {u16,u16} ratio table 0x7E74A518: 4:3, 3:2, 16:9, 1:1, 5:4, 7:6, 6:5, 7:5, 3:4. LV crop table 0x7E7FD1A8 has rows 1–9 (codes 5–8 = 600/560/576/640-wide crops) [V]. The choice lists hold only 1,3,2,4,9: mcon byte lists 0x7E849C30 and 0x7E84A098, u16 list 0x7EFE83CC, u32 list 0x7F00483C [V bytes; roles I]. Setting = prm 0x3081, info 271 [V 07] | **Low–medium**: the codes exist, but every crop, size and label table needs a new geometry; the still crop and JPEG-size tables are not mapped |
| **LCD colour fix** | Panel command 0xd9 [mode,R,G,B] from a 15×15×26-byte `.data` table. Stock lowers G at every step (pink cast); the patch raises G 8 % and turns the colour slider into green↔magenta [X `EP7:patches/lcd_tint/build.py:6-25`] | **Found, new to our map.** `api_disp_Disp_Set_ColorTemp` 0x7E679C3B (−7..+7 → step 0..14) → DISPLAY task case 22 → 0x7E6AF444 → (display type 1 = LCD) 0x7E6B5505: row = step×12 + `.data` **0x602AD8FC** (init image **0x7E8DDDBC**) → sent by 0x7E6B582D. At LCD open, 0x7E6B53BE reads prm 0x6739 (s8, default 0) + 7 [V]. Rows are three {reg, value} pairs, regs 0x32/0x34/0x36. Step 7 (0) = 0x80/0x80/0x80; step 0 (−7) = 0x80/0x5D/0x37; step 14 (+7) = 0x47/0x5D/0x80 [V]. Reading regs as R/G/B gains [I] | **High** for a data edit (180 bytes, LCD only). But the E-P7 cause is **absent**: the neutral row has no G cut [V]. Edit only if the user sees a cast; the table maximum is 0x80, so trim by lowering R/B [I] |
| **Recording limit** | Two imm16 operands (1740 and 7200 → 32400) in the mode→seconds routine 0x60319139 [X `EP7:patches/rec_limit/edits.json`] | Two imm16 operands in 0x7E6EDE08. Gain is small; see §2.2 | **High** to patch; gain limited (§2.2) |
| **OM-3 COLOR 1–4 profile editing, FILM 1–20 rows** | COLOR editor records (56 B, keys 0x1540–0x1543), sector settings 928–975, settings facade 0x60e57474. FILM rows are aliases on sub-setting 901 that store COLOR k [X `OM3:research/NOTES.md:30-48`; `OM3:docs/DEVELOPER_NOTES.md:512-545`] | No COLOR profile [V strings]. Picture Mode = prm 0x9481. GUI↔stored tables `gui[]` 0x7E83F70C (19) and `raw[]` 0x7E844CC0 [V 09 §1] | Editor: **not possible**. Alias rows that pick another look table: **low** (code + table moves; NOTES §14.5) |
| **Movie colour slot** (EP7) | Re-key movie Vivid to the COLOR path (one key at mapper 0x60316bfb) [X `FIRMWARE_GUIDE.md:402-403`] | Movie art filters use the same art codes and tables. Cross Process I in movie (87) takes the patched Portra tables with no extra edit [V NOTES §11.1, §14.1; on-camera I] | **High** (test only) |
| **AP Custom, Live ND** | AP-mode Vivid re-key; ND3/ND4 by averaging frames [X `EP7:README.md:54-55`] | No AP mode. Multiple Exposure (infos 268–270: 2 frames, Auto Gain) is the only frame merge [V 10a] | **Not possible** / **low** |
| **Lowest S/S** | Stock AE logic and settings 1146/1147 were hidden; a row was added [X `EP7:docs/MIN_SHUTTER.md:9-14`] | Nothing similar in 07-settings.tsv or the strings; program line is parametric [V 12 §1.1] | **Low** |
| **Vertical video** | Latch the rotation at REC_START and write the `tkhd` matrix [X `EP7:docs/VIDEO_ROTATION.md:10-21`] | Accelerometer and PER_ROTATE task exist [V 01]. The QT `moov` writer is the AVSCA library; no matrix writer traced | **Low–medium** (code) |
| **Firmware label, EXIF film name** | Label kind 4→5 text pointer; EXIF hook [X research_notes §2.2] | Equal-length string edits camera-tested (`pixel-hacking`, `label-portra`) [V camera-log] | **High** (labels) / low (EXIF) |
| **SD look loading, on-camera editor, buttons** | File API, half-press hook, heap state, facade/vtable re-points [X `FIRMWARE_GUIDE.md` §4, §8] | No file API or half-press hook traced on the E-PM2 [V research_notes §6.2] | **Low** |

**What differs in the engine.** On the E-P7 and OM-3 the job carries a key (11 COLOR, 12 MONO,
0x01xx00yy art), and a work list adds ISP passes from job flags (0x80 Soft Focus, 0x40 Star Light) on any
key [X `FIRMWARE_GUIDE.md:351-360`]. On the E-PM2 the IMG job has an op type (job+194) and a parameter
block P (art code at P+79). Effects are not job flags but modules in the ART task chain, which only art
modes reach (`rec_art_set_artmode`, `mov_art_exec`) [V 13a §3.1, 03 §9]. So every E-P7 trick that adds
passes to a normal-mode job has no E-PM2 equivalent without new code. What does transfer is the tone and
colour **table** design: base gamma, luma look curve, six-axis records and the saturation gain pair. The
E-PM2 firmware has no 12-sector stage. The E-P5, also TruePic VI, ships Color Creator, so the absence may
be firmware, not hardware [I].

### 2.2 The recording limit (the original goal)

**Their patch** [X]. On the E-P7 the routine 0x60319139 (d0 = mode, a0 = output) stores a time limit:
modes 3/6/8/9 → `mov 1740,d0`, mode 4 → `mov 7200,d0`. The patch rewrites both imm16 operands to 32400
(9 h). This is the published PEN-F pattern [X `EP7:patches/rec_limit/build_and_verify.py:4-7`;
`FISHCU:docs/features/HISTORICAL_HACKS.md:19-22`]. The routine only gives the duration. File-size and
chapter handling are separate, and **the E-P7 splits files into chapters** (`AVSCA_INF_DIV_FILESIZE`,
`DivStop`) [X `EP7:docs/VIDEO_ROTATION.md:155`]. "Camera-tested" means the remaining-time display read
~1 h after the flash [X `EP7:WORKLOG.md:187`]. No recording longer than 29 min is reported, and long
recordings are listed as not tested [X `EP7:CHANGELOG.md:86`, `:98`]. The OM-3 project did not research
the limit [X `OM3:docs/PARITY.md:86`].

**The E-PM2 mechanism** [V, bytes re-read for this report].

| Step | E-PM2 |
|---|---|
| Limit sites | 0x7E6EDEE0 `27 20 1c` = `mov 7200,a3` (MOV quality 4, VGA). 0x7E6EDF20 `27 cc 06` = `mov 1740,a3` (MOV q6/q3, AVCHD q5/q3). Block offsets 0x2CCEC0 / 0x2CCF00 |
| Arithmetic | In 0x7E6EDE08: rate (4,sp) + overhead (12,sp) (MOV 375, AVCHD 47 sectors/s); free = (8,sp) − reserve a2; cap (16,sp) = 8,388,608 sectors (4 GiB) − reserve. `divu` both, then min(a3, cap time, free time) → ×30 (`udfu01 30`) → **(40,ctx) = max frames** (0x7E6EDF53–0x7E6EDF73) |
| Per-frame stop | 0x7E6EE006: if byte 0x605B1FA2 == 1, count (96) ≥ 30 and (40) ≤ count − 15 → state 0x602ADFF4 = 5 → event 0x04070026 `RECMOVIE_TIME_LIMIT` |
| 4 GiB | Folded into (40); no separate check. **No file splitting** (`DIV_FILESIZE` is only logged) [V 04 §1.2, §2] |
| Second cap | 0x7E6D82EF: `mov 1800000,d0` (q3/q5/q6), 0x7E6D82F7: `mov 7200000,d0` (q4) → 0x607306D4 = QT `ulMaxRecTime`. Copied to 0x60730600 and passed to the AVSCA library by pointer (0x7E6D8197–0x7E6D81BD). The only absolute read is a debug print (0x7E6D918C). **Whether the library enforces it is unknown** |
| MJPEG (AVI) | Separate formula: min(2 GiB AVI time, prm 25812[idx]). prm 0x64D4 (25812) defaults 0,0,0 → 86,400 s, so only the 2 GiB AVI cap applies [V 04 §1.3, 07-settings.tsv] |
| Other `1740`/`7200` immediates | A scan of every `mov imm16,Dn/An` and `mov imm32` encoding finds no other duration site. The other hits are struct offsets or random byte matches [V] |

**Differences.** The E-P7 routine is a pure mode→seconds lookup. The E-PM2 folds the time limit, the
4 GiB file size and the free space into one frame count. The E-PM2 encoding is `mov imm16,a3` (`27`)
where the E-P7 has `mov imm16,d0` (`2c`). 32400 = 0x7E90 is below 0x8000, so it is correct whether the
form sign- or zero-extends [I ISA]. 32400 × 30 frames fits in 32 bits [V arithmetic]. The patch bytes
would be `cc 06` → `90 7e` at 0x7E6EDF21 and, optionally, `20 1c` → `90 7e` at 0x7E6EDEE1.

**What the patch would gain on the E-PM2** (MOV is 29.97 fps for every quality [V 04 §1.1]; minutes):

| Mode (q, Fine/Normal) | Stock | 1740 → 32400, library cap not enforced | If the 30-min library cap is enforced |
|---|---|---|---|
| 1080 MOV Fine (q6, 20 Mb/s) | 26.6 (4 GiB) | 26.6 (no gain) | 26.6 |
| 1080 MOV Normal (q6, 17 Mb/s) | 29.0 | 30.9 | 30.0 |
| 720 MOV Fine (q3, 13 Mb/s) | 29.0 | 39.4 | 30.0 |
| 720 MOV Normal (q3, 10 Mb/s) | 29.0 | 49.6 | 30.0 |
| VGA MOV (q4) | 103.4 (4 GiB) | 103.4: **7200 → 32400 gains nothing** | 103.4 |
| AVCHD q5 / q3 (if reachable) | 23.7 / 29.0 | 23.7 / 29.4 Fine, 34.2 Normal | n/a |
| AVI (MJPEG) | 2 GiB cap | unchanged | unchanged |

[V arithmetic from the constants; whether the encoder's real VBR output reaches 4 GiB first is open,
04 §1.2.] A recording longer than 26.6–49.6 min (4 GiB) would need file splitting, which the E-PM2
firmware does not have. That is new code in the MOV/AVSCA file path: **low** feasibility.

**Verdict.** The E-P7 patch has a direct E-PM2 counterpart, and it is the cheapest code-free edit in
this report. Its value on the E-PM2 is limited to 720p and to 1080 Normal, and it may be capped at 30
min by `ulMaxRecTime`. One test settles the cap: patch the 1740 site, record 720p Normal past 30:00, and
note where it stops. If it stops at 30:00, also patch the imm32 operand of 0x7E6D82EF (bytes 0x7E6D82F1–F4
`40 77 1b 00`), for example to 32,400,000. The thermal behaviour above 30 min is unknown [I].

## 3. Recommendations (ranked by value, safety and effort)

| # | Action | Value | Risk | Effort | Approval needed |
|---|---|---|---|---|---|
| 1 | **Recording-limit test build:** 1740 → 32400 at 0x7E6EDF21 (2 bytes). Record 720p Normal past 30 min. Then decide on `ulMaxRecTime` (4 bytes at 0x7E6D82F1). Leave the 7200 site alone (no gain) | Original project goal; up to +20 min at 720p | Low: operand-only, movie path only, same class as the E-P5/PEN-F/E-P7 edits | Hours | **Yes**: patch + flash |
| 2 | **Movie check of the flashed Portra slot:** record a clip in Cross Process I. Shows whether movie uses the patched variant column (P+99, NOTES §16.4) | Confirms a "movie look" for free; decides #4 | None | Minutes | No (camera use only) |
| 3 | **Soft Focus on the Portra slot:** 0x7E849E45 `02` → `01` (Cross Process effect list: Pin-Hole → Soft Focus). Test stills, then movie | Glow on the film look with no code | Low: same-length list edit. Unknown: whether the GUI or pipeline rejects it | Hours | **Yes** |
| 4 | **Flat/log-like movie curve in Cross Process II:** 24 base tables + identity look curve, fitted to a log2 line like EP7's 2001 (~12 % per stop) | A gradable movie profile | Low (data-only, proven class) | 1–2 days, including measuring the gamma's input headroom | **Yes** |
| 5 | **Six-axis hue/saturation for looks** (continue NOTES §16.2): probe one slot at a time | Portra fidelity (hue rotation) | Low | Days | **Yes** (probe flashes) |
| 6 | **LCD tint table** 0x7E8DDDBC (180 B), only if the user sees a cast. Also add the chain to the map (16c/16d do not list 0x7E6B5505/0x602AD8FC) | Comfort | Low (LCD only, `.data` image) | Hours | Map note: no. Flash: **yes** |
| 7 | Map additions with no flash: who reads AVSCA param+0x40; the still crop/JPEG-size tables per aspect code; the Soft Focus blend weight | Unblocks #1, XPan, clarity | None | Days | No |
| — | Not recommended now: colour grain, clarity, halation, 12-sector HSL, on-camera editor, SD looks, alias FILM rows, XPan, AP/Live ND/min S/S | — | Medium–high (new code on capture/display paths) | Weeks | — |

Running the FISHCU MN103 emulator on our selectors would verify #3–#5 without flashes. It is external
code, so it needs the user's approval (see the tooling report).

## 4. Licence notes

- caduceus-ep7 and caduceus-om3: Apache-2.0, with NOTICE files [X `EP7:NOTICE`, `OM3:NOTICE`]. Nothing
  above copies their code. The E-PM2 edits are our own bytes at our own addresses, and the ideas (operand
  patch, table re-use, list edit) are not copyrightable. If we copy a script, a table generator or a
  parameter set (for example `lcd_tint`'s +8 %), keep the Apache notice and credit the project in our
  NOTICE/README.
- `EP7:patches/aspect_fix` follows a **GPL-3.0** fork (flickering-star) [X `EP7:NOTICE`, "65:24
  aspect fixes"]. Do not copy from it into non-GPL work.
- oly_fw_analysis: mixed licence; its emulator wrapper is GPL-3.0 [X `EP7:NOTICE`]. The PEN-F
  rec-limit description is a fact, not code.
- Look recipes: the community recipes in EP7 are credited per author in `EP7:docs/LIBRARY_V1.md`. They are
  in 12-sector units and do not fit the E-PM2, so there is no reuse.
- OM's firmware: both projects ship edit lists only, never firmware [X both NOTICEs]. Our builds should
  stay on the same practice.

## 5. Open questions

1. Does the AVSCA library stop a QT recording at `ulMaxRecTime` (param+0x40 = 1,800,000)? Static: find
   the library code that reads the param block passed at 0x7E6D81B9. Dynamic: test #1.
2. Can the E-PM2 menu select AVCHD (format 2)? (04 open question 1.) This decides whether the AVCHD rows matter.
3. Does the encoder's real VBR output reach 4 GiB before the code's estimate (spec 22 min vs 26.6 min)?
4. How does the E-PM2 behave thermally past 30 min? Neither project has data for this body class.
5. LCD regs 0x32/0x34/0x36: are they R/G/B gains, and is 0x80 the maximum? Does the user see a cast?
6. Does the Soft Focus effect run with art code 85 in stills and in movie (codes 85/87)? Where is its
   blend weight?
7. How many stops of headroom above metered grey reach the base-gamma input (needed to fit a log curve, #4)?
8. Which variant column (P+99) does movie use, and does the patched Cross Process I show in clips (#2)?

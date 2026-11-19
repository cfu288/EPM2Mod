# 05 — What of the Caduceus imaging pipeline is impossible on the E-PM2? (2026-11-17)

**Question.** Which parts of the Caduceus imaging pipeline and look system cannot be done on the E-PM2, and which are only unbuilt or untested?

**Method.** Static reading of the v1.6 block 0 with `tools/fwmap.py` and `tools/disasm.py`, plus runs in the in-repo emulator (`emulator/`, on scratch copies, never in the repo). Five read-only Opus agents did the digging; the coordinator re-read these in the bytes: the enable masks of tables A and B and Muted, that Muted differs from A only in the mask, that the two orphan tables are copies of A and B, the four loader end words, the art hash at 0x7E85C45C, and the record for setting 111. Nothing was built for a camera or flashed.

Labels: **[V]** read in our bytes or run in the emulator, **[C]** camera result already in `docs/camera-log.md` or the NOTES, **[X]** stated by an external source, **[I]** inferred, **[?]** needs a camera (the probe is named).

Scratch scripts and outputs are in the session scratchpad, not in the repo. They are lost when the session ends. The addresses below are enough to redo each check.

## 1. Answer

**Nothing in the Caduceus pipeline is proven impossible on this body.** The earlier statement "no 12-sector engine, assume absent" ([01]–[04], `docs/feasibility.md`) was wrong. Five real limits remain (§2). Everything else is unbuilt code or an untested step (§3).

## 2. Real limits

| # | Limit | Label | Evidence |
|---|---|---|---|
| L1 | **No 3D lookup table** in the colour upload paths. The largest colour table written has 256 entries. | [V] for the paths read | 0x7E5501AF, 0x7E550324, 0x7E54EB1E |
| L2 | **12 regions per table**, each with a hue, chroma and luma window and three adjustments (hue shift, saturation, lightness). | [V] | table layout, builder 0x7E56E186 |
| L3 | **The 12-region stage is in pipe A only.** Stills and RAW Data Edit use pipe A. Live view and standard movie set desc+84 bit 28 and use pipe B, which has no 12-region stage. A film's hue/saturation/lightness work will not show in live view. | [V] code and emulator; [C] for RAW Data Edit (NOTES §37) | 0x7E6C9099 case 0; 0x7E562404 never calls the setter; 0x7E54F786 stops at +620 |
| L4 | **Full-frame CPU effects are slow, and impossible in movie.** About 1–2.5 s per 16 MP still at 5 instructions per pixel, 4–10 s at 50, 7.5–18 s at 100. Movie 1080p30 is about 62 Mpx/s, over ten times the CPU budget. Live view allows only sparse effects (about 66 ms for one read of a 640×480×2 frame, uncached). | [I] from a clock of 162 or 324 MHz, with one measured number [C]: 0.41–0.46 µs per uncached read | `build/logs/log2–4.jsonl`, pk_stats; the clock needs a timing probe |
| L5 | **Each look is limited to one byte of art code (256 codes), and the gamma hash holds at most 31 keys** (a full hash loops forever on a missing key). | [V] | job+79; hash 0x7E78C154 has 24 used |

Also real, but about risk and not about the pipeline: **boot-loop recovery has no hardware record on this body** (§4 of [06]).

## 3. Not limits (unbuilt, or an unsettled step)

| Item | Status |
|---|---|
| The 12-region engine itself | **Exists and is used by stock.** Every still gets a table. [V] |
| Per-film 12-region data | Data only. Film codes 70, 71, 72, 85, 94, 98, 144, 145, 156, 159 and others have no hash key, so they all fall back to **Natural's table A** (mask 0x38F, records 0–3 and 7–9, hue turns of 5–15°). [V] This is probably part of the ~2 ΔE residual of the current films ([I]). |
| Tables at a RAM address | The CPU copies each table into the registers. The engine never reads the pointer. [V] The firmware caches its choices (§4). |
| Card-loaded looks | No hard limit found. Needs a loader, banks and selector hooks (§5). |
| Free-text film names | Hook on getText 0x7ECFF3E9; works in the emulator. [V] |
| More than 12 looks | See §6. The 12 is set by three name spaces, not by storage. |
| An on-camera editor | Missing UI code, not a hardware limit. |
| Grain, halation, glow, CPU LUT | Feasible with an art-route hook (§7), at the costs in L4. |

## 4. The 12-region stage

All **[V]** unless marked. Block A is job+572; the register window is 0x9C000000 (CPU0) or 0x9E000000 (CPU1), two views of one engine [I, strong: the 18 users all pick by CPU number, the write is wrapped in one cross-CPU lock].

**Table** (3028 B, PEN-F layout): 12 records of 28 B, then 4 × (96 × u32), 6 × (96 × u16), then a 12-bit enable mask at +3024.

**Source record (28 B).** h0 hue window start, h1 hue window width (32768 = 360° [I, strong]), h2/h3 chroma window start/width, h4/h5 luma window start/width, bytes 20–25 multiplier and shift per window (width × mult >> shift = 256), **h6 hue shift, h7 saturation, h8 lightness**. Output is 12 × 24 B plus a control word at +856.

**Selection.** Hash 0x7E78C6E4 (64 slots, key = code − 8, 43 used), else a default by picture mode (0x7E56E5DC).

| Case | Table (sRGB / AdobeRGB) | Mask |
|---|---|---|
| Natural, i-Enhance, Custom, Monotone, Vivid, Portrait, **all film codes** | A 0x7E76C3C8 / B 0x7E76CF9C (Vivid and Portrait are copies) | 0x38F |
| Muted | identical to A except the mask | 0x387 |
| Code 91/93 (Gentle Sepia) | 0x7E780EF8 | 0x41 |
| Code 119/123 (Key Line) | 0x7E7826A0 | 0xC3 |
| **Code 167/168 (Cross Process II)** | 0x7E783274 | 0x1 (record 0, S −64) |
| Code 181–184 (Watercolor) | 0x7E783E48, 0x7E784A1C | 0x3C3 |
| Dramatic Tone 96/97/165/166 | off | |

**Weights.** All 32 ISO weight curves are flat 256. The ISO attenuation is never used. The ten 96-entry tables form two groups of five for records 0–5 and 6–11. Each point is (level << 8) | signed slope, with level[k+1] = level[k] + slope[k] over all 42,840 steps in the 34 tables. Each record has 7 weight curves: S, L, H, and a shared luma weight. The pairing of two of these is [I].

**Clamps.** The CPU does no clamping: it multiplies, shifts right by 8 and stores 16 bits. The hardware bit widths are **[?]**.

**Position.** After the RGB gamma, in YCbCr [I]. Its order relative to the luma look curve is **[?]**: register order points the wrong way (the luma-curve window at 0x5400 sits below the gamma window at 0x5C00, the opposite of the camera-confirmed order).

**Space.** The tables at 0x7E77B058 and 0x7E77BC2C have no references on any alias, and are byte copies of A and B: 6056 B free in segment 1 plus 576 B of orphan curve groups. Twenty scene sets point at private copies of A/B that nothing else uses; re-pointing them at A/B frees about 60 KB [I].

## 5. Card-loaded looks: findings

**RAM tables [V].** The four selectors (0x7E56B790 gamma, 0x7E56E837 curve, 0x7E56D1C3 six-axis, 0x7E56DC71 Cb/Cr) give tables to CPU code that copies or packs them. Requirements:
- **Alignment:** word loads, so 4-byte aligned. A misaligned read crashed the E-P7 and OM-3. [X]
- **Coherency:** use the uncached alias (+0x40000000). The firmware has only whole-cache routines (0x7E45DA9D, 0x7E506058, 0x7E45DA3D); CPU0 cannot invalidate CPU1's cache. Stock does the same with its own RAM tables (0x602AAFE0, 0x602AC1B4).
- **Cache keys:** gamma rebuilds on a changed pointer, the art code (P+79) or P+96; the six-axis, Cb/Cr and 12-region stages use key blocks (188 B; CPU0 0x605100C8, CPU1 0x6072C51C) with op class, art code, mode byte and P+62/80/82/90/96/99. The look curve has a fast path at 0x7E56EC4A–ECEB before its pointer compare. **Guaranteed refresh:** write bank B through the uncached alias, flip the pointers so A and B differ, then write 0 to the shared word 0xA07500B4 two or three times, about 100 ms apart. That works for stills, live view and RAW Data Edit without knowing which op is which.

**File read [V emulator, ? camera].** Wrappers post to FILECLBK through 0x7E50689F with no timeout (0x7E5C536F read is `mov 0x10005,d1` at 0x7E5C5380). Mode "r" uses a 16 KiB bounce buffer, so no alignment or 512 B rule. **fseek whence is 2 = SET, 0 = CUR, 1 = END.** The log flush task USRTEST_A read a 512 B card file correctly in the emulator (CRC equal to the host). A real read on the camera is untested.

**Trigger.** The T_GUI pattern runs in task 0x98 (CAM_APP), which is not CA_MAIN. Hook at 0x7ECDF6E4 sets a flag and starts a dormant task through OlyTaSt 0x7E449541 when `isMediaWriting()` is 0. The half-press handler is `press1stReleaseSubAppStateShootingStill` 0x7ECDF3D0; a do-nothing site is the 5-byte trace call at 0x7ECDF3E2. The emulator cannot produce S1 **[?]**.

**Persistence.** 76 settings tags nothing reads; 11 have no info id (0x6BCD, 0x83E4, 0x1872, 0x83F2, 0x8521, 0x83B4, 0x8822 and four u8 tags) and are in no reset list. For tags with an info id, **both** planes must be written, or mode load reverts the value. Camera-proven persistence is only for tag 0x8971 (peaking) and the level calibration.

**Budget.** A minimal card-loaded-looks mod needs about 600 B of code, against 2184 B + 283 B free in segment 2 for the pinned build (3267 B of code in use). Two RAM banks of 13–16 KiB each need their own place and probe (the gap below 0x7E4F9000 is unproven).

## 6. More than 12 looks

The cap of 12 is three name spaces, not storage or the 128-row list limit:
- **Art codes with no firmware compare:** 94, 98, 144, 156, 159 are used. **Code 92 is clean** (its "8 compare sites" are bounds on other loops and `\` checks) [V emulator].
- **Hidden stored values:** 111, 112, 114, 115, 118 used. 113 is usable only after rewriting its entries, which are Soft Focus's (code 69, class 3). 110, 116, 117 need their code sites neutralised first.
- **Menu entries:** all 12 art entries are films.

| Looks | How | Effort |
|---|---|---|
| 12 | pinned `films-12d` | done |
| 13 | code 92 as **type II** of an entry that already has types | one case (about 17 B) + one look's tables; no GUI work. Cheapest |
| 13 | value 113 + code 92 as a 20th list row | 9 tables + 3 hashes + a longer Picture Mode list + show-flag entry (table 0x7E826AFC, bound `cmp 19` at 0x7E703FD3) + the Shooting Menu 1 row (about 48 edits) |
| about 19–20 | codes 185–255 plus type II in all 8 typed entries | 4 stage hooks (about 142 B) + gamma bound byte 0x7E56B7AF 0xAA → 0xFF, then about 16 B per look + 6 B matrix; limited by 7 free gamma keys and about 1.2 KB of code space |
| beyond | new values 110/116/117, more rows, new pictures and texts | large |

Codes of 185 or more cannot freeze live view (every range test sends them down the stock default branch [V emulator]). They get the stock look, so each of the five stage hooks is needed to give them a film.

**Menu side.** Setting 111's callback record is 0x7E814E40 (record 25 of 250 at 0x7E814864, not 248): +16 get and +20 list-variant key are empty; +24 = 0x7E70300F, +48 = 0x7E7051E0. The +20 slot is a **list-variant key**, not a count/item/set callback. The simplest way to present N rows is to repoint record 0x7E84A388's +4/+8/+12 at a longer list, plus show-flag entries. The two runtime override slots (0x605B4C1C, 2 × 76 B) have no writer outside start-up and give at most 17 rows of existing values.

**Labels.** The only pointer-valued label kind (13) is the slideshow music name. The hook on getText 0x7ECFF3E9 (about 25 B + about 2·(n+7) B per name) gave free-text names in the emulator. Widths: Picture Mode list 336 px (20 capitals), live-control strip 408 px, Super Control Panel title about 572 px. The Super Control Panel's Picture Mode cell shows only "ARTn". The block-1 text blob has a hard cap of 117,760 B per language (`cmp 117760` at 0x7E6752EC).

**Per-look parameters, data only [V]:** base gammas (R/G/B), look curve, six-axis records, Cb/Cr gain, chroma curves, matrix, and the 12-region table. Shared: white balance, sharpening/NR. **Contrast, Sharpness, Saturation and Highlight&Shadow do not reach art filters:** 0x7E702D54 (`cmp 100` at 0x7E702D5D, `bcs` at 0x7E702D5F) writes 0 into the effective ids for setting values of 100 and up.

## 7. CPU-side effects

| Fact | Label | Evidence |
|---|---|---|
| **No film code runs the art chain for a still.** `art_IsSupportType` 0x7E71BC93 refuses every film code (and Natural) when req+0 = 1, unless an art effect is on. So no YC buffer reaches the CPU. Codes with a module (73, 74, 86, 91, 96, 104, 106, 108, 118, 151, 153, 163, 165, 169, 181, 182) do. | [V] emulator | art hash 0x7E85C45C (verified) |
| The still develop for a film code is one image-engine job (type 4) with an internal YC buffer. | [I] strong | 0x7E714A2A → img_exec, wait at 0x7E713A59, free at 0x7E713A7F |
| YC format: packed Y0 Cb Y1 Cr, 8-bit 4:2:2, 2 B per pixel. The still buffer is always the full 4608 × 3456 sensor frame (9216 B pitch, 31,850,496 B), whatever the JPEG size. | [V] from the stock red-eye code 0x7F0654BF; the still buffer's byte order [?] | 0x7E713657 |
| No lock or bus-window call is needed. Plain CPU addresses work. | [V], and the peaking loop reads and writes the job buffer [C] | |
| To add a pass for film code X: make `art_IsSupportType` return 0, add a hash entry {X−72, stub} (codes 70–72 also need the check at 0x7E72A5D3 lowered), add a module top function and a pass table `{0x0000FFFF, 0x10000, P1}, {0x7FFFFFFF, 0x80000000, fin}, {-1}`. | [V] | 0x7E72A346, 0x7E72A562 |
| CPU1 can take half the rows (kernel ids 1, 3, 4, 6 run in ART_SUB, task 0x900B, priority 4). | [V] | 0x7E72CC68 |
| Watchdog is 10 s (PER_WDT 0x7E46C29B). A pass must yield about every 2–3 s. | [V] | |
| RAW Data Edit also runs a pass in the art route. | [I] strong | 0x7E948E4F → REC_IMAGE → 0x7E70E687 |
| Cost per 16 MP still, cached alias: 5 instr/px 1–2.5 s; 15 instr/px 2–4 s; 50 instr/px 4–10 s; 100 instr/px 7.5–18 s. The uncached route has a 4.6 s memory floor and is ruled out. | [I] | needs the clock probe |
| Grain, 8–22 instr/px: about 1.5–4.5 s. Halation about 1–2.5 s with 30 KB of RAM. A CPU 3D LUT about 5–10 s and poor value. | [I] | OM-3 `xblock.s` and `halation.py` port with pitch 9216 |

## 8. Probes that need a camera

| What | Probe | Settles |
|---|---|---|
| Hue sign, saturation scale, hardware clamps | Cross Process II table 0x7E783274: record 0 covers all hue/chroma/luma, H = +2731 (30°), curves flat 0x3F00, mask 0x1; second build S = +256; third S/L = +2000. RAW Data Edit a chart. | L3, §4 |
| Live view has no 12-region stage | same shot in live view and a short clip | L3 |
| Stage vs luma curve order | record with luma 0–128, S = −1023, on a colour ramp | §4 |
| RAM table pointer works | copy a slot's ROM curve into a RAM bank, return the bank from the stub, compare RAW Data Edit pixel for pixel | §5 |
| Card read | the 175 B probe in `06` §3 | §5 |
| Half-press | log hook at 0x7ECDF3E2 | §5 |
| CPU clock and cached rate | 60 B timing probe in the kernel gap 0x7E4C93A4–0x7E4C9800 | L4 |
| Film codes 85 etc. get their own table | 3 data edits (06 §2) | §3 |
| Boot-loop recovery on hardware | owner's decision (06 §4) | recovery |

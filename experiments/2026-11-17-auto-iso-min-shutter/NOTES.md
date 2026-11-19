# Minimum shutter speed for Auto ISO, and exposure compensation in M

Date: 2026-11-17. Desk work, function harness and full-boot emulator. Nothing was flashed. No build was made.

Labels: **V** = read in the firmware bytes or run in the harness / emulator; **I** = inferred; **U** = unknown.
Values are Q8 APEX numbers: Tv 0x0600 = 1/64 s (shown as 1/60), 0x0800 = 1/250, Sv 0x0600 = ISO 200, 0x0900 = ISO 1600.

## 1. Answer

1. **The stock firmware already has the setting.** The threshold speed of Auto ISO is
   `tv_th = min(X-Sync, max(1/(2 × focal length), 1/30, Flash Slow Limit))`, with or without a flash (V in the
   harness, U on the camera). The menu row is MENU → Custom Menu → F → **# Slow Limit** (30 s to 1/250, default 1/60).
   With 1/250 there, P and A hold about 1/250 s and raise ISO up to the High Limit of ISO-Auto Set.
2. So the first step is a camera test of the pinned build (section 8). It needs no flash unit and no new firmware.
3. A row of its own ("ISO-Auto Min S/S", Auto to 1/4000, not tied to the flash) is a medium job: a 50-byte rewrite of
   one function in place (prototype V in the harness) and a menu row made as the Peaking row was. Plan in section 7.
4. Exposure compensation in M with Auto ISO: the exposure routine already uses a compensation value in M (V in the
   harness). One test in the caller sets it to 0 in M. The open part is the user interface (section 6).
5. The stabiliser setting has no part in the threshold (V: the function reads the focal length, X-Sync and Slow Limit
   only).

![Custom Menu F](results/f-rows.png) ![Slow Limit at 1/250](results/slow-limit-250.png)

## 2. Where the exposure program is

All addresses are in **segment 1** (0x7E4FE000–0x7E881000, loaded by the boot task before Usr1) (V, load map).

| Part | Address | What it does | Label |
|---|---|---|---|
| Task | TAKE_EXPOSE, id 0x46, entry 0x7E5829E8 | Half-press, release and continuous handlers call 0x7E5865B3 → 0x7E5865F2 | V calls, I task |
| Caller | 0x7E5865F2 | Builds the blocks on its stack, calls `exp_cal_still`, copies the result (56 B) to RAM 0x60515DB0 | V |
| Settings → mode block | 0x7E58669D | Fills the 44-byte mode block and the 16-byte set block with the settings read 0x7E457C75 | V |
| `exp_cal_still` | 0x7E693D00 | The still exposure: threshold, corner values, program line, results | V, ran in the harness |
| Threshold | **0x7E694001** (61 B) | `tv_th`, stored at result +46 | V, ran |
| Mode → program code | 0x7E69433B, table 0x7E7DBC94 | 3 P, 4 A, 5 S, 6 M; art and scene modes map to their own codes | V |
| Program records | 0x7E6942CE, table **0x7E7DB508** | 45 records of 42 B: 10 Av corners, 4 Sv corners, 5 Tv corners, a flag, the key | V |
| Corner resolvers | 0x7E694412 (Av), 0x7E694474 (Sv), 0x7E6944D5 (Tv) | Replace the marks in a record by real values (table below) | V |
| Auto path / manual path | 0x7E6947C1 / 0x7E69464B | P, A, S and scenes / M (program code 6 or 58) | V |
| Debug capture | 0x7E69E86F, printers 0x7E69E9EA–0x7E69EEAE | Copies inputs and results when RAM byte 0x605A7374 is 1 (`exp still on` in the debug shell). The printers give the field names used here | V |

Marks in a program record (V):

| Mark | In Av corners | In Sv corners | In Tv corners |
|---|---|---|---|
| 0x9B00 | the user's aperture | – | the user's shutter speed |
| 0x6400 | smallest aperture | **High Limit** (mode +20) | X-Sync (mode +16) |
| 0x6300 | – | **Default** (mode +22) | **tv_th** (result +46) |
| 0x9C00 | open aperture | – | – |

The P record (key 3): Sv corners `High Limit, Default, 200, 200`; Tv corners `1/4000, X-Sync, tv_th, 60 s, tv_th`.
The A record has the same Sv and Tv corners. Sport (key 8) has a fixed 1/500 in place of the first `tv_th`; key 41 has
1/250. The whole table: `experiments/2026-11-08-feature-map/sections/12-exposure-af-files.md` §1.3.

Settings that enter (V: the tags in 0x7E58669D; the values after the first start in the emulator):

| Mode block | Tag | Setting id | Menu | Value after first start |
|---|---|---|---|---|
| +16 `stb_sync` | 0x94BA (and the flash state 0x7E5E2976, the lower of the two) | 114 | F → # X-Sync. | 0x0800 = 1/250 |
| +20 `iso_limiter` | 0x949A | 112 | E → ISO-Auto Set → High Limit | 0x0900 = 1600 |
| +22 `iso_standard` | 0x9A9A | 172 | E → ISO-Auto Set → Default | 0x0600 = 200 |
| +24 `shutter_stb_limit` | **0x9ABA**, read without any flash test | 174 | F → # Slow Limit | 0x0600 = 1/60 |
| +5 `ae` | 0x8E81 or 0x80A1 | – | metering mode (I); it chooses which metered BV is used (0x7E69403E) | – |
| +6 `stb_onoff`, +7 `strobe` | 0x7E5875D3, tag 0x8171 | 16 | flash state and flash mode | – |
| set +6 `cv` | 0x80BA through 0x7E5878A6 | 2 | exposure compensation (0 in M, section 6) | 0 |
| set +2 `sv` | 0x810A | 6 | ISO (0 = Auto) | 0 |

Focal length: `exp_cal_still` takes 0x7E53840B, which returns RAM 0x60503974, the driver's `focal_length_effect`
(V). The lens driver writes it as 2 × a lens table value (0x7E5387AF) (V). So it is the 35 mm-equivalent focal
length (I). The manual says the same: "1/(lens focal length × 2)" (page 86).

## 3. What sets the threshold today

Function 0x7E694001, in words (V, and run in the harness for 8 focal lengths × 4 Slow Limits):

```
t = 256 * log2(focal_length_effect)        # 0x7E507DFD: 1/t seconds = 1/(2 x lens focal length)
t = max(t, 0x0500)                         # never slower than 1/30
tv_th = min(X-Sync, max(t, Slow Limit))    # mode +16, mode +24
```

- No table by focal length, no constant per lens, no stabiliser input.
- 17 mm lens, defaults: max(1/34, 1/30, 1/60) = **1/60**. 45 mm lens: 1/90. Above 125 mm: 1/250 (the X-Sync cap).
- A web report agrees for another body: a user lowered the Auto ISO speed with Flash Slow Limit "to 1/30 but no
  lower" (photo.net topic 451867), and an E-M5 thread says the two are tied (fredmiranda.com topic 1163652).

What the program line does with it (harness, 17 mm f/2.5 lens, High Limit 1600; `results/expcal-stock.txt`):

| Scene BV | P, Slow Limit 1/60 | P, Slow Limit 1/250 | A at f/4, Slow Limit 1/250 |
|---|---|---|---|
| 8 | 1/400 f/6.4 ISO 200 | 1/800 f/4.5 ISO 200 | 1/1000 ISO 200 |
| 5 | 1/140 f/3.8 ISO 200 | 1/285 f/2.7 ISO 200 | 1/250 ISO 400 |
| 3 | 1/70 f/2.7 ISO 200 | 1/285 f/2.7 ISO 800 | 1/250 ISO 1600 |
| 2 | 1/70 f/2.7 ISO 400 | 1/285 f/2.7 ISO 1600 | 1/128 ISO 1600 |
| 0 | 1/70 f/2.7 ISO 1600 | 1/80 f/2.5 ISO 1600 | 1/32 ISO 1600 |
| −2 | 1/20 f/2.5 ISO 1600 | 1/20 f/2.5 ISO 1600 | 1/8 ISO 1600 |

- P: shutter and aperture fall together to about `tv_th` and open aperture + 0.15 EV. Then ISO rises from Default
  to High Limit with the shutter held. Then the shutter falls.
- A: the shutter falls to `tv_th`, ISO rises to High Limit, then the shutter falls.
- With High Limit 6400 the hold lasts 2 EV longer (table 4 in the results file).
- Flash on (`stb_onoff` = 1, `strobe` = 1): the shutter is the Slow Limit and ISO stays at 200 (table 6).

The # Slow Limit list (V, emulator): 40 values, 30 s to 1/250, in 1/3 EV steps; DOWN goes to faster speeds, and
the value after 1/250 is 30 s. The stored value is the Q8 Tv (1/4 s gave 0x0200). The mode controller's list is
0x7E849B2E (record 0x7E84B5F8); the GUI list has its own 40 items at 0x7F006EE4 (descriptor 0x7F00BF6C).

## 4. PEN-F and E-M1 II (guide only)

- Both have the menu text "Lowest S/S Setting" and the help text "Choose the slowest shutter …" (V, block 1).
- Their `exp_cal_still[mode]` dump has a new field **`shutter_iso_limit`** directly after `shutter_stb_limit`, and
  the result has `flash_point_tv` where the E-PM2 has `tv_th` (V, strings of E122 v3.1 and E125 v3.7).
- So Olympus added a second limit beside the flash one and split the flash threshold from the ISO threshold (I).
  The prototype in section 5 does the same thing in 50 bytes.

### 4.1 How the PEN-F 3.1 does it (traced 2026-11-18)

Firmware `OLY_E_122_3101_0000_0000.BIN` (sha256 77398610…69f2c, in `experiments/2026-11-08-feature-map/out/firmware/`).
Same instruction set as the E-PM2 (MN103), block-0 base 0x60021020. Function database:
`python3 tools/fwmap.py --fw PENF.BIN --base 0x60021020 --out /tmp/scratch/penf build`. English texts:
`experiments/2026-11-15-feature-survey/scripts/lang_enu.py` on block 1. All addresses below are PEN-F.

UI (V, data):

- Custom Menu E → ISO-Auto Set (text 155) opens a screen with two rows: "Upper Limit / Default" (text 2874) and
  "Lowest S/S Setting" (text 2875). Row record 0x60F963D6 (kind 4, text 2875). Manual page 181 agrees.
- Value list 0x60F943D0 (a second, identical one at 0x60F94694): 59 items of 12 B. **Auto, then 60 s to 1/8000 in
  1/3 EV steps.** Auto is text 71; the speeds are ASCII strings.
- Two settings: tag **0x5351** (Auto or not) and tag **0x536A** (the speed, Q8 Tv). Filled into the mode block at
  0x605DDA19: `shutter_iso_limit = (0x5351 == 0) ? 0x7FFF : 0x536A`.

Mode block (V, debug printer 0x6112C54D): `stb_sync` +16, `iso_limiter` +22, `iso_standard` +24,
`shutter_stb_limit` +26 (tag 0x9ABA, the same tag as the E-PM2's Slow Limit), **`shutter_iso_limit` +28**.

Logic (V read; not run):

| Function | What it does |
|---|---|
| `exp_cal_still` 0x605B906E | Same frame as the E-PM2's. `flash_point_tv` (result +54) = clamp(1/(2 f), low, high) via 0x605D7106 |
| Gate 0x605BB441 | Lowest S/S is **active** only if: flash off (+5 = 0), program code 3 (P), 4 (A), 36 or 37, ISO Auto (set +2 = 0), +28 ≠ 0x7FFF, and 0x605D68E1(+36, +44) = 0 (fields +36/+44 not named; U) |
| Rounding 0x605D344E | Rounds the limit up to the exposure step grid (set +12: 85 = 1/3 EV, 128 = 1/2, 256 = 1 EV; tables 0x6065D7B0, 0x6065D830, 0x6065D888) |
| Tv corner resolver 0x605B9CD4, mark **0x5F00** | Active: the corner **is** the rounded Lowest S/S. No focal-length term, no 1/30 floor, no Slow Limit. Not active: the stock rule 0x605B97B0 |
| Stock rule 0x605B97B0 (marks 0x5E00, 0x5F00) | `max(1/(2 f), Slow Limit)`, floor 1/30, cap X-Sync (+16) **only with the flash on**, else the cap is +18 (not named; I = the fastest speed). If active, then also `max(…, Lowest S/S)` |
| 0x605B984A | When +28 = 3328 (1/8000) it calls 0x605BB42C, the body's fastest speed (I: "1/8000" means "fastest") |

What this means for the E-PM2 row (section 7):

- Olympus's limit **replaces** the focal-length rule in P and A with ISO Auto and no flash. So it can be slower than
  1/30 and slower than 1/(2 f). Our prototype only takes a max, so it can only make the hold speed faster.
- Olympus's list is 1/3 EV from 60 s; the E-PM2's top speed is 1/4000, so the same list would be Auto + 56 items.
- The X-Sync cap only with the flash on is the same change as our prototype.
- Nothing can be copied: the E-PM2 has no mark 0x5F00 and no second field. The method fits in the in-place rewrite of
  0x7E694001 if the active case returns the limit instead of the max (I; size not checked).

## 5. The smallest change

| Step | Change | State |
|---|---|---|
| A. No change | Use # Slow Limit. Up to 1/250. It is also the flash shutter speed | V harness, U camera |
| B. Own row, Auto to 1/4000 | Rewrite the tail of 0x7E694001 in place + a menu row + a dormant setting | prototype V in the harness; menu not made |
| C. # Slow Limit up to 1/4000 | Longer lists for setting 174 + the rewrite | **rejected**: with the flash on, a Slow Limit above X-Sync gives 1/1000 s with flash in the harness (stock code path, bright scene) |

Prototype of B (`scripts/th.s`, `scripts/mkproto.py` → `specs/proto-threshold-inplace.json`; 46 B of code + 4 nop in
the 50 B from 0x7E69400C; no new code area, no hook, so no load-order question):

```
tv_th = max(t, Slow Limit, 1/30 x 2^k)     # k = the byte of setting 447, 0..7: Auto, 1/60, 1/125 ... 1/4000
if stb_onoff == 1: tv_th = min(tv_th, X-Sync)
```

Harness results (`results/expcal-proto.txt`):

- k = 0: every row of the stock tables is equal, but `tv_th` of lenses above 125 mm without flash is 1/(2 f), not
  1/250 (the X-Sync cap now needs the flash). The chosen exposure in those rows is the same (V).
- k = 2 … 7 hold 1/125 … 1/4000 in P and A while ISO has room (V). Flash on with k = 5: 1/250 or slower (V).
- The byte is read at its RAM address **0x60413275** (tag 0xD791; V in the emulator on stock; I that the address is
  the same on the camera: the bank layout comes from ROM lists). A second way, with the settings read, needs about
  15 B more: put it in the dead debug capture 0x7E69E86F (191 B, segment 1).

No candidate build was made: B is useful only with its menu row, and A needs no build.

## 6. Exposure compensation in M with Auto ISO

| Fact | Label |
|---|---|
| M path 0x7E69464B with ISO Auto: `Sv = Av + Tv − (BV − cv)`, held between Default and High Limit, rounded to 1/3 EV | V read, V harness (table 5: cv −1 EV gives 1 EV less ISO, +1 EV gives 1 EV more) |
| The bias 0x7E694540 takes `cv` from the set block for every mode | V |
| **The gate:** 0x7E5878A6 fills `cv`. It calls 0x7E5870FF (1 for mode 6, 58, 90) and returns 0 for those modes. Else it reads tag 0x80BA | V |
| Patch: the 2 bytes of `bne` at 0x7E5878AF → `nop nop`. M then gets the stored compensation for the shot | I (not run) |
| The live-view exposure block reads tag 0x80BA at 0x7E69D4ED with no mode test at the read | V; what its M path does with it: U |
| In M the F button changes shutter and aperture. The manual: "Exposure compensation is not available in M mode" (pages 26 and 32) | V manual |
| Does the value set in P stay in tag 0x80BA after a change to M? One tag, MODE bank | I; U until tried |

Feasible. What it takes: the 2-byte gate (small) and a way to set the value. Two ways: (a) the value set in P or A is
kept in M (no new screen; probe first that the tag keeps it), (b) a new row with its own dormant setting, −3 to +3
(as section 7, steps 3–5). The meter bar in M would still show the deviation from the uncompensated exposure (I).
Effort: (a) 1 to 2 hours with the emulator checks; (b) half a day.

## 7. Build plan for the row "ISO-Auto Min S/S" (after the camera test of section 8)

Design (decided 2026-11-18, from §4.1): follow the PEN-F. Values Auto, 60 s to 1/4000 in 1/3 EV (56 items). Active
only with the flash off, P or A, and ISO Auto; then `tv_th` **is** the chosen speed (not a max), so it can be slower
than 1/30 and 1/(2 f). Otherwise the stock rule, with the X-Sync cap only when the flash is on. Steps 2 and 5 below
change to match: the threshold rewrite needs the set block (ISO Auto test) and a 56-item list. GitHub issue #2.

| # | Step | Effort |
|---|---|---|
| 1 | Camera test of # Slow Limit on the pinned build. If it holds 1/250, decide whether 1/500 and faster are wanted at all | 2 min, owner |
| 2 | Take `specs/proto-threshold-inplace.json` as the code spec. Check 0x60413275 on the pinned image (`scripts/tagplay.mjs … tag:d791`). Run `scripts/expcal.py --patch`, `emulator/hookcheck.py` | 30 min |
| 3 | Setting: dormant **447** (tag 0xD791, MODE bank, u8, default 0; EVF info, no reader found by the static scan; its list page is the dormant panel 608, descriptor 0x7F00BFCC). Mode-controller record 0x7E84C41C: list (0, 1) at 0x7E849EC2, length 2 → a stock byte list 0…7 (to find in segment 1), length 8. Check the reset lists as Peaking §15.2 did for 458 | 1 h |
| 4 | Menu row in group E after ISO-Auto (index 45 of the item table 0x7EBF2000): `{4, text 1498, 447, 0, order, help 1509, value list 608, 0}`. 81-row table → the dead 79-row tables of `level-adjust-row` at 0x7EBF3000–0x7EBF3780 (1,920 B, no reader since `peaking-menu`); child list grows in place at 0x7EBF2600 (+8 B, 120 B free behind it); 10 address loads, 11 page records, counts 79/80 → 80/81, row-state array 160 → 162 B, rows of group E 13 → 14 in the `.data` image. Generator: copy `experiments/2026-11-14-focus-peaking/scripts/mkspec_menu.py` | 3 h |
| 5 | List of panel 608: 8 items of 28 B. "Auto" = kind 2 with text 53. Speeds = kind 8 with numerator 1 and the denominator as a number (the stock items are `00 08 0100 fa00 …` for 1/250), so no new texts (I for 1/4000). Value → text list entry 608 (table 0x7F014614, now null). Both fit behind the new item table | 1 h |
| 6 | Texts, English first: 1498 "Built-in EVF Style" → "ISO-Auto Min S/S"; 1509 "Select the frame rate / in the built-in EVF." → "Slowest shutter speed / before ISO rises." (both free in the pinned build; 1499–1502, 1505, 1506 are taken) | 30 min |
| 7 | `builds/auto-iso-min-shutter.json` = the specs of `builds/films-12d.json` + the new spec; `.venv/bin/epm2mod make`; boot test, update-path test, screenshots of the row and list, value over three restarts, menu crawl comparison | 1 to 2 h |
| 8 | Camera test: section 8 with the new row | 5 min, owner |

Constraints (facts on 2026-11-17):

- The AE code, the mode-controller lists (0x7E849xxx) and the settings read are in segment 1. The rewrite is in
  place: no jump leaves the function.
- Kernel range 0x7E4C90CA–0x7E4C9800: 18 B free. Not needed.
- Segment-2 area 0x7EBF1090–0x7EBF3BAD: 1,104 B free in pieces of at most 177 B (`tools/freespace.py area
  0x7EBF1090`). The tables go into the dead tables instead. Debug builds: `log-probes` starts at 0x7EBF3780, so the
  new data must end before it (item table 1,298 B + items 224 B + text list 216 B = 1,738 B: fits).
- The GUI tables are read by segment-3 code after start-up only.

Risks:

- U: the row-state array grows 2 bytes again (RAM after 0x606A31B7): check as level-gauge NOTES §12.2.
- U: a reset list or Myset may write setting 447. The code masks the byte with 7, so a wrong value gives a valid speed.
- I: the direct RAM read. If the owner prefers the settings read, use the second way of section 5.
- A fast minimum (1/1000 and up) in dim light pins ISO at the High Limit; that is the setting working.

## 8. Camera test and probes

Test of the pinned build, two minutes, no flash unit on the camera. Lens at one focal length, mode P, ISO Auto.

1. MENU → Custom Menu → E → ISO-Auto Set → High Limit **6400** → OK. (Before: 1600. More room for the test.)

   ![Custom Menu E](results/e-rows.png) ![ISO-Auto Set](results/iso-auto-set.png)
2. MENU → Custom Menu → F → # Slow Limit. The row shows **1/60**. Leave it. Take 3 photos of a dim indoor scene.
3. Same row → RIGHT → press DOWN until **1/250** (the next value would be 30) → OK. Take 3 photos of the same scene.
4. Optional: 1/125, 3 photos. Then set the value you want to keep.
5. `exiftool -ShutterSpeed -ISO -FNumber -FocalLength -Flash /path/to/card/DCIM/100OLYMP/*.JPG`

| Result | Meaning |
|---|---|
| 1/60 photos: 1/60 to 1/80 s. 1/250 photos: 1/250 to 1/320 s with about 4 × the ISO | As the harness. The feature is there; write the guide |
| 1/250 photos: ISO 6400 and slower than 1/250 | The scene is too dark for the test. Use more light |
| Both sets have the same shutter speed and ISO below 6400 | The camera does not fill the mode block as read. Flash the probe build below |
| 1/60 photos slower than 1/60 with ISO below 6400 | Same |

Probes for a debug build (describe only; `logs/events.json` and the generator were not touched):

| Event | Level | arg0 | arg1 |
|---|---|---|---|
| `ae_still_in` | debug | bits 0–15 `bv` (result +0), 16–31 `tv_th` (result +46), both s16 | bits 0–15 focal length (result +28), 16–23 mode (mode +3), 24–31 `stb_onoff` (mode +6) |
| `ae_still_out` | debug | bits 0–15 `tv` (+2), 16–31 `av` (+8) | bits 0–15 `sv` (+4), 16–31 `cv` (+10) |
| `ae_still_lim` | debug | bits 0–15 Slow Limit (mode +24), 16–31 X-Sync (mode +16) | bits 0–15 High Limit (mode +20), 16–31 Default (mode +22) |

- Site: the last call of `exp_cal_still`, **0x7E693E2E** `call 0x7E69E86F,[a2],8` (7 B). There a0 = a2 = the
  argument block: +0 → mode block, +20 → result. Cost at the site: 0 B, if the routine takes the place of the body
  of 0x7E69E86F (191 B, segment 1; it returns at once on a camera because byte 0x605A7374 is 0). It must end with
  `ret [a2],8`. The routine is about 80 B (I) and calls `log_chg` 0x7E4C9514 (kernel range: allowed from segment 1),
  so that a held half-press does not fill the ring.
- One set of three records per calculation that changed: per half-press, per shot, per frame of a sequence (I).

## 9. Scripts and results

| File | Use |
|---|---|
| `scripts/expcal.py` | Runs `exp_cal_still` in the function harness: the tables, one row (`--row`), a patched block (`--patch`), the prototype table (`--proto`). The stand-ins are listed at the top of the file |
| `scripts/th.s`, `scripts/mkproto.py` | The prototype code and the generator of `specs/proto-threshold-inplace.json` |
| `scripts/tagplay.mjs` | Full-boot emulator: keys, screenshots and `tag:HEX` (stored value and RAM address of a settings tag) |
| `scripts/mkimg.py` | An image folder for the emulator from stock + prototype specs |
| `scripts/texts.py` | The items of the stock lists and English strings by pattern |
| `specs/proto-slow-limit-list.json` | Variant C, first part (6 B). In the emulator the list wraps after 40 items: the GUI has its own item count |
| `results/expcal-stock.txt`, `results/expcal-proto.txt` | Harness tables |

## 10. Unknown, and the probe for each

| Unknown | Probe |
|---|---|
| Does the camera hold the Slow Limit speed without a flash, as the harness does? | Section 8 |
| Is the focal value 2 × the lens focal length? | Set Slow Limit to 30 s and X-Sync 1/250, 45 mm lens: the hold speed should be 1/90 |
| Which calculation gives the numbers on the screen before the half-press? | `ae_still_*` records against the screen |
| Kind-8 list item with denominator 4000; reset and Myset of setting 447; RAM after the row-state array | Emulator, steps 3 to 5 of the plan |
| Compensation in M: does tag 0x80BA keep the P value in M; does live view follow | Emulator with `tagplay.mjs`; then one camera test of the 2-byte gate |

## 11. Menu row "Lowest S/S Setting" (asked for as "8. Menu row"; the number 8 is taken above)

Date: 2026-11-19. Emulator only. Not flashed. The row moved before ISO-Auto Set on 2026-11-19 (11.1); `builds/lss.json`
is made with `epm2mod make` (11.5).

![Row](results/lss-row-auto.png) ![List](results/lss-list-auto.png) ![1/15](results/lss-row-1-15.png)

### 11.1 Where the row is

MENU → Custom Menu → **E. Exp/ ▣ /ISO** → **Lowest S/S Setting** (the 6th row, after ISO Step; ISO-Auto Set is now
the 7th) → RIGHT opens the value box (▲ value ▼, the box of # Slow Limit) → UP/DOWN → OK. Values: Auto, 60, 50 … 1,
1/1.3 … 1/4000. Seconds show without a mark (as the stock # Slow Limit list). Default Auto.

**Why before ISO-Auto Set (2026-11-19).** In the first candidate the row was the 7th (after ISO-Auto Set), the last
row of the page. There the value box is moved up to fit the screen, but its white field is not: the text and the
arrows sit about 20 px above the field, and the field covers the ▼ arrow. The owner saw this on the camera; the
emulator shows the same (old `results/` screenshot of 2026-11-19, column x = 575 against `slow-limit-250.png`: the
frame lines and the field start at other offsets). Cause: the # Slow Limit page class 0x7EE01678 places the frame,
arrows and text by the room left on the screen, the field by the row (I, from the pictures; the class code was not
read). Fix: the row goes before ISO-Auto Set, so it is the 6th row. In the 6th row every pixel of the box outside the
text, in columns x = 470, 520, 575 and 660, is at the same offset from the row centre as on # Slow Limit (2nd row of
F) (V emulator, `results/lss-list-auto.png`, `lss-list-1-15.png` against `slow-limit-250.png`). ISO-Auto Set in the
7th row has no value box: it opens its own screen (`results/lss-iso-auto-set-screen.png`).

Not in the ISO-Auto Set screen (the PEN-F place), V: that screen is page 143, a page class of its own (0x7EDE6826–
0x7EDE6DD8) on panel 83 (two fields, shared with pages 126 and 453). The class code knows two fields with ISO index
tables (`cmp 21` / `cmp 22`). A third field needs a new panel layout and a rewritten class. No stock three-field
panel of that kind was found (I).

### 11.2 Interface for the exposure code

| Item | Value | Label |
|---|---|---|
| Setting | **653**, prm tag **0x9F11**, MODE bank, u8 | V (tables) |
| RAM | **0x60413225** (`tagplay.mjs … tag:9f11`, pinned image and this image) | V emulator, I camera |
| Value | index 0..55: **0 = Auto**, 1 = 60 s, 19 = 1 s, 31 = 1/15, 43 = 1/250, 55 = 1/4000 | V emulator |
| Index → Tv (Q8) | i ≥ 1: `Tv = trunc((i − 19) × 256 / 3)` (−1536 … 3072) | V for i = 4..43 (equal to the stock # Slow Limit values), I for the rest |
| Default | 0: ROM prm default 0 and full-reset default 0; the emulator's first boot holds 0 | V tables, V emulator; U the owner's camera |
| Who writes it | only the row. No constant-id access in stock; not in bank lists (Myset), restore lists or the boot reset; a full reset writes 0 | R (`../2026-11-18-look-editor/settings.md`) |

Why not 447 (the plan of section 7): 447 is Debug Log (`custom-menu-rows-2`), 449 Load Looks, 446/458 Peaking.
448 (tag 0xD7A1, panel 609) is free, but its full-reset default is 1 (60 s) and the emulator's first boot holds 1
(V): a camera would show 60 s on first use. 653 has 0 in both defaults. Panel 609 is only the list page; its
descriptor now names setting 653.

### 11.3 What the specs change

`scripts/mkspec_lss_menu.py` writes both.

- `patches/custom-menu-rows-3.json` (48 ops) takes the place of `custom-menu-rows-2` in the build. A delta on top
  cannot add a row: `epm2mod make` refuses a change to a byte that `custom-menu-rows-2` covers and keeps (byte 0xBF
  of each of the 10 item-table address loads, 81 bytes of its table, 35 of its child list; V, `spec.py`
  `_check_kept_bytes`). So the row needs a new table spec, as `custom-menu-rows-2` replaced `custom-menu-rows`.
  - item table: 83 rows at **0x7EBF1FE0** (16 B earlier, still ends at 0x7EBF2512 where `stock-films-structure`
    BK0 starts); row `{4, 1503, 653, order 11, 1504, value list 609, 0}` at index 43, before ISO-Auto Set (44);
    10 address loads.
  - child list: 84 entries in place at 0x7EE3CBF4, (609, 653) at index 43. Debug Log's value list moves 8 B to
    0x7EE3CE94 (word 0x7F014F94).
  - constants: last index 82, count 83, row-state array 166 B (RAM to 0x606A31BD; next object 0x606A32F0, R);
    rows in group E 13 → 14 (.data 0x7E8EE858). Everything else as `custom-menu-rows-2`.
  - `docs/space-superseded.tsv`: new row `custom-menu-rows-2` → `custom-menu-rows-3`.
- `patches/lss-menu.json` (7 ops, last in the build):
  - 56 items (28 B) at **0x7EBB1F4C** and the value → text list (57 × 24 B) at **0x7EBB256C**, ending 0x7EBB2AC4.
    30 … 1/250 are copies of the stock # Slow Limit records (0x7F006EE4) with the index as value; Auto is kind 2,
    text 71; 60/50/40 kind 3; 1/320 … 1/4000 kind 8.
  - descriptor 0x7F00BFDC: setting 448, 2 items → setting 653, 56 items. Value → text word 609 (0x7F014F98).
  - page registry 0x7EFE1B00: list 609 from the generic list page 0x7EDC7ECB to **0x7EE01678**, the class of
    # Slow Limit and Interval Frame (128 items). The generic page's cursor wraps after 40 items (V emulator: the 41st
    DOWN went back to Auto).
  - English texts 1503 → "Lowest S/S Setting", 1504 → "Choose the shutter speed at / which the camera raises / ISO
    in P and A." (the label and help of panel 594 "EVF Info Settings", which no menu reaches since
    `level-gauge-lvinfo-row`). Other languages show the old EVF texts.
  - No code, no hook.

### 11.4 Space (decided: the evidence rows of commit bd4f8a5 make the area pass)

The two lists need 1,568 B and 1,368 B in one piece each. After the pinned build no USABLE area has a run that size
(largest free runs 733 B in segment 3 and 408 B in segment 2; `level-adjust-row`'s dead tables at 0x7EBF3000 are
blocked by its kept bytes). The lists are in **0x7EBB1F4C–0x7EBB304C**, Bluetooth debug strings that
`experiments/2026-11-13-reclaim-space/README.md` row 2 grades A (no reference into the run). `tools/freespace.py`
gives it NEEDS-DECISION: two pointer hits that it calls unaligned data words (0x7E86D81A, 0x7E864E1F, segment-1
data) and no proven bound for the string before it (ends with its NUL at 0x7EBB1F4B). `make` fails with exactly
these two FAIL lines; every other line passes.

Decided way (a): the pointer waiver (OKAO model data) and the bound of the Bluetooth switch table (0x7EBB1F08,
11 entries) are in `docs/space-pointer-waivers.tsv` and `docs/space-bounds.tsv` since commit bd4f8a5, and the
free-space check passes. The fallback (b) was: build the value → text list in RAM by code at the first GUI state and
take `level-adjust-row` out of the build.

### 11.5 Checks

Build `builds/lss.json` (row before ISO-Auto Set, with `lss-core`), made with `uv run epm2mod make builds/lss.json`:
sha256 `2b15214bd38075c4e86e7782d37aa6ba2fca77e3aa4ad6b9a75da95f297e9f5b` (2026-11-19). The first candidate (row after
ISO-Auto Set) was `1ce469bf…aa8`.

| Check | Result |
|---|---|
| `epm2mod make` (free-space check inside) | exit 0; check PASS (0 FAIL) |
| `emulator/boot-test builds/lss.json` | exit 0, PASS |
| `emulator/update-path-test builds/lss.json` | exit 0, PASS |
| `emulator/opcheck.py builds/lss.json` | exit 0; 16 specs, 501 byte ops, 0 FAIL |
| Crawl `p-nocard-shallow`, `crawlcmp.py` against `stock-films` | exit 0; 269 screens equal outside the Custom Menu rows; rows 82 → 83: 13 lost, 14 new, all cursor positions of group E; firmware errors equal |
| The same against the first `lss` image (row after ISO-Auto Set) | exit 0; 269 equal; rows 83 / 83: 7 lost, 7 new, the cursor positions of the first page of E |
| `shotdiff.sh` D → Info Settings and its 4 sub-lists (first candidate) | 0 of 12 differ (texts 1503/1504 not shown there) |
| Value box, 6th row | aligned as # Slow Limit: columns x = 470, 520, 575, 660 equal to `slow-limit-250.png` relative to the row centre (`results/lss-list-auto.png`, `lss-list-1-15.png`, `lss-list-1-4000.png`) |
| Value list | Auto → 1/4000 in 55 DOWN, the 56th wraps to Auto (OK stores 0) |
| ISO-Auto Set, 7th row | RIGHT opens its High Limit / Default screen (`results/lss-iso-auto-set-slot7.png`, `lss-iso-auto-set-screen.png`) |
| 1/15 kept | tag 0x9F11 = 31 after OK; 31 after a restart with the RAM banks kept, then after a restart from flash only; the row shows 1/15 (`results/lss-row-after-restart.png`). A restart from flash only straight after the setting session read 0: the emulator writes the bank to flash later in the next session (I, emulator stand-in; the camera saves at power-off) |

Not checked: the help text (the emulator shows no help text for any row), other languages, the owner's stored
value of 653 (U; 0 expected).

## 12. Exposure part "lss-core" (2026-11-19)

Labels as above. All addresses E-PM2 unless marked PEN-F.

### 12.1 What the PEN-F does (V, read; and run in the PEN-F harness)

The PEN-F's program line is the E-PM2's with **one more stage**. Corner block (PEN-F): +24 fastest, +26 STOCK, +28
LOWSS, +32 slowest. 9 breakpoints in place of 8 (PEN-F 0x605BA4B9; E-PM2 0x7E6948AE):

| BP | PEN-F | E-PM2 |
|---|---|---|
| 0–4 | as the E-PM2 with hold = STOCK | c6/c8/c10 + c22/c24 − Sv − f(Sv) |
| 5' | c10 + LOWSS − c18 − f(c16) | – |
| 6' | c10 + LOWSS − c16 − f(c16) | BP5 with hold = LOWSS |
| 7', 8' | as the E-PM2's BP6, BP7 | |

- STOCK = 0x605B97B0: max(1/(2 f), Slow Limit), not slower than 1/30, then the cap: the flash's sync speed (+16) with
  the flash on, else the X-Sync setting (tag 0x94BA); then, when the limit applies, max(…, Lowest S/S).
- LOWSS = the Lowest S/S when it applies, else STOCK. Both clamped to [slowest, fastest].
- Gate 0x605BB441: flash off, mode P (3) or A (4) (also 36, 37: not on the E-PM2), ISO Auto, value not Auto, and
  0x605D68E1(+36, +44) = 0 (U; no E-PM2 counterpart found, not copied). Rounding 0x605D344E: up to the exposure step.
- Stage 5 (BP4..BP5'): the shutter falls at the base ISO c18 (the E-PM2's stage function 0x7E694DDE with c18 for c16).
  Stage 6 (BP5'..BP6'): ISO rises at LOWSS (0x7E694D34 with hold = LOWSS), then the PEN-F's own rounding
  (0x605BABE3–0x605BACE0): to the nearest 1/3 EV (85/170 grid) — up for P when stage 5 has no length — the change
  limited to ±42 by moving ISO back (1/3 EV step), and the **shutter** takes the rest.

### 12.2 The E-PM2 code (`gen/lss-core/lss.s`, generator `gen/lss-core/mkspec.py`, spec `patches/lss-core.json`)

641 B of new code in the exp debug printers 0x7E69E9EA–0x7E69EEAF (segment 1). Five edits, no RAM:

| Address | Edit |
|---|---|
| 0x7E69E9EA | NEWTH (the STOCK rule), GATE, NEWAUTO (stages 5 and 6 and the rounding); calls only segment-1 and kernel code |
| 0x7E69E858 | the shell command "exp still info" no longer calls the printers (5 nops) |
| 0x7E693D4B | `call 0x7E694001,[d2,d3,a2,a3],32` (5-byte form, as stock) |
| 0x7E694001 | the stock tv_th (one caller) becomes `jmp NEWTH; jmp NEWAUTO` (the new code is beyond d16 range) |
| 0x7E694610 | `call 0x7E694006,[d2,d3,a2,a3],76` in place of the auto path |

- The setting: 653 (tag 0x9F11, RAM byte 0x60413225, section 11). Value i = 1..55 → Q8 Tv trunc(256 (i − 19) / 3),
  the PEN-F's 1/3 EV table; 1/2 EV and 1 EV exposure steps round up as the PEN-F does.
- NEWTH finds the set block through a2 (exp_cal_still's argument list, untouched at the call). NEWAUTO gets the mode,
  set and corner blocks as arguments of the auto path.
- Mistakes found in the harness, fixed: 7-byte calls over the stock 5-byte calls; locals inside the saved registers;
  `retf` after `div` (MDR); the AM33 `mov sp,dn` (now assembled for plain MN10300).

### 12.3 Differential test (`scripts/penf_expcal.py`, `scripts/lss_compare.py`, `results/lss-compare.txt`)

The PEN-F 3.1's exposure routine runs in the E-PM2 function harness (same instruction set; its code and tables are
written at their own addresses). Stock E-PM2 against stock PEN-F: Tv and Av equal in every row, Sv differs by a
fixed 376 (the PEN-F's ISO scale). Rows: P and A, 4 focal lengths, 2 Slow Limits, 10 Lowest S/S values, 2 High
Limits, flash on/off, 3 exposure steps, BV −6 to +10.6 in 1/3 EV, manual ISO.

| Rows | Result |
|---|---|
| 15,996 | limit on: Tv, Av, Sv equal to the PEN-F's |
| 852 | limit on: the PEN-F goes faster than 1/4000 (its top speed is 1/8000); the E-PM2 output is its stock 1/4000 |
| 5,076 | limit off (Auto, flash on, manual ISO): equal to the stock E-PM2 |
| 0 | different, or changed when off |

Not the same as the PEN-F, on purpose or by the body (V in the harness):
- The PEN-F's top speed is 1/8000; at the brightest rows it goes past 1/4000, the E-PM2 cannot.
- Without the limit (Auto, flash, manual ISO, other modes) the E-PM2 keeps its own code: e.g. its ISO rounding
  (84/171 up) where the PEN-F rounds A mode to the nearest step. Those are body differences, not this feature.
- U: the PEN-F gate's fields +36/+44. The per-ISO correction f(Sv) is 0 in both harnesses (settings read stubbed);
  the code paths that use it are the PEN-F's formulas, copied (BP5' uses f(c16), as the PEN-F does).

### 12.4 Build `builds/lss.json`

`stock-films` with `custom-menu-rows-3` in place of `custom-menu-rows-2`, then `lss-menu`, `lss-core`. Checks:
free-space PASS; boot-test PASS; update-path-test PASS; hookcheck: all lss-core transfers stay in segment 1 / kernel
(the 7 FAILs are the pinned build's allowed hooks, same as stock-films); opcheck 0 FAIL. Shared files changed:
`docs/space-candidates.tsv` (2 rows), `docs/space-pointer-waivers.tsv` (3 rows), `docs/space-bounds.tsv` (1 row),
`docs/space-superseded.tsv` (1 row, by the menu work).

### 12.5 Acceptance criteria (owner's view)

| # | Criterion | How checked | State |
|---|---|---|---|
| 1 | Custom Menu E has a row Lowest S/S Setting before ISO-Auto Set; Auto by default; its value box is drawn aligned | emulator screenshots (section 11) | pass (emulator) |
| 2 | The list goes Auto, 60" … 1/4000 in 1/3 EV; the value survives power off | emulator | pass (emulator) |
| 3 | P and A, ISO Auto, no flash: ISO starts to rise at the chosen speed | harness vs PEN-F; camera | pass (harness); camera not run |
| 4 | Slower than the stock speed: P first lowers the shutter at base ISO down to it | harness vs PEN-F; camera | pass (harness); camera not run |
| 5 | Auto, flash on, manual ISO, other modes: exposure as before | harness vs stock; camera | pass (harness); camera not run |
| 6 | Nothing that works today breaks (start, update, menus, looks, peaking, level gauge, Debug Log) | boot/update tests, menu crawl; camera | pass (emulator); camera not run |

### 12.6 First camera run (build `1ce469bf…aa8`, 2026-11-19; photos PB180001–012, 17 mm f/2.8, −0.3 EV, High Limit 6400)

| Shots | Setting | Camera | Harness, same scene (`bv` −1.0) |
|---|---|---|---|
| 1–3 | P, Auto | 1/60 f/2.8 ISO 2500 | 1/65 ISO 2542 |
| 4–6 | P, 1/250 | 1/160–1/200 ISO 6400 | 1/165 ISO 6400 |
| 7–9 | P, 1/8 (planned) | 1/160 ISO 6400 | 1/8 ISO 317 |
| 10–12 | A f/5.6, 1/125 | 1/40 ISO 6400 | ISO at the High Limit: same as stock, no test |

- V: the camera reads setting 653 and the new code changes the exposure (shots 4–6 differ from stock as the harness says).
- U: shots 7–9 equal shot 4, the result with 1/250. Inferred: the value was still 1/250 (the misaligned box of this
  build); the owner was asked. Retest in the next run, in P and in A at f/2.8.
- Fault seen: the value box of the last row (slot 7) was misaligned; fixed by moving the row to slot 6 (section 11.1),
  build `2b15214b…9f5b`.

### 12.7 Second camera run (build `2b15214b…9f5b`, 2026-11-19; photos PB180001–008 of run 2)

The owner: the value box is centred (V, criterion 1). The steps meant for P were taken in A at f/5.6.

| Photos | Setting | Camera | Harness (`bv` −1.5) |
|---|---|---|---|
| 1–2 | A f/5.6, Auto | 1/30 ISO 6400 | 1/29 ISO 6400 |
| 3–6 | A f/5.6, 1/8 | 1/8 ISO 1600 | 1/7 ISO 1600 |
| 7–8 | A f/2.8, Auto | 1/80 ISO 4000 | 1/73 ISO 4017 |

- V: the slower-than-stock path works on the camera (stage 6, ISO rises at the limit), as the harness predicts.
- Not yet on the camera: P with a slower limit (stage 5, the shutter falls at base ISO), and the value after power off.

### 12.8 Third camera run (same build, P; photos PB180001–008 of run 3)

| Photos | Framing | Setting | Camera |
|---|---|---|---|
| 1–2 | dim | P, Auto | 1/60 f/2.8 ISO 4000 |
| 5–6 | dim | P, 1/8 | 1/8 f/2.8 ISO 400 |
| 3–4 | bright | P, Auto | 1/160 f/4.5 ISO 200 |
| 7–8 | bright | P, 1/8 | 1/160 f/4.5 ISO 200 |

- V: P with a slower limit works (stage 6): 3 EV slower shutter, ISO 4000 → 400.
- Bright framing: no change, as the PEN-F gives (its stage 5 starts only below the stock hold point at base ISO;
  this scene is brighter). So stage 5 is still verified in the harness only. A scene where Auto gives 1/60 at
  ISO 400–1600 would reach it.

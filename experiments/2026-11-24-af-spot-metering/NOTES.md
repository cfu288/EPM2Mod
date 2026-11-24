# Spot metering at the AF target

Date: 2026-11-24. Desk work and function harness. Nothing was flashed. No build was made.

Labels: **V** = read in the firmware bytes or run in the harness; **I** = inferred; **U** = unknown.
BVs are Q8 APEX (0x100 = 1 EV). Addresses are runtime addresses of firmware 1.6.

Question: how can Spot metering (and Spot HI / Spot SH) follow the selected AF target, as on the E-M5 II with firmware
3.0, and what is the smallest change?

## 1. Answer

1. **Feasible, with one 5-byte hook and about 125 bytes of new code.** The spot BV comes from a fixed 4×4 window of the
   18×18 BV grid. The window position is a constant in code (`movhu (266,a0),d1` at 0x7E690AB2: 266 = 2 × (7×18+7)).
   It is not a table and not a variable (V).
2. **One routine serves live view, the still exposure and Spot HI / SH.** Every path to the spot BV goes through the
   single call at 0x7E690920 (V, static call graph). HI and SH add a fixed offset to the spot BV, so they follow too (V).
3. **The selected AF target is the setting prm 0x88B2** (0..34). The exp code can read it with the settings getter
   0x7E457C75, which the exp module already calls (V for the call; I that 0x88B2 is the target the user picks).
4. **Proposed change:** retarget the call at 0x7E690920 to a stub. In single-target AF the stub moves the grid pointer
   by the cell offset of the target (a 35-byte table), then calls the stock routine. The hook is in segment 1. The
   stub goes in segment 1 too (the free part of the exp debug printers that `lss-core` reused).
5. **Main unknown:** whether the 18×18 grid covers the same field as the AF frame coordinates (U). It needs live view,
   so the emulator cannot settle it. Smaller unknowns: the value encoding of prm 0x88B2, touch AF, the digital
   tele-converter.

## 2. Where the spot BV is computed (question 1)

All of it is in the exp module (0x7E68F07C–0x7E6A935C, segment 1) (V).

| Step | Address | What it does | Label |
|---|---|---|---|
| Grid | 0x7E6904E7 | Builds the 18×18 BV grid (324 s16, struct +112) from the hardware sums, and a clipped copy (+116) | V |
| Result struct | 0x605AA3C4 (getter 0x7E6A3CDD) | +0 spot, +2 ESP, +4 centre-weighted ("bv_ave" in the dump), +6 ave2, +8 cntr, +10 arnd, +12 limit −768, +200 face count, +201 mode. A copy of 208 bytes goes to 0x605AA494 (0x7E6A3CF8), which the `exp` shell prints (0x7E69C800) | V |
| Six BVs | 0x7E6907F0 | Calls the zone builder, then spot 0x7E691007, ave 0x7E691025, cntr 0x7E69107B, arnd 0x7E6910AF, ESP 0x7E69117E | V |
| Zone builder | 0x7E6908CE | Picks tables (0x7E690928), averages the 18×18 grid by a zone map (0x7E6909A8), averages the spot window (0x7E690A62) | V |
| Spot window | 0x7E690A62 | 4×4 cells at grid rows 7–10, cols 7–10. The 4×4 map gives each cell zone 5, 4 or 0 | V, harness |
| Spot BV | 0x7E691007 | (Z5 × w0 + Z4 × w1 + 128) >> 8 | V, harness |

Tables (all in segment-1 rodata) (V, harness):

| Variant | When | 4×4 map | Spot weights w0, w1 | 18×18 zone map |
|---|---|---|---|---|
| A | normally | 0x7E7DA8E8: centre 2×2 = zone 5, the 8 edge cells = zone 4, corners unused | 0x7E7DA8A8: 230, 26 | 0x7E7DA620 |
| B | struct byte (6) = 1 and halfword (8) = 200 | 0x7E7DA8F8: centre 2×2 only | 0x7E7DA8C8: 256, 0 | 0x7E7DA764 (smaller) |

So in variant A the spot is 90 % the centre 2×2 cells (rows 8–9, cols 8–9) and 10 % the ring of 8 around them (V,
harness: `results/spotgrid.txt`). 12 of 324 cells is about 3.7 % of the grid, the 2×2 core about 1.2 % (I that the
grid spans the whole frame, section 4). Variant B is probably the 2× digital tele-converter (I).

Live view and still: the zone builder has one caller chain, 0x7E6A3E8E → 0x7E6907F0 → 0x7E6908CE → 0x7E690A62 (V; the
xrefs show no pointer to these functions). 0x7E6A3E8E is called from the live-view loop (0x7E6A521C → 0x7E6A35B7 →
0x7E6A39C8), from the pre-still calculation (`exp_pre_still_cal_result` 0x7E6A5B70 → 0x7E6A35B7), from 0x7E6A4730 and
from 0x7E6A7EB2 (V). The still result block that `exp_cal_still[bv]` prints has the layout of the result struct (I: a
copy). So the still exposure uses the same spot BV (I; a mirrorless body meters on the sensor frames).

## 3. Metering mode and Spot HI / SH (question 2)

| Part | Address | Finding | Label |
|---|---|---|---|
| Settings | prm 0x80A1 (metering, default 2), prm 0x9699 (HI/SH, s8) | 0x80A1: 0 = centre-weighted, 1 = spot, 2 = ESP. 0x9699: 1 = HI, 2 = SH. Read from the Exif writer 0x7E587300 (MeteringMode 2/3/5, +0x200 HI, +0x400 SH) | V |
| Packet to exp | 0x7E585D03 (TAKE_EXPOSE) | +4 = HI/SH (0x9699), +6 = metering (0x80A1); in a scene mode prm 0x97A9 and 0x8E81 instead | V |
| Effective mode | 0x7E6A355A | 3 (ave2) when command flag bit 2 is set; 2 (ESP) when 0x7E6A1819(0) = 1; 0 when packet +5 = 3; else the user's mode | V code, I meaning |
| BV pick | 0x7E6A340C (via 0x7E6A344C) | 0 → +4, 1 → +0 spot, 2 → +2 ESP, 3 → +6 ave2 | V |
| HI / SH offset | 0x7E6971B4, called by 0x7E69710F only when the metering byte = 1 (spot) | HI +537 (+2.1 EV), SH −771 (−3.0 EV) | V constants, I units |

HI and SH use the spot BV with an offset. When the spot window moves, they move with it (I, follows from the code).

## 4. Where the AF target is (question 3)

| Part | Address | Finding | Label |
|---|---|---|---|
| AF target mode | prm 0x84D1 | 0 → af_type spot (single target), 2 → multi (all targets) (0x7E593187) | V code, I meaning |
| Selected target | prm 0x88B2 (u16, MODE class, 13 GUI reads, 4 GUI writes) | 0x7E5932AB (`mode2fcs`) maps it to an AF area: values ≥ 35 or unmapped give area 17 (the centre) | V |
| Index order | ROM 0x7E79167C, init 0x7E5880D9 | The prm value is column-major (k = col × 5 + row); the AF area is row-major (row × 7 + col). Centre: k = 17 = area 17 | V |
| Area centres | 0x7E7A1C60 (read by 0x7E5E7EAE) | 35 × (x, y) in a 640×480 frame: x = 103 + 72 × col, y = 95 + 72 × row; 7 columns, 5 rows | V |
| Geometry | 0x7E593894 | For single target, x, y, w, h of the target from prm 0x88B2 (`point:spot/group`); for the magnified "special" frame, x, y in −100..+100 from the TAKE_FOCUS globals +58 / +60 | V |
| Touch AF | – | Not traced. Whether a touch writes prm 0x88B2 or the special frame is unknown | U |
| Default | 07-settings.tsv | The ROM default of 0x88B2 is 0 (k = 0 is the top-left target) | V value, U why |

The `[exp]:apical af_target` dump (0x7E69CDA8, called from 0x7E6A3A9F) prints a u32 `af_target`, 35 `area_status`
bytes and `mode_af_area` from a 68-byte buffer at 0x605AB160 (pointer 0x605AB154). No code writes that buffer by its
address. The exp post step passes the block 0x605AB150 to a callback that TAKE_EXPOSE put in the command
(0x7E6A6249) (V). How the buffer gets filled was not settled, and the TAKE callbacks read it in a way that does not
fit a 68-byte buffer (U). It feeds the Apical shadow code, not the spot meter (V: its only reader is 0x7E6A3A9F →
0x7E692613). The proposal does not use it.

Mapping a target to the grid (I: assumes the 18×18 grid spans the same field as the 640×480 AF frame): window top-left
c0 = round(x × 18 / 640) − 2 = 1, 3, 5, 7, 9, 11, 13 by column; r0 = round(y × 18 / 480) − 2 = 2, 4, 7, 10, 12 by row.
Every window stays inside the grid. The cell delta to the stock window is (r0 − 7) × 18 + (c0 − 7), −96 … +96, so it
fits a signed byte. The harness ran the stock 0x7E690A62 with the grid pointer moved by each of the 35 deltas: each
window reads the cells under its target (V, harness: `results/spotgrid.txt`).

## 5. Proposed change (question 4)

Ranked by what a mistake costs (cheapest first):

| Option | Hook | Code | Cost of a mistake | Unknowns |
|---|---|---|---|---|
| A (proposed) | 5 bytes at 0x7E690920 (segment 1): `call 0x7E690A62,[d2,d3,a2,a3],56` (`cd 42 01 f0 38`) → `jmp STUB` (`dc` + rel32) | ≈ 90 B code + 35 B table in segment 1 (the free part of the exp debug printers at 0x7E69E9EA, after the 641 B of `lss-core`; to be confirmed with `tools/freespace.py`) | A fault shows at the first live view, not at start-up: the hooked code runs only during metering (I) | U1–U3 below |
| B | none in flash for segment 1: a segment-3 routine rewrites the 16-bit displacement 266 of 0x7E690AB2 in RAM when the AF target changes | ≈ 60 B in segment 3, plus a trigger | Low at start-up | Is segment-1 code writable at run time, and does the instruction cache see the write? (U, needs its own probe) |

Option A is smaller and has no new unknown. Segment 1 for both hook and stub follows the rule in
`docs/dev/feasibility.md` ("A hook in the kernel or in segment 1 must jump only to code in the kernel or in segment 1").

Stub of option A (sketch, not assembled). It runs in the frame of 0x7E6908CE, which returns right after the call, so
d3, a2 and a3 are free; that function's own `ret [d3,a2,a3],20` restores them:

```
STUB:   mov  d0,d3                 ; out: spot zones
        mov  a0,a2                 ; clipped 18x18 grid
        mov  a1,a3                 ; 4x4 map
        mov  0x7E7DA8F8,d0         ; variant B (tele-converter, I): keep the centre
        cmp  d0,a3
        beq  go
        mov  0x84D1,d0 ; mov 0,a0 ; clr d1 ; call 0x7E457C75,[d2,d3],12   ; AF target mode
        cmp  0,d0
        bne  go                    ; not single target: keep the centre
        mov  0x88B2,d0 ; mov 0,a0 ; clr d1 ; call 0x7E457C75,[d2,d3],12   ; selected target k
        exthu d0
        cmp  35,d0
        bcc  go                    ; k >= 35: keep the centre
        mov  TABLE,a0
        movbu (d0,a0),d1
        extb d1
        add  d1,d1                 ; cells -> bytes
        add  d1,a2
go:     mov  d3,d0 ; mov a2,a0 ; mov a3,a1
        call 0x7E690A62,[d2,d3,a2,a3],56
        ret  [d3,a2,a3],20
TABLE:  35 x s8, indexed by k (column-major): (r0-7)*18 + (c0-7) of area row*7+col where k = col*5+row
```

The getter saves only d2 and d3 (its call form), so a2 and a3 survive it (I from the register list). The getter
runs twice per metering frame (I: cheap). Live view, the still exposure, Spot, Spot HI and Spot SH share the one
hook (section 2). ESP and centre-weighted do not change. Exif keeps MeteringMode Spot.

Open design points for the owner (not decided here): always on, or a menu row as on the E-M5 II; behaviour with face
priority (the stub follows prm 0x88B2, not the face).

## 6. Risks

- **U1, field alignment.** If the 18×18 grid does not span the 640×480 AF frame, the window lands beside the target.
  The AE area that exp sends to the camera core (`CAM_AE_SETTING` area.hs/hw/hdiv/vs/vw/vdiv, 0x7E68F9BA) decides it.
  Sensor modes differ (`ae_param HSHR/HS/HS3D/MSSC/LSSC/CLIPx4…/STILL`, 0x7E69A522), so it may differ by mode.
- **U2, prm 0x88B2.** Its value encoding is read from the ROM order table, but its ROM default is 0 and no camera
  reading exists. If the GUI stores something else, the table index is wrong.
- **U3, touch AF and the magnified frame.** If they use the special frame (x, y in −100..+100), the stub keeps the
  last single target. Handling them needs a second branch (≈ 30 B).
- Variant B is skipped on the guess that it is the digital tele-converter.
- Segment-1 code: a fault would appear in live view, which the update path does not start (I). Run `hookcheck.py`,
  `boot-test` and `update-path-test` before a build is offered.

## 7. Proposed first probe (question 5)

Before any flash, in this order:

1. **Emulator, full boot (settles U2):** go to the AF target selection screen, move the target to the four corners
   and the centre, and record each prm 0x88B2 write (breakpoint on the setter 0x7E457CED with tag 0x88B2) and the
   value of prm 0x84D1. Expected: k = col × 5 + row; centre 17. Take the menu path from the camera manual.
2. **Function harness (stub correctness):** run the assembled stub in place of 0x7E690A62 with a stub getter
   for prm 0x84D1 and 0x88B2, for all 35 k, for mode 2 and for the variant-B map, against the model in
   `scripts/spotgrid.py`.
3. **Harness or static (tries U1 without the camera):** run the AE area calculation (0x7E698978 / 0x7E69917F, the
   `calc_cs hs/vs/hw/vw` values) for the live-view sensor mode, and compare the area with the live-view image size.

If step 3 does not settle U1, the camera run is the feature build with two Debug Log events (`docs/reference/logging.md`):
the AE area at each `CAM_AE_SETTING` (0x7E68F9BA), and once a second k, the cell delta and bv_spot. Camera check:
Spot metering, a dark room with one small lamp; put the AF target on the lamp and beside it. Expected: the exposure
drops by several EV only when the target is on the lamp, and the log shows the window that contains the lamp.

## Files

- `scripts/spotgrid.py`: runs the stock zone builder and spot routine in the function harness; maps the spot window
  cell by cell for variants A and B, and checks the moved window for all 35 targets. `uv run python
  experiments/2026-11-24-af-spot-metering/scripts/spotgrid.py` (exit status 0 = PASS).
- `results/spotgrid.txt`: its output.

## Donor study

- [donor.md](donor.md): how the E-M5 II 4.1 and the PEN-F 3.1 move the same 4×4 spot window to the AF target, and what the E-PM2 version should copy.

## Decision (owner, 2026-11-24)

Mimic the E-M5 II: a "[•] Spot Metering" menu row with one check box each for Spot, Spot HI and Spot SH, all off by
default. A checked variant meters at the selected AF target. Faces are ignored, as in the donor (donor.md).

## Acceptance criteria

Each is checked where named. A build that fails one is not pinned.

1. Custom Menu E has a row "[•] Spot Metering". It opens Spot, Spot HI and Spot SH, each with a check box. All start
   off, and the choices are kept after power-off. Texts are English in every menu language. (Emulator screenshots;
   camera.)
2. With a checked Spot variant and single-target AF, the exposure follows the selected AF target, in live view and in
   the saved photo: a target on a bright area gives a darker picture than a target on a dark area. (Camera.)
3. Unchecked variant, ESP, centre-weighted, or the all-targets AF mode: metering is stock. (Emulator harness; camera.)
4. Face priority on: the spot stays on the selected AF target. (Camera.)
5. Start-up, the update path and the other EPM2Mod features are unchanged. (hookcheck, boot-test, update-path-test;
   camera.)

## Emulator findings (2026-11-24)

Full-boot emulator (stock image and the pinned build, English P-mode state from `emulator/mkstate`), function harness
and static reading. Nothing was flashed. No firmware was made. Labels as above. The screens are the firmware's own,
as the emulator draws them: LEFT in shooting opens the AF target screen, OK opens Live Control.

### E1. The selected AF target (question 1)

| Finding | Label |
|---|---|
| After a reset prm 0x88B2 holds **17, the centre**. On an empty settings store the boot writes 0x84D1 = 2 and 0x88B2 = 17 through Set_CameraInfo (from 0x7E706905 and 0x7E6800D7), over the ROM default 0. A boot with a saved store writes neither | V emulator |
| The AF target screen writes info 85 → prm 0x88B2 through Set_CameraInfo (0x7E6FEA37 ← 0x7E6FED15 ← 0x7E6FF3ED) at every move, and info 40 → prm 0x84D1 (← 0x7E6FF507) when the AF target mode changes | V emulator |
| **k = col × 5 + row** (col 0..6 left to right, row 0..4 top to bottom). Seen: RIGHT from all targets → 2 (left middle), UP → 1 → 0, LEFT from all targets → 32, LEFT → 27 → 22 → 17, DOWN from 32 → 33 → 34 (bottom right). The screenshots (not kept) showed the frame at each place. `scripts/af_probe.mjs` logs the stores | V emulator |
| prm 0x84D1: **2 = all targets**, **0 = single target**. UP from the top row returns to all targets (0x84D1 = 2, 0x88B2 kept) | V emulator |
| Small target (AF target screen → INFO → DOWN, `[•]s`) stores neither tag: the target keeps its k and its centre | V emulator (no store), I (same centre) |
| Touch AF: `startTouchTargetAf` 0x7ECDD97D passes the touch point (x, y) to OlyApi slot 220 → `touchTargetAf` 0x7E98A0B9 → an AF lock with reason TOUCH_TARGET_AF (`startAFLock` 0x7EB8E7E2 → `api_rec_AEAF_Lock` 0x7E689D21). This path has no Set_CameraInfo(85). Whether a touch writes 0x88B2 elsewhere or sets a free frame is not traced. The emulator has no touch panel | V for the calls read, **U** for the result |

### E2. prm 0x6761 (question 2)

| Live Control → AF mode | prm 0xC021 | prm 0x6761 |
|---|---|---|
| S-AF | 0 | 0 |
| C-AF | 2 | 0 |
| MF | 1 | 0 |
| S-AF+MF | 0 | 0 |
| C-AF+TR | 2 | **1** |

prm 0x6761 is **1 only in C-AF+TR**. Every other AF mode writes 0 (V emulator). Stock code tests tracking as
info 25 (0xC021) = 2 and info 676 (0x6761) = 1 (0x7E986724 `getTouchTrackingAfl`, 0x7EB8E917, 0x7EA881A2) (V). So it
is the donor's `af_tracking`, and the stub keeps the centre when it is not 0, as the donor does.

The same run, metering in Live Control: ESP → 0x80A1 = 2; centre-weighted → 0; Spot → 1 with 0x9699 = 0; Spot HI →
1, 1; Spot SH → 1, 2 (V emulator; agrees with section 3).

### E3. The menu row (question 3)

How rows are added (V, `gen/lss-menu/mkspec.py`, `../2026-11-17-auto-iso-min-shutter/NOTES.md` section 11,
`gen/stock-films/loader.py`):

- A Custom Menu row is 16 B `{u16 group, u16 label, u32 setting (info id; 2000 = opens a page), u16 order, u16 help,
  u16 panel or value list, u16 flag}` plus a child-list entry `(page, setting)`. A fifth added row needs
  **custom-menu-rows-4** in place of -3 (a delta cannot grow -3's table): 84 rows 16 B earlier at 0x7EBF1FD0
  (0x7EBF1F4F–0x7EBF1FDF is covered by no pinned spec, reclaimed `sdk` strings; free-space check not run, U), the child
  list grown in place with Debug Log's value list moved to 0x7EE3CE9C, last index 83, count 84, clear 168 B, group E
  14 → 15. The row-state array becomes 168 B, to 0x606A31BF (next object 0x606A32F0).
- Texts: the English text in block 1, plus the film loader's text table (`card-looks-8`, from `gen/stock-films/`)
  for "the same text in every menu language". A new text there means a new loader version; `gen/log-menu/` reads the
  loader's `_symbols` and runs after it (I).

**The E-PM2 has no stock check-box page** (V: LV-Info, ▶ Info, ▣ Settings, Picture Mode Settings, Control Settings
and Image Stabilizer all show On/Off rows, `results/menu-stock-lists.png`). They use the sub-item page class (creator
0x7EDE1E3D, vtable 0x7EFF67F0). Its rows come from the sub-item table 0x7EFEF4FC (`{panel, title, setting, 2, 7, 1,
row text, 0}`); the count is the number of records of the panel. Each row stores its own u8 setting (LV-Info: tag
0x9161 bytes 0–2) and opens a generic list page (0x7EDC7ECB) as its picker; the picker writes its descriptor's setting
(V emulator, `results/menu-lvinfo-toggle.png`, `menu-probe-shared-picker.png`, `menu-tags.txt`).

**Prototype, data only (V emulator, `results/menu-probe-spot-page.png`, `scripts/menu_probe_image.py spot-page`):**
page 594 ("EVF Info Settings", which no menu reaches since `level-gauge-lvinfo-row`, already on this class) with title
169 "Metering" and three rows with the stock texts 171 "Spot", 106 "Spot Hilight", 107 "Spot Shadow", settings 606 /
660 / 621, pickers on the unused lists 198 / 584 / 659 (only their descriptors change), a new child list at
0x7EBF1F50. 15 data ops. The page draws; each row writes only its own tag; the values survive a restart from the
saved state. The prototype reached the page through AF Mode's row; the build uses a new row in E instead.

Real check boxes would need new draw and OK-key code on the sub-item class (a vtable hook, estimated a few hundred
bytes) and a check glyph, which was not found (U). That is new GUI code in a class no build has patched.

### E4. Settings storage (question 4)

- Bits in 0x9681 do not fit: the mode controller's value list for info 606 is {1, 0} (V, menu agent), so the menu
  cannot store 2..7 (I).
- **One u8 setting per variant:** Spot = info 606 (prm 0x9681), Spot HI = info 660 (0x9F91), Spot SH = info 621
  (0x9821). All are MODE u8 with ROM and full-reset default 0 and no stock reference except the Exif one below (V).
  Kept after a restart from the saved state (V emulator). An empty store's boot writes 0x9681 = 0 (V emulator).
- **Exif side effect of 0x9681 (V, 0x7E587300–0x7E58736D):** the writer maps 0x80A1 2 → 5 (ESP), 0 → 2, 1 → 3, adds
  0x200 / 0x400 for HI / SH, and only when the result is 5 (ESP) and 0x9681 = 1 it adds 0x100. The full value goes to
  record +2984, the low byte to +2376. So with the Spot row On, an **ESP** photo records 0x105 at +2984; the standard
  Exif MeteringMode (low byte) stays 5. ExifTool names Olympus MakerNote MeteringMode 261 (0x105) "Pattern+AF" (R, from
  memory; check before quoting). It is a wrong label in one MakerNote field, no effect on exposure (I: no other reader
  of 0x9681). (The menu agent's note that 5 is "plain Spot" is wrong: 5 is ESP.)
- **Avoidable at no code cost:** give Spot another free MODE u8 setting with default 0, and leave 0x9681 at 0. The
  stub takes its three tags from a table, so this is a data choice. Candidates are in `07-settings.tsv` (MODE, u8,
  default 0, no reference); the chosen one needs the same emulator row test as 660 and 621.

### E5. Grid field against the AF frame (question 5, U1)

Harness runs of the real AE set-up (`scripts/field_aeparam.py`, `results/field-aeparam.txt`) and AF window set-up
(`scripts/field_afarea.py`, `results/field-afarea.txt`):

- Live view (HS / HSSC, the default): readout 1548×700; the AE grid starts at (82, 36), 18×18 blocks of 80 × 36 px
  (V). The AF window of each of the 35 areas is at x × 1536/640 + 34, y × 691/480 + 15 in the same readout (V, all 35
  matched). The AE record's own origin gives the same 34/15 (V numbers), so both use one coordinate system (I, strong).
- **The grid covers x 20.0..620.0, y 14.6..464.7 of the 640×480 AF frame (93.75 %, centred), not all of it.** Cell
  pitch 33.33 × 25.0. Window top-left: c0 = round((x − 20)/33.33) − 2 = 0, 3, 5, 7, 9, 11, 13 by column; r0 =
  round((y − 14.6)/25.0) − 2 = 1, 4, 7, 10, 13 by row. Section 4's table (c0 = 1, r0 = 2 and 12 at the edges) was up to
  one cell off at the corners. Deltas −115..+114, inside a signed byte; every window stays inside the grid; the centre
  is unchanged. Label: **I (strong)** — the numbers are V, live view itself does not run in the emulator.
- MSSC uses the same field. LSSC (240 fps) covers y 41.9..443.7 (V numbers; whether it meters, U). **HSHR (movie) is
  18 × 14** (`mov 14` at 0x7E698685) while the grid builder still loops 324 cells (V): a moved window there may read
  rows that do not exist. **CLIP modes** (index 0..4) cover a small crop of the readout (V numbers), so a moved window
  would land beside the target in magnified views (I).

### E6. The stub in the harness

`scripts/spot.s`, run by `scripts/spot_stub.py` (exit status 0 = PASS, `results/spot-stub.txt`): the hook `jmp STUB`
at 0x7E690920 and **184 B** at **0x7E69ED8B–0x7E69EE43** (the free end of the exp debug printers after `lss-core` and
`pana-ring-probe`; `tools/freespace.py area` gives 292 B free, USABLE-CODE, segment 1), run inside the stock zone
builder 0x7E6908CE with the settings getter answered by the harness. Order: 0x80A1 = 1, HI/SH value 0..2, that
variant's setting ≠ 0, 0x84D1 = 0, 0x6761 = 0, 0x88B2 < 35, map A; then the grid pointer moves by the table (E5).

- All 35 k × Spot / HI / SH: the spot zones equal the stock window moved to that target (V harness).
- The stock centre in each other case: all off; another variant's setting on; HI/SH value 3; ESP; centre-weighted;
  all targets; C-AF+TR; k = 35 and 0xFFFF; map B (asks no setting) (V harness).
- ESP, average, centre and surround BVs do not read the spot zones (+12, +14): 0x7E691025 reads +0..+8, 0x7E69107B
  +0..+4, 0x7E6910AF +6, +8, and ESP 0x7E6910CE works on the grid with its own table (V static). The move changes only
  the spot BV.

### E7. Build plan

Base: the pinned build `peaking-mf`. One build, `spot-af`, with:

1. **Pre-build step (desk/harness, ≈ 10 B more stub):** find where exp keeps the current sensor mode (the d0 that
   0x7E6900AB passes to 0x7E68FF9B) and keep the centre unless it is HS / HSSC / MSSC. This covers movie (HSHR 18 × 14)
   and the CLIP crops (E5). Add these cases to `spot_stub.py`.
2. **`spot-core`** (generator `gen/spot-core/`, from `scripts/spot.s` and `spot_stub.py`): 5 B at 0x7E690920
   `cd 42 01 f0 38` → `jmp STUB`; the stub, GETP and the 35 B table (E5 values) and 6 B tag table at 0x7E69ED8B.
   Segment 1 to segment 1 and the kernel getter only. Not first code: `lss-core` runs in this area.
3. **`custom-menu-rows-4`** (extend `gen/lss-menu/`), in place of -3: the E row `{4, LABEL, 2000, order, HELP, 594,
   flag}` with child (594, check setting), 84 rows at 0x7EBF1FD0, constants as E3.
4. **`spot-menu`** (data only): the prototype's page 594 ops without the AF Mode shortcut; Spot on the setting chosen
   in E4, HI 660, SH 621; title and three row texts as the prototype; the label and help in English block 1.
5. **Texts in every language:** the new label and help in the film loader's text table: a new loader version and a new
   `log-menu` version (both generated; `log-menu` runs last). Spare text ids: 1509 and 1510 are candidates (U).
6. Optional Debug Log events (one per second: k, cell delta, spot BV; the AE area at each `CAM_AE_SETTING`) only if
   the owner wants V for U1 and touch AF from the first flash. They add a log-dictionary change.

Checks before the build is offered (AGENTS.md rule 7):

- `uv run epm2mod make spot-af` (free-space check inside) and `uv run python tools/checks.py data/builds/spot-af.json`.
- `emulator/hookcheck.py data/specs/spot-core.json` exit 0.
- `emulator/boot-test data/builds/spot-af.json` and `emulator/update-path-test data/builds/spot-af.json`, exit 0.
- Crawl `p-nocard-shallow` of `spot-af` and `peaking-mf`, `crawlcmp.py`: only group E and the new page differ.
- `shotdiff.sh` against `peaking-mf`: Custom Menu E (the new row), the new page (three rows, On/Off, pickers), D →
  Info Settings and its sub-lists (unchanged); the row in iAUTO and ART (greyed or not, as the check setting says).
- Emulator settings test: each row On/Off writes only its tag; kept after a restart; an empty store gives all 0.
- `spot_stub.py` PASS on the bytes of the built image (assemble once, compare with the spec).

Camera test (owner): Spot metering, single target, a dark room with one small lamp. Target on the lamp, then beside
it, at the centre and at a corner (bottom left, k = 4, where the old and new tables differ by a row). Expected with
the Spot row On: the exposure drops by several EV only when the target is on the lamp, in live view and in the photo;
with it Off, only the centre target reacts. Then HI and SH, ESP, all targets, C-AF+TR, face priority, a touch on the
screen (touch AF, U), movie.

### E8. Still unknown

- **Check boxes:** the owner's decision asks for check boxes; the stock GUI has On/Off rows only (E3). Real check
  boxes need new GUI code and a glyph (U). The help text of the donor ("For the ✓ selected items …") must be
  reworded for On/Off rows.
- The row's label glyph: the donor's `@A000@` is the Custom Menu icon on the E-PM2 (I); an AF-target glyph in the
  E-PM2 font was not looked for (U).
- Touch AF (E1), the sensor-mode source for movie and magnified views (E7 step 1), the 2× tele-converter (map B keeps
  the centre), the field match on the camera (E5, I strong), whether mode presets overwrite the three settings (U),
  which check setting greys the row in iAUTO / ART (U).

## Build spot-af (2026-11-24)

Emulator and harness only. Nothing was flashed. Labels as above.

### What was built

`data/builds/spot-af.json`: the pinned `peaking-mf` with `custom-menu-rows-4` in place of `-3`, `card-looks-9` in
place of `-8`, and `spot-core` and `spot-menu` at the end. Made with `uv run epm2mod make spot-af` (free-space check
inside): **sha256 `64421e1bd2befd251bfd7280391c4975259456023645b15318f5cbbfb67f0e01`**, `build/spot-af.BIN`.

| Spec | Generator | What |
|---|---|---|
| `spot-core` | `gen/spot-core/mkspec.py`, `spot.s` | 5 B at 0x7E690920: `call 0x7E690A62,[d2,d3,a2,a3],56` → `jmp STUB`; 212 B at 0x7E69ED8B–0x7E69EE5F (exp debug printers, after `lss-core`; 80 B left to 0x7E69EEAF) |
| `custom-menu-rows-4` | `gen/spot-menu/mkspec.py` | `-3` with the row `{4, 1494, 2000, order 12, 1509, 0, 1}` at index 48 (after AEL Metering; AF Mode's form), child `(594, 1)`; 84 rows at 0x7EBF1FD0; child list 85 entries in place; Debug Log's value list to 0x7EE3CE9C; last index 83, count 84, row-state array 168 B; group E 14 → 15 |
| `spot-menu` | `gen/spot-menu/mkspec.py` | Page 594 "Spot Metering": rows Spot / Spot Hilight / Spot Shadow (stock texts 171, 106, 107) on settings 593 / 660 / 621; pickers 198 / 584 / 659 with list 200's Off/On items; value records of 446 / 448 / 449 re-keyed; page child list at 0x7EE3CEE4 (segment 3, after Debug Log's value list) |
| `card-looks-9` | `gen/stock-films/loader.py` (changed: it now writes `-9`) | `-8` with two more texts: 1494 "Spot Metering", 1509 "Spot modes set to On meter / at the selected AF target / in single-target AF." Labels (`_symbols`) unchanged, so `log-menu-3` applies as it is |

Changes against the build plan E7:

- **Pre-build step (V static, V harness).** exp keeps the sensor mode in **0x605A7254** (u32; writers 0x7E697B60 and
  0x7E69969B; 0x7E68F947 checks each CAM_AE_SETTING against it). Its numbers are CAM_SENSOR_MODE (table 0x7E7ABDA0):
  0 HS, 1 HSSC, 2 MSSC, 3 LSSC, 4 HSHR (movie, 18 × 14), 5 CLIP, 6 FULL, 7 STILL. 0x7E68FF9B gives modes 0 and 9 the
  HS area, 1 the HS area or, when 0x7E6A2680 returns 1, the HS3D crop (576 × 180 px), 2 MSSC, 3 LSSC, 4 HSHR, 5 CLIP.
  The stub now keeps the centre unless the mode is 0 or 2, or 1 with 0x7E6A2680 = 0 (+28 B). `spot_stub.py` checks
  HSSC and MSSC for all 35 targets and keeps the centre for HSHR, LSSC, CLIP, mode 9, 0xFFFF and the HS3D crop: PASS
  (`results/spot-stub.txt`).
- **Spot setting 593 (prm 0x94D1), not 0x9681.** 622 (0x9851) was the first pick and was dropped: the mode-controller
  scan puts it in the bank lists, standard reset and restore lists with a reset value 1
  (`../2026-11-18-look-editor/out/scan.tsv`). 593, 660 and 621 are MODE u8, default 0, no constant-id access, and in
  no mode-controller table but the full reset (R); 0x94D1 appears only in the info-id table (one raw hit inside a
  call displacement).
- **Texts by the loader only.** "Spot Metering" does not fit any spare English text in block 1, so the label and help
  are the unused built-in EVF texts 1494 and 1509, written by pointer in the loaded language (as `log-menu` writes
  its texts). Not in block 1.
- **Page child list at 0x7EBF1F50 was refused** by the free-space check (the candidate `osd-battery` holds
  0x7EBF1F4F–0x7EBF1FCA); it moved to 0x7EE3CEE4.
- `tools/space-ledger/superseded.tsv`: two rows, `card-looks-8` → `-9`, `custom-menu-rows-3` → `-4`.
- `gen/run.sh` and `gen/README.md` list the two new generators; the README's stock-films row names `card-looks-9`.

### Checks

| Check | Result |
|---|---|
| `epm2mod make spot-af` (free-space check inside) | exit 0, check PASS (0 FAIL) |
| `tools/checks.py data/builds/spot-af.json` (quick tier) | free space, op check (22 specs, 591 byte ops), boot-test, update-path-test: 4 PASS, exit 0 |
| `emulator/hookcheck.py data/specs/spot-core.json` | exit 0: hook segment 1 → segment 1; calls to 0x7E6A2680, 0x7E690A62 (segment 1) and 0x7E457C75 (kernel). The fifth line, `jmp 0x7E6A2653` at 0x7E69EE51, is the target table decoded as code |
| `emulator/boot-test`, `emulator/update-path-test` | PASS, exit 0 |
| `emulator/filmcheck.py` (the loader changed) | RESULT PASS, exit 0 |
| Harness `scripts/spot_stub.py` | PASS; the stub and hook bytes in `build/spot-af.BIN` equal the harness's assembled stub |
| Crawl `p-nocard-shallow`, `crawlcmp.py` against `peaking-mf` | exit 0: 269 screens equal outside the Custom Menu rows; rows 83 → 84: 14 lost, 15 new, all cursor positions of group E; firmware errors equal (36 × the stock 0x2a001001) |
| `shotdiff.sh` against `peaking-mf`: D → Info Settings, its page and the three sub-lists with a picker each; J → Load Looks and Debug Log with their lists | 0 of 10 and 0 of 4 differ, exit 0 |
| Settings test (P state from an empty store) | start 0 / 0 / 0. Spot On → 1 / 0 / 0; Spot Hilight On → 1 / 1 / 0; Spot Shadow On → 1 / 1 / 1; Spot Off → 0 / 1 / 1. Three restarts from the saved state: 0 / 1 / 1, the page shows Off / On / On (V emulator) |
| Greying (`canexec.mjs`) | The row's check is setting 1 (Metering), as the Metering row: iAUTO check 26 status 1 (greyed, the cursor skips it); P and ART all 0 (enabled; seen in ART) (V emulator) |
| Mode presets | P → ART → iAUTO → P (prm 0x8A71 = 3, 70, 7, 3), once with 0 / 1 / 1 and once with 1 / 1 / 1: the three values do not change (V emulator; R: no bank list or mode preset names them) |
| `tools/checks.py --tier full` (peaking scenarios, against `peaking-fast`) | exit 1: save-guard FAIL, peaking-s1-s5 and -s6-s7 REVIEW (S6 FAIL for art codes 9 …). The pinned `peaking-mf` has the same three statuses (`build/check-cache`), and `scen_direct4.py s6` gives the same S6 line, character for character, for `peaking-mf` and `spot-af`: the scenarios predate the stock-films structure, not a change of this build. S24, S25, S7 PASS; S4, S5 as the pinned build |

Screens: `results/spot-af-custom-menu-e.png` (E, page 2, the row), `results/spot-af-page.png`,
`results/spot-af-picker.png`, `results/spot-af-page-after-restart.png`.

Cosmetic, seen in the emulator: the page shows the sub-item class's ▤⚙ ▶ hint in its footer, as LV-Info does; the
row in E shows no value on the right (as ISO-Auto Set). The help text was not seen (the emulator shows no help).

### Still unknown, for the camera run

1. The exposure follows the AF target in live view **and in the saved photo** (acceptance 2). The still uses the
   pre-still result from live-view frames (I); whether 0x605A7254 still holds 0, 1 or 2 at that moment is U.
2. The grid against the AF frame (E5, I strong): a target at the bottom-left corner (k = 4) on the lamp.
3. Spot HI and Spot SH follow too; ESP, centre-weighted, all targets and C-AF+TR stay stock (acceptance 3).
4. Face priority: the spot stays on the selected target (acceptance 4).
5. Touch AF and the magnified frame (U, E1): which spot a touch gives.
6. Movie and the digital tele-converter keep the centre (V harness only).
7. Which HSSC case is the HS3D crop (0x7E6A2680 = 1) (U).
8. The help text in a non-English language, and the three rows after power-off on the camera.

## Camera run 1 (2026-11-24)

The owner flashed `spot-af` (sha256 `64421e1b…`) on 2026-11-24. Results as the owner reported them (V camera):

| Check | Result |
|---|---|
| Spot row Off, AF target on a bright and on a dark area | The same shutter speed: stock (pass) |
| Spot On, AF target chosen with the arrow keys | The exposure follows the target (pass) |
| Spot On, AF point set by a touch on the screen | **Fail.** The spot does not follow the touched point; it meters elsewhere. The owner: "the touch target does not control the spot, which is the biggest use case" |
| Spot HI, Spot SH | Work |
| ESP (with a film simulation) | Works |
| Face priority on | Meters at the AF point, not at the face (pass) |
| The menu row, the settings after power-off, the bottom-left alignment check | Not reported |

So the stub reads the right target for the arrow keys (prm 0x88B2), and a touch does not set prm 0x88B2 to the touched
point (I, from the result). The next step is to find where a touch stores its point (U in E1).

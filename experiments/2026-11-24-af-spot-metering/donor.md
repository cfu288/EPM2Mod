# Donor study: spot metering at the AF target in the E-M5 II and the PEN-F

Date: 2026-11-24. Desk work on the stock firmware of the E-M5 II 4.1 and the PEN-F 3.1. Nothing was built or flashed.

Labels: **V** = read in the firmware bytes; **I** = inferred; **U** = unknown; **R** = reported by another project.
Addresses are runtime addresses of the donor (block 0 offset + 0x60021020). E-PM2 addresses are firmware 1.6.

Method. `tools/oetool.py unpack`, then `tools/fwmap.py --base 0x60021020 build` for each donor (block 0 kept in the
scratchpad, not in the repository). The base comes from the om-c project's `profiles.json` (R). It is right: the map
resolves 60,660 string references, for example 0x605DCE7E loads `[TakeExp] af_tracking | af_enable:` (V). The donors
use the same MN103/AM33 instruction set: objdump decodes whole functions with matching `call`/`ret` frames (V).
`scripts/donor_check.py` re-checks the byte facts below in both files (exit status 0 = pass).

## 1. Answer

1. **The donors move the same 4×4 window over the same 18×18 BV grid** as the E-PM2. They do not compute a new
   window from the AF frame. The two 4×4 maps are byte-identical to the E-PM2 maps (V).
2. **The decision is made before the exp module.** The take-expose code (`[TakeExp]`) puts an AF position
   (−100..+100) in the exposure packet only when the metering mode is Spot, HI or SH, the AF target mode is single
   target, tracking is off and the user setting for that metering variant is on. Otherwise the exp module uses the
   stock centre window (V).
3. **Faces are ignored.** The position comes from the selected AF target (prm 0x88B2) or the magnified AF frame,
   never from face detection (V code, I behaviour).
4. **The PEN-F code is the same as the E-M5 II code**, instruction for instruction, at other addresses (V).

## 2. The user setting (question 1)

| Item | E-M5 II | PEN-F | Label |
|---|---|---|---|
| Menu text | `@A000@Spot Metering` (string id 2683) | id 2828 | V |
| Help text | "For the ✓ selected items, metering will be executed in the area of the AF target." (2684) | 2829 | V |
| Menu row record | 0x60F5BBE6 | 0x60F525E2 | V |
| Setting for Spot (HI/SH value 0) | prm 0x9681 = 1 | same | V |
| Setting for Spot HI (value 1) | prm 0xF931 = 1 | same | V |
| Setting for Spot SH (value 2) | prm 0xF941 = 1 | same | V |
| Default | 0 (off) for all three: ROM records `81 96 01 00 00000000` at 0x60114240, `31 f9 …`, `41 f9 …` at 0x60115084 | not read | I (the same record format holds 0x80A1 = 2, the known ESP default) |

The three tags are read only in the link test 0x605DCE7E (E-M5 II; PEN-F 0x605DE6AB) and in a handle cache (V). That
the menu row writes them is inferred from the help text and the HI/SH index (I). So the user picks Spot, Spot HI and
Spot SH one by one. ESP and centre-weighted metering never link (V).

The E-PM2 has prm 0x9681 too (MODE, u8, default 0, no GUI use). Its only reader is the Exif writer: with ESP and
0x9681 = 1 it adds 0x100 to MeteringMode (0x7E58734E) (V). The E-PM2 has no 0xF931 or 0xF941 (V: no reference).

## 3. The algorithm (question 2)

The link test 0x605DCE7E (V):

1. af_tracking = prm 0x6761. af_enable and the target centre (fx, fy) in a 640×480 frame come from
   `get_af_frame_single_target` 0x6047F116.
2. If the magnified AF frame flag (0x618ACE3A) is set: type 2, x, y = the frame's own −100..+100 coordinates.
   Else: type 5, x = fx × 200 / 640 − 100, y = fy × 200 / 480 − 100 (unsigned, truncating).
3. Type becomes 0 (no link) unless af_tracking = 0, (af_enable or the magnified frame), metering = 1 (spot) and the
   setting of the HI/SH variant = 1 (section 2).
4. It writes {u8 type, s16 x, s16 y, u8 HI/SH} to exposure packet +128 and to globals 0x618ACE42..48.

The spot routine 0x605B001D (PEN-F 0x605B4B4F) (V):

- Map A (12 cells: centre 2×2 and the ring of 8) normally; map B (centre 2×2) when halfword +14 of the exposure input
  struct is ≥ 160. The E-PM2 switch is byte (6) = 1 and halfword (8) = 200 instead.
- Window top-left cell: 133 (row 7, col 7, the E-PM2 constant 266 / 2) when type = 0. Else
  col = (x + 100) × 18 / 200, row = (y + 100) × 18 / 200, then top-left = (row − 2) × 18 + (col − 2), each term set to
  0 when it would be negative. There is no clamp at the bottom or right edge.
- Spot BV = rounded mean of the window cells of the clipped grid (+116), weighted 13 for the centre 2×2 and 12 for the
  ring (table 0x60660398: 13, 12, 9, 6, 4). The centre 2×2 carries 52 of 148, about 35 %.

Edges. The 81 targets (9×9, centres x = 91 + 57 × col, y = 91 + 37 × row at 0x605E54B4) give top-left col 0..13 and
row 1..12, so every window stays inside the grid (V, arithmetic). The low clamp acts only on the left column. A
magnified frame near +100 would read past the right edge; its range was not traced (U).

The target centre is scaled about (319, 239) by a percentage from 0x605396DF before step 2 (`0x6041B1D4`) (V). It
depends on digital zoom state (I: the 2× digital tele-converter).

## 4. AF modes and targets (question 3)

| Mode | Donor behaviour | Label |
|---|---|---|
| Single target (prm 0x84D1 = 0) | Linked to the target prm 0x88B2 (0..80; ≥ 81 gives target 40, the centre) | V |
| All targets, group target (0x84D1 ≠ 0) | Not linked: af_enable = 0, centre window | V code, I mode names |
| Magnified frame AF | Linked: `Set_MagnifyAF_Frame` 0x602E71EB → 0x60227F5B → `set_special_af_frame` 0x605DCDBB stores flag, x, y, mag at 0x618ACE3A..40. It wins over the single target | V |
| Face / eye priority | No face input in 0x6047F116, 0x605DCE7E or 0x605B001D. The spot stays on the selected target when a face is found | V code, I behaviour |
| Tracking (prm 0x6761 ≠ 0, printed as `af_tracking`) | Not linked | V code, I that it is C-AF+TR |
| Touch AF | Not traced. Only the magnify path and the `exp` debug shell set the special frame | U |
| Small target | Not traced | U |

## 5. Live view and still (question 4)

- The AF position travels in the exposure packet (+128) built by 0x605DC71B. Its callers are 0x605DBE4E (the
  `take_expose_calculate` path of the release) and 0x605DB897 (called through a pointer) (V). That 0x605DB897 is the
  live-view packet is inferred (I).
- In the exp task one chain reaches the spot routine: 0x605AD892 (task entry) → 0x605C0758 → 0x605CE09F →
  0x605CE9AA → 0x605CEB32 → 0x605AFED9 → 0x605B001D (V, static). So one moved window serves live view and the still,
  as on the E-PM2 (I).
- A second spot source exists only in the donors. When byte +24 of the exp state is set, the spot BV is halfword +14
  of the struct that the grid block points to at +120, not the grid mean (V). 0x605B0E93 places that hardware AE window at the AF position
  (`focus_linkage VGA position_x | y`, `[exp]:full_expand spot hs|vs`), except when the mode word at +4 of the exp input is 5 (V). Which frames
  use it is unknown (U). The E-PM2 has none of these strings (V).
- Digital tele-converter: map B is used, and the window still moves (V). Target coordinates are scaled first (I).
- Exif: for spot metering the MakerNote MeteringMode keeps bit 0x800 from the shot record (0x605DD315) (V); that the
  bit means "linked to AF" is inferred (I).
- The GUI test 0x6022667C returns 0 while the link is active (V); what it hides is unknown (U). The SDK command
  `m74 getAfPointSpotMetering` returns the link state (0x607365B1 → 0x602E9842) (V).
- Movie, AE lock and the AEL/AFL button: not traced (U).

## 6. Same code family as the E-PM2 (question 5)

| Part | E-PM2 0x7E690A62 / 0x7E691007 | Donors 0x605B001D | Label |
|---|---|---|---|
| Grid | 18×18 s16, clipped copy at +116 | same | V |
| 4×4 maps | 0x7E7DA8E8 / 0x7E7DA8F8 | identical bytes, 0x606604E6 / 0x606604F6 | V |
| Weights | zone means, (Z5 × 230 + Z4 × 26 + 128) >> 8: the core is 90 % | per-cell 13 / 12: the core is 35 % | V |
| Window position | constant displacement 266 | from the AF position, default cell 133 | V |
| Result struct | +0 spot, +12 = −768 | same | V |
| Zone builder | separate functions | merged into one routine | V |
| Hardware spot window | none | 0x605B0E93 | V |

The donor routine is the E-PM2 routine with the constant window start replaced by a computed one (V). Our option A
(NOTES.md section 5) does the same thing by moving the grid pointer before the stock call (I: equivalent). The weight
table 230/26 is not in the donors (V): Olympus also changed the spot weighting. That is a separate change.

The donor maps −100..+100 linearly onto the 18 grid columns and rows with no offset (V). So on the donors the grid
spans the AF coordinate field. This supports the NOTES.md assumption U1 for the E-PM2 but does not prove it (I).

## 7. Design for the E-PM2 (question 6)

1. **Window:** keep the stock 4×4 window and the stock 230/26 weights, and only move it. The donors use the same
   window size (V). Their flatter weights would change Spot even at the centre; leave them for a later, separate test.
2. **Position:** use the 35-entry table of NOTES.md with rounding. The donor's truncation puts its centre target one
   cell up and left of its own unlinked window (`donor_check.py`: (6, 6) against (7, 7)). Rounding keeps the centre
   target identical to stock. All 35 rounded windows lie inside the grid (V, harness), so no clamp code is needed.
3. **Conditions:** copy the donor. Move the window only when metering is Spot, HI or SH (prm 0x80A1 = 1), the AF target
   mode is single (prm 0x84D1 = 0) and tracking is off. Everywhere else read the stock centre. The metering test
   matters for our hook: the donor never moves the window outside spot metering (V), and on the E-PM2 the spot zones
   are part of the zone output that other BVs may read (U).
4. **Faces:** follow the selected target and ignore faces, as the donor does. No code.
5. **Magnified frame AF:** the donor links it. The E-PM2 has the same special frame (x, y in −100..+100, NOTES.md
   section 4), so the donor formula col = (x + 100) × 18 / 200 fits. Leave it for a second step (≈ 30 B).
6. **Tele-converter (map B):** keep the centre in the first build. The donor's coordinate scaling is only inferred.
7. **Setting:** Olympus made the link opt-in, per metering variant, off by default (I). Whether the E-PM2 version gets
   a menu row is the owner's decision. If it does, prm 0x9681 is a candidate store: it exists on the E-PM2, is unused by
   the GUI and is the tag the donors use for Spot. Its persistence (MODE class) is unknown (U), and with ESP it would
   add 0x100 to the Exif MeteringMode.

## 8. Unknowns and the smallest probes

- E-PM2 meaning of prm 0x6761 (U): in the emulator, set AF mode to C-AF+TR and read the prm.
- Whether E-PM2 ESP or other BVs read the spot zones Z4/Z5 (U): harness, move the window and compare the six BVs of
  0x7E6907F0 in ESP mode.
- Touch AF, small target, movie, AE lock in the donors (U): not needed for the first E-PM2 build.
- When the donors use the hardware spot window (U): it has no E-PM2 counterpart, so it does not change the design.

## Files

- `scripts/donor_check.py`: checks the maps, weights, AF target table and the setting loads in both donors, and prints
  the E-PM2 window placement with the donor arithmetic and with rounding. `uv run python
  experiments/2026-11-24-af-spot-metering/scripts/donor_check.py /path/to/OLY_E_118_4100_0000_0000.BIN
  /path/to/OLY_E_122_3101_0000_0000.BIN` (exit status 0 = PASS).

# The 12-region stage: one camera run that measures it (2026-11-20)

Goal: one flash that gives every number needed to model stage 7 of `docs/dev/colour-pipeline.md` (the 12-region hue,
saturation and lightness stage, builder 0x7E56E186) and to write per-film tables. Labels: **V** = read in the firmware
bytes or run in the emulator, **I** = inferred, **U** = unknown until the camera run, **[C]** camera-confirmed. Nothing
here is camera-tested yet.

## 1. What the firmware says (checked for this design)

| Item | Finding | Label |
|---|---|---|
| Builder 0x7E56E186 | Called only from 0x7E56E661 (twice: the normal path, and Dramatic Tone's table 0x7E78BE00 for op class 2). Input: a descriptor `{u32 table, 12 x u32 ISO-weight pointers}` (52 B). Output block: per record 6 words at out+568+24r: `hs\|hw<<16`, `cs\|cw<<16`, `ys\|yw<<16`, bytes 20-23, `b24\|b25<<8\|H<<16`, `S\|L<<16`; the mask at out+856; ten curve pointers at out+884..920 (table+336, +720, +1104, +1296, +1488, +1680, +2064, +2448, +2640, +2832). The engine reads the curves through these pointers | V |
| Record bytes 18-19 and 26-27 | Never read by the builder: they cannot reach the engine. Bytes 20-25 are (mult, shift) of the hue, chroma and luma windows; width x mult >> shift = 256 in every stock record | V |
| Curves | 7 curves per record, 16 points each, a point = (level << 8) \| signed slope; level[k+1] = level[k] + slope[k] in every stock table. Two groups of five arrays (records 0-5, 6-11), 16 entries per record. Slot order c0..c6 in `scripts/tables.py` | V |
| Curve roles | c5 = luma (flat 63 whenever a record's luma window is "all"); c0 and c3 = saturation along hue and chroma (Key Line, Watercolor, Cross Process II: sat-only records vary only c0 / c3, and Cross Process II sets c1, c2, c4, c6 to 0); c2 = lightness along chroma (Key Line r7, Watercolor r9: light-only records vary c2); c4 = hue shift along chroma; c1 / c6 = lightness / hue shift along hue, which one is which unknown | I (strong), U (c1 vs c6) |
| ISO weights | All 12 x 24 B arrays of every descriptor the probe uses are flat 256: the record values reach the engine unchanged (`mkspec.py` asserts it) | V |
| Selection | 0x7E56E661: op class (job+194) through 0x7E56A844 → normal / Dramatic only / off; code = P+79 (3 when P+20 bit 16 or 17); P+20 bit 16 takes another source (0x7E56DFF5, P->4->8); else hash 0x7E78C6E4 (64 slots, key = code − 8, linear probing, key 0 = empty) → a case of the worker 0x7E56E495, else a default by picture mode P+83 (0x7E56A8B7). In every case P+82 != 0 picks the second descriptor (table B) | V |
| What films get now | Base build (films-look-exif-artbkt), emulator, all 12 film codes: table A (P+83 = 2) or its byte copy 0x7E772268 (P+83 = 4); with P+82 = 1, table B or its copy | V |
| Table B and films | "When [Picture Mode] is set to [ART], [Color Space] is locked to [sRGB]" (manual p. 66). Films never get table B; the probe does not test it on the camera (no Adobe RGB developments) | V (manual) |
| Second builder | 0x7E55E2CE (same structure, ISO table 0x7E769B04) prebuilds blocks for a fixed list of tables at start (0x7E55E829, 0x7E55EAFF): A, B, the mode 1 / 3 / 4 tables, Gentle Sepia, Cross Process II, Watercolor I and II. Its user is not traced. The probe does not touch those tables | V (refs), U (user) |
| Hardware | The per-pixel arithmetic is in the engine; the CPU only uploads. Hue, chroma and luma definitions, units, curve interpolation, window edges, combination and clipping are all U: the camera run measures them | U |

The doc `colour-pipeline.md` §2 says bytes 18-27 hold the multipliers and that the stage's tables "may" be shared;
the table above corrects that (not edited here: the doc is shared).

## 2. The build: data edits only

`data/builds/twelve-region-probe.json` = `films-look-exif-artbkt` (pinned films-look-exif + the RAW Data Edit ART BKT
row, `../2026-11-20-raw-edit-art-bkt/NOTES.md` §8) + `data/specs/twelve-region-probe.json` (written by
`scripts/mkspec.py`, 29 ops, 51,568 bytes, **no code, no hook**):

- 10 hash entries for the film codes, in empty slots only (every stock key is found as before: an emulator run of 43
  stock codes gives the same table pointers on both builds). Each points at an **existing** case of the worker.
- 17 tables written over the tables that those cases' descriptors point at: 16 byte copies of table A / B (pair cases
  0x7E56E4E6 ... 0x7E56E598, sRGB and P+82 descriptors) and the stock Key Line still table 0x7E7826A0 (case 0x7E56E5B8,
  codes 119 / 123; peaking uses 163 / 164). Each of these tables is referenced only by its descriptor (scan of every
  byte offset of block 0). Side effect in this test build only: 26 stock scene / Key Line codes render with probe tables.
- ART 12's code 159: look entry 0x7E78CB40 → Cross Process I's look handler 0x7E56E94A (table 0x7E75F2F0), instead of
  LKID. The emulator's look selector gives 0x7E75F2F0 for 159 and the identity table for the other film codes.
- Code 75 (ART 2) has no hash entry: it keeps what every film gets on the pinned build.
- Free space used: none. Areas written: tables inside 0x7E773A10-0x7E780EF8 and 0x7E7826A0-0x7E783274, 0x7E78C704-0x7E78C8E4
  (hash slots), 0x7E78CB40 (4 B). raw-edit-art-bkt's 0x7EBB2AC4-0x7EBB2CEC and its hooks are untouched.

| ART | Entry (code) | Table | Film | Answers |
|---|---|---|---|---|
| 1 | Pop Art (79) | CTRL: mask 0, all zero | clear | the stage-7 input of every other entry (control) |
| 2 | Soft Focus (75) | default: table A | clear | what Natural's table A does to films today; the model checked on Olympus's own curves |
| 3 | Pale&Light (71) | HUEMAP: 12 windows of 10° at 10+30k°, L −40…−150 | clear | hue zero, direction and scale; window width |
| 4 | Light Tone (72) | MAGL: 12 sectors of 30°, L −1023…+1023 | clear | lightness units, linearity, sign, added or scaled, clipping |
| 5 | Grainy Film (94) | MAGS: sectors, S −256…+2048 | clear | saturation: multiply or add, units, extremes. Also the live-view / movie entry |
| 6 | Pin Hole (92) | MAGH: sectors, H −180°…+120° | clear | hue-shift units, sign, wrap |
| 7 | Diorama (125) | CURVES: record k has slot c_k as a ramp, all three effects on | clear | which slot shapes which effect along which axis; c1 vs c6; c5 shared |
| 8 | Cross Process (85) | OVERLAP: equal-effect pairs, a mixed half-overlap, two records with mask bit off | clear | how records combine; the mask, bits 4 and 10 off, 5 and 11 on (both groups) |
| 9 | Gentle Sepia (98) | WINDOW: mult/shift for ½ and 2× width, luma (0,0), chroma (0,0), a window through 0°, slopes inconsistent with levels, levels 126, one record flat 63 to its ends | clear | window edges: hard or a clamped position; mult/shift; width 0; wrap; slope byte used; level > 63 |
| 10 | Dramatic Tone (144) | BOX: luma bands 192-320, 704-832, 448-576; chroma bands 24-56 … 400-560 at hue 0-180°; hue bands | clear | luma and chroma units; Euclidean or other chroma |
| 11 | Key Line (156) | BOX | gain 423 (1.5 x Natural) + chroma curves, first stored slope 0.5, second 0.75 | order against the saturation gain and the chroma curves; which stored curve is Cb (camera-confirmed Cb first on 2026-11-12: a second check) |
| 12 | Watercolor (159) | BOX | clear + Cross Process I's look | order against the look curve |

Every record: `uv run python scripts/tables.py`. Films: `scripts/films.py` writes `out/films/clear.npz`,
`stage6.npz`, `twelve-looks.json` and packs `build/twelve-probe/EPM2LOOK.BIN` (sha256
`a71c78b1617164dfb33126fbfe5bf525d938a7200b5089160875e41187881b9d`; menu names "T CTRL" … "T BOX LOOK"). "clear" =
identity matrix, identity tone curves, six-axis 0, gain 282 (Natural), straight chroma curves.

Redundancy: effects of one kind appear in several entries (L: 3, 4, 8, 9, 10; S: 5, 7, 8, 9; H: 6, 7, 8, 10), window
edges in 3, 4, 5, 6, 10 (36 hue edges, interleaved), and the patches outside every window of an entry are a second
control. Two RAWs (below) give each entry twice.

## 3. The test RAW

`testraw/PB200001.ORF` (sha256 `e82e18a66d898c9a716603427feca9d05e72aa4210af7ce99a264bba45ea738c`), layout
`testraw/twelve_layout.npz` (`e0e0b895…`), by `scripts/chart.py` with make_mock2.py's geometry, encoder and blanked
header. Patches are chosen in the stage-7 input space (8-bit Y, Cb, Cr of the clear film at WB 5300 K), inverted through
model2: grid 72 hues x 7 chroma x 8 lumas (3,825 in gamut), 1° hue ring (360), 12 chroma lines (648), 7 luma lines
(574), 300 raw copies of PB130001 patches (scene check), 25 equal greys, 1,072 filler. Round trip through the model: max
0.9 code. Self-test (`chart.py --selftest`: model development, lens-like warp, JPEG): all 5,732 non-filler patches read,
mean error 0.40 code. The registration of a heavily changed entry (MAG L clips whole sectors) uses ART 1's: RAW Data
Edit gives every entry the same geometry (I).

## 4. Checks

| Check | Result |
|---|---|
| `uv run epm2mod make twelve-region-probe` | sha256 `d492e3c853b60fbef5c7e3d2dcf85cfd677096873806f3ae709286f46e2608df`; free space PASS; boot-test PASS; update-path-test PASS; FIRST CODE note (raw-edit-art-bkt's code) |
| `emulator/hookcheck.py data/specs/twelve-region-probe.json` | 0 transfers, 0 FAIL |
| `scripts/emucheck.py` (0x7E56E661 run in om-emu: worker + builder, P+82 0 / 1, P+83 2 / 4) | PASS: every film code builds its table's exact words, mask and curve pointers; code 75 gets table A; 43 stock codes keep their table pointers (`results/emucheck.txt`) |
| Look selector 0x7E56E837 (emulator) | code 159 → 0x7E75F2F0; 92, 144, 156 → 0x7E75B8F0 |
| `tools/checks.py --tier full` | free space, op-check, boot-test, update-path-test PASS; save-guard "FAIL" and peaking-s6-s7 "FAIL" are the reference's: run side by side, the base build films-look-exif-artbkt gives the same (save-guard S19-S25: base and probe PASS, only the reference peaking-fast fails, by design; S6 against peaking-fast: base and probe differ from it in the same 172 codes, against the pinned films-look-exif both PASS); peaking-s1-s5 REVIEW: same state as pinned |
| `scripts/analyse.py --selftest` | PASS on two simulated runs (`results/analyse-selftest.txt`): "nominal" and "other" (hue sign −1, zero 7°, chroma 3.1 per code, added saturation, clamped windows, c1 / c6 swapped, stage 7 between the gain and the chroma curves). Every check (hue sign, zero, luma and chroma units, L, S mode, H units, windows, roles, both orders) recovered |
| Menu paths | WB Sunny and LN+RAW: emulator screenshots `results/live-control-wb-sunny.png`, `results/live-control-quality.png`; ART BKT list and RAW Data Edit row: raw-edit-art-bkt §8.6 (emulator) |

## 5. Camera sheet (one flash)

On the Mac, card in, mounted at `/Volumes/Untitled`:

1. Empty the photo folder; copy the two RAWs and the film file:
   `rm -f /Volumes/Untitled/DCIM/100OLYMP/* && mkdir -p /Volumes/Untitled/DCIM/100OLYMP`
   `scp USER@HOST:/path/to/epm2-tools/experiments/2026-11-20-twelve-region/testraw/PB200001.ORF /Volumes/Untitled/DCIM/100OLYMP/PB200001.ORF`
   `scp USER@HOST:/path/to/epm2-tools/experiments/2026-11-09-film-portra/testraw/PB130001.ORF /Volumes/Untitled/DCIM/100OLYMP/PB130001.ORF`
   `scp USER@HOST:/path/to/epm2-tools/build/twelve-probe/EPM2LOOK.BIN /Volumes/Untitled/EPM2LOOK.BIN`
2. Flash: `epm2flash twelve-region-probe d492e3c853b60fbef5c7e3d2dcf85cfd677096873806f3ae709286f46e2608df`
3. Card in the camera, camera off. Hold **OK** and **ON/OFF** together; let go when the orange lamp lights. Wait for it
   to blink, then switch off and on.

On the camera:

4. MENU → SETUP → gears tab → **J** → **Load Looks** → **Load** → OK. The row reads **Loaded**.
5. P mode: MENU → the mode screen; LEFT / RIGHT to **P** (the text reads "Sets the Aperture and Shutter Speed
   Automatically") → OK.
6. Press OK. In the right column, UP / DOWN to **Picture Mode** → **Natural**. Then UP / DOWN to the **WB** icon →
   RIGHT to **Sunny** (the bar reads "Sunny"). Then to the image-quality icon → RIGHT to **LN +RAW** (the bar reads
   4608x3456). OK.
7. ART BKT selection: MENU → the mode screen; LEFT x 4 to **ART** → OK; DOWN to **13 ART BKT**; RIGHT → screen
   **ART BKT**. All 12 entries (T CTRL … T BOX LOOK) **On**; the rows below Watercolor **Off**. MENU, MENU. Back to P as
   in step 5.

Part 1, developments (13 JPEGs per RAW):

8. Press ▶. Show **PB200001**. OK → **RAW Data Edit** → OK. The list reads Current, Custom1, Custom2, **ART BKT**, No.
   DOWN x 3 to **ART BKT** → OK. Preview with **Yes / No** → **Yes** → OK. **Busy** for each frame; at the end
   **Reset / No** → **No** → OK.
9. Show **PB130001** and repeat step 8.

   If ART BKT misbehaves (no row, an error, a freeze, fewer than 13 new files): switch off and on, then develop each
   entry by hand, ART 1 to ART 12 in order, first PB200001, then PB130001: MENU → the mode screen; LEFT x 4 to **ART**
   → OK; DOWN to entry n → OK; ▶; show the RAW; OK → **RAW Data Edit** → OK → **Current** → OK → **Yes** → OK. Say
   which way was used.

Part 2, one capture (stage 7 outside RAW Data Edit):

10. MENU → the mode screen; LEFT x 4 to **ART** → OK; DOWN to **13 ART BKT** → OK. Aim at a colourful scene (red,
    yellow, green, blue objects, a face or skin, sky if there is one). One press of the shutter. Wait until the card
    lamp stops (13 JPEGs and one ORF).

Part 3, live view and movie:

11. MENU → the mode screen; LEFT x 4 to **ART** → OK; DOWN to **5 T MAG S** → OK. Look at the same scene in live view,
    then take one photo and look at it (▶). Write down which colours differ between live view and the photo (for
    example: red objects grey in the photo, yellow or blue much stronger).
12. Still in ART 5: press the movie button, record 5 s of the same scene, press it again. Then select **1 T CTRL** as
    in 11 and record 5 s of the same scene.
13. MENU, switch off. Copy back:
    `scp -r /Volumes/Untitled/DCIM/100OLYMP USER@HOST:/path/to/twelve-probe/`

Go back (the build is for this test only):

14. `scp USER@HOST:/path/to/epm2-tools/build/twelve-probe/EPM2LOOK-restore.BIN /Volumes/Untitled/EPM2LOOK.BIN`
    (the pinned film list, sha256 `98d0ce5c…0748`), then `epm2flash films-look-exif af4bcb38df908c3d29b3ef028059a3142cbecc4b66737f7bb2cc2848d6a4bcf4`,
    flash as in step 3, then step 4 (Load Looks → Load): the test looks stay in the camera until a Load replaces them.

Expected:

| Step | Result | Other results mean |
|---|---|---|
| 4 | Loaded; ART 1 reads T CTRL | — |
| 8, 9 | 13 new JPEGs each: Natural, then ART 1-12 | Fewer: the ART BKT row failed; use the fallback |
| 8 | ART 3-12 visibly differ from ART 1 in some colours; ART 1 and ART 2 nearly equal | ART 1 = all others: the stage does not act in RAW Data Edit (the P+20 bit-16 source or op class), part 2 still answers for captures |
| 10 | 13 JPEGs differ as in step 8 | Equal to each other: the stage does not act in captures either; the hash route is not taken |
| 11 | Live view keeps colours the photo changes | Live view changed too: pipe B has the stage |
| 12 | The two movies look alike | ART 5's movie changed: movies have the stage |

## 6. Analysis plan (ready before the flash)

```
OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/analyse.py /path/to/twelve-probe/100OLYMP --guess
OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/analyse.py /path/to/twelve-probe/100OLYMP --map /path/to/twelve-probe/100OLYMP/map.json
```

`--guess` maps files by the sheet's order (with the fallback: `--no-frame0`); the run prints a classification line per
file (which entry it resembles) to catch a wrong order. Output: stdout and `results.json`.

| Stage | Data | Gives (with uncertainty) |
|---|---|---|
| A | ART 3 vs 1 | hue = sign x atan2(Cr, Cb) + zero; scale; window widths (selftest: zero within 0.3°) |
| B | ART 10 vs 1 | luma units per 8-bit code and offset; chroma units; chroma metric (edge radius by hue) |
| C | ART 4, 5, 6 vs 1 | L: codes per unit, added or scaled, clipping; S: multiply or add, per unit, extremes; H: degrees per unit, wrap |
| D | ART 7 vs 1 | slot → (effect, axis); c1 vs c6; c5 shared (indicative; E decides) |
| E | ART 3-10 | one least-squares fit of `tables.apply`: zero, units, scales; window hard / clamped, roles, sat mode by residual |
| F | ART 8, 9, 2, 11, 12, REF, capture, movie | overlap sums and mask; window semantics (W1-W8); table A's effect and the model's residual on it; order against stage 6 and the look curve (residual of each hypothesis); slope of each stored chroma curve; scene check (raw-identical patches in both RAWs); capture and movie differences |

Then: write the stage into `colour-pipeline.md` as [C], and fit per-film tables with `tables.apply` added to model2.

## 7. Risks and unknowns

| Risk | What happens | Label |
|---|---|---|
| RAW Data Edit takes the P+20 bit-16 source or an op class that skips the stage | Part 1 shows no effect; part 2 (capture) still measures the stage on a real scene, without the chart | U |
| ART BKT row (first code of raw-edit-art-bkt) | The fallback develops 24 files by hand | U |
| Engine bit widths: S 2048, L ±1023, H ±180° | May wrap instead of clip: measured, and those sectors are excluded from the linear fits | U, intended |
| W1 (curves not 0 at the ends) spills over the whole ART 9 picture if windows are not hard | Measured as an offset; the other ART 9 records still read | U, intended |
| Stage D's labels can be wrong when windows are clamped or saturation is added (selftest "other": c1, c4) | E's fit decides the roles | V (simulation) |
| E's uncertainties are NaN when a parameter does not move the residual (nominal simulation) | Read A-C's uncertainties | V (simulation) |
| Order residuals are 2.6-6.6 codes even for the true order: the in-entry maps of stage 5/6 are interpolated across the BOX bands | The true order still won by 1.4-4.7 codes in both simulations | V (simulation) |
| W6 (slope byte) margin is small: 3.5 vs 4.5 codes in simulation | Decided also by E's residual | V (simulation) |
| Scene modes and stock Key Line stills use probe tables in this build | Not used in the test; the build goes back after it | V |

## 7. First attempt (2026-11-20): neither RAW in playback

With PB200001.ORF and PB130001.ORF in `DCIM/100OLYMP/` the camera showed neither. Both files decode alike (rawpy: same
size, white balance, three embedded JPEGs), so the files are sound [C]. Both carry the DCF file number 0001; DCF counts
files of one number in one folder as one picture, and two RAWs under one number are not a valid picture [I]. Every
earlier run had one RAW per number. Fix: the new RAW goes on the card as **PB200002.ORF** (the repository file keeps
its name); in steps 8 and 9 read PB200002 for PB200001. The analysis maps by order, not by name.

## 8. Camera run 1 (2026-11-20): PB200002 developed with ART BKT

With the RAW renamed (§7) both RAWs showed in playback [C]. The owner copied back 13 JPEGs (PB200003–PB200015). All 13
come from PB200002 (luma correlation with a PB130001 development 0.03–0.07, with each other 0.56–1.00); the 13
developments of PB130001 are not on the card. EXIF of all 13: Picture Mode Natural, ArtFilter Off, ImageDescription
Olympus's text, one ColorMatrix. Parts 2–5 not yet run. Output: `results/camera-1/analyse.txt` (map in
`results/camera-1/map.json`, the sheet's order). The classification check agrees with the order except ART 5 (looks
like ART 6, r 0.27) and ART 11, 12 (look like ART 10, whose table they reuse); stage C reads ART 5 as the MAG S entry
it is, so the order stands.

Measured [C], RAW Data Edit, pipe A:

| Question | Result |
|---|---|
| Does the stage act in RAW Data Edit, per ART entry? | Yes: every probe table changes its development; ART 1 (all records off) and ART 2 (table A) differ by rms 1.17 codes, as table A predicts (model residual 0.67) |
| Hue | record hue = +1 × atan2(Cr, Cb) + 0.13° (± 0.14°); 32768 = 360° (scale 1.001) |
| Luma window | luma = 4.05 × Y8 − 4.6: the 10-bit luma, 0–1024 |
| Chroma window | about 6.0 × the 8-bit Cb/Cr radius (± 0.5); the first edge at hue 158° is off (13.7 against 58–64 elsewhere): metric not settled |
| Window edges | hard: a pixel inside gets the full change, outside none; a window position past 256 of the multiplier has no effect |
| Lightness change | added to Y: 0.239 × L 8-bit codes (L/4, 10-bit), linear up to ±512, then clipped; not scaled by Y |
| Saturation change | added to the chroma radius: 0.238 codes per unit (S/4); S −128 and below remove all colour; S +1024 acts as a negative value and +2048 as 0 (an 11-bit signed field [I]) |
| Hue shift | not understood: written −5° gives +25.9°, +30° gives +1.8°, +60° gives +50.5°; no linear rule (154 ± 117° per 32768) |
| Overlapping records | effects add (L −64 twice = −30 codes; H +10° and +20° = +28.5°) |
| Enable mask | a record with its bit off has no effect; bits 4, 5, 10, 11 as written |
| Curve slots | c0 saturation along hue; c2 and c6 lightness along chroma; c3 saturation along chroma; c4 hue along chroma; c5 saturation and lightness along luma; c1 no visible role |
| Order | before the look curve (residual 5.1 against 8.0 after) and before the saturation gain and chroma curves (4.1 against 4.6 after: a small margin) |
| Whole-stage model | best residual 8.7 codes over entries 3–10: the hue-shift rule is missing |

Open: the hue-shift rule; the chroma metric; captures, live view and movies (parts 2, 3); ART BKT with PB130001, three
entries and a full card (parts 1 second half, 4, 5).

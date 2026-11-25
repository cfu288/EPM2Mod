# Film tables that live view reads before segment 2 is in RAM (2026-11-25)

Labels: V verified (bytes, disassembly, a harness run, a camera report), I inferred, U unknown.

The class of fault is that of [issue #6](../2026-11-24-slow-boot/NOTES.md): code in segment 1 that runs in the quick
start goes to segment 2 before the task Usr1 has copied it. `stock-films-structure-3` points 25 words of three stock
jump tables at stubs in segment 2, for the stored values 111, 112, 114, 115 and 118 (the film simulations on Grainy
Film, Gentle Sepia, Dramatic Tone, Key Line and Watercolor).

## 1. Which of the 25 words are reached early

MOV_TASK 0x7E6C33B5 makes one pass per message or frame. In a pass with a frame it calls, in this order (V
disassembly): the struct refresh 0x7E6ECCAF (0x7E6C33EE), then, unless the tests at 0x7E6C3407 and 0x7E6C341A leave,
0x7E6C5A23 (0x7E6C3433) and 0x7E6C3FD8 (0x7E6C3447). 0x7E6C3FD8 takes the pending request and calls the current
state function; the request "start" (0x08000000) makes that 0x7E6C410A, the start of live view.

On a contributor's camera the first refresh ran before segment 2 was in RAM (V camera, issue #6). U: whether the two
tests let that same pass through. Both read the frame record (0x605B0EF4 + 136 × index: +20 bit 15, +100 = 1).

| Words | Read by | Reached from | Before segment 2? |
|---|---|---|---|
| 5 at 0x7E7FF088–0x7E7FF0A4, still | mov_art 0x7E6CBFD3, Picture Mode from the struct (+3) | 0x7E6C5ACB in 0x7E6C5A23, and 0x7E6C4722 in 0x7E6C410A: both in the first pass that gets through | **yes, if that pass is early enough** (V static and harness that they are reached; U the time) |
| 5 at 0x7E854A50–0x7E854A6C | art_GetFilterType 0x7E71BD94 | 0x7E6C4736 in 0x7E6C410A → 0x7E6CBF87 → 0x7E6CD1F2 → 0x7E6CD2EE, right after the call above | **yes, the same** |
| 5 at 0x7E7FF034–0x7E7FF050, movie | mov_art, when the struct's movie word (+32, 0xA07511DC) is not 0 or its argument is odd | the same two calls. The word is cleared at MOV's init (0x7E6C32AD); its other writer 0x7E6CFCCF has five callers at 0x7E5965B9–0x7E5994A8 | not excluded (U) |
| 10 at 0x7E807858–0x7E8078C8 | 0x7E6DBA95 | seven calls. 0x7E6ECD73 and 0x7E6C5B79 need the movie-effect state 0x7E6DB43E = 4 or 5, 0x7E6C36A7 and 0x7E6C36FC = 5 (V disassembly). 0x7E6DB088 and 0x7E6DB21C handle movie-effect messages. 0x7E6CB1AC is in the frame pass (0x7E6C33F6 → 0x7E6CAE8B → 0x7E6CB0FB), only while the flag 0x605B0958 is 1, which 0x7E6DB8CA sets for a movie-effect event | no, needs a movie effect (I) |

So 10 words are on the path of every start of live view, not 5: art_GetFilterType is on it too. The harness shows it
(`scripts/frame_pass.py`, `results/frame-pass.txt`, V): 0x7E6C5A23 and 0x7E6C410A, whole, segments 2 and 3 not copied.
The pinned build faults in both for the five values (in 0x7E6C410A already in mov_art, which comes first) and returns
for modes 1 and 100. `results/film-cold.txt` shows art_GetFilterType's own fault.

A cold start with one of the five film simulations selected would be enough (I). Nobody has reported it.

## 2. The fix: `stock-films-structure-4`

No stock case stub gives 94, 98, 144, 156 or 159 (V search around the three functions). But each value has its own
stock stub, `mov CODE,d2; jmp tail`, and the only stock pointer to a stub is the value's table word, and nothing
branches to it (V: search of block 0 and of the linear disassembly). So the words keep their stock bytes and the stub's
immediate becomes the film code.

- 23 of 25: one immediate byte each, in segment 1. 0 B of new space.
- A stub with an 8-bit immediate sign-extends 144 and 156. mov_art's tail and 0x7E6DBA95's tail keep the low byte
  (`mov d2,d0; extbu d0`; with peaking's hook on mov_art's tail, 0x7E4C9262 does the same): they give the code.
  art_GetFilterType's tail keeps 16 bits, so its values 114 and 115 get new stubs in segment 1: 16 B at
  0x7E69ECA8–0x7E69ECB8, in the run of `pana-ring-probe` where code has run on the camera. 212 B of the area
  are free after it.
- The 15 stubs of version 3 in segment 2 (VF, VL, VM of the five codes) stay as they are, unused. The other 147 ops
  are the same. `gen/stock-films/structure.py`, `early_route`, finds and checks each stub.
- The 48 colour-stage table words of the film codes are unchanged: the colour stage runs 1.28 s or more after the copy
  in the owner's logs (safe by timing only, `emulator/hookcheck-allow.tsv`). Neither whole run of `frame_pass.py`
  reaches a colour stage.
- The entries of Soft Focus, Pin Hole and Diorama use words that the loader switches after the copy (from segment 3's
  constructor table), and segment 1 is copied again at each start: not early (V design, I).

Allow list: the three rows for these words are unused by this build (0 lines in `results/hookcheck-film-tables-fix.txt`).
They stay while `cold-start-fix` is pinned: CI's free-space check of the pinned build reads them, and
`cli/tests/test_hookcheck.py` holds spot-af-2, which has these words, to one FAIL. Remove them, and update that test,
when this build is pinned.

## 3. Build `film-tables-fix` and checks

`data/builds/film-tables-fix.json`: cold-start-fix with `stock-films-structure-4` in place of `-3`, label 2026.11.26. sha256
`e029facb38569880c0cec4c16b0f295ca2a96214ed75900fe00585f6b0cedd28`.

| Check | Result |
|---|---|
| `uv run epm2mod make film-tables-fix` | free space PASS (0 FAIL), 25,766 bytes changed |
| `scripts/film_cold.py` (values 100 to 120 through 10 routes of the three functions, peaking on too) | PASS (`results/film-cold.txt`). Copied: 210 of 210 as cold-start-fix. Not copied (0xFF, random): film-tables-fix 210 of 210 as copied, no fault, 0 instructions in late-loaded space; cold-start-fix: 50 cases fault, the five values only, on every route |
| `scripts/frame_pass.py` | film-tables-fix returns in all 14 runs, 0 late instructions; cold-start-fix faults in the 10 runs of the five values (`results/frame-pass.txt`) |
| `emulator/hookcheck.py` | 167 transfers, 0 FAIL, 62 allowed (cold-start-fix: 190, 87); none of the 62 is one of the 25 words |
| `emulator/opcheck.py` | 0 FAIL |
| `emulator/filmcheck.py` | PASS (`results/filmcheck.txt`) |
| `emulator/boot-test`, `emulator/update-path-test` | PASS, PASS |
| `uv run python -m unittest discover -s cli/tests` | 280 tests OK (6 skipped: they need the built app page) |
| `gen/run.sh --check` | every generated spec as committed |

Not run: `tools/checks.py --tier full` (the peaking scenarios; no peaking byte changes). Only the camera can show live
view with the five film simulations, and the start from cold.

## 4. Camera test sheet

Mac, card at `/Volumes/Untitled`. The look pack on the card, the old log off it, then the flash:

```sh
scp USER@HOST:/path/to/epm2-tools/build/default-looks/EPM2LOOK.BIN /Volumes/Untitled/EPM2LOOK.BIN
rm -f /Volumes/Untitled/EPM2LOG.BIN
epm2flash film-tables-fix e029facb38569880c0cec4c16b0f295ca2a96214ed75900fe00585f6b0cedd28
```

Go back: `epm2flash cold-start-fix eab0c64ea47d100c73a8b7889ab9ff1b83a91088dfc413073c1adb8268ba83d0`

This pack puts Double-X on Grainy Film (ART5), Provia on Gentle Sepia (ART9), Portra 160 on Dramatic Tone (ART10),
Gold 200 on Key Line (ART11) and Vis 500T on Watercolor (ART12).

1. **The build.** Update as in [flashing](../../docs/user/flashing.md). MENU → SETUP → wrench tab → Firmware.
   Expected: `Body : 1.6  EPM2Mod 2026.11.26`.
2. **Debug Log on.** MENU → SETUP → Custom Menu → J → Debug Log → On → OK.
3. **Load the pack.** MENU → SETUP → Custom Menu → J → Load Looks → Load → OK. Expected: Loading, then Loaded.
4. **P mode, five entries.** Mode dial P. Press OK, select Picture Mode, scroll right past Custom. Select Double-X,
   press OK, take a photo of something colourful. Expected: live view shows the film simulation (Double-X:
   black-and-white), the photo shows the same. Repeat with Provia, Portra 160, Gold 200 and Vis 500T. Live view of
   each must differ from Natural, and no entry may freeze or restart the camera.
5. **ART mode, five entries.** Mode dial ART. Choose Double-X in the list, press OK, take a photo. Repeat with
   Provia, Portra 160, Gold 200, Vis 500T. Expected: as step 4.
6. **Peaking.** Mode dial P. Press OK, in the right column choose AF Mode → MF. MENU → SETUP → Custom Menu → A →
   Peaking → White → OK. Picture Mode Double-X. Expected: white lines in live view. Press OK, AF Mode → S-AF: no
   lines.
7. **Spot metering.** MENU → SETUP → Custom Menu → E. Exp/▣/ISO → Spot Metering → RIGHT → Spot → RIGHT → On → OK. Press
   OK, in the right column choose the metering item → Spot. Tap a lamp on the screen, then a dark area. Expected:
   darker after the lamp, brighter after the dark area.
8. **Starts.** Mode dial P, Picture Mode Double-X. For each start press ON/OFF once and count the seconds until live
   view shows the picture. Write down the time, whether the screen lit, went dark and lit again, and whether the
   picture is black-and-white.
   1. Off 2 min, then a start. Twice.
   2. Battery out for 2 min. Battery in. Wait 10 s. A start. Twice.
9. Turn the camera off. Card into the Mac:

```sh
scp /Volumes/Untitled/EPM2LOG.BIN USER@HOST:/path/to/epm2-tools/.local/spot-af-logs/EPM2LOG-film-tables-fix.BIN
```

| Result | Meaning |
|---|---|
| Steps 3 to 7 as expected, every start of step 8 about 2 s and black-and-white | pass: pin the build |
| One entry shows the wrong picture in live view or in the photo | its edited stub is wrong: write down which entry, which mode, live view or photo; go back |
| All five entries wrong | the pack was not read (step 3), or the build is not this one |
| A freeze or a restart when an entry is selected | a fault in a stub: go back |
| A start of step 8 takes 8 s or more, or the screen lights twice | the issue shows on this body: the log tells whether `seg_loaded` came before the first live-view state |
| No lines in step 6 | not from this change (peaking is byte for byte as flashed): go back, repeat step 6 |
| Spot metering fails | not from this change (spot-core-2 is byte for byte as flashed): go back, repeat step 7 |

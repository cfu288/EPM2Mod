# Can every visible art filter become a film slot? Evaluation, 2026-11-12

Question: can all twelve art filters in the quick menu be rebuilt to accept any film look, the way
Portra 400 was built, without making the firmware unstable?

Evidence: `experiments/2026-11-09-film-portra/NOTES.md` §26–32, the inventory
`experiments/2026-11-09-film-portra/slots/artcode_inventory.json`, and the emulator cases in
`tools/emu/cases.py`. Labels: **[C]** confirmed on the camera, **[E]** confirmed in the emulator,
**[R]** read from code or tables, **[I]** inferred.

## 1. Answer

| Group | Filters | Verdict |
|---|---|---|
| Done | Cross Process, Light Tone, Pop Art | Film slots today, measured on the camera **[C]** |
| Ready to test | Pale&Light, Soft Focus, Pin Hole, Diorama | **Yes, with the same kind of change.** Built as a prototype and checked in the emulator **[E]**; needs one flash to confirm on the camera |
| Built, by a different route | Grainy Film, Gentle Sepia, Dramatic Tone, Key Line, Watercolor | **Prototype built** (§4): the menu entries are sent to the numbers of five hidden second types. Number selection, curves and matrix checked in the emulator **[E]**; how the recording code copes is untested and needs a flash |

So seven of twelve: yes, at low risk (four of them still to be confirmed on the camera). The other
five: a prototype exists and passes every check that can be made without the camera, but it changes
which number the menu produces, in code this project has not worked in before, and only the
camera can show whether recording, live view and playback accept it.

**What this evaluation cannot settle at the desk:** anything about live view, movie, art bracketing
and the recording flow. The emulator runs single image-library functions only. Those need the camera.

## 2. What was checked

1. **Screening on the camera.** Each remaining filter developed the test RAW with its stock look
   (NOTES §31). Pale&Light has no spatial effect and matches the model to 1.0 ΔE; Diorama's colour
   is clean under its blur; Pin Hole is a vignette; Soft Focus a blur and glow; the other five are
   effects first.
2. **A full inventory of where the firmware treats filter numbers specially**
   (`slots/scan_artcode.py`): every lookup table indexed by the filter number and every group of
   comparisons against filter numbers, in the image library, the white balance module and the
   record / art / movie code.

   | Filter | Special comparisons in the image library | Own entries in image-library lookup tables beyond the six stages | Effect program |
   |---|---|---|---|
   | Light Tone, Pop Art, Pale&Light | 0 (Pop Art: the matrix) | none | none |
   | Soft Focus | 0 | none | blur, forced by two comparisons in the art task |
   | Pin Hole | 0 | none | vignette, one lookup entry |
   | Diorama | 0 | none | blur bands, one lookup entry |
   | Cross Process | 2 (the scene-dependent hue) | none | none |
   | Gentle Sepia | 5 | 1 table | toning program |
   | Grainy Film | 3 | 3 tables | grain program; 14 more places in record / art code |
   | Watercolor | 4 | 3 tables | effect program; 13 more places |
   | Key Line | 8 | 2 tables | effect program; 14 more places |
   | Dramatic Tone | 27 | 1 table | effect program |

3. **The white balance shift** of Pale&Light and Pin Hole: function 0x7E57A028 multiplies the white
   balance gains by a pair from a five-pair table at 0x7E768DB8 (Pale&Light I 200/256 and 278/256,
   Pin Hole I 250 and 231; the other three pairs belong to their second and third types). The
   values reproduce the gains recorded in the JPEGs. Setting a pair to 256, 256 removes the shift;
   it is table data. **[R]**
4. **A generic mechanism**, built and emulated (§3).

## 3. The mechanism for the four "ready" filters

Per filter, the same six stages as before plus two removals:

| Item | Change | Kind |
|---|---|---|
| Red / green / blue curves | a small stub per slot hands three records to one shared routine | new code, 71 bytes shared by four slots |
| Matrix | one routine tests all fourteen film codes (seven slots, still and movie) | new code, 121 bytes; replaces the three-film routine |
| Brightness curve | all film slots share one copy of the stock table | lookup entries |
| Chroma curves | point at the straight-line set | lookup entries |
| Saturation, per-colour values | each filter's own tables | table data |
| White balance shift | pairs set to 1.0 | table data (8 bytes) |
| Soft Focus blur | the two comparisons that force it no longer match | 2 one-byte values in code |
| Pin Hole vignette, Diorama blur | their effect lookup entries point at "no effect" | lookup entries |

Code lives in the second unused, loaded area (0x7ECB0888, 1,720 of 1,912 bytes used: 192 bytes of
code, the rest matrices, records and two tables). `slots/cave2.s`, `slots/build_slots.py`.

**Emulator results** (stock firmware against the seven-slot patch set):
- matrix choice, 256 filter numbers: 16 changed (the fourteen film codes and Pop Art II's two),
  240 identical, 0 flagged, every row equal to the independent Python model. **[E]**
- curve selection, 917 rows (131 filter numbers × 7 input combinations): 134 changed, 783 identical,
  0 flagged, every row equal to the model (which reads the lookup table, each slot's records and
  the table-picking routine from the image). **[E]**

**Prototype firmware:** `build/seven-slots-neutral.BIN`, sha256
`aeaa8ff0335aac10ee69a1f08ec9b0ad8c05496c2e5caf74bcf7dfdeb6ca5e5b` (a first version, `2800dc25…`, differed only in which tables the new slots use outside raw stills; either is valid for the test). The three films as they are
(Pro 400H with its pending refinement), and the four new slots filled with the camera's own
Natural settings. NOT flashed. Test: develop the test RAW in Pale&Light, Soft Focus, Pin Hole and
Diorama. Each should come out like Natural: no blur, no vignette, normal white balance. That one
flash answers whether the four slots are clean. Films then go in as data only
(`fit_film.py --slot palelight1 | softfocus | pinhole1 | diorama`; tool path checked with a
Vision3 250D fit, `patches/history/film-vision3-250d-pl1.json`).

## 4. Why the other five are different

Their filter numbers are tested by hand in many places (table above). There are two ways to
convert one, neither done:

- **Remove each special case.** Dramatic Tone alone has 27 groups of comparisons in the image
  library. Every one would need to be read, understood and changed. Many small edits in code that
  every photo runs through is exactly the kind of change that introduces instability.
- **Give the menu entry a fresh number.** `art_GetFilterType` (0x7E71BD94) turns a menu entry into
  the filter number. Pointing, say, Dramatic Tone at an unused number that nothing special-cases
  would give a clean slot at once. But the number is also looked up by the menu's own validity
  table (0x7E818CC8; an unknown number is reset to Pop Art), by the record-side tables
  (0x7E8520E0, 0x7E852354), by two movie tables, and by the code that writes the filter name into
  the JPEG. Each needs a new entry. This is menu and recording code this project has not touched;
  the risk is of a different kind (a filter that cannot be selected, wrong metadata, a hang in
  art bracketing), and it is unassessed.

The second route is the promising one. Reading the code further gives a concrete form of it that
needs no new numbers at all:

- **Use the numbers of the hidden second types.** Pop Art II (102), Pin Hole II (106), Pin Hole III
  (108), Pale&Light II (145) and Cross Process II (167) are numbers the whole firmware already
  accepts as art filters, and none has an effect that cannot be removed with the tools of §3
  (their own brightness, saturation and per-colour tables exist; chroma curves, white balance pairs
  2–4 and the two Pin Hole effect entries are data).
- **`art_GetFilterType` returns the number with a `mov` instruction per menu entry.** Grainy Film,
  Gentle Sepia and Dramatic Tone use the two-byte form, so they can take 102, 106, 108; Key Line
  and Watercolor use the three-byte form and can take 145 and 167. Five immediates, no moved code. **[R]**
- **The recording code decides how to handle a picture from a second table, indexed by the menu
  entry** (0x7E8522AC, read by 0x7E70DBDE, which is called from 49 places): Pop Art, Pale&Light,
  Light Tone and Cross Process are kind 1, Soft Focus and Diorama kind 3, the others kind 4. The
  five entries would be set to kind 1, so that all 49 places treat them like Pop Art, the flow the
  films already use. That table is data. **[R]** What kinds 3 and 4 do differently was not read.
- Still open for this route: what else is indexed by the menu entry rather than the number (art
  bracketing, the effect choices offered in the menu); the name written into the JPEG would be the
  hidden type's; movie has its own mapping and would keep the old effects; and the curve tables
  for five more slots must come from somewhere (§5, point 1).

**Built as a second prototype** (`slots/build_slots12.py`, NOTES §33): `build/twelve-slots-neutral.BIN`,
sha256 `987d0f2ed96881b7eb200146b65a96576cd7f55dead0be961bf411d27dab69db`. NOT flashed.

- All twelve visible entries are film slots; the nine without a film hold Natural settings.
- The recording code's "kind" table is left alone (as for Soft Focus, Pin Hole and Diorama in the
  seven-slot build): the five entries keep kind 4 but their numbers no longer have an effect module.
  If that flow misbehaves on the camera, setting the kind to 1 is the fallback.
- Curve tables: Pro 400H is reduced to its three stills tables (its stills output is unchanged
  by construction; the emulator shows the same three tables selected), which frees 21 tables.
- Changed bytes inside stock code, in total: 16 (two for the scene-dependent hue, one range check,
  a five-byte jump, five in `art_GetFilterType`, two for Soft Focus, one counted twice above).
  Everything else is table data or the two new code areas (120 + 320 bytes).
- **Emulator** (stock against the twelve-slot patch set):
  - menu entry → number, 75 cases: the stock mapping matches the model in all; patched, exactly
    seven cases change (Grainy type 1 → 102, Sepia → 106, Dramatic type 1 → 108, Key Line type 1 →
    145, Watercolor type 1 → 167). **[E]**
  - matrix choice, 256 numbers: 22 changed, 0 flagged. **[E]**
  - curve selection, 917 cases: 156 changed, 0 flagged; the twelve slots select 36 different
    stills tables, and Portra, Ektachrome and Pro 400H select the same tables as in the
    three-film build. **[E]**
- Not checkable without the camera: everything the recording, menu, playback and movie code does
  with the changed numbers. Known consequences: the JPEG metadata will name the hidden type
  (for example "Pop Art" for the Grainy Film entry); movie keeps its own mapping, so those five
  entries still apply their old effects in movie mode; the second types of the five effect filters
  (reachable only in ART mode) are unchanged.

## 5. Limits that apply to all slots

1. **Table space is not the limit, under one condition.** A film needs one curve table per channel
   for the path stills use. The four new slots take their twelve tables from the two unused areas
   and from brightness-curve tables that are no longer needed (the slots' own, and those of four
   hidden second types: Pop Art II, Pale&Light II, Cross Process II, Pin Hole II). For twelve slots
   the three existing films would have to give up 21 of their 24 tables each.
2. **Which curve table is used when** (partly answered by reading the code): each curve record has
   eight tables, four columns by two members, chosen by a byte called P+99 here and a flag.
   Raw stills use column 0, member 1 **[C]**. The recording and art code write P+99 = 0xC0 or 0xC2
   for jobs whose input is an already developed image (JPEG from YC, thumbnails, view images, noise
   reduction passes), and movie code writes 5 or a computed value **[R]**; those select the other
   columns. The stock tables of those columns differ from the stills table by 2–4 % on average.
   The new slots therefore use the film's one table for member 1 of all four columns: movie and
   view jobs get the film curve on a slightly different base than stock would use. Member 0 (a
   much flatter stock curve; its user was not found) stays stock. The three existing films carry
   the film curve in all 24 tables. **Still needs a look on the camera** (live view, a movie clip).
3. **One input the new slots ignore:** stock filters that use the default curves switch to an
   alternative default set when a flag (P+87) is set. Filters with their own curves ignore it, in
   stock too; Soft Focus, Pin Hole and Diorama now ignore it as well. What sets the flag is not known.
4. **Hidden second types lose their looks** (they were already not reachable from the quick menu).
5. **Not covered by any test so far:** movie recording and live view with the new code; art
   bracketing; the add-on art effects (frame, star light, white edge) combined with a converted
   filter; the limits the camera places on effect filters (for example drive modes), which stay
   as they are because the tables behind them were not changed.

## 6. Stability assessment

| Kind of change | In the seven-slot build | Risk | How it is checked |
|---|---|---|---|
| Table data in read-only memory | all looks, white balance pairs | low | measured on the camera per look |
| Lookup entries re-pointed to existing code | curves, brightness, chroma, effects | low | emulator (every filter number); camera |
| One-byte compare values | range check, Soft Focus ×2 | low | read; camera |
| New code | 120 + 192 bytes in two unused loaded areas | medium | emulator against a Python model; the first 120 bytes are confirmed on the camera |
| Boot code | none | – | – |

Nothing in it runs before the camera has started, so a fault would show when an art filter is
used, not as a camera that does not boot; reflashing recovers. The first new-code build behaved
exactly as emulated, which is the main reason to trust the second.

## 6a. First camera result (2026-11-12) and the correction

`seven-slots-neutral` on the camera: **live view froze in Soft Focus, Pin Hole and Diorama**;
Pale&Light did not. Those three are the entries the recording code classifies as effect filters.
Removing the effect while leaving that classification was the open risk named in §4, and it is
now shown not to work. The correction classifies the converted entries like the colour-only filters,
in all three places the recording code looks (two tables and a lookup, all data; NOTES §34), and
is checked in the emulator (11 intended changes, 0 flagged).

Corrected builds, NOT camera-tested:
- `build/seven-slots-neutral-b.BIN`, sha256 `da5f1586005315b9363eaa4bf50404902a7b7af7bb67945171bca9c6ccd33838`
- `build/twelve-slots-neutral-b.BIN`, sha256 `eab02461d0af1fe749ed6b703a766dd463b65c7fe9eec80a85c8c75f6d36f78f`

The hashes given for the first versions in §3 and §4 are superseded by these.

## 6b. Second camera result (2026-11-12): the in-place conversion of effect filters fails

`seven-slots-neutral-b` on the camera: Soft Focus, Pin Hole and Diorama **still freeze live view**.
Live view runs through the camera's movie-art code, which has its own hard-coded lists and tables
of effect filter numbers, separate from the still path (NOTES §35). Removing an effect in the
still path leaves live view waiting for it.

**This changes the verdict of §1:**

| Filters | Verdict now |
|---|---|
| Cross Process, Light Tone, Pop Art | Film slots, measured on the camera |
| Pale&Light | Converted in place; a colour-only filter, did not freeze; rendering still to be measured |
| Soft Focus, Pin Hole, Diorama | **Not convertible in place at low risk.** Redone by sending the menu entry to a spare colour-only number (102, 145, 167); built, emulator-checked, not flashed |
| Grainy Film, Gentle Sepia, Dramatic Tone, Key Line, Watercolor | **No route at low risk.** Only three spare colour-only numbers exist and they are used above. Converting these needs the still, live-view and movie paths all edited |

So the supportable answer is **seven film slots**, not twelve. The twelve-slot builds of §4 must
not be flashed: two of the numbers they use (106, 108) are effect numbers and would freeze too.

Current build to test: `build/seven-slots-remap-neutral.BIN`, sha256
`b4d239a714835a96e41fd035c9e4c3fc95aef8a540c81fbe9054147469a791ea`. It changes the same 8 bytes
of stock code as the working three-film build; everything else is table data and the two code areas.

## 6c. Third camera result (2026-11-12): the remap build freezes too

`seven-slots-remap-neutral` on the camera: Soft Focus, Pin Hole and Diorama freeze live view again,
although their own numbers and effects were stock in that build. So sending the menu entry to
another number, or changing the record-side classification, also conflicts with live view.

**Verdict as it stands:** four film slots are supportable: Cross Process, Light Tone, Pop Art
(measured) and Pale&Light (converted in place, never reported frozen, rendering not yet measured).
For the other eight visible filters no working method has been found; three different attempts
on Soft Focus, Pin Hole and Diorama all froze live view. Further attempts need the live-view path
traced first (NOTES §36), not another guess.

Current build: `build/four-slots-neutral.BIN` (three films + Pale&Light with Natural settings; no
effect filter touched).

## 6d. What the stills of the remap build show, and the live-view cause (2026-11-12)

RAW developments on `seven-slots-remap-neutral` (NOTES §37): the Soft Focus entry renders within
0.09 ΔE of Natural (no blur), Pale&Light the same, Diorama within 0.66 (no blur), Pin Hole has no
vignette and differs only by a white balance shift that is also chosen by menu entry. So **for
still photos the remap method works for all three effect entries.**

The freeze is specific to live view, and the cause is now read from dumped tables, not guessed: the
movie / live-view code has its own menu-entry → number tables in two functions, and they still gave
the effect numbers while the art request carried the new ones. `seven-slots-remap2-neutral.BIN`
(sha256 `bf5ee5c1d83bf26779838e3432f2e454283f5591b0b6b252ffff90fc6d17da29`) makes those tables
agree. It is the fourth attempt on these entries and is NOT camera-tested; the two movie-art
functions cannot be run in the emulator.

## 6e. Fourth build on the camera: seven slots work (2026-11-12)

`seven-slots-remap2-neutral`: live view in Soft Focus, Pin Hole and Diorama no longer freezes and
looks normal. RAW developments of the test image in Soft Focus, Pin Hole, Diorama and Pale&Light
are **pixel-identical to each other** and within 0.09 ΔE of Natural (grays identical). The Pin Hole
white balance shift and Diorama's extra stage are gone (NOTES §37.6).

**Verdict:**

| Filters | Status |
|---|---|
| Cross Process, Light Tone, Pop Art | Film slots with films, measured |
| Pale&Light, Soft Focus, Pin Hole, Diorama | **Film slots, confirmed on the camera for stills and live view**; currently empty (Natural settings) |
| Grainy Film, Gentle Sepia, Dramatic Tone, Key Line, Watercolor | No route found: the three spare colour-only numbers are used, and converting an effect number in place means editing the still, live-view and movie paths |

What made the difference: an effect entry cannot be converted by removing its effect. Its **menu
entry** has to be sent to a colour-only number in every place the firmware turns a menu entry into
a number: `art_GetFilterType` and the two live-view tables (and, for movie, two more that were
left stock here).

Not yet tested on this build: an ordinary photo in the new entries, art bracketing, movie.

## 6f. Equivalence check (2026-11-12)

`seven-slots-portra-check`: the measured Portra look written into all four new slots. Developments
of the test image in Pale&Light, Soft Focus, Pin Hole and Diorama are pixel-identical to the
Portra 400 entry (100 % of pixels, maximum difference 0). Every stage, including the matrix and the
per-colour values that the neutral test could not exercise, behaves the same in all seven slots.

## 7. Recommended order (superseded by §6b: test `seven-slots-remap-neutral.BIN`)

Two prototypes exist. Test them in this order, so that a problem can be traced to one change:

1. Flash `seven-slots-neutral-b.BIN`; develop the test RAW in the four new entries, plus Portra,
   Ektachrome and Pro400H as a regression check; shoot one photo, look at live view and record a
   short clip in a new slot (limit 2 above).
2. If clean: choose films for the four slots; fit, flash, one correction round each.
3. Then flash `twelve-slots-neutral-b.BIN` and repeat the test for Grainy Film, Gentle Sepia, Dramatic
   Tone, Key Line and Watercolor (each should render like Natural, with no grain, toning, outline or
   local contrast), plus art bracketing and playback of the saved files.

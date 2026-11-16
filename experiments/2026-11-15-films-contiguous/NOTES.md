# The seven film looks next to each other in every list (2026-11-15)

Owner: "any reason we left a default filter grainy film right in the middle of our new custom films in the
quick menu? feels weird and out of place".

Candidate build `builds/films-contiguous.json` = the pinned build `peaking-fast` + `patches/films-contiguous.json`.
sha256 `78c5b2419e4ac816aa16db6c6e29d36eaac54bd34f326f7c9103924b7dbad33c`. **Not camera-tested. Nothing was flashed.**

Labels: **V** = ran in the emulator or read in the firmware bytes. **I** = inferred. **U** = unknown.

## Result

| Place | Pinned build | Candidate |
|---|---|---|
| 1 to 4 | Portra, Ektachrome, Pro 400H, Kodachrome | the same |
| 5 | Grainy Film | Vis 250D |
| 6 | Vis 250D | Velvia |
| 7 | Velvia | Superia 400 |
| 8 | Superia 400 | Grainy Film |
| 9 to 12 | Gentle Sepia, Dramatic Tone, Key Line, Watercolor | the same |

The number pictures follow the place: the films are ART 1 to ART 7 and Grainy Film is ART 8.

## What fixes the order

Every list has its own tables. None of them is in code, but the ART list page keeps several tables by the
place in the list. All addresses are run-time addresses of block 0 (V: each was turned alone or in a group in a
test image and the screens were looked at).

| List | What fixes the order |
|---|---|
| Live control strip (the quick menu), mode P and movie mode | The value list of the setting Picture Mode (info 111): stored values 0x7E844CC0 (19 × 64 B) with the menu values 0x7E83F70C. Name and picture come from the menu value, so they follow the entry |
| RAW-edit picture mode (info 509, 510) | The same kind of list: 0x7E846F40 / 0x7E83F934 and 0x7E847400 / 0x7E83F980. Where they show: U |
| Shooting Menu 1 → Picture Mode | Rows 14 to 25 of the row table 0x7EFEF4FC (20 B: setting id of the show flag, text id), and the table row → menu value 0x7EFF63EC. The table row → page of the entry (0x7EFF9564: pages 423 to 432, 600, 627) is by place and stays |
| ART BKT list | Rows 72 to 83 of the row table, and the table row → {Off / On page, bracket flag} 0x7EFF9D5C |
| Custom Menu → Picture Mode Settings | Rows 122 to 138 of the row table, and the table row → Off / On page 0x7EFF9314 |
| ART list (ART mode) | The records 0x7EFE8B14 (13 × 44 B: art code, name, pictures, setting ids). The title number is the place |
| Filter Type and Add Effects screen of an ART entry | Eight more tables of the ART list page (code 0x7EDD1C00 to 0x7EDD7200), all read with the place in the list (member +228): rows 0x7EFE872C (30 B), setting ids 0x7EFE8894 (8 B), jump tables 0x7EFE88F4, 0x7EFE89A4, 0x7EFE89D4, 0x7EFE8A04, 0x7EFE8A34, 0x7EFE8A64 |
| ART mode value list (info 281) | 13 art codes at 0x7E849784. No screen follows it (V for the ART list); turned too, so that a step through the values has the new order (I) |
| Number pictures "ART n" | Tables entry → picture number, in many places (strip, ART list, shooting screens). The picture table itself is in block 1: offset 0x2CD024, one pointer per picture number (lookup 0x7ECFF3AC) |
| Icon in the Picture Mode list | The text of the row: `@A045@Grainy Film` (ids 601, 602, 603, 582) |

The first two test images showed two faults that the screenshots of the lists do not show. Both are fixed, and
`scripts/settings.sh` and `scripts/artsub.sh` are the checks for them:

- With only the row table turned, the row "Grainy Film" of Picture Mode Settings and of ART BKT wrote the flag of
  Superia 400 (the row → page tables are by place).
- With only the ART records turned, RIGHT on Vis 250D opened Grainy Film's Filter Type screen (the eight tables).

## Approach

(a) Turn the list entries, keep every stored value. **Chosen.**
(b) Swap what entries 5 to 8 are (art codes behind the stored values 104 to 107). Rejected: it changes the
menu-entry → art-code tables in the still, live-view and movie paths (the tables behind three live-view freezes,
film notes §34 to §37), the classification tables, the EXIF table, and a saved selection would give another look.

With (a) no stored value, art code, setting id or picture-pipeline table changes. For the number pictures the
pointers of the pictures "ART 5" to "ART 8" turn in the picture table (8 sets of 4), so every screen that shows
the picture of an entry shows the new number, with no edit to the tables entry → picture.

## The spec

`patches/films-contiguous.json`, made by `scripts/make_spec.py`: 468 `bytes` ops, 555 bytes. A delta on the
pinned build. No code byte changes (the six jump tables are data; their targets are stock code).

| Block | Edit | Bytes |
|---|---|---|
| 0 | 22 tables: entries of Grainy Film, Vis 250D, Velvia, Superia 400 turn by one place (table above) | 219 |
| 1 | Picture table: 32 pointers (pictures 0xBF/C1/C3/C5, 0xC0/C2/C4/C6, 0x22B–22E, 0x23C–23F, 0x370/38A/38D/38E, 0x4A8–4AB, 0x54B–54E, 0x5EC–5EF) | 64 |
| 1 | 34 languages × 8 texts, one character each: ids 601, 602, 603, 582 (`@A045@` → `@A048@`, `@A046@` → `@A045@`, …) and ids 1653 to 1656 (`ART5` → `ART8`, `ART6` → `ART5`, …) | 272 |

Ids 1653 to 1656 are the short texts of the same four entries in tables keyed by the menu value (0x7EFCA94C,
0x7EFCC9D0) and by the colour-tone number of a picture (0x7EFD13C0). Where they show: U (playback info is I).

Not changed, on purpose:

- Ids 341 to 348 ("ART1" to "ART8", older set) and 1163, 1173, 1186, 1194 (`@A042@Grainy Film` …): no table
  ties them to an entry and no screen shows them (U).
- The label table 0x7EF1F4D6 of the ART BKT rec view (panel GCPnl_Art_Bkt_Rec, index 1 to 19 from data block
  101). Who writes the index was not found (U). If it is the place in the Picture Mode list, the rec view of an
  ART bracket names the four entries wrongly; the fix is the same turn of 4 × 2 bytes there.
- The order in which an ART bracket takes its frames: code (0x7EA7633A, 0x7EA9528D), by stored value. Grainy
  Film stays the fifth frame. Which filters a bracket takes does not change (V: the flags are the same settings).

## Checks (emulator, V unless marked)

Outputs: `build/emu/films-contiguous/` (ignored by git). All with `scripts/run-all.sh`.

| Check | Result |
|---|---|
| `epm2mod make`: free-space check, boot test, update-path test | PASS, PASS, PASS |
| Live control strip, mode P, all 19 values (`new/lc-*.png`, `new/sheet-lc.png`) | Portra … Superia 400 = ART 1 to 7, Grainy Film ART 8, then ART 9 to 12 |
| The same in movie mode (`new/mlc-*.png`) | the same order |
| Shooting Menu 1 → Picture Mode, Picture Mode Settings, ART BKT (`new/sheet-menu.png`) | the new order; the Picture Mode list shows ART 1 to 12 from the top |
| ART list, 12 entries and ART BKT (`new/sheet-art.png`) | title numbers 1 to 12 with the new order, pictures ART 1 to 12 |
| A selection made on the pinned build, state loaded by the candidate: 12 entries in mode P, 12 in ART mode (`stored/sheet-*.png`) | 24 of 24 show the same name. The number picture is the new one |
| The same choice by name on both builds, then the settings states compared (`scripts/settings.sh`): Picture Mode from the menu list, Filter Type II from the menu list's entry page, show flag Off, bracket flag Off, Filter Type II and first effect from the ART list | 71 of 71 pairs byte-equal; no run without a change |
| Filter Type / Add Effects screens of all 12 entries, 15 key steps each, below the title line (`scripts/artsub.sh`) | 180 of 180 equal |
| Menu crawl, shallow, mode P, ART and movie, candidate against pinned | Mode P: 372 screens by name, 12 differ, all Shooting Menu 1 → Picture Mode (`sm1.01.05` to `.16`); 80 Custom Menu screens equal. Movie: the same 12 of 222. ART: 0 of 211 (the Picture Mode row is grey there). Firmware error entries equal. The shallow crawl does not open Picture Mode Settings or ART BKT; the rows above cover them |
| English, German, Japanese, French: Picture Mode list, Picture Mode Settings, ART list, ART BKT (`sheets-new/`) | the new order with ART 1 to 12 in all four; Grainy Film keeps its own name in each language. All 34 languages: static, the generator checks the 8 texts of each and that every other id reads as before |
| A show flag and a bracket flag set to Off on the pinned build, state loaded by the candidate (`hidden/`) | both builds: the strip goes from Superia 400 to Gentle Sepia (Kodachrome to Vis 250D on the pinned build), and the row Grainy Film reads Off in both lists (`scripts/hidden.sh`) |
| Peaking | Static: it forces picture mode 119 and art code 163 (focus-peaking notes §7); neither changes, and the spec touches no byte of the peaking specs (`make` would refuse) |

Not checked: the camera. Live view, a photo, a movie, an ART bracket. RAW Data Edit and playback info (the
emulator has no picture). The super control panel. Five of the eight picture sets were not seen on a screen
(they were found by eye on sheets of all pictures, `scripts/pictures.py`).

## On the camera

Flash: `epm2flash films-contiguous 78c5b2419e4ac816aa16db6c6e29d36eaac54bd34f326f7c9103924b7dbad33c`
Back: `epm2flash peaking-fast 0e8a25b9578b8119b14b4895be7d2a0b70d7315e5e817758699777f0f31d917e`

Before the flash, choose Velvia in mode P.

1. After the flash, mode P. **Expected:** the screen shows ART 6 (it was ART 7). Press OK: the live control
   opens; with ▲▼ go to Picture Mode. The name bar reads **Velvia**: the look you had selected before the flash
   is still selected.
2. Press ▶ step by step. **Expected:** Superia 400 (ART 7), Grainy Film (ART 8), Gentle Sepia (ART 9).
   Press ◀ from Velvia: Vis 250D (ART 5), Kodachrome (ART 4). A film whose name and look do not match = report it.
3. Take one photo in Vis 250D and one in Grainy Film. **Expected:** colour film look, and black-and-white with grain.
4. MENU → Shooting Menu 1 → Picture Mode. **Expected:** after Custom: Portra, Ektachrome, Pro 400H, Kodachrome,
   Vis 250D, Velvia, Superia 400, Grainy Film, Gentle Sepia, Dramatic Tone, Key Line, Watercolor, with ART 1 to 12.
5. MENU → ART (the mode screen) → OK. **Expected:** the same order, 1 to 12. On 8 Grainy Film press ▶:
   Filter Type has I and II. On 5 Vis 250D press ▶: Filter Type has I, II and III (as Pin Hole had).
6. In the ART list go to 13 ART BKT → ▶. **Expected:** the same order. Set only Grainy Film and Velvia to On,
   take one photo: the card gets these two looks. The names in the rec view: write down what they read
   (the unknown above).
7. MENU → Custom Menu → D → Picture Mode Settings (switch the Custom Menu on in Setup Menu → Menu Display).
   **Expected:** Grainy Film is the row after Superia 400. Set it to Off: the quick menu goes from Superia 400
   to Gentle Sepia. Set it to On again.

## Scripts

```sh
.venv/bin/python experiments/2026-11-15-films-contiguous/scripts/make_spec.py           # the spec; --table lists every edit
.venv/bin/epm2mod make builds/films-contiguous.json && .venv/bin/epm2mod make           # candidate, then the pinned build
experiments/2026-11-15-films-contiguous/scripts/run-all.sh                              # every check above
.venv/bin/python experiments/2026-11-15-films-contiguous/scripts/pictures.py build/peaking-fast.BIN build/emu/films-contiguous/pics
```

`shots.sh` (screens), `stored.sh` (saved selection), `artsub.sh` (entry pages), `settings.sh` (settings written),
`cmp_png.py`, `cmp_state.py`.

## Grainy Film as an eighth film (a black-and-white stock, grain kept): what it would take

Not built. Grainy Film I is art code 74 (II: 104): monochrome, its own look curve, and a grain module that reads
a texture from block 2 (`docs/art-filter-slots.md`).

- Keep the code and the module. Then live view, the classification tables and the effect lists stay as they are
  (the freezes of film notes §34 to §37 came from taking a module away). **I**
- Tone: write the film's curve into the entry's look table (512 B, jump table 0x7E78C8E4). Data, method known. **V** for colour slots.
- Spectral response (how colours turn to grey): a matrix for code 74 through the `matrix3` hook, which needs one
  more compare there (a few bytes of code). Whether the matrix acts before the monochrome step: **U**; probe =
  one RAW development with a strong matrix.
- Grain amount and size: parameters of the module (0x7E722B38 and its texture); not decoded. **U**
- A target and a fit: the model has no monochrome path yet; the fit tools take colour targets.
- Name: ids 64 and 601 in 34 languages, as `film-names-all-languages`.

Size: one or two days. First step: develop the test RAW in stock Grainy Film I and II and measure the tone curve.

# Olympus's art filters by default, films loaded at run time (2026-11-18)

The owner's requirement (asked several times; not built until now): the firmware carries Olympus's 12 art filters
unchanged. Films reach the camera only through the looks flow (installer or `looks pack` -> `EPM2LOOK.BIN` -> Custom
Menu J -> Load Looks -> Load), which overwrites the entries the file lists. There is no Built-in (owner, 2026-11-18:
"The original requirement is the firmware comes with default Olympus filters, and we can overwrite them with looks.
I'd drop this feature entirely"). The test is that exact workflow: flash -> the 12 stock filters -> load films.

Labels: V verified, I inferred, U unknown.

## Criteria (agreed 2026-11-17, `experiments/2026-11-17-installer/design.md`)

- F1. After the flash, all 12 entries are Olympus's art filters.
- F2. Loading a film changes only that slot.
- ~~F3. Built-in brings back the stock filters~~: dropped by the owner, 2026-11-18. The Load Looks row is Off / Load.
- F4. Every existing criterion holds (card-looks criteria 1-13, the Debug Log, peaking, interval, level gauge).
- F5. Movies and ART bracket behave as stock, or as the loaded film, slot by slot.

## How the film firmware changes the filters today (inventory, `scripts/inventory.py`)

The film specs of `builds/log-menu.json` change 26.7 KB of stock bytes and add 2.9 KB in free space:

| Spec | Free space | Stock bytes | What the stock bytes are |
|---|---|---|---|
| `remap7b-code` | 857 B | 139 B | per-art-code stage tables (0x7E78xxxx), menu entry -> number tables of live view (0x7E7FF05C, 0x7E807880), `art_GetFilterType` (0x7E854A24), record kind (0x7E8522xx), white-balance pairs (0x7E768DB8), and two code sites: the matrix hook 0x7E56C6A5, the range check 0x7E56B7A7 |
| `seven-fixes-1` | 16 B | 26 B | stage tables, and 3 code bytes 0x7E71BDDB / F1 / 0D (the type II codes select type I) |
| `seven-movie-1` | 26 B | 18 B | the movie entry -> number tables (0x7E7FF008, 0x7E80782C) |
| `seven-structure-extra` | 0 | 857 B | identity look tables for Cross Process I, Light Tone, Pop Art I; Light Tone's tone-curve handler |
| `seven-films-5` | 1,089 B | 20,256 B | the film tables written over the tables of the first seven filters |
| `xp-adaptive-hue-off` | 0 | 2 B | code: Cross Process's scene-adaptive hue |
| `films12-structure` | 784 B | 178 B | table entries of the hidden art codes and hidden stored values |
| `films12cl-looks` | 83 B | 5,131 B | film tables in look tables of codes no entry reaches |
| `films12-entry-*` x 5 | 0 | 13 B each | the entry's stored value: Picture Mode value lists (data) and immediates in code (ART bracket 0x7E5A774C / 0x7E5A7B6E, 0x7EA76517, 0x7EA9545D: `cmp 119` / `mov 119` for Key Line) |
| `seven-labels`, `films12bw-names` | | block 1 | the menu names (the loader already writes names in RAM) |

All of these are in segments that the boot copies into RAM (V for segments 1 to 3). Look tables are written at run
time by the loader today (camera-tested, card-looks-4).

## Design

1. **Flashed always:** what sits in free space and what only the film routes reach (new code, film tables, the hidden
   codes' structure, look tables of unreachable codes). Check: with no film loaded, the image behaves as stock for
   every stock entry (emulator cases `filter_type`, `art_kind`, `matrix_choice`, `gamma_select`: 0 changed rows for
   stock values and codes; menu crawls equal to the stock-filter build).
2. **Switched at run time, per entry, by the loader:** every stock data byte that the film firmware changes for that
   entry (routing words, WB pair, tables). The loader keeps the stock bytes (the snapshot of card-looks) and writes
   the film bytes for the entries the file lists. A load is the whole state: an entry the file does not list gets its
   stock bytes back (the installer always writes the user's whole choice). With all 12 entries loaded the RAM equals
   the camera-tested film firmware; with none, it equals the stock firmware.
3. **No code is changed at run time.** CPU 0 and CPU 1 cache code, and the cache has no ranged flush (CHCTR 0x8070,
   caduceus review 06). A code site whose immediate the film firmware changes gets a flash-time hook that reads the
   entry's current value from a RAM table; with the stock value in the table it does what stock does.
4. **Shared bytes** (used by several entries, e.g. the matrix hook and the range check) stay flashed when the check
   of point 1 shows them transparent for stock codes; otherwise they move into the per-entry switch.
5. **The stored Picture Mode setting:** an entry that switches between its stock value and a hidden value must not
   leave the camera's Picture Mode setting (settings 509 / 510, the ART mode code) on a value that no longer exists.
   The loader maps the current setting along with the entry (U: which settings hold the value; read from the
   inventory of films-max section 5a).

## Owner's decisions (2026-11-18)

- F5 in full: "whatever should be the expected behavior for a user should be the proper behavior, nothing confusing or
  an unintentional artifact of the mod". ART bracket and movies use the loaded film of an entry, as stills and live
  view do; an entry without a film is the stock filter everywhere.
- `log-menu` pinned meanwhile; this project starts from it.

## Finding: art codes (2026-11-18, emulator, `tools/emu/emurun.py run filter_type` on stock)

`art_GetFilterType` on stock firmware, stored value -> art code for Filter Type I / II / III:

| Value | Entry | I | II | III |
|---|---|---|---|---|
| 100 | Pop Art | 70 | 102 | - |
| 101 | Soft Focus | 69 | 69 | 69 |
| 102 | Pale&Light Color | 71 | 145 | - |
| 103 | Light Tone | 72 | 72 | 72 |
| 104 | Grainy Film | 74 | 104 | - |
| 105 | Pin Hole | 73 | 106 | 108 |
| 106 | Diorama | 86 | 86 | 86 |
| 107 | Cross Process | 85 | 167 | - |
| 108 | Gentle Sepia | 91 | 91 | 91 |
| 109 | Dramatic Tone | 96 | 165 | - |
| 119 | Key Line | 163 | 169 | - |
| 120 | Watercolor | 181 | 182 | - |
| 110-118 (hidden) | none | 145, 75, 84, 69, 117, 118, 119, 151, 153 | | |

- The film firmware sends Soft Focus, Pin Hole and Diorama to the codes 102, 145 and 167, and makes Pop Art II,
  Pale&Light II and Cross Process II select their type I code (`seven-fixes-1`) so that those codes are free. With
  the stock filters kept, Filter Type II of these three filters must work: **102, 145 and 167 are not free.**
- Free colour-only codes that no stock entry or type reaches: 94, 98, 144, 156, 159 (films-max section 3.2), which
  the five hidden-value entries use. **Soft Focus, Pin Hole and Diorama need three more**, for F2 (each entry
  switches alone).
- Pop Art, Pale&Light, Light Tone and Cross Process are colour-only filters: a film goes into their own codes' tables
  (as today); a later load without that entry puts the stock tables back. With a film in such an entry, its type II / III must give the
  film too (the entry shows one film), so the loader also routes II / III to the type I code, and a later load without the entry puts the
  stock route back.

Candidates for the three codes (films-max section 3.3): code 92 (8 compare sites not read yet), or codes above 184,
which miss every stage table: each of the five table stages (gamma 0x7E56B7A6, look 0x7E56E84D, saturation
0x7E56DC78, six-axis 0x7E56D2AB, chroma 0x7E5662E2) needs a hook with a table of its own (about 150 B), and the
record and movie-art range tests (69-183) must accept the code (U).

### Code 92 and codes outside the tables (2026-11-18)

- Code 92: the stock image has 59 `cmp 92` instructions (`build/map/linear.txt`). The 9 in the image library and the
  movie / record code (0x7E5C8138, 0x7E5C8940: path characters; 0x7E66B7CC / 80A / 826: coordinate ranges;
  0x7E700859 / 8C7 / 953: loop counts) do not test an art code. films-max named "8 compare sites" without a list; no
  site that reads the art code byte compares 92 (films-max 5a, kind B: the 37 compares are of stock codes). So 92 is
  a candidate (I), not verified: the dynamic reads through pointers (films-max 5a b) are the gap.
- Codes 75, 84, 117, 119: compared in the image library (films-max 3.1): not clean.
- Codes above 184 (films-max 3.3): no table has an entry, so each of the five table stages needs a hook that loads
  the slot's own handler (about 150 B). The hooks are in the image library (segment 1). Code reached only through
  the image-job table may jump to segment 2 (the allowed remap7b-code hook, `tools/emu/hookcheck-allow.tsv`); the
  same argument for the five stage selectors is I and must be checked. The record and movie-art code tests the
  range 69-183 (U how a code outside it is treated: as "no art", the plain path, would be right for a colour-only
  film). Probe: one hidden-value entry with code 200 in the live-view rig (`experiments/2026-11-16-films-max/scripts/
  scen_films.py`), then on the camera with the Debug Log (capture, movie, ART bracket: films-max 5a c).

Plan for the three entries: code 92 for one if the dynamic reads show nothing, codes above 184 for the others; or
all three above 184 with one mechanism.

### Choice for the three effect entries (2026-11-18)

Codes 75 / 125 and 92, all inside every stage's table range (gamma 71-170, look 8-184, saturation 69-184, six-axis
9-184, chroma 69-168: the range tests at 0x7E56B7A6, 0x7E56E84D, 0x7E56DC78, 0x7E56D2AB, 0x7E5662E2), so the 18 range
tests 69-183 / 184 of the record and movie-art code do not matter.

- 75 / 125: reached in stock only through the hidden value 111 (no menu entry stores it). Compared after a read of
  the art code at four job-block sites (0x7E54B52E, 0x7E54B5F3, 0x7E54BF5C, 0x7E54BF67: a flag-dependent extra step);
  in no hash table, in no compare cluster, not in the effect lists. At flash time these four compares get an
  immediate that no byte matches (-1). Stock never produces 75 or 125, so this changes no stock filter (I, by
  reachability; `filter_type` above).
- 92: no compare of the art code found (static: films-max 5a kind B; the 59 `cmp 92` of the image are other values).
- Codes 84, 117, 119 (with 121, 123, 124) are in the monochrome / Dramatic / Watercolor groups of the hashes 0x7E74A568
  and 0x7E78B29C and in several compare clusters: more to neutralize; not used. 95 and 161: their only tests sit next to
  shooting-mode codes on a value that may not be the art code; not used.

### The three mechanisms

| Entries | Stored value | Art code with a film | What the loader switches | What is flashed |
|---|---|---|---|---|
| Pop Art, Pale&Light Color, Light Tone, Cross Process (colour-only filters) | stock | the entry's own type I code (70, 71, 72, 85), all types | the film tables over the stock ones; the code's stage words (tone stub, look, chroma, matrix flag), the WB pair, Cross Process's adaptive-hue flag; type II / III routed to type I | the matrix chain and a hook for the adaptive hue that read RAM flags |
| Soft Focus, Pin Hole, Diorama (effect filters) | stock | 75, 125 and 92, all types | the value's routing words (art_GetFilterType, the two live-view functions' still and movie tables, record kind, EXIF, "is art") | the codes' stage entries, stubs and handlers with own tables; the 75 / 125 compares neutralized |
| Grainy Film, Gentle Sepia, Dramatic Tone, Key Line, Watercolor (value-tested filters) | hidden 111, 112, 114, 115, 118 | 94, 98, 144, 156, 159 (as films-12) | the stored value: the three value lists, the three "is art" lists, the ART-mode preset; the current Picture Mode setting; the ART bracket constants through a hook | the hidden values' and codes' structure (films12-structure) with own tables |

Own tables: films-12 borrowed stock tables of Pin Hole I / II / III, Diorama and code 153, and 15 tone tables that no
record used once remap7b had freed them. In the stock base those belong to stock filters, so the film codes get
their own tables in the RAM gap (written by the loader from the look file, like the live-view tables of card-looks-4)
and stubs or handlers in free space that point at them.

Hooks from the image library into segment 2 follow the allowed remap7b-code case (`tools/emu/hookcheck-allow.tsv`):
code that only image jobs reach runs after segment 2 is loaded. Each new hook needs that evidence.

### One mechanism for all 12 entries (2026-11-18, replaces the three rows above)

Each entry has one film code. Its film tables are in RAM (a block of 0x2000 bytes per entry at 0x7E4D8000: stills
tone tables, live-view tone tables, saturation, six-axis, chroma record, matrix), written by the loader from the look
file. The flashed structure gives every film code a tone stub with its own three records, and saturation, six-axis and
chroma stubs that point at its RAM block. **A film never writes over a stock table, so nothing has to be restored.**
Loading an entry = writing a list of words (address, film word); an entry without a film gets the list's stock words
(known at build time). The lists are generated from the stock image.

| Entry | Value | Film code | Switched words besides the stored value |
|---|---|---|---|
| Pop Art | 100 | 79 (its stock movie code: key 9 in the tone hash, no range-test change) | stage entries of 79; value 100's routes (all types and movie to 79) |
| Soft Focus | 101 | 75 | value 101's routes |
| Pale&Light Color | 102 | 71 | stage entries of 71; value 102's routes; WB pair of 71 -> 1.0 |
| Light Tone | 103 | 72 | stage entries of 72; value 103's routes |
| Grainy Film | 104 -> 111 | 94 | the stored value (lists, preset, ART bracket hook, current setting) |
| Pin Hole | 105 | 92 | value 105's routes |
| Diorama | 106 | 125 | value 106's routes |
| Cross Process | 107 | 85 | stage entries of 85; value 107's routes; the adaptive-hue flag |
| Gentle Sepia | 108 -> 112 | 98 | the stored value |
| Dramatic Tone | 109 -> 114 | 144 | the stored value |
| Key Line | 119 -> 115 | 156 | the stored value |
| Watercolor | 120 -> 118 | 159 | the stored value |

The matrix chain (hook 0x7E56C6A5) reads a matrix pointer per in-place code from RAM (0 = the stock path); the film
codes 75, 92, 125, 94, 98, 144, 156, 159 always use their RAM matrix. For a code that has no tone-hash entry in stock,
a flashed entry with the stock default handler as target is added; the loader switches only the target word.

## Build log

- 2026-11-18, item 1 (`scripts/mkspec_structure.py` -> `patches/stock-films-structure.json`, 103 operations; the
  loader's switch lists in `build/stock-films/layout.json`): stubs 861 B at 0x7EE53830 (segment 3, where card-looks-4's
  code ran), the shared tone part, the chroma helper and the matrix chain at 0x7ECB0888, records 1,296 B at 0x7EE541B4.
  Switch lists: Pop Art 11 words, Soft Focus 6, Pale&Light 13, Light Tone 11, Pin Hole 6, Diorama 6, Cross Process 11,
  each hidden entry 7 bytes (the value lists, the "is art" lists, the ART-mode preset).
  F1 in the emulator, stock against stock + the structure (`tools/emu/emurun.py diff`): `filter_type` changes only the
  hidden values 111, 112, 114, 115, 118; `art_kind` only 115, 118; `gamma_select` and `curve_select` only the film
  codes 75, 92, 125, 94, 98, 144, 156, 159; `six_handler` nothing; the matrix chain (all 256 codes, stock against
  patched without the case's model) only the eight film codes. The in-place codes 71, 72, 79, 85 are stock until the
  loader switches them; their RAM matrix pointer counts only when it holds the exact film address (RAM in the gap
  is not reliably zero at a start: the log ring survived power-offs).

- 2026-11-18, item 2 (`scripts/mkspec_loader.py` -> `patches/card-looks-5.json`, `patches/looks-menu-4.json`): the
  card-looks-4 assembly with no snapshot, no live tables and no Built-in; APPLY into each listed entry's RAM block
  (one operation list for all entries, 8 tone tables per channel); MASK and SWITCH (words written as words); the
  Picture Mode remap in T_GUI after a switch. The structure moved to segment 2 (stubs 435 B at 0x7EBF38BC, shared part
  and stubs 707 B at 0x7ECB0888); RAM blocks 0x7E4CA000-0x7E4EF800 (0x3200 each).
  `builds/stock-films.json` = the feature specs + looks-menu-4 + stock-films-structure + card-looks-5 + log-menu-2
  (`mkspec_logmenu.py --stock-films`). `epm2mod make`: free space PASS, boot-test PASS, update-path-test PASS, sha256
  `258f8be64526dd1813e2b333c21381434554184e64e1c8fa4a5e829fd3c673fc` (19,217 bytes changed). Not yet: the ART
  bracket hook, Cross Process's adaptive-hue hook, the functional emulator sessions.

- 2026-11-18, emulator sessions (`scripts/emu_stock.py`, six sessions on one flash state): the switch words, the
  listed entries' RAM blocks, the names and the row status equal the model in every state: nothing stored (all
  stock); Load of the 12 default films (all film; "Pro 400H" on ART 3); restart from flash (applied at start); Load of
  Velvia in Pop Art and C200 in Key Line (only those two film, ART 3 "Pale&Light Color" again); Load of a file with no
  film (all stock); a damaged file (refused, unchanged). The first run found the entries' RAM blocks overlapping the
  loader's names at 0x7E4D0000 (a fault in the names code): the blocks start at 0x7E4D1000 now. sha256
  `3d7d80781886cdbc76d333bdafff6848bdb7f6ce18d131b102dfb8fd3cc15f83`.

- 2026-11-18, the hooks and the Picture Mode (sha256 `2859767da0014bcb637ca3016898c940f7678d244794d3d5bb231c7e8c0ba8cd`):
  - ART bracket: 30 hooks at the five hidden entries' constants in the two menu list builders (0x7EA7633A,
    0x7EA9528D) and the frame composer (0x7E5A75AE): a compare skips the entry at its stock or hidden value; a value
    load takes the entry's byte of the value list of info 111 (stock or hidden, as the loader switched it). No flag.
    The routines are in 24-byte slots of free runs of segment 2 (osd-battery's runs are left free).
  - Cross Process's adaptive hue: hook 0x7E546160; off only while the entry's matrix pointer holds the film address.
  - No replaced instruction of the 32 hooks is a branch target (`mkspec_log.branch_targets_inside`). The six
    segment-1 hooks are in `tools/emu/hookcheck-allow.tsv` (image job and ART bracket capture only; boot-test and
    update-path-test pass).
  - The Picture Mode: after a Load, the info ids 111, 509, 510 that hold an entry's stock value while the entry has a
    film take its hidden value, and the other way round (Get_CameraInfo 0x7E67F822, Set_CameraInfo 0x7E67F882, in
    T_GUI). Emulator, the stored value (prm tag 0x9481) at the next start: Key Line selected, C200 loaded into Key
    Line -> 115; a file with no film -> 119. Two dead ends on the way: the GUI's getSetting(111) is another
    numbering (it gave 19), and a remap at every start changed the boot (boot-test failed): the remap runs after a
    Load only.
  - The six sessions of `emu_stock.py` pass on this build; crawls P and ART against stock: every art-filter screen
    equal (ART list, Picture Mode lists, quick menu); only the mod's rows differ (Custom Menu A and J, Shooting Menu
    2's Time Lapse Settings).

- 2026-11-18, tables against the film firmware (`scripts/equal_tables.py`, `scripts/loaded_image.py`): after a Load of
  the 12 default films (the file of `looks pack` with no choice, sha256 `5d5df335…`), every entry's saturation,
  six-axis, matrix and chroma values and its stills tone tables (all 8 per channel for Light Tone and Cross Process)
  are byte-equal to the tables of the camera-tested film firmware `log-menu`: 12 of 12 entries. Live view: the film
  firmware's member-0 tables of the ten three-table slots were interpolated (within 8 codes); here each is the curve
  read at its stock default, as the record slots always did.

- 2026-11-18, live view (`experiments/2026-11-16-films-max/scripts/scen_films.py`, the firmware's own live-view tasks,
  3 frames without and 3 with the peaking request):
  - all 12 films loaded (`loaded_image.py`), the stored values 100, 101, 102, 103, 105, 106, 107 and the hidden 111,
    112, 114, 115, 118, and 119: a picture in every frame, no anomaly, peaking lines (pass 9 gain 0x0200) in every
    case. Code byte: Pop Art 79, Soft Focus 75, Diorama 125, Pin Hole 0 (code 92: the new codes read 0 in this rig,
    films-max). The rig's "expected" codes are those of the film firmware.
  - nothing loaded, the stock values: equal to the reference build with the mod's features and no film part
    (`nofilm`): Soft Focus 69, Pin Hole and Dramatic Tone no picture, Diorama an error report and no picture,
    Watercolor a write to a freed block, in both: limits of the rig with the stock effect filters, not changes.
- 2026-11-18, the other features and the unloaded bytes (same sha256):
  - `scripts/features_same.py`: interval (guard, selector, start, movie guard, frames step and editor, shot done) and
    the menu-row cases (help, child, value) give the same results on `log-menu` (pinned) and `stock-films`: ALL SAME.
  - The Debug Log sessions of `log-menu` (`run_logmenu.sh`) on `stock-films`: the same results.
  - `scripts/unloaded_vs_stock.py`: every byte the film part changes in the image, with nothing loaded, is free space,
    a switched word that holds its stock bytes, a film-code or hidden-value table entry, a new tone-hash key, a hook
    or the task entry, the 75/125 compares, the Load Looks row list or a block-1 text: ALL BYTES EXPLAINED.
- The emulator gate is complete: build checks, six sessions, Picture Mode remap, stock-vs-build crawls, the stage
  cases, the tables against the film firmware, live view, the other features, the unloaded bytes. Next: the camera run (`docs/camera-log.md`).

## Open questions (settle in code and the emulator before any camera run)

- U0. Three more colour-only art codes for Soft Focus, Pin Hole and Diorama (above).
- U1. Which shared bytes are transparent for the stock codes (point 4).
- U2. Every code site of the hidden entries (5 x about 6) and of xp-adaptive-hue / seven-fixes: hook or leave stock,
  and what a stock ART bracket gives for a film entry (F5).
- U3. The settings that hold a Picture Mode value (point 5).
- U4. Live view freezes came from entries whose live-view and still paths disagreed (film notes sections 34-37): the
  switch must write every routing table of an entry in one step, while the GUI is not developing a frame (the
  loader runs in its own task; the switch happens at the first GUI state and in the menu, as today).

## Steps

1. Inventory per entry (which bytes belong to which of the 12 entries, which are shared): `scripts/inventory.py`.
2. The stock-base build: the mod features with the film parts of point 1 only. Emulator: F1 (all stock rows equal).
3. The loader's slot table extended with the routing bytes per entry; the hooks of point 3; the setting mapping.
4. Emulator: load each film into each entry alone (F2), all 12 (RAM equal to the film firmware), a file with no film
   (RAM equal to stock in every switched region), crawls P and ART, boot-test, update-path-test, hookcheck.
5. One camera run of the exact workflow, with the Debug Log On.

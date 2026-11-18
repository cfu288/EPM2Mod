# Olympus's art filters by default, films loaded at run time (2026-11-18)

The owner's requirement (asked several times; not built until now): the firmware carries Olympus's 12 art filters
unchanged. Films reach the camera only through the looks flow (installer or `looks pack` -> `EPM2LOOK.BIN` -> Custom
Menu J -> Load Looks -> Load). **Built-in** brings back the 12 stock filters, effects included, with no file and no
flash. The test is that exact workflow: flash -> the 12 stock filters -> load films -> Built-in -> the 12 stock
filters again.

Labels: V verified, I inferred, U unknown.

## Criteria (agreed 2026-11-17, `experiments/2026-11-17-installer/design.md`)

- F1. After the flash, all 12 entries are Olympus's art filters.
- F2. Loading a film changes only that slot.
- F3. Built-in brings back the stock filters, effects included.
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
   the film bytes for the entries the file lists. **Built-in writes the stock bytes back: after it, the RAM of every
   switched region equals the stock firmware, so the stock filters come back by construction (F3).** With all 12
   entries loaded the RAM equals the camera-tested film firmware.
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
  (as today) and Built-in puts the stock tables back. With a film in such an entry, its type II / III must give the
  film too (the entry shows one film), so the loader also routes II / III to the type I code, and Built-in puts the
  stock route back.

Candidates for the three codes (films-max section 3.3): code 92 (8 compare sites not read yet), or codes above 184,
which miss every stage table: each of the five table stages (gamma 0x7E56B7A6, look 0x7E56E84D, saturation
0x7E56DC78, six-axis 0x7E56D2AB, chroma 0x7E5662E2) needs a hook with a table of its own (about 150 B), and the
record and movie-art range tests (69-183) must accept the code (U).

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
4. Emulator: load each film into each entry alone (F2), all 12 (RAM equal to the film firmware), Built-in (RAM equal to
   stock in every switched region: F3), crawls P and ART, boot-test, update-path-test, hookcheck.
5. One camera run of the exact workflow, with the Debug Log On.

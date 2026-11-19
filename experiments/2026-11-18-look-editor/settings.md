# Look editor: dormant settings for the menu rows (2026-11-18)

Question: how many camera settings can hold a look-editor value while the menu is open, with no stock code that
reads or writes them, so that a change does not change camera behaviour? The editor needs about 15.

Labels: V camera-verified, E emulator-checked, R read in code or bytes, I inferred, U unknown.

A "setting" is an info id (the id that a menu row and a list descriptor name). Each info id maps to a prm tag (the
store). The panel side (one list panel per row, pickers with -7..+7) is in [rows.md](rows.md).

## Short answer

- **23 free settings pass every check**, with no build using them (list below). 3 more pass the same checks but
  are already used: 447 (Debug Log), 449 (Load Looks), 458 (Peaking). 15 rows fit (R + E).
- Each one holds any value of its storage type. A u8 holds 0..255, so -7..+7 is stored as 0..14 (or as the s8 byte).
  The mode controller does not check a value against its list when it stores it (R, 0x7E7070B4). The GUI's
  setSetting stored 14 into 448, whose list is Off/On only (E).
- No stock code reads or writes them in boot, the menus, INFO, half-press, playback, or a change between P, ART and
  iAUTO (E). A full reset (Setup → Reset → Full) writes their defaults (R). That is harmless, because the look store
  holds the real values.
- Blocker: the setting side is solved. The open problem is the panel side: each row needs its own list panel, and
  only 6 stock panels for dormant settings exist (see "Pickers" and [rows.md](rows.md)).

## Method

| Check | How | Tool |
|---|---|---|
| Constant-id call sites | prm get/set, Get/Set_CameraInfo (+User), GUI getSetting/setSetting with a constant id or tag | `../2026-11-08-feature-map/sections/07-settings.tsv` columns 8-15 (all 0) |
| Mode-controller tables | value lists (505 records), operation records with hooks (250), conflict rules (92) and their conditions, dependency table (86), 25 bank lists, restore lists A/B, standard reset (300), full reset (881), boot reset (16), resets of 2 and 3 ids, mode presets, region defaults, composite lists | `scripts/settings_scan.py` → `out/scan.tsv` (layouts from feature map 13e §2-3) |
| GUI list descriptors | a scan of 0x7EF00000-0x7F030000 for `{setting, count, 0, 1, items}` (166 found) | same script |
| Runtime access | hooks on prm_get 0x7E457C75, prm_get2 0x7E6803BC, prm_set 0x7E457CED, Get/Set_CameraInfo, User, Bank and W variants, mcon get/set and its 5 writers, Set/Get_CameraInfo_Simple, GUI getSetting/setSetting; also a poll of each stored value every 20 ms | `scripts/trace.mjs` on `stock` |
| Holds a value | write 9 into the current and user values, then boot, menus, mode changes, restart with RAM kept and from flash only. Also turn a stock setSetting(281, 70) into setSetting(448, 14) | `trace.mjs` steps `poke:9:user`, `GUISWAP=281:448:14` |

A raw search for the ids and tags as 16-bit values in block 0 (`scripts/raw_refs.py`) gave hundreds of hits for
each id, mostly instruction bytes. It does not prove anything, so the conclusions do not use it.

The emulator needs Node 26; `OM_EMU_NODE=/path/to/node26/bin/node` for `tools/emu/emu-run`.

## Candidates

All are in the MODE bank (saved with the settings), unless marked otherwise. "Tables" = mode-controller lists
that name the id. "Boot" = written at start in stock (E).

### Tier 1: no stock reference at all, value held through every test (R + E)

| Id | Tag | Type | Default (mcon) | Stock value list | Stock picker panel | Tables | Boot | Note |
|---|---|---|---|---|---|---|---|---|
| 448 | 0xD7A1 | u8 | 1 | 0, 1 | panel 609, descriptor 0x7F00BFDC | full reset | no | EVF Info Settings (I). Free. GUI setSetting stored 14 (E) |
| 446 | 0xD781 | u8 | 1 | 0, 1 | panel 607 is now Peaking's | full reset | no | EVF Info Settings (I). The setting itself is free |
| 442 | 0x6901 | u8 | 0 | 0, 1 | descriptor 0x7F00BCEC | full reset | no | meaning U |
| 451 | 0xD7D1 | u8 | 0 | 0, 1 | none | full reset | no | next to the EVF block |
| 697 | 0xD741 | u8 | 24 | none | none | none | no | |
| 698 | 0xD761 | u8 | 24 | none | none | none | no | |
| 37 | 0x8461 | u8 | 0 | none | none | full reset | no | GUI setSetting stored 14 (E) |
| 293 | 0x5061 | u8 | 60 | 0, 20 … 100 | none | full reset | no | |
| 402 | 0x6281 | u8 | 0 | none | none | full reset | no | |
| 550 | 0x8471 | u8 | 1 | none | none | full reset | no | |
| 583 | 0x8A51 | u8 | 0 | none | none | none | no | |
| 593 | 0x94D1 | u8 | 0 | none | none | full reset | no | |
| 621 | 0x9821 | u8 | 0 | none | none | full reset | no | |
| 653 | 0x9F11 | u8 | 0 | none | none | full reset | no | GUI setSetting stored 14 (E) |
| 660 | 0x9F91 | u8 | 0 | none | none | full reset | no | |
| 632 | 0x9D39 | s8 | 0 | none | none | full reset | no | signed: -7..+7 as is |
| 633 | 0x9D49 | s8 | 0 | none | none | full reset | no | signed: -7..+7 as is |
| 531 | 0xE061[0] | u8 | 0 | none | none | none | no | shares the tag with 532 |
| 528 | 0xDFF2[0] | u16 | 513 | none | none | full reset | no | shares the tag with 529 |
| 558 | 0x8652 | u16 | 2000 | none | none | full reset | no | |
| 559 | 0x8662 | u16 | 2000 | none | none | full reset | no | |
| 487 | 0xDE64 | u32 | 0 | none | none | none | no | |
| 488 | 0xDE74 | u32 | 1 | none | none | none | no | |

Already used by EPM2Mod builds, same profile: 447 (0xD791, Debug Log, panel 608), 449 (0xD7B1, Load Looks,
panel 610), 458 (0x8971, Peaking).

On stock, the start does not write 449: the value 9 stayed through two restarts (E). The start write of 449 seen with
`card-looks` (`../2026-11-17-card-looks/design.md`) is therefore not from stock code (I).

### Tier 2: same static result, weaker runtime evidence

| Id | Why lower |
|---|---|
| 529 (0xDFF2[1]), 532 (0xE061[1]) | second element of a tag above. Not in the runtime trace (R only) |
| 618 (0xA001, CPRAM) | cleared to 0 at every start (E). Holds a value while the camera is on, which is all the editor needs |
| 10002-10123 (about 100 ids, full reset only) | no constant reference (R). setSetting(10111, 14) stored 14 (E). Ids above 700 have no user value (0x7E67FC78 drops them, R), so a mode change does not copy them back. Meaning unknown; families of ids (10021-10040, all u16 512) look like table-driven use (I) |
| 15003-15128 (the 63-element arrays 0x5F01 and 0x5F11) | no constant reference, not touched in the trace (E). Arrays of 63 are very likely read with a computed id (I) |

### Rejected

| Id | Reason (label) |
|---|---|
| 30, 286 | boot reset list 0x7E84D830: rewritten at every start (E, R) |
| 699, 700 | set to 0 at every start through Set_CameraInfo_Simple (E) |
| 108 | the shooting mode: 3 in P, 70 in ART, 7 in iAUTO (E) |
| 450 | bank lists, standard reset, restore lists: one value per mode bank (R, E) |
| 452, 453 | they have -7..+7 lists, but a custom writer (op slot +52) changes the display at every write (R) |

## One wide setting for several rows

No, not without new code. A row writes the whole value of its setting (setSetting(id, item value)), and the row
shows the whole value (R, rows.md). Two rows on one u16 or u32 setting overwrite each other. Code can hook
setSetting and getSetting for one id and split the value into 4-bit fields. That hook could also keep all values in
RAM, without a setting at all. So a wide setting brings no gain (I).

## Binding rows to stock settings of unused features

Not recommended. The art-filter and Picture Mode settings (for example Contrast 117-127, i-Enhance Effect 300, the
ART options) are in the mode presets (ART has 103 entries), the bank lists and the conflict rules. Many have
operation hooks that copy them into the image settings (R, 13e §3.2). Their ranges are -2..+2 or 3 steps (R,
rows.md). Risks:

- a mode change or Myset load rewrites the value;
- the value changes the picture when the user picks that mode or filter;
- the stock menu shows the edited value under the stock name.

The 23 free settings above make this unnecessary.

## Limits of the evidence

- The runtime trace sees only the hooked functions. A direct RAM read of a setting is not seen. The static scan sees
  only constant ids. A table-driven read with a computed id is possible and not proven absent (U). The ids in Tier 1
  are in no mode-controller table except the full reset, which lowers that risk.
- Not run: an attached accessory EVF (446-451 are "EVF" settings, I), Wi-Fi/PTP, a flash, a full reset, movie
  recording, a real shot (`E101_TAKEFAKE` faulted at start in ART, a stand-in fault).
- The smallest camera probe: one row on 448 with a -7..+7 list, set +7, change modes, take a photo, and compare a
  photo with the row at 0. Pass if both photos are equal and the row still shows +7.

## Files

- `scripts/settings_scan.py`: table scan → `out/scan.tsv` (one line per info id).
- `scripts/trace.mjs`: runtime trace, pokes and setSetting swaps (`CANDS` from `out/cands.sh`).
- `scripts/raw_refs.py`: the raw 16-bit search (not used for conclusions).
- Traces: `out/trace-*.txt` (boot, menus, mode changes, restarts, swaps).

# Film name in EXIF, ArtFilter Off, identity look (2026-11-20)

Build `data/builds/films-look-exif.json` = `gauge-info-3` with `stock-films-structure-2` and `card-looks-6` in place of
`stock-films-structure` and `card-looks-5`. Made by `gen/stock-films/structure.py --v2` and `loader.py --v2`; the old
specs regenerate byte for byte. sha256 `af4bcb38df908c3d29b3ef028059a3142cbecc4b66737f7bb2cc2848d6a4bcf4`.

Labels: V verified (firmware or emulator), I inferred, U unknown.

## 1. Identity look for every film (structure-2)

- Fault (V, found by the tone-fault check of 2026-11-20, camera-measured): the film codes' look entry was
  `slots.IDENTITY_LOOK_HANDLER` 0x7E56E94A, which is Cross Process I's handler (`mov 0x7E75F2F0,a0; jmp 0x7E56EB0F`).
  The compiled builds had written the identity table over that table; the card path does not, so every film got
  Cross Process I's S-curve.
- Fix: stub `LKID: mov 0x7E75B8F0,a0; jmp 0x7E56EB0F` at the end of the shared area, 0x7ECB0B6D-0x7ECB0B77 (10 B; the
  area ends 0x7ECB0BA0; nothing else moved). The 8 flashed look entries (codes 75, 92, 94, 98, 125, 144, 156, 159) and
  the film words of the switched entries (79, 71, 72, 85) point at LKID; their stock words are unchanged.
- Emulator (`scripts/emu_look.py`, curve_select 0x7E56E837, all 12 entries loaded, d1 = 0 and 1): `gauge-info-3`
  24/24 rows Cross Process I's table 0x7E75F2F0; this build 24/24 the identity table 0x7E75B8F0 (V).
- Not edited: `experiments/2026-11-18-stock-filters/scripts/equal_tables.py` (another experiment's record) has no
  look check. The missing check: for each entry, decode the `mov imm32,a0` of the handler that the entry's code has in
  the look table (0x7E78C9xx, `slots.LOOK_JUMP`) in both images, and compare the 512 B at the two addresses. It would
  have shown the fault: the film firmware's handler loads identity, the loaded stock-films image Cross Process I.

## 2. ArtFilter Off for an entry with a film (structure-2, data only)

- `rec_art_set_exif_data` 0x7E70DC24 jumps by stored Picture Mode (struct+0x405F) through 0x7E852300 (V). The default
  case 0x7E70DF1B writes no ArtFilter (the field was cleared to 0 = Off), skips the art-effect writer 0x7E70E2E2, does
  not write CustomRendered (struct+2416) or the EXIF Contrast, Saturation and Sharpness fields (struct+2438, 2440,
  2442), and returns 0, as for a normal Picture Mode (V, read and emulator).
- Hidden values 111, 112, 114, 115, 118: stock already points them at 0x7E70DF1B; version 1 had set them to Pop Art's
  case 0x7E70DC9F. Version 2 leaves them stock (5 ops fewer).
- Values 100-103, 105-107: the table word is one more word in the entry's switch list: 0x7E70DF1B with a film, the stock
  word without (Pop Art 12 words, Soft Focus 7, Pale&Light 14, Light Tone 12, Pin Hole 7, Diorama 7, Cross Process 12).
- Emulator piece (`scripts/exif_case.py`, fake struct with 0xAA sentinels): unloaded, values 100-110, 119, 120 equal
  the pinned build's art cases (Pop Art: ArtFilter 2, Contrast High, Saturation High); with all 12 films loaded, the
  film values 100-103, 105-107, 111, 112, 114, 115, 118 give ArtFilter (0, 0, 0, 0), effect 0, return 0, and Contrast,
  Saturation, Sharpness, CustomRendered not written; the stock values 104, 108, 109, 119, 120 keep their art cases (V).
- What Contrast, Saturation and Sharpness then hold: whatever the earlier writers set for the shot (saturation:
  0x7E709A6C from the Picture Mode's saturation setting) (I: Normal, as a Natural shot). U until the camera shot.
- The second caller 0x7E710959 uses the return value: 0 takes the same EXIF branch as a normal Picture Mode (I: harmless).

## 3. Film name in ImageDescription (card-looks-6)

- Template: ImageDescription is 32 B at 0x605BAEC0 (template 0x605BA918 + 0x5A8), filled once at start by 0x7E708F24
  with 0x7E70B0F6(dst, "OLYMPUS DIGITAL CAMERA" 0x7E8517C2, 32, 1): space-padded, NUL at byte 31 (V). Emulator: the
  fill runs once, at 15-17 ms, before the first FILMNAME (29-32 ms), and not again in any session (V).
- T_GUI (0x7ECB0EE8) calls `GUIEXTRA` in place of its remap block (the same remap, then `FILMNAME`). FLAGS stays at
  0x7ECB0FCC and T_END at 0x7EE5392B, which log-menu-2 hooks (the generator asserts it). T_GUI's `.tk` keeps its size
  (`.org` before FLAGS).
- `FILMNAME` (segment 3, `.ap` after the loader, 0x7EE53BFE; GUIEXTRA 0x7EE53BDD): prm_get(0x9481) -> value; a 19-byte
  table maps value - 100 to the entry: 100-103 -> 0-3, 105-107 -> 5-7, 111 -> 4, 112 -> 8, 114 -> 9, 115 -> 10, 118 ->
  11, others none. The stock values 104, 108, 109, 119, 120 map to none: those entries store them only without a film
  (the loader's design; a camera that still holds 104 renders stock Grainy Film). If STOREOK (0x7ECB0FCE) is set and
  the store 0x603F8000 has a record for the entry with a name, the 32 B are 31 spaces + NUL with the name (up to 16 B)
  over the start; otherwise Olympus's text by the stock routine. Built in a 32-byte buffer, then copied as 8 words to
  the cached and the uncached address (as SWITCH writes).
- Sizes: `.ap` 941 -> 1217 B (121 B free); `.tk` 256 B as before; data area 0 1754 B, area 1 912 B.
- Calls: prm_get with `[d2,d3],12`, 0x7E70B0F6 with `[d2,d3,a2,a3],20` (the stock call forms). T_GUI saves every
  register (`movm [d2,d3,other]`); `calls GUIEXTRA` writes its return slot as `calls PMREMAP` did; GUIEXTRA keeps 8 B
  for its own calls. Stack depth: below PMREMAP's (16 + 28 B and Get_CameraInfo) (I).
- Emulator sessions (`scripts/emu_desc.mjs`, look file ART1 Portra 400, ART2 Velvia, ART5 Superia 400, ART11 Gold
  200), the template after each step, cached and uncached equal in every dump (V):

  | Mode | Selection | Stored value | ImageDescription |
  |---|---|---|---|
  | P, before Load | Natural | 2 | OLYMPUS DIGITAL CAMERA |
  | P, after Load | Natural | 2 | OLYMPUS DIGITAL CAMERA |
  | P | ART 1 / 2 / 3 / 5 / 11 | 100 / 101 / 102 / 111 / 115 | Portra 400 / Velvia / OLYMPUS DIGITAL CAMERA / Superia 400 / Gold 200 |
  | P | Natural again | 2 | OLYMPUS DIGITAL CAMERA |
  | ART | ART 1 / 2 / 3 / 5 / 11 | 100 / 101 / 102 / 111 / 115 | as in P |
  | P, from ART | (P's Picture Mode) | 2 | OLYMPUS DIGITAL CAMERA |

- **Open question 3 answered (V, emulator):** in ART mode prm 0x9481 holds the chosen ART entry's value (100, 101,
  102, 111, 115); back in P it holds P's Picture Mode again.
- U: whether each shot copies the template on the core and cache that T_GUI wrote (both aliases are written); whether
  the ORF and RAW Data Edit use the same template; whether a Picture Mode change without a following GUI state reaches
  the template before the shot (in the emulator every selection did).

## 4. Checks

| Check | Result |
|---|---|
| `gen/run.sh` (all generators, v1 and v2), `git diff data/specs/` | no committed spec changes |
| `uv run epm2mod make films-look-exif` (free-space check included) | PASS, sha256 above; two rows added to `tools/space-ledger/superseded.tsv` |
| `emulator/hookcheck.py` on both new specs, with `emulator/hookcheck-allow.tsv` | 111 transfers, 0 FAIL (the 7 allowed hooks of version 1) |
| `emulator/boot-test`, `emulator/update-path-test` | PASS, PASS |
| `scripts/emu_stock2.py` (the six loader sessions of stock-filters on this build) | ALL PASS |
| `scripts/emu_look.py`, `scripts/exif_case.py`, `scripts/emu_desc.mjs` | sections 1 to 3 |
| Firmware errors in the sessions | 2 (0x2a001001 at 41.9 and 43.4 ms), the same 2 in `gauge-info-3` |
| `uv run python -m unittest discover -s cli/tests`, `uv run epm2mod generate --check` | 307 OK; up to date |

## 5. Camera test (one flash, four shots)

Card: `epm2flash films-look-exif af4bcb38df908c3d29b3ef028059a3142cbecc4b66737f7bb2cc2848d6a4bcf4`, then
`uv run epm2mod films set --card /path/to/card --film ART1=portra-400` (ART 1 Portra 400, every other entry Olympus's).
Clear the card's photos first.

1. MENU → SETUP → Custom Menu → J → **Load Looks** → **Load** → OK. The row reads **Loaded**.
2. MENU, LEFT to **ART** (Apply creative effects), OK. In the ART list choose **1 Portra 400**, OK. Shoot (shot 1).
3. MENU, RIGHT to **P**, OK. MENU, LEFT to **ART**, OK. Choose **2 Soft Focus**, OK. Shoot (shot 2). (In the
   emulator, MENU then OK in ART mode goes back to live view without the list; the way through P opens it.)
4. MENU, RIGHT to **P**, OK. OK opens the quick menu; on Picture Mode choose **Natural**, OK. Shoot (shot 3).
5. Quick menu: Picture Mode **ART 1** (Portra 400); image quality: the RAW+JPEG item; OK. Shoot (shot 4).
6. Playback Menu → Edit → Sel. Image → shot 4's RAW → OK → **RAW Data Edit** → Yes (shot 5, Picture Mode still ART 1).
7. On the computer: `exiftool -ArtFilter -ImageDescription -PictureMode -Contrast -Saturation -Sharpness DCIM/100OLYMP/*`

Expected:

| Shot | ArtFilter | ImageDescription |
|---|---|---|
| 1, 4 (JPEG and ORF), 5 | Off | Portra 400 |
| 2 | Soft Focus | OLYMPUS DIGITAL CAMERA |
| 3 | Off | OLYMPUS DIGITAL CAMERA |

Shot 1 has no Cross Process S-curve (compare with a Portra 400 shot of `gauge-info-3`). Other results: Olympus's text on
1 or 4 = the shot's EXIF does not read the template T_GUI writes (core, cache or another copy); a name on 2 or 3 = the
mapping is wrong; Pop Art (or another filter) on 1 or 4 = the switch word is not applied; the ORF or shot 5 differs
from the JPEG = RAW and RAW Data Edit use another template. Record Contrast, Saturation and Sharpness of shots 1, 3
and 4 (section 2, U).

# The look file (EPM2LOOK.BIN), version 1

A look file holds up to twelve film looks, one per art-filter menu entry. The pinned build reads
it from the top folder of the SD card when Load Looks runs, checks it, writes the looks into the entries it lists and keeps a copy in its settings
memory. The looks then stay after a restart and without the card, until another file is loaded.

Make one with `uv run epm2mod films set` (no film argument: the twelve default films, `looks/card-looks.json`).
Check one with `uv run epm2mod inspect FILE`. The flags are in the [command-line reference](cli.md). Code:
`src/epm2mod/looks/lookfile.py` (the format), `src/epm2mod/looks/records.py` (from the film records), `src/epm2mod/looks/lookpack.py` (from the fit files). Why the format
is this way: `experiments/2026-11-17-card-looks/design.md` section 5.

## Layout

Little-endian. Offsets in bytes. Reserved bytes are 0.

Header, 32 bytes:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | magic `EPLK` |
| 4 | 1 | format version: 1 |
| 5 | 1 | number of looks: 0 to 12 |
| 6 | 2 | record size: 1,708 |
| 8 | 4 | file length: 32 + number x 1,708 |
| 12 | 4 | CRC-32 of bytes 16 to the end (zlib's CRC-32, as `zlib.crc32`) |
| 16 | 2 | camera model: 0x0101 (E-PM2) |
| 18 | 2 | firmware version: 0x0160 (1.6) |
| 20 | 12 | reserved |

Then the looks, 1,708 bytes each, in any order.

Look record, the parts that both kinds have:

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | slot: the menu entry, 0 to 11 (table below) |
| 1 | 1 | kind: 1 colour, 2 black-and-white |
| 2 | 2 | reserved |
| 4 | 16 | name: ASCII, padded with 0. The menus show it (camera log, card-looks-3 and -4) |
| 46 | 18 | art matrix, 9 x s16, by rows; each row sums to 256 |

Kind 1, colour:

| Offset | Size | Field |
|---|---|---|
| 20 | 2 | saturation gain, u16 |
| 22 | 12 | six-axis saturation, 6 x s16 |
| 34 | 12 | six-axis hue, 6 x s16 |
| 64 | 97 | chroma curves, u8 each: Cb x[16], y[16], slope[17], then Cr x[16], y[16], slope[16] |
| 161 | 3 | reserved |
| 164 | 3 x 514 | tone curves red, green, blue (below) |
| 1706 | 2 | reserved |

A tone curve has 1,024 points with values 0 to 1,023 that never fall. It is stored as its first value (u16) and
then the 1,023 steps between neighbouring points, 4 bits each (0 to 15), low nibble first; the last nibble is 0.
The camera makes each tone table of the slot from the curve: entry k of a table is the curve at entry k of the
stock default table, kept rising (as the film generator does; the built-in looks give the same bytes).

Kind 2, black-and-white (only build `card-looks`, slot 4; in `card-looks-2` a black-and-white film is a colour look):

| Offset | Size | Field |
|---|---|---|
| 20 | 44 | reserved |
| 64 | 100 | reserved |
| 164 | 512 | grain table: 256 x u16, 0 to 1,023, never falling (the tone of still pictures) |
| 676 | 512 | live table: 256 x u16, the same kind (the tone of live view and movies) |
| 1188 | 520 | reserved |

## Slots

The slot is the place of the entry in the art-filter menu. Each slot takes the kind of look it has in the build: in
`card-looks-4` and the pinned build (`card-looks-5`) every slot takes a colour look (a black-and-white film is a colour look with saturation gain 0); in
`card-looks` slot 4 (Grainy Film) takes only a black-and-white look (kind 2) and the others only colour looks.

| Slot | Menu entry | Look in `looks/card-looks.json` |
|---|---|---|
| 0 | Pop Art | Portra 400 |
| 1 | Soft Focus | Ektachrome |
| 2 | Pale&Light Color | Pro 400H |
| 3 | Light Tone | Kodachrome |
| 4 | Grainy Film | Double-X (a colour look with saturation 0, `looks/fits/doublex3.npz`) |
| 5 | Pin Hole | Vis 250D |
| 6 | Diorama | Velvia |
| 7 | Cross Process | Superia 400 |
| 8 | Gentle Sepia | Provia |
| 9 | Dramatic Tone | Portra 160 |
| 10 | Key Line | Gold 200 |
| 11 | Watercolor | Vis 500T |

A file may hold fewer looks: an entry the file leaves out has its Olympus art filter again (`card-looks-5` writes
its stock words).

## Checks

A file that fails a check is refused whole: nothing is written or kept.

- The camera checks: magic, version 1, record size 1,708, number 0 to 12, file length, the CRC-32, model and
  firmware, every slot 0 to 11 and none twice, the kind of each slot. Curve values above 1,023 are cut to 1,023;
  the tables of kind 2 are copied as they are.
- The tools check also: the name is printable ASCII, the gain and the six-axis values fit their types, each matrix
  row sums to 256 +/- 8, the chroma x values do not fall, every curve step is 0 to 15.

## Writing one in a web page

Build the 1,024-point curves, round them, keep them rising, write the steps; fill a 1,708-byte record per look with
a `DataView` (little-endian); write the header with the CRC of bytes 16 to the end. The CRC-32 in JavaScript:

```js
function crc32(bytes) {
  let crc = ~0;
  for (const b of bytes) {
    crc ^= b;
    for (let k = 0; k < 8; k++) crc = (crc >>> 1) ^ (0xEDB88320 & -(crc & 1));
  }
  return ~crc >>> 0;
}
```

## Test vector

`uv run epm2mod films set -o FILE` gives 20,528 bytes with sha256
`5d5df335dc14100a3fb7c90265ca07470419f12f52f806cc6b80f1bc09cae7ad`. Its first 32 bytes:

```
00000000: 45 50 4c 4b 01 0c ac 06 30 50 00 00 92 4c 77 d2 
00000010: 01 01 60 01 00 00 00 00 00 00 00 00 00 00 00 00
```

`tests/test_lookfile.py` checks this file, the layout, the refusals, and that the tables the camera makes from each
look are the bytes of the built-in looks.

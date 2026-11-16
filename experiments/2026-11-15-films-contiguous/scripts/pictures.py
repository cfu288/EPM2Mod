"""Draw the OSD pictures of block 1 as contact sheets, to find every picture "ART 5".."ART 8".

    .venv/bin/python experiments/2026-11-15-films-contiguous/scripts/pictures.py build/peaking-fast.BIN OUTDIR

Needs Pillow. Writes OUTDIR/pics-XXXX.png (all pictures, number above each) and OUTDIR/art-numbers.png (the
eight sets that make_spec.py moves, ART 1..10 of each).

The picture table (read from the firmware: lookup 0x7ECFF3AC, base pointer at RAM 0x602BA8BC = 0xBFA26844):
block-1 offset 0x2CD024, one u32 per picture number, a run-time pointer to a record
{u16 kind, u16 width, u16 height, u16 bits, u32 0, u32 size, u32 data pointer, u32 0}. Pointers below
0xBFA4BE20 are block offset + 0xBF759820, the others block offset + 0xBF314220. The data is the run-length
format that the OSD engine draws (tools/emu/e101/osd.mjs, command 0x30).
"""

import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from epm2mod.container import parse

TABLE, COUNT = 0x2CD024, 0x9FF
SETS = {
    "ART list, chosen": [0xA4, 0xA5, 0xBB, 0xBD, 0xBF, 0xC1, 0xC3, 0xC5, 0xC7, 0xC9],
    "ART list": [0xA3, 0xBA, 0xBC, 0xBE, 0xC0, 0xC2, 0xC4, 0xC6, 0xC8, 0xCA],
    "strip, chosen": list(range(0x227, 0x231)),
    "strip": list(range(0x238, 0x242)),
    "50x38 dark": [0x32A, 0x32B, 0x333, 0x35A, 0x370, 0x38A, 0x38D, 0x38E, 0x3CA, 0x3CB],
    "54x54": [0x4A4, 0x4A5, 0x4A6, 0x4A7, 0x4A8, 0x4A9, 0x4AA, 0x4AB, 0x4A3, 0x515],
    "44x32 grey": list(range(0x547, 0x551)),
    "44x32 black": list(range(0x5E8, 0x5F2)),
}
FORMATS = {2: (8, 4, 0), 10: (8, 4, 0), 9: (8, 6, 0), 1: (4, 2, 16), 3: (10, 2, 6), 11: (12, 4, 5)}


def offset(pointer: int) -> int:
    """Return the block offset of a run-time pointer of the picture data."""
    return pointer - (0xBF759820 if pointer < 0xBFA4BE20 else 0xBF314220)


def picture(data: bytes, number: int) -> Image.Image | None:
    """Return picture `number` as a grey image, or None when it has no data."""
    pointer = struct.unpack_from("<I", data, TABLE + 4 * number)[0]
    if not 0xBF75A020 <= pointer < 0xC0000000:
        return None
    source = offset(struct.unpack_from("<I", data, offset(pointer) + 16)[0])
    if not 0 < source < len(data) - 16:
        return None
    head = data[source : source + 4]
    lines, width = (head[0] | (head[1] & 15) << 8) + 1, (head[1] >> 4 | head[2] << 4) + 1
    if head[3] not in FORMATS:
        return None
    bits, runbits, per_word = FORMATS[head[3]]
    total, pixels, position = width * lines, bytearray(), source + 4
    while len(pixels) < total and position < len(data) - 8:
        if per_word:
            word = struct.unpack_from("<Q", data, position)[0]
            position += 8
            tokens = [(word >> (bits * k)) & ((1 << bits) - 1) for k in range(per_word)]
        else:
            tokens = [data[position]]
            position += 1
        for token in tokens:
            pixels += bytes([(token >> runbits) & 255]) * ((token & ((1 << runbits) - 1)) + 1)
    top = max(pixels[:total]) or 1
    return Image.frombytes("L", (width, lines), bytes(40 + p * 215 // top if p else 0 for p in pixels[:total]))


def sheet(data: bytes, numbers: list[int], columns: int, cell: tuple[int, int], labels: list[str]) -> Image.Image:
    """Return a contact sheet of the pictures."""
    out = Image.new("RGB", (columns * cell[0], ((len(numbers) + columns - 1) // columns) * cell[1]), (60, 60, 90))
    draw = ImageDraw.Draw(out)
    for k, number in enumerate(numbers):
        x, y = (k % columns) * cell[0], (k // columns) * cell[1]
        image = picture(data, number)
        if image:
            out.paste(image.crop((0, 0, min(image.width, cell[0] - 2), min(image.height, cell[1] - 12))), (x, y + 11))
        draw.text((x + 1, y), labels[k], fill=(255, 255, 0))
    return out


def main() -> None:
    """Write the sheets."""
    data = bytes(parse(Path(sys.argv[1]).read_bytes()).blocks[1].payload)
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    numbers = list(range(1, COUNT))
    for start in range(0, len(numbers), 24 * 14):
        part = numbers[start : start + 24 * 14]
        sheet(data, part, 24, (72, 64), [f"{n:x}" for n in part]).save(out / f"pics-{part[0]:04x}.png")
    flat = [n for ids in SETS.values() for n in ids]
    names = [f"{name} {n:x}" for name, ids in SETS.items() for n in ids]
    sheet(data, flat, 10, (120, 80), names).save(out / "art-numbers.png")


if __name__ == "__main__":
    main()

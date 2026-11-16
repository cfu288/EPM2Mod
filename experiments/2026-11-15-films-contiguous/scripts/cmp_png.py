"""cmp_png.py DIR_A DIR_B [--below Y] [--skip TEXT]: compare the PNG files of two folders by name, pixel by pixel.

--below Y compares only the lines from Y down (the title line of an ART list screen has the entry's place).
--skip TEXT leaves out the files with TEXT in the name.
Prints the names that differ, with the number of different lines and their range, and a count. Exit 0 = equal.
"""

import struct
import sys
import zlib
from pathlib import Path


def rows(path: Path) -> list[bytes]:
    """Return the pixel rows of an 8-bit RGB PNG without filters other than 0 (the emulator's screenshots)."""
    data = path.read_bytes()
    i, width, idat = 8, 0, b""
    while i < len(data):
        size, kind = struct.unpack(">I4s", data[i : i + 8])
        body = data[i + 8 : i + 8 + size]
        i += 12 + size
        if kind == b"IHDR":
            width = struct.unpack(">I", body[:4])[0]
        if kind == b"IDAT":
            idat += body
    raw = zlib.decompress(idat)
    step = width * 3 + 1
    return [raw[y * step + 1 : (y + 1) * step] for y in range(len(raw) // step)]


def main() -> int:
    """Compare and print."""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    below = int(sys.argv[sys.argv.index("--below") + 1]) if "--below" in sys.argv else 0
    if "--below" in sys.argv:
        args.remove(str(below))
    skip = sys.argv[sys.argv.index("--skip") + 1] if "--skip" in sys.argv else None
    if skip:
        args.remove(skip)
    a, b = Path(args[0]), Path(args[1])
    names = sorted(p.name for p in a.glob("*.png") if not (skip and skip in p.name))
    missing = [n for n in names if not (b / n).exists()] + [p.name for p in b.glob("*.png") if not (a / p.name).exists()]
    differ = 0
    for name in names:
        if not (b / name).exists():
            continue
        ra, rb = rows(a / name)[below:], rows(b / name)[below:]
        lines = [y + below for y, (x, z) in enumerate(zip(ra, rb)) if x != z]
        if lines or len(ra) != len(rb):
            differ += 1
            print(f"DIFFERENT {name}: {len(lines)} lines, {lines[0] if lines else '-'}..{lines[-1] if lines else '-'}")
    print(f"{len(names)} files compared from line {below}: {differ} differ, {len(missing)} only in one folder {missing[:8]}")
    return 1 if differ or missing else 0


if __name__ == "__main__":
    sys.exit(main())

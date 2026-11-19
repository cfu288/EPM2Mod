"""Write data/specs/films-contiguous.json: the seven film looks next to each other in every list of looks.

Run from the repository root (the pinned build must be in build/):

    .venv/bin/python experiments/2026-11-15-films-contiguous/scripts/make_spec.py --pinned build/peaking-fast.BIN

The spec is a delta on the pinned build: every `expect` is a byte string of that build. It moves the list
entry of Grainy Film behind Superia 400 in each list, and it moves the number pictures "ART 5..8" so that
the lists still count 1..12 from the top. No stored value, art code or picture table changes.
--table prints what changed, per place.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "2026-11-14-emulator-audit" / "scripts"))
from film_names_spec import N_IDS, STOCK, Blob  # noqa: E402

from epm2mod.container import parse  # noqa: E402
from epm2mod.hashing import sha256_bytes  # noqa: E402

BASE0 = 0x7E421020  # run-time address of block 0, offset 0
PINNED_SHA256 = "0e8a25b9578b8119b14b4895be7d2a0b70d7315e5e817758699777f0f31d917e"

# Block 0: tables whose order is the order of a list. Each row: (name, address, entry size, index of the
# Grainy Film entry, index of the Superia 400 entry). The four entries Grainy Film, Vis 250D, Velvia,
# Superia 400 turn by one place: Grainy Film goes behind Superia 400.
ORDER_TABLES = [
    ("Picture Mode value list (info 111): stored values, 64 B each", 0x7E844CC0, 64, 11, 14),
    ("Picture Mode value list (info 111): menu values, u32", 0x7E83F70C, 4, 11, 14),
    ("RAW-edit picture mode list (info 509): stored values", 0x7E846F40, 64, 11, 14),
    ("RAW-edit picture mode list (info 509): menu values", 0x7E83F934, 4, 11, 14),
    ("RAW-edit picture mode list (info 510): stored values", 0x7E847400, 64, 11, 14),
    ("RAW-edit picture mode list (info 510): menu values", 0x7E83F980, 4, 11, 14),
    ("Shooting Menu 1 -> Picture Mode rows (row table 0x7EFEF4FC, rows 18..21)", 0x7EFEF4FC, 20, 18, 21),
    ("Shooting Menu 1 -> Picture Mode: row -> menu value, u32", 0x7EFF63EC, 4, 11, 14),
    ("ART BKT rows (row table, rows 76..79)", 0x7EFEF4FC, 20, 76, 79),
    ("ART BKT: row -> its Off / On page and bracket flag (pages 576..579, info 418..421)", 0x7EFF9D5C, 8, 4, 7),
    ("Picture Mode Settings rows (row table, rows 131..134)", 0x7EFEF4FC, 20, 131, 134),
    ("Picture Mode Settings: row -> its Off / On page (pages 237..240, show flags 356..359)", 0x7EFF9314, 8, 9, 12),
    ("ART list records, 44 B each (code, name, pictures, settings)", 0x7EFE8B14, 44, 4, 7),
    ("ART mode value list (info 281): art codes, u8", 0x7E849784, 1, 4, 7),
    # The ART list page (code 0x7EDD1C00..0x7EDD7200) keeps more tables by the place in the list (its member
    # +228): what the Filter Type / Add Effects screen of an entry shows and which settings it writes.
    ("ART list page: rows of the Filter Type / Add Effects screen, 30 B per entry", 0x7EFE872C, 30, 4, 7),
    ("ART list page: setting ids of that screen (type, effect, two more), 8 B per entry", 0x7EFE8894, 8, 4, 7),
    ("ART list page: jump table 0x7EFE88F4 by place (function 0x7EDD1E80)", 0x7EFE88F4, 4, 4, 7),
    ("ART list page: jump table 0x7EFE89A4 by place (writes the settings)", 0x7EFE89A4, 4, 4, 7),
    ("ART list page: jump table 0x7EFE89D4 by place (function 0x7EDD6084)", 0x7EFE89D4, 4, 4, 7),
    ("ART list page: jump table 0x7EFE8A04 by place (function 0x7EDD62CB)", 0x7EFE8A04, 4, 4, 7),
    ("ART list page: jump table 0x7EFE8A34 by place (function 0x7EDD6A72)", 0x7EFE8A34, 4, 4, 7),
    ("ART list page: jump table 0x7EFE8A64 by place (function 0x7EDD6C3D)", 0x7EFE8A64, 4, 4, 7),
]
# What each table must hold at the first of the four entries before the change (a guard against a wrong address).
GUARD = {
    0x7E844CC0: struct.pack("<I", 104), 0x7E83F70C: struct.pack("<I", 12), 0x7E846F40: struct.pack("<I", 104),
    0x7E83F934: struct.pack("<I", 12), 0x7E847400: struct.pack("<I", 104), 0x7E83F980: struct.pack("<I", 12),
    0x7EFF63EC: struct.pack("<I", 12), 0x7EFE8B14: struct.pack("<IH", 74, 64), 0x7E849784: bytes([74]),
    0x7EFF9D5C: struct.pack("<2I", 576, 418), 0x7EFF9314: struct.pack("<I", 237),
    0x7EFE872C: struct.pack("<2H", 0xF9, 0xFE), 0x7EFE8894: struct.pack("<4H", 365, 372, 465, 467),
    0x7EFE88F4: struct.pack("<I", 0x7EDD2197), 0x7EFE89A4: struct.pack("<I", 0x7EDD5EFB),
    0x7EFE89D4: struct.pack("<I", 0x7EDD60C0), 0x7EFE8A04: struct.pack("<I", 0x7EDD6670),
    0x7EFE8A34: struct.pack("<I", 0x7EDD6AAF), 0x7EFE8A64: struct.pack("<I", 0x7EDD6C74),
}
ROW_GUARD = {18: (356, 601), 76: (418, 64), 131: (356, 64)}  # row -> (info id, text id) of the Grainy Film row

# Block 1: the picture table. Entry = u32 pointer to a picture record, index = picture number.
PICTURE_TABLE = 0x2CD024  # block-1 offset of entry 0 (the run-time table is at 0xBFA26844)
# The pictures "ART 5", "ART 6", "ART 7", "ART 8" of each size (found by eye on the sheets of pictures.py; build/emu/films-contiguous/pics/art-numbers.png)
PICTURE_SETS = {
    "ART list, chosen (64x48)": (0xBF, 0xC1, 0xC3, 0xC5),
    "ART list (50x38)": (0xC0, 0xC2, 0xC4, 0xC6),
    "live control strip, chosen (64x48)": (0x22B, 0x22C, 0x22D, 0x22E),
    "live control strip (50x38)": (0x23C, 0x23D, 0x23E, 0x23F),
    "50x38, dark": (0x370, 0x38A, 0x38D, 0x38E),
    "54x54": (0x4A8, 0x4A9, 0x4AA, 0x4AB),
    "44x32, grey": (0x54B, 0x54C, 0x54D, 0x54E),
    "44x32, black": (0x5EC, 0x5ED, 0x5EE, 0x5EF),
}
# Texts. Icon + name in the Picture Mode list: the icon is the escape "@A045@".."@A048@" (ART 5..8).
ICON_TEXTS = {601: ("@A045@", "@A048@"), 602: ("@A046@", "@A045@"), 603: ("@A047@", "@A046@"), 582: ("@A048@", "@A047@")}
# The short texts "ART5".."ART8" of the same four entries (tables keyed by the entry, e.g. 0x7EFCA94C).
SHORT_TEXTS = {1653: ("5", "8"), 1654: ("6", "5"), 1655: ("7", "6"), 1656: ("8", "7")}


def turn(data: bytearray, offset: int, size: int, first: int, last: int) -> None:
    """Move entry `first` of a table behind entry `last`."""
    a, b, c = offset + first * size, offset + (first + 1) * size, offset + (last + 1) * size
    data[a:c] = data[b:c] + data[a:b]


def diff_ops(before: bytes, after: bytes, block: int, note: str, start: int, end: int) -> list[dict[str, object]]:
    """Return one bytes op per run of changed bytes in [start, end)."""
    ops: list[dict[str, object]] = []
    i = start
    while i < end:
        if before[i] == after[i]:
            i += 1
            continue
        j = i
        while j < end and before[j] != after[j]:
            j += 1
        ops.append({"type": "bytes", "block": block, "offset": f"{i:#x}", "expect": before[i:j].hex(),
                    "new": after[i:j].hex(), "_note": note})
        i = j
    return ops


def main() -> None:
    """Write the spec."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1])
    parser.add_argument("--pinned", default="build/peaking-fast.BIN")
    parser.add_argument("--out", default="data/specs/films-contiguous.json")
    parser.add_argument("--table", action="store_true")
    args = parser.parse_args()
    raw = Path(args.pinned).read_bytes()
    if sha256_bytes(raw) != PINNED_SHA256:
        raise SystemExit(f"{args.pinned} is not the pinned build {PINNED_SHA256[:8]}")
    blocks = parse(raw).blocks
    b0, b1 = bytes(blocks[0].payload), bytes(blocks[1].payload)
    ops: list[dict[str, object]] = []
    table: list[str] = []

    # ---- block 0: the order of the lists
    out0 = bytearray(b0)
    for name, address, size, first, last in ORDER_TABLES:
        offset = address - BASE0
        at = offset + first * size
        if address in GUARD and address != 0x7EFEF4FC and not b0[at:].startswith(GUARD[address]):
            raise SystemExit(f"{name}: the Grainy Film entry is not at {address + first * size:#x}")
        if address == 0x7EFEF4FC:
            row = struct.unpack_from("<10H", b0, at)
            if (row[2], row[8]) != ROW_GUARD[first]:
                raise SystemExit(f"{name}: row {first} is {row}")
        turn(out0, offset, size, first, last)
        new = diff_ops(b0, bytes(out0), 0, name, at, offset + (last + 1) * size)
        ops += new
        table.append(f"block 0\t{address + first * size:#x}\t{sum(len(str(o['new'])) // 2 for o in new)} B\t{name}")

    # ---- block 1: the number pictures
    out1 = bytearray(b1)
    pointers = lambda n: struct.unpack_from("<I", b1, PICTURE_TABLE + 4 * n)[0]  # noqa: E731
    every = [pointers(n) for n in range(0xA00)]
    for name, ids in PICTURE_SETS.items():
        for n in ids:
            if every.count(pointers(n)) != 1:
                raise SystemExit(f"picture {n:#x} shares its record")
        five, six, seven, eight = (pointers(n) for n in ids)
        # the entry that had "ART 5" (Grainy Film) shows "ART 8"; the three films move up by one
        for n, value in zip(ids, (eight, five, six, seven)):
            struct.pack_into("<I", out1, PICTURE_TABLE + 4 * n, value)
        for n in ids:
            at = PICTURE_TABLE + 4 * n
            ops += diff_ops(b1, bytes(out1), 1, f"picture {n:#x}: ART 5..8, {name}", at, at + 4)
        table.append(f"block 1\tpictures {', '.join(f'{n:#x}' for n in ids)}\t16 B\t{name}")

    # ---- block 1: the texts, 34 languages
    for entry in range(1, 35):
        blob = Blob(b1, entry)
        spans = {i: (blob.offset(i), blob.offset(i) + 2 * len(blob.text(i))) for i in range(N_IDS)}
        before = bytes(out1)
        for string_id, (old, new_text) in {**ICON_TEXTS, **SHORT_TEXTS}.items():
            text = blob.text(string_id)
            if text.count(old) != 1:
                raise SystemExit(f"{blob.code}: id {string_id} is {text!r}")
            place = spans[string_id][0] + 2 * (text.index(old) + len(old) - (2 if string_id in ICON_TEXTS else 1))
            want = old[-2] if string_id in ICON_TEXTS else old
            if out1[place : place + 2] != want.encode("utf-16-le"):
                raise SystemExit(f"{blob.code}: id {string_id}: no {want!r} at {place:#x}")
            for other, (a, b) in spans.items():
                if other != string_id and a <= place < b:
                    raise SystemExit(f"{blob.code}: id {other} shares the text of id {string_id}")
            digit = new_text[-2] if string_id in ICON_TEXTS else new_text
            out1[place : place + 2] = digit.encode("utf-16-le")
            table.append(f"block 1\t{place:#x}\t2 B\t{blob.code} id {string_id}: {text!r} -> {text.replace(old, new_text)!r}")
        after = Blob(bytes(out1), entry)
        for string_id in range(N_IDS):
            want_text = blob.text(string_id)
            if string_id in ICON_TEXTS or string_id in SHORT_TEXTS:
                old, new_text = {**ICON_TEXTS, **SHORT_TEXTS}[string_id]
                want_text = want_text.replace(old, new_text)
            if after.text(string_id) != want_text:
                raise SystemExit(f"{blob.code}: id {string_id} reads {after.text(string_id)!r}")
        ops += diff_ops(before, bytes(out1), 1, f"{blob.code} (language {entry}): ART numbers of four entries", blob.head, blob.array)

    if args.table:
        print("\n".join(table))
        return
    changed = sum(len(str(o["new"])) // 2 for o in ops)
    spec = {
        "name": "films-contiguous",
        "description": (
            "The seven film looks next to each other in every list of looks: the entry Grainy Film moves from "
            "the fifth place to the eighth, behind Superia 400. Only the order of list entries changes (the "
            "Picture Mode value lists of info 111, 509 and 510, the rows of Shooting Menu 1 -> Picture Mode, of "
            "ART BKT and of Picture Mode Settings, the ART list records with the eight tables that the ART list page keeps by place, and the ART mode value list). The "
            "number pictures ART 5 to ART 8, the icon escapes of string ids 601, 602, 603 and 582 and the "
            "texts ART5 to ART8 (ids 1653 to 1656) in all 34 languages move with them, so Vis 250D, Velvia and "
            "Superia 400 show ART 5, 6, 7 and Grainy Film shows ART 8. No stored value, art code or picture "
            "table changes: a saved Picture Mode still selects the same look. A delta on "
            "data/builds/peaking-fast.json: every expect is a byte string of that build. Made by "
            "experiments/2026-11-15-films-contiguous/scripts/make_spec.py."
        ),
        "base": STOCK,
        "base_sha256": sha256_bytes(Path(STOCK).read_bytes()),
        "status": "candidate: emulator-checked, not flashed",
        "_delta_on": f"data/builds/peaking-fast.json (sha256 {PINNED_SHA256})",
        "ops": ops,
    }
    Path(args.out).write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{args.out}: {len(ops)} ops, {changed} bytes")


if __name__ == "__main__":
    main()

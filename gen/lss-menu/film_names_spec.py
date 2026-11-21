"""Write data/specs/film-names-all-languages.json: the film names in all 34 menu languages.

Run from the repository root:

    .venv/bin/python experiments/2026-11-14-emulator-audit/scripts/film_names_spec.py \
        --pinned build/peaking-gain-2x.BIN [--out data/specs/film-names-all-languages.json] [--table]

The spec is a delta on the pinned build: each `expect` is what the pinned build has.

Block 1 holds one text blob per language (directory entries 1..34 at the start of the block).
A blob is {u32 pointer array, u32 pointer array end}, a pool of NUL-terminated UTF-16LE strings
in id order, then 1970 u32 pointers. A pointer is a run-time address for a blob loaded at
0xBFF3D000. The string id is the index into the pointer array, the same in every language.

A name that fits its old string is written in place. A longer name is written into an old
string that no id uses any more, and the pointer of its id is changed. A plain name ("Velvia")
can point into the tail of the same name with an icon ("@A047@Velvia").
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from epm2mod.container import parse
from epm2mod.hashing import sha256_bytes

STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
BLOCK1_LOAD = 0x43C40000
RUNTIME = 0xBFF3D000
N_IDS = 1970
ICON = 6  # characters of an icon escape "@Axxx@"

# English stock name -> film name
FILMS = {
    "Pop Art": "Portra",
    "Soft Focus": "Ektachrome",
    "Pale&Light Color": "Pro 400H",
    "Light Tone": "Kodachrome",
    "Pin Hole": "Vis 250D",
    "Diorama": "Velvia",
    "Cross Process": "Superia 400",
}
# string id -> (English stock text, id of the same name with an icon or None)
IDS: dict[int, tuple[str, int | None]] = {
    60: ("Cross Process", 582),
    61: ("Diorama", 603),
    65: ("Light Tone", 600),
    66: ("Pale&Light Color", 599),
    67: ("Pop Art", 597),
    68: ("Soft Focus", 598),
    69: ("Pin Hole", 602),
    582: ("@A048@Cross Process", None),
    597: ("@A040@Pop Art", None),
    598: ("@A042@Soft Focus", None),
    599: ("@A043@Pale&Light Color", None),
    600: ("@A044@Light Tone", None),
    602: ("@A046@Pin Hole", None),
    603: ("@A047@Diorama", None),
    1173: ("@A043@Pin Hole", None),
    1186: ("@A044@Diorama", None),
}
NEIGHBOURS = (62, 63, 64, 601)  # between the film names in the pool; they can move, text not changed
EFFECT_ID = 764  # "Add Soft Focus Effect": the effect, not the filter
ENGLISH = 8  # directory entry of the English blob


def target(english: str) -> str:
    """Return the new text of an id from its English stock text."""
    if english.startswith("@"):
        return english[:ICON] + FILMS[english[ICON:]]
    return FILMS[english]


class Blob:
    """One language blob of a block-1 payload."""

    def __init__(self, data: bytes, entry: int) -> None:
        address, size = struct.unpack_from("<2I", data, 16 * entry)
        start = address - BLOCK1_LOAD
        for head in range(start - 0x200, start + 0x200, 2):
            first, end = struct.unpack_from("<2I", data, head)
            if RUNTIME < first < end < RUNTIME + 0x80000 and end - first == 4 * N_IDS:
                if struct.unpack_from("<I", data, head + first - RUNTIME)[0] == RUNTIME + 8:
                    break
        else:
            raise SystemExit(f"language {entry}: no blob header found")
        self.data, self.entry, self.head = data, entry, head
        self.array = head + first - RUNTIME
        self.pointers = list(struct.unpack_from(f"<{N_IDS}I", data, self.array))
        foot = data[self.array + 4 * N_IDS : start + size].decode("utf-16-le", "replace")
        self.code = foot.split("OlympusLanguage_")[1][:3] if "OlympusLanguage_" in foot else "?"

    def offset(self, string_id: int) -> int:
        """Return the block offset of the text of an id."""
        return self.head + self.pointers[string_id] - RUNTIME

    def text(self, string_id: int) -> str:
        """Return the text of an id."""
        start = end = self.offset(string_id)
        while self.data[end : end + 2] != b"\0\0":
            end += 2
        return self.data[start:end].decode("utf-16-le")


class NoRoom(Exception):
    """A name found no free old string."""


def pack(sizes: list[int], rooms: list[int]) -> list[int] | None:
    """Put each size into a room (depth-first search). Return the room index per size, or None."""
    left = list(rooms)
    choice = [0] * len(sizes)

    def place(k: int) -> bool:
        if k == len(sizes):
            return True
        tried = set()
        for r in sorted(range(len(left)), key=lambda r: left[r]):
            if left[r] >= sizes[k] and left[r] not in tried:
                tried.add(left[r])
                left[r] -= sizes[k]
                choice[k] = r
                if place(k + 1):
                    return True
                left[r] += sizes[k]
        return False

    return choice if place(0) else None


def plan_language(stock: Blob, now: Blob, out: bytearray, level: int) -> list[str]:
    """Change one language in `out`. Return one table line per id.

    Level 1: a plain name that fits stays in its own string. Level 2: every plain name points into
    the name with an icon, so its old string is free. Level 3: the neighbours of the film names
    (ids 62 to 64 and 601, text not changed) can move too, so the free strings join.
    """
    code = stock.code
    lines: list[str] = []
    where: dict[int, int] = {}  # id -> block offset of its final text
    free: list[list[int]] = []  # [offset, bytes] of old strings that no id uses any more
    moved: list[int] = []  # ids whose text goes into a free string
    shared: list[int] = []  # plain ids that point into the name with an icon
    want = {i: target(english) for i, (english, _) in IDS.items()}
    twins = {i: twin for i, (_, twin) in IDS.items()}
    if level >= 3:
        for extra in NEIGHBOURS:
            want[extra] = now.text(extra)
            twins[extra] = None
        if now.text(601)[ICON:] == now.text(64):
            twins[64] = 601

    def line(string_id: int, how: str) -> None:
        lines.append(f"{code}\t{string_id}\t{stock.text(string_id)}\t{want[string_id]}\t{how}")

    def repoint(string_id: int, offset: int, how: str) -> None:
        struct.pack_into("<I", out, now.array + 4 * string_id, offset - now.head + RUNTIME)
        where[string_id] = offset
        line(string_id, how)

    for string_id in sorted(want):
        old, new = now.text(string_id), want[string_id]
        room = len(stock.text(string_id))
        plain = twins[string_id] is not None
        if old == new and string_id in IDS:
            where[string_id] = now.offset(string_id)
            line(string_id, "already right")
        elif len(new) <= room and string_id in IDS and not (plain and level >= 2):
            padded = (new + "\0" * (room - len(new))).encode("utf-16-le")
            out[now.offset(string_id) : now.offset(string_id) + len(padded)] = padded
            where[string_id] = now.offset(string_id)
            line(string_id, "in place")
        else:
            free.append([now.offset(string_id), 2 * (room + 1)])
            (shared if plain else moved).append(string_id)
    free.sort()
    joined: list[list[int]] = []
    for offset, size in free:
        if joined and joined[-1][0] + joined[-1][1] == offset:
            joined[-1][1] += size
        else:
            joined.append([offset, size])
    moved.sort(key=lambda i: -len(want[i]))
    texts = [(want[i] + "\0").encode("utf-16-le") for i in moved]
    rooms = pack([len(t) for t in texts], [size for _, size in joined])
    if rooms is None:
        raise NoRoom(code)
    for string_id, raw, room_index in zip(moved, texts, rooms):
        spot = joined[room_index]
        out[spot[0] : spot[0] + len(raw)] = raw
        repoint(string_id, spot[0], "moved, text not changed" if string_id in NEIGHBOURS else "moved to a free string")
        spot[0] += len(raw)
        spot[1] -= len(raw)
    for string_id in shared:
        twin = twins[string_id]
        assert twin is not None
        repoint(string_id, where[twin] + 2 * ICON, f"points into the text of id {twin}")
    return lines


def diff_ops(before: bytes, after: bytes, start: int, end: int, note: str) -> list[dict[str, object]]:
    """Return one bytes op per run of changed 2-byte units between two payloads."""
    ops: list[dict[str, object]] = []
    run: int | None = None
    for offset in range(start & ~1, end + 2, 2):
        differ = offset < end and before[offset : offset + 2] != after[offset : offset + 2]
        if differ and run is None:
            run = offset
        elif not differ and run is not None:
            ops.append(
                {
                    "type": "bytes",
                    "block": 1,
                    "offset": f"{run:#x}",
                    "expect": before[run:offset].hex(),
                    "new": after[run:offset].hex(),
                    "_note": note,
                }
            )
            run = None
    return ops


def main() -> None:
    """Write the spec, or print the table."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--stock", default=STOCK)
    parser.add_argument("--pinned", required=True, help="the pinned build's .BIN")
    parser.add_argument("--out", default="data/specs/film-names-all-languages.json")
    parser.add_argument("--table", action="store_true", help="print one line per language and id, write nothing")
    args = parser.parse_args()
    stock_file = Path(args.stock).read_bytes()
    stock = parse(stock_file).blocks[1].payload
    pinned = parse(Path(args.pinned).read_bytes()).blocks[1].payload
    english = Blob(stock, ENGLISH)
    for string_id, (text, _) in IDS.items():
        if english.text(string_id) != text:
            raise SystemExit(f"id {string_id} is not {text!r} in the stock English table")
    ops: list[dict[str, object]] = []
    table: list[str] = []
    for entry in range(1, 35):
        before, now = Blob(stock, entry), Blob(pinned, entry)
        for level in (1, 2, 3):
            out = bytearray(pinned)
            try:
                lines = plan_language(before, now, out, level)
                break
            except NoRoom:
                continue
        else:
            raise SystemExit(f"{before.code}: the names do not fit")
        # the effect label that seven-labels renamed by accident (French only)
        if now.text(EFFECT_ID) != before.text(EFFECT_ID):
            raw = before.text(EFFECT_ID).encode("utf-16-le")
            out[now.offset(EFFECT_ID) : now.offset(EFFECT_ID) + len(raw)] = raw
            lines.append(f"{before.code}\t{EFFECT_ID}\t{before.text(EFFECT_ID)}\t{before.text(EFFECT_ID)}\tback to stock")
        after = Blob(bytes(out), entry)
        for string_id in range(N_IDS):
            if string_id in IDS:
                if after.text(string_id) != target(IDS[string_id][0]):
                    raise SystemExit(f"{before.code}: id {string_id} is {after.text(string_id)!r}")
            elif after.text(string_id) != before.text(string_id):  # every other id reads as stock
                raise SystemExit(f"{before.code}: id {string_id} changed")
        note = f"{before.code} (language {entry}, level {level})"
        ops += diff_ops(pinned, bytes(out), now.head, now.array + 4 * N_IDS, note)
        table += [f"{entry}\t{level}\t{text}" for text in lines]
    if args.table:
        print("\n".join(table))
        return
    spec = {
        "name": "film-names-all-languages",
        "description": (
            "The seven film names in all 34 menu languages (string ids "
            + ", ".join(str(i) for i in sorted(IDS))
            + "), and the French label of the effect 'Add Soft Focus Effect' (id 764) back to its stock text. "
            "A delta on data/specs/seven-labels.json: apply after it. A name longer than its old string is moved "
            "inside the language's text pool and the pointer of its id is changed. Made by "
            "experiments/2026-11-14-emulator-audit/scripts/film_names_spec.py."
        ),
        "base": STOCK,
        "base_sha256": sha256_bytes(stock_file),
        "ops": ops,
        "status": "emulator-checked 2026-11-14 (all 34 languages), not camera-tested",
    }
    Path(args.out).write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{args.out}: {len(ops)} ops")


if __name__ == "__main__":
    main()

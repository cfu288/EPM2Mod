"""Write the patch spec with the names of the films beyond the first seven, in all 34 menu languages.

Run from the repository root, after `epm2mod make` has made the base build:

    .venv/bin/python experiments/2026-11-16-films-max/scripts/names_spec.py \
        --base build/peaking-fast.BIN [--out data/specs/films12-names.json] [--table]

The names come from data/films/more-films.json (entry -> label). The text-pool reader is that of
experiments/2026-11-14-emulator-audit/scripts/film_names_spec.py. If every name fits its old string, the names
are written in place. Else the old strings of the names are joined where they touch, the names with an icon
go into them, and a plain name points into the name with its icon; neighbours in the pool move (text not
changed) when that joins enough room. Every other string id reads as in the base build (checked).

The spec takes the place of data/specs/film-names-all-languages.json in a build: its operations are the difference
between the base build without that spec and the base build with the new names. (`epm2mod make` lets no later
spec change a byte that an earlier spec covers and keeps; the Japanese names need such bytes of that spec.)
"""

from __future__ import annotations

import argparse
import itertools
import json
import struct
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments" / "2026-11-14-emulator-audit" / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import film_names_spec as names  # noqa: E402

from epm2mod.container import parse  # noqa: E402
from epm2mod.hashing import sha256_bytes  # noqa: E402

# string id -> (English stock text, id of the same name with an icon or None)
# a name of the first seven films that changes in this build (name in the base build -> new name): with
# Portra 160 in the list, the first Portra entry says which Portra it is
RENAMED = {"Portra": "Portra 400"}
IDS: dict[int, tuple[str, int | None]] = {
    67: ("Portra", 597),
    597: ("@A040@Portra", None),
    62: ("Dramatic Tone", 583),
    63: ("Gentle Sepia", 650),
    64: ("Grainy Film", 601),
    1452: ("Key Line", 1453),
    1717: ("Watercolor", 1718),
    583: ("@A041@Dramatic Tone", None),
    601: ("@A045@Grainy Film", None),
    650: ("@A049@Gentle Sepia", None),
    1453: ("@A075@Key Line", None),
    1718: ("@A07A@Watercolor", None),
    1163: ("@A042@Grainy Film", None),
    1194: ("@A045@Dramatic Tone", None),
}
# ids with a second icon number. No table ties them to a menu entry and no screen was found that shows them
# (experiments/2026-11-15-films-contiguous/NOTES.md). They keep the stock text in a language whose text pool has
# no room for all names (Chinese simplified, Korean).
SPARE_IDS = (1163, 1194)
# ids next to the names in the text pool: some of them can move (text not changed), so that free strings join
#: how many neighbours one language may move (the search stays short)
MOST_MOVED = 3
NEIGHBOURS = (582, 584, 649, 651, 1162, 1164, 1193, 1195, 1451, 1454, 1716, 1719)


def kept_bytes(spec_paths: list[str]) -> set[int]:
    """Return the block-1 offsets that the given specs cover with an operation and do not change.

    `epm2mod make` refuses a later spec that changes such a byte (it counts as part of the earlier spec), also
    when the later spec is a delta that knows the earlier output. So this spec must leave them as they are.
    """
    kept: set[int] = set()
    for path in spec_paths:
        for op in json.loads(Path(path).read_text())["ops"]:
            if op.get("type") != "bytes" or op.get("block") != 1:
                continue
            offset = int(op["offset"], 16)
            for k, (old, new) in enumerate(zip(bytes.fromhex(op["expect"]), bytes.fromhex(op["new"]))):
                if old == new:
                    kept.add(offset + k)
                else:
                    kept.discard(offset + k)
    return kept


def place(
    texts: list[tuple[int, bytes]],
    free: list[tuple[int, int]],
    fits: Callable[[int, bytes, int], bool],
    limit: list[int],
) -> list[int] | None:
    """Put each text at an offset inside the free intervals (depth-first search). Return the offsets, or None.

    `texts` holds (string id, text). `free` holds (start, end) intervals. `fits(id, text, offset)` says if the
    text of the id may be written at the offset.
    `limit` holds the number of steps that the search may still take; it gives up (None) at 0.
    """
    if not texts:
        return []
    if sum(len(text) for _, text in texts) > sum(end - start for start, end in free):
        return None
    string_id, text = texts[0]
    if len(text) > max((end - start for start, end in free), default=0):
        return None
    tried: set[tuple[int, int]] = set()
    for index, (start, end) in sorted(enumerate(free), key=lambda item: item[1][1] - item[1][0]):
        for offset in range(start, end - len(text) + 1, 2):
            if not fits(string_id, text, offset):
                continue
            shape = (end - start, offset - start)
            if shape in tried or limit[0] <= 0:
                break
            tried.add(shape)
            limit[0] -= 1
            rest = free[:index] + free[index + 1 :]
            rest += [(start, offset), (offset + len(text), end)]
            tail = place(texts[1:], [(lo, hi) for lo, hi in rest if hi > lo], fits, limit)
            if tail is not None:
                return [offset] + tail
            break  # another offset in the same interval does not help the texts that follow
    return None


def doubles(
    now: names.Blob,
    busy: set[int],
    keeps: Callable[[bytes, int], bool],
    pointer: Callable[[int, int], tuple[int, bytes]],
) -> list[tuple[int, int]]:
    """Return (id, id with the same text) for strings that can go, the longest first.

    A string can go if another id holds the same text in another string, no other id points into it, the id
    is not one of `busy`, and its pointer may change.
    """
    offsets = [now.offset(i) for i in range(names.N_IDS)]
    texts = [now.text(i) for i in range(names.N_IDS)]
    first: dict[str, int] = {}
    out = []
    for string_id, text in enumerate(texts):
        if string_id in busy or len(text) < 3:
            continue
        if text not in first:
            first[text] = string_id
            continue
        keep = first[text]
        start, end = offsets[string_id], offsets[string_id] + 2 * (len(text) + 1)
        if offsets[keep] == start or keep in busy:
            continue
        if sum(start <= offset < end for offset in offsets) != 1:
            continue
        if not keeps(*reversed(pointer(string_id, offsets[keep]))):
            continue
        out.append((string_id, keep))
    return sorted(out, key=lambda pair: -len(texts[pair[0]]))


def plan(
    now: names.Blob,
    base: bytes,
    ids: dict[int, tuple[str, int | None]],
    moved: tuple[int, ...],
    kept: set[int],
    apart: bool = False,
    twice: int = 0,
) -> tuple[list[tuple[int, bytes]], list[str]]:
    """Plan one language. Return the writes (block offset, bytes) and one table line per id. Raises names.NoRoom.

    Every id of `ids` and of `moved` gives up its old string. The freed strings that touch are joined. A
    name with an icon and the text of a moved neighbour go into the free strings; a plain name points into
    the name with its icon. With no neighbour moved, a name that fits its own old string stays there.
    No byte of `kept` gets another value. With `apart`, a plain name gets a string of its own.
    With `twice` = n, up to n texts that the pool holds twice (two ids, the same text, two strings) give up
    their second string: that id points at the first string, and the second string is free room.
    """
    writes: list[tuple[int, bytes]] = []
    want = {i: names.target(english) for i, (english, _) in ids.items()}
    twins = {i: None if apart else twin for i, (_, twin) in ids.items()}
    for extra in moved:
        want[extra], twins[extra] = now.text(extra), None
    lines: list[str] = []
    where: dict[int, int] = {}

    def keeps(raw: bytes, offset: int) -> bool:
        return not any(raw[k] != base[offset + k] and offset + k in kept for k in range(len(raw)))

    def pointer(string_id: int, offset: int) -> tuple[int, bytes]:
        return now.array + 4 * string_id, struct.pack("<I", offset - now.head + names.RUNTIME)

    def fits(string_id: int, raw: bytes, offset: int) -> bool:
        """True if the text, its pointer and the pointers of the plain names inside it keep the kept bytes."""
        inside = [i for i in want if twins[i] == string_id]
        return (
            keeps(raw, offset)
            and keeps(*reversed(pointer(string_id, offset)))
            and all(keeps(*reversed(pointer(i, offset + 2 * names.ICON))) for i in inside)
        )

    def repoint(string_id: int, offset: int, how: str) -> None:
        writes.append(pointer(string_id, offset))
        where[string_id] = offset
        lines.append(f"{now.code}\t{string_id}\t{now.text(string_id)}\t{want[string_id]}\t{how}")

    if not moved and all(len(want[i]) <= len(now.text(i)) for i in ids):
        padded = {
            i: (want[i] + "\0" * (len(now.text(i)) - len(want[i]))).encode("utf-16-le") for i in ids
        }
        if all(keeps(raw, now.offset(i)) for i, raw in padded.items()):
            for string_id in sorted(ids):
                writes.append((now.offset(string_id), padded[string_id]))
                lines.append(f"{now.code}\t{string_id}\t{now.text(string_id)}\t{want[string_id]}\tin place")
            return writes, lines
    free = sorted((now.offset(i), now.offset(i) + 2 * (len(now.text(i)) + 1)) for i in want)
    for string_id, first in doubles(now, set(want), keeps, pointer)[:twice]:
        free.append((now.offset(string_id), now.offset(string_id) + 2 * (len(now.text(string_id)) + 1)))
        writes.append(pointer(string_id, now.offset(first)))
        lines.append(f"{now.code}\t{string_id}\t{now.text(string_id)}\t{now.text(string_id)}\tshares the string of id {first}")
    free.sort()
    joined: list[tuple[int, int]] = []
    for start, end in free:  # a plain name can lie inside the name with its icon already: take the union
        if joined and joined[-1][1] >= start:
            joined[-1] = (joined[-1][0], max(joined[-1][1], end))
        else:
            joined.append((start, end))
    raw_of = {i: (want[i] + "\0").encode("utf-16-le") for i in want if twins[i] is None}

    def choices(string_id: int) -> int:
        """In how many of the free strings the text of an id can go: the texts with few places go first."""
        raw = raw_of[string_id]
        return sum(
            any(fits(string_id, raw, offset) for offset in range(start, end - len(raw) + 1, 2))
            for start, end in joined
        )

    own = sorted(raw_of, key=lambda i: (choices(i), -len(raw_of[i])))
    texts = [raw_of[i] for i in own]
    offsets = place(list(zip(own, texts)), joined, fits, [400])
    if offsets is None:
        raise names.NoRoom(now.code)
    for string_id, raw, offset in zip(own, texts, offsets):
        writes.append((offset, raw))
        repoint(string_id, offset, "moved, text not changed" if string_id in moved else "moved to a free string")
    for string_id in sorted(i for i in want if twins[i] is not None):
        twin = twins[string_id]
        assert twin is not None
        repoint(string_id, where[twin] + 2 * names.ICON, f"points into the text of id {twin}")
    return writes, lines


def attempts(now: names.Blob) -> Iterator[tuple[int, ...]]:
    """Yield the neighbours that may move: none, then ever more of them.

    A neighbour whose string holds the text of another id too (a plain name inside a name with an icon) stays.
    """
    starts = [now.offset(i) for i in range(names.N_IDS)]
    alone = [
        n
        for n in NEIGHBOURS
        if sum(now.offset(n) <= start < now.offset(n) + 2 * (len(now.text(n)) + 1) for start in starts) == 1
    ]
    for count in range(min(len(alone), MOST_MOVED) + 1):
        yield from itertools.combinations(alone, count)


def main() -> None:
    """Write the spec, or print the table."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--stock", default=names.STOCK)
    parser.add_argument("--base", required=True, help="the .BIN of the build that the spec is a delta on")
    parser.add_argument("--films", default="data/films/more-films.json")
    parser.add_argument("--out", default="data/specs/films12-names.json")
    parser.add_argument(
        "--earlier",
        nargs="*",
        default=["data/specs/seven-labels.json"],
        help="the specs of the build that change menu texts and stay in it",
    )
    parser.add_argument(
        "--replaces",
        default="data/specs/film-names-all-languages.json",
        help="the spec of the base build that this spec takes the place of (its changes become part of this spec)",
    )
    parser.add_argument("--table", action="store_true", help="print one line per language and id, write nothing")
    args = parser.parse_args()
    films = {film["entry"]: film["label"] for film in json.loads(Path(args.films).read_text())["films"]}
    films.update(RENAMED)
    names.FILMS = films
    stock_file = Path(args.stock).read_bytes()
    base = parse(Path(args.base).read_bytes()).blocks[1].payload
    english = names.Blob(base, names.ENGLISH)
    for string_id, (text, _) in IDS.items():
        if english.text(string_id) != text:
            raise SystemExit(f"id {string_id} is {english.text(string_id)!r}, not {text!r}, in the base build's English table")
    kept = kept_bytes(args.earlier)
    # the block as the build has it without the spec that this one replaces: the `expect` side of the operations
    before = bytearray(base)
    for op in reversed(json.loads(Path(args.replaces).read_text())["ops"]):
        if op.get("block") != 1:
            raise SystemExit(f"{args.replaces}: an operation outside block 1")
        offset, new = int(op["offset"], 16), bytes.fromhex(op["new"])
        if before[offset : offset + len(new)] != new:
            raise SystemExit(f"{args.replaces}: the base build does not hold its bytes at {offset:#x}")
        before[offset : offset + len(new)] = bytes.fromhex(op["expect"])
    before = bytes(before)
    ops: list[dict[str, object]] = []
    table: list[str] = []
    short: list[str] = []
    no_space: list[str] = []
    shared: list[str] = []
    for entry in range(1, 35):
        now = names.Blob(base, entry)
        choices = [
            (spare, tight, apart, twice)
            for tight in (False, True)
            for twice in (0, 4, 12)
            for spare in (True, False)
            for apart in (False, True)
        ]
        found = None
        for spare, tight, apart, twice in choices:  # the full names first; for each choice, few neighbours first
            ids = IDS if spare else {i: v for i, v in IDS.items() if i not in SPARE_IDS}
            names.FILMS = {entry: label.replace(" ", "") for entry, label in films.items()} if tight else films
            for moved in attempts(now):
                try:
                    found = plan(now, base, ids, moved, kept, apart, twice)
                    break
                except names.NoRoom:
                    continue
            if found is not None:
                break
        if found is None:
            raise SystemExit(f"{now.code}: the names do not fit")
        writes, lines = found
        if tight:
            no_space.append(now.code)
        if twice:
            shared.append(now.code)
        if len(ids) != len(IDS):
            short.append(now.code)
        out = bytearray(base)
        for offset, raw in writes:
            out[offset : offset + len(raw)] = raw
        after = names.Blob(bytes(out), entry)
        for string_id in range(names.N_IDS):
            if string_id in ids:
                if after.text(string_id) != names.target(ids[string_id][0]):
                    raise SystemExit(f"{now.code}: id {string_id} is {after.text(string_id)!r}")
            elif after.text(string_id) != now.text(string_id):
                raise SystemExit(f"{now.code}: id {string_id} changed")
        note = f"{now.code} (language {entry}; neighbours moved: {list(moved) or 'none'})"
        ops += names.diff_ops(before, bytes(out), now.head, now.array + 4 * names.N_IDS, note)
        table += [f"{entry}\t{text}" for text in lines]
    if args.table:
        print("\n".join(table))
        return
    spec = {
        "name": Path(args.out).stem,
        "description": (
            "The names of the films beyond the first seven in all 34 menu languages, and Portra renamed to Portra 400 ("
            + ", ".join(f"{entry} -> {label}" for entry, label in films.items())
            + "; string ids "
            + ", ".join(str(i) for i in sorted(IDS))
            + (
                f"; ids {' and '.join(str(i) for i in SPARE_IDS)} keep the stock text in {', '.join(short)}, "
                "where the text pool has no room"
                if short
                else ""
            )
            + (
                f"; the names have no space character in {', '.join(no_space)}, where the text pool has no "
                "room for it"
                if no_space
                else ""
            )
            + (
                f"; in {', '.join(shared)} some ids that show the same text share one string, which gives the room"
                if shared
                else ""
            )
            + "). The spec also holds what data/specs/film-names-all-languages.json does (the names of the first seven "
            "films in all languages) and takes its place in a build: put it after the other specs of the pinned "
            "build, and leave film-names-all-languages out. One spec, because `epm2mod make` lets no later spec "
            "change a byte that an earlier spec covers and keeps, and the Japanese names need such bytes. A name "
            "longer than its old string is moved inside the language's text pool and the pointer of its id is "
            "changed. Made by experiments/2026-11-16-films-max/scripts/names_spec.py."
        ),
        "base": names.STOCK,
        "base_sha256": sha256_bytes(stock_file),
        "ops": ops,
        "status": "candidate: emulator-checked, not flashed",
    }
    Path(args.out).write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{args.out}: {len(ops)} ops")


if __name__ == "__main__":
    main()

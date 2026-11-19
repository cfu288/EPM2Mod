"""Static inventory of the code that reads the Picture Mode value or the art code (stock firmware 1.6, block 0).

    .venv/bin/python experiments/2026-11-16-films-max/scripts/readers.py [--image build/films-12.BIN] [--tsv OUT.tsv]

Needs build/map/linear.txt (the objdump sweep of tools/fwmap.py). It lists:

A  call sites of a settings getter with a constant id in d0 (or a0 for the mode controller's rule getter):
   the prm getter 0x7E457C75 with the tags of Picture Mode (0x9481), of settings 509 / 510 (0xDF31), of the ART
   mode code (0x2891), of Filter Type (0x44C1) and Add Effects (0x44D1); Get_CameraInfo 0x7E67F822 / 0x7E67F82B,
   the mode-controller getters 0x7E6FEA5F / 0x7E6FCC91 / 0x7E704B75 and the GUI's getSetting 0x7EE01D38 with the
   ids 111, 509, 510, 281;
B  reads of the art code byte of the image library's job block (`movbu (79,aN)`) in the image library;
C  reads of the mov layer's mode byte 0x605B1CD3 and code bytes 0x605B1CD2 / 0xA07507CC / 0x605B091C, and of the
   record context's Picture Mode (+16479) and art codes (+16456, +16460);
D  tables: jump tables read with (stored value - 100), and the jump and hash tables read with an art code
   (experiments/2026-11-09-film-portra/slots/artcode_inventory.json).

For A to C the 40 instructions after the read (up to a return) are scanned for compares with constants. Class:
  hidden    a compare with one of the hidden values 111, 112, 114, 115, 118 (A, C) or a new art code (B, C)
  stock     compares with stored values 100..120 / art codes of stock filters only: the new values take the
            branch "none of these" (the default branch: the case to read)
  range     only compares with 100 and 120 (a range test), or with 69 / 183 / 184 for codes
  none      no such compare: the value is stored, passed on or used as a table index (see D)
For D the entry of each hidden value / new art code in IMAGE is "own" (films-12 sets it), "as Pop Art" (the
stock entry is the one of Pop Art) or "default" (the stock entry or no key: the table's branch for a value it
does not know).

Limits: a scan of constants. It does not see a value that goes through memory or a register for more than 40
instructions, a compare in a callee, a computed table index, or data that is decoded as code.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "cli" / "src"))

from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import slots  # noqa: E402

BASE = 0x7E421020
HIDDEN = {slot.value for slot in slots.EXTRA_SLOTS}
NEW_CODES = {slot.art_code for slot in slots.EXTRA_SLOTS}
TAGS = {38017: "Picture Mode (prm 0x9481)", 57137: "settings 509/510 (prm 0xDF31)", 10385: "ART mode code (prm 0x2891)",
        17601: "Filter Type (prm 0x44C1)", 17617: "Add Effects (prm 0x44D1)"}
INFOS = {111: "setting 111", 509: "setting 509", 510: "setting 510", 281: "setting 281 (ART mode code)"}
PRM_GETTER = "0x7e457c75"
INFO_GETTERS = {"0x7e67f822": "d0", "0x7e67f82b": "d0", "0x7e6fea5f": "d0", "0x7e6fcc91": "d0", "0x7ee01d38": "d0", "0x7e704b75": "a0"}
ABSOLUTE = {"0x605b1cd3": "mov layer: Picture Mode byte", "0x605b1cd2": "mov layer: code byte", "0xa07507cc": "mov layer: expose code",
            "0x605b091c": "mov layer: mode byte of the frame"}
OFFSETS = {"16479": "record context: Picture Mode", "16456": "record context: art code", "16460": "record context: art code (2)"}
IMG = (0x7E544AA9, 0x7E581FAF)
LINE = re.compile(r"^([0-9a-f]{8}):\t[^\t]*\t(\S+)\t?(.*)$")
VALUE_TABLES = {"art_GetFilterType": 0x7E854A24, "live view still A": 0x7E7FF05C, "live view movie A": 0x7E7FF008,
                "live view still B": 0x7E807880, "live view movie B": 0x7E80782C, "record class by value": 0x7E8522AC,
                "EXIF case": 0x7E852300, "is art filter (application)": 0x7EBBAA10, "art packet mode 0x7E6CC9E8": 0x7E7FF400}
VALUE_HASHES = {"colour-tone name": 0x7EC4A864, "movie file tag": 0x7E810200, "record class": 0x7E851A94,
                "settings loader (art = cleared)": 0x7EBBAAE4, "B&W settings": 0x7EBBABE4, "Filter Type / Add Effects": 0x7EBBACE4}


def instructions() -> list[tuple[int, str, str]]:
    """The linear disassembly as (address, mnemonic, operands)."""
    out = []
    with open(ROOT / "build/map/linear.txt", errors="replace") as handle:
        for line in handle:
            match = LINE.match(line.rstrip("\n"))
            if match:
                out.append((int(match.group(1), 16), match.group(2), match.group(3).strip()))
    return out


def classify(code: list[tuple[int, str, str]], index: int, new: set[int], stock_low: int, stock_high: int, range_values: set[int]) -> tuple[str, list[int]]:
    """Class of a read at code[index], and the constants its next 40 instructions compare with."""
    seen: list[int] = []
    for _, mnemonic, operands in code[index + 1 : index + 41]:
        if mnemonic in ("ret", "retf", "rets"):
            break
        if mnemonic == "cmp":
            first = operands.split(",")[0]
            if first.isdigit():
                seen.append(int(first))
    values = [v for v in seen if stock_low <= v <= stock_high]
    if any(v in new for v in values):
        return "hidden", values
    if values and set(values) <= range_values:
        return "range", values
    if values:
        return "stock", values
    return "none", values


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--image", default=str(ROOT / "build/films-12.BIN"))
    parser.add_argument("--stock", default=str(ROOT / "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"))
    parser.add_argument("--tsv", default=str(ROOT / "experiments/2026-11-16-films-max/results/readers.tsv"))
    args = parser.parse_args()
    code = instructions()
    rows: list[tuple[str, int, str, str, str]] = []  # kind, address, what, class, compares

    for index, (address, mnemonic, operands) in enumerate(code):
        if not (0x7E430000 <= address < 0x7F1A0000):
            continue
        if mnemonic == "call":
            target = operands.split(",")[0]
            if target == PRM_GETTER or target in INFO_GETTERS:
                register = "d0" if target == PRM_GETTER else INFO_GETTERS[target]
                wanted = TAGS if target == PRM_GETTER else INFOS
                for _, m2, o2 in reversed(code[max(0, index - 8) : index]):
                    if m2 == "mov" and o2.endswith("," + register):
                        first = o2.split(",")[0]
                        if first.isdigit() and int(first) in wanted:
                            cls, values = classify(code, index, HIDDEN, 100, 120, {100, 120})
                            rows.append(("A", address, f"{wanted[int(first)]} through {target}", cls, " ".join(map(str, values))))
                        break
        elif mnemonic == "movbu" and "," in operands:
            source = operands.split(",d")[0] if operands.startswith("(") else ""
            if not source:
                continue
            inner = source.strip("()")
            if inner in ABSOLUTE:
                cls, values = classify(code, index, HIDDEN | NEW_CODES, 69, 184, {100, 120, 69, 183, 184})
                rows.append(("C", address, ABSOLUTE[inner], cls, " ".join(map(str, values))))
            elif inner.split(",")[0] == "79" and IMG[0] <= address < IMG[1]:
                cls, values = classify(code, index, NEW_CODES, 69, 184, {69, 183, 184, 168, 170})
                rows.append(("B", address, "job block: art code (+79)", cls, " ".join(map(str, values))))
        if mnemonic in ("movbu", "movhu") and operands.startswith("(") and operands.split(",")[0].strip("(") in OFFSETS and ",a" in operands.split(")")[0]:
            offset = operands.split(",")[0].strip("(")
            if operands.split(")")[1].startswith(",d"):
                is_mode = offset == "16479"
                cls, values = classify(code, index, HIDDEN if is_mode else NEW_CODES, 100 if is_mode else 69, 120 if is_mode else 184,
                                       {100, 120} if is_mode else {69, 183, 184})
                rows.append(("C", address, OFFSETS[offset], cls, " ".join(map(str, values))))

    block = parse(Path(args.image).read_bytes()).blocks[0].payload
    stock = parse(Path(args.stock).read_bytes()).blocks[0].payload
    word = lambda a: struct.unpack_from("<I", block, a - BASE)[0]
    for name, table in VALUE_TABLES.items():
        entries = [word(table + 4 * k) for k in range(21)]
        before = [struct.unpack_from("<I", stock, table - BASE + 4 * k)[0] for k in range(21)]
        pop_art = entries[0]
        for value in sorted(HIDDEN):
            entry = entries[value - 100]
            how = "own" if entry != before[value - 100] else ("as Pop Art" if entry == pop_art else "default")
            rows.append(("D", table, f"table by stored value: {name}, value {value}", how, f"{entry:#x}"))
    for name, table in VALUE_HASHES.items():
        keys = {word(table + 8 * k) for k in range(32)}
        for value in sorted(HIDDEN):
            rows.append(("D", table, f"hash by stored value: {name}, value {value}", "own" if value in keys else "default", ""))
    inventory = json.loads((ROOT / "experiments/2026-11-09-film-portra/slots/artcode_inventory.json").read_text())
    for item in inventory["jump"]:
        table, first, last = item["table"], item["K"], item["HI"]
        if table in (0x7E78C154, 0x7E852354):  # hash tables that the scan also read as jump tables
            continue
        entries = {c: word(table + 4 * (c - first)) for c in range(first, last + 1)}
        common = collections.Counter(entries.values()).most_common(1)[0][0]
        for art in sorted(NEW_CODES):
            if first <= art <= last:
                rows.append(("D", table, f"jump table by art code (first {first}), code {art}", "own" if entries[art] != common else "default", f"{entries[art]:#x}"))
            else:
                rows.append(("D", table, f"jump table by art code (first {first}, last {last}), code {art}", "default", "outside the table"))
    for item in inventory["hash"]:
        table, first = item["table"], item["K"]
        if table in (0x7E7FDBE0, 0x7E8045B0, 0x7E851810, 0x7E853DB8):  # ISO and other keys
            continue
        keys = {word(table + 8 * k) + first for k in range(32) if word(table + 8 * k)}
        for art in sorted(NEW_CODES):
            rows.append(("D", table, f"hash by art code (key = code - {first}), code {art}", "own" if art in keys else "default", ""))

    Path(args.tsv).write_text("kind\taddress\twhat\tclass\tcompares or entry\n" + "".join(
        f"{kind}\t{address:#010x}\t{what}\t{cls}\t{extra}\n" for kind, address, what, cls, extra in rows))
    for kind, title in (("A", "settings getter call sites"), ("B", "art code byte reads (image library)"), ("C", "mov-layer and record-context reads"), ("D", "table entries (per value / code)")):
        mine = [row for row in rows if row[0] == kind]
        count = collections.Counter(row[3] for row in mine)
        print(f"{kind} {title}: {len(mine)}: " + ", ".join(f"{k} {v}" for k, v in sorted(count.items())))
        if kind == "A":
            for what, n in sorted(collections.Counter(row[2] for row in mine).items()):
                print(f"    {n:3d} {what}")
        if kind != "D":
            for row in mine:
                if row[3] in ("stock", "hidden"):
                    print(f"    {row[3]:6s} {row[1]:#010x} {row[2]}: compares {row[4]}")
        else:
            for row in mine:
                if row[3] == "default":
                    print(f"    default {row[1]:#010x} {row[2]} {row[4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

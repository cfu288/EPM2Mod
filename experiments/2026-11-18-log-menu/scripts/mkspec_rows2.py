"""Write data/specs/custom-menu-rows-2.json: the Custom Menu of data/specs/custom-menu-rows.json with one row more, Debug
Log (setting 447, the stock Off / On panel 608) at the end of J, after Load Looks. It takes the place of
custom-menu-rows; no stock row is changed.

    uv run python experiments/2026-11-18-log-menu/scripts/mkspec_rows2.py

Changes against custom-menu-rows (design.md, finding 8):
  item table: 82 rows + the end group at 0x7EBF1FF0, to 0x7EBF2512 (0x7EBF2502-0x7EBF2600 is free);
  child list: 82 entries + the zero entry, moved to segment 3 data at 0x7EE3CBF4 (in place it would end at
    0x7EBF2898, and card-looks-4's code starts at 0x7EBF2890); the 11 page records point at it;
  row constants: last index 81, count 82, row-state array 164 B; rows in group J 7 -> 8;
  panel 608 gets a value -> text list (Off 0, On 1) after the child list.
The row's label and help are the unused built-in EVF texts 1507 and 1508; the log's GUI routine
(data/specs/log-menu.json) points them at "Debug Log" and its help in the loaded language's table in RAM.
Every expect is a byte string of the specs before custom-menu-rows in data/builds/card-looks-4.json.
"""

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod.container import parse  # noqa: E402
from epm2mod.spec import BytesOp, load_spec  # noqa: E402

SPEC = "custom-menu-rows-2"
OLD = "custom-menu-rows"
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
ITEMS, OLD_KIDS, KIDS = 0x7EBF1FF0, 0x7EBF2600, 0x7EE3CBF4
ROWS = 82
LABEL, HELP = 1507, 1508                         # unused built-in EVF texts (1499, 1501, 1502 are peaking-colours')
SETTING, PANEL = 447, 608
LOG_ROW = struct.pack("<HHIHHHH", 9, LABEL, SETTING, 7, HELP, PANEL, 0)
LOG_KID = struct.pack("<II", PANEL, SETTING)
VALUES = KIDS + ROWS * 8 + 8                       # the value -> text list of panel 608
VLIST = 0x7F014F94                                 # value -> text list word of panel 608 (0 in stock)
OFF, ON = 1371, 198                                # the stock texts of panel 608's two items
SIZES = 0x7E8DA000 + (0x602BE390 - 0x602A9B40)
CONSTS = {                                         # custom-menu-rows' value -> this spec's value
    "2da200": ("2da400", "clear the row-state array, 162 -> 164 bytes"),
    "a550": ("a551", "cmp last index 80 -> 81"),
    "aa51": ("aa52", "cmp row count 81 -> 82"),
    "8550": ("8551", "wrap to last index 80 -> 81"),
    "8050": ("8051", "wrap to last index 80 -> 81"),
    "a050": ("a051", "cmp last index 80 -> 81"),
}


def base_block():
    """Block 0 of the specs before custom-menu-rows in data/builds/card-looks-4.json."""
    specs = json.load(open(os.path.join(ROOT, "data", "builds", "card-looks-4.json")))["specs"]
    before = specs[:specs.index("data/specs/%s.json" % OLD)]
    blk = bytearray(parse(open(os.path.join(ROOT, STOCK), "rb").read()).blocks[0].payload)
    for s in before:
        for o in load_spec(Path(ROOT, s)).ops:
            if isinstance(o, BytesOp) and o.block == 0:
                assert bytes(blk[o.offset:o.offset + len(o.expect)]) == o.expect, s
                blk[o.offset:o.offset + len(o.new)] = o.new
    return bytes(blk)


def main():
    old = json.load(open(os.path.join(ROOT, "data", "specs", OLD + ".json")))
    blk = base_block()
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    for o in old["ops"]:
        a = o.get("_addr")
        note = o["_note"]
        if a == "0x%08X" % ITEMS:
            items = bytes.fromhex(o["new"])
            assert len(items) == 81 * 16 + 2 and struct.unpack_from("<H", items, 81 * 16)[0] == 98
            assert struct.unpack_from("<HHI", items, 80 * 16) == (9, 1498, 449)          # Load Looks, the last of J
            op(ITEMS, items[:81 * 16] + LOG_ROW + items[81 * 16:], "Custom Menu item table, 82 rows + the end group "
               "98: the 81 rows of custom-menu-rows and {group 9, text %d 'Debug Log', setting %d, order 7, help %d, "
               "value list %d, 0} at index 81, after Load Looks" % (LABEL, SETTING, HELP, PANEL))
        elif a == "0x%08X" % OLD_KIDS:
            kids = bytes.fromhex(o["new"])
            assert len(kids) == 82 * 8 and kids[-8:] == bytes(8)
            op(KIDS, kids[:81 * 8] + LOG_KID + bytes(8), "Custom Menu child list, 82 entries + zero entry, in segment "
               "3 data: custom-menu-rows' list and (panel %d, setting %d) at index 81" % (PANEL, SETTING))
        elif note.startswith("page record"):
            assert o["new"] == struct.pack("<I", OLD_KIDS).hex()
            op(int(a, 16), struct.pack("<I", KIDS), note.split(":")[0] + ": child list 0x7EBF3500 -> 0x%08X" % KIDS)
        elif o["new"] in CONSTS:
            new, what = CONSTS[o["new"]]
            where = note.split(":")[0]
            op(int(a, 16), bytes.fromhex(new), "%s: %s" % (where, what))
        elif note.startswith(".data image") and "group 9" in note:
            op(int(a, 16), struct.pack("<H", 8), ".data image (RAM 0x602BE3A2): rows in group 9 (J), 6 -> 8 "
               "(Load Looks, Debug Log)")
        else:
            n = dict(o)
            if o["block"] == 0:
                assert get(int(a, 16), len(o["new"]) // 2).hex() == o["expect"], note
            n["_note"] = note + " (as custom-menu-rows)"
            ops.append(n)
    vals = b"".join(struct.pack("<iiiiii", v, 2, t, 0, 0, 0) for v, t in ((0, OFF), (1, ON))) + \
        struct.pack("<iiiiii", -15, 0, 0, 0, 0, 0)
    op(VALUES, vals, "value -> text list of the Debug Log row: 0 Off (text %d), 1 On (text %d), end mark -15 (24 B "
       "each, the layout of the Peaking row's list)" % (OFF, ON))
    assert get(VLIST, 4) == bytes(4)
    op(VLIST, struct.pack("<I", VALUES), "value -> text list 608: null -> 0x%08X" % VALUES)
    assert get(0x7F00BFCC, 4) == struct.pack("<HH", SETTING, 2), "panel 608 is not the Off / On list of setting 447"
    seen = {o["_note"].split(":")[0] for o in ops}
    assert sum(1 for o in ops if o["_note"].startswith("page record")) == 11, seen
    spec = {
        "name": SPEC,
        "description": (
            "The Custom Menu with three added rows: Peaking in A after MF Assist, Load Looks in J after Eye-Fi (both "
            "as data/specs/custom-menu-rows.json, whose place this spec takes) and Debug Log in J after Load Looks "
            "(setting %d, the stock Off / On list panel %d; Off is 0, the setting's default). No stock row is "
            "changed. An 82-row copy of the item table at 0x7EBF1FF0 (10 address loads re-pointed), an 82-entry "
            "child list in segment 3 data at 0x%08X (11 page records re-pointed), 9 row constants (last index 81, "
            "count 82, row-state array 164 B), the group sizes of A (11) and J (8), and a value -> text list for "
            "panel %d. The row's texts %d and %d are pointed at English strings by data/specs/log-menu.json. Every "
            "expect is a byte string of the specs before custom-menu-rows in data/builds/card-looks-4.json. See "
            "experiments/2026-11-18-log-menu/design.md." % (SETTING, PANEL, KIDS, PANEL, LABEL, HELP)),
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_ram": "the row-state array of the Custom Menu page grows by 6 bytes (158 -> 164) into 0x606A31B6-BB (the "
                "next addressed object is 0x606A32F0)",
        "ops": ops,
    }
    with open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "w") as fh:
        json.dump(spec, fh, indent=1)
        fh.write("\n")
    print("wrote data/specs/%s.json: %d ops" % (SPEC, len(ops)))


if __name__ == "__main__":
    main()

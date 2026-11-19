"""Write data/specs/custom-menu-rows.json: the Custom Menu with two added rows, Peaking (as data/specs/peaking-menu.json)
and Load Looks (at the end of J, after Eye-Fi). It takes the place of peaking-menu; no stock row is changed.

    uv run python experiments/2026-11-17-card-looks/scripts/mkspec_rows.py

peaking-menu put an 80-row copy of the item table at 0x7EBF2000 and an 80-entry child list at 0x7EBF2600. This spec
writes all of peaking-menu's other operations unchanged (the Peaking list, its texts, its code: camera-tested bytes),
and the two tables with one row more:
  item table: 81 rows + the end group at 0x7EBF1FF0 (0x7EBF1FF0-0x7EBF2000 is free; the table ends at 0x7EBF2502,
    where peaking-menu's ended), the 10 address loads pointed at it;
  child list: 81 entries + the zero entry at 0x7EBF2600, to 0x7EBF2890 (the loader's first run starts there);
  row constants from level-adjust-row's (last index 78, count 79, row-state array 158 B) to 80, 81, 162 B;
  rows in group A (0) 10 -> 11 and in group J (9) 6 -> 7 in the .data image.
The row Load Looks is {group 9, text 1498, setting 449, order 6, help 1497, value list 610, 0} with the child entry
(panel 610, setting 449); its list, texts and status are data/specs/looks-menu-3.json (mkspec_lmenu.py --v4).
Every expect is a byte string of the specs before peaking-menu in data/builds/card-looks-3.json.
"""
import hashlib, json, os, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from epm2mod.container import parse  # noqa: E402
import mkspec_slots  # noqa: E402

SPEC = "custom-menu-rows"
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
OLD_ITEMS, OLD_KIDS = 0x7EBF3000, 0x7EBF3500          # level-adjust-row's tables (79 rows)
ITEMS, KIDS = 0x7EBF1FF0, 0x7EBF2600
ROWS = 81
LOAD_ROW = struct.pack("<HHIHHHH", 9, 1498, 449, 6, 1497, 610, 0)
LOAD_KID = struct.pack("<II", 610, 449)
SIZES = 0x7E8DA000 + (0x602BE390 - 0x602A9B40)
CONSTS = (
    (0x7EDE9AE5, "2d9e00", "2da200", "constructor: clear the row-state array, 158 -> 162 bytes"),
    (0x7EDE9B85, "a54e", "a550", "open: cmp last index 78 -> 80"),
    (0x7EDE9B92, "aa4f", "aa51", "open: cmp row count 79 -> 81"),
    (0x7EDE9CBA, "854e", "8550", "UP: wrap to last index 78 -> 80"),
    (0x7EDE9D10, "804e", "8050", "UP, skip a greyed row: wrap to last index 78 -> 80"),
    (0x7EDE9D26, "aa4f", "aa51", "UP: cmp row count 79 -> 81"),
    (0x7EDE9D6B, "a04e", "a050", "DOWN: cmp last index 78 -> 80"),
    (0x7EDE9DBF, "a54e", "a550", "DOWN, skip a greyed row: cmp last index 78 -> 80"),
    (0x7EDE9DCC, "aa4f", "aa51", "DOWN: cmp row count 79 -> 81"),
)


def main():
    peak = json.load(open(os.path.join(ROOT, "data", "specs", "peaking-menu.json")))
    build = json.load(open(os.path.join(ROOT, "data", "builds", "card-looks-3.json")))["specs"]
    before = build[:build.index("data/specs/peaking-menu.json")]
    work = os.path.join(ROOT, "build", "card-looks")
    os.makedirs(work, exist_ok=True)
    out = os.path.join(work, "before-rows.BIN")
    subprocess.run(["uv", "run", "epm2mod", "apply", *before, "--from", "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "-o", out], cwd=ROOT, check=True, capture_output=True)
    blk = parse(open(out, "rb").read()).blocks[0].payload
    get = lambda a, n: bytes(blk[a - BASE:a - BASE + n])
    by_addr = {o.get("_addr"): o for o in peak["ops"]}
    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new, note
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    # the tables: peaking-menu's, with the row Load Looks at the end of J
    items = bytes.fromhex(by_addr["0x7EBF2000"]["new"])
    assert len(items) == 80 * 16 + 2 and struct.unpack_from("<H", items, 80 * 16)[0] == 98
    assert struct.unpack_from("<HHIH", items, 79 * 16) == (9, 1447, 404, 5)            # Eye-Fi, the last row of J
    op(ITEMS, items[:80 * 16] + LOAD_ROW + items[80 * 16:], "Custom Menu item table, 81 rows + the end group 98: "
       "the 80 rows of peaking-menu's table (Peaking at index 7) and {group 9, text 1498 'Load Looks', setting 449, "
       "order 6, help 1497, value list 610, 0} at index 80, after Eye-Fi")
    kids = bytes.fromhex(by_addr["0x7EBF2600"]["new"])
    assert len(kids) == 81 * 8 and kids[-8:] == bytes(8)
    op(KIDS, kids[:80 * 8] + LOAD_KID + bytes(8), "Custom Menu child list, 81 entries + zero entry: peaking-menu's "
       "list and (panel 610, setting 449) at index 80")
    for o in peak["ops"]:
        a = o.get("_addr")
        if a in ("0x7EBF2000", "0x7EBF2600") or o["_note"].startswith(("constructor", "open:", "UP", "DOWN", ".data")):
            continue
        if o["_note"].startswith("item-table address"):
            addr = int(a, 16)
            assert get(addr, 6)[2:] == struct.pack("<I", OLD_ITEMS)
            op(addr, get(addr, 2) + struct.pack("<I", ITEMS), "item-table address 0x%08X -> 0x%08X" % (OLD_ITEMS, ITEMS))
            continue
        if o["_note"].startswith("page record"):
            assert get(int(a, 16), 4) == struct.pack("<I", OLD_KIDS)
        n = dict(o)
        if o["block"] == 0:
            assert get(int(a, 16), len(o["new"]) // 2).hex() == o["expect"], o["_note"]
        n["_note"] = o["_note"] + " (as peaking-menu)"
        ops.append(n)
    for a, was, new, note in CONSTS:
        assert get(a, len(was) // 2) == bytes.fromhex(was), "%08X" % a
        op(a, bytes.fromhex(new), note)
    sizes = struct.unpack("<10H", get(SIZES, 20))
    assert sizes == (10, 4, 6, 17, 13, 3, 8, 7, 5, 6) and sum(sizes) == 79, sizes
    op(SIZES, struct.pack("<H", 11), ".data image (RAM 0x602BE390): rows in group 0 (A), 10 -> 11 (Peaking)")
    op(SIZES + 18, struct.pack("<H", 7), ".data image (RAM 0x602BE3A2): rows in group 9 (J), 6 -> 7 (Load Looks)")
    spec = {
        "name": SPEC,
        "description": (
            "The Custom Menu with two added rows: Peaking in A after MF Assist (Off / White / Black; everything of "
            "data/specs/peaking-menu.json, whose place this spec takes: its list, texts and code unchanged) and Load Looks "
            "in J after Eye-Fi (setting 449, list panel 610: data/specs/looks-menu-3.json). No stock row is changed. An "
            "81-row copy of the item table at 0x7EBF1FF0 (10 address loads re-pointed), an 81-entry child list at "
            "0x7EBF2600 (11 page records re-pointed), 9 row constants (last index 80, count 81, row-state array 162 B) "
            "and the group sizes of A (11) and J (7) in the .data image. Every expect is a byte string of the specs "
            "before peaking-menu in data/builds/card-looks-3.json. See experiments/2026-11-17-card-looks/design.md section 10.2."),
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "_ram": "the row-state array of the Custom Menu page grows by 4 bytes (158 -> 162) into 0x606A31B6-B9 (the "
                "next addressed object is 0x606A32F0)",
        "ops": ops,
    }
    with open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "w") as fh:
        json.dump(spec, fh, indent=1)
        fh.write("\n")
    print("wrote data/specs/%s.json: %d ops" % (SPEC, len(ops)))


if __name__ == "__main__":
    main()

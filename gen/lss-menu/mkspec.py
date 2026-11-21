"""Write the menu part of "Lowest S/S Setting" (GitHub issue #2): two specs.

    uv run python gen/lss-menu/mkspec.py

data/specs/custom-menu-rows-3.json takes the place of custom-menu-rows-2 in data/builds/stock-films.json. It is
custom-menu-rows-2 with one row more: "Lowest S/S Setting" in group E before ISO-Auto Set (setting 653, panel 609,
value -> text list 609). Why a new spec and not a delta: a delta cannot move or grow custom-menu-rows-2's item table,
because `epm2mod make` refuses a change to a byte that custom-menu-rows-2 covers and keeps (byte 0xBF of the 10
address loads, and 81 bytes of the table). NOTES.md section 11.
  item table: 83 rows + the end group at 0x7EBF1FE0 (16 B earlier than custom-menu-rows-2's, so it still ends at
    0x7EBF2512, where stock-films-structure's BK0 starts); the 10 address loads point at it;
  child list: 84 entries in place at 0x7EE3CBF4 (8 B longer); Debug Log's value -> text list moves 8 B to 0x7EE3CE94;
  row constants: last index 82, count 83, row-state array 166 B; rows in group E 13 -> 14.
Every expect is a byte string of the specs before custom-menu-rows-2 in data/builds/stock-films.json.

data/specs/lss-menu.json goes last. Setting 653 (prm tag 0x9F11, MODE bank, u8; ROM and full-reset default 0), the list
of panel 609 (56 items: Auto, 60" ... 1/4000 in 1/3 EV; the stored value is the index 0..55), the value -> text list
609, and the English texts 1503 (label) and 1504 (help).
"""

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod.container import parse  # noqa: E402
from epm2mod.spec import apply_specs, load_spec  # noqa: E402

BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
BUILD = "data/builds/stock-films.json"
OLD = "custom-menu-rows-2"
ROWS3 = "custom-menu-rows-3"
LSS = "lss-menu"

# custom-menu-rows-3
OLD_ITEMS, ITEMS_TABLE, KIDS = 0x7EBF1FF0, 0x7EBF1FE0, 0x7EE3CBF4
OLD_ROWS, ROWS = 82, 83
SETTING, PANEL, LABEL, HELP = 653, 609, 1503, 1504
AT = 43                                          # index of ISO-Auto Set in custom-menu-rows-2's table; the new row goes there
# (before ISO-Auto Set: slot 6 of the page. In slot 7, the last, the # Slow Limit value box draws its field 20 px
# below its text and arrows; NOTES.md section 11)
ROW = struct.pack("<HHIHHHH", 4, LABEL, SETTING, 11, HELP, PANEL, 0)   # order 11: unused in group E
KID = struct.pack("<II", PANEL, SETTING)
OLD_DLOG_VT, DLOG_VT, DLOG_WORD = 0x7EE3CE8C, KIDS + (ROWS + 1) * 8, 0x7F014F94
GROUP_E = 0x7E8EE850 + 2 * 4                     # .data image (RAM 0x602BE398): rows in group 4 (E)
CONSTS = {                                       # custom-menu-rows-2's value -> this spec's value
    "2da400": ("2da600", "clear the row-state array, 164 -> 166 bytes"),
    "a551": ("a552", "cmp last index 81 -> 82"),
    "aa52": ("aa53", "cmp row count 82 -> 83"),
    "8551": ("8552", "wrap to last index 81 -> 82"),
    "8051": ("8052", "wrap to last index 81 -> 82"),
    "a051": ("a052", "cmp last index 81 -> 82"),
}

# lss-menu
AREA = (0x7EBB1F4C, 0x7EBB304C)                  # Bluetooth debug strings, reclaim-space row 2 (NEEDS-DECISION)
LIST = AREA[0]                                   # 56 items x 28 B
NAMES = LIST + 56 * 28                           # value -> text list, 57 x 24 B
DESC = 0x7F00BFDC                                # list descriptor of panel 609 (stock: setting 448, 2 items)
VT_WORD = 0x7F014614 + 4 * PANEL                 # value -> text list word of panel 609 (stock: 0)
REGISTRY = 0x7EFE1AFC                            # menu-page registry entry {u16 list 609, 0, create}
GENERIC, SPIN = 0x7EDC7ECB, 0x7EE01678           # generic list page (wraps after 40 items); # Slow Limit's page class
SLOW = 0x7F006EE4                                # stock # Slow Limit items: 30" ... 1/250 (40 x 28 B)
AUTO_TEXT = 71                                   # "Auto", as the first item of the ISO list (0x7F006B9C)
TEXTS = {LABEL: "Lowest S/S Setting",
         HELP: "Choose the shutter speed at\r\nwhich the camera raises\r\nISO in P and A."}
SPEEDS = ['Auto', '60"', '50"', '40"', '30"', '25"', '20"', '15"', '13"', '10"', '8"', '6"', '5"', '4"', '3.2"',
          '2.5"', '2"', '1.6"', '1.3"', '1"', '1/1.3', '1/1.6', '1/2', '1/2.5', '1/3', '1/4', '1/5', '1/6', '1/8',
          '1/10', '1/13', '1/15', '1/20', '1/25', '1/30', '1/40', '1/50', '1/60', '1/80', '1/100', '1/125', '1/160',
          '1/200', '1/250', '1/320', '1/400', '1/500', '1/640', '1/800', '1/1000', '1/1250', '1/1600', '1/2000',
          '1/2500', '1/3200', '1/4000']


def image(specs):
    """Blocks 0 and 1 of stock + specs."""
    stock = open(os.path.join(ROOT, STOCK), "rb").read()
    if not specs:
        c = parse(stock)
    else:
        c = parse(apply_specs(stock, [load_spec(Path(ROOT, s)) for s in specs]).image)
    return bytes(c.blocks[0].payload), bytes(c.blocks[1].payload)


class Ops:
    """A list of bytes ops against one base image."""

    def __init__(self, b0, b1):
        self.b0, self.b1, self.ops = b0, b1, []

    def get(self, a, n):
        return self.b0[a - BASE:a - BASE + n]

    def add(self, addr, new, note):
        expect = self.get(addr, len(new))
        assert expect != new, note
        self.ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                         "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    def text(self, blob, tid, s):
        off = blob.offset(tid)
        old = blob.text(tid)
        assert len(s) <= len(old), (tid, s)
        expect = self.b1[off:off + 2 * len(old) + 2]
        new = s.encode("utf-16-le").ljust(len(expect), b"\0")
        self.ops.append({"type": "bytes", "block": 1, "offset": "0x%X" % off, "expect": expect.hex(),
                         "new": new.hex(), "_note": "English text %d: %r -> %r" % (tid, old, s)})


def spec(name, description, ops, **extra):
    d = {"name": name, "description": description, "base": STOCK,
         "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
         "status": "candidate: emulator-checked, not flashed"}
    d.update(extra)
    d["ops"] = ops
    with open(os.path.join(ROOT, "data", "specs", name + ".json"), "w") as fh:
        json.dump(d, fh, indent=1)
        fh.write("\n")
    print("wrote data/specs/%s.json: %d ops" % (name, len(ops)))


def rows3(specs):
    before = specs[:specs.index("data/specs/%s.json" % OLD)]
    o = Ops(*image(before))
    old = json.load(open(os.path.join(ROOT, "data", "specs", OLD + ".json")))
    for x in old["ops"]:
        a, note = x.get("_addr"), x["_note"]
        if a == "0x%08X" % OLD_ITEMS:
            t = bytes.fromhex(x["new"])
            assert len(t) == OLD_ROWS * 16 + 2
            assert struct.unpack_from("<HHI", t, AT * 16) == (4, 155, 2000), "row 43 is not ISO-Auto Set"
            assert struct.unpack_from("<HH", t, (AT + 1) * 16) == (4, 154), "row 44 is not ISO-Auto"
            cut = AT * 16
            o.add(ITEMS_TABLE, t[:cut] + ROW + t[cut:], "Custom Menu item table, 83 rows + the end group 98: the 82 "
                  "rows of custom-menu-rows-2 and {group 4, text %d 'Lowest S/S Setting', setting %d, order 11, help "
                  "%d, value list %d, 0} at index %d, before ISO-Auto Set" % (LABEL, SETTING, HELP, PANEL, AT))
        elif a == "0x%08X" % KIDS:
            k = bytes.fromhex(x["new"])
            assert len(k) == (OLD_ROWS + 1) * 8 and k[-8:] == bytes(8)
            assert struct.unpack_from("<II", k, AT * 8) == (143, 112), "child 43 is not ISO-Auto Set's"
            cut = AT * 8
            o.add(KIDS, k[:cut] + KID + k[cut:], "Custom Menu child list, 84 entries + zero entry, in place (8 B "
                  "longer): custom-menu-rows-2's list and (panel %d, setting %d) at index %d" % (PANEL, SETTING, AT))
        elif note.startswith("item-table address"):
            assert x["new"].endswith(struct.pack("<I", OLD_ITEMS).hex())
            o.add(int(a, 16), bytes.fromhex(x["new"][:4]) + struct.pack("<I", ITEMS_TABLE),
                  "item-table address -> 0x%08X" % ITEMS_TABLE)
        elif a == "0x%08X" % OLD_DLOG_VT:
            o.add(DLOG_VT, bytes.fromhex(x["new"]), note.replace("Debug Log row", "Debug Log row, moved 8 B to "
                                                                 "0x%08X" % DLOG_VT))
        elif a == "0x%08X" % DLOG_WORD:
            o.add(DLOG_WORD, struct.pack("<I", DLOG_VT), "value -> text list 608: null -> 0x%08X" % DLOG_VT)
        elif x["new"] in CONSTS:
            new, what = CONSTS[x["new"]]
            o.add(int(a, 16), bytes.fromhex(new), "%s: %s" % (note.split(":")[0], what))
        else:
            n = dict(x)
            blk = o.b0 if x["block"] == 0 else o.b1
            off = int(x["offset"], 16)
            assert blk[off:off + len(x["new"]) // 2].hex() == x["expect"], note
            n["_note"] = note + " (as custom-menu-rows-2)"
            o.ops.append(n)
    assert struct.unpack("<H", o.get(GROUP_E, 2))[0] == 13
    o.add(GROUP_E, struct.pack("<H", 14), ".data image (RAM 0x602BE398): rows in group 4 (E), 13 -> 14 (Lowest S/S "
          "Setting)")
    assert sum(1 for x in o.ops if x["_note"].startswith("item-table address")) == 10
    assert sum(1 for x in o.ops if x["_note"].startswith("page record")) == 11
    assert sum(1 for x in o.ops if x["new"] in [v[0] for v in CONSTS.values()]) == 9
    spec(ROWS3, "The Custom Menu with four added rows: Peaking in A after MF Assist, Load Looks and Debug Log in J "
         "(all three as data/specs/custom-menu-rows-2.json, whose place this spec takes) and Lowest S/S Setting in E "
         "before ISO-Auto Set (setting %d, panel %d, value -> text list %d; the list and texts are in "
         "data/specs/lss-menu.json, which a build with this spec needs). No stock row is changed. An 83-row copy of the "
         "item table at 0x%08X (10 address loads re-pointed), the 84-entry child list in place at 0x%08X (Debug Log's "
         "value -> text list moved to 0x%08X), 9 row constants (last index 82, count 83, row-state array 166 B), the "
         "group sizes of A (11), E (14) and J (8). Every expect is a byte string of the specs before "
         "custom-menu-rows-2 in %s. See experiments/2026-11-17-auto-iso-min-shutter/NOTES.md section 11."
         % (SETTING, PANEL, PANEL, ITEMS_TABLE, KIDS, DLOG_VT, BUILD), o.ops,
         _ram="the row-state array of the Custom Menu page grows by 8 bytes (158 -> 166) into 0x606A31B6-BD (the "
              "next addressed object is 0x606A32F0)")


def item(kind, a, b, c, d, value):
    return struct.pack("<BBHHHIIiII", 0, kind, a, b, c, d, 2000, value, 192, 197)


def name(kind, a, b, c, d, value):
    return struct.pack("<iiHHIIi", value, kind, a, b, c, d, 0)


def lss(specs):
    o = Ops(*image(specs))
    stock_items = [struct.unpack("<BBHHHIIiII", o.get(SLOW + 28 * i, 28)) for i in range(40)]
    assert struct.unpack("<HHIII", o.get(0x7F00BF6C, 16)) == (174, 40, 1, 1, SLOW)
    assert all(f[6:] == (2000, f[7], 192, 197) for f in stock_items)
    fields = [(2, AUTO_TEXT, 0, 0, 0)]                                   # Auto
    fields += [(3, 0, 2, n, 0) for n in (60, 50, 40)]                    # 60" 50" 40": kind 3 as the stock 30"
    fields += [f[1:6] for f in stock_items]                              # 30" ... 1/250: the stock records
    fields += [(8, 1, n, 0, 0) for n in (320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000)]
    assert len(fields) == len(SPEEDS) == 56
    for (k, a, b, c, d), s in zip(fields, SPEEDS):                       # the text each record shows
        if k == 2:
            got = "Auto"
        elif k == 3:
            got = ("%d.%d" % divmod(c, 100) if a == 1 else str(c)) + '"'
        else:
            got = "1/" + ("%d.%d" % divmod(b, 100) if d == 0x10000 else str(b))
        assert got == s, (got, s)
    items = b"".join(item(*f, i) for i, f in enumerate(fields))
    names = b"".join(name(*f, i) for i, f in enumerate(fields)) + name(0, 0, 0, 0, 0, -15)
    assert NAMES + len(names) <= AREA[1]
    o.add(LIST, items, "list items of panel 609: Auto (value 0, text %d), 60\" (1) ... 1/4000 (55); 28 B each; "
          "30\" ... 1/250 are the stock # Slow Limit records (0x%08X) with the index as value" % (AUTO_TEXT, SLOW))
    o.add(NAMES, names, "value -> text list of the row: 0 Auto ... 55 1/4000, end mark -15 (24 B each, the layout "
          "of the stock # Slow Limit list 0x7F012FF4)")
    assert struct.unpack("<HHIII", o.get(DESC, 16)) == (448, 2, 0, 1, 0x7F007520)
    o.add(DESC, struct.pack("<HHIII", SETTING, 56, 0, 1, LIST), "list descriptor of panel 609: setting 448, 2 items "
          "at 0x7F007520 -> setting %d, 56 items at 0x%08X" % (SETTING, LIST))
    assert struct.unpack("<HHI", o.get(REGISTRY, 8)) == (PANEL, 0, GENERIC)
    o.add(REGISTRY + 4, struct.pack("<I", SPIN), "menu-page registry, list 609: the generic list page 0x%08X (its "
          "cursor wraps after 40 items) -> 0x%08X, the page class of # Slow Limit (list 148) and of the Interval "
          "Frame list 638 (128 items)" % (GENERIC, SPIN))
    assert o.get(VT_WORD, 4) == bytes(4)
    o.add(VT_WORD, struct.pack("<I", NAMES), "value -> text list 609: null -> 0x%08X" % NAMES)
    import importlib.util
    m = importlib.util.spec_from_file_location("fns", os.path.join(
        HERE, "film_names_spec.py"))       # a copy of experiments/2026-11-14-emulator-audit/scripts/film_names_spec.py
    fns = importlib.util.module_from_spec(m)
    m.loader.exec_module(fns)
    eng = next(b for b in (fns.Blob(o.b1, e) for e in range(1, 35)) if b.code.upper().startswith("EN"))
    for tid, s in TEXTS.items():
        o.text(eng, tid, s)
    spec(LSS, "Lowest S/S Setting (GitHub issue #2), the menu part: the list and texts of the row that "
         "data/specs/custom-menu-rows-3.json adds to Custom Menu E before ISO-Auto Set. Setting %d (prm tag 0x9F11, MODE "
         "bank, u8, ROM and full-reset default 0; no stock code reads or writes it, experiments/2026-11-18-look-editor"
         "/settings.md) holds the index 0..55 of: Auto, 60\", 50\", 40\", 30\" ... 1/250 (the stock # Slow Limit "
         "records), 1/320 ... 1/4000. Panel 609 (a list page of the dormant setting 448) gets the 56 items, the "
         "page class of # Slow Limit (the generic list page wraps after 40 items) and a value -> text list, both in the Bluetooth debug strings 0x%08X-0x%08X (segment 2, reclaim-space row "
         "2). English texts 1503 (label) and 1504 (help) of the unreachable panel 594 'EVF Info Settings'. No code."
         % (SETTING, AREA[0], AREA[1]), o.ops,
         _interface="setting 653 = prm tag 0x9F11 (MODE bank, u8), RAM 0x60413225 in the emulator; value = index: "
                    "0 Auto, i = 1..55 -> Tv (Q8) = trunc((i - 19) * 256 / 3), 1 = 60 s, 19 = 1 s, 55 = 1/4000")


def main():
    specs = json.load(open(os.path.join(ROOT, BUILD)))["specs"]
    rows3(specs)
    specs = [s.replace(OLD, ROWS3) for s in specs]
    lss(specs)


if __name__ == "__main__":
    main()

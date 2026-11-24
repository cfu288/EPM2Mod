"""Write the menu part of spot metering at the AF target: two specs.

    uv run python gen/spot-menu/mkspec.py

data/specs/custom-menu-rows-4.json takes the place of custom-menu-rows-3 in data/builds/spot-af.json. It is
custom-menu-rows-3 with one row more: "Spot Metering" in group E after AEL Metering (setting 2000: it opens page 594;
child (594, 1) so the row is greyed where Metering is). Why a new spec and not a delta: as custom-menu-rows-3 (a delta
cannot grow the item table that custom-menu-rows-3 covers and keeps).
  item table: 84 rows + the end group at 0x7EBF1FD0 (16 B earlier than custom-menu-rows-3's, so it still ends at
    0x7EBF2512, where stock-films-structure's BK0 starts); the 10 address loads point at it;
  child list: 85 entries in place at 0x7EE3CBF4 (8 B longer); Debug Log's value -> text list moves 8 B to 0x7EE3CE9C;
  row constants: last index 83, count 84, row-state array 168 B; rows in group E 14 -> 15.
Every expect is a byte string of the specs before custom-menu-rows-3 in data/builds/peaking-mf.json.

data/specs/spot-menu.json goes last. Page 594 (the sub-item page class of LV-Info, "EVF Info Settings", which no menu
reaches since level-gauge-lvinfo-row) becomes "Spot Metering" with three On/Off rows: Spot (setting 593, prm 0x94D1),
Spot Hilight (660, 0x9F91), Spot Shadow (621, 0x9821), the stock texts 171, 106, 107. Their pickers are the generic
list pages 198, 584, 659 (no table names them; only their descriptors change), the On/Off value records of the
settings 446, 448, 449 are re-keyed to the three settings, and page 594 gets a child list at 0x7EE3CEE4. The label
(1494) and help (1509) are unused built-in EVF texts: the film loader (data/specs/card-looks-9.json) points them at
"Spot Metering" and the help in the loaded language, so they read the same in every menu language. No code.
experiments/2026-11-24-af-spot-metering/NOTES.md, E3, E4 and "Build spot-af".
"""

import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "gen", "lss-menu"))
from mkspec import Ops, image, spec  # noqa: E402  (gen/lss-menu)

BUILD = "data/builds/peaking-mf.json"
OLD, ROWS4, MENU = "custom-menu-rows-3", "custom-menu-rows-4", "spot-menu"

# custom-menu-rows-4
OLD_ITEMS, ITEMS_TABLE, KIDS = 0x7EBF1FE0, 0x7EBF1FD0, 0x7EE3CBF4
OLD_ROWS, ROWS = 83, 84
PAGE, CHECK, LABEL, HELP = 594, 1, 1494, 1509   # CHECK: the Metering setting, whose state greys the row
AT = 48                                          # index of BULB/TIME Timer in custom-menu-rows-3; the row goes there
ROW = struct.pack("<HHIHHHH", 4, LABEL, 2000, 12, HELP, 0, 1)   # as AF Mode's row; order 12: unused in group E
KID = struct.pack("<II", PAGE, CHECK)
OLD_DLOG_VT, DLOG_VT, DLOG_WORD = 0x7EE3CE94, KIDS + (ROWS + 1) * 8, 0x7F014F94
GROUP_E = 0x7E8EE850 + 2 * 4                     # .data image (RAM 0x602BE398): rows in group 4 (E)
CONSTS = {                                       # custom-menu-rows-3's value -> this spec's value
    "2da600": ("2da800", "clear the row-state array, 166 -> 168 bytes"),
    "a552": ("a553", "cmp last index 82 -> 83"),
    "aa53": ("aa54", "cmp row count 83 -> 84"),
    "8552": ("8553", "wrap to last index 82 -> 83"),
    "8052": ("8053", "wrap to last index 82 -> 83"),
    "a052": ("a053", "cmp last index 82 -> 83"),
}

# spot-menu
SETS = (593, 660, 621)                           # Spot, Spot HI, Spot SH: prm 0x94D1, 0x9F91, 0x9821
TEXTS = (171, 106, 107)                          # stock "Spot", "Spot Hilight", "Spot Shadow"
LISTS = (198, 584, 659)                          # generic list pages that no table names
SUBROWS = (0x7EFF03FC, 0x7EFF0410, 0x7EFF0438)   # page 594's sub-item rows (0x7EFF0424 is LV-Info's Level Gauge)
PAGE_KIDS = DLOG_VT + 72                         # page 594's child list, after Debug Log's value list (0x7EE3CEE4)
PAGE_REC = 0x7EFFD804                            # page record of 594: +20 = child list
DESCS = (0x7F00C2FC, 0x7F00BCEC, 0x7F00C7BC)     # list descriptors of 198, 584, 659
OFFON = 0x7F008CC0                               # list 200's items: Off (text 1371, value 0), On (text 198, value 1)
VALUE_RECS = ((0x7EFF4AE0, 446, 593), (0x7EFF4B00, 446, 593), (0x7EFF4B60, 448, 660), (0x7EFF4B80, 448, 660),
              (0x7EFF4BA0, 449, 621), (0x7EFF4BC0, 449, 621))   # {setting, value, 2, text}: value 0 Off, 1 On


def rows4(specs):
    before = specs[:specs.index("data/specs/%s.json" % OLD)]
    o = Ops(*image(before))
    old = json.load(open(os.path.join(ROOT, "data", "specs", OLD + ".json")))
    for x in old["ops"]:
        a, note = x.get("_addr"), x["_note"]
        if a == "0x%08X" % OLD_ITEMS:
            t = bytes.fromhex(x["new"])
            assert len(t) == OLD_ROWS * 16 + 2
            assert struct.unpack_from("<HHI", t, (AT - 1) * 16) == (4, 45, 103), "row 47 is not AEL Metering"
            assert struct.unpack_from("<HHI", t, AT * 16) == (4, 1464, 173), "row 48 is not BULB/TIME Timer"
            cut = AT * 16
            o.add(ITEMS_TABLE, t[:cut] + ROW + t[cut:], "Custom Menu item table, 84 rows + the end group 98: the 83 "
                  "rows of custom-menu-rows-3 and {group 4, text %d 'Spot Metering', setting 2000, order 12, help %d, "
                  "0, 1} at index %d, after AEL Metering" % (LABEL, HELP, AT))
        elif a == "0x%08X" % KIDS:
            k = bytes.fromhex(x["new"])
            assert len(k) == (OLD_ROWS + 1) * 8 and k[-8:] == bytes(8)
            assert struct.unpack_from("<II", k, AT * 8) == (145, 173), "child 48 is not BULB/TIME Timer's"
            cut = AT * 8
            o.add(KIDS, k[:cut] + KID + k[cut:], "Custom Menu child list, 85 entries + zero entry, in place (8 B "
                  "longer): custom-menu-rows-3's list and (page %d, setting %d Metering) at index %d" % (PAGE, CHECK, AT))
        elif note.startswith("item-table address"):
            assert x["new"].endswith(struct.pack("<I", OLD_ITEMS).hex())
            o.add(int(a, 16), bytes.fromhex(x["new"][:4]) + struct.pack("<I", ITEMS_TABLE),
                  "item-table address -> 0x%08X" % ITEMS_TABLE)
        elif a == "0x%08X" % OLD_DLOG_VT:
            o.add(DLOG_VT, bytes.fromhex(x["new"]), "value -> text list of the Debug Log row, moved 8 B to 0x%08X: "
                  "0 Off (text 1371), 1 On (text 198), end mark" % DLOG_VT)
        elif a == "0x%08X" % DLOG_WORD:
            o.add(DLOG_WORD, struct.pack("<I", DLOG_VT), "value -> text list 608: null -> 0x%08X" % DLOG_VT)
        elif a == "0x%08X" % GROUP_E:
            assert x["new"] == "0e00"
            o.add(GROUP_E, struct.pack("<H", 15), ".data image (RAM 0x602BE398): rows in group 4 (E), 14 -> 15 "
                  "(Spot Metering)")
        elif x["new"] in CONSTS:
            new, what = CONSTS[x["new"]]
            o.add(int(a, 16), bytes.fromhex(new), "%s: %s" % (note.split(":")[0], what))
        else:
            n = dict(x)
            blk = o.b0 if x["block"] == 0 else o.b1
            off = int(x["offset"], 16)
            assert blk[off:off + len(x["new"]) // 2].hex() == x["expect"], note
            n["_note"] = note + " (as custom-menu-rows-3)"
            o.ops.append(n)
    assert sum(1 for x in o.ops if x["_note"].startswith("item-table address")) == 10
    assert sum(1 for x in o.ops if x["_note"].startswith("page record")) == 11
    assert sum(1 for x in o.ops if x["new"] in [v[0] for v in CONSTS.values()]) == 9
    assert len(o.ops) == len(old["ops"])
    spec(ROWS4, "The Custom Menu with five added rows: Peaking in A after MF Assist, Load Looks and Debug Log in J, "
         "Lowest S/S Setting in E before ISO-Auto Set (all four as data/specs/custom-menu-rows-3.json, whose place this "
         "spec takes) and Spot Metering in E after AEL Metering (setting 2000: it opens page %d; child setting %d, "
         "Metering; the page is in data/specs/spot-menu.json, which a build with this spec needs). No stock row is "
         "changed. An 84-row copy of the item table at 0x%08X (10 address loads re-pointed), the 85-entry child list "
         "in place at 0x%08X (Debug Log's value -> text list moved to 0x%08X), 9 row constants (last index 83, count "
         "84, row-state array 168 B), the group sizes of A (11), E (15) and J (8). Every expect is a byte string of "
         "the specs before custom-menu-rows-3 in %s. See experiments/2026-11-24-af-spot-metering/NOTES.md, E3 and "
         "\"Build spot-af\"." % (PAGE, CHECK, ITEMS_TABLE, KIDS, DLOG_VT, BUILD), o.ops,
         _ram="the row-state array of the Custom Menu page grows by 10 bytes (158 -> 168) into 0x606A31B6-BF (the "
              "next addressed object is 0x606A32F0)")


def menu(specs):
    o = Ops(*image(specs))
    for a, s, t in zip(SUBROWS, SETS, TEXTS):
        old = struct.unpack("<HHIIHHHH", o.get(a, 20))
        assert old[0] == PAGE and old[3:6] == (2, 7, 1), old
        o.add(a, struct.pack("<HHIIHHHH", PAGE, LABEL, s, 2, 7, 1, t, 0), "sub-item row of page %d: title %d, "
              "setting %d, text %d -> title %d 'Spot Metering', setting %d, text %d" % (PAGE, old[1], old[2], old[6],
                                                                                    LABEL, s, t))
    assert struct.unpack("<Ii", o.get(PAGE_REC, 8)) == (PAGE, -15)
    o.add(PAGE_KIDS, b"".join(struct.pack("<II", l, s) for l, s in zip(LISTS, SETS)) + bytes(8),
          "child list of page %d: (list, setting) %s and a zero entry (segment 3, reclaim-space row 6, after Debug "
          "Log's value -> text list)"
          % (PAGE, ", ".join("(%d, %d)" % x for x in zip(LISTS, SETS))))
    o.add(PAGE_REC + 20, struct.pack("<I", PAGE_KIDS), "page record of %d: child list 0x%08X -> 0x%08X"
          % (PAGE, struct.unpack("<I", o.get(PAGE_REC + 20, 4))[0], PAGE_KIDS))
    for d, lid, s in zip(DESCS, LISTS, SETS):
        old = struct.unpack("<HHIII", o.get(d, 16))
        new = struct.pack("<HHIII", s, 2, 0, 1, OFFON)
        if old[1:] == (2, 0, 1, OFFON):
            new = new[:2]
        o.add(d, new, "list descriptor of %d (no table names the list): setting %d, %d items at 0x%08X -> setting %d, "
              "the Off/On items 0x%08X of list 200" % (lid, old[0], old[1], old[4], s, OFFON))
    for a, s_old, s in VALUE_RECS:
        assert struct.unpack("<I", o.get(a, 4))[0] == s_old
        o.add(a, struct.pack("<I", s), "On/Off value record {setting, value, 2, text}: setting %d -> %d" % (s_old, s))
    spec(MENU, "Spot metering at the AF target, the menu part: page %d 'Spot Metering', opened by the Custom Menu E "
         "row that data/specs/custom-menu-rows-4.json adds, with three On/Off rows: Spot (setting 593, prm 0x94D1), "
         "Spot Hilight (660, 0x9F91), Spot Shadow (621, 0x9821); MODE bank, u8, ROM and full-reset default 0 (Off); "
         "no stock code reads or writes them, and no mode-controller table but the full reset names them (bank lists, "
         "mode presets and restore lists do not: experiments/2026-11-18-look-editor/out/scan.tsv). "
         "data/specs/spot-core.json reads them. The rows use the stock texts 171, 106, 107 and the generic list "
         "pages 198, 584, 659 with the Off/On items of list 200; the On/Off value records of the settings 446, 448, "
         "449 name the three settings. The title (and the row's label) is text %d, the row's help %d: unused built-in "
         "EVF texts that data/specs/card-looks-9.json points at the English texts in every menu language. No code. "
         "See experiments/2026-11-24-af-spot-metering/NOTES.md, E3, E4 and \"Build spot-af\"." % (PAGE, LABEL, HELP),
         o.ops,
         _interface="settings 593 / 660 / 621 = prm 0x94D1 / 0x9F91 / 0x9821 (MODE bank, u8): 0 Off, 1 On")


def main():
    specs = json.load(open(os.path.join(ROOT, BUILD)))["specs"]
    rows4(specs)
    specs = [s.replace(OLD, ROWS4).replace("card-looks-8", "card-looks-9") for s in specs] + ["data/specs/spot-core.json"]
    menu(specs)


if __name__ == "__main__":
    main()

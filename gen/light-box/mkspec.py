"""Write the two menu rows of Light Box: two specs, no code.

    uv run python gen/light-box/mkspec.py

data/specs/custom-menu-rows-5.json takes the place of custom-menu-rows-4 in data/builds/light-box.json. It is
custom-menu-rows-4 (gen/spot-menu) with one row more: "▶ Close Up Mode" in group D after LV Close Up Mode, the E-PL5's
record {3, text 208, setting 321, order 0, help 1126, value list 130, 0} and child entry (130, 321) at the same place.
  item table: 85 rows + the end group (1,362 B) at 0x7EBF1FC0 (16 B earlier than custom-menu-rows-4's, so it still ends
    at 0x7EBF2512, where stock-films-structure's BK0 starts; its first 10 B are osd-battery's, released 2026-11-26);
    the 10 address loads point at it;
  child list: 86 entries in place at 0x7EE3CBF4 (8 B longer, to 0x7EE3CEAC); Debug Log's value -> text list moves to
    0x7EE3CF04, after spot-menu's page list 0x7EE3CEE4 (its place 0x7EE3CE9C would overlap the longer child list);
  row constants: last index 84, count 85, row-state array 170 B; rows in group D 17 -> 18.
Every expect is a byte string of the specs before custom-menu-rows-4 in data/builds/light-box.json.

data/specs/light-box-row.json goes last: the row "Light Box" in Custom Menu D > ▶/Info Settings > ▶ Info (panel 191),
as on the E-PL5. The sub-item table is walked from top to bottom and a panel's rows are its records in that order. The
record 119 of the unreachable panel 651 ("Mode Dial Function", Myset4) takes panel 191's first row, and the records
139-142 take panel 191's other three rows and {191, title 150, setting 257, 2, 7, 1, text 868}, so Light Box is the
fifth row. The row's picker is list 655 (panel 651's Myset4 list), its descriptor re-keyed to setting 257 with the
stock Off/On items of 257: the stock picker 198 is Spot's since spot-menu. Panel 191's child list gets the fifth entry
(655, 257) in place: its end entry moves 8 B into panel 192's old list, which nothing points at since
level-gauge-lvinfo-row. experiments/2026-11-19-light-box/NOTES.md.
"""

import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "gen", "lss-menu"))
from mkspec import Ops, image, spec  # noqa: E402  (gen/lss-menu: the same helpers as custom-menu-rows-4)

BUILD = "data/builds/light-box.json"
OLD, ROWS5, ROW_SPEC = "custom-menu-rows-4", "custom-menu-rows-5", "light-box-row"

# custom-menu-rows-5
OLD_ITEMS, ITEMS_TABLE, KIDS = 0x7EBF1FD0, 0x7EBF1FC0, 0x7EE3CBF4
OLD_ROWS, ROWS = 84, 85
AT = 34                                          # index of Backlit LCD in custom-menu-rows-4; the new row goes there
SETTING, PANEL, LABEL, HELP = 321, 130, 208, 1126
ROW = struct.pack("<HHIHHHH", 3, LABEL, SETTING, 0, HELP, PANEL, 0)   # the E-PL5 1.6 record (0x7EFF8B5C)
KID = struct.pack("<II", PANEL, SETTING)
OLD_DLOG_VT, DLOG_VT, DLOG_WORD = 0x7EE3CE9C, 0x7EE3CF04, 0x7F014F94
SPOT_KIDS = 0x7EE3CEE4                           # spot-menu's child list of page 594, 32 B
GROUP_D = 0x7E8EE850 + 2 * 3                     # .data image (RAM 0x602BE396): rows in group 3 (D)
CONSTS = {                                       # custom-menu-rows-4's value -> this spec's value
    "2da800": ("2daa00", "clear the row-state array, 168 -> 170 bytes"),
    "a553": ("a554", "cmp last index 83 -> 84"),
    "aa54": ("aa55", "cmp row count 84 -> 85"),
    "8553": ("8554", "wrap to last index 83 -> 84"),
    "8053": ("8054", "wrap to last index 83 -> 84"),
    "a053": ("a054", "cmp last index 83 -> 84"),
}

# light-box-row
SUBROWS = 0x7EFEF4FC                             # sub-item table: 196 records of 20 B, walked top to bottom
R651, R191 = SUBROWS + 119 * 20, SUBROWS + 139 * 20   # 0x7EFEFE48 (panel 651, Myset4), 0x7EFEFFD8 (panel 191's 4)
LIST191 = 0x7EFF91FC                             # child list of panel 191: 4 entries, then the end entry
PICKER = 655                                     # generic list page of panel 651's Myset4 row; Light Box's stock
DESC655, DESC_OF = 0x7F00C78C, 0x7F00DDD8        # picker 198 is Spot's since spot-menu. {list, descriptor} entry
ITEMS257 = 0x7F008C88                            # the stock Off/On items of setting 257 (list 198's before spot-menu)


def subrow(panel, title, setting, text):
    return struct.pack("<HHIIHHHH", panel, title, setting, 2, 7, 1, text, 0)


def kids(pairs):
    return b"".join(struct.pack("<II", p, s) for p, s in pairs)


def rows5(specs):
    before = specs[:specs.index("data/specs/%s.json" % OLD)]
    o = Ops(*image(before))
    old = json.load(open(os.path.join(ROOT, "data", "specs", OLD + ".json")))
    for x in old["ops"]:
        a, note = x.get("_addr"), x["_note"]
        if a == "0x%08X" % OLD_ITEMS:
            t = bytes.fromhex(x["new"])
            assert len(t) == OLD_ROWS * 16 + 2
            assert struct.unpack_from("<HHI", t, (AT - 1) * 16) == (3, 1476, 344), "row 33 is not LV Close Up Mode"
            assert struct.unpack_from("<HHI", t, AT * 16) == (3, 72, 161), "row 34 is not Backlit LCD"
            cut = AT * 16
            new = t[:cut] + ROW + t[cut:]
            assert ITEMS_TABLE + len(new) == OLD_ITEMS + len(t)
            o.add(ITEMS_TABLE, new, "Custom Menu item table, 85 rows + the end group 98: the 84 rows of "
                  "custom-menu-rows-4 and {group 3, text %d 'Close Up Mode', setting %d, order 0, help %d, value list "
                  "%d, 0} at index %d, after LV Close Up Mode (the E-PL5 record)" % (LABEL, SETTING, HELP, PANEL, AT))
        elif a == "0x%08X" % KIDS:
            k = bytes.fromhex(x["new"])
            assert len(k) == (OLD_ROWS + 1) * 8 and k[-8:] == bytes(8)
            assert struct.unpack_from("<II", k, AT * 8) == (133, 161), "child 34 is not Backlit LCD's"
            cut = AT * 8
            new = k[:cut] + KID + k[cut:]
            assert KIDS + len(new) <= SPOT_KIDS
            o.add(KIDS, new, "Custom Menu child list, 86 entries + zero entry, in place (8 B longer): "
                  "custom-menu-rows-4's list and (panel %d, setting %d) at index %d" % (PANEL, SETTING, AT))
        elif note.startswith("item-table address"):
            assert x["new"].endswith(struct.pack("<I", OLD_ITEMS).hex())
            o.add(int(a, 16), bytes.fromhex(x["new"][:4]) + struct.pack("<I", ITEMS_TABLE),
                  "item-table address -> 0x%08X" % ITEMS_TABLE)
        elif a == "0x%08X" % OLD_DLOG_VT:
            assert len(x["new"]) // 2 == 72
            o.add(DLOG_VT, bytes.fromhex(x["new"]), "value -> text list of the Debug Log row, moved to 0x%08X, after "
                  "spot-menu's page list: 0 Off (text 1371), 1 On (text 198), end mark (as custom-menu-rows-4)" % DLOG_VT)
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
            n["_note"] = note.replace(" (as custom-menu-rows-3)", "") + " (as custom-menu-rows-4)"
            o.ops.append(n)
    assert struct.unpack("<H", o.get(GROUP_D, 2))[0] == 17
    o.add(GROUP_D, struct.pack("<H", 18), ".data image (RAM 0x602BE396): rows in group 3 (D), 17 -> 18 (Close Up "
          "Mode)")
    assert sum(1 for x in o.ops if x["_note"].startswith("item-table address")) == 10
    assert sum(1 for x in o.ops if x["_note"].startswith("page record")) == 11
    assert sum(1 for x in o.ops if x["new"] in [v[0] for v in CONSTS.values()]) == 9
    assert len(o.ops) == len(old["ops"]) + 1
    spec(ROWS5, "The Custom Menu with six added rows: Peaking in A after MF Assist, Load Looks and Debug Log in J, "
         "Lowest S/S Setting in E before ISO-Auto Set, Spot Metering in E after AEL Metering (all five as "
         "data/specs/custom-menu-rows-4.json, whose place this spec takes; Spot Metering needs data/specs/spot-menu.json) "
         "and the E-PL5's row '▶ Close Up Mode' in D after LV Close Up Mode (setting %d, prm tag 0x91A1, mode1 / mode2; "
         "value list %d and its value -> text list are stock). No stock row is changed. An 85-row copy of the item "
         "table at 0x%08X (10 address loads re-pointed), the 86-entry child list in place at 0x%08X (Debug Log's value "
         "-> text list moved to 0x%08X), 9 row constants (last index 84, count 85, row-state array 170 B), the group "
         "sizes of A (11), D (18), E (15) and J (8). Every expect is a byte string of the specs before "
         "custom-menu-rows-4 in %s. See experiments/2026-11-19-light-box/NOTES.md, \"Rebuild on main\"."
         % (SETTING, PANEL, ITEMS_TABLE, KIDS, DLOG_VT, BUILD), o.ops,
         _ram="the row-state array of the Custom Menu page grows by 2 bytes (168 -> 170) into 0x606A31C0-C1 (the "
              "next addressed object is 0x606A32F0)")


def light_box_row(specs):
    o = Ops(*image(specs))
    i191 = [(191, 150, 253, 845), (191, 150, 254, 926), (191, 150, 255, 844), (191, 150, 256, 842)]
    assert o.get(R651, 20) == subrow(651, 1353, 493, 607)
    assert o.get(R191, 80) == b"".join(subrow(*r) for r in i191)
    assert o.get(R191 + 80, 2) == struct.pack("<H", 192)
    o.add(R651, subrow(*i191[0]), "sub-item record 119: panel 651 'Mode Dial Function' / setting 493 / text 607 "
          "'Myset4' (no menu reaches panel 651 on the E-PM2) -> panel 191's first row, '▶ Info' / setting 253 / text "
          "845 'Image Only'")
    o.add(R191, b"".join(subrow(*r) for r in i191[1:]) + subrow(191, 150, 257, 868), "sub-item records 139-142: "
          "panel 191's rows 2-4 (settings 254, 255, 256), each one record earlier, and the fifth row: panel 191 '▶ "
          "Info' (title 150) / setting 257 / text 868 'Light Box', equal to the E-PL5 row at 0x7EFF08D0. Panel 191's "
          "rows keep their order")
    assert o.get(LIST191, 40) == kids([(194, 253), (195, 254), (196, 255), (197, 256), (0, 0)])
    assert o.get(LIST191 + 40, 8) == kids([(200, 244)])        # panel 192's old list, unreferenced (V, word scan)
    assert struct.unpack("<II", o.get(DESC_OF, 8)) == (PICKER, DESC655)
    assert struct.unpack("<HHIII", o.get(DESC655, 16)) == (493, 9, 0, 1, 0x7F00BAE8)
    assert struct.unpack("<HHIII", o.get(0x7F00C2FC, 16))[0] == 593, "list 198 is not Spot's picker"
    o.add(DESC655, struct.pack("<HHIII", 257, 2, 0, 1, ITEMS257), "list descriptor of %d (the picker of panel 651's "
          "Myset4 row; no menu reaches panel 651): setting 493, 9 items at 0x7F00BAE8 -> setting 257, the stock Off/On "
          "items 0x%08X of setting 257 (the descriptor of list 198 before spot-menu)" % (PICKER, ITEMS257))
    o.add(LIST191 + 32, kids([(PICKER, 257), (0, 0)]), "child list of panel 191, in place: the fifth entry (list %d, "
          "setting 257) in place of the end entry, and the end entry in place of the first entry of panel 192's old "
          "list 0x7EFF9224 (no pointer to it since level-gauge-lvinfo-row). The E-PL5's list 0x7EFF9AE0 has list 198, "
          "which is Spot's picker here" % PICKER)
    spec(ROW_SPEC, "Light Box (E-PL6 manual p.86): the row 'Light Box' in Custom Menu D > ▶/Info Settings > ▶ Info "
         "(panel 191, setting 257 = prm tag 0x9171, Off / On), as on the E-PL5. Data only, 4 edits in "
         "place, no free space: the sub-item record 119 of panel 651 ('Mode Dial Function', which no menu reaches on "
         "the E-PM2) and the records 139-142 hold panel 191's four rows in their order and then "
         "{191, title 150, setting 257, 2, 7, 1, text 868}; panel 191's child list gets the fifth entry (655, 257), "
         "its end entry moving into panel 192's old list, which nothing points at since "
         "data/specs/level-gauge-lvinfo-row.json. The row's picker is list 655 (panel 651's Myset4 list), its "
         "descriptor re-keyed to setting 257 with the stock Off/On items of 257: the stock picker 198 is the Spot row's "
         "since data/specs/spot-menu.json. The Light Box display needs Close Up Mode mode2 as well "
         "(data/specs/custom-menu-rows-5.json). See experiments/2026-11-19-light-box/NOTES.md, \"Rebuild on main\".",
         o.ops)


def main():
    specs = json.load(open(os.path.join(ROOT, BUILD)))["specs"]
    assert specs[-1] == "data/specs/%s.json" % ROW_SPEC
    rows5([s.replace(ROWS5, OLD) for s in specs])
    light_box_row(specs[:-1])


if __name__ == "__main__":
    main()

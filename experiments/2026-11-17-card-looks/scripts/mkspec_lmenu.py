"""Write data/specs/looks-menu.json: the menu row "Load Looks" (Off / Load) in Custom Menu J.

    uv run python experiments/2026-11-17-card-looks/scripts/mkspec_lmenu.py [--v3]

--v3 writes data/specs/looks-menu-2.json: the list gets a third item, Built-in (value 2), and the row shows a status text
when it is Off: text 1495, which the loader of data/specs/card-looks-3.json points at "Off", "Loaded", "No file",
"Bad file" or "Built-in" (English texts here; the loader writes them for every language at run time).

The row takes the place of "Touch Screen Settings" (setting 427), the fifth row of J: the E-PM2 has no touch screen
(the row comes with the firmware it shares with the E-PL5). No row is added, so no table moves and no row constant
changes. (An added row needs the item table and the child list of data/specs/peaking-menu.json to grow or move; every
place for them has bytes that an earlier spec covers and keeps, which src/epm2mod/spec.py refuses to change.)
  (a) the row in the item table of peaking-menu (0x7EBF2000, index 78): {group 9, text 1498, setting 449, order 4,
      help 1497, value list 610, 0};
  (b) its child entry (0x7EBF2600, index 78): (panel 610, setting 449);
  (c) panel 610 (the stock Off / On list of the dormant setting 449, in no menu): Off gets the value 1, which the
      firmware writes into the setting at every start, and the second item shows text 1496 "Load" with the value 0;
      the value -> text list 610 for the row (null in stock) at NAMES: 1 Off, 0 Load;
  (d) English texts (block 1): 1498 "Built-in EVF Style" -> "Load Looks", 1497 (the help of the built-in EVF grid)
      -> the row's help, 1496 "@A07A@ Displayed Grid" -> "Load". Texts of built-in EVF panels: the body has none.
The loader (data/specs/card-looks-2.json) reads setting 449 (prm tag 0xD7B1, MODE bank, one byte; no stock code reads
it, experiments/2026-11-17-osd-info/NOTES.md section 7) when the GUI leaves the menu; at 0 (Load) it sets it back to 1
with the GUI's setSetting 0x7EE01D4E, as the menu does, and starts the load.
Every expect is a byte string of the specs before it (mkspec_slots.LAYOUT).
"""
import hashlib, json, os, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from epm2mod.container import parse  # noqa: E402
import mkspec_slots  # noqa: E402

V4 = "--v4" in sys.argv      # the row itself is in data/specs/custom-menu-rows.json: no row edit here
V3 = "--v3" in sys.argv or V4
SPEC = "looks-menu-3" if V4 else "looks-menu-2" if V3 else "looks-menu"
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
ITEMS, KIDS, AT = 0x7EBF2000, 0x7EBF2600, 78               # the tables of peaking-menu; the row Touch Screen Settings
NAMES = 0x7EE46D28          # value -> text list of the row: 3 x 24 B (segment 3, data area 0x7EE46D27-0x7EE4709D)
FORMATS = 0x7F014614        # table of the value -> text lists, by "value list" number
SETTING, TAG, PANEL = 449, 0xD7B1, 610
V_OFF, V_LOAD = 1, 0        # the firmware writes 1 into setting 449 at every start (emulator: prm set at 11 and 227 ms)
DESC = 0x7F00BFEC           # list descriptor of panel 610: (449, 2 items, 0, 1, items)
T_LABEL, T_HELP, T_LOAD, T_OFF, T_ON = 1498, 1497, 1496, 1371, 198
T_BUILTIN, T_STATUS = 1503, 1495       # v3: the third item; the row's text for value 1
V_BUILTIN = 2
ITEMS3 = NAMES + 4 * 24     # v3: the three items of panel 610 (84 B)
ROW = struct.pack("<HHIHHHH", 9, T_LABEL, SETTING, 4, T_HELP, PANEL, 0)
KID = struct.pack("<II", PANEL, SETTING)
# English texts: (text id, block-1 offset, old string, new string); the new one is not longer
TEXTS = (
    (T_LABEL, 0x3885AE, "Built-in EVF Style", "Load Looks"),
    (T_HELP, 0x388528, "Select a framing grid\r\nfor the built-in EVF.\r\nEnable while @A07A@.",
     "Load film looks from\r\nEPM2LOOK.BIN on the card."),
    (T_LOAD, 0x3884FC, "@A07A@ Displayed Grid", "Load"),
)
TEXTS_V3 = (
    (T_BUILTIN, 0x38865A, "@A07A@ Info Settings", "Built-in"),
    (T_STATUS, 0x38848A, "Menu about the built-in\r\nelectronic viewfinder settings.", "Off"),
)


OLD_DESCRIPTION = "The menu row 'Load Looks' (Off / Load) in Custom Menu J, in the place of Touch Screen Settings (the E-PM2 has no touch screen). Its value is the dormant setting 449 (prm tag 0xD7B1, MODE bank, one byte, default 0, read by no stock code); its list is the stock Off / On panel 610 with 'On' shown as 'Load'. The loader of data/specs/card-looks-2.json reads the setting when the GUI leaves the menu and sets it back to Off (1; Load is 0, so that the value 1 that the firmware gives the setting at every start reads Off). An edit of one row and one child entry of the tables of data/specs/peaking-menu.json, the list of panel 610, and three English texts of built-in EVF panels (block 1). Other languages keep the old texts of these ids. See experiments/2026-11-17-card-looks/design.md section 9.5."


def main():
    work = os.path.join(ROOT, "build", "card-looks")
    os.makedirs(work, exist_ok=True)
    before = mkspec_slots.LAYOUT4 if V4 else mkspec_slots.LAYOUT
    out = os.path.join(work, "before-menu.BIN")
    subprocess.run(["uv", "run", "epm2mod", "apply", *before, "--from", "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "-o", out], cwd=ROOT, check=True, capture_output=True)
    c = parse(open(out, "rb").read())
    blk, b1 = c.blocks[0].payload, c.blocks[1].payload
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    ops = []

    def op(addr, new, note, block=0):
        src, off = (blk, addr - BASE) if block == 0 else (b1, addr)
        expect = src[off:off + len(new)]
        assert expect != new, note
        o = {"type": "bytes", "block": block, "offset": "0x%X" % off, "expect": expect.hex(), "new": new.hex()}
        if block == 0:
            o["_addr"] = "0x%08X" % addr
        o["_note"] = note
        ops.append(o)

    # (a) the row, (b) its child entry (v4: an added row, data/specs/custom-menu-rows.json)
    assert V4 or struct.unpack("<HHIHHHH", get(ITEMS + 16 * AT, 16)) == (9, 544, 427, 4, 1132, 0, 1)   # Touch Screen Settings
    assert V4 or struct.unpack("<II", get(KIDS + 8 * AT, 8)) == (174, 427)
    if not V4:
        op(ITEMS + 16 * AT, ROW, "Custom Menu item table of peaking-menu, row 78 (J, Touch Screen Settings: text 544, "
       "setting 427, help 1132, value list 0) -> {group 9, text 1498 'Load Looks', setting 449, order 4, help 1497, "
       "value list 610, 0}")
    if not V4:
        op(KIDS + 8 * AT, KID, "Custom Menu child list of peaking-menu, entry 78: (panel 174, setting 427) -> (panel 610, "
       "setting 449)")
    # (c) panel 610: its second item shows "Load"; the row's value -> text list
    d = struct.unpack("<HHIII", get(DESC, 16))
    assert d[:4] == (SETTING, 2, 0, 1), d
    assert blk.count(struct.pack("<I", d[4])) == 1, "the items of panel 610 have another reader"
    it = get(d[4], 56)
    assert struct.unpack("<BBH6I", it[:28]) == (0, 2, T_OFF, 0, 0, 2000, 0, 192, 197)
    assert struct.unpack("<BBH4I", it[28:48]) == (0, 2, T_ON, 0, 0, 2000, 1)
    name = lambda value, text: struct.pack("<iIH14x", value, 2, text)   # {value, kind 2 = one label, text}, 24 B
    assert get(FORMATS + 4 * PANEL, 4) == bytes(4)
    if V3:
        item = lambda text, value: struct.pack("<BBH4I", 0, 2, text, 0, 0, 2000, value) + it[20:28]
        op(ITEMS3, item(T_OFF, V_OFF) + item(T_LOAD, V_LOAD) + item(T_BUILTIN, V_BUILTIN),
           "the three items of panel 610: Off (value 1, the value the firmware gives setting 449 at every start), "
           "Load (0), Built-in (2); 28 B each, the layout of the stock Off/On items")
        op(DESC + 2, struct.pack("<H", 3), "list descriptor of panel 610: 2 items -> 3")
        op(DESC + 12, struct.pack("<I", ITEMS3), "list descriptor of panel 610: items 0x%08X -> 0x%08X" % (d[4], ITEMS3))
        op(NAMES, name(V_OFF, T_STATUS) + name(V_LOAD, T_LOAD) + name(V_BUILTIN, T_BUILTIN) +
           struct.pack("<i20x", -15), "value -> text list of the row: 1 the status text 1495, 0 Load, 2 Built-in, "
           "end mark -15 (the layout of the stock Off/On list 0x7F012724)")
    else:
        op(d[4] + 16, struct.pack("<I", V_OFF), "panel 610, item 1 (Off): value 0 -> 1, the value the firmware gives "
           "setting 449 at every start (so a camera shows Off)")
        op(d[4] + 28 + 2, struct.pack("<HIII", T_LOAD, 0, 0, 2000) + struct.pack("<I", V_LOAD),
           "panel 610, item 2: text 198 'On' -> 1496 'Load', value 1 -> 0")
        op(NAMES, name(V_OFF, T_OFF) + name(V_LOAD, T_LOAD) + struct.pack("<i20x", -15),
           "value -> text list of the row: 1 Off, 0 Load, end mark -15 (the layout of the stock Off/On list 0x7F012724)")
    op(FORMATS + 4 * PANEL, struct.pack("<I", NAMES), "value -> text list 610: null -> 0x%08X" % NAMES)
    # (d) texts
    for tid, off1, was, new in TEXTS + (TEXTS_V3 if V3 else ()):
        w, n = was.encode("utf-16-le"), new.encode("utf-16-le")
        assert b1[off1:off1 + len(w) + 2] == w + b"\0\0" and b1[off1 - 2:off1] == b"\0\0", tid
        assert len(n) <= len(w)
        op(off1, n + bytes(len(w) - len(n)), "English text %d: %r -> %r" % (tid, was, new), block=1)
    spec = {
        "name": SPEC,
        "description": (
            "The menu row 'Load Looks' in Custom Menu J, in the place of Touch Screen Settings (the E-PM2 has no "
            "touch screen). Its value is the dormant setting 449 (prm tag 0xD7B1, MODE bank, one byte, read by no "
            "stock code; the firmware writes 1 into it at every start); its list is the stock Off / On panel 610. "
            "Three items: Off (1), Load (0), Built-in (2). When it is Off the row shows text 1495, which the loader "
            "of data/specs/card-looks-3.json points at the result of the last action (Off, Loaded, No file, Bad file, "
            "Built-in). The loader starts at Load or Built-in and sets the row back to Off. An edit of one row and "
            "one child entry of the tables of data/specs/peaking-menu.json, the list of panel 610, and English texts of "
            "built-in EVF panels (block 1). See experiments/2026-11-17-card-looks/design.md section 10."
            if V3 and not V4 else
            "The list, texts and status of the menu row 'Load Looks', which data/specs/custom-menu-rows.json adds at the "
            "end of Custom Menu J. Its value is the dormant setting 449 (prm tag 0xD7B1, MODE bank, one byte, read by "
            "no stock code; the firmware writes 1 into it at every start); its list is the stock Off / On panel 610, "
            "with three items: Off (1), Load (0), Built-in (2). When it is Off the row shows text 1495, which the "
            "loader of data/specs/card-looks-4.json points at the result of the last action (Off, Loaded, No file, Bad "
            "file, Built-in). English texts of built-in EVF panels (block 1); the loader writes the row's texts into "
            "every language at run time. See experiments/2026-11-17-card-looks/design.md section 10.2."
            if V4 else OLD_DESCRIPTION),
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "ops": ops,
    }
    with open(os.path.join(ROOT, "data", "specs", SPEC + ".json"), "w") as fh:
        json.dump(spec, fh, indent=1)
        fh.write("\n")
    print("wrote data/specs/%s.json: %d ops" % (SPEC, len(ops)))


if __name__ == "__main__":
    main()

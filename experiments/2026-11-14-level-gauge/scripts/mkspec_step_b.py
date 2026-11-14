"""Write the patch spec for step B: the "Level Adjust" row in the Custom Menu's last group (Utility).

Research code. It reads the stock E-PM2 block 0 and writes patches/level-adjust-row.json.

The Custom Menu is one list of rows in two parallel tables (NOTES.md section 12):
  item table  0x7EFF7E80, 78 records of 16 bytes
              {u16 group, u16 label text, u32 setting, u16 order, u16 help text, u16 value format, u16 flag},
              ended by a group number 98;
  child list  0x7EFF8E4C, 78 entries {u32 panel, u32 setting}, ended by a zero entry. Entry i belongs to
              item i. The 11 page records 24..34 point to it.
Neither table has a free slot. The E-PL6 has the row {9, 160, 2213, 3, 478, 0, 1} and the child (173, 2213)
between "Warning Level" and "Touch Screen Settings". This spec makes the same insert:
  (a) a 79-row copy of the item table at ITEMS, and the 10 address loads in the page code point to it;
  (b) a 79-entry copy of the child list at KIDS, and the 11 page records point to it;
  (c) the row constants of the page code: last index 77 -> 78 (5 sites), count 78 -> 79 (3 sites), size of
      the row-state array 156 -> 158 bytes (1 site);
  (d) the size of group 9 in the .data image: 5 -> 6.
The old tables stay where they are, without a reader. Data and immediates only; no new code.

Usage: mkspec_step_b.py OUT.json [E-PL6 block 0]
With the E-PL6 block every new record and constant is also asserted equal to the E-PL6's.
"""
import json, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
STOCK_SHA = json.load(open(os.path.join(ROOT, "patches/interval-frames-240.json")))["base_sha256"]
BLOCK0 = os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin")

OLD_ITEMS, N = 0x7EFF7E80, 78   # item table and its row count
OLD_KIDS = 0x7EFF8E4C           # child list
ITEMS = 0x7EBF3000              # new item table: 79 x 16 + 2 bytes
KIDS = 0x7EBF3500               # new child list: 79 x 8 + 8 bytes
AT = 76                         # the new row's index (after "Warning Level", before "Touch Screen Settings")
ROW = struct.pack("<HHIHHHH", 9, 160, 2213, 3, 478, 0, 1)
KID = struct.pack("<II", 173, 2213)
PAGES = 0x7EFFA44C              # page records, 40 bytes each, child-list pointer at +20
SIZE_J = 0x7E8DA000 + (0x602BE390 + 2 * 9 - 0x602A9B40)  # .data image: size of group 9 (RAM 0x602BE3A2)

# the 10 loads of the item-table address (address of the imm32), each with its two opcode bytes before it
ITEM_LOADS = (0x7EDE9B9D, 0x7EDE9CDD, 0x7EDE9D85, 0x7EDE9F19, 0x7EDEA02A, 0x7EDEA035, 0x7EDEA2F2, 0x7EDEA392,
              0x7EDEA3A1, 0x7EDEA3F5)
# (address, stock instruction, new instruction, meaning); E-PL6 address = E-PM2 + 0xE9A, values 81 / 82 / 164
CONSTS = (
    (0x7EDE9AE5, "2d9c00", "2d9e00", "constructor: clear the row-state array, 156 -> 158 bytes"),
    (0x7EDE9B85, "a54d", "a54e", "open: cmp last index 77 -> 78"),
    (0x7EDE9B92, "aa4e", "aa4f", "open: cmp row count 78 -> 79"),
    (0x7EDE9CBA, "854d", "854e", "UP: wrap to last index 77 -> 78"),
    (0x7EDE9D10, "804d", "804e", "UP, skip a greyed row: wrap to last index 77 -> 78"),
    (0x7EDE9D26, "aa4e", "aa4f", "UP: cmp row count 78 -> 79"),
    (0x7EDE9D6B, "a04d", "a04e", "DOWN: cmp last index 77 -> 78"),
    (0x7EDE9DBF, "a54d", "a54e", "DOWN, skip a greyed row: cmp last index 77 -> 78"),
    (0x7EDE9DCC, "aa4e", "aa4f", "DOWN: cmp row count 78 -> 79"),
)
PL6_SHIFT = 0xE9A


def main():
    blk = open(BLOCK0, "rb").read()
    pl6 = open(sys.argv[2], "rb").read() if len(sys.argv) > 2 else None
    get = lambda a, n: blk[a - BASE:a - BASE + n]
    ops = []

    def op(addr, new, note):
        expect = get(addr, len(new))
        assert expect != new
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE), "expect": expect.hex(),
                    "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    # (a) item table
    old = get(OLD_ITEMS, N * 16 + 2)
    assert struct.unpack_from("<H", old, N * 16)[0] == 98 and struct.unpack_from("<H", old, AT * 16)[0] == 9
    assert struct.unpack_from("<HH", old, (AT - 1) * 16) == (9, 73) and struct.unpack_from("<HH", old, AT * 16) == (9, 544)
    items = old[:AT * 16] + ROW + old[AT * 16:]
    assert len(items) == 79 * 16 + 2
    # (b) child list
    oldk = get(OLD_KIDS, N * 8 + 8)
    assert oldk[-8:] == bytes(8) and struct.unpack_from("<II", oldk, (AT - 1) * 8) == (172, 278)
    for i in range(N):  # entry i is the child of item i wherever the item has its own setting
        s = struct.unpack_from("<I", old, i * 16 + 4)[0]
        assert s == 2000 or i in (2, 66) or s == struct.unpack_from("<I", oldk, i * 8 + 4)[0], i
    kids = oldk[:AT * 8] + KID + oldk[AT * 8:]
    assert len(kids) == 79 * 8 + 8
    if pl6:  # the E-PL6's last six rows and children are the same bytes
        assert pl6[0x7EFF9A1C - BASE - 48:0x7EFF9A1C - BASE + 50] == items[(AT - 3) * 16:], "E-PL6 item rows"
        k = struct.unpack_from("<I", pl6, 0x7EFFBB74 + 40 * 34 + 20 - BASE)[0] + (82 - 6) * 8 - BASE  # 82 entries there
        assert pl6[k:k + 56] == kids[(AT - 3) * 8:], "E-PL6 children"
    op(ITEMS, items, "new Custom Menu item table, 79 rows + the end group 98: the stock table 0x7EFF7E80 with the row "
       "{group 9, text 160 'Level Adjust', setting 2213, order 3, help 478, 0, 1} inserted at index 76 "
       "(= the E-PL6 row at 0x7EFF9A1C)")
    op(KIDS, kids, "new Custom Menu child list, 79 entries + zero entry: the stock list 0x7EFF8E4C with "
       "(panel 173, setting 2213) inserted at index 76 (= E-PL6)")
    for a in ITEM_LOADS:
        assert get(a, 4) == struct.pack("<I", OLD_ITEMS)
        op(a - 2, get(a - 2, 2) + struct.pack("<I", ITEMS), "item-table address 0x7EFF7E80 -> 0x%08X" % ITEMS)
    for page in range(24, 35):
        a = PAGES + 40 * page + 20
        assert get(a, 4) == struct.pack("<I", OLD_KIDS)
        op(a, struct.pack("<I", KIDS), "page record %d: child list 0x7EFF8E4C -> 0x%08X" % (page, KIDS))
    assert blk.count(struct.pack("<I", OLD_KIDS)) == 11 and blk.count(struct.pack("<I", OLD_ITEMS)) == len(ITEM_LOADS)
    # (c) row constants
    for a, was, new, note in CONSTS:
        assert get(a, len(was) // 2) == bytes.fromhex(was), "%08X" % a
        if pl6:
            p = pl6[a + PL6_SHIFT - BASE:a + PL6_SHIFT - BASE + len(was) // 2]
            assert p[0] == bytes.fromhex(was)[0] and p[1] == bytes.fromhex(was)[1] + (8 if len(was) == 6 else 4), "%08X" % a
        op(a, bytes.fromhex(new), note)
    # (d) group size
    assert get(SIZE_J - 18, 20) == struct.pack("<10H", 10, 4, 6, 17, 13, 3, 8, 7, 5, 5)
    op(SIZE_J, struct.pack("<H", 6), ".data image (RAM 0x602BE3A2): rows in group 9 (Utility), 5 -> 6 (= E-PL6)")
    spec = {
        "name": "level-adjust-row",
        "description": "Adds the E-PL6's 'Level Adjust' row (calibrate the level gauge: Reset / Adjust) to the "
                       "Custom Menu's last group (Utility), between Warning Level and Touch Screen Settings: panel 173, "
                       "setting 2213, text 160, help 478. A real insert, as on the E-PL6: a 79-row copy of the item "
                       "table (1,266 B at 0x7EBF3000) and a 79-entry copy of the child list (640 B at 0x7EBF3500) in "
                       "the unreferenced `sdk` shell name list 0x7EBF1090-0x7EBF3BAC (segment 2; interval-frames-240 "
                       "has camera-tested table data in the same list), 10 address loads and 11 page-record pointers "
                       "re-pointed, 9 row constants +1 (index 77 -> 78, count 78 -> 79, state array 156 -> 158 B) and "
                       "the group size 5 -> 6 in the .data image. No new code, no hook. The panel, its code, the "
                       "texts and the calibration routines are stock. The row-state array (RAM 0x606A3118) grows by 2 "
                       "bytes into 0x606A31B4-B5, which no byte of block 0 addresses (next addressed object: "
                       "0x606A32F0). Side effect: the `sdk` debug-shell name list loses 1.9 KB more of its text (UART "
                       "/ factory shell only). Checked in the emulator, NOT camera-tested. See "
                       "experiments/2026-11-14-level-gauge/NOTES.md section 12.",
        "base": STOCK, "base_sha256": STOCK_SHA, "ops": ops,
        "status": "candidate: emulator-checked 2026-11-14, not flashed",
    }
    json.dump(spec, open(sys.argv[1], "w"), indent=1)
    changed = sum(sum(x != y for x, y in zip(bytes.fromhex(o["expect"]), bytes.fromhex(o["new"]))) for o in ops)
    print("wrote", sys.argv[1], len(ops), "ops,", sum(len(o["new"]) // 2 for o in ops), "bytes in windows,", changed, "bytes changed")


main()

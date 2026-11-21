"""Write data/specs/level-gauge-lvinfo-row.json (step A): the "Level Gauge" row in Custom Menu > Info Settings > LV-Info.

Research code.

The E-PL6 has one more row in the LV-Info list (panel 192): setting 273, text 866 "Level Gauge".
The E-PM2 has the setting, the texts, the value records and all the code. It lacks:
  (1) the row record in the sub-item row table 0x7EFEF4FC (20 bytes per row; the E-PL6 has 197 rows,
      the E-PM2 196, and the table has no free row), and
  (2) the fourth entry (panel 203, setting 273) in panel 192's child list 0x7EFF9224 (no room either).

The E-PM2 also holds a list that no menu can reach: panel 594, "EVF Info Settings" (rows for settings
446-449, child list 0x7EFFA244). Panel 594 is in no page or panel child list. This spec re-uses its bytes:
  op 0  row 0x7EFF0424 "594 / 448 / Level Gauge" becomes "192 / 273 / Level Gauge". The code reads the
        row table from top to bottom and takes every row whose panel number matches, so the row does not
        have to sit next to the other LV-Info rows. It is the last LV-Info row, as on the E-PL6.
  op 1  panel 594's child list is overwritten with the E-PL6's list for panel 192.
  op 2  panel 192's record points to that list.
No new bytes, no code, no free space, block 0 only.

Usage: uv run python gen/level-gauge/mkspec_step_a.py
"""
import json, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod.container import parse  # noqa: E402

BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
STOCK_SHA = json.load(open(os.path.join(ROOT, "data/specs/interval-frames-240.json")))["base_sha256"]

ROW = 0x7EFF0424        # row "594, 1503, 448, 2, 7, 1, 866"
LIST594 = 0x7EFFA244    # child list of panel 594
OUT = os.path.join(ROOT, "data/specs/level-gauge-lvinfo-row.json")
REC192 = 0x7EFFB02C     # record of panel 192 (LV-Info); +20 = child-list pointer


def row(panel, title, info, text):
    return struct.pack("<HHIIHHHH", panel, title, info, 2, 7, 1, text, 0)


def kids(pairs):
    return b"".join(struct.pack("<II", p, i) for p, i in pairs)


def main():
    blk = parse(open(os.path.join(ROOT, STOCK), "rb").read()).blocks[0].payload
    ops = []

    def op(addr, expect, new, note):
        assert len(expect) == len(new)
        assert blk[addr - BASE:addr - BASE + len(expect)] == expect, "stock bytes differ at %08X" % addr
        ops.append({"type": "bytes", "block": 0, "offset": "0x%X" % (addr - BASE),
                    "expect": expect.hex(), "new": new.hex(), "_addr": "0x%08X" % addr, "_note": note})

    op(ROW, row(594, 1503, 448, 866), row(192, 1646, 273, 866),
       "sub-item row: panel 594 'EVF Info Settings' / setting 448 / text 866 -> panel 192 'LV-Info' (title 1646) / "
       "setting 273 / text 866 'Level Gauge'. Equal to the E-PL6 row at 0x7EFF160C")
    op(LIST594, kids([(607, 446), (608, 447), (609, 448), (610, 449)]),
       kids([(200, 244), (201, 245), (204, 246), (203, 273)]),
       "child list of the unreachable panel 594 -> the E-PL6's child list of panel 192 (0x7EFFA93C): "
       "Histogram, Highlight&Shadow, Image Only, Level Gauge. The zero terminator that follows stays")
    assert blk[LIST594 - BASE + 32:LIST594 - BASE + 40] == bytes(8)
    op(REC192 + 20, struct.pack("<I", 0x7EFF9224), struct.pack("<I", LIST594),
       "panel 192 record: child-list pointer 0x7EFF9224 (3 entries, no room for a 4th) -> 0x7EFFA244")
    spec = {
        "name": "level-gauge-lvinfo-row",
        "description": "Adds the E-PL6's 'Level Gauge' row to Custom Menu > "
                       "Info Settings > LV-Info (panel 192, setting 273, text 866). Data only: 3 edits, 56 bytes "
                       "replaced in place, no new bytes. It re-uses the row and the child list of panel 594 "
                       "('EVF Info Settings'), which no E-PM2 menu reaches. See "
                       "experiments/2026-11-14-level-gauge/NOTES.md.",
        "base": STOCK, "base_sha256": STOCK_SHA, "ops": ops,
    }
    with open(OUT, "w") as f:
        json.dump(spec, f, indent=1)
        f.write("\n")  # the committed file ends with a newline
    print("wrote", os.path.relpath(OUT, ROOT), len(ops), "ops")


main()

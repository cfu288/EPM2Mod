"""Write data/specs/gauge-bar-left-2.json: the level gauge's left position moves right of the left information column.

    uv run python gen/gauge-info/mkspec_gauge_bar_left.py

gauge-bar-left (the first version, on the camera 2026-11-19) moved the rectangles only; its scale dots and marker stayed
at the old place. Their x is not in the lists: 0x7ED7E0CB writes the bases of the gauge marks to RAM 0x602BA42C-37 per
display (as the PEN-F's 0x60C5CE3F does); the left one is `mov 22,d0` (80 16) in each of three variants.

The gauge parts (bar, + mark, - mark, icon) take their rectangle from lists of {x1, y1, x2, y2} s16, one entry per
orientation, in 0x7EF989F8-0x7EF98CE8 (three display variants). Entry 3 is the left edge of the screen (bar x 14-41),
where the ISO and touch icons of the information are. The PEN-F has the same lists (0x60EC85BC...) with its left
bar at x 88-103, right of its information column. This spec adds DX to x1 and x2 of every left entry.
"""

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cli" / "src"))
from epm2mod import container  # noqa: E402

BASE = 0x7E421020
STOCK = ROOT / "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
OUT = ROOT / "data/specs/gauge-bar-left-2.json"
DX = 86  # bar 14-41 -> 100-127: the touch icon ends at x 94
#: (address, kind, stock rectangle): the left entry of each list
LEFT = [
    (0x7EF98A10, "bar, 640 wide", (14, 95, 41, 385)),
    (0x7EF98A50, "bar", (14, 95, 41, 385)),
    (0x7EF98A90, "bar, low", (14, 95, 41, 385)),
    (0x7EF98AD0, "+ mark, 640 wide", (42, 368, 58, 383)),
    (0x7EF98B10, "+ mark", (42, 368, 58, 383)),
    (0x7EF98B50, "+ mark, low", (42, 368, 58, 383)),
    (0x7EF98B90, "- mark, 640 wide", (42, 97, 58, 112)),
    (0x7EF98BD0, "- mark", (42, 97, 58, 112)),
    (0x7EF98C10, "- mark, low", (42, 97, 58, 112)),
    (0x7EF98C50, "icon, 640 wide", (10, 54, 47, 88)),
    (0x7EF98C90, "icon", (10, 54, 47, 88)),
    (0x7EF98CD0, "icon, low", (10, 54, 47, 88)),
]
#: `mov 22,d0` (80 16) of each display variant in 0x7ED7E0CB: the x of the left bar's scale dots and marker
DOTS = [(0x7ED7E10A, "640 wide"), (0x7ED7E16B, "720"), (0x7ED7E1CB, "720 low")]


def main() -> None:
    raw = STOCK.read_bytes()
    img = container.parse(raw).blocks[0].payload
    ops = []
    for addr, kind, rect in LEFT:
        old = img[addr - BASE : addr - BASE + 8]
        assert struct.unpack("<4h", old) == rect, (hex(addr), struct.unpack("<4h", old))
        x1, y1, x2, y2 = rect
        new = struct.pack("<4h", x1 + DX, y1, x2 + DX, y2)
        ops.append(
            {
                "type": "bytes",
                "block": 0,
                "offset": f"{addr - BASE:#x}",
                "expect": old.hex(),
                "new": new.hex(),
                "_addr": f"{addr:#x}",
                "_note": f"level gauge {kind}, left position: x {x1}-{x2} -> {x1 + DX}-{x2 + DX}",
            }
        )
    for addr, kind in DOTS:
        old = img[addr - BASE : addr - BASE + 2]
        assert old == b"\x80\x16", (hex(addr), old.hex())
        ops.append(
            {
                "type": "bytes",
                "block": 0,
                "offset": f"{addr + 1 - BASE:#x}",
                "expect": "16",
                "new": f"{22 + DX:02x}",
                "_addr": f"{addr + 1:#x}",
                "_note": f"level gauge marks, left position, {kind}: x 22 -> {22 + DX} (mov imm8,d0)",
            }
        )
    spec = {
        "name": "gauge-bar-left-2",
        "description": "Level gauge, left position (camera held vertically): the bar, its + and - marks, its icon, its scale dots "
        f"and its marker move {DX} px to the right, past the ISO and touch icons, as the PEN-F places it (x 88-103). "
        "See experiments/2026-11-19-gauge-info/NOTES.md.",
        "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
        "base_sha256": hashlib.sha256(raw).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "ops": ops,
    }
    OUT.write_text(json.dumps(spec, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(ops)} ops")


if __name__ == "__main__":
    main()

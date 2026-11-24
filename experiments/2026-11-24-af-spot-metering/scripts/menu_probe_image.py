"""Write an emulator-only probe image: the pinned build's specs plus one probe spec (never for the camera).

    uv run python experiments/2026-11-24-af-spot-metering/scripts/menu_probe_image.py PROBE OUT.BIN

PROBE shared-picker: LV-Info's child entry 1 (list 201, setting 245 Highlight&Shadow) -> (list 200, setting 245).
  List 200 is the Off/On picker whose descriptor names setting 244 (the histogram). Toggling the Highlight&Shadow
  row shows which setting the picker writes: the child's (245) or the descriptor's (244).
PROBE spot-page: a three-row On/Off page "Spot / Spot Hilight / Spot Shadow" made from stock pieces, data only:
  the sub-item page 594 (class 0x7EDE1E3D, unreachable "EVF Info Settings"), opened from Custom Menu A's AF Mode row
  (its child (100, 25) -> (594, 25); a probe shortcut, a build adds its own row in E). Rows: settings 606 (0x9681),
  660 (0x9F91), 621 (0x9821); texts 171, 106, 107; title 169 "Metering". Pickers: lists 198, 584, 659 (generic list
  pages no table names) with their descriptors' setting changed. Value records (table 0x7EFF0460) of 446, 448, 449
  re-keyed to 606, 660, 621. Panel 594's child list: 32 B at 0x7EBF1F50 (reclaimed `sdk` strings, no pinned spec covers it).
"""

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod.container import parse  # noqa: E402
from epm2mod.spec import apply_specs, load_spec, spec_from_json  # noqa: E402

BASE = 0x7E421020
STOCK = os.path.join(ROOT, "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN")
SETS, TEXTS, LISTS = (606, 660, 621), (171, 106, 107), (198, 584, 659)
OFFON = 0x7F008CC0                                  # list 200's items: Off (text 1371, value 0), On (198, 1)
KIDS = 0x7EBF1F50


def spot_page():
    ops = [(0x7EE3CBF4, struct.pack("<II", 594, 25))]                          # AF Mode row -> page 594
    for a, s, t in zip((0x7EFF03FC, 0x7EFF0410, 0x7EFF0438), SETS, TEXTS):      # the three sub-item rows of 594
        ops.append((a, struct.pack("<HHIIHHHH", 594, 169, s, 2, 7, 1, t, 0)))
    ops.append((KIDS, b"".join(struct.pack("<II", l, s) for l, s in zip(LISTS, SETS)) + bytes(8)))
    ops.append((0x7EFFD804 + 20, struct.pack("<I", KIDS)))                     # panel 594 record: child list
    for desc, s in ((0x7F00C2FC, 606), (0x7F00BCEC, 660)):
        ops.append((desc, struct.pack("<H", s)))
    ops.append((0x7F00C7BC, struct.pack("<HHIII", 621, 2, 0, 1, OFFON)))
    for a, s in ((0x7EFF4AE0, 606), (0x7EFF4B00, 606), (0x7EFF4B60, 660), (0x7EFF4B80, 660), (0x7EFF4BA0, 621),
                 (0x7EFF4BC0, 621)):
        ops.append((a, struct.pack("<I", s)))
    return ops


PROBES = {"shared-picker": lambda: [(0x7EFFA24C, struct.pack("<II", 200, 245))], "spot-page": spot_page}


def main(probe, out):
    stock = open(STOCK, "rb").read()
    specs = [load_spec(Path(ROOT, s)) for s in json.load(open(os.path.join(ROOT, "data/builds/peaking-mf.json")))["specs"]]
    pinned = bytes(parse(apply_specs(stock, specs).image).blocks[0].payload)
    ops = [{"type": "bytes", "block": 0, "offset": hex(a - BASE), "expect": pinned[a - BASE:a - BASE + len(n)].hex(),
            "new": n.hex()} for a, n in PROBES[probe]()]
    specs.append(spec_from_json({"name": "probe-" + probe, "description": "emulator probe", "base": STOCK,
                                 "base_sha256": hashlib.sha256(stock).hexdigest(), "ops": ops}))
    open(out, "wb").write(apply_specs(stock, specs).image)
    print("wrote", out, len(ops), "ops")


if __name__ == "__main__":
    main(*sys.argv[1:])

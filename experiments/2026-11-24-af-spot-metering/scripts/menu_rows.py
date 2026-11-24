"""Print Custom Menu rows (custom-menu-rows-3: item table and child list) and sub-item table rows (stock) for the
labels and panels given, to see how a submenu row (setting 2000) reaches its page.

    uv run python experiments/2026-11-24-af-spot-metering/scripts/menu_rows.py
"""

import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "gen", "lss-menu"))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from blob import Blob  # noqa: E402
from epm2mod.container import parse  # noqa: E402

BASE = 0x7E421020
c = parse(open(os.path.join(ROOT, "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"), "rb").read())
b0, b1 = bytes(c.blocks[0].payload), bytes(c.blocks[1].payload)
eng = next(b for b in (Blob(b1, e) for e in range(1, 35)) if b.code.upper().startswith("EN"))
T = lambda i: eng.text(i) if 0 <= i < 1970 else "?"
spec = json.load(open(os.path.join(ROOT, "data/specs/custom-menu-rows-3.json")))
tab = kids = None
for o in spec["ops"]:
    if o.get("_addr") == "0x7EBF1FE0":
        tab = bytes.fromhex(o["new"])
    if o.get("_addr") == "0x7EE3CBF4":
        kids = bytes.fromhex(o["new"])
print("Custom Menu rows (custom-menu-rows-3): index {group, label, setting, order, help, panel, 0} | child (panel, setting)")
for i in range(len(tab) // 16):
    g, lab, st, order, hlp, pan, z = struct.unpack_from("<HHIHHHH", tab, 16 * i)
    k = struct.unpack_from("<II", kids, 8 * i)
    if g in (0, 3, 4):
        print(i, (g, lab, st, order, hlp, pan, z), k, repr(T(lab)))
print("\nsub-item rows (stock 0x7EFEF4FC): {panel, title, setting, 2, 7, 1, row text, 0}")
for i in range(197):
    r = struct.unpack_from("<HHIIHHHH", b0, 0x7EFEF4FC - BASE + 20 * i)
    if r[0] in (100, 149, 191, 192, 193, 594, 14, 478):
        print(hex(0x7EFEF4FC + 20 * i), r, repr(T(r[1])), repr(T(r[6])))

print("\nCustom Menu rows of groups 0 (A) and 9 (J) in custom-menu-rows-3, after the above")
for i in range(len(tab) // 16):
    g, lab, st, order, hlp, pan, z = struct.unpack_from("<HHIHHHH", tab, 16 * i)
    if g == 9:
        print(i, (g, lab, st, order, hlp, pan, z), struct.unpack_from("<II", kids, 8 * i))
# the pinned image: list descriptors and registry entries of the lists around 594..610
pc = parse(open(os.path.join(ROOT, "build/peaking-mf.BIN"), "rb").read())
p0 = bytes(pc.blocks[0].payload)
w = lambda a, f, n: struct.unpack_from(f, p0, a - BASE)
desc = {w(0x7F00D710 + 8 * i, "<H", 2)[0]: w(0x7F00D710 + 8 * i + 4, "<I", 4)[0] for i in range(312)}
reg = {w(0x7EFE180C + 8 * i, "<H", 2)[0]: w(0x7EFE180C + 8 * i + 4, "<I", 4)[0] for i in range(312)}
print("\nlist id: registry page class | descriptor {setting, count, ?, ?, items} (pinned image)")
for lid in (139, 200, 201, 203, 204, 594, 606, 607, 608, 609, 610, 611, 612):
    d = desc.get(lid)
    print(lid, hex(reg[lid]) if lid in reg else "-", (hex(d), w(d, "<HHIII", 16)) if d else "-")

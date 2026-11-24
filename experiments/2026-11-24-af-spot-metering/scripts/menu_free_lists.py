"""Find list ids of the pinned image that no table names: generic list pages (registry class 0x7EDC7ECB) whose id is
in no page/panel record's child list and in no Custom Menu child entry. Candidates for the three pickers of a
Spot Metering page (unreferenced in tables; code could still open one by number: I).

    uv run python experiments/2026-11-24-af-spot-metering/scripts/menu_free_lists.py [build/NAME.BIN]
"""

import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod.container import parse  # noqa: E402

B = 0x7E421020
D = bytes(parse(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build/peaking-mf.BIN"), "rb").read()).blocks[0].payload)
u32 = lambda a: struct.unpack_from("<I", D, a - B)[0]
st = next(B + o for o in range(0, len(D) - 80, 4) if struct.unpack_from("<5I", D, o) == (1, 0xFFFFFFF1, 0, 1, 2))
refs, a, recs = set(), st, {}
while u32(a):
    r = struct.unpack_from("<10I", D, a - B)
    recs[r[0]] = a
    stride = 12 if 2 <= r[0] <= 6 else 8
    p = r[5]
    if p >> 24 in (0x7E, 0x7F):
        while u32(p):
            refs.add(u32(p))
            p += stride
    a += 40
cm = 0x7EE3CBF4                                   # Custom Menu child list (custom-menu-rows-3), 84 entries
for i in range(84):
    refs.add(u32(cm + 8 * i))
reg = {struct.unpack_from("<H", D, 0x7EFE180C + 8 * i - B)[0]: u32(0x7EFE180C + 8 * i + 4) for i in range(312)}
desc = {struct.unpack_from("<H", D, 0x7F00D710 + 8 * i - B)[0]: u32(0x7F00D710 + 8 * i + 4) for i in range(312)}
print("page/panel records from 0x%08X: %d; panel 594 record 0x%08X child list 0x%08X" % (st, len(recs), recs.get(594, 0), u32(recs[594] + 20) if 594 in recs else 0))
print("generic list ids in no child list: id, descriptor {setting, count, ?, ?, items}")
for lid in sorted(reg):
    if reg[lid] == 0x7EDC7ECB and lid not in refs and lid in desc:
        print(lid, hex(desc[lid]), struct.unpack_from("<HHIII", D, desc[lid] - B))

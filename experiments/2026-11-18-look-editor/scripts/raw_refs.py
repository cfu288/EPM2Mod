"""Every place in stock block 0 where a candidate's info id or prm tag appears as an aligned u16 (weak check).

    python3 experiments/2026-11-18-look-editor/scripts/raw_refs.py ID:TAG ...
Known homes are named: prm ROM default lists, info -> tag table, mcon value lists / defaults, GUI list descriptors.
"""
import struct, sys
B = open("build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin", "rb").read()
BASE = 0x7E421020
HOMES = [  # (lo, hi, name)
    (0x7E4762B4, 0x7E4B113C + 0x3000, "prm-default-lists"),  # CPRAM..MODE lists (wide)
    (0x7E7C95B4, 0x7E7CA6B9, "info->tag"),
    (0x7E84A0B8, 0x7E84A0B8 + 505 * 20, "mcon-valuelist-rec"),
    (0x7E84C82C, 0x7E84C82C + 4 * 701, "mcon-default"),
    (0x7E84D850, 0x7E84E194 + 2 * 843, "mcon-reset/restore"),
    (0x7EF00000, 0x7F030000, "gui-rodata"),
]
def home(a):
    for lo, hi, n in HOMES:
        if lo <= a < hi:
            return n
    return "?"
for arg in sys.argv[1:]:
    i, t = (int(x, 0) for x in arg.split(":"))
    for v, kind in ((i, "id"), (t, "tag")):
        pat = struct.pack("<H", v)
        out = []
        o = B.find(pat)
        while o >= 0:
            if o % 2 == 0:
                out.append((BASE + o, home(BASE + o)))
            o = B.find(pat, o + 1)
        unk = [hex(a) for a, h in out if h == "?"]
        known = {}
        for a, h in out:
            if h != "?":
                known[h] = known.get(h, 0) + 1
        print(arg, kind, "aligned=%d" % len(out), known, "other=%d" % len(unk), " ".join(unk[:12]))

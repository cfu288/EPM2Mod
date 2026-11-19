"""Scan block 0 of the stock firmware for the fixed-point forms of the HSHR 1.4 resize.

Usage: uv run python experiments/2026-11-19-movie-sampling/scripts/geom_scan.py
Prints each hit as a runtime address, with the function that holds it (if build/map has one).
"""
import bisect, struct, sys

BLOCK = "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"
BASE = 0x7E421020
b = open(BLOCK, "rb").read()
starts = []
for line in open("build/map/functions.tsv"):
    f = line.split("\t")
    if f[0] != "addr":
        starts.append((int(f[0], 16), int(f[2])))
starts.sort()
keys = [s for s, _ in starts]


def owner(a):
    i = bisect.bisect_right(keys, a) - 1
    if i >= 0 and a < starts[i][0] + starts[i][1]:
        return hex(starts[i][0])
    return "data"


forms = {
    "Q16 1.4 (u32)": struct.pack("<I", 91750),
    "Q16 1/1.4 (u32)": struct.pack("<I", 46811),
    "Q12 1.4 (u16)": struct.pack("<H", 5734),
    "Q14 1.4 (u16)": struct.pack("<H", 22938),
    "Q15 1/1.4 (u16)": struct.pack("<H", 23405),
    "Q14 1/1.4 (u16)": struct.pack("<H", 11703),
    "2304,1646 (u16 pair)": struct.pack("<HH", 2304, 1646),
    "1646,2304 (u16 pair)": struct.pack("<HH", 1646, 2304),
    "2326 (u16)": struct.pack("<H", 2326),
}
for name, pat in forms.items():
    hits, i = [], b.find(pat)
    while i >= 0:
        hits.append(i)
        i = b.find(pat, i + 1)
    print(f"{name}: {len(hits)} hits")
    for o in hits[:40]:
        a = BASE + o
        print(f"  {a:#x} in {owner(a)}")

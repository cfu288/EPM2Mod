#!/usr/bin/env python3
"""Ad-hoc queries on block 0 (read-only).  q.py win LO HI  -> every 4-byte window (any alignment) with value in [LO, HI)."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach
B = reach.BASE


def win(lo, hi, data=None):
    data = data or open(reach.BLK, "rb").read()
    out = []
    # the two high bytes of every value in range are fixed per 64 KiB, so search for them
    for hi16 in range(lo >> 16, ((hi - 1) >> 16) + 1):
        pat = struct.pack("<H", hi16)
        i = data.find(pat, 2)
        while i >= 0:
            v = struct.unpack_from("<I", data, i - 2)[0]
            if lo <= v < hi:
                out.append((B + i - 2, v))
            i = data.find(pat, i + 1)
    return sorted(out)


if __name__ == "__main__":
    if sys.argv[1] == "win":
        for s, v in win(int(sys.argv[2], 0), int(sys.argv[3], 0)):
            print(f"{s:08x} -> {v:08x}  seg{reach.seg_of(s)}")

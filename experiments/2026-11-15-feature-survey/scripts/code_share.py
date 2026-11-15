"""A rough measure of how much E-PM2 code another body's main block still holds.

    python3 code_share.py EPM2_BLOCK0 OTHER_BLOCK0 [OTHER_BLOCK0 ...]

Takes 40,000 random 12-byte windows from the E-PM2 code range (block offsets 0x1000..0x7D0000,
windows with fewer than 8 distinct bytes dropped) and reports the share found, at any offset, in
the other block. Code with absolute call targets differs between two builds, so the share is far
below 100% even for a sister body; use it only to rank donors. Needs numpy.
"""
import random, sys
import numpy as np


def windows(d: bytes) -> np.ndarray:
    a = np.frombuffer(d, dtype=np.uint8)
    n = len(a) - 12
    lo = np.zeros(n, dtype=np.uint64)
    for k in range(8):
        lo |= a[k:k + n].astype(np.uint64) << np.uint64(8 * k)
    hi = np.zeros(n, dtype=np.uint64)
    for k in range(4):
        hi |= a[8 + k:8 + k + n].astype(np.uint64) << np.uint64(8 * k)
    return lo * np.uint64(0x9E3779B97F4A7C15) ^ hi * np.uint64(0xC2B2AE3D27D4EB4F)


def main() -> None:
    base = open(sys.argv[1], "rb").read()
    rnd = random.Random(1)
    offs = [o for o in (rnd.randrange(0x1000, 0x7D0000) for _ in range(60000)) if len(set(base[o:o + 12])) >= 8][:40000]
    wb = windows(base)[offs]
    for path in sys.argv[2:]:
        w = windows(open(path, "rb").read())
        print(f"{np.isin(wb, w).mean() * 100:5.1f}%  {path.split('/')[-2]}")


main()

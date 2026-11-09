"""Profile the 16-bit tone-curve region of E-PM2 v1.6 block 0 (0x7E74E000-0x7E763FFF, 14d).

Finds monotone runs of u16 words, reports their lengths and spacing, and writes every
256-entry curve to out/curves.tsv (address, unique id, samples at 0/32/64/128/192/224/255).

Usage: python3 profile_curves.py [BLOCK0]
       (default: ../../build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin, made by oetool unpack)
"""
import os
import struct
import sys
from collections import Counter

BASE = 0x7E421020          # runtime address of block-0 offset 0 (firmware-map.md)
LO, HI = 0x7E74E000, 0x7E764000
MIN_RUN = 200

here = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    here, "..", "..", "build", "blocks", "OLY_E_101_1600_0000_0000.BIN.block0.bin")
data = open(path, "rb").read()[LO - BASE:HI - BASE]
w = struct.unpack("<%dH" % (len(data) // 2), data)

runs, start = [], 0
for i in range(1, len(w) + 1):
    if i == len(w) or w[i] < w[i - 1]:
        if i - start >= MIN_RUN:
            runs.append((start, i - start))
        start = i

curves = [(LO + 2 * s, w[s:s + 256]) for s, n in runs if n >= 256]
ids = {}
for _, c in curves:
    ids.setdefault(c, len(ids))
strides = Counter(curves[i + 1][0] - curves[i][0] for i in range(len(curves) - 1))

print(f"runs >= {MIN_RUN} words: {len(runs)}; run lengths {Counter(n for _, n in runs).most_common(6)}")
print(f"256-entry curves: {len(curves)}, unique {len(ids)}, "
      f"{hex(curves[0][0])}..{hex(curves[-1][0])}; strides {strides.most_common(5)}")
print(f"output range {min(min(c) for _, c in curves)}..{max(max(c) for _, c in curves)}")

os.makedirs(os.path.join(here, "out"), exist_ok=True)
with open(os.path.join(here, "out", "curves.tsv"), "w") as f:
    f.write("addr\tuid\ts0\ts32\ts64\ts128\ts192\ts224\ts255\n")
    for a, c in curves:
        f.write("\t".join([hex(a), str(ids[c])] + [str(c[k]) for k in (0, 32, 64, 128, 192, 224, 255)]) + "\n")
print("wrote out/curves.tsv")

"""List the byte runs where a build's block 0 differs from stock, with the load segment of each run.

Usage (from the repository root):
    uv run python experiments/2026-11-24-slow-boot/scripts/changed_runs.py build/emu/stock-*/block0_0100.bin \
        build/emu/peaking-mf-*/block0_0100.bin

The segment comes from tools/freespace.py's load model (emulator/bootmem.py), as emulator/hookcheck.py uses it.
"""

import os
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import hookcheck  # noqa: E402

BASE = 0x7E421020
a, b = (open(p, "rb").read() for p in sys.argv[1:3])
assert len(a) == len(b), "blocks of different size"
runs = []
i = 0
while i < len(a):
    if a[i] != b[i]:
        j = i
        while j < len(a) and (a[j] != b[j] or (j + 8 < len(a) and a[j + 1 : j + 9] != b[j + 1 : j + 9])):
            j += 1
        runs.append((BASE + i, BASE + j))
        i = j
    i += 1
by_seg: Counter[str] = Counter()
for lo, hi in runs:
    seg = hookcheck.segment(lo)
    by_seg[seg] += hi - lo
    print(f"{lo:#010x}-{hi:#010x} {hi - lo:6d} B  {seg}")
print("bytes by segment:", dict(by_seg))

"""lists.py: the layout lists of the rec-view code. Every immediate in the code from 0x7ED99E1D to 0x7ED9D500 that points
into 0x7EFCE000-0x7EFD1000 starts a list; a list ends where the next one starts or at a word > 40. For each list:
address, code sites, values, and whether it holds 8 (histogram) and 22 (level gauge)."""
import re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "cli/src")
from epm2mod import container
BASE = 0x7E421020
img = container.parse(Path("build/epm2mod-2026.11.19.BIN").read_bytes()).blocks[0].payload
w = lambda a: int.from_bytes(img[a - BASE:a - BASE + 4], "little")
LO, HI = 0x7EFCE000, 0x7EFD1000
sites = defaultdict(list)
for line in open("build/map/functions.txt"):
    m = re.match(r"^([0-9a-f]+):\t(\S+)\t(.*)", line)
    if not m: continue
    pc = int(m.group(1), 16)
    if not 0x7ED99E1D <= pc < 0x7ED9D500: continue
    for imm in re.findall(r"\b(\d{9,10})\b", m.group(3)):
        v = int(imm)
        if LO <= v < HI: sites[v].append(m.group(1))
starts = sorted(sites)
for i, a in enumerate(starts):
    end = starts[i + 1] if i + 1 < len(starts) else a + 64
    vals = []
    for p in range(a, end, 4):
        v = w(p)
        if v > 40: break
        vals.append(v)
    print(f"{a:#x} n={len(vals):2} has8={int(8 in vals)} has22={int(22 in vals)} sites={','.join(sites[a][:3])} {vals}")

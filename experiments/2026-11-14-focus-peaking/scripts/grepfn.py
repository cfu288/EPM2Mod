"""grep the per-function disassembly and print the hits grouped by function.

Usage: grepfn.py FUNCTIONS_TXT REGEX [LO HI]   (LO/HI: optional address range, hex)
"""
import re, sys
txt, rx = sys.argv[1], re.compile(sys.argv[2])
lo = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
hi = int(sys.argv[4], 16) if len(sys.argv) > 4 else 1 << 32
cur, hits = None, {}
for l in open(txt, errors="replace"):
    if l.endswith(">:\n"):
        cur = l.split()[0]
        continue
    if rx.search(l):
        a = int(l.split(":")[0], 16) if l[:1] in "67" else 0
        if lo <= a < hi:
            hits.setdefault(cur, []).append(l.rstrip())
for fn, ls in hits.items():
    print(fn, len(ls))
    for l in ls[:12]:
        print("   ", l)

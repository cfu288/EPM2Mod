"""Free bytes left in each area of docs/code-space-map.tsv after builds/card-looks-4.json and the specs given.

    uv run python experiments/2026-11-18-log-menu/scripts/free_after.py patches/log-core.json patches/log-probes.json
"""
import csv, json, sys
from pathlib import Path
from epm2mod.spec import load_spec, BytesOp
BASE = 0x7E421020
specs = json.load(open('builds/card-looks-4.json'))['specs'] + sys.argv[1:]
used = set()
for s in specs:
    for op in load_spec(Path(s)).ops:
        if isinstance(op, BytesOp) and op.block == 0:
            used.update(range(BASE + op.offset, BASE + op.offset + len(op.new)))
rows = list(csv.DictReader(open('docs/code-space-map.tsv'), delimiter='\t'))
tot = {}
for r in rows:
    if r['verdict'] in ('REJECT',): continue
    a, b = int(r['start'], 16), int(r['end'], 16)
    runs, cur = [], None
    for x in range(a, b):
        if x not in used:
            if cur is None: cur = x
        elif cur is not None:
            runs.append((cur, x)); cur = None
    if cur is not None: runs.append((cur, b))
    free = sum(e - s for s, e in runs)
    if free == 0: continue
    big = sorted(runs, key=lambda t: t[0]-t[1])[:4]
    print(f"{r['start']}-{r['end']} {r['region']:10} {r['verdict']:15} use={r['allowed_use']:5} free {free:6} in {len(runs):3} runs; largest {[f'{s:#x}+{e-s}' for s,e in big]}")

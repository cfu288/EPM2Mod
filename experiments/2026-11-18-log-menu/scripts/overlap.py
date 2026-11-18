"""Ops of extra specs on top of builds/card-looks-4.json: does each expect match, and does a pinned spec own the bytes.

    uv run python experiments/2026-11-18-log-menu/scripts/overlap.py patches/log-core.json patches/log-probes.json
"""
import json, sys
from pathlib import Path
from epm2mod.paths import RepoPaths
from epm2mod.stock import read_stock
from epm2mod.spec import load_spec, BytesOp
from epm2mod.container import parse
root = Path.cwd()
paths = RepoPaths(root)
stock = read_stock(paths)
build = json.load(open('builds/card-looks-4.json'))
specs = [load_spec(Path(s)) for s in build['specs']]
c = parse(stock)
pay = [bytearray(b.payload) for b in c.blocks]
owner = {}
for s in specs:
    for op in s.ops:
        if isinstance(op, BytesOp):
            for i in range(len(op.new)):
                owner[(op.block, op.offset+i)] = s.name
            pay[op.block][op.offset:op.offset+len(op.new)] = op.new
for extra in sys.argv[1:]:
    sp = load_spec(Path(extra))
    print('==', sp.name)
    for i, op in enumerate(sp.ops):
        if not isinstance(op, BytesOp): print('  ', i, 'text op'); continue
        found = bytes(pay[op.block][op.offset:op.offset+len(op.expect)])
        owners = {owner[(op.block, op.offset+j)] for j in range(len(op.new)) if (op.block, op.offset+j) in owner}
        raw = json.load(open(extra))['operations'] if 'operations' in json.load(open(extra)) else None
        note = ''
        ok = found == op.expect
        diff = sum(a != b for a, b in zip(found, op.expect))
        print(f'   op{i:2} b{op.block}+{op.offset:#x} len {len(op.new):4} {"OK " if ok else "BAD"} diffbytes={diff:4} owners={sorted(owners)}')
    # apply if possible for chaining
    for op in sp.ops:
        if isinstance(op, BytesOp):
            for j in range(len(op.new)):
                owner[(op.block, op.offset+j)] = sp.name
            pay[op.block][op.offset:op.offset+len(op.new)] = op.new

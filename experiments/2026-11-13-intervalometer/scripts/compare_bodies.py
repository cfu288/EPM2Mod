#!/usr/bin/env python3
"""Run the menu cases on several block-0 images and compare them row for row.

    python3 compare_bodies.py [--cases=a,b] OUT.json NAME=BLOCK0 ...      (first image = reference for the 'vs' columns)

For each case and row: every image's outputs, its model check, and which images differ from the others.
Uses tools/emu (om-emu). Rows are compared on public outputs only (keys without a leading '_').
"""
import json, sys, os
sys.path.insert(0, '/path/to/EPM2Mod/tools/emu')
import emurun
from cases import CASES
args = sys.argv[1:]
cases = ('menu_help', 'menu_child', 'menu_value')
if args[0].startswith('--cases='):
    cases = tuple(args.pop(0).split('=', 1)[1].split(','))
out = args[0]
imgs = [a.split('=', 1) for a in args[1:]]
report = {}
for cname in cases:
    case = CASES[cname]
    res = {n: emurun.run_image(case, p) for n, p in imgs}
    rows = []
    for i, row in enumerate(case.rows()):
        outs = {n: emurun.public(res[n][i][1]) for n, _ in imgs}
        errs = {n: res[n][i][3] for n, _ in imgs if res[n][i][3]}
        rows.append({"row": row, "out": outs, "errors": errs})
    report[cname] = rows
json.dump(report, open(out, 'w'), indent=1)
names = [n for n, _ in imgs]
for cname, rows in report.items():
    nerr = sum(bool(r["errors"]) for r in rows)
    print(f"== {cname}: {len(rows)} rows, {nerr} with model/run errors")
    for r in rows:
        o = r["out"]
        if r["errors"]:
            print("  ERR", r["row"], r["errors"])
        groups = {}
        for n in names:
            groups.setdefault(json.dumps(o[n], sort_keys=True), []).append(n)
        if len(groups) > 1:
            print("  diff", r["row"], " | ".join(f"{'+'.join(v)}: {k}" for k, v in groups.items()))

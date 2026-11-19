#!/usr/bin/env python3
# crawldiff.py DIR_A DIR_B OUT: compare two crawl output folders (crawl.mjs) screen by screen (byte compare of the PNGs).
# Prints: counts, the names only in A / only in B, the differing names; writes OUT/<name>.png = A left, B right for each
# differing screen (at most MAXPAIRS, default 400) and OUT/report.txt. Also lists notes and firmware-error entries of the logs.
import sys, os, json, subprocess, glob, filecmp
a, b, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
na = {f for f in os.listdir(a) if f.endswith('.png')}; nb = {f for f in os.listdir(b) if f.endswith('.png')}
same = [f for f in sorted(na & nb) if filecmp.cmp(f'{a}/{f}', f'{b}/{f}', shallow=False)]
diff = [f for f in sorted(na & nb) if f not in set(same)]
lines = [f'A={a} ({len(na)} screens)  B={b} ({len(nb)} screens)', f'same {len(same)}  differ {len(diff)}  only-A {len(na - nb)}  only-B {len(nb - na)}']
def units(names):
    d = {}
    for n in names: d.setdefault(n.split('.')[0].split('-entry')[0], []).append(n)
    return d
for title, names in (('DIFFER', diff), ('ONLY-A', sorted(na - nb)), ('ONLY-B', sorted(nb - na))):
    lines.append(f'--- {title}')
    for u, ns in sorted(units(names).items()):
        # compress to top-level rows
        rows = {}
        for n in ns: rows.setdefault('.'.join(n[:-4].split('.')[:2]), []).append(n)
        lines.append(f'{u}: {len(ns)}: ' + ' '.join(f'{r}({len(v)})' for r, v in sorted(rows.items())))
sheet = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sheet.py')
for f in diff[:int(os.environ.get('MAXPAIRS', 400))]:
    subprocess.run(['python3', sheet, f'{out}/{f}', '2', '1', f'{a}/{f}', f'{b}/{f}'], check=False, stdout=subprocess.DEVNULL)
for side, d in (('A', a), ('B', b)):
    lines.append(f'--- logs {side}')
    for lf in sorted(glob.glob(f'{d}/*.log.json')):
        L = json.load(open(lf)); errs = [x for x in L if x.get('err')]; notes = [x for x in L if x.get('note') and not x['note'].startswith('DOWN does nothing') and 'TOPMAX' not in x['note']]
        kinds = {}
        for x in notes: kinds[x['note'].split(':')[0][:40]] = kinds.get(x['note'].split(':')[0][:40], 0) + 1
        allerr = sorted({e.split(' ', 1)[1] for x in errs for e in x['err']})
        if kinds or len(allerr) > 1: lines.append(f'{os.path.basename(lf)}: {len(L)} entries, distinct firmware errors {len(allerr)} {allerr[:4]}, notes {kinds}')
    lines.append('(logs without notes and with only the boot-time error 0x2a001001 are not listed)')
open(f'{out}/report.txt', 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))

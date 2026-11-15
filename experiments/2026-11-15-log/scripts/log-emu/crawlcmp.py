#!/usr/bin/env python3
"""crawlcmp.py PINNED_DIR NEW_DIR OUT: compare two menu crawls (audit/crawl.mjs output) when one image has one more
Custom Menu row.

The Custom Menu's rows are one long list that wraps, and the crawl walks it in units of 8 rows (custrows00..15). One
more row shifts every later row to another unit and index, so those units cannot be compared name by name.
  1. Units other than custrowsNN: per-name byte compare of the PNGs (as audit/crawldiff.py).
  2. custrowsNN units: compare the SETS of screens (sha1 of the PNG file). "Lost" = a screen that some pinned unit
     shows and no new unit shows. "New" = the reverse. Each is listed with the top row it was seen under.
  3. Logs: firmware errors and crawler notes per side.
Writes OUT/report.txt and OUT/lost-*.png / OUT/new-*.png (one copy of each lost or new screen, at most 60 each).
"""
import sys, os, json, glob, hashlib, shutil, filecmp, collections
a, b, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
L = []
def P(s=''): L.append(s); print(s)
na = {f for f in os.listdir(a) if f.endswith('.png')}; nb = {f for f in os.listdir(b) if f.endswith('.png')}
isrow = lambda f: f.startswith('custrows')
P(f'pinned {a}: {len(na)} screens; new {b}: {len(nb)} screens')
# 1. per name
ua = {f for f in na if not isrow(f)}; ub = {f for f in nb if not isrow(f)}
same = [f for f in sorted(ua & ub) if filecmp.cmp(f'{a}/{f}', f'{b}/{f}', shallow=False)]
diff = sorted((ua & ub) - set(same))
P(f'1. units other than custrowsNN, by name: same {len(same)}, differ {len(diff)}, only pinned {len(ua - ub)}, only new {len(ub - ua)}')
for t, s in (('differ', diff), ('only pinned', sorted(ua - ub)), ('only new', sorted(ub - ua))):
    by = collections.Counter(n.split('.')[0].split('-entry')[0] for n in s)
    if s: P(f'   {t}: ' + ', '.join(f'{u} {c}' for u, c in sorted(by.items())) + ' | ' + ' '.join(s[:12]))
# 2. by content
def hashes(d, names):
    h = collections.defaultdict(list)
    for f in sorted(names): h[hashlib.sha1(open(f'{d}/{f}', 'rb').read()).hexdigest()].append(f)
    return h
ha = hashes(a, [f for f in na if isrow(f)]); hb = hashes(b, [f for f in nb if isrow(f)])
lost = sorted(set(ha) - set(hb), key=lambda h: ha[h][0]); new = sorted(set(hb) - set(ha), key=lambda h: hb[h][0])
P(f'2. custrowsNN units, by content: pinned {sum(map(len, ha.values()))} screens / {len(ha)} distinct, new {sum(map(len, hb.values()))} / {len(hb)} distinct; in both {len(set(ha) & set(hb))}, lost {len(lost)}, new {len(new)}')
top = lambda n: '.'.join(n[:-4].split('.')[:2])
for t, hs, hh, d in (('lost (pinned only)', lost, ha, a), ('new (new image only)', new, hb, b)):
    rows = collections.Counter(top(hh[h][0]) for h in hs)
    P(f'   {t}, by the top row of the first sighting: ' + ', '.join(f'{r} {c}' for r, c in sorted(rows.items())))
    for k, h in enumerate(hs[:60]): shutil.copyfile(f'{d}/{hh[h][0]}', f'{out}/{t.split()[0]}-{k:02d}-{hh[h][0]}')
    for h in hs[:200]: P(f'      {hh[h][0]}' + (f' (+{len(hh[h]) - 1} more sightings)' if len(hh[h]) > 1 else ''))
# 3. logs
for side, d in (('pinned', a), ('new', b)):
    errs = collections.Counter(); notes = collections.Counter(); early = []
    for lf in sorted(glob.glob(f'{d}/*.log.json')):
        for x in json.load(open(lf)):
            for e in x.get('err', []): errs[e.split(' ', 1)[1][:60]] += 1
            n = x.get('note')
            if n and not n.startswith('DOWN does nothing') and 'TOPMAX' not in n:
                if isrow(os.path.basename(lf)): notes['custrows: ' + n.split(':')[0][:50]] += 1
                else: notes[os.path.basename(lf)[:-9] + ': ' + n.split(':')[0][:50]] += 1
            if n and ('DESYNC' in n or 'ENDED EARLY' in n or x['name'] in ('STOP', 'LIMIT')): early.append(x['name'] + ' ' + n[:60])
    P(f'3. logs {side}: distinct firmware errors {dict(errs)}')
    P(f'   notes: {dict(sorted(notes.items()))}')
    P(f'   stops: {early}')
open(f'{out}/report.txt', 'w').write('\n'.join(L) + '\n')

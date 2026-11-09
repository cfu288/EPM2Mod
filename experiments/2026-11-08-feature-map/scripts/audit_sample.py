# Draw a reproducible random sample of "verified" claims from sections 01-08 for an audit.
# A claim = one table row or bullet line that is labelled verified ("verified", "[V]") and cites an address.
import re, glob, random, sys, os, json
root = sys.argv[1]; per = int(sys.argv[2]); seed = int(sys.argv[3])
ADDR = re.compile(r'0x7[EF][0-9A-Fa-f]{6}|0x[0-9A-Fa-f]{4,}')
VER = re.compile(r'\bverified\b|\*\*\[V\]\*\*|\[V\]', re.I)
random.seed(seed); out = []
for path in sorted(glob.glob(os.path.join(root, 'sections', '0[1-8]-*.md'))):
    sec = os.path.basename(path)[:2]; claims = []
    for n, line in enumerate(open(path), 1):
        t = line.strip()
        if not (t.startswith('|') or t.startswith('-') or re.match(r'\d+\.', t)): continue
        if t.startswith('|---') or not VER.search(t) or not ADDR.search(t): continue
        if re.search(r'\binferred\b|\[I\]', t, re.I) and not re.search(r'verified|\[V\]', t, re.I): continue
        claims.append((n, t))
    pick = random.sample(claims, min(per, len(claims)))
    for n, t in sorted(pick):
        out.append({'id': f'{sec}-{n}', 'section': os.path.basename(path), 'line': n, 'text': t})
    print(f'{os.path.basename(path)}: {len(claims)} candidate claims, sampled {len(pick)}')
json.dump(out, open(os.path.join(root, 'audit', 'sample.json'), 'w'), indent=1)
print('total', len(out))

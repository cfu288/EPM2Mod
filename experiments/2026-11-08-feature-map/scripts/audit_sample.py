# Draw a reproducible random sample of "verified" claims from section files for an audit.
# usage: audit_sample.py ROOT PER_SECTION SEED [GLOB (default 0[1-8]-*.md)] [OUT (default sample.json)]
# A claim = one table row or bullet line that is labelled verified ("verified", "[V]") and cites an address.
import re, glob, random, sys, os, json
root = sys.argv[1]; per = int(sys.argv[2]); seed = int(sys.argv[3])
glob_pat = sys.argv[4] if len(sys.argv) > 4 else '0[1-8]-*.md'   # which section files
out_name = sys.argv[5] if len(sys.argv) > 5 else 'sample.json'
ADDR = re.compile(r'0x7[EF][0-9A-Fa-f]{6}|0x[0-9A-Fa-f]{4,}')
VER = re.compile(r'\bverified\b|\*\*\[V\]\*\*|\[V\]', re.I)
random.seed(seed); out = []
for path in sorted(glob.glob(os.path.join(root, 'sections', glob_pat))):
    sec = os.path.basename(path)[:2]; claims = []
    for n, line in enumerate(open(path), 1):
        t = line.strip()
        if not (t.startswith('|') or t.startswith('-') or re.match(r'\d+\.', t)): continue
        if t.startswith('|---') or not VER.search(t) or not ADDR.search(t): continue
        if re.search(r'\binferred\b|\[I\]', t, re.I) and not re.search(r'verified|\[V\]', t, re.I): continue
        claims.append((n, t))
    pick = random.sample(claims, min(per, len(claims)))
    for n, t in sorted(pick):
        out.append({'id': f'{os.path.basename(path)[:3].rstrip("-")}-{n}', 'section': os.path.basename(path), 'line': n, 'text': t})
    print(f'{os.path.basename(path)}: {len(claims)} candidate claims, sampled {len(pick)}')
json.dump(out, open(os.path.join(root, 'audit', out_name), 'w'), indent=1)
print('total', len(out))

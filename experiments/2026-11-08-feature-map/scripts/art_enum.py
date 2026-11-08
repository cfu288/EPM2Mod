import sys, re, os
sys.path.insert(0, sys.argv[1] + '/tools'); import oetool
pfx = sys.argv[2].encode()
for f in sys.argv[3:]:
    blocks, _ = oetool.parse(open(f, 'rb').read())
    b0 = blocks[0]['payload']
    seen = []
    for m in re.finditer(re.escape(pfx) + rb'[A-Z0-9_]+(?= *\x00)', b0):
        n = m.group().decode()[len(pfx):]
        if n not in seen: seen.append(n)
    print(os.path.basename(f)[6:14], len(seen), ' '.join(seen))

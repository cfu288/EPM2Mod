# Find block-0 runtime base: the base that makes most `mov imm32,aN/dN` values land on string starts.
import sys, re, collections, random
sys.path.insert(0, sys.argv[1] + '/tools'); import oetool
for f in sys.argv[2:]:
    blocks, _ = oetool.parse(open(f, 'rb').read())
    b = blocks[0]['payload']
    starts = [m.start() for m in re.finditer(rb'(?<=\x00)[\x20-\x7e]{12,}\x00', b)]
    sset = set(starts)
    imms = [int.from_bytes(b[m.start()+2:m.start()+6], 'little') for m in re.finditer(rb'\xfc[\xdc\xdd\xde\xdf\xcc\xcd\xce\xcf]', b)]
    random.seed(1); sample = random.sample(starts, min(400, len(starts)))
    cnt = collections.Counter()
    imset = set(imms)
    for v in set(imms):
        for s in sample:
            d = (v - s) & 0xFFFFFFFF
            if d & 0xF == 0: cnt[d] += 1
    best = [(d, n) for d, n in cnt.most_common(5)]
    out = []
    for d, n in best:
        hits = sum(1 for v in imset if (v - d) & 0xFFFFFFFF in sset)
        out.append(f'{d:#010x}:{hits}')
    print(f.split('/')[-1][6:14], ' '.join(out))

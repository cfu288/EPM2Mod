#!/usr/bin/env python3
"""Follow supported instructions from lens entry stubs; report every gap."""

import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path

from r32c import Decoder, Unknown


def analyze(image):
    data = image[32:-32]
    decoder = Decoder(data)
    seeds = list(range(4, 0x7C, 8))
    for p in range(0x7C, 0x400):
        if data[p:p+3] == bytes.fromhex('5bfffb') and data[p+6:p+9] == bytes.fromhex('7bffcf'):
            seeds.append(p)
    pending = seeds[:]
    insns, gaps, outside, clashes = {}, {}, [], []
    owner = {}
    while pending:
        p = pending.pop()
        while 0 <= p < 0x9400 and p not in insns and p not in gaps:
            if p in owner:
                clashes.append([p, owner[p]])
                break
            try:
                ins = decoder.decode(p)
            except Unknown as exc:
                gaps[p] = {'reason': str(exc), 'bytes': data[p:p+12].hex(' ')}
                break
            if any(a in owner for a in range(p, p+ins.size)):
                clashes.append([p, 'overlap'])
                break
            insns[p] = ins
            for a in range(p, p+ins.size):
                owner[a] = p
            if ins.target is not None:
                if 0 <= ins.target < 0x9400:
                    pending.append(ins.target)
                else:
                    outside.append({'caller': p, 'target': ins.target, 'kind': ins.kind})
            if ins.kind in ('return', 'jump', 'indirect_jump'):
                break
            p += ins.size
    return {
        'seeds': seeds,
        'instructions': [asdict(insns[p]) for p in sorted(insns)],
        'decoded_bytes': len(owner),
        'gaps': {hex(p): gaps[p] for p in sorted(gaps)},
        'outside': outside,
        'clashes': clashes,
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = analyze(args.image.read_bytes())
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print({k: len(result[k]) for k in ('seeds', 'instructions', 'gaps', 'outside', 'clashes')},
          'bytes', result['decoded_bytes'])
    print('gap opcodes:', Counter(v['bytes'].split()[0] for v in result['gaps'].values()))
    for p, gap in list(result['gaps'].items())[:20]:
        print(p, gap)

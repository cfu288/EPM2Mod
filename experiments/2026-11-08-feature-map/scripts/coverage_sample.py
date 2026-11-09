# Draw random code functions from block 0 for a blind coverage test of the map.
import sys, random, json, os
sys.path.insert(0, sys.argv[1] + '/tools'); import fwmap
n, seed, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
rows = [r for r in fwmap.load_tsv('functions.tsv') if r[7] == '0' and int(r[2]) >= 32]
random.seed(seed)
pick = sorted(random.sample(rows, n), key=lambda r: int(r[0], 16))
json.dump([{'id': f'F{i+1:03d}', 'addr': '0x' + r[0].upper(), 'size': int(r[2])} for i, r in enumerate(pick)], open(out, 'w'), indent=1)
print(len(rows), 'candidate functions; sampled', n)

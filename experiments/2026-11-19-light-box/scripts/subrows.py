"""subrows.py BUILD.json OUT.bin: write the build's block 0 to OUT.bin and list the panels whose sub-item rows
(table 0x7EFEF4FC, 196 records of 20 B) no child list of the 361 menu panel records names.

    uv run python experiments/2026-11-19-light-box/scripts/subrows.py data/builds/cold-start-fix.json /tmp/b0.bin
"""
import collections, json, struct, sys
sys.path.insert(0, 'gen/lss-menu')
from mkspec import image  # noqa: E402
B = 0x7E421020
D, _ = image(json.load(open(sys.argv[1]))['specs'])
open(sys.argv[2], 'wb').write(D)
u32 = lambda a: struct.unpack_from("<I", D, a - B)[0]
T0, T1 = 0x7EFEF4FC, 0x7EFF044C
rows = [(T0 + i * 20,) + struct.unpack_from("<HHIIHHHH", D, T0 + i * 20 - B) for i in range((T1 - T0) // 20)]
st = next(B + o for o in range(0, len(D) - 80, 4) if struct.unpack_from("<5I", D, o) == (1, 0xFFFFFFF1, 0, 1, 2))
a, ref = st, collections.Counter()
while u32(a):
    r = struct.unpack_from("<10i", D, a - B); stride = 12 if 2 <= r[0] <= 6 else 8; p = r[5] & 0xFFFFFFFF
    if p >> 24 in (0x7E, 0x7F):
        while u32(p): ref[struct.unpack_from("<i", D, p - B)[0]] += 1; p += stride
    a += 40
byp = collections.defaultdict(list)
for r in rows: byp[r[1]].append(r)
for pid, rs in sorted(byp.items()):
    if ref[pid] == 0:
        print('panel', pid, 'in no child list:', [(hex(r[0]), r[2], r[3], r[7]) for r in rs])

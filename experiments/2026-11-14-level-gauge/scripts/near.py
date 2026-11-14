"""near.py BLOCK0 WINDOW V1 V2 [V3...]: addresses where the u16 values V1.. all occur (aligned) within WINDOW bytes."""
import sys, struct
d = open(sys.argv[1], "rb").read(); B = 0x7E421020; W = int(sys.argv[2]); ids = [int(x, 0) for x in sys.argv[3:]]
pos = {v: [] for v in ids}
for o in range(0, len(d) - 1, 2):
    v = d[o] | d[o + 1] << 8
    if v in pos: pos[v].append(o)
import bisect
for o in pos[ids[0]]:
    ok = []
    for v in ids[1:]:
        p = pos[v]; i = bisect.bisect_left(p, o - W)
        if i < len(p) and p[i] <= o + W: ok.append(p[i])
        else: break
    else:
        s = min([o] + ok) - 8; e = max([o] + ok) + 10
        print("%08x:" % (B + s), " ".join("%d" % x for x in struct.unpack_from("<%dH" % ((e - s) // 2), d, s)))

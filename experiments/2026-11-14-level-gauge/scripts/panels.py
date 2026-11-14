"""panels.py BLOCK0: dump the 361 menu page/panel records (40 bytes each) and their child lists.
Pointers are printed as '@' so that two bodies can be compared with diff. --raw keeps addresses."""
import struct, sys
B = 0x7E421020
D = open(sys.argv[1], "rb").read(); raw = "--raw" in sys.argv
u32 = lambda a: struct.unpack_from("<I", D, a - B)[0]
st = None
for o in range(0, len(D) - 80, 4):
    if struct.unpack_from("<5I", D, o) == (1, 0xFFFFFFF1, 0, 1, 2): st = B + o; break
a = st
def kids(p, stride):
    out = []
    while u32(p):
        out.append(tuple(struct.unpack_from("<%di" % (stride // 4), D, p - B))); p += stride
    return out
while u32(a):
    r = struct.unpack_from("<10i", D, a - B)
    pid = r[0]; stride = 12 if 2 <= pid <= 6 else 8
    k = kids(r[5] & 0xFFFFFFFF, stride) if (r[5] & 0xFFFFFFFF) >> 24 == 0x7E or (r[5] & 0xFFFFFFFF) >> 24 == 0x7F else []
    f = ["@" if (x & 0xFFFFFFFF) >> 24 in (0x7E, 0x7F) and not raw else ("%x" % (x & 0xFFFFFFFF) if (x & 0xFFFFFFFF) >> 24 in (0x7E, 0x7F) else str(x)) for x in r]
    print(("%08x " % a if raw else "") + " ".join(f), k)
    a += 40

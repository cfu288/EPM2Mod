"""rowtable.py BLOCK0 ANY_ROW_ADDR [EN_TSV]: find the bounds of the sub-item row table (20-byte records
{u16 panel, u16 title, u32 info, u32 a, u16 b, u16 c, u16 text, u16 0}) and dump it; then list pointers to it."""
import sys, struct
d = open(sys.argv[1], "rb").read(); B = 0x7E421020
T = {}
if len(sys.argv) > 3:
    for l in open(sys.argv[3], errors="replace"):
        p = l.rstrip("\n").split("\t", 1); T[int(p[0])] = p[1][:30].replace("\n", " ")
a = int(sys.argv[2], 0)
rec = lambda x: struct.unpack_from("<HHIIHHHH", d, x - B)
ok = lambda r: r[7] == 0 and r[0] < 1000 and r[1] < 2100 and r[6] < 2100 and r[3] < 64
s = a
while ok(rec(s - 20)): s -= 20
e = a
while ok(rec(e)) and rec(e)[0]: e += 20
print("table %08x..%08x rows %d" % (s, e, (e - s) // 20))
x = s
while x < e + 20:
    r = rec(x); print("%08x %4d %4d %5d  %d %d %d  %4d | %s / %s" % (x, r[0], r[1], r[2], r[3], r[4], r[5], r[6], T.get(r[1], ""), T.get(r[6], ""))); x += 20
for t in (s, e):
    k = struct.pack("<I", t); i = -1
    while (i := d.find(k, i + 1)) >= 0: print("ref to %08x at %08x" % (t, B + i))

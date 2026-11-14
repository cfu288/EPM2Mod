"""onlyblobs.py DONOR_BLOCK0 EPM2_BLOCK0 [MINRUN]: runs of 32-byte chunks of the donor that occur nowhere in the
E-PM2 block (any 4-aligned offset). Pointer tables and code with addresses always differ; pixel data and
plain tables match. Prints runs >= MINRUN bytes with a rough class (share of zero / pointer-like words)."""
import sys, struct
a = open(sys.argv[1], "rb").read(); b = open(sys.argv[2], "rb").read()
B = 0x7E421020; N = 32; minrun = int(sys.argv[3]) if len(sys.argv) > 3 else 512
have = set()
for o in range(0, len(b) - N, 4): have.add(hash(b[o:o + N]))
for sh in (0,):
    run = None; out = []
    for o in range(sh, len(a) - N, N):
        miss = hash(a[o:o + N]) not in have
        if miss and run is None: run = o
        if not miss and run is not None:
            if o - run >= minrun: out.append((run, o))
            run = None
    for s, e in out:
        w = struct.unpack_from("<%dI" % ((e - s) // 4), a, s)
        ptr = sum(1 for x in w if 0x7E000000 <= x < 0x7F200000 or 0x60000000 <= x < 0x61000000) / len(w)
        print("%08x-%08x %7d B  ptr-like %.2f" % (B + s, B + e, e - s, ptr))

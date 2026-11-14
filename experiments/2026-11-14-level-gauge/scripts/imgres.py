"""imgres.py EPM2_BLOCK1 DONOR_BLOCK1: compare the image resource tables of block-1 entry 0.
Entry 0 = image data, then a table of pointers (one per image id). Prints the table sizes, the load base,
and an alignment of the two id lists by image content (which donor ids have no E-PM2 image)."""
import sys, struct, hashlib, difflib
def load(p):
    d = open(p, "rb").read()
    a, s = struct.unpack_from("<2I", d, 0); o = a - 0x43C40000; e = d[o:o + s]
    best = None; run = 0
    for i in range(0, len(e) - 4, 4):
        v = struct.unpack_from("<I", e, i)[0]
        if 0xBF000000 <= v < 0xC0000000:
            if run == 0: start = i
            run += 1
        else:
            if run >= 100: best = (start, run)
            run = 0
    start, n = best
    ptr = struct.unpack_from("<%dI" % n, e, start)
    base = min(ptr)  # the first image is at entry offset 0 (checked: gives sizes that tile the data)
    srt = sorted(set(ptr)) + [base + start]
    nxt = {srt[i]: srt[i + 1] for i in range(len(srt) - 1)}
    imgs = [e[q - base:nxt[q] - base] for q in ptr]
    return e, start, n, base, ptr, imgs
A = load(sys.argv[1]); Bd = load(sys.argv[2])
for nm, X in (("E-PM2", A), ("donor", Bd)):
    print("%s: table at entry offset 0x%x, %d ids, load base 0x%08x, image bytes %d" % (nm, X[1], X[2], X[3], sum(len(i) for i in X[5])))
ha = [hashlib.md5(i).hexdigest() for i in A[5]]; hb = [hashlib.md5(i).hexdigest() for i in Bd[5]]
sm = difflib.SequenceMatcher(None, ha, hb, autojunk=False)
for t, i1, i2, j1, j2 in sm.get_opcodes():
    if t != "equal":
        print(t, "E-PM2 ids %d..%d (%d)" % (i1, i2 - 1, i2 - i1), "donor ids %d..%d (%d)" % (j1, j2 - 1, j2 - j1),
              "sizes E-PM2", [len(x) for x in A[5][i1:i2]][:12], "donor", [len(x) for x in Bd[5][j1:j2]][:12])

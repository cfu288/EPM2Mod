"""datawalk.py EPM2_BLOCK0 DONOR_BLOCK0 EPM2_START DONOR_START EPM2_END: walk two data regions in step and
print inserts, deletes and replaced bytes. Words that look like addresses in both bodies count as equal.
The regions must start at the same item in both bodies (use a string that both have)."""
import sys, struct
a = open(sys.argv[1], "rb").read(); b = open(sys.argv[2], "rb").read(); B = 0x7E421020
i = int(sys.argv[3], 0) - B; j = int(sys.argv[4], 0) - B; end = int(sys.argv[5], 0) - B
def isptr(d, o):
    return d[o + 3] in (0x7E, 0x7F, 0x60) if o + 3 < len(d) else False
def eq(i, j):
    if a[i] == b[j]: return True
    for k in range(4):  # inside a pointer word at any alignment
        if i - k >= 0 and isptr(a, i - k) and isptr(b, j - k): return True
    return False
def same(i, j, n=48):
    return all(eq(i + k, j + k) for k in range(n))
while i < end:
    if eq(i, j): i += 1; j += 1; continue
    found = None
    for skip in range(1, 6000):
        for da, db in ((0, skip), (skip, 0), (skip, skip)):
            if same(i + da, j + db): found = (da, db); break
        if found: break
    if not found:
        for da in range(0, 6000, 2):
            for db in range(0, 6000, 2):
                if same(i + da, j + db, 32): found = (da, db); break
            if found: break
    if not found: print("lost sync at E-PM2 %08x donor %08x" % (B + i, B + j)); break
    da, db = found
    kind = "insert(donor)" if da == 0 else "delete(donor)" if db == 0 else "replace"
    print("%-13s E-PM2 %08x +%d | donor %08x +%d | %s | %s" % (kind, B + i, da, B + j, db, a[i:i + min(da, 24)].hex(), b[j:j + min(db, 24)].hex()))
    i += da; j += db
print("end E-PM2 %08x donor %08x" % (B + i, B + j))

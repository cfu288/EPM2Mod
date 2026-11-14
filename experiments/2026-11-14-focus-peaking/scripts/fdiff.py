"""Side-by-side difference of one E-P5 function and one E-PM2 function.

Instructions are compared after addresses and large numbers are replaced by placeholders.
Only the hunks that differ are printed, with the raw disassembly lines of both bodies.

Usage: fdiff.py EP5_MAP_DIR EPM2_MAP_DIR EP5_FN EPM2_FN [context]
"""
import difflib, re, sys

NUM = re.compile(r"(?<![\w.])-?\d+(?![\w.])")
SYMREF = re.compile(r"[0-9a-f]{8} <[^>]*>")


def fn_lines(mapdir, fn):
    off = None
    for l in open(mapdir + "/fnidx.tsv"):
        p = l.split()
        if p and p[0] == "%08x" % fn:
            off = int(p[1])
            break
    if off is None:
        sys.exit("function %08x not in %s" % (fn, mapdir))
    out = []
    f = open(mapdir + "/functions.txt", errors="replace")
    f.seek(off)
    first = True
    for l in f:
        if l.endswith(">:\n"):
            if not first:
                break
            first = False
            continue
        if len(l) > 9 and l[8] == ":":
            out.append(l.rstrip("\n"))
    return out


def norm(l, fn):
    p = l.split("\t")
    mn = p[1].strip() if len(p) > 1 else ""
    op = p[2] if len(p) > 2 else ""
    m = SYMREF.search(op)
    if mn in ("call", "calls") and m:
        return mn + " F"
    if m:
        t = int(m.group()[:8], 16)
        if mn.startswith(("b", "l", "jmp")) and abs(t - fn) < 0x10000 and "(" not in op:
            op = "L"
        else:
            op = SYMREF.sub("A", op)
    op = NUM.sub(lambda mm: "A" if abs(int(mm.group())) >= 0x8000 else mm.group(), op)
    return mn + " " + op


def main():
    a, b = int(sys.argv[3], 16), int(sys.argv[4], 16)
    ctx = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    la, lb = fn_lines(sys.argv[1], a), fn_lines(sys.argv[2], b)
    na, nb = [norm(l, a) for l in la], [norm(l, b) for l in lb]
    sm = difflib.SequenceMatcher(None, na, nb, autojunk=False)
    same = sum(i2 - i1 for t, i1, i2, j1, j2 in sm.get_opcodes() if t == "equal")
    print("E-P5 %08x: %d insns   E-PM2 %08x: %d insns   equal after normalising: %d" % (a, len(la), b, len(lb), same))
    for group in sm.get_grouped_opcodes(ctx):
        print("-" * 60)
        for t, i1, i2, j1, j2 in group:
            if t == "equal":
                for l in la[i1:i2]:
                    print("    " + l[:70])
            else:
                for l in la[i1:i2]:
                    print("P5  " + l[:90])
                for l in lb[j1:j2]:
                    print("PM2 " + l[:90])


main()

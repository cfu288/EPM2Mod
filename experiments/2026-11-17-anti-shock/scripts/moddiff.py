#!/usr/bin/env python3
"""Align the functions of one module in two bodies, in link order.

Both firmwares link the camera core in the same file order, so the functions of one
module appear in the same order in both. Each function is reduced to a signature
(normalised instructions: addresses and large numbers replaced by placeholders) and the
two signature lists are aligned with difflib.

Usage:
    moddiff.py MAP_A A_START A_END MAP_B B_START B_END [--all]

MAP_x is a function database made by tools/fwmap.py (functions.txt, fnidx.tsv).
Output: one line per function: `=` identical after normalising, `~` paired but different
(with the count of equal instructions), `A` only in A, `B` only in B.
"""
import difflib
import re
import sys

NUM = re.compile(r"(?<![\w.])-?\d+(?![\w.])")
SYMREF = re.compile(r"[0-9a-f]{8} <[^>]*>")


def load(mapdir, lo, hi):
    idx = []
    for line in open(mapdir + "/fnidx.tsv"):
        p = line.split()
        try:
            a = int(p[0], 16)
        except (ValueError, IndexError):
            continue
        if lo <= a < hi:
            idx.append((a, int(p[1])))
    out = []
    f = open(mapdir + "/functions.txt", errors="replace")
    for a, off in idx:
        f.seek(off)
        first = True
        lines = []
        for line in f:
            if line.endswith(">:\n"):
                if not first:
                    break
                first = False
                continue
            if len(line) > 9 and line[8] == ":":
                lines.append(line.rstrip("\n"))
        out.append((a, lines))
    return out


def norm(line, fn):
    p = line.split("\t")
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
    show_all = "--all" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--all"]
    fa = load(args[0], int(args[1], 16), int(args[2], 16))
    fb = load(args[3], int(args[4], 16), int(args[5], 16))
    sa = ["\n".join(norm(l, a) for l in ls) for a, ls in fa]
    sb = ["\n".join(norm(l, b) for l in ls) for b, ls in fb]
    sm = difflib.SequenceMatcher(None, sa, sb, autojunk=False)
    n_eq = n_mod = n_a = n_b = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                n_eq += 1
                if show_all:
                    print("=  %08x %08x  %d insns" % (fa[i1 + k][0], fb[j1 + k][0], len(fa[i1 + k][1])))
            continue
        # inside a changed block, pair functions greedily by similarity, keeping order
        ia, jb = i1, j1
        while ia < i2 or jb < j2:
            if ia < i2 and jb < j2:
                best, bj = 0.0, None
                for j in range(jb, min(j2, jb + 6)):
                    r = difflib.SequenceMatcher(None, sa[ia].split("\n"), sb[j].split("\n"), autojunk=False).ratio()
                    if r > best:
                        best, bj = r, j
                if best >= 0.5:
                    for j in range(jb, bj):
                        n_b += 1
                        print("B           %08x  %d insns" % (fb[j][0], len(fb[j][1])))
                    eq = sum(
                        x[2] - x[1]
                        for x in difflib.SequenceMatcher(
                            None, sa[ia].split("\n"), sb[bj].split("\n"), autojunk=False
                        ).get_opcodes()
                        if x[0] == "equal"
                    )
                    n_mod += 1
                    print("~  %08x %08x  %d / %d insns, %d equal" % (fa[ia][0], fb[bj][0], len(fa[ia][1]), len(fb[bj][1]), eq))
                    ia += 1
                    jb = bj + 1
                else:
                    n_a += 1
                    print("A  %08x           %d insns" % (fa[ia][0], len(fa[ia][1])))
                    ia += 1
            elif ia < i2:
                n_a += 1
                print("A  %08x           %d insns" % (fa[ia][0], len(fa[ia][1])))
                ia += 1
            else:
                n_b += 1
                print("B           %08x  %d insns" % (fb[jb][0], len(fb[jb][1])))
                jb += 1
    print("# identical %d, changed %d, only A %d, only B %d" % (n_eq, n_mod, n_a, n_b))


main()

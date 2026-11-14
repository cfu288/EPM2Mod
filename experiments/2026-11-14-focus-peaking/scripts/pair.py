"""Pair functions of two firmware bodies (E-P5 1.8 <-> E-PM2 1.6).

Method (the same idea as the interval work used for E-PL6 <-> E-PM2):
  1. Fingerprint each function: its instruction list with every large number (address,
     pointer, big constant) replaced by "A" and branch targets written relative to the
     function start. "strict" keeps small numbers (struct offsets, constants); "loose"
     keeps only the mnemonics and register operands.
  2. Pair functions whose strict fingerprint is unique in both bodies.
  3. Pair functions that load the same unique set of strings.
  4. Propagate: when two paired functions make the same number of calls, pair the
     callees in order (and check the loose fingerprint).
Output: TSV  ep5_addr  epm2_addr  how  strict_equal  loose_equal  size_ep5  size_epm2

Usage: pair.py EP5_MAP_DIR EPM2_MAP_DIR OUT_TSV CACHE_DIR
The map directories are only read. Fingerprint caches go to CACHE_DIR (a scratch folder).
"""
import collections, hashlib, pickle, os, re, sys

NUM = re.compile(r"(?<![\w.])-?\d+(?![\w.])")
SYMREF = re.compile(r"[0-9a-f]{8} <[^>]*>")


def load(mapdir, cache):
    src = os.path.join(mapdir, "functions.txt")
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(src):
        return pickle.load(open(cache, "rb"))
    fns = {}
    cur = None
    for l in open(src, errors="replace"):
        if l.endswith(">:\n") and l[8:11] == " <f":
            cur = int(l[:8], 16)
            fns[cur] = [[], [], [], 0]  # strict, loose, callees, size
            continue
        if cur is None or len(l) < 10 or l[8] != ":":
            continue
        a = int(l[:8], 16)
        parts = l.rstrip("\n").split("\t")
        mn = parts[1].strip() if len(parts) > 1 else ""
        op = parts[2] if len(parts) > 2 else ""
        rec = fns[cur]
        rec[3] = a - cur + 1
        if mn in ("call", "calls") and SYMREF.search(op):
            rec[2].append(int(SYMREF.search(op).group()[:8], 16))
            rest = op.split(">", 1)[1] if ">" in op else ""
            rec[0].append(mn + " F" + rest)
            rec[1].append(mn)
            continue
        m = SYMREF.search(op)
        if m:
            t = int(m.group()[:8], 16)
            if mn.startswith(("b", "l", "jmp")) and abs(t - cur) < 0x10000 and "(" not in op:
                op_s = "+%x" % (t - cur)
                op_l = "L"
            else:
                op_s = SYMREF.sub("A", op)
                op_l = op_s
        else:
            op_s = op_l = op

        def big(mm):
            v = int(mm.group())
            return "A" if abs(v) >= 0x8000 else mm.group()

        op_s = NUM.sub(big, op_s)
        op_l = NUM.sub("N", op_l)
        rec[0].append(mn + " " + op_s)
        rec[1].append(mn + " " + op_l)
    out = {}
    for a, (s, lo, cal, size) in fns.items():
        out[a] = (hashlib.md5("\n".join(s).encode()).hexdigest(),
                  hashlib.md5("\n".join(lo).encode()).hexdigest(), cal, size, len(s))
    pickle.dump(out, open(cache, "wb"))
    return out


def strsets(mapdir):
    d = collections.defaultdict(set)
    for l in open(os.path.join(mapdir, "strrefs.tsv"), errors="replace"):
        p = l.rstrip("\n").split("\t")
        if len(p) >= 4 and p[0] != "fn":
            d[int(p[0], 16)].add(p[3])
    return d


def main():
    cdir = sys.argv[4]
    A = load(sys.argv[1], os.path.join(cdir, "fp_a.pkl"))
    B = load(sys.argv[2], os.path.join(cdir, "fp_b.pkl"))
    pairs = {}
    how = {}
    used = set()

    def add(a, b, h):
        if a in pairs or b in used or a not in A or b not in B:
            return False
        pairs[a] = b
        used.add(b)
        how[a] = h
        return True

    # 2. unique strict fingerprints (skip tiny functions)
    ia, ib = collections.defaultdict(list), collections.defaultdict(list)
    for a, r in A.items():
        if r[4] >= 6:
            ia[r[0]].append(a)
    for b, r in B.items():
        if r[4] >= 6:
            ib[r[0]].append(b)
    for k, la in ia.items():
        lb = ib.get(k)
        if lb and len(la) == 1 and len(lb) == 1:
            add(la[0], lb[0], "strict")
    # 3. unique string sets
    sa, sb = strsets(sys.argv[1]), strsets(sys.argv[2])
    ka, kb = collections.defaultdict(list), collections.defaultdict(list)
    for a, s in sa.items():
        ka[frozenset(s)].append(a)
    for b, s in sb.items():
        kb[frozenset(s)].append(b)
    for k, la in ka.items():
        lb = kb.get(k)
        if lb and len(la) == 1 and len(lb) == 1 and sum(len(x) for x in k) >= 8:
            add(la[0], lb[0], "strings")
    # unique single strings
    oa, ob = collections.defaultdict(set), collections.defaultdict(set)
    for a, s in sa.items():
        for x in s:
            oa[x].add(a)
    for b, s in sb.items():
        for x in s:
            ob[x].add(b)
    for x, fa in oa.items():
        fb = ob.get(x)
        if fb and len(fa) == 1 and len(fb) == 1 and len(x) >= 10:
            add(next(iter(fa)), next(iter(fb)), "string1")
    # 4. propagate through call lists
    changed = True
    while changed:
        changed = False
        for a, b in list(pairs.items()):
            ca, cb = A[a][2], B[b][2]
            if len(ca) == len(cb):
                for x, y in zip(ca, cb):
                    if x in A and y in B and x not in pairs and y not in used:
                        same = A[x][1] == B[y][1]
                        near = how[a] != "calls?" and abs(A[x][4] - B[y][4]) <= max(3, A[x][4] // 5)
                        if same or near:
                            if add(x, y, "calls" if same else "calls?"):
                                changed = True
    with open(sys.argv[3], "w") as f:
        for a in sorted(pairs):
            b = pairs[a]
            f.write("%08x\t%08x\t%s\t%d\t%d\t%d\t%d\n" % (
                a, b, how[a], A[a][0] == B[b][0], A[a][1] == B[b][1], A[a][3], B[b][3]))
    c = collections.Counter(how.values())
    print(len(A), len(B), len(pairs), dict(c))


main()

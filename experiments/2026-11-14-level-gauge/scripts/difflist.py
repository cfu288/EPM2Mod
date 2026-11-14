"""difflist.py PAIRS_TSV PL6_MAP PM2_MAP: paired functions that are not identical after normalising,
and donor functions with no pair, each with its first debug string."""
import sys, collections
pairs, plm, pmm = sys.argv[1:4]
def strs(m):
    d = collections.defaultdict(list)
    for l in open(m + "/strrefs.tsv", errors="replace"):
        p = l.rstrip("\n").split("\t")
        if len(p) >= 4 and p[0] != "fn": d[int(p[0], 16)].append(p[3][:60])
    return d
def fns(m):
    d = {}
    for l in open(m + "/functions.tsv"):
        p = l.split("\t")
        try: d[int(p[0], 16)] = int(p[2])
        except ValueError: pass
    return d
S = strs(plm); F = fns(plm); P = {}
for l in open(pairs):
    p = l.split("\t"); a = int(p[0], 16); P[a] = p
    if p[3] == "0":
        print("DIFF %s %s %-7s loose=%s size %s -> %s  %s" % (p[0], p[1], p[2], p[4], p[5], p[6].strip(), "; ".join(S[a][:2])))
for a in sorted(F):
    if a not in P and F[a] >= 12:
        print("ONLY %08x size %d  %s" % (a, F[a], "; ".join(S[a][:2])))

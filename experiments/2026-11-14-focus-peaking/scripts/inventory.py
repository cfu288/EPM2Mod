"""Inventory of E-P5 functions that carry focus-peaking logic, with their E-PM2 counterpart.

A function is listed when its disassembly has one of these marks:
  A  art code 188/189 (ART_EXPOSE_PEAKING_WHITE/BLACK) as an immediate
  M  picture-mode value 201/202 (the internal "peaking" picture modes)
  F  a call to the peaking-active getter 0x7E3AD2B3
  K  access to IMG_PARAM.ucPeak (offset 109) inside the IMG library
  S  a peaking debug string
Usage: inventory.py EP5_MAP_DIR PAIRS_TSV
"""
import re, sys, collections
mapdir, pairs_tsv = sys.argv[1:3]
pairs = {}
for l in open(pairs_tsv):
    p = l.rstrip("\n").split("\t")
    pairs[p[0]] = p
size = {}
for l in open(mapdir + "/functions.tsv"):
    p = l.split("\t")
    size[p[0]] = p[2]
marks = collections.defaultdict(set)
cur = None
for l in open(mapdir + "/functions.txt", errors="replace"):
    if l.endswith(">:\n"):
        cur = l[:8]
        continue
    if len(l) < 10 or l[8] != ":":
        continue
    a = int(l[:8], 16)
    if not 0x7E200000 <= a < 0x7E440000:
        continue
    if re.search(r"\t(cmp|mov)\t(188|189),", l): marks[cur].add("A")
    if re.search(r"\t(cmp|mov)\t(201|202),", l): marks[cur].add("M")
    if "call\t7e3ad2b3" in l: marks[cur].add("F")
    if a < 0x7E23B050 and re.search(r"\(109,a\d\)", l): marks[cur].add("K")
for l in open(mapdir + "/strrefs.tsv", errors="replace"):
    p = l.rstrip("\n").split("\t")
    if len(p) >= 4 and re.search(r"(?i)peaking|ucPeak", p[3]):
        marks[p[0]].add("S")
tot = 0
for fn in sorted(marks):
    q = pairs.get(fn)
    m = "".join(sorted(marks[fn]))
    if q:
        d = int(q[5]) - int(q[6])
        tot += max(d, 0)
        print("%s %-4s %5s -> %s %5s  %+5d  %s" % (fn, m, q[5], q[1], q[6], d, q[2]))
    else:
        print("%s %-4s %5s -> (no pair)" % (fn, m, size.get(fn, "?")))
print("sum of positive size differences of paired functions:", tot)

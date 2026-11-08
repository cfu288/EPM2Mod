import sys, re, collections
SYM = re.compile(r'^([0-9a-f]{8}) <'); INS = re.compile(r'^\s*([0-9a-f]+):\tmov\t(\d+),d\d$')
cur = None; M = collections.defaultdict(set); A = set(); J = set(); C = collections.defaultdict(set)
for l in open(sys.argv[1] + '/functions.txt'):
    m = SYM.match(l)
    if m: cur = int(m.group(1), 16); continue
    m = INS.match(l)
    if m: M[cur].add(int(m.group(2)))
    if '\tadd\t-100,d0' in l: A.add(cur)
    if '\tjmp\t(a0)' in l: J.add(cur)
    m = re.search(r'\tcmp\t(1[0-9][0-9]),d0$', l)
    if m: C[cur].add(int(m.group(1)))
for f in A & J:
    s = M[f]
    if {25, 26, 33, 34} <= s:
        print(f'{f:08x}', 'cmp', sorted(C[f]), 'exif movs', sorted(v for v in s if v < 64))

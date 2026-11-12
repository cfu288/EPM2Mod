# strpair.py REGEX: pair E-PM2/E-PL6 functions by the (unique) strings they reference, then diff
import sys, re, collections
sys.path.insert(0,'/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/scripts')
from pairlib import A,B,diff
S='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/'
def load(p):
    m=collections.defaultdict(set)
    for l in open(p):
        f=l.rstrip('\n').split('\t',3)
        if len(f)<4 or f[0]=='fn': continue
        m[f[3]].add(int(f[0],16))
    return m
SA=load('/path/to/epm2-tools/build/map/strrefs.tsv'); SB=load(S+'map-112_1400/strrefs.tsv')
rx=re.compile(sys.argv[1]); v='-v' in sys.argv
done=set(); onlyA=[]; onlyB=[]
for t in sorted(set(SA)|set(SB)):
    if not rx.search(t): continue
    fa=SA.get(t,set()); fb=SB.get(t,set())
    if not fa: onlyB.append((t,[hex(x) for x in fb])); continue
    if not fb: onlyA.append((t,[hex(x) for x in fa])); continue
    if len(fa)!=1 or len(fb)!=1: continue
    a=fa.pop(); b=fb.pop()
    if (a,b) in done: continue
    done.add((a,b))
    if a not in A or b not in B: print('missing fn',hex(a),hex(b)); continue
    d=diff(a,b)
    print('%x -> %x  %-45s insns %d/%d hunks %d'%(a,b,t[:45],len(A[a]),len(B[b]),len(d)))
    if v and d:
        for k,x,y in d[:15]:
            for l in x: print('      -',l)
            for l in y: print('      +',l)
            print('      ..')
print('strings only in E-PM2:',onlyA)
print('strings only in E-PL6:',onlyB)

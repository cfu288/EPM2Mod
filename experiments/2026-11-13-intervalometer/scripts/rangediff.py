import sys, bisect
sys.path.insert(0,'/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/scripts')
from pairlib import *
v='-v' in sys.argv; tot=0; same=0
for r in [x for x in sys.argv[1:] if x!='-v']:
    lo,hi=[int(x,16) for x in r.split('-')]
    for a in sa[bisect.bisect_left(sa,lo):bisect.bisect_left(sa,hi)]:
        tot+=1
        b,ratio=counterpart(a)
        if b is None: print('%x NO MATCH'%a); continue
        d=diff(a,b)
        if not d: same+=1; continue
        print('%x -> %x ratio %.2f insns %d/%d hunks %d'%(a,b,ratio,len(A[a]),len(B[b]),len(d)))
        if v:
            for t,x,y in d[:12]:
                for l in x: print('    -',l)
                for l in y: print('    +',l)
                print('    ..')
print('functions',tot,'identical',same)

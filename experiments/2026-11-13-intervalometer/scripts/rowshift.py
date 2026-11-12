# rowshift.py LO-HI...: find paired functions whose diffs replace an immediate k by k+1 (11<=k<=36),
# i.e. code that may index top-menu rows by global row number
import sys, bisect, re
sys.path.insert(0,'/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/scripts')
from pairlib import *
num=re.compile(r'\b(\d+)\b')
for r in sys.argv[1:]:
    lo,hi=[int(x,16) for x in r.split('-')]
    for a in sa[bisect.bisect_left(sa,lo):bisect.bisect_left(sa,hi)]:
        b,ratio=counterpart(a)
        if b is None or ratio<0.8: continue
        for t,x,y in diff(a,b):
            if t!='replace' or len(x)!=len(y): continue
            for p,q in zip(x,y):
                np_,nq=num.findall(p),num.findall(q)
                if len(np_)==len(nq) and num.sub('#',p)==num.sub('#',q):
                    dd=[(int(u),int(v)) for u,v in zip(np_,nq) if u!=v]
                    if dd and all(v==u+1 and 10<=u<=40 for u,v in dd): print('%x -> %x: %s  |  %s'%(a,b,p,q))

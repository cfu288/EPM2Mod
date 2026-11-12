# cmp.py PM2ADDR PL6ADDR LEN [LEN2]: normalised diff
import sys, difflib
sys.path.insert(0,'/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/scripts')
from dis import dis, norm
a,b=int(sys.argv[1],0),int(sys.argv[2],0); n=int(sys.argv[3],0); n2=int(sys.argv[4],0) if len(sys.argv)>4 else n
A=dis('pm2',a,n); Bl=dis('pl6',b,n2)
na=[norm(l) for l in A]; nb=[norm(l) for l in Bl]
sm=difflib.SequenceMatcher(None,na,nb,autojunk=False)
nd=0
for tag,i1,i2,j1,j2 in sm.get_opcodes():
    if tag=='equal': continue
    nd+=1
    for l in A[i1:i2]: print('-',l.strip())
    for l in Bl[j1:j2]: print('+',l.strip())
    print('..')
print('insns',len(A),len(Bl),'diff hunks',nd)

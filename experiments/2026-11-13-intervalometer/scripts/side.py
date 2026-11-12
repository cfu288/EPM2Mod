import sys
sys.path.insert(0,'/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/scripts')
from dis import dis
a,b,n=int(sys.argv[1],16),int(sys.argv[2],16),int(sys.argv[3],0)
for body,x in (('pm2',a),('pl6',b)):
    print('---',body,hex(x))
    for l in dis(body,x,n):
        p=l.split('\t')
        if len(p)>2: print(p[0],' '.join(p[2:]))

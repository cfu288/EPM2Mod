import sys,ast,difflib
def load(f):
    out={}
    for l in open(f):
        h,k=l.split(' [',1); p=h.split(); out[int(p[0])]=(p[1:],ast.literal_eval('['+k))
    return out
A=load(sys.argv[1]);B=load(sys.argv[2])
for pid in sorted(set(A)|set(B)):
    a=A.get(pid);b=B.get(pid)
    if a==b: continue
    if not a or not b: print(pid,'only',a,b);continue
    if a[0]!=b[0]: print(pid,'rec',a[0],b[0])
    sm=difflib.SequenceMatcher(None,a[1],b[1],autojunk=False)
    for t,i1,i2,j1,j2 in sm.get_opcodes():
        if t!='equal': print(pid,'kids',t,'pm2',a[1][i1:i2],'pl6',b[1][j1:j2], 'at index',i1)

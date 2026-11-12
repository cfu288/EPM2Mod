import pickle, bisect, difflib
S='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/'
A,B,pairs=pickle.load(open(S+'fnmatch.pkl','rb'))
ka=sorted(pairs); sb=sorted(B); sa=sorted(A)
def counterpart(a):
    if a in pairs: return pairs[a],1.0
    i=bisect.bisect_right(ka,a)-1
    off=pairs[ka[i]]-ka[i]; guess=a+off
    j=bisect.bisect_left(sb,guess-0x200); best=(None,0)
    for b in sb[j:j+80]:
        if b-guess>0x200: break
        r=difflib.SequenceMatcher(None,A[a],B[b],autojunk=False).ratio()
        if r>best[1]: best=(b,r)
    return best
def diff(a,b):
    sm=difflib.SequenceMatcher(None,A[a],B[b],autojunk=False)
    return [(t,A[a][i1:i2],B[b][j1:j2]) for t,i1,i2,j1,j2 in sm.get_opcodes() if t!='equal']

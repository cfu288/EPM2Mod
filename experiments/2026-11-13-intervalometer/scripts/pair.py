# pair.py [-v] PM2ADDR... : find the E-PL6 counterpart of each E-PM2 function and diff normalised text
import pickle, bisect, sys, difflib
S='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/'
A,B,pairs=pickle.load(open(S+'fnmatch.pkl','rb'))
ka=sorted(pairs); sb=sorted(B)
def counterpart(a):
    if a in pairs: return pairs[a],'anchor'
    i=bisect.bisect_right(ka,a)-1
    if i<0: return None,'none'
    off=pairs[ka[i]]-ka[i]; guess=a+off
    j=bisect.bisect_left(sb,guess-0x40)
    best=None
    for b in sb[j:j+40]:
        if abs(b-guess)>0x400: break
        r=difflib.SequenceMatcher(None,A[a],B[b],autojunk=False).ratio()
        if best is None or r>best[1]: best=(b,r)
    return (best[0] if best else None),'near %.2f'%(best[1] if best else 0)
def fnof(a):
    sa=sorted(A); i=bisect.bisect_right(sa,a)-1; return sa[i]
verbose='-v' in sys.argv
for x in [s for s in sys.argv[1:] if s!='-v']:
    a=fnof(int(x,16))
    b,how=counterpart(a)
    if b is None: print(hex(a),'no counterpart'); continue
    sm=difflib.SequenceMatcher(None,A[a],B[b],autojunk=False)
    d=[op for op in sm.get_opcodes() if op[0]!='equal']
    print('%x -> %x (%s) insns %d/%d diff hunks %d'%(a,b,how,len(A[a]),len(B[b]),len(d)))
    if verbose:
        for t,i1,i2,j1,j2 in d:
            for l in A[a][i1:i2]: print('   -',l)
            for l in B[b][j1:j2]: print('   +',l)
            print('   ..')

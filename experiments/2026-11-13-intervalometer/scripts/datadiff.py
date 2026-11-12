# datadiff.py: align the two .data init images (E-PM2 0x7E8DA000.., E-PL6 the same start) on u16 words and print
# replaced runs where pointers are normalised away; flags runs whose values differ by +1 (possible row renumbering)
import struct, difflib
B=0x7E421020
SC='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/blocks/'
D=open(SC+'OLY_E_101_1600_0000_0000.BIN.block0.bin','rb').read(); P=open(SC+'OLY_E_112_1400_0000_0000.BIN.block0.bin','rb').read()
def words(X,lo,n): return list(struct.unpack_from('<%dH'%(n//2),X,lo-B))
N=0x19200
a=words(D,0x7E8DA000,N); b=words(P,0x7E8DA000,N)
sm=difflib.SequenceMatcher(None,a,b,autojunk=False)
for t,i1,i2,j1,j2 in sm.get_opcodes():
    if t=='equal': continue
    x,y=a[i1:i2],b[j1:j2]
    plus1 = t=='replace' and len(x)==len(y) and all(v==u or v==u+1 for u,v in zip(x,y)) and any(v==u+1 for u,v in zip(x,y))
    if t!='replace' or plus1 or len(x)<=12:
        print('%-7s RAM %08x (%d w) | E-PL6 RAM %08x (%d w)%s'%(t,0x602A9B40+2*i1,i2-i1,0x602A9B40+2*j1,j2-j1,'  +1-RUN' if plus1 else ''),
              ' '.join('%x'%v for v in x[:16]),'|',' '.join('%x'%v for v in y[:16]))

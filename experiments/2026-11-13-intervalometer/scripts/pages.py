import struct,sys
B=0x7E421020
F={'pm2':'blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin','pl6':'blocks/OLY_E_112_1400_0000_0000.BIN.block0.bin'}
def load(body):
    D=open('/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/'+F[body],'rb').read()
    u32=lambda a:struct.unpack_from('<I',D,a-B)[0]
    # find record table start: first record id 1, -15
    st=None
    for o in range(0,len(D)-80,4):
        if struct.unpack_from('<5I',D,o)==(1,0xFFFFFFF1,0,1,2): st=B+o; break
    recs={}; a=st
    while u32(a)!=0:
        recs[u32(a)]=(a,)+struct.unpack_from('<10I',D,a-B); a+=40
    return D,u32,st,recs
def kids(u32,p,stride):
    out=[]; a=p
    while True:
        e=[u32(a+4*k) for k in range(stride//4)]
        if e[0]==0: break
        out.append(tuple(e)); a+=stride
    return out,a
if __name__=='__main__':
    body=sys.argv[1]; D,u32,st,recs=load(body)
    print('table',hex(st),len(recs))
    for pid in map(int,sys.argv[2:]):
        r=recs.get(pid)
        if not r: print(pid,"none"); continue
        stride=12 if 2<=pid<=6 else 8
        k,end=kids(u32,r[6],stride)
        print(pid,'rec',hex(r[0]),'type',r[3],'f4',r[5],'kids@',hex(r[6]),'end',hex(end),k)

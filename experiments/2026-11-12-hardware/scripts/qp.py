import struct,sys,pickle,collections
F=sys.argv[1]; data=open(F,'rb').read(); at=pickle.load(open(sys.argv[2],'rb')); P=pickle.load(open(sys.argv[3],'rb'))
sys.path.insert(0,sys.argv[4]); 
class BR:
    def __init__(s,b): s.b=b; s.p=0
    def u(s,n):
        v=0
        for _ in range(n): v=(v<<1)|((s.b[s.p>>3]>>(7-(s.p&7)))&1); s.p+=1
        return v
    def ue(s):
        z=0
        while s.u(1)==0: z+=1
        return (1<<z)-1+s.u(z)
    def se(s):
        k=s.ue(); return (k+1)//2 if k&1 else -(k//2)
def rbsp(n):
    o=bytearray(); z=0
    for c in n[:64]:
        if z>=2 and c==3: z=0; continue
        o.append(c); z=z+1 if c==0 else 0
    return bytes(o)
base='/moov/trak/mdia/minf/stbl/'
co,ce=at[base+'stco'][0]; nc=struct.unpack('>I',data[co+4:co+8])[0]; chunks=struct.unpack(f'>{nc}I',data[co+8:co+8+4*nc])
sc,sce=at[base+'stsc'][0]; ns=struct.unpack('>I',data[sc+4:sc+8])[0]; stsc=[struct.unpack('>III',data[sc+8+12*i:sc+20+12*i]) for i in range(ns)]
sizes=P['sizes']; keys=set(P['keys'])
# sample offsets
offs=[]; si=0
for ci,c in enumerate(chunks,1):
    spc=[e[1] for e in stsc if e[0]<=ci][-1]; o=c
    for _ in range(spc):
        if si>=len(sizes): break
        offs.append(o); o+=sizes[si]; si+=1
qps=[]; types=collections.Counter(); nslices=collections.Counter()
for i,(o,sz) in enumerate(zip(offs,sizes)):
    end=o+sz; p=o; fq=[]; ns_=0
    while p+4<=end:
        l=struct.unpack('>I',data[p:p+4])[0]; nal=data[p+4:p+4+l]; p+=4+l
        t=nal[0]&31; ref=(nal[0]>>5)&3
        if t not in (1,5): continue
        ns_+=1
        r=BR(rbsp(nal[1:])); r.ue(); st=r.ue(); r.ue(); r.u(P['l2fn'])
        if t==5: r.ue()
        if st%5 in (0,):  # P
            if r.u(1): r.ue()
            if r.u(1): raise SystemExit('ref list modification present')
        if st%5==2 and False: pass
        if ref:
            if t==5: r.u(1); r.u(1)
            else:
                if r.u(1): raise SystemExit('adaptive marking present')
        q=P['qp']+r.se(); fq.append(q); types['I' if st%5==2 else 'P']+=1
    nslices[ns_]+=1
    qps.append((i+1, i+1 in keys, sizes[i], fq[0] if fq else None))
Iq=[q for _,k,_,q in qps if k]; Pq=[q for _,k,_,q in qps if not k]
print('slices per frame',dict(nslices),'slice types',dict(types))
print('I-frame QP: min',min(Iq),'max',max(Iq),'dist',sorted(collections.Counter(Iq).items()))
print('P-frame QP: min',min(Pq),'max',max(Pq),'dist',sorted(collections.Counter(Pq).items()))
big=sorted(qps,key=lambda x:-x[2])[:5]; print('largest frames (n, key, bytes, qp):',big)

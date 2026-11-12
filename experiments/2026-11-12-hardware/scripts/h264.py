import struct,sys,pickle,statistics
F=sys.argv[1]; data=open(F,'rb').read(); at=pickle.load(open(sys.argv[2],'rb'))
def box(path,i=0): return at[path][i]
class BR:
    def __init__(s,b): s.b=b; s.p=0
    def u(s,n):
        v=0
        for _ in range(n):
            v=(v<<1)|((s.b[s.p>>3]>>(7-(s.p&7)))&1); s.p+=1
        return v
    def ue(s):
        z=0
        while s.u(1)==0: z+=1
        return (1<<z)-1+s.u(z)
    def se(s):
        k=s.ue(); return (k+1)//2 if k&1 else -(k//2)
def rbsp(n):
    o=bytearray(); z=0
    for c in n:
        if z>=2 and c==3: z=0; continue
        o.append(c); z = z+1 if c==0 else 0
    return bytes(o)
# video track: the first trak
vs,ve=at['/moov/trak/mdia/minf/stbl/stsd/avc1'][0]
w,h=struct.unpack('>HH',data[vs+32:vs+36]); print('avc1',w,'x',h)
p=vs+86
while p<ve:
    sz,typ=struct.unpack('>I4s',data[p:p+8])
    if typ==b'avcC': avcc=data[p+8:p+sz]; break
    p+=sz
print('avcC profile',avcc[1],'compat',hex(avcc[2]),'level',avcc[3],'NAL len',(avcc[4]&3)+1)
q=5; nsps=avcc[q]&31; q+=1; sps=[]
for _ in range(nsps):
    l=struct.unpack('>H',avcc[q:q+2])[0]; sps.append(avcc[q+2:q+2+l]); q+=2+l
npps=avcc[q]; q+=1; pps=[]
for _ in range(npps):
    l=struct.unpack('>H',avcc[q:q+2])[0]; pps.append(avcc[q+2:q+2+l]); q+=2+l
r=BR(rbsp(sps[0][1:])); prof=r.u(8); cons=r.u(8); lvl=r.u(8); spsid=r.ue()
print('SPS profile_idc',prof,'constraints',bin(cons),'level_idc',lvl)
if prof in (100,110,122,244,44,83,86,118,128):
    cf=r.ue(); 
    if cf==3: r.u(1)
    r.ue(); r.ue(); r.u(1); m=r.u(1)
    print(' chroma_format_idc',cf,'seq_scaling_matrix',m)
    if m:
        for i in range(8 if cf!=3 else 12):
            if r.u(1):
                size=16 if i<6 else 64; last=8; nxt=8; lst=[]
                for j in range(size):
                    if nxt!=0: nxt=(last+r.se()+256)%256
                    v= last if nxt==0 else nxt; lst.append(v); last=v
                print(f'  scaling list {i} ({size}): {lst}')
            else: print(f'  scaling list {i}: not present (fallback)')
l2fn=r.ue()+4; poc=r.ue(); l2poc=None
if poc==0: l2poc=r.ue()+4
elif poc==1: raise SystemExit('poc type 1')
nref=r.ue(); gaps=r.u(1); wmb=r.ue()+1; hmu=r.ue()+1; fmo=r.u(1)
if not fmo: r.u(1)
d8=r.u(1); crop=r.u(1)
if crop: cr=[r.ue() for _ in range(4)]; print(' crop',cr)
print(' max_frame_num bits',l2fn,'poc_type',poc,'num_ref_frames',nref,'size MB',wmb,'x',hmu,'frame_mbs_only',fmo,'direct_8x8',d8)
vui=r.u(1)
if vui:
    if r.u(1):
        idc=r.u(8)
        if idc==255: r.u(16); r.u(16)
    if r.u(1): r.u(1)
    if r.u(1):
        r.u(3); r.u(1)
        if r.u(1): r.u(8); r.u(8); r.u(8)
    if r.u(1): r.ue(); r.ue()
    if r.u(1):
        nu=r.u(32); ts=r.u(32); ff=r.u(1); print(' VUI timing',nu,ts,'fixed',ff,'-> fps',ts/(2*nu))
    for name in ('nal_hrd','vcl_hrd'):
        if r.u(1):
            cnt=r.ue()+1; bsc=r.u(4); csc=r.u(4)
            for i in range(cnt):
                br=(r.ue()+1)<<(6+bsc); cpb=(r.ue()+1)<<(4+csc); cbr=r.u(1)
                print(f' {name} SchedSel{i}: bit_rate {br} b/s, cpb_size {cpb} bits ({cpb/br:.2f} s), cbr {cbr}')
            r.u(5); r.u(5); r.u(5); r.u(5)
r=BR(rbsp(pps[0][1:])); ppsid=r.ue(); r.ue(); ent=r.u(1); bfo=r.u(1); nsg=r.ue()+1
nr0=r.ue()+1; nr1=r.ue()+1; wp=r.u(1); wb=r.u(2); qp=r.se()+26; qs=r.se()+26; cqo=r.se(); dfc=r.u(1); cip=r.u(1); rpc=r.u(1)
t8=None
try:
    t8=r.u(1); pm=r.u(1); print(' PPS transform_8x8',t8,'pic_scaling_matrix',pm)
except Exception: pass
print('PPS entropy',('CABAC' if ent else 'CAVLC'),'pic_init_qp',qp,'chroma_qp_offset',cqo,'deblock_ctrl',dfc,'transform_8x8',t8)
# sample table
mo,me=at['/moov/trak/mdia/mdhd'][0]; v=data[mo]; ts,dur=(struct.unpack('>II',data[mo+12:mo+20]) if v==0 else (None,None))
so,se_=at['/moov/trak/mdia/minf/stbl/stsz'][0]; n=struct.unpack('>I',data[so+8:so+12])[0]; sizes=list(struct.unpack(f'>{n}I',data[so+12:so+12+4*n]))
to,te=at['/moov/trak/mdia/minf/stbl/stts'][0]; ent_=struct.unpack('>I',data[to+4:to+8])[0]; cnt,delta=struct.unpack('>II',data[to+8:to+16])
ss,sse=at['/moov/trak/mdia/minf/stbl/stss'][0]; nk=struct.unpack('>I',data[ss+4:ss+8])[0]; keys=struct.unpack(f'>{nk}I',data[ss+8:ss+8+4*nk])
fps=ts/delta; secs=n/fps; tot=sum(sizes)
print(f'frames {n} @ {fps:.3f} fps = {secs:.2f} s; video bytes {tot} -> avg {tot*8/secs/1e6:.2f} Mb/s')
gops=[keys[i+1]-keys[i] for i in range(len(keys)-1)]; print('keyframes',nk,'GOP lengths',sorted(set(gops)))
I=[sizes[k-1] for k in keys]; P=[s for i,s in enumerate(sizes,1) if i not in set(keys)]
print(f'I-frame bytes: mean {statistics.mean(I):.0f} max {max(I)}; P-frame mean {statistics.mean(P):.0f} max {max(P)}')
win=[sum(sizes[i:i+int(round(fps))])*8/1e6 for i in range(0,n-int(fps),int(round(fps)))]
print('per-second Mb/s: min %.1f max %.1f'%(min(win),max(win)))
pickle.dump(dict(sizes=sizes,keys=keys,fps=fps,l2fn=l2fn,poc=poc,l2poc=l2poc,fmo=fmo,ppsid=ppsid,qp=qp,ent=ent,bfo=bfo,wp=wp,wb=wb,nr0=nr0,cip=cip,rpc=rpc,dfc=dfc,nal=(avcc[4]&3)+1),open(sys.argv[3],'wb'))

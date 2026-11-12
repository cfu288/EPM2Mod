import sys,re,collections,bisect
img=open(sys.argv[3],'rb').read(); B=0x7E421020
fns=[]
for i,row in enumerate(open(sys.argv[1])):
    f=row.rstrip('\n').split('\t')
    if i==0: hdr=f; continue
    d=dict(zip(hdr,f)); fns.append((int(d['addr'],16),d['data_page'],d['suspect']))
fns.sort(); starts=[f[0] for f in fns]
c=collections.Counter(); ex=collections.defaultdict(list); nf=collections.defaultdict(set)
for line in open(sys.argv[2]):
    m=re.match(r'^([0-9a-f]{8}):\t(\S+)\s*(.*)$',line)
    if not m: continue
    a=int(m.group(1),16); o=a-B
    if o<0 or o+2>len(img): continue
    b0=img[o]
    if b0 not in (0xf5,0xf6,0xf9,0xfb,0xfd): continue
    if b0 in (0xf9,0xfb,0xfd) and not m.group(2).startswith(('udf','mcst','getc','putc','getx','putx')): continue
    i=bisect.bisect_right(starts,a)-1
    if i<0 or fns[i][1]=='1' or fns[i][2]=='1': continue
    b1=img[o+1]; nn=b1>>4
    if b0 in (0xf5,0xf6):
        key=('udf%02d'%(nn+20) if b0==0xf5 else 'udf%02d'%nn)+' Dm,Dn'+(' (m==n)' if ((b1>>2)&3)==(b1&3) else '')
    else:
        tt=(b1>>2)&3; base=['udf%02d','udfu%02d','udf%02d','udfu%02d'][tt]%(nn+(20 if tt>=2 else 0)); key=base+' imm'+{0xf9:'8',0xfb:'16',0xfd:'32'}[b0]
        if base in('udf14',): key+=' val=%s'%img[o+2:o+{0xf9:3,0xfb:4,0xfd:6}[b0]].hex()
    c[key]+=1; nf[key].add(fns[i][0])
    if len(ex[key])<2: ex[key].append(hex(a)+' '+m.group(2)+' '+m.group(3))
for k,v in sorted(c.items(), key=lambda x:-x[1]): print(v,len(nf[k]),k,ex[k])

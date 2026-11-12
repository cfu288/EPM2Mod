import sys,re,collections,bisect
img=open(sys.argv[3],'rb').read(); B=0x7E421020
fns=[]
for i,row in enumerate(open(sys.argv[1])):
    f=row.rstrip('\n').split('\t')
    if i==0: hdr=f; continue
    d=dict(zip(hdr,f)); fns.append((int(d['addr'],16),int(d['size']),d['data_page'],d['suspect']))
fns.sort(); starts=[f[0] for f in fns]
CODE=[(0x7E421020,0x7E4C90CA),(0x7E4FE000,0x7E731585),(0x7E8808C0,0x7E880F44),(0x7E8F5800,0x7EBABF8E),(0x7ECCB800,0x7EECE319),(0x7F05C000,0x7F0691C6),(0x7F080000,0x7F0AB000)]
c=collections.Counter(); ex=collections.defaultdict(list); real=0
for line in open(sys.argv[2]):
    m=re.match(r'^([0-9a-f]{8}):\t(\S+)\s*(.*)$',line)
    if not m: continue
    a=int(m.group(1),16)
    if not any(lo<=a<hi for lo,hi in CODE): continue
    i=bisect.bisect_right(starts,a)-1
    if i<0 or fns[i][2]=='1' or fns[i][3]=='1': continue
    real+=1
    o=a-B
    if o<0 or o>=len(img): continue
    b0=img[o]; op=m.group(2); args=m.group(3)
    if b0 in (0xf5,0xf6,0xf9,0xfb,0xfd): continue  # UDF space
    k=None
    if b0==0xf7: k='F7 '+op
    elif re.search(r'\b(r\d+|xr\d+|usp|ssp|msp|epsw)\b',args) or op in ('unknown','syscall','rtm','trap','.word'): k=op
    elif b0==0xfe: k='FE '+op
    if k:
        c[k]+=1
        if len(ex[k])<3: ex[k].append(hex(a)+' '+args)
print('instructions in real functions:',real)
for k,v in c.most_common(30): print(v,k,ex[k])

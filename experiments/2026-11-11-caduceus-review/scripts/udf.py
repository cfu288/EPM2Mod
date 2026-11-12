import sys,re,collections
R=[(0x7E421020,0x7E4C90CA),(0x7E4FE000,0x7E731585),(0x7E8808C0,0x7E880F44),(0x7E8F5800,0x7EBABF8E),(0x7ECCB800,0x7EECE319)]
EXCL=[(0x7E7F0F78,0x7E7FABB5)]
c=collections.Counter(); ex=collections.defaultdict(list)
for line in open(sys.argv[1]):
    m=re.match(r'^([0-9a-f]{8}):\t(udfu?\d+)\t(\S+)',line)
    if not m: continue
    a=int(m.group(1),16)
    if not any(lo<=a<hi for lo,hi in R): continue
    op=m.group(2); args=m.group(3)
    reg = ',' in args and args.split(',')[0].startswith('d')
    key=op+(' Dm,Dn' if reg else ' imm')
    c[key]+=1
    if len(ex[key])<3: ex[key].append(hex(a)+' '+args)
for k,v in sorted(c.items(), key=lambda x:-x[1]): print(v,k,ex[k])

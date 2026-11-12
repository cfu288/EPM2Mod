import sys,re,collections,csv
# load function table: start,size,data_page
fns=[]
for i,row in enumerate(open(sys.argv[1])):
    f=row.rstrip('\n').split('\t')
    if i==0: hdr=f; continue
    d=dict(zip(hdr,f)); fns.append((int(d['addr'],16),int(d['size']),d.get('data_page','0')))
fns.sort()
import bisect
starts=[f[0] for f in fns]
def fn_of(a):
    i=bisect.bisect_right(starts,a)-1
    return fns[i] if i>=0 else None
R=[(0x7E421020,0x7E4C90CA),(0x7E4FE000,0x7E731585),(0x7E8808C0,0x7E880F44),(0x7E8F5800,0x7EBABF8E),(0x7ECCB800,0x7EECE319),(0x7F05C000,0x7F06A000),(0x7F080000,0x7F0EB800)]
pat=re.compile(r'\b(r\d+|xr\d+|usp|ssp|msp|epsw|mcrh|mcrl|mcvf)\b|\b(unknown|syscall|rtm|trap)\b|^(dcpf|bsch|sat16|sat24|swhw|swap|mac|mul\w*|min|max|cmp_|add_|sub_|mov_|and_|or_|xor_|asr_|lsr_|asl_)')
c=collections.Counter(); ex=collections.defaultdict(list); fnset=collections.defaultdict(set)
for line in open(sys.argv[2]):
    m=re.match(r'^([0-9a-f]{8}):\t(\S+)\s*(.*)$',line)
    if not m: continue
    a=int(m.group(1),16)
    if not any(lo<=a<hi for lo,hi in R): continue
    op,args=m.group(2),m.group(3)
    if op.startswith('udf') or op in ('getchx','getclx','putx','putcx','getx'): continue
    if re.search(r'\b(r\d+|xr\d+|usp|ssp|msp|epsw)\b',args) or op in('unknown','syscall','rtm','trap','swhw','swap','sat16','sat24','bsch','dcpf','mcst9','mcst48','mcst16') or '_' in op or op.startswith('mac') or op in ('min','max','mul','mulu') and ',r' in args:
        f=fn_of(a)
        if f and f[2]=='1': continue
        c[op]+=1; fnset[op].add(f[0] if f else 0)
        if len(ex[op])<3: ex[op].append(hex(a)+' '+args)
for k,v in c.most_common(40): print(v,len(fnset[k]),k,ex[k])

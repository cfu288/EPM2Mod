# specscan.py OURSPEC [LO-HI]: every spec under patches/ and patches/history: block-0 op windows; overlaps with
# OURSPEC's op windows and with the runtime range LO-HI; also other block-0 op types
import json, glob, sys, os
B=0x7E421020; ROOT='/path/to/EPM2Mod/'
def wins(spec):
    out=[]
    for op in spec['ops']:
        if op.get('block')!=0: continue
        if op['type']!='bytes': out.append((None,None,op['type'])); continue
        o=int(op['offset'],0) if isinstance(op['offset'],str) else op['offset']
        e,n=bytes.fromhex(op['expect']),bytes.fromhex(op['new'])
        ch=[i for i in range(len(e)) if e[i]!=n[i]]
        out.append((o,o+len(e),(o+ch[0],o+ch[-1]+1) if ch else None))
    return out
ours=json.load(open(sys.argv[1])); ow=wins(ours)
rng=tuple(int(x,16)-B for x in sys.argv[2].split('-')) if len(sys.argv)>2 else None
FILMS=['remap7b-code','seven-fixes-1','seven-movie-1','seven-structure-extra','seven-films-5','xp-adaptive-hue-off','seven-labels']
tot=0
for f in sorted(glob.glob(ROOT+'patches/*.json')+glob.glob(ROOT+'patches/history/*.json')):
    s=json.load(open(f)); w=wins(s); name=os.path.relpath(f,ROOT+'patches')
    other=[x[2] for x in w if x[0] is None]
    hits=[]; inr=[]
    for a,b,ch in w:
        if a is None: continue
        if rng and a<rng[1] and rng[0]<b: inr.append('%#x-%#x'%(B+a,B+b))
        for c,d,_ in ow:
            if a<d and c<b: hits.append('%#x-%#x vs ours %#x-%#x'%(B+a,B+b,B+c,B+d))
    tot+=len(hits)+len(inr)
    b0=[x for x in w if x[0] is not None]
    print('%-40s block0 ops %3d %s| in range: %s | overlaps: %s%s'%(name+(' [FILM]' if s['name'] in FILMS else ''),len(b0),
          ('span %#x-%#x '%(B+min(x[0] for x in b0),B+max(x[1] for x in b0))) if b0 else '', inr or '-', hits or '-', ' | non-bytes block0: %s'%other if other else ''))
print('total conflicts',tot)

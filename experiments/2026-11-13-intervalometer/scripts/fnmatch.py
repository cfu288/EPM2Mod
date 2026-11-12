# Build normalised per-function text for both bodies and anchor-match them.
import re, pickle, sys, collections, hashlib
S='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/'
SRC={'pm2':'/path/to/epm2-tools/build/map/functions.txt','pl6':S+'map-112_1400/functions.txt'}
def normline(s):
    s=re.sub(r'<[^>]*>','',s)
    s=re.sub(r'\b(0x)?7[ef][0-9a-f]{6}\b','A',s)
    s=re.sub(r'(0x)?6[0-9a-f]{7}','R',s)
    s=re.sub(r'\b\d{9,10}\b','K',s)
    s=re.sub(r'\b-\d{9,10}\b','K',s)
    return s.strip()
def load(body):
    fns={}; cur=None; lines=[]
    for l in open(SRC[body]):
        m=re.match(r'^([0-9a-f]{8}) <f_',l)
        if m:
            if cur: fns[cur]=lines
            cur=int(m.group(1),16); lines=[]; continue
        m=re.match(r'^\s*[0-9a-f]+:\t(.*)$',l.rstrip('\n'))
        if m and cur: lines.append(normline(m.group(1).replace('\t',' ')))
    if cur: fns[cur]=lines
    return fns
if __name__=='__main__':
    A=load('pm2'); B=load('pl6')
    h=lambda L: hashlib.md5('\n'.join(L).encode()).hexdigest()
    HA=collections.defaultdict(list); HB=collections.defaultdict(list)
    for a,L in A.items(): HA[h(L)].append(a)
    for b,L in B.items(): HB[h(L)].append(b)
    pairs={}
    for k,v in HA.items():
        if len(v)==1 and len(HB.get(k,[]))==1 and len(A[v[0]])>=6: pairs[v[0]]=HB[k][0]
    print('pm2 fns',len(A),'pl6 fns',len(B),'unique anchors',len(pairs))
    pickle.dump((A,B,pairs),open(S+'ivl/fnmatch.pkl','wb'))

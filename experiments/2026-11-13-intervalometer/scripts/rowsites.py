# rowsites.py: exact E-PM2 instruction addresses of the row constants the E-PL6 renumbered (k -> k+1, k>=11),
# for the menu functions found by rowshift.py; prints addr, bytes, E-PL6 addr, bytes
import sys, difflib, re, subprocess
sys.path.insert(0,'/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/scripts')
from dis import dis, norm
S='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/'
def size(addr, pl6=False):
    cmd=['python3','/path/to/EPM2Mod/tools/fwmap.py']
    if pl6: cmd+=['--fw',S+'dl-bodies/112_1400/OLY_E_112_1400_0000_0000.BIN','--base','0x7E421020','--out',S+'map-112_1400']
    out=subprocess.run(cmd+['fn',hex(addr)],capture_output=True,text=True,cwd='/path/to/EPM2Mod').stdout
    f=out.split('\n')[0].split(); return int(f[f.index('data_page:')+1],16), int(f[f.index('data_page:')+3])
PAIRS=[l.split(':')[0].split(' -> ') for l in open(sys.argv[1]) if ' -> ' in l]
seen=set()
for a,b in PAIRS:
    if (a,b) in seen: continue
    seen.add((a,b)); a=int(a,16); b=int(b,16)
    fa,na=size(a); fb,nb=size(b,True)
    A=dis('pm2',fa,na); Bl=dis('pl6',fb,nb)
    sm=difflib.SequenceMatcher(None,[norm(l) for l in A],[norm(l) for l in Bl],autojunk=False)
    for t,i1,i2,j1,j2 in sm.get_opcodes():
        if t!='replace' or i2-i1!=j2-j1: continue
        for x,y in zip(A[i1:i2],Bl[j1:j2]):
            px,py=x.split('\t'),y.split('\t')
            mx=re.match(r'(mov|cmp)\s+(\d+),d0',' '.join(px[2:])); my=re.match(r'(mov|cmp)\s+(\d+),d0',' '.join(py[2:]))
            if mx and my and int(my.group(2))==int(mx.group(2))+1 and int(mx.group(2))>=11:
                print('%s %-12s %-14s | %s %-12s %s'%(px[0].strip(),px[1].strip(),' '.join(px[2:]),py[0].strip(),py[1].strip(),' '.join(py[2:])))

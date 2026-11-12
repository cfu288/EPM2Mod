# dis.py {pm2|pl6} ADDR LEN [--norm]  -> objdump text of block0 at runtime ADDR
import sys, subprocess, re, os
I='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/blocks/'
F={'pm2':I+'OLY_E_101_1600_0000_0000.BIN.block0.bin','pl6':I+'OLY_E_112_1400_0000_0000.BIN.block0.bin'}
B=0x7E421020
def dis(body,a,n):
    od=os.path.expanduser('~/opt/mn10300/bin/mn10300-elf-objdump')
    r=subprocess.run([od,'-D','-b','binary','-m','am33-2','-EL','--adjust-vma=%#x'%B,'--start-address=%#x'%a,'--stop-address=%#x'%(a+n),F[body]],capture_output=True,text=True).stdout
    return [l for l in r.splitlines() if re.match(r'^\s*[0-9a-f]+:\t',l)]
def norm(l):
    p=l.split('\t'); s=p[-1] if len(p)>=3 else p[-1]
    s=re.sub(r'0x7[ef][0-9a-f]{6}','A',s); s=re.sub(r'<[^>]*>','',s)
    return s.strip()
if __name__=='__main__':
    body,a,n=sys.argv[1],int(sys.argv[2],0),int(sys.argv[3],0)
    for l in dis(body,a,n): print(norm(l) if '--norm' in sys.argv else l)

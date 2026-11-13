# fmtindex.py BLOCK0: row index passed to the value-list formatters 0x7EE01DDA / 0x7EE01E8C at each of their 26
# E-PM2 call sites (the last `mov imm,d0` before the call; the switch tail 0x7EDEC437 gets the switch's constants)
import sys, struct, subprocess, os, re
B=0x7E421020; D=open(sys.argv[1],'rb').read()
od=os.path.expanduser('~/opt/mn10300/bin/mn10300-elf-objdump')
def dis(a,n):
    r=subprocess.run([od,'-D','-b','binary','-m','am33-2','-EL','--adjust-vma=%#x'%B,'--start-address=%#x'%a,'--stop-address=%#x'%(a+n),sys.argv[1]],capture_output=True,text=True).stdout
    return [l.split('\t') for l in r.splitlines() if re.match(r'^\s*[0-9a-f]+:\t',l)]
SITES=[0x7EDE3736,0x7EDE3769,0x7EDE4FEC,0x7EDE5009,0x7EDE5489,0x7EDEA21F,0x7EDEA252,0x7EDFD3D6,0x7EDFD3EF,           # mov before 0x7EE01DDA
       0x7EDE50A3,0x7EDE50BD,0x7EDE5222,0x7EDE523C,0x7EDE5290,0x7EDE52AA,0x7EDFD483,0x7EDFD499,0x7EDFD6CB,0x7EDFD6E1,0x7EDFD731,0x7EDFD747,  # 0x7EE01E8C
       0x7EDEC462,0x7EDEC491,0x7EDEC4C5]                                                                              # switch, direct
mx=0
for a in SITES:
    l=dis(a,9); ins=' '.join(l[0][2:]); call=' '.join(l[1][2:])
    v=int(re.match(r'mov\s+(\d+),d0',ins).group(1)); mx=max(mx,v)
    assert 'call' in call and ('0x7ee01dda' in call or '0x7ee01e8c' in call), call
    print('%08x  %-12s -> %s'%(a,ins,call.split(',')[0]))
# switch tail 0x7EDEC432/0x7EDEC437: every `mov imm,d0; jmp 0x7edec432` (and the fall-through before it), incl. the cave
tail=[]
for lo,n in ((0x7EDEC2C0,0x180),(0x7ECB0D78,51),(0x7F033DE0,51)):
    L=dis(lo,n)
    for i in range(1,len(L)):
        t=' '.join(L[i][2:])
        if ('jmp' in t and '0x7edec432' in t):
            m=re.match(r'mov\s+(\d+),d0',' '.join(L[i-1][2:]))
            if m: tail.append(int(m.group(1)))
m=re.match(r'mov\s+(\d+),d0',' '.join(dis(0x7EDEC430,2)[0][2:])); tail.append(int(m.group(1)))
print('switch tail 0x7EDEC437 receives rows',sorted(set(tail)))
mx=max([mx]+tail); print('largest row index',mx,'-> slot address %#x'%(0x602BE874+4*mx),'(table 0x602BE874..0x602BE907, 37 slots; next variable 0x602BE908):','IN BOUNDS' if mx<=36 else 'OUT OF BOUNDS')

# modedef.py: parse the MODE-class ROM default list in both bodies; print tags 0xDDF1..0xDEB1
import struct
B=0x7E421020
I='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/blocks/'
F={'pm2':I+'OLY_E_101_1600_0000_0000.BIN.block0.bin','pl6':I+'OLY_E_112_1400_0000_0000.BIN.block0.bin'}
SIZE={1:1,2:2,3:2,4:4,5:4,0:1}
def parse(D,start):
    o=start-B; out={}
    while True:
        tag,cnt=struct.unpack_from('<2H',D,o)
        if tag==0: break
        sz={1:1,2:2,4:4}.get(tag&0xF, None)
        # type by low nibble: 1=u8, 2=s16?, 4=u32 (per 07-settings.tsv: de11 u8, de0a s16, de34 u32)
        sz={0x1:1,0x2:2,0x3:2,0x4:4,0xa:2}.get(tag&0xF,1)
        n=cnt*sz; data=D[o+4:o+4+n]
        out[tag]=(B+o,cnt,sz,data)
        o+=4+n; o=(o+3)&~3
    return out,B+o
if __name__=='__main__':
    D=open(F['pm2'],'rb').read(); P=open(F['pl6'],'rb').read()
    head=D[0x7E4B40D0-B:0x7E4B40D0-B+16]
    i=P.find(head); print('pl6 list start',hex(B+i))
    a,ea=parse(D,0x7E4B40D0); b,eb=parse(P,B+i)
    print('pm2 tags',len(a),'end',hex(ea),' pl6 tags',len(b),'end',hex(eb))
    for t in sorted(set(a)|set(b)):
        if 0xDDF0<=t<=0xDEC0:
            x=a.get(t); y=b.get(t)
            f=lambda r: '-' if r is None else '%s cnt%d %s'%(hex(r[0]),r[1],r[3].hex())
            print(hex(t),'| pm2',f(x),'| pl6',f(y))
    diff=[hex(t) for t in sorted(set(a)|set(b)) if (a.get(t) or (0,0,0,None))[1:]!=(b.get(t) or (0,0,0,None))[1:]]
    print('tags whose default differs or exists in one body only:',len(diff),diff[:80])

# dump all language tables of a block-1 file: returns {lang: [strings]}
import sys, struct, re, pickle
def load(path, base=0x43C40000):
    d=open(path,'rb').read(); out={}
    for m in re.finditer(re.escape('OlympusLanguage_'.encode('utf-16le'))+rb'((?:[a-z]\x00){2,8})', d):
        name=m.group(1).decode('utf-16le'); fp=m.start()
        # find header: {A,B} with pointer array ending before footer
        best=None
        for i in range(1,200):
            a,sz=struct.unpack_from('<2I',d,16*i); o=a-base
            if 0<o<=fp<o+sz+0x200: best=(o,sz); break
        if not best: continue
        o,sz=best; done=False
        for hdr in range(max(0,o-0x200),o+0x200,2):
            A,B=struct.unpack_from('<2I',d,hdr)
            if A>>24!=B>>24 or A>>28<8 or not 0<B-A<0x20000 or (B-A)%4: continue
            for pad in range(0,0x80,2):
                RT=B-(fp-pad-hdr); arr=hdr+A-RT
                if hdr<arr<fp and struct.unpack_from('<I',d,arr)[0]==RT+8:
                    n=(B-A)//4; ptrs=struct.unpack_from('<%dI'%n,d,arr); S=[]
                    for p in ptrs:
                        s=hdr+p-RT; e=s
                        while e<len(d)-1 and d[e:e+2]!=b'\0\0': e+=2
                        S.append((s,d[s:e].decode('utf-16le','replace')))
                    out[name]=S; done=True; break
            if done: break
    return out
if __name__=='__main__':
    r=load(sys.argv[1]); pickle.dump(r,open(sys.argv[2],'wb'))
    print(len(r), sorted((k,len(v)) for k,v in r.items()))

import struct,sys
f=open(sys.argv[1],'rb'); data=f.read()
CONT={b'moov',b'trak',b'mdia',b'minf',b'stbl',b'udta',b'edts',b'dinf'}
out={}
def walk(off,end,depth,path):
    while off+8<=end:
        sz,typ=struct.unpack('>I4s',data[off:off+8]); hdr=8
        if sz==1: sz=struct.unpack('>Q',data[off+8:off+16])[0]; hdr=16
        if sz==0: sz=end-off
        p=path+'/'+typ.decode('latin1')
        print('  '*depth+f'{typ.decode("latin1")} {sz}')
        out.setdefault(p,[]).append((off+hdr,off+sz))
        if typ in CONT: walk(off+hdr,off+sz,depth+1,p)
        elif typ==b'stsd':
            # version/flags(4) count(4) then sample entries
            e=off+hdr+8; esz,etyp=struct.unpack('>I4s',data[e:e+8]); print('  '*(depth+1)+f'entry {etyp} {esz}')
            out.setdefault(p+'/'+etyp.decode('latin1'),[]).append((e,e+esz))
        off+=sz
walk(0,len(data),0,'')
import pickle; pickle.dump(out,open(sys.argv[2],'wb'))

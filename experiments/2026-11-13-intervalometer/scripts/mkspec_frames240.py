# mkspec_frames240.py: build experiments/2026-11-13-intervalometer/patches/interval-frames-240.json
# Frame count (info 483): 1-99 by 1 (stock labels), then 100-240 by 5 (composed number labels) = 128 choices,
# the most the list editor can index (its key handler sign-extends the byte index: 0x7EE017BB / 0x7EE017FC).
import json, struct
B=0x7E421020
SC='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/'
D=bytearray(open('/path/to/EPM2Mod/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin','rb').read())
FV=open(SC+'v2-films.block0.bin','rb').read()                      # films + interval-timelapse-v2, built in scratch
OUT='/path/to/EPM2Mod/experiments/2026-11-13-intervalometer/patches/interval-frames-240.json'
VALUES=list(range(1,100))+list(range(100,241,5))
assert len(VALUES)==128 and max(VALUES)==240
assert 128 not in VALUES  # 128 is the mcon error value for u8 lists (cmp 128 at 0x7E6FCAD6); review-4 S2
rd=lambda a,n,X=None: bytes((X or D)[a-B:a-B+n])
REC, LIST = 0x7E84C5FC, 0x7E849F56
assert struct.unpack_from('<HHIIHHBBH',D,REC-B)==(483,128,LIST,0,99,1,1,1,0) and rd(LIST,99)==bytes(range(1,100))
DESC, ITEMS = 0x7F00C6EC, 0x7F00ABD0
assert struct.unpack_from('<HHIII',D,DESC-B)==(483,99,0,0,ITEMS)
ROWS = 0x7EFF5160
label={}
for k in range(99):
    info,v,kind,lab=struct.unpack_from('<4I',D,ROWS-B+32*k); assert (info,v,kind)==(483,k+1,2); label[v]=lab
tmpl=rd(ITEMS,28)
for k in range(99):
    assert rd(ITEMS+28*k,28)==tmpl[:2]+struct.pack('<5H',label[99-k],0,0,0,0)+tmpl[12:16]+struct.pack('<I',99-k)+tmpl[20:]
# new homes: mcon list in the reset-stub-loaded 0xFF padding 0x7E4C90CA-0x7E4C97FF (the record is boot-part data, so
# its list must not wait for a Usr1 segment); editor items in the unreferenced `sdk` name list 0x7EBF1090-0x7EBF3BAC
NEW_LIST, NEW_ITEMS = 0x7E4C9100, 0x7EBF1100
for X in (D,FV):
    assert rd(0x7E4C90CA,0x7E4C9800-0x7E4C90CA,X)==b'\xff'*(0x7E4C9800-0x7E4C90CA)
    assert rd(0x7EBF1090,0x7EBF3BAD-0x7EBF1090,X)==rd(0x7EBF1090,0x7EBF3BAD-0x7EBF1090,D)
edits=[]
edits.append((NEW_LIST,bytes(VALUES),'mcon value list of info 483: 128 x u8 (1-99, 100-240 by 5)'))
edits.append((REC+4,struct.pack('<IIH',NEW_LIST,0,128),'mcon record 0x7E84C5FC: list pointer and total 99 -> 128'))
items=b''
for v in reversed(VALUES):
    kind,args=(2,(label[v],0,0,0,0)) if v<=99 else (4,(v,0,0,0,0))
    items+=bytes([tmpl[0],kind])+struct.pack('<5H',*args)+tmpl[12:16]+struct.pack('<I',v)+tmpl[20:]
assert NEW_ITEMS+len(items)<=0x7EBF3BAD
edits.append((NEW_ITEMS,items,'frame editor (list 638) items: 128 x 28 B, values 240..1'))
edits.append((DESC+2,struct.pack('<H',128),'list 638 descriptor 0x7F00C6EC: count 99 -> 128'))
edits.append((DESC+12,struct.pack('<I',NEW_ITEMS),'list 638 descriptor: items pointer'))
edits.append((ROWS+32*98+8,struct.pack('<2I',4,99),'sub-item row of value 99 -> kind 4 (number + unit 0): shows 99 and every value without a row as a number'))
ops=[]
for a,new,why in sorted(edits):
    o=a-B; old=bytes(D[o:o+len(new)]); assert old!=new
    assert bytes(FV[o-4:o+len(new)+4])==bytes(D[o-4:o+len(new)+4]), ('films+v2 differs here',hex(a))
    ops.append({"type":"bytes","block":0,"offset":'0x%X'%(o-4),"expect":bytes(D[o-4:o+len(new)+4]).hex(),"new":(bytes(D[o-4:o])+new+bytes(D[o+len(new):o+len(new)+4])).hex(),"_why":why})
    print(hex(a),len(new),why)
spec={"name":"interval-frames-240","description":open(SC+'frames_desc.txt').read().strip(),
 "base":"firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN","base_sha256":"34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300","ops":ops}
json.dump(spec,open(OUT,'w'),indent=1); open(OUT,'a').write('\n')

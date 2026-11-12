# mkspec_insert.py: build experiments/2026-11-13-intervalometer/patches/interval-timelapse-insert.json
# (E-PL6 1.4 menu wiring reproduced on the E-PM2 v1.6: a 37-row top table, the .data tab layout and value
# lists renumbered, page 3's child list with {628, 482}, the value switch and every row constant renumbered)
import json, struct
B=0x7E421020; K=0x1E6304C0                       # .data ROM image = RAM + K
SC='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/'
D=bytearray(open('/path/to/epm2-tools/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin','rb').read())
P=open(SC+'blocks/OLY_E_112_1400_0000_0000.BIN.block0.bin','rb').read()
OUT='/path/to/epm2-tools/experiments/2026-11-13-intervalometer/patches/interval-timelapse-insert.json'
rd=lambda X,a,n: bytes(X[a-B:a-B+n])
u32=lambda X,a: struct.unpack_from('<I',X,a-B)[0]
edits=[]                                           # (addr, old, new, why)
def edit(a,new,why):
    old=rd(D,a,len(new)); assert old!=new, (hex(a),why); edits.append((a,old,bytes(new),why))

# free space: 0xFF padding inside the Usr1 copy 0x7ECCB800-0x7F034000 (after the segment-3 ctor table + its FF word)
FREE_LO, FREE_HI = 0x7F033C00, 0x7F034000
assert rd(D,0x7F033B7C,FREE_HI-0x7F033B7C)==b'\xff'*(FREE_HI-0x7F033B7C)
NEW_TOP, NEW_P3, CAVE = 0x7F033C00, 0x7F033D80, 0x7F033DE0

# (a) top table: E-PM2 rows 1-10, E-PL6 row 11 (Time Lapse Settings), E-PM2 rows 11-36, 10-byte zero terminator
OLD_TOP, PL6_TOP = 0x7EFFE13C, 0x7EFFF864
rows=[rd(D,OLD_TOP+10*i,10) for i in range(36)]
assert rd(D,OLD_TOP+360,10)==b'\0'*10
tl=rd(P,PL6_TOP+100,10); assert tl==struct.pack('<5H',0,1357,1358,0x102,1)
top=b''.join(rows[:10])+tl+b''.join(rows[10:])+b'\0'*10
assert top==rd(P,PL6_TOP,380), 'new table must equal the E-PL6 table'
edit(NEW_TOP,top,'37-row top-menu table (= E-PL6 0x7EFFF864 byte for byte)')
for site in (0x7EDEC0A5,0x7EDEC0FA,0x7EDEC121,0x7EDEC7A6,0x7EDECF42,0x7EDED085):
    assert u32(D,site)==OLD_TOP
    edit(site,struct.pack('<I',NEW_TOP),'top-table imm32 %#x'%site)

# (b) .data tab layout (ROM 0x7E8EE88E -> RAM 0x602BE3CE): 6 x 20-byte lists + 6 counts = E-PL6 values
TAB=0x602BE3CE+K; PTAB=0x602BE3F6+K
assert rd(D,TAB,126)!=rd(P,PTAB,126)
new=bytearray(rd(D,TAB,126))
for t in range(6):
    for s in range(12):
        v=new[20*t+s]
        if v!=0xFF and v>=11: new[20*t+s]=v+1
new[120+1]=6                                      # tab 1 count 5 -> 6
# tab 1 list must read 07 08 09 0a 0b 0c: rows 7..10 keep, old 11 (RC) became 12, new 11 = Time Lapse
new[20:32]=bytes([7,8,9,10,11,12])+b'\xff'*6
assert bytes(new)==rd(P,PTAB,126), 'tab layout must equal the E-PL6'
edit(TAB+20,bytes(new[20:126]),'.data tab layout tabs 1-5 and counts (= E-PL6)')

# (c) page 3 child list: E-PL6 order {13,14,15,16,628/482,18} + 12-byte terminator, relocated; record ptr updated
P3REC=0x7EFFA49C; assert u32(D,P3REC)==3 and u32(D,P3REC+20)==0x7EFF8C38
old=[struct.unpack_from('<3I',D,0x7EFF8C38-B+12*i) for i in range(5)]
lst=old[:4]+[(628,482,0)]+old[4:]
p3=b''.join(struct.pack('<3I',*e) for e in lst)+b'\0'*12
assert p3==rd(P,u32(P,0x7EFFBBC4+20),84), 'page-3 list must equal the E-PL6'
edit(NEW_P3,p3,'page-3 child list with {628,482} (= E-PL6)')
edit(P3REC+20,struct.pack('<I',NEW_P3),'page-3 record child pointer')

# (d1) .data per-row value-list pointers (RAM 0x602BE874, 40 entries): insert Off/On at row 11, shift 11..38 up
PT=0x602BE874+K; ptrs=list(struct.unpack_from('<40I',D,PT-B)); assert ptrs[39]==0
onoff=ptrs[11]
newp=ptrs[:11]+[onoff]+ptrs[11:39]
edit(PT,struct.pack('<40I',*newp),'.data row value-list pointers renumbered (+ Off/On at row 11)')

# (d2) value switch 0x7EDEC2C0: rows 13,31,32,33,34 -> +1; the old row-11 case (RC, 180) moves into a cave
#      that handles row 11 (482, new) and row 12 (180), as E-PL6 0x7EDED1CB-0x7EDED1F2 does
for a,op,k in ((0x7EDEC35E,0xA0,13),(0x7EDEC36D,0x80,13),(0x7EDEC372,0xA0,31),(0x7EDEC420,0xA0,32),(0x7EDEC430,0x80,32),
               (0x7EDEC445,0xA0,33),(0x7EDEC462,0x80,33),(0x7EDEC491,0x80,33),(0x7EDEC4B1,0xA0,34),(0x7EDEC4C5,0x80,34)):
    assert rd(D,a,2)==bytes([op,k]); edit(a,bytes([op,k+1]),'switch row %d -> %d'%(k,k+1))
GET, NEXT, TAIL, HOOK = 0x7EE01D38, 0x7EDEC34A, 0x7EDEC432, 0x7EDEC335
assert rd(D,HOOK,21)==bytes.fromhex('a00bc9132cb4003c50ddfa590100a00c800bcc')+rd(D,HOOK+19,2)
rel=lambda frm,to: struct.pack('<i',to-frm)
c=CAVE
cave=(bytes.fromhex('a00b')+bytes.fromhex('c80b')+bytes.fromhex('a00c')+bytes.fromhex('c81a')+b'\xdc'+rel(c+8,NEXT)
      +bytes.fromhex('2ce201')+b'\x3c\x50'+b'\xdd'+rel(c+18,GET)+b'\xa0\x0c'+bytes.fromhex('800b')+b'\xdc'+rel(c+27,TAIL)
      +bytes.fromhex('2cb400')+b'\x3c\x50'+b'\xdd'+rel(c+37,GET)+b'\xa0\x0c'+bytes.fromhex('800c')+b'\xdc'+rel(c+46,TAIL))
assert len(cave)==51
edit(CAVE,cave,'value-switch cave: row 11 -> getSetting(482), row 12 -> getSetting(180)')
edit(HOOK,b'\xdc'+rel(HOOK,CAVE),'value switch: old row-11 case -> jmp cave')

# (d3) the 20 `mov 33,d0` row arguments of the formatter / reverse formatter in the monitor-adjust panels -> 34
for a in (0x7EDE3736,0x7EDE3769,0x7EDE4FEC,0x7EDE5009,0x7EDE50A3,0x7EDE50BD,0x7EDE5222,0x7EDE523C,0x7EDE5290,0x7EDE52AA,
          0x7EDEA21F,0x7EDEA252,0x7EDFD3D6,0x7EDFD3EF,0x7EDFD483,0x7EDFD499,0x7EDFD6CB,0x7EDFD6E1,0x7EDFD731,0x7EDFD747):
    assert rd(D,a,2)==b'\x80\x21'; edit(a,b'\x80\x22','panel formatter row 33 -> 34 at %#x'%a)

# (e) defaults, as in the replacement spec
edit(0x7E4C3EB8,b'\x0a','default 0xDE21 (483 Frame) 0 -> 10')
edit(0x7E4C3EC8,struct.pack('<I',5),'default 0xDE44 (485 Interval, s) 0 -> 5')

# ops with 4 context bytes each side; edits closer than 8 bytes are merged into one op (no overlapping windows)
edits.sort()
groups=[]
for a,old,new,why in edits:
    if groups and a-(groups[-1][0]+len(groups[-1][2]))<8:
        g=groups[-1]; gap=rd(D,g[0]+len(g[2]),a-(g[0]+len(g[2])))
        groups[-1]=(g[0],g[1]+gap+old,g[2]+gap+new,g[3]+'; '+why)
    else: groups.append((a,old,new,why))
ops=[]
for a,old,new,why in groups:
    o=a-B
    pre,post=bytes(D[o-4:o]),bytes(D[o+len(old):o+len(old)+4])
    assert bytes(D[o:o+len(old)])==old
    ops.append({"type":"bytes","block":0,"offset":'0x%X'%(o-4),"expect":(pre+old+post).hex(),"new":(pre+new+post).hex(),"_why":why})
spec={"name":"interval-timelapse-insert",
 "description":open(SC+'insert_desc.txt').read().strip(),
 "base":"firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
 "base_sha256":"34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300","ops":ops}
json.dump(spec,open(OUT,'w'),indent=1); open(OUT,'a').write('\n')
print(len(ops),'ops', sum(len(e[2]) for e in edits),'new bytes')
for e in groups: print(hex(e[0]),len(e[2]),e[3])

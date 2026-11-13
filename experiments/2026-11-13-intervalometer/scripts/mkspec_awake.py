# mkspec_awake.py (= mkspec_insert.py + awake_part.py): build experiments/2026-11-13-intervalometer/patches/interval-timelapse-insert.json
# (E-PL6 1.4 menu wiring reproduced on the E-PM2 v1.6: a 37-row top table, the .data tab layout and value
# lists renumbered, page 3's child list with {628, 482}, the value switch and every row constant renumbered)
import json, struct
B=0x7E421020; K=0x1E6304C0                       # .data ROM image = RAM + K
SC='/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/ivl/'
D=bytearray(open('/path/to/EPM2Mod/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin','rb').read())
P=open(SC+'blocks/OLY_E_112_1400_0000_0000.BIN.block0.bin','rb').read()
OUT='/path/to/EPM2Mod/experiments/2026-11-13-intervalometer/patches/interval-timelapse-insert-awake.json'
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

# ---- keep-awake port (E-PL6 0x7E989552 and 0x7E998C41), trampolines in the padding after the insert spec's cave ----
# tiny MN103 assembler: items are bytes, ('call', target, regs, imm), ('jmp', target), ('b', cond, label), ('L', label)
COND = {'eq': 0xC8, 'ne': 0xC9, 'ls': 0xC7, 'ra': 0xCA}        # beq bne bls bra (rel8, from the insn start)
INV = {'eq': 'ne', 'ne': 'eq', 'ls': None}
def assemble(org, items):
    long_ = set()                                              # branches that need the long form
    while True:
        pc, labels, sizes = org, {}, []
        for k, it in enumerate(items):
            if isinstance(it, tuple) and it[0] == 'L':
                labels[it[1]] = pc; sz = 0
            elif isinstance(it, (bytes, bytearray)): sz = len(it)
            elif it[0] in ('call',): sz = 7
            elif it[0] == 'jmp': sz = 5
            elif it[0] == 'b': sz = (2 if it[1] == 'ra' else 2 + 3) if k in long_ else 2
            sizes.append(sz); pc += sz
        out, pc, again = bytearray(), org, False
        for k, it in enumerate(items):
            if isinstance(it, tuple) and it[0] == 'L': continue
            if isinstance(it, (bytes, bytearray)): out += it
            elif it[0] == 'call': out += b'\xdd' + struct.pack('<i', it[1] - pc) + bytes([it[2], it[3]])
            elif it[0] == 'jmp': out += b'\xdc' + struct.pack('<i', it[1] - pc)
            elif it[0] == 'b':
                tgt = labels[it[2]]
                if k in long_:
                    if it[1] == 'ra': out += b'\xcc' + struct.pack('<h', tgt - pc)          # jmp rel16 (3 bytes) - fits sz 2? no
                    else:
                        inv = INV[it[1]]; assert inv
                        out += bytes([COND[inv], 5]) + b'\xcc' + struct.pack('<h', tgt - (pc + 2))
                else:
                    r = tgt - pc
                    if not -128 <= r <= 127: long_.add(k); again = True; break
                    out += bytes([COND[it[1]], r & 0xFF])
            pc += sizes[k]
        if not again:
            assert len(out) == sum(sizes), 'size mismatch'
            return bytes(out), labels
# long 'bra' would need 3 bytes; keep the assert above honest by never emitting it
_orig_assemble = assemble

GETTER, ISST, RESTORE, HOLD, PRINT = 0x7E6FCC91, 0x7E997C67, 0x7E997DC9, 0x7E997E94, 0x7E9670E9
T1, T2 = 0x7F033E20, 0x7F033E40
assert rd(D, 0x7F033E13, FREE_HI - 0x7F033E13) == b'\xff' * (FREE_HI - 0x7F033E13)

# T1: startIntervalShooting fresh-start branch. Hook 0x7E98855F (after `bne 0x7E9885CA`, (32,sp) == 0), as E-PL6
#     0x7E989552: call the timer hold, then the 6 displaced bytes, then back to 0x7E988565
H1 = 0x7E98855F
disp = rd(D, H1, 6); assert disp == bytes.fromhex('0042143c2014')        # clr d0; mov d0,(20,sp); mov sp,a0; add 20,a0
t1, _ = assemble(T1, [('call', HOLD, 0x00, 4), disp, ('jmp', H1 + 6)])
edit(T1, t1, 'keep-awake T1: call 0x7E997E94 (timer hold), displaced 6 bytes, jmp 0x7E988565')
edit(H1, b'\xdc' + struct.pack('<i', T1 - H1) + disp[5:6], 'startIntervalShooting: jmp T1 at 0x7E98855F (1 byte left, unreachable)')

# T2: the interval sleep-timer selector 0x7E997BD9 rewritten as E-PL6 0x7E998C41 (same branches, same call order),
#     with E-PM2 callees, the E-PM2 assert strings and line 721; entry becomes `jmp T2`; returns are `ret [],16`
H2 = 0x7E997BD9
assert rd(D, H2, 5) == bytes.fromhex('a000c864a0')
RET = b'\xdf\x00\x10'
M = lambda v: b'\x2c' + struct.pack('<H', v)                        # mov imm16,d0
CMP = lambda v: bytes([0xA0, v])                                    # cmp imm8,d0
t2, lab = assemble(T2, [
    CMP(0), ('b', 'eq', 'C7D'), CMP(1), ('b', 'eq', 'C53'), CMP(2), ('b', 'eq', 'C8B'), CMP(3), ('b', 'eq', 'CB7'),
    ('jmp', 0), ('L', 'C53'),                                       # placeholder for `bra CC4`, fixed below
    M(482), ('call', GETTER, 0, 4), CMP(0), ('b', 'eq', 'C7D'),
    M(489), ('call', GETTER, 0, 4), CMP(0), ('b', 'ne', 'CBD'),
    M(487), ('call', GETTER, 0, 4), CMP(0), ('b', 'ne', 'CBD'),
    ('L', 'C7D'), ('call', ISST, 0x80, 16), b'\x00', ('call', RESTORE, 0xA0, 16), RET,
    ('L', 'C8B'), M(482), ('call', GETTER, 0, 4), CMP(1), ('b', 'ne', 'CE2'),
    M(487), ('call', GETTER, 0, 4), CMP(0), ('b', 'ls', 'CAF'),
    b'\xfc\xcc' + struct.pack('<I', 60001), ('b', 'ra', 'CB0'),
    ('L', 'CAF'), b'\x00', ('L', 'CB0'), ('call', ISST, 0x80, 16), ('b', 'ra', 'CE2'),
    ('L', 'CB7'), b'\x00', ('call', ISST, 0x80, 16),
    ('L', 'CBD'), ('call', HOLD, 0, 4), ('b', 'ra', 'CE2'),
    ('L', 'CC4'), b'\xfc\xcc' + struct.pack('<I', 2126448461), b'\x42\x04', b'\xfc\xcc' + struct.pack('<I', 2126448477),
    b'\x42\x08', M(721), b'\x42\x0c', b'\x80\x04', ('call', PRINT, 0xA0, 12),
    ('L', 'CE2'), RET])
# second pass with the real `jmp CC4` (5 bytes, same size as the placeholder)
items2 = None
t2, lab = assemble(T2, [
    CMP(0), ('b', 'eq', 'C7D'), CMP(1), ('b', 'eq', 'C53'), CMP(2), ('b', 'eq', 'C8B'), CMP(3), ('b', 'eq', 'CB7'),
    ('jmp', lab['CC4']), ('L', 'C53'),
    M(482), ('call', GETTER, 0, 4), CMP(0), ('b', 'eq', 'C7D'),
    M(489), ('call', GETTER, 0, 4), CMP(0), ('b', 'ne', 'CBD'),
    M(487), ('call', GETTER, 0, 4), CMP(0), ('b', 'ne', 'CBD'),
    ('L', 'C7D'), ('call', ISST, 0x80, 16), b'\x00', ('call', RESTORE, 0xA0, 16), RET,
    ('L', 'C8B'), M(482), ('call', GETTER, 0, 4), CMP(1), ('b', 'ne', 'CE2'),
    M(487), ('call', GETTER, 0, 4), CMP(0), ('b', 'ls', 'CAF'),
    b'\xfc\xcc' + struct.pack('<I', 60001), ('b', 'ra', 'CB0'),
    ('L', 'CAF'), b'\x00', ('L', 'CB0'), ('call', ISST, 0x80, 16), ('b', 'ra', 'CE2'),
    ('L', 'CB7'), b'\x00', ('call', ISST, 0x80, 16),
    ('L', 'CBD'), ('call', HOLD, 0, 4), ('b', 'ra', 'CE2'),
    ('L', 'CC4'), b'\xfc\xcc' + struct.pack('<I', 2126448461), b'\x42\x04', b'\xfc\xcc' + struct.pack('<I', 2126448477),
    b'\x42\x08', M(721), b'\x42\x0c', b'\x80\x04', ('call', PRINT, 0xA0, 12),
    ('L', 'CE2'), RET])
assert T2 + len(t2) <= FREE_HI
edit(T2, t2, 'keep-awake T2: sleep-timer selector as E-PL6 0x7E998C41 (%d bytes)' % len(t2))
edit(H2, b'\xdc' + struct.pack('<i', T2 - H2), 'sleep-timer selector 0x7E997BD9: jmp T2 (old body unreachable)')
print('T1', hex(T1), len(t1), 'T2', hex(T2), len(t2), {k: hex(v) for k, v in lab.items()})

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
spec={"name":"interval-timelapse-insert-awake",
 "description":open(SC+'insert_desc.txt').read().strip()+' '+open(SC+'awake_desc.txt').read().strip(),
 "base":"firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
 "base_sha256":"34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300","ops":ops}
json.dump(spec,open(OUT,'w'),indent=1); open(OUT,'a').write('\n')
print(len(ops),'ops', sum(len(e[2]) for e in edits),'new bytes')
for e in groups: print(hex(e[0]),len(e[2]),e[3])

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

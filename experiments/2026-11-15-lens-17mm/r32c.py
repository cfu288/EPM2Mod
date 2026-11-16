#!/usr/bin/env python3
"""Partial R32C decoder for lens research. Unknown instructions stop a walk.

Encoding source: Renesas REJ09B0267-0100, chapter 4. This is not an emulator.
Addresses printed by the CLI are payload offsets, including out-of-image targets.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

REGS = (
    ('R0L', 'R0H', 'R2L', 'R2H', 'R1L', 'R1H', 'R3L', 'R3H'),
    ('R0', 'R2', 'R1', 'R3', 'R4', 'R6', 'R5', 'R7'),
    ('R2R0', 'R3R1', 'R6R4', 'R7R5', 'A0', 'A1', 'A2', 'A3'),
)
COND = ('LTU', 'LEU', 'NE', 'PZ', 'NO', 'GT', 'GE', '?',
        'GEU', 'GTU', 'EQ', 'N', 'O', 'LE', 'LT', '?')


class Unknown(ValueError):
    pass


@dataclass
class Insn:
    pc: int
    size: int
    mnemonic: str
    args: str = ''
    kind: str = 'normal'
    target: int | None = None


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


class Decoder:
    def __init__(self, data):
        self.data = data

    def decode(self, start):
        p = start
        data = self.data

        def take(n, sign=False):
            nonlocal p
            if p + n > len(data):
                raise Unknown('end of image')
            v = int.from_bytes(data[p:p+n], 'little', signed=sign)
            p += n
            return v

        def out(mn, args='', kind='normal', target=None):
            return Insn(start, p-start, mn, args, kind, target)

        def gen(code, width):
            if width == 3:
                raise Unknown('reserved size')
            if code < 8:
                return REGS[width][code]
            if code in (8, 12):
                n = (1, 1, 2)[width] if code == 8 else (1, 2, 4)[width]
                return f'#{take(n, code == 8):#x}'
            if code == 9:
                return f'{take(1, True):+#x}[FB]'
            if code == 10:
                return f'{take(2, True):+#x}[FB]'
            if code in (11, 13):
                return f'[{take(3, True) & 0xffffffff:#x}]' if code == 11 else f'[{take(2):#x}]'
            if code in (14, 15):
                return f'{take(2 if code == 14 else 3, True):+#x}[SB]'
            bank, disp = divmod(code - 16, 4)
            return f'{take(disp, True):+#x}[A{bank}]' if disp else f'[A{bank}]'

        def short(code, width, alt=False):
            if code == 0:
                return REGS[width][1 if alt else 0]
            if code == 1:
                return f'[{take(2):#x}]'
            return f'{take(1, True):+#x}[{"FB" if code == 2 else "SB"}]'

        def pair(op, mnemonic, extension=False):
            w = op & 3
            if w == 3:
                raise Unknown('reserved generic size')
            b = take(1)
            dest = ((op >> 2) & 3) * 8 + (b >> 5)
            src = b & 31
            if dest in (8, 12):
                raise Unknown('immediate destination: needs a special opcode decoder')
            dw, sw = ((1, 0), (2, 0), (2, 1))[w] if extension else (w, w)
            # #IMMEX changes both operation size and immediate size.
            if src == 8 and not extension:
                dw = (1, 2, 2)[w]
            d = gen(dest, dw)
            s = gen(src, sw)
            suffix = ('BW', 'BL', 'WL')[w] if extension else ('B', 'W', 'L')[dw]
            return out(f'{mnemonic}.{suffix}', f'{s}, {d}')

        op = take(1)
        if op in (0x9F, 0xDF, 0xCF, 0xEF):
            return out({0x9F: 'NOP', 0xDF: 'RTS', 0xCF: 'REIT', 0xEF: 'EXITD'}[op],
                       kind='normal' if op == 0x9F else 'return')
        if op in (0x1B, 0xDB):
            return out('ENTER', f'#{take(1 if op == 0x1B else 2):#x}')
        if op in (0x4B, 0x5B, 0x6B, 0x7B):
            return out('PUSHM' if op < 0x60 else 'POPM',
                       f'mask={take(1):#x}' + (', SB' if op & 0x10 else ''))
        if op in (0x0B, 0x2B, 0x3B, 0x8B, 0x9B, 0xCB):
            size = {0x0B: 1, 0x2B: 1, 0x3B: 1, 0x8B: 2, 0x9B: 2, 0xCB: 4}[op]
            return out('PUSH', f'#{take(size, op in (0x0B,0x3B,0x9B)):#x}')
        if op == 0xFF:
            return out('WAIT')
        if op == 0xBF:
            return out('BRK', kind='return')
        if op in (0x73, 0xAB, 0xEB, 0xBB, 0xFB):
            n = {0x73: 1, 0xAB: 2, 0xEB: 3, 0xBB: 2, 0xFB: 3}[op]
            target = start + 1 + take(n, True)
            kind = 'call' if op in (0xBB, 0xFB) else 'jump'
            return out('JSR' if kind == 'call' else 'JMP', f'{target:#x}', kind, target)
        if op & 0x0F == 3 and COND[op >> 4] != '?':
            target = start + 1 + take(1, True)
            return out('J' + COND[op >> 4], f'{target:#x}', 'branch', target)
        if op & 0x8F == 0x87:
            q = (op >> 4) & 7
            # Table 4.13: q=0..7 encodes displacement 1..8.
            target = start + 1 + q + 1
            return out('JMP.S', f'{target:#x}', 'jump', target)
        if op & 0x8F == 7:
            return out('BTST', f'{(op >> 4) & 7}, [{take(2):#x}]')
        if op in (0x44, 0x4C, 0x48) and not (op == 0x4C and data[p] & 31 == 8):
            b = take(1)
            return out({0x44: 'BCLR', 0x4C: 'BSET', 0x48: 'BTST'}[op],
                       f'{b >> 5}, {gen(b & 31, 0)}')
        if op in (0x4C, 0x4D) and data[p] & 31 == 8:
            bit = take(1) >> 5
            return out('FSET' if op == 0x4D else 'FCLR', f'flag{bit}')
        if op in (0x48, 0x49) and data[p] & 31 == 8:
            creg = ('SVP', 'INTB', 'SVF', 'FLG', 'SP', 'ISP', 'FB', 'SB')[take(1) >> 5]
            return out('PUSHC' if op == 0x48 else 'POPC', creg)
        if op == 0x49:
            b = take(1)
            return out('MOVA', f'{gen(b & 31,2)}, {REGS[2][b >> 5]}')
        if op == 0x4D:
            b = take(1)
            if b & 0xE0:
                raise Unknown('reserved PUSHA bits')
            return out('PUSHA', gen(b & 31,2))
        if op == 0x45:
            b = take(1)
            return out('EXTZ.WL', f'{gen(b & 31,1)}, {REGS[2][b >> 5]}')
        if op == 0x3F:
            op2 = take(1)
            if op2 >> 4 in (11, 3):
                return pair(op2, 'EXTS' if op2 >> 4 == 11 else 'EXTZ', True)
            if op2 >> 4 in (4,5,10):
                return pair(op2, {4:'MUL',5:'MULU',10:'XOR'}[op2 >> 4])
            if op2 >> 4 in (0,1):
                return pair(op2, 'DIV' if op2 >> 4 == 0 else 'DIVU')
            if op2 & 0xFC == 0x70 and op2 & 3 != 3:
                b = take(1)
                return out('EMULU.' + ('B','W','L')[op2 & 3],
                           f'{gen(b & 31,op2 & 3)}, {REGS[op2 & 3][b >> 5]}')
            raise Unknown(f'extended opcode 3f {op2:02x}')
        if op == 0x7F:
            a, b = take(1), take(1)
            if a in (0xA5,0xA6) and b & 0xE0 in (0,0xA0):
                indirect = 'JSRI' if b & 0xE0 else 'JMPI'
                return out(indirect + ('.W' if a == 0xA5 else '.L'),
                           gen(b & 31,1 if a == 0xA5 else 2),
                           'indirect_call' if indirect == 'JSRI' else 'indirect_jump')
            raise Unknown(f'extended opcode 7f {a:02x} {b:02x}')
        if op & 0xFC in (0xA4,0x94,0x84,0xC4,0xD4) and op & 3 != 3:
            b = take(1)
            if b & 0xE0 == 0 and b & 31 != 8:
                mn = {0xA4:'INDEX1',0x94:'INDEX2',0x84:'INDEXB',0xC4:'SHL',0xD4:'POP'}[op & 0xFC]
                d = gen(b & 31,op & 3)
                return out(mn + '.' + ('B','W','L')[op & 3],
                           f'#{take(1,True)}, {d}' if mn == 'SHL' else d)
            if b & 0xE0 == 0x80 and op & 0xFC in (0xA4,0x94):
                return out(('NOT' if op & 0xFC == 0xA4 else 'NEG') + '.' + ('B','W','L')[op & 3],
                           gen(b & 31,op & 3))
            if b & 0xE0 == 0x80 and op & 0xFC == 0xD4:
                if b == 0x88:
                    return out('SSTR.' + ('B','W','L')[op & 3])
                return out('PUSH.' + ('B','W','L')[op & 3], gen(b & 31,op & 3))
            if b & 0xE0 == 0x80 and op & 0xFC == 0xC4:
                d = gen(b & 31,op & 3)
                return out('ROT.' + ('B','W','L')[op & 3], f'#{take(1,True)}, {d}')
            p -= 1
        if op >> 4 in (8, 9, 10, 11, 12, 13) and op & 3 != 3:
            return pair(op, {8: 'ADD', 9: 'SUB', 10: 'CMP', 11: 'MOV',
                             12: 'AND', 13: 'OR'}[op >> 4])
        if op & 0xF8 in (0xE0, 0xE8, 0xF0, 0xF8) and op & 3 != 3:
            b = take(1)
            q = ((op >> 2) & 1) * 8 + (b >> 5)
            d = gen(b & 31, op & 3)
            return out(('CMP' if op & 0xF8 == 0xE0 else
                        'SHL' if op & 0xF8 == 0xE8 else
                        'ADD' if op & 0xF8 == 0xF0 else 'MOV') + '.' + ('B', 'W', 'L')[op & 3],
                       f'#{signed(q, 4)}, {d}')
        if op >> 4 in (0, 1, 2, 3, 5, 6, 7) and op & 3 != 3:
            group, w, s = op >> 4, op & 3, (op >> 2) & 3
            if group == 0:
                return out('MOV.' + ('B', 'W', 'L')[w], f'{REGS[w][0]}, {short(s,w)}')
            if group == 1:
                return out('MOV.' + ('B', 'W', 'L')[w], f'#0, {short(s,w)}')
            if group in (2, 3, 6, 7):
                dst = short(s,w)
                return out({2: 'MOV', 3: 'CMP', 6: 'AND', 7: 'ADD'}[group] + '.' + ('B', 'W', 'L')[w],
                           f'#{take((1,2,4)[w]):#x}, {dst}')
            return out('MOV.' + ('B', 'W', 'L')[w], f'{short(s,w,True)}, {REGS[w][0]}')
        if op & 0xF3 == 0x42:
            return out('MOV.L', f'{short((op >> 2) & 3,2)}, A0')
        raise Unknown(f'opcode {op:02x}')


def walk(decoder, start, limit=100):
    p = start
    for _ in range(limit):
        try:
            ins = decoder.decode(p)
        except Unknown as exc:
            print(f'{p:06x}  {decoder.data[p:p+8].hex(" "):26} UNKNOWN: {exc}')
            return
        print(f'{p:06x}  {decoder.data[p:p+ins.size].hex(" "):26} {ins.mnemonic:10} {ins.args}')
        p += ins.size
        if ins.kind in ('return', 'jump'):
            return


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image', type=Path)
    ap.add_argument('offset', type=lambda s: int(s, 0))
    ap.add_argument('--count', type=int, default=100)
    args = ap.parse_args()
    walk(Decoder(args.image.read_bytes()[32:-32]), args.offset, args.count)

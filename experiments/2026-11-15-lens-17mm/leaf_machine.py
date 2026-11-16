#!/usr/bin/env python3
"""Execute the decoded lens driver-programming leaves, without motor hardware.

Calls to ADC sampling, serial output, and the short delay have explicit hooks.
This proves computed register words, not physical motor timing or sound.
"""

import re

from r32c import Decoder, Unknown


class LeafMachine:
    def __init__(self, payload):
        self.payload = payload
        self.decoder = Decoder(payload)
        self.regs = {f'R{i}': 0 for i in range(8)}
        self.regs.update({f'A{i}': 0 for i in range(4)})
        self.regs.update(SP=0x20000, FB=0)
        self.mem = {}
        self.z = self.s = self.o = False
        self.c = True
        self.words = []
        self.trace = []
        self.adc = 250

    def reg(self, name, value=None):
        byte = re.fullmatch(r'R([0-3])([LH])', name)
        pair = re.fullmatch(r'R([0-7])R([0-7])', name)
        if byte:
            key = 'R' + byte[1]
            shift = 0 if byte[2] == 'L' else 8
            if value is None:
                return (self.regs[key] >> shift) & 255
            self.regs[key] = (self.regs[key] & ~(255 << shift)) | ((value & 255) << shift)
        elif pair:
            high, low = 'R' + pair[1], 'R' + pair[2]
            if value is None:
                return (self.regs[high] << 16) | self.regs[low]
            self.regs[high], self.regs[low] = (value >> 16) & 65535, value & 65535
        elif name in self.regs:
            bits = 16 if name.startswith('R') else 32
            if value is None:
                return self.regs[name]
            self.regs[name] = value & ((1 << bits) - 1)
        else:
            raise Unknown(f'unknown register {name}')

    def address(self, operand):
        m = re.fullmatch(r'([^\[]*)\[([^\]]+)\]', operand)
        if not m:
            raise Unknown(f'not a memory operand: {operand}')
        base = self.reg(m[2]) if m[2] in self.regs else int(m[2],0)
        return (base + (int(m[1],0) if m[1] else 0)) & 0xffffffff

    def memory(self, address, width, value=None):
        if value is None:
            result = 0
            for n in range(width):
                a = (address+n) & 0xffffffff
                if 0xfffc0000 <= a < 0xffff0000:
                    b = self.payload[a-0xfffc0000]
                else:
                    b = self.mem.get(a,0)
                result |= b << (8*n)
            return result
        for n in range(width):
            self.mem[(address+n) & 0xffffffff] = (value >> (8*n)) & 255

    def operand(self, operand, width, value=None):
        if operand.startswith('#'):
            if value is not None:
                raise Unknown('write to immediate')
            return int(operand[1:],0) & ((1 << (8*width))-1)
        if '[' in operand:
            return self.memory(self.address(operand),width,value)
        return self.reg(operand,value)

    def flags(self, value, bits):
        self.z = value & ((1 << bits)-1) == 0
        self.s = bool(value & (1 << (bits-1)))

    def condition(self, cond):
        return {'LTU':not self.c, 'LEU':not self.c or self.z,
                'NE':not self.z, 'PZ':not self.s, 'NO':not self.o,
                'GT':not self.z and self.s == self.o, 'GE':self.s == self.o,
                'GEU':self.c, 'GTU':self.c and not self.z, 'EQ':self.z,
                'N':self.s, 'O':self.o, 'LE':self.z or self.s != self.o,
                'LT':self.s != self.o}[cond]

    def run(self, entry, limit=20000):
        pc = entry
        self.memory(self.reg('SP'),4,0xfffffffe)
        for _ in range(limit):
            if pc == 0xfffffffe:
                return self.words
            ins = self.decoder.decode(pc)
            self.trace.append(pc)
            nxt = pc+ins.size
            op, _, suffix = ins.mnemonic.partition('.')
            args = ins.args.split(', ') if ins.args else []
            width = {'B':1,'W':2,'L':4}.get(suffix,0)
            bits = 8*width
            mask = (1 << bits)-1 if bits else 0
            if op == 'ENTER':
                sp = self.reg('SP')-4
                self.memory(sp,4,self.reg('FB'))
                self.reg('FB',sp)
                self.reg('SP',sp-int(args[0][1:],0))
            elif op in ('EXITD','RTS'):
                if op == 'EXITD':
                    self.reg('SP',self.reg('FB'))
                    self.reg('FB',self.memory(self.reg('SP'),4))
                    self.reg('SP',self.reg('SP')+4)
                nxt = self.memory(self.reg('SP'),4)
                self.reg('SP',self.reg('SP')+4)
            elif op == 'JSR':
                target = ins.target
                if target == 0x6ca4:
                    self.words.append(self.reg('R0'))
                    self.reg('R2R0',1)
                elif target == 0x650:
                    self.reg('R0',self.adc)
                elif target == 0x6e88:
                    pass
                else:
                    sp = self.reg('SP')-4
                    self.reg('SP',sp)
                    self.memory(sp,4,nxt)
                    nxt = target
            elif op == 'JMP':
                nxt = ins.target
            elif op.startswith('J'):
                if self.condition(op[1:]):
                    nxt = ins.target
            elif op in ('MOV','EXTZ','EXTS'):
                if op != 'MOV':
                    sw, dw = {'BW':(1,2),'BL':(1,4),'WL':(2,4)}[suffix]
                    v = self.operand(args[0],sw)
                    if op == 'EXTS' and v & (1 << (sw*8-1)):
                        v -= 1 << (sw*8)
                    self.operand(args[1],dw,v)
                    self.flags(v,8*dw)
                else:
                    v = self.operand(args[0],width)
                    self.operand(args[1],width,v)
                    self.flags(v,bits)
            elif op in ('CMP','ADD','SUB','AND','OR','MULU','DIVU','SHL'):
                v, old = self.operand(args[0],width), self.operand(args[1],width)
                if op in ('CMP','SUB'):
                    result = old-v
                    self.c = old >= v
                    self.o = bool(((old ^ v) & (old ^ result)) & (1 << (bits-1)))
                elif op == 'ADD':
                    result = old+v
                    self.c = result > mask
                    self.o = bool((~(old ^ v) & (old ^ result)) & (1 << (bits-1)))
                elif op == 'AND':
                    result = old & v
                elif op == 'OR':
                    result = old | v
                elif op == 'MULU':
                    result = old*v
                elif op == 'DIVU':
                    if v == 0:
                        raise Unknown('division by zero')
                    result = old//v
                else:
                    shift = int(args[0][1:],0)
                    result = old << shift if shift >= 0 else old >> -shift
                self.flags(result,bits)
                if op != 'CMP':
                    self.operand(args[1],width,result & mask)
            elif op == 'EMULU' and suffix == 'B' and args[1] == 'R0L':
                self.reg('R0',self.operand(args[0],1)*self.reg('R0L'))
                self.flags(self.reg('R0'),16)
            elif op in ('BCLR','BSET','BTST'):
                bit = int(args[0],0)
                v = self.operand(args[1],1)
                if op == 'BTST':
                    self.z = not bool(v & (1 << bit))
                else:
                    v = v & ~(1 << bit) if op == 'BCLR' else v | (1 << bit)
                    self.operand(args[1],1,v)
            else:
                raise Unknown(f'unsupported execution at {pc:#x}: {ins}')
            pc = nxt
        raise Unknown(f'instruction limit at {pc:#x}')

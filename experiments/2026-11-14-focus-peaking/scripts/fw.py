"""Small helpers to read two firmware blocks (research code).

Set EP5_BLOCK0 to the decoded E-P5 1.8 main block (see NOTES.md "Material").
"""
import os, struct

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class FW:
    def __init__(self, path, base):
        self.d = open(path, "rb").read()
        self.B = base

    def b(self, a, n):
        return self.d[a - self.B:a - self.B + n]

    def u32(self, a):
        return struct.unpack_from("<I", self.d, a - self.B)[0]

    def u16(self, a):
        return struct.unpack_from("<H", self.d, a - self.B)[0]

    def u8(self, a):
        return self.d[a - self.B]

    def s(self, a):
        o = a - self.B
        if not 0 <= o < len(self.d):
            return None
        e = self.d.index(b"\0", o)
        t = self.d[o:e]
        return t.decode("latin-1") if t and all(32 <= c < 127 or c in (9, 10, 13) for c in t) else None

    def has(self, a):
        return self.B <= a < self.B + len(self.d)


def epm2():
    return FW(os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"), 0x7E421020)


def ep5():
    return FW(os.environ.get("EP5_BLOCK0", "/tmp/scratch/peaking/ep5/EP5.BIN"), 0x7E101020)

import sys, struct
sys.path.insert(0, "/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/qp/live")
from omemu import Emu, DATA, SP0
IMG = "/path/to/epm2-tools/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"
DRV, OUT = DATA + 0x20000, DATA + 0x21000
def st_stub(size, ovf, rq):
    def f(emu, r):
        st = bytearray(36)
        struct.pack_into("<I", st, 4, size); st[12] = rq; struct.pack_into("<I", st, 28, ovf)
        emu.write(r["a0"], st); return {"d0": 301}
    return f
with Emu() as emu:
    emu.load(IMG)
    for qp in (20, 33):
        for size in (0, 20_000, 75_000, 200_000, 600_000, 2_000_000):
            for ovf in (0,):
                drv = bytearray(0x400); drv[218] = qp
                emu.write(DRV, drv); emu.write(OUT, b"\0" * 32)
                r = emu.call(0x7EEA3E0A, {"a0": DRV, "a1": OUT, "d0": 1}, frame=(0, 0),
                             stubs={0x7EEC6B01: st_stub(size, ovf, 20), 0x7EEC684A: lambda e, r: {"d0": 300}})
                print("qp", qp, "size", size, "ovf", ovf, "-> drv+218", emu.read(DRV + 218, 1)[0], "out+8", emu.read(OUT + 8, 1)[0], "ret", r["regs"]["d0"])
    drv = bytearray(0x400); drv[218] = 40; emu.write(DRV, drv)
    r = emu.call(0x7EEA3E0A, {"a0": DRV, "a1": OUT, "d0": 1}, frame=(0, 0), stubs={0x7EEC6B01: st_stub(75000, 1, 20), 0x7EEC684A: lambda e, r: {"d0": 300}})
    print("overflow qp40 ->", emu.read(DRV + 218, 1)[0])

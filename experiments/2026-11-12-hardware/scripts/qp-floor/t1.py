import sys, struct
sys.path.insert(0, "/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/qp/live")
from omemu import Emu, DATA, SP0
STOCK_BLOCK0 = "/path/to/epm2-tools/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"
CTX, OBJ, VT, FAKE = DATA + 0x10000, DATA + 0x11000, DATA + 0x11100, DATA + 0x11200
def setup(emu, ctxfields):
    ctx = bytearray(0x1000)
    for off, (fmt, v) in ctxfields.items():
        struct.pack_into(fmt, ctx, off, v)
    emu.write(CTX, ctx)
    emu.write(OBJ, struct.pack("<I", VT))
    emu.write(FAKE, b"\x00\xf0\xfc")        # clr d0; rets
    emu.write(VT, struct.pack("<32I", *([FAKE] * 32)))
with Emu() as emu:
    emu.load(STOCK_BLOCK0)
    f = {68: ("<I", OBJ), 28: ("<I", 20_000_000), 48: ("<I", 2997), 12: ("<I", 1920), 16: ("<I", 1080),
         108: ("<H", 1), 52: ("<I", 0), 634: ("<B", 1)}
    setup(emu, f)
    emu.write(DATA, b"\0" * 64)
    r = emu.call(0x7EEA57D4, {"a0": CTX, "a1": DATA})
    print(hex(r["regs"]["d0"]), r["insns"])
    sp = SP0 - 16 - 356
    st = emu.read(sp + 164, 192)
    print("struct+36/37", st[36], st[37], "+172/173", st[172], st[173], "+32", struct.unpack_from("<I", st, 32))

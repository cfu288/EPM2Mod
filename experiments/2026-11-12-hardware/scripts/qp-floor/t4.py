import sys, struct
sys.path.insert(0, "/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/qp/live")
from omemu import Emu, DATA, SP0
IMG = "/path/to/EPM2Mod/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"
CTX, OUT = DATA + 0x10000, DATA + 0x21000
with Emu() as emu:
    emu.load(IMG)
    for hist in ([0,0,0,0], [20,20,20,20], [16,17,16,18], [25,20,20,20], [26,28,30,32], [60,60,60,60], [12,0,0,0]):
        for frame in (0, 3):
            ctx = bytearray(0x1000); ctx[635:639] = bytes(hist); ctx[634] = 1; struct.pack_into("<I", ctx, 52, frame); struct.pack_into("<I", ctx, 96, 1)
            emu.write(CTX, ctx); out = bytearray(32); out[25] = 33; emu.write(OUT, out)
            r = emu.call(0x7EEA6B37, {"a0": CTX, "a1": OUT})
            o = emu.read(OUT, 32)
            print(hist, "f", frame, "qp", o[16], "o8", struct.unpack_from("<I", o, 8)[0], "o12", struct.unpack_from("<I", o, 12)[0], "o20", hex(struct.unpack_from("<I", o, 20)[0]), "d0", r["regs"]["d0"], "ins", r["insns"])

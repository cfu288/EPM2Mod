import sys, struct
sys.path.insert(0, "/tmp/scratch/04b1caa0-6975-4677-98e3-f42129671871/scratchpad/qp/live")
from omemu import Emu, DATA, SP0
IMGS = {"stock": "/path/to/epm2-tools/build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin",
        "A": "../floor16-a.block0.bin", "AB": "../floor16-ab.block0.bin"}
CTX, OBJ, VT, FAKE = DATA + 0x10000, DATA + 0x11000, DATA + 0x11100, DATA + 0x11200
def setup(emu, f):
    ctx = bytearray(0x1000)
    for off, (fmt, v) in f.items(): struct.pack_into(fmt, ctx, off, v)
    emu.write(CTX, ctx); emu.write(OBJ, struct.pack("<I", VT)); emu.write(FAKE, b"\x00\xf0\xfc")
    emu.write(VT, struct.pack("<32I", *([FAKE] * 32)))
base = {68: ("<I", OBJ), 28: ("<I", 20_000_000), 48: ("<I", 2997), 12: ("<I", 1920), 16: ("<I", 1080),
        108: ("<H", 1), 52: ("<I", 3), 634: ("<B", 1), 96: ("<I", 1)}
for k, path in IMGS.items():
    with Emu() as emu:
        emu.load(path)
        for entry, frame_sz, stoff in ((0x7EEA57D4, 356, 164), (0x7EEA5C4C, 436, 176)):
            setup(emu, {**base, 104: ("<I", 0 if entry == 0x7EEA57D4 else 1)})
            emu.write(DATA, b"\0" * 64)
            r = emu.call(entry, {"a0": CTX, "a1": DATA})
            sp = SP0 - 16 - frame_sz
            st = emu.read(sp + stoff, 260)
            if entry == 0x7EEA57D4: mx, mn, q = st[36], st[37], st[172]
            else: mx, mn, q = st[44], st[45], st[248]
            calls = sorted({hex(p) for p in r["pcs"] if p >= 0x7D000000 and p < 0x7E000000})
            print(k, hex(entry), "d0", hex(r["regs"]["d0"]), "max", mx, "min", mn, "qp", q, "ctx104", emu.u32(CTX+104), "insns", r["insns"], calls)

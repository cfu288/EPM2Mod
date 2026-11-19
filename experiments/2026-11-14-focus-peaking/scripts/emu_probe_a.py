"""Emulator check of probe A (single functions, emulator driver).

Test 1: colour-tone getter 0x7E6CBFD3 (d0 = flags, d1 = 0: read the live-view struct, a0 = mode-byte
        pointer) for picture modes 0..6 and 100..120, flags 0 and 1, on stock and on the patched block.
        Output: returned art code and the byte written through a0.
Test 2: the code piece 0x7E6C6148..0x7E6C6159 of the expose setter (a1 = pointer to the picture mode,
        (13,sp) = art code returned by test 1), run as a pc range. Output: (13,sp) and byte 0x605B091C.

Usage: emu_probe_a.py STOCK_BLOCK0 PATCHED_BLOCK0
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
from omemu import Emu, SP0  # noqa: E402

LV_STRUCT = 0x605B1CD0      # returned by 0x7E6ECFB6 for index 0
MODE_BYTE = 0x605B091C
BUF = 0x7D200000


def test1(emu, mode, flags):
    emu.write(LV_STRUCT, bytes([0, 0, 7, mode]) + b"\0" * 32)   # +2 = 7 (marker), +3 = picture mode, +32 = 0
    emu.write(MODE_BYTE, b"\xee")
    r = emu.call(0x7E6CBFD3, {"d0": flags, "d1": 0, "a0": MODE_BYTE},
                 stubs={0x7E6D144F: lambda e, rg: {}})
    return r["regs"]["d0"] & 0xFF, emu.read(MODE_BYTE, 1)[0]


def test2(emu, mode, art):
    emu.write(BUF, bytes([mode]))
    emu.write(MODE_BYTE, bytes([119 if art in (163, 164) and mode < 100 else mode]))
    sp = SP0 - 0x100
    emu.write(sp + 13, bytes([art]))
    emu.req("reset", regs={"pc": 0x7E6C6148, "sp": sp, "mdr": 0, "psw": 0, "a1": BUF})
    r = emu.req("cont", stops=[0x7E6C6159])
    rg = emu.regs_of(r)
    assert r["stop"] == "break" and rg["pc"] == 0x7E6C6159, (r["stop"], hex(rg["pc"]))
    return emu.read(sp + 13, 1)[0], emu.read(MODE_BYTE, 1)[0]


def main():
    res = {}
    for name, img in (("stock", sys.argv[1]), ("patched", sys.argv[2])):
        with Emu() as emu:
            emu.load(img)
            for flags in (0, 1):
                for mode in list(range(0, 7)) + list(range(100, 121)):
                    art, mb = test1(emu, mode, flags)
                    e13, gb = test2(emu, mode, art)
                    res[(name, flags, mode)] = (art, mb, e13, gb)
    print("flags mode | stock: ret modebyte -> expose modebyte | patched: ret modebyte -> expose modebyte")
    changed = []
    for flags in (0, 1):
        for mode in list(range(0, 7)) + list(range(100, 121)):
            s, p = res[("stock", flags, mode)], res[("patched", flags, mode)]
            mark = "" if s == p else "   <-- changed"
            if s != p:
                changed.append((flags, mode))
            print("%5d %4d | %3d %3d -> %3d %3d | %3d %3d -> %3d %3d%s" % ((flags, mode) + s + p + (mark,)))
    print("changed rows:", changed)
    ok = changed == [(0, 3), (1, 3)]
    kl = res[("stock", 0, 119)], res[("stock", 1, 119)]
    ok = ok and res[("patched", 0, 3)] == kl[0] and res[("patched", 1, 3)] == kl[1]
    print("RESULT:", "PASS: only mode 3 changes, and it gives the same four values as stock Key Line (mode 119)"
          if ok else "FAIL")
    sys.exit(0 if ok else 1)


main()

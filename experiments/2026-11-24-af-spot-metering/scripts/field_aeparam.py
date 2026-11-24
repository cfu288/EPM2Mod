#!/usr/bin/env python3
"""Run the exp module's AE-area init (0x7E697C05) in the scenario harness and print the 8 ae_param records.

    uv run python experiments/2026-11-24-af-spot-metering/scripts/field_aeparam.py

0x7E697C05 fills the 7-byte mode records at 0x605A704C (0x7E6996A4) and then calls 0x7E698615, which builds one
24-byte ae_param record per sensor mode (0x7E698658 HSHR ... 0x7E698922 STILL) through 0x7E698978. The pointer
table to the records is 0x602AC7A8 (.data). Layout (printer 0x7E69A777): +0 hs, +2 vs, +4 hdiv, +6 vdiv, +8 hw,
+10 vw, +12 obhs, +14 obhw, +16 yshift (u8), +20 target (u32).
"""
import os, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
from scenario import Scenario  # noqa: E402
import omemu  # noqa: E402

PTRS = 0x602AC7A8
NAMES = {0x605A7148: "HSHR (mode 0)", 0x605A7178: "HS / HS3D / mode 5 (index 0 = HS, 1 = HS3D)",
         0x605A71A8: "MSSC (mode 3)", 0x605A71C0: "LSSC (mode 4)", 0x605A71D8: "CLIP (mode 6, index 0..4)",
         0x605A7160: "STILL (mode 7)"}


def rec(sc, a):
    hs, vs, hdiv, vdiv, hw, vw, obhs, obhw = struct.unpack("<hhHHHHhH", sc.read(a, 16))
    ysh = sc.read(a + 16, 1)[0]
    tgt = struct.unpack("<I", sc.read(a + 20, 4))[0]
    return (f"hs {hs:5d} vs {vs:5d} hdiv {hdiv:3d} vdiv {vdiv:3d} hw {hw:4d} vw {vw:4d} obhs {obhs:5d} "
            f"obhw {obhw:4d} yshift {ysh} target 0x{tgt:X}  -> field {hdiv * hw} x {vdiv * vw} from ({hs}, {vs})")


def main():
    with Scenario(omemu.STOCK_BLOCK0) as sc:
        log = []
        if "--trace" in sys.argv:            # debug flag bit 0x4000 turns on the calc_* prints of 0x7E698978
            sc.stub(0x7E69F188, lambda sc, g: {"d0": 0x4000}, "exp debug flags")
            cstr = lambda a: sc.read(a, 64).split(b"\0")[0].decode("latin1")
            sc.stub(0x7E50652F, lambda sc, g: log.append(f"{cstr(g['a0'])}{g['d0'] & 0xFFFFFFFF}") or {}, "print val")
            sc.stub(0x7E5064A1, lambda sc, g: log.append(cstr(g["a0"])) or {}, "print str")
        r = sc.call(0x7E697C05, {}, frame=(0xC0, 12))
        print("\n".join(log))
        print(r.summary())
        print("mode records 0x605A704C (7 bytes each):")
        for m in range(8):
            print(f"  mode {m}: {sc.read(0x605A704C + 7 * m, 7).hex(' ')}")
        ptrs = struct.unpack("<8I", sc.read(PTRS, 32))
        print("ae_param records:")
        for p in sorted(set(ptrs)):
            n = 5 if p == 0x605A71D8 else 2 if p == 0x605A7178 else 1
            for i in range(n):
                print(f"  {NAMES.get(p, '?')} [{i}] @0x{p + 24 * i:08X}: {rec(sc, p + 24 * i)}")
        # AE grid against the AF frame: AF geometry records (0x7E5E6BE0) give the readout origin (+20, +22) and size
        # (+8, +10) of the image that the 640x480 AF frame spans; field_afarea.py checks this mapping in the harness.
        img = open(omemu.STOCK_BLOCK0, "rb").read()
        geo = lambda a: struct.unpack_from("<13h", img, a - omemu.BASE)
        print("AE grid in the 640x480 AF frame (x0..x1, y0..y1; cell pitch in frame units):")
        for name, rec_addr, geo_addr in (("HS/HSSC", 0x605A7178, 0x7E7A101C), ("MSSC", 0x605A71A8, 0x7E7A1036),
                                         ("LSSC", 0x605A71C0, 0x7E7A106A)):
            hs, vs, hdiv, vdiv, hw, vw = struct.unpack("<hhHHHH", sc.read(rec_addr, 12))
            g = geo(geo_addr)
            bw, bh, ox, oy = g[4], g[5], g[10], g[11]
            fx = lambda px: (px - ox) * 640 / bw
            fy = lambda ln: (ln - oy) * 480 / bh
            print(f"  {name:8s} readout image {bw}x{bh} at ({ox},{oy}); AE {hdiv}x{vdiv} blocks of {hw}x{vw} at ({hs},{vs})"
                  f" -> x {fx(hs):.1f}..{fx(hs + hdiv * hw):.1f}, y {fy(vs):.1f}..{fy(vs + vdiv * vw):.1f};"
                  f" pitch {hw * 640 / bw:.2f} x {vw * 480 / bh:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

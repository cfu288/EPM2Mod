#!/usr/bin/env python3
"""Run the PEN-F 3.1 still-exposure routine (0x605B906E) in the E-PM2 function harness, as a reference.

    python3 experiments/2026-11-17-auto-iso-min-shutter/scripts/penf_expcal.py PENF_BLOCK0 [--row k=v ...] [-v]

PENF_BLOCK0 is block 0 of OLY_E_122_3101_0000_0000.BIN, unpacked (tools/oetool.py unpack) and expanded
(experiments/2026-11-15-feature-survey/scripts/expand.py). Both bodies use MN103 code, so the E-PM2 machine runs it:
the PEN-F code and tables are written at their own run-time addresses (base 0x60021020) over scratch RAM.
Layouts are the PEN-F's (NOTES.md section 4.1): mode block +2 program code, +5 stb_onoff, +6 strobe, +16 X-Sync,
+18 fastest speed without flash, +22 High Limit, +24 Default, +26 Slow Limit, +28 Lowest S/S (0x7FFF = Auto).
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import omemu  # noqa: E402
from omemu import DATA  # noqa: E402

PBASE = 0x60021020
SPAN = 0x6E0000                       # 0x60021020-0x60701020: runtime, lens, exp module, exp tables
ENTRY = 0x605B906E
ARG = DATA
SLOTS = [DATA + 0x1000 * (i + 1) for i in range(12)]     # ARG[i] -> SLOTS[i], zero-filled
MODE, SET, BV, STILL = SLOTS[0], SLOTS[1], SLOTS[2], SLOTS[7]
LENS, AVLIM = DATA + 0x10000, DATA + 0x10100

D = dict(mode=3, ae=0, focal=34, bv=0x500, av_open=0x02B0, av_close=0x0900, av_set=0x0400, tv_set=0x0600,
         sv_set=0, cv=0, limit=0x0900, std=0x0600, slow=0x0600, sync=0x0800, fast=0x0C00, stb_onoff=0, strobe=0,
         lss=0x7FFF, step=85)


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def load(emu, penf_block0):
    emu.load(omemu.check_stock())
    img = open(penf_block0, "rb").read()[:SPAN]
    for o in range(0, len(img), 0x80000):
        emu.write(PBASE + o, img[o:o + 0x80000])


def run(emu, row):
    r = dict(D, **row)
    emu.write(ARG, struct.pack("<12I", *SLOTS))
    for s in SLOTS:
        emu.write(s, bytes(0x400))
    m = bytearray(0x100)
    m[2], m[4], m[5], m[6] = r["mode"], r["ae"], r["stb_onoff"], r["strobe"]
    struct.pack_into("<2h", m, 16, s16(r["sync"]), s16(r["fast"]))
    struct.pack_into("<4h", m, 22, s16(r["limit"]), s16(r["std"]), s16(r["slow"]), s16(r["lss"]))
    emu.write(MODE, bytes(m))
    emu.write(SET, struct.pack("<8h", s16(r["tv_set"]), s16(r["sv_set"]), s16(r["av_set"]), s16(r["cv"]), 0, 0,
                               r["step"], 0))
    emu.write(BV, struct.pack("<6h", *[s16(r["bv"])] * 6))
    emu.write(LENS, bytes(0x40))
    emu.write(AVLIM, struct.pack("<3h", 0, s16(r["av_open"]), s16(r["av_close"])))
    nul = lambda e, g: {"d0": 0}
    stubs = {
        0x600750EE: nul,                                       # settings read
        0x6015C8FD: lambda e, g: {"a0": LENS},                 # a lens is attached
        0x601871C7: lambda e, g: {"d0": r["focal"]},           # focal length
        0x6015A81D: lambda e, g: {"a0": AVLIM},                # +2 open, +4 close
        0x6015E801: nul,
        0x602DC4C2: lambda e, g: {"d0": r["sync"]},            # flash sync limit
        0x60022FE1: lambda e, g: {"d0": g["d0"].bit_length() - 1 if g["d0"] else 32},   # hardware bit search
        0x4700148E: nul, 0x600232C4: nul, 0x6002304A: nul, 0x600241B5: nul, 0x6112C42C: nul,
    }
    res = emu.call(ENTRY, {"a0": ARG}, stubs=stubs, frame=(0xF0, 132), trace=False)
    st = emu.read(STILL, 0x48)
    f = struct.unpack_from("<36h", st, 0)
    return r, dict(bv=f[0], tv=f[1], sv=f[2], av=f[5], fp_tv=f[27], insns=res.get("insns"),
                   errs=[c for c in res["stub_calls"] if c["stub"] == 0x600241B5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("block0")
    ap.add_argument("--row", nargs="*", default=[])
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    from expcal import tv_str, iso_str, fno_str
    with omemu.Emu() as emu:
        load(emu, a.block0)
        r, o = run(emu, {k: int(v, 0) for k, v in (x.split("=") for x in a.row)})
        print(f"Tv {tv_str(o['tv']):>7} Av {fno_str(o['av']):>6} ISO {iso_str(o['sv']):>5} fp_tv {tv_str(o['fp_tv'])}"
              + ("  ERR" if o["errs"] else ""))
        if a.v:
            print(o)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run the E-PM2 still-exposure routine exp_cal_still (0x7E693D00) in the function harness.

    python3 experiments/2026-11-17-auto-iso-min-shutter/scripts/expcal.py            # the tables of NOTES.md
    python3 .../expcal.py --patch data/specs/SPEC.json                                  # the same on a patched block 0
    python3 .../expcal.py --row mode=3 focal=17 slow=0x800 bv=0x200 -v                # one row, all fields

The routine runs as stock code. Stand-ins (stubs) answer the calls that leave the exp module:
the settings read 0x7E457C75 (by tag), the lens record 0x7E51FD09, the focal length 0x7E53840B,
the aperture limits 0x7E51F366, the flash state 0x7E5E2976, the error logger 0x7E426D4B and the
hardware bit search 0x7E507E4B.
`focal` is the value the routine gets: the firmware's focal_length_effect, 2 x the lens focal length.
All values are Q8 APEX: 0x0600 = Tv 6 = 1/64 s (shown 1/60), Sv 6 = ISO 200, Av 4 = f/4.
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import omemu  # noqa: E402
from omemu import DATA  # noqa: E402

ENTRY = 0x7E693D00
PRM_GET = 0x7E457C75
ARG, MODE, SET, BV, P16, STILL, P24, LENS, AVLIM = (DATA + o for o in
                                                    (0, 0x100, 0x200, 0x300, 0x500, 0x600, 0x700, 0x800, 0x900))
STATE = 0x605A7C50          # 18 halfwords that 0x7E692BF3 copies (the live-view exposure state)

D = dict(mode=3, ae=0, focal=34, bv=0x500, av_open=0x02B0, av_close=0x0900, av_set=0x0400, tv_set=0x0600,
         sv_set=0, cv=0, limit=0x0900, std=0x0600, slow=0x0600, sync=0x0800, stb_onoff=0, strobe=0, c222=0,
         k=0, step=85)


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def tv_str(q8):
    t = 2.0 ** (-s16(q8 & 0xFFFF) / 256.0)
    return f"1/{1 / t:.0f}" if t < 1 else f"{t:.1f}s"


def iso_str(q8):
    return f"{100 * 2 ** (s16(q8 & 0xFFFF) / 256.0 - 5):.0f}"


def fno_str(q8):
    return f"f/{2 ** (s16(q8 & 0xFFFF) / 512.0):.1f}"


def run(emu, row):
    r = dict(D, **row)
    emu.write(ARG, struct.pack("<7I", MODE, SET, BV, 0, P16, STILL, P24))
    m = bytearray(44)
    m[3], m[5], m[6], m[7] = r["mode"], r["ae"], r["stb_onoff"], r["strobe"]
    struct.pack_into("<4h", m, 16, s16(r["sync"]), 0, s16(r["limit"]), s16(r["std"]))
    struct.pack_into("<h", m, 24, s16(r["slow"]))
    emu.write(MODE, bytes(m))
    # set: tv, sv (0 = Auto), av, cv (exposure compensation), cv_stb, step, program_shift
    emu.write(SET, struct.pack("<8h", s16(r["tv_set"]), s16(r["sv_set"]), s16(r["av_set"]), s16(r["cv"]), 0, r["step"], 0, 0))
    emu.write(BV, struct.pack("<6h", *[s16(r["bv"])] * 6) + bytes(196))
    emu.write(P16, bytes(68)); emu.write(STILL, bytes(56)); emu.write(P24, bytes(32))
    emu.write(STATE, bytes(36))
    emu.write(AVLIM, struct.pack("<3h", 0, s16(r["av_open"]), s16(r["av_close"])))
    tags = {}

    def prm(e, g):
        t = g["d0"] & 0xFFFF
        tags[t] = tags.get(t, 0) + 1
        return {"d0": {0xC222: r["c222"], 0x94BA: r["sync"]}.get(t, 0)}

    stubs = {
        PRM_GET: prm,
        0x7E51FD09: lambda e, g: {"a0": LENS},                 # a lens is attached
        0x7E53840B: lambda e, g: {"d0": r["focal"]},           # focal length in mm
        0x7E51F366: lambda e, g: {"a0": AVLIM},                # +2 open, +4 close
        0x7E5224D5: lambda e, g: {"d0": 0},
        0x7E5E2976: lambda e, g: {"d0": r["sync"]},
        0x7E426D4B: lambda e, g: {"d0": 0},
        0x7E550957: lambda e, g: {"d0": 0},
        # the hardware bit search (register 0x9A100110): index of the highest set bit, 32 for 0
        0x7E507E4B: lambda e, g: {"d0": g["d0"].bit_length() - 1 if g["d0"] else 32},
    }
    emu.write(K_ADDR, bytes([r["k"]]))
    res = emu.call(ENTRY, {"a0": ARG}, stubs=stubs, frame=(0xF0, 68), trace=False)
    st = emu.read(STILL, 56)
    f = struct.unpack_from("<24h", st, 0)
    out = dict(bv=f[0], tv=f[1], sv=f[2], sv_target=f[3], av=f[4], cv=f[5], over=st[21], over_exp=st[22],
               dev=f[12], focal=struct.unpack_from("<I", st, 28)[0], tv_th=f[23], tags=tags,
               errs=[c for c in res["stub_calls"] if c["stub"] == 0x7E426D4B])
    return r, out


K_ADDR = 0x60413275        # the byte of setting 447 (tag 0xD791); only the prototype reads it


def fmt(r, o):
    return (f"mode {r['mode']} feq={r['focal']:3d}mm slow={tv_str(r['slow']):>6} bv={s16(r['bv'])/256:5.2f} | "
            f"tv_th={tv_str(o['tv_th']):>6} | Tv {o['tv']&0xffff:04x} {tv_str(o['tv']):>7}  Av {o['av']&0xffff:04x} "
            f"{fno_str(o['av']):>6}  Sv {o['sv']&0xffff:04x} ISO {iso_str(o['sv']):>5}  over={o['over']} "
            f"dev={o['dev']}" + ("  ERR" if o["errs"] else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", nargs="*", default=[])
    ap.add_argument("--row", nargs="*")
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--proto", action="store_true", help="the table for the prototype (use with --patch)")
    a = ap.parse_args()
    image = omemu.check_stock()
    tmp = None
    if a.patch:
        import patchblock, tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".block0.bin", dir="/dev/shm", delete=False).name
        open(tmp, "wb").write(patchblock.patched_block0(a.patch)[1])
        image = tmp
    with omemu.Emu() as emu:
        emu.load(image)
        if a.row:
            row = {k: int(v, 0) for k, v in (x.split("=") for x in a.row)}
            r, o = run(emu, row)
            print(fmt(r, o))
            if a.v:
                print(o)
        elif a.proto:
            proto(emu)
        else:
            tables(emu)
    if tmp:
        os.unlink(tmp)


def proto(emu):
    print("# P1. k = 0 (Auto): tv_th for focal lengths and Slow Limits, flash off and on")
    for stb in (0, 1):
        for focal in (18, 34, 90, 300, 600):
            for slow in (0x0000, 0x0600, 0x0800):
                r, o = run(emu, dict(focal=focal, slow=slow, bv=0x0100, stb_onoff=stb, strobe=stb))
                print(f"flash={stb} " + fmt(r, o))
    print("# P2. k = 0..7, P, ISO limit 6400, 34 mm, Slow Limit 1/60, flash off")
    for k in range(8):
        for bv in (0x0900, 0x0600, 0x0400, 0x0200, 0x0000, -0x0200):
            r, o = run(emu, dict(k=k, focal=34, bv=bv, limit=0x0B00))
            print(f"k={k} " + fmt(r, o))
    print("# P3. k = 5 (1/1000) with the flash on: the X-Sync cap holds")
    for bv in (0x0900, 0x0400, 0x0000):
        r, o = run(emu, dict(k=5, focal=34, bv=bv, limit=0x0B00, stb_onoff=1, strobe=1))
        print("k=5 flash=1 " + fmt(r, o))
    print("# P4. A mode f/4, k = 4 (1/500)")
    for bv in (0x0900, 0x0600, 0x0400, 0x0200, 0x0000):
        r, o = run(emu, dict(mode=4, k=4, focal=34, bv=bv, limit=0x0B00))
        print("k=4 " + fmt(r, o))


def tables(emu):
    print("# 1. tv_th against focal length and Flash Slow Limit (P, no flash, X-Sync 1/250)")
    for focal in (18, 28, 34, 50, 90, 150, 300, 600):
        for slow in (0x0000, 0x0500, 0x0600, 0x0800):
            r, o = run(emu, dict(focal=focal, slow=slow, bv=0x0100))
            print(fmt(r, o))
    print("# 2. P mode, ISO Auto (limit 1600 = 0x0900, default 200), 35 mm-equivalent focal length 34 mm (a 17 mm lens), f/2.5 to f/22, brightness sweep")
    for slow in (0x0600, 0x0800):
        for bv in range(0x0A00, -0x0500, -0x0080):
            r, o = run(emu, dict(slow=slow, bv=bv))
            print(fmt(r, o))
    print("# 3. A mode (f/4), same sweep")
    for slow in (0x0600, 0x0800):
        for bv in range(0x0A00, -0x0500, -0x0080):
            r, o = run(emu, dict(mode=4, slow=slow, bv=bv))
            print(fmt(r, o))
    print("# 4. ISO limit 6400 (0x0B00), P, Slow Limit 1/250 and 1/125")
    for slow in (0x0800, 0x0700):
        for bv in range(0x0600, -0x0500, -0x0100):
            r, o = run(emu, dict(slow=slow, bv=bv, limit=0x0B00))
            print(fmt(r, o))
    print("# 5. M mode, ISO Auto (f/4, 1/250): exposure compensation cv = 0, -1 EV, +1 EV given to the routine")
    for cv in (0, -0x100, 0x100):
        for bv in range(0x0600, -0x0100, -0x0100):
            r, o = run(emu, dict(mode=6, tv_set=0x0800, av_set=0x0400, bv=bv, cv=cv, limit=0x0B00))
            print(f"cv={s16(cv)/256:+.1f} " + fmt(r, o))
    print("# 6. P with the flash on (stb_onoff=1, strobe=1), Slow Limit 1/60 and 1/250")
    for slow in (0x0600, 0x0800):
        for bv in (0x0800, 0x0400, 0x0100, -0x0200):
            r, o = run(emu, dict(slow=slow, bv=bv, stb_onoff=1, strobe=1))
            print(fmt(r, o))


if __name__ == "__main__":
    main()

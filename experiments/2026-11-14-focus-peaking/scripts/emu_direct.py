"""Emulator check of the direct focus-peaking spec (single functions and code pieces, tools/emu driver).

Every case runs on a base image and on the same image with the spec. Two properties are checked:
  1. flag clear: the patched image gives the same outputs as the base image (byte for byte) in every row;
  2. flag set:   the patched image gives the values that the case's model states.
"flag" is the new byte L (0x602BE8C4); for the art-task pieces J and K it is the byte L2 (0x602BE8C6).
Case A (the latch) is the only code that writes L. Its inputs are the new byte R (0x602BE8C5) and the stock
word 0x602B0DA8 ("MF Assist is running"); property 1 there is "R = 0 or word = 0 -> same struct as the base,
L = 0". Cases S and N (entries of startMfAssist / endMfAssist) write R in every run: "flag clear" there means
"same registers as the base, R = 1 (S) or 0 (N)".

Usage: emu_direct.py BASE_BLOCK0 PATCHED_BLOCK0 [NAME]
"""
import itertools, os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools", "emu"))
from omemu import Emu, SP0  # noqa: E402

LFLAG, MFA, LV, MOVST, EXPG = 0x602BE8C4, 0x602B0DA8, 0x605B1CD0, 0x605B039C, 0xA07507CC
RFLAG, L2FLAG = 0x602BE8C5, 0x602BE8C6
REC_IDX, REC = 0x605B10A4, 0x605B0EF4          # live-view record index and table (136 bytes per record)
MODE_BYTE = 0x605B091C
D = 0x7D200000                                 # scratch buffers
SP = SP0 - 0x400                               # stack pointer for code pieces


def w32(emu, a, v):
    emu.write(a, struct.pack("<I", v & 0xFFFFFFFF))


def piece(emu, start, stops, regs):
    """Run from start until one of stops; returns the registers."""
    init = {"pc": start, "sp": SP, "mdr": 0, "psw": 0}
    init.update(regs)
    emu.req("reset", regs=init)
    r = emu.req("cont", stops=list(stops))
    rg = emu.regs_of(r)
    assert r["stop"] == "break" and rg["pc"] in stops, (r["stop"], hex(rg["pc"]), rg["fault"])
    assert rg["sp"] == SP, hex(rg["sp"])
    return rg


def kind_of(rec4):
    return {-1: 0, 1: 2, 2: 2, 3: 5, 4: 3, 5: 4}.get(rec4, 1)


# ---- A: latch at the end of the struct refresh 0x7E6ECCAF
def rows_A():
    return [dict(req=q, mfa=m, mov=mv, s32=s, rec4=k, path=p)
            for q in (0, 1) for m in (0, 1, 0x100) for mv in (0, 1, 2) for s in (0, 1) for k in (-1, 0, 1, 2, 3, 4, 5, -3) for p in (0, 5)]


def run_A(emu, r, flag):
    emu.write(RFLAG, bytes([r["req"]])); w32(emu, MFA, r["mfa"]); emu.write(MOVST, bytes([r["mov"]])); emu.write(REC_IDX, b"\0\0")
    w32(emu, REC + 4, r["rec4"]); emu.write(LFLAG, b"\xee"); emu.write(LV, b"\xaa" * 0x30)
    emu.write(D, bytes(range(1, 65)))
    stubs = {0x7E6DB43E: lambda e, g: {"d0": r["path"]},
             0x7E457C75: lambda e, g: {"d0": ((g["d0"] * 31 + g["d1"]) & 0x3F) + 1},
             0x7E6CFCDE: lambda e, g: {"d0": r["s32"]},
             0x7E6CFFE4: lambda e, g: {"d0": 0x1234},
             0x7E6DB789: lambda e, g: {"a0": D},
             0x7E6DB895: lambda e, g: e.write(g["a0"], bytes(range(0x41, 0x59))) or {},
             0x7E6DBA95: lambda e, g: {"d0": g["d0"] & 0xFF}}
    emu.call(0x7E6ECCAF, {}, stubs=stubs)
    return {"struct": emu.read(LV, 0x30).hex(), "flag": emu.read(LFLAG, 1)[0]}


def model_A(r, base):
    on = r["req"] != 0 and r["mfa"] != 0 and r["mov"] != 1 and r["s32"] == 0 and kind_of(r["rec4"]) not in (2, 5)
    s = bytearray(bytes.fromhex(base["struct"]))
    if on:
        s[4] = 0
    return {"struct": s.hex(), "flag": 1 if on else 0}


# ---- B: colour-tone getter 0x7E6CBFD3 (whole function)
def rows_B():
    return [dict(mode=m, movie=f, ptr=p) for f in (0, 1) for p in (1, 0)
            for m in list(range(0, 8)) + list(range(100, 121))]


def run_B(emu, r, flag):
    emu.write(LFLAG, bytes([flag]))
    emu.write(LV, bytes([0, 0, 7, r["mode"]]) + b"\0" * 44)
    emu.write(MODE_BYTE, b"\xee")
    g = emu.call(0x7E6CBFD3, {"d0": r["movie"], "d1": 0, "a0": MODE_BYTE if r["ptr"] else 0},
                 stubs={0x7E6D144F: lambda e, x: {}})
    return {"ret": g["regs"]["d0"] & 0xFF, "mode_byte": emu.read(MODE_BYTE, 1)[0]}


def model_B(r, base):
    return {"ret": 3, "mode_byte": 119 if r["ptr"] else 0xEE}


C_L2 = {}                                      # (mode, art, flag) -> byte L2 after the piece (last image run)


# ---- C: piece 0x7E6C6148..0x7E6C6159 of the expose setter
def rows_C():
    return [dict(mode=m, art=a) for m in list(range(0, 8)) + list(range(100, 121)) for a in (3, 7, 70, 163, 164)]


def run_C(emu, r, flag):
    emu.write(LFLAG, bytes([flag]))
    emu.write(D, bytes([r["mode"]])); emu.write(MODE_BYTE, b"\x77"); emu.write(SP + 13, bytes([r["art"]]))
    emu.write(L2FLAG, b"\xee")
    g = piece(emu, 0x7E6C6148, [0x7E6C6159], {"a1": D, "d2": 0})
    C_L2[(r["mode"], r["art"], flag)] = emu.read(L2FLAG, 1)[0]
    return {"expose": emu.read(SP + 13, 1)[0], "mode_byte": emu.read(MODE_BYTE, 1)[0], "a2": g["a2"]}


def model_C(r, base):
    return {"expose": 163, "mode_byte": 0x77, "a2": 0}


# ---- D: job setup 0x7E6C74BE (whole function)
IN, JOB, RECD = D + 0x1000, D + 0x2000, D + 0x3000
IMGP_LV = 0x605B0584


def rows_D():
    return [dict(flags=f, r2=r2, code=c, t=t) for f in (0x00, 0x08, 0x28, 0x29) for r2 in (0, 1, 2)
            for c in (0, 2, 74, 104, 163) for t in (0, 0x200)]


def run_D(emu, r, flag):
    emu.write(LFLAG, bytes([flag]))
    emu.write(IN, b"\0" * 64); emu.write(JOB, b"\0" * 256); emu.write(RECD, bytes(range(128)))
    for o, v in ((0, r["flags"]), (12, 0x11111111), (16, 0x22222222), (20, 0x33333333), (44, RECD)):
        w32(emu, IN + o, v)
    emu.write(IN + 36, struct.pack("<H", 3))
    emu.write(REC_IDX, b"\0\0"); w32(emu, REC + 4, 0); emu.write(REC + 96, b"\0")
    emu.write(0x605B038E, bytes([r["r2"]]))
    emu.write(0x605B0E78, bytes([r["code"], 1, 2, 3, 4, 5, 6, 0x21, 0x22, 7]))
    emu.write(EXPG, b"\x99"); w32(emu, 0xA07507D0, r["t"]); w32(emu, 0xA07507D4, 0)
    emu.write(IMGP_LV, bytes((i * 3 + 9) & 0xFF for i in range(104)))      # the job's IMG_PARAM (fixed address)
    stubs = {0x7E6DD29C: lambda e, g: {"a0": D + 0x800}, 0x7E457C75: lambda e, g: {"d0": 0x55},
             0x7E6F2DE0: lambda e, g: {"d0": 0x11}, 0x7E6C9FA0: lambda e, g: {"d0": 2},
             0x7E6DAE68: lambda e, g: {"d0": 0x44}, 0x7E6D0298: lambda e, g: {"d0": 0x4000}}
    emu.call(0x7E6C74BE, {"a0": IN, "a1": JOB}, frame=(0xF0, 48), stubs=stubs)
    ip = struct.unpack("<I", emu.read(JOB + 96, 4))[0]
    assert ip == IMGP_LV, hex(ip)
    return {"job": emu.read(JOB, 256).hex(), "imgparam": emu.read(ip, 104).hex(), "expg": emu.read(EXPG, 1)[0],
            "in": emu.read(IN, 64).hex()}


def model_D(r, base):
    p = bytearray(bytes.fromhex(base["imgparam"]))
    p[79], p[83] = 3, 2
    return {"job": base["job"], "imgparam": p.hex(), "expg": 3, "in": base["in"]}


# ---- E: mov_art_set_line_yc_param 0x7E6CD9C5 (whole function)
IMGP, B1, B2, B3, B4 = D + 0x4000, D + 0x5000, D + 0x6000, D + 0x7000, D + 0x8000
CODES_E = (0, 3, 74, 163, 164, 169, 170, 181, 182, 183, 184, 200)


def rows_E():
    return [dict(code=c, bufs=b) for c in CODES_E for b in (1, 0)]


def run_E(emu, r, flag):
    emu.write(LFLAG, bytes([flag]))
    emu.write(JOB, bytes((i * 7 + 1) & 0xFF for i in range(256))); w32(emu, JOB + 96, IMGP)
    p = bytearray((i * 5 + 3) & 0xFF for i in range(128)); p[79] = r["code"]
    emu.write(IMGP, bytes(p))
    for b in (B1, B2, B3, B4):
        emu.write(b, b"\xcc" * 256)
    for a, v in ((0x605B0AF4, B1), (0x605B0AF8, B2), (0x605B0B00, B3), (0x605B0B04, B4)):
        w32(emu, a, v if r["bufs"] else 0)
    w32(emu, 0x605B0AF0, 0x12345678); w32(emu, 0x605B0AFC, 0x9ABCDEF0)
    emu.call(0x7E6CD9C5, {"a0": JOB}, frame=(0xF0, 24), stubs={0x7E6D13BD: lambda e, g: {}})
    return {k: emu.read(b, 256).hex() for k, b in (("job_copy", B1), ("imgparam_copy", B2), ("b3", B3), ("b4", B4))} | \
        {"job": emu.read(JOB, 256).hex(), "imgparam": emu.read(IMGP, 128).hex()}


def model_E(r, base_163):
    """Flag set: the two copies are the stock Key Line line job (the base output for art code 163)."""
    return None


# ---- G: art packet proc kind 0x7E6CCA57 (whole function)
def rows_G():
    return [dict(k=k, rec4=c, tone=t, b14=b, r96=q, st=s) for k in (0, 7, 8, 9) for c in (0, 5, 1)
            for t in (0, 115) for b in (0, 2, 3) for q in (0, 3) for s in (0, 1)]


def run_G(emu, r, flag):
    emu.write(LFLAG, bytes([flag]))
    emu.write(REC_IDX, b"\0\0"); w32(emu, REC + 4, r["rec4"]); emu.write(REC + 96, bytes([r["r96"]]))
    emu.write(LV, b"\0" * 48); emu.write(LV + 2, bytes([r["tone"]])); emu.write(LV + 14, bytes([r["b14"]]))
    g = emu.call(0x7E6CCA57, {"d0": r["k"]}, stubs={0x7E6D079D: lambda e, x: {"d0": r["st"]}})
    return {"ret": g["regs"]["d0"] & 0xFFFF}


def model_G(r, base):
    return {"ret": 0} if r["k"] in (8, 9) else base


# ---- H: piece 0x7E6C3868..0x7E6C386D of the frame-time function
def rows_H():
    return [dict(a2=a, d3=t) for a in (0, 1) for t in (5, 15, 30, 50, 85, 150)]


def run_H(emu, r, flag):
    emu.write(LFLAG, bytes([flag]))
    g = piece(emu, 0x7E6C3868, [0x7E6C386D], {"a2": r["a2"], "d3": r["d3"], "d0": 0x777})
    return {"d0": g["d0"], "d3": g["d3"], "a2": g["a2"], "flags": g["psw"] & 0xF}


def model_H(r, base):
    return dict(base, d3=85)


# ---- I: piece of img_param_set_ucType 0x7E6DAE68 from 0x7E6DAF22
def rows_I():
    return [dict(cls=c, code=a) for c in (0, 1, 2) for a in (0, 74, 163, 164, 169, 181, 182, 183, 184, 200)]


def run_I(emu, r, flag):
    emu.write(LFLAG, bytes([flag]))
    emu.write(SP + 44, bytes([r["cls"]])); emu.write(SP + 48, bytes([r["code"]]))
    g = piece(emu, 0x7E6DAF1B, [0x7E6DAF3D, 0x7E6DAF57, 0x7E6DAF67], {"d3": 4})
    return {"next": "0x%08X" % g["pc"], "d3": g["d3"]}


def model_I(r, base):
    return dict(base, next="0x7E6DAF3D") if r["cls"] == 2 else base


# ---- F: piece of mov_art_set_artpacket 0x7E6CCBE1 from 0x7E6CCE62
def rows_F():
    return [dict(movie=m, kind=k) for m in (0, 1) for k in (0, 1, 2, 3, 4, 5)]


def run_F(emu, r, flag):
    emu.write(LFLAG, bytes([flag]))
    w32(emu, D, r["movie"]); w32(emu, SP + 4, D); w32(emu, SP + 16, r["kind"])
    g = piece(emu, 0x7E6CCE62, [0x7E6CCE99, 0x7E6CCE73, 0x7E6CCE7E], {})
    return {"next": "0x%08X" % g["pc"], "d0": g["d0"] if g["pc"] == 0x7E6CCE99 else None}


def model_F(r, base):
    return {"next": "0x7E6CCE99", "d0": 0}


# ---- J: piece 0x7E726421..0x7E726428 of Key Line art pass 7
def rows_J():
    return [dict(pkt=p) for p in (0, 1, 2, 3, 4)]


def run_J(emu, r, flag):
    emu.write(L2FLAG, bytes([flag])); emu.write(LFLAG, bytes([1 - flag]))
    emu.write(IMGP, bytes((i * 5 + 3) & 0xFF for i in range(128))); w32(emu, D, IMGP)
    emu.write(D + 0x100, struct.pack("<H", r["pkt"])); w32(emu, SP + 32, D + 0x100)
    g = piece(emu, 0x7E726421, [0x7E726428], {"a2": D, "a3": 0x1111, "d2": 0x2222, "d3": 0x3333})
    return {"imgparam": emu.read(IMGP, 128).hex(), "a2": g["a2"], "a3": g["a3"], "d2": g["d2"], "d3": g["d3"]}


def model_J(r, base):
    if r["pkt"] != 2:
        return base
    p = bytearray(bytes.fromhex(base["imgparam"])); p[79] = 3
    return dict(base, imgparam=p.hex())


# ---- K: piece 0x7E726761..0x7E726770 of Key Line art pass 9
def rows_K():
    return [dict(pkt=p) for p in (0, 1, 2, 3, 4)]


def run_K(emu, r, flag):
    emu.write(L2FLAG, bytes([flag])); emu.write(LFLAG, bytes([1 - flag]))
    emu.write(JOB, b"\x5a" * 64); emu.write(D + 0x100, struct.pack("<H", r["pkt"]))
    g = piece(emu, 0x7E726761, [0x7E726770], {"a3": JOB, "a2": D + 0x100, "d2": 0x2222, "d3": 0x3333})
    return {"job": emu.read(JOB, 64).hex(), "a2": g["a2"], "a3": g["a3"], "d2": g["d2"], "d3": g["d3"]}


def model_K(r, base):
    if r["pkt"] != 2:
        return base
    j = bytearray(bytes.fromhex(base["job"])); j[34:36] = struct.pack("<H", 0x0100)
    return dict(base, job=j.hex())


# ---- S, N: entries of startMfAssist / endMfAssist (pieces up to the first stock instruction that follows)
def rows_S():
    return [dict(r0=x) for x in (0, 1, 0xEE)]


def run_S(emu, r, flag):
    emu.write(RFLAG, bytes([r["r0"]])); emu.write(LFLAG, bytes([flag]))
    g = piece(emu, 0x7E9889EB, [0x7E9889F2], {"a0": 0x12345678, "d0": 5, "d1": 6, "d2": 7, "d3": 8, "a1": 9, "a3": 10})
    return {k: g[k] for k in ("d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3")} | {"R": emu.read(RFLAG, 1)[0]}


def model_S(r, base):
    return dict(base, R=1)


def run_N(emu, r, flag):
    emu.write(RFLAG, bytes([r["r0"]])); emu.write(LFLAG, bytes([flag]))
    g = piece(emu, 0x7E9830E0, [0x7E9830E6], {"a0": 0x12345678, "d0": 5, "d1": 6, "d2": 7, "d3": 8, "a1": 9, "a2": 11, "a3": 10})
    return {k: g[k] for k in ("d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3")} | {"R": emu.read(RFLAG, 1)[0]}


def model_N(r, base):
    return dict(base, R=0)


CASES = [("A latch 0x7E6ECCAF", rows_A, run_A, model_A), ("B getter 0x7E6CBFD3", rows_B, run_B, model_B),
         ("C setter piece 0x7E6C6148", rows_C, run_C, model_C), ("D job setup 0x7E6C74BE", rows_D, run_D, model_D),
         ("E set_line_yc_param 0x7E6CD9C5", rows_E, run_E, model_E), ("G packet proc kind 0x7E6CCA57", rows_G, run_G, model_G),
         ("H frame-time piece 0x7E6C3868", rows_H, run_H, model_H), ("I ucType piece 0x7E6DAF1B", rows_I, run_I, model_I),
         ("F artpacket piece 0x7E6CCE62", rows_F, run_F, model_F), ("J pass-7 piece 0x7E726421", rows_J, run_J, model_J),
         ("K pass-9 piece 0x7E726761", rows_K, run_K, model_K),
         ("S startMfAssist entry 0x7E9889EB", rows_S, run_S, model_S), ("N endMfAssist entry 0x7E9830E0", rows_S, run_N, model_N)]


def main():
    name = sys.argv[3] if len(sys.argv) > 3 else "base"
    res = {}
    for tag, img in (("base", sys.argv[1]), ("patched", sys.argv[2])):
        with Emu() as emu:
            emu.load(img)
            for cname, rows, run, _ in CASES:
                for i, r in enumerate(rows()):
                    for flag in ((0,) if cname[0] == "A" else (0, 1)):
                        res[(tag, cname, i, flag)] = run(emu, r, flag)
    bad = 0
    print("image pair: %s and %s + peaking-direct-1" % (name, name))
    print("%-34s %5s  %-28s %-28s %s" % ("case", "rows", "flag clear: patched = base", "flag set: patched = model", "base ignores the flag"))
    for cname, rows, run, model in CASES:
        rs = rows()
        n0 = n1 = nb = 0
        changed = 0
        for i, r in enumerate(rs):
            b0, p0 = res[("base", cname, i, 0)], res[("patched", cname, i, 0)]
            if cname[0] == "A":
                want = model(r, {k: b0[k] for k in ("struct",)})
                off = r["mfa"] == 0 or r["req"] == 0
                n0 += (p0["struct"] == b0["struct"] and p0["flag"] == 0) if off else 1
                n1 += p0 == want
                nb += b0["flag"] == 0xEE
                changed += p0["struct"] != b0["struct"]
                continue
            b1, p1 = res[("base", cname, i, 1)], res[("patched", cname, i, 1)]
            if cname[0] in "SN":                      # these two hooks write R whatever the flag is
                n0 += p0 == model(r, b0) and {k: v for k, v in p0.items() if k != "R"} == {k: v for k, v in b0.items() if k != "R"}
                n1 += p1 == model(r, b1)
                nb += b1 == b0 and b0["R"] == r["r0"]
                changed += p1 != b1
                continue
            n0 += p0 == b0
            nb += b1 == b0
            if cname[0] == "E":
                ref = res[("base", cname, next(j for j, q in enumerate(rs) if q["code"] == 163 and q["bufs"] == r["bufs"]), 0)]
                ok = all(p1[k] == ref[k] for k in ("job_copy", "imgparam_copy", "b3", "b4")) and p1["job"] == b0["job"] \
                    and p1["imgparam"] == b0["imgparam"]
                n1 += ok
            else:
                n1 += p1 == model(r, b0)
            changed += p1 != b0
        ok = n0 == len(rs) and n1 == len(rs) and nb == len(rs)
        bad += not ok
        print("%-34s %5d  %-28s %-28s %-10s %s" % (cname, len(rs), "%d of %d" % (n0, len(rs)), "%d of %d" % (n1, len(rs)),
                                                   "%d of %d" % (nb, len(rs)), "ok" if ok else "FAIL")
              + "   (rows where the flag changes an output: %d)" % changed)
    l2 = all(v == f for (_, _, f), v in C_L2.items())
    print("case C also writes byte L2 = flag: %s (%d runs, patched image)" % ("ok" if l2 else "FAIL", len(C_L2)))
    bad += not l2
    print("RESULT:", "PASS" if not bad else "FAIL (%d cases)" % bad)
    sys.exit(1 if bad else 0)


main()

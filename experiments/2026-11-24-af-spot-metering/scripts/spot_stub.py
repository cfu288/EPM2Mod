#!/usr/bin/env python3
"""Assemble scripts/spot.s and run it in the function harness inside the stock zone builder 0x7E6908CE.

    uv run python experiments/2026-11-24-af-spot-metering/scripts/spot_stub.py [SPOT_TAG]

The hook `jmp STUB` is written at 0x7E690920 and the stub at 0x7E69ED8B (the free end of the exp debug printers)
in the harness memory only. The settings getter 0x7E457C75 is a harness stub that answers from a dict. For a random
18x18 grid the two spot zones (output +12, +14) must equal those of the stock window moved by the table delta of k,
for all 35 k, for Spot / HI / SH with their setting on (Spot: argument TAG, default 0x94D1), in the sensor modes HS,
MSSC and HSSC without the HS3D crop; and equal the stock centre window in each case where the stub must not move it,
movie (HSHR), LSSC, CLIP and the HS3D crop included. Prints the stub size. Exit status 1 on any mismatch.
"""
import os, random, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
sys.path.insert(0, os.path.join(ROOT, "gen", "lss-core"))
sys.path.insert(0, HERE)
import omemu  # noqa: E402
from mkspec import asm  # noqa: E402  (gen/lss-core: as + ld + objcopy with --defsym)
from spotgrid import X, Y, F, ZOUT, WOUT, MOUT, GRID, ZONES_FN, SPOTZ_FN, s16  # noqa: E402

HOOK, AT, PRM = 0x7E690920, 0x7E69ED8B, 0x7E457C75
MAPB = 0x7E7DA8F8
SMODE, HS3D = 0x605A7254, 0x7E6A2680                      # exp's sensor mode; HSSC's HS3D-crop test
SPOT_TAG = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x94D1   # the Spot setting (info 593)
END = 0x7E69EEAF
R0, C0 = (1, 4, 7, 10, 13), (0, 3, 5, 7, 9, 11, 13)        # results/field-aeparam.txt; k = col*5 + row
DELTA = [(R0[k % 5] - 7) * 18 + (C0[k // 5] - 7) for k in range(35)]


def zones(emu, grid, prm, f6=0, f8=0, mode=0, hs3d=0):
    emu.write(SMODE, struct.pack("<I", mode))
    emu.write(GRID, b"".join(struct.pack("<h", v) for v in grid))
    emu.write(X, bytes(16) + struct.pack("<I", Y))
    emu.write(X + 10, bytes([0]))
    emu.write(Y + 116, struct.pack("<I", GRID))
    emu.write(F, bytes(6) + bytes([f6, 0]) + struct.pack("<H", f8))
    emu.write(ZOUT, bytes(32))
    asked = []

    def getter(_emu, r):
        asked.append(r["d0"] & 0xFFFF)
        assert r["a0"] == 0 and r["d1"] == 0, r
        return {"d0": prm[r["d0"] & 0xFFFF]}

    def hs3d_test(_emu, r):
        asked.append("HS3D")
        return {"d0": hs3d}

    emu.call(ZONES_FN, {"d0": ZOUT, "a0": X, "a1": F, "d1": WOUT}, stack=[MOUT], trace=False,
             stubs={PRM: getter, HS3D: hs3d_test})
    return [s16(v) for v in struct.unpack("<2H", emu.read(ZOUT + 12, 4))], asked


def window(emu, grid, delta, mapaddr):
    emu.write(GRID, b"".join(struct.pack("<h", v) for v in grid))
    emu.write(ZOUT, bytes(32))
    emu.call(SPOTZ_FN, {"d0": ZOUT + 12, "a0": GRID + 2 * delta, "a1": mapaddr}, trace=False)
    return [s16(v) for v in struct.unpack("<2H", emu.read(ZOUT + 12, 4))]


def main():
    work = "/dev/shm/spot-asm"
    os.makedirs(work, exist_ok=True)
    src = open(os.path.join(HERE, "spot.s")).read().replace("SPOT_TAG,", "%#x," % SPOT_TAG)
    code, syms = asm(work, "spot", src, AT, {"PRM": PRM, "SPOTZ": SPOTZ_FN, "MAPB": MAPB, "SMODE": SMODE, "HS3D": HS3D})
    print(f"stub {len(code)} bytes at 0x{AT:08X}-0x{AT + len(code):08X} (free to 0x{END:08X}: "
          f"{'fits' if AT + len(code) <= END else 'DOES NOT FIT'})")
    rel = (syms["STUB"] - HOOK) & 0xFFFFFFFF
    jmp = b"\xdc" + struct.pack("<I", rel)
    bad = 0
    with omemu.Emu() as emu:
        emu.load(omemu.STOCK_BLOCK0)
        assert emu.read(HOOK, 5).hex() == "cd4201f038", emu.read(HOOK, 5).hex()
        emu.write(AT, code)
        emu.write(HOOK, jmp)
        rnd = random.Random(1)
        grid = [rnd.randrange(-512, 2048) for _ in range(324)]
        mapa = 0x7E7DA8E8
        on = {SPOT_TAG: 1, 0x9F91: 1, 0x9821: 1, 0x80A1: 1, 0x9699: 0, 0x84D1: 0, 0x6761: 0, 0x88B2: 17}
        centre = window(emu, grid, 0, mapa)
        # 1. every k, Spot / HI / SH with all three boxes on
        for hs in (0, 1, 2):
            for k in range(35):
                got, _ = zones(emu, grid, {**on, 0x9699: hs, 0x88B2: k})
                want = window(emu, grid, DELTA[k], mapa)
                if got != want:
                    print(f"  MISMATCH hisht {hs} k {k}: {got} want {want}")
                    bad += 1
        print(f"moved: 3 x 35 cases checked (sensor mode HS)")
        # 1b. the other live-view modes that move: MSSC (2) and HSSC (1) without the HS3D crop, all k, Spot
        for mode in (1, 2):
            for k in range(35):
                got, _ = zones(emu, grid, {**on, 0x88B2: k}, mode=mode)
                if got != window(emu, grid, DELTA[k], mapa):
                    print(f"  MISMATCH mode {mode} k {k}")
                    bad += 1
        print(f"moved: 2 x 35 cases checked (sensor modes HSSC, MSSC)")
        # 2. cases that keep the stock centre (k = 0 makes a move visible)
        keep = {
            "all off": {SPOT_TAG: 0, 0x9F91: 0, 0x9821: 0},
            "only HI on, Spot used": {SPOT_TAG: 0, 0x9821: 0},
            "only Spot on, SH used": {0x9F91: 0, 0x9821: 0, 0x9699: 2},
            "HI/SH value 3": {0x9699: 3},
            "ESP": {0x80A1: 2},
            "centre-weighted": {0x80A1: 0},
            "all targets": {0x84D1: 2},
            "C-AF+TR": {0x6761: 1},
            "k = 35": {0x88B2: 35},
            "k = 0xFFFF": {0x88B2: 0xFFFF},
        }
        keep_mode = {"movie HSHR (4)": (4, 0), "LSSC (3)": (3, 0), "CLIP (5)": (5, 0), "mode 9": (9, 0),
                     "MODE_NON 0xFFFF": (0xFFFF, 0), "HSSC with the HS3D crop": (1, 1)}
        for name, (mode, h) in keep_mode.items():
            got, asked = zones(emu, grid, {**on, 0x88B2: 0}, mode=mode, hs3d=h)
            ok = got == centre and not any(isinstance(t, int) for t in asked)
            bad += not ok
            print(f"  keep centre, sensor mode {name}: {'ok' if ok else 'MISMATCH'} (asked {asked})")
        for name, d in keep.items():
            got, asked = zones(emu, grid, {**on, 0x88B2: 0, **d})
            ok = got == centre
            bad += not ok
            print(f"  keep centre, {name}: {'ok' if ok else 'MISMATCH'} (getter asked {[hex(t) for t in asked if isinstance(t, int)]})")
        # 3. only one box checked moves only its variant
        for hs, tag in ((0, SPOT_TAG), (1, 0x9F91), (2, 0x9821)):
            bits = tag
            got, _ = zones(emu, grid, {**on, SPOT_TAG: 0, 0x9F91: 0, 0x9821: 0, tag: 1, 0x9699: hs, 0x88B2: 0})
            ok = got == window(emu, grid, DELTA[0], mapa)
            bad += not ok
            print(f"  only 0x{bits:04X} on, hisht {hs}: moved {'ok' if ok else 'MISMATCH'}")
        # 4. variant B (map B: struct byte (6) = 1 and halfword (8) = 200) keeps the centre and asks nothing
        got, asked = zones(emu, grid, {**on, 0x88B2: 0}, f6=1, f8=200)
        ok = got == window(emu, grid, 0, MAPB) and not asked
        bad += not ok
        print(f"  variant B: centre {'ok' if ok else 'MISMATCH'} (getter asked {asked})")
    print("FAIL" if bad else "PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

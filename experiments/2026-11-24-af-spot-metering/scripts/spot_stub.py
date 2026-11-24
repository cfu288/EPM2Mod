#!/usr/bin/env python3
"""Assemble gen/spot-core/spot.s and run it in the function harness inside the stock zone builder 0x7E6908CE.

    uv run python experiments/2026-11-24-af-spot-metering/scripts/spot_stub.py

The hook `jmp STUB` is written at 0x7E690920 and the stub at 0x7E69ED8B (the free end of the exp debug printers)
in the harness memory only. The settings getter 0x7E457C75 and the AF geometry's clip test 0x7E5871C0 are harness
stubs; TAKE_FOCUS (the pointer at 0x60515FA8) is a buffer in harness RAM with the special AF frame at +54 (on),
+56 mag, +58 x, +60 y. For a random 18x18 grid the two spot zones (output +12, +14) must equal those of the stock
window moved to the expected place:
1. the 35 AF targets (special frame off) for Spot / HI / SH, in HS, HSSC and MSSC: the window of build spot-af (the
   table of results/field-aeparam.txt), so the arrow-key behaviour that passed on the camera is kept;
2. special-frame points (a touch or the MAGNIFY frame) over the whole -100..+100 range, every 5 steps on both axes and
   the corners: the window whose top-left cell is round(c - 2), c the point's cell on the grid field
   (X = (x + 100) * 3.19, Y = (y + 100) * 2.39 in the 640x480 AF frame; the grid covers x 20..620, y 14.6..464.7),
   kept in 0..14; the point must lie in the window's centre 2x2 unless the window is kept at the edge;
3. the special frame wins over the AF target and also works in the all-targets AF mode;
4. the stock centre in each case where the stub must not move the window.
Then compares the assembled bytes with data/specs/spot-core-2.json. Prints the stub size. Exit status 1 on any mismatch.
"""
import json
import os
import random
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
sys.path.insert(0, HERE)
import importlib.util  # noqa: E402
import omemu  # noqa: E402
_m = importlib.util.spec_from_file_location("spot_mkspec", os.path.join(ROOT, "gen", "spot-core", "mkspec.py"))
spot = importlib.util.module_from_spec(_m)
_m.loader.exec_module(spot)                                 # gen/spot-core/mkspec.py: EXT, AREA, HOOK, asm
from spotgrid import X, Y, F, ZOUT, WOUT, MOUT, GRID, ZONES_FN, SPOTZ_FN, s16  # noqa: E402
from omemu import DATA  # noqa: E402

HOOK, AT, END = spot.HOOK, spot.AREA, spot.AREA_END
PRM, CLIP, TFP, SMODE, HS3D, MAPB = (spot.EXT[k] for k in ("PRM", "CLIP", "TFP", "SMODE", "HS3D", "MAPB"))
TF = DATA + 0x800                                           # the harness's TAKE_FOCUS
R0, C0 = (1, 4, 7, 10, 13), (0, 3, 5, 7, 9, 11, 13)        # build spot-af's windows; k = col*5 + row
DELTA = [(R0[k % 5] - 7) * 18 + (C0[k // 5] - 7) for k in range(35)]
MAPA = 0x7E7DA8E8


def touch_window(x, y):
    """Expected top-left cell (r0, c0) of the window for a special-frame point x, y (-100..+100), and whether the
    point lies in the window's centre 2x2 cells."""
    px, py = Fraction(x + 100) * Fraction(319, 100), Fraction(y + 100) * Fraction(239, 100)
    c, r = (px - 20) * 3 / 100, (py - Fraction(146, 10)) / 25        # the point's cell coordinates on the grid
    half = Fraction(1, 2)
    c0 = min(14, max(0, int((c - 2 + half) // 1)))
    r0 = min(14, max(0, int((r - 2 + half) // 1)))
    inside = c0 + 1 <= c < c0 + 3 and r0 + 1 <= r < r0 + 3
    return r0, c0, inside


def zones(emu, grid, prm, f6=0, f8=0, mode=0, hs3d=0, clip=0, special=None):
    """Run the zone builder with the hook; special = (on, mag, x, y) or None for no TAKE_FOCUS pointer change."""
    emu.write(SMODE, struct.pack("<I", mode))
    emu.write(TFP, struct.pack("<I", TF))
    on, mag, x, y = special or (0, 100, 0, 0)
    emu.write(TF, bytes(54) + bytes([on, 0]) + struct.pack("<hhh", mag, x, y) + bytes(8))
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

    def clip_test(_emu, r):
        asked.append("CLIP")
        return {"d0": clip}

    emu.call(ZONES_FN, {"d0": ZOUT, "a0": X, "a1": F, "d1": WOUT}, stack=[MOUT], trace=False,
             stubs={PRM: getter, HS3D: hs3d_test, CLIP: clip_test})
    return [s16(v) for v in struct.unpack("<2H", emu.read(ZOUT + 12, 4))], asked


def window(emu, grid, delta, mapaddr):
    emu.write(GRID, b"".join(struct.pack("<h", v) for v in grid))
    emu.write(ZOUT, bytes(32))
    emu.call(SPOTZ_FN, {"d0": ZOUT + 12, "a0": GRID + 2 * delta, "a1": mapaddr}, trace=False)
    return [s16(v) for v in struct.unpack("<2H", emu.read(ZOUT + 12, 4))]


def main():
    work = "/dev/shm/spot-asm"
    os.makedirs(work, exist_ok=True)
    code, syms = spot.asm(work, "spot", open(os.path.join(ROOT, "gen", "spot-core", "spot.s")).read(), AT, spot.EXT)
    print(f"stub {len(code)} bytes at 0x{AT:08X}-0x{AT + len(code):08X} (free to 0x{END:08X}: "
          f"{'fits' if AT + len(code) <= END else 'DOES NOT FIT'})")
    jmp = b"\xdc" + struct.pack("<I", (syms["STUB"] - HOOK) & 0xFFFFFFFF)
    bad = 0
    with omemu.Emu() as emu:
        emu.load(omemu.STOCK_BLOCK0)
        assert emu.read(HOOK, 5).hex() == "cd4201f038", emu.read(HOOK, 5).hex()
        emu.write(AT, code)
        emu.write(HOOK, jmp)
        rnd = random.Random(1)
        grid = [rnd.randrange(-512, 2048) for _ in range(324)]
        on = {0x94D1: 1, 0x9F91: 1, 0x9821: 1, 0x80A1: 1, 0x9699: 0, 0x84D1: 0, 0x6761: 0, 0x88B2: 17}
        centre = window(emu, grid, 0, MAPA)
        # 1. every AF target, special frame off: the windows of build spot-af
        n = 0
        for mode in (0, 1, 2):
            for hs in (0, 1, 2):
                for k in range(35):
                    got, _ = zones(emu, grid, {**on, 0x9699: hs, 0x88B2: k}, mode=mode)
                    n += 1
                    if got != window(emu, grid, DELTA[k], MAPA):
                        print(f"  MISMATCH AF target: mode {mode} hisht {hs} k {k}")
                        bad += 1
        print(f"1. AF targets: {n} cases (35 k x Spot/HI/SH x HS/HSSC/MSSC) against build spot-af's windows")
        # 2. special-frame points over the whole range, all three variants at a few points
        pts = sorted({(x, y) for x in range(-100, 101, 5) for y in range(-100, 101, 5)}
                     | {(-70, -70), (70, 70), (-70, 70), (70, -70), (70, -59), (0, 0), (3, 0), (7, -6), (-99, 99)})
        n = edge = 0
        rows, cols = set(), set()
        for x, y in pts:
            r0, c0, inside = touch_window(x, y)
            rows.add(r0)
            cols.add(c0)
            for hs in ((0, 1, 2) if (x, y) in ((-100, -100), (100, 100), (70, -59)) else (0,)):
                for mag in ((300, 1000, 1400) if (x, y) == (70, -59) else (1000,)):
                    got, _ = zones(emu, grid, {**on, 0x9699: hs, 0x88B2: 0}, special=(1, mag, x, y))
                    n += 1
                    if got != window(emu, grid, (r0 - 7) * 18 + (c0 - 7), MAPA):
                        print(f"  MISMATCH special frame ({x}, {y}) hisht {hs} mag {mag}: want r0 {r0} c0 {c0}")
                        bad += 1
            if not inside:
                edge += 1
                if 1 <= r0 <= 13 and 1 <= c0 <= 13:     # only a window kept at the grid edge may miss the point
                    print(f"  POINT OUTSIDE the window centre: ({x}, {y}) r0 {r0} c0 {c0}")
                    bad += 1
        print(f"2. special frame: {len(pts)} points, {n} cases; top-left rows {min(rows)}..{max(rows)}, columns "
              f"{min(cols)}..{max(cols)}; {edge} points near the edge where the window is kept inside the grid")
        for x, y in ((-100, -100), (100, 100), (-70, -70), (70, 70), (0, 0), (70, -59)):
            r0, c0, inside = touch_window(x, y)
            print(f"   ({x:4d}, {y:4d}) -> window rows {r0}-{r0 + 3}, columns {c0}-{c0 + 3}{'' if inside else ' (kept in the grid)'}")
        # 3. the special frame wins over the AF target, also in the all-targets mode
        want = window(emu, grid, (touch_window(70, -59)[0] - 7) * 18 + (touch_window(70, -59)[1] - 7), MAPA)
        for name, d in (("AF target 0 set", {0x88B2: 0}), ("all-targets AF mode", {0x84D1: 2}),
                        ("k = 0xFFFF", {0x88B2: 0xFFFF})):
            got, asked = zones(emu, grid, {**on, **d}, special=(1, 1000, 70, -59))
            ok = got == want and 0x84D1 not in asked and 0x88B2 not in asked
            bad += not ok
            print(f"3. special frame (70, -59) with {name}: {'ok' if ok else 'MISMATCH'} (asked {asked})")
        # 4. cases that keep the stock centre (k = 0 and the special frame at a corner make a move visible)
        sp = (1, 1000, -100, -100)
        keep = {
            "all off, special frame on": ({0x94D1: 0, 0x9F91: 0, 0x9821: 0}, sp),
            "only HI on, Spot used, special frame on": ({0x94D1: 0, 0x9821: 0}, sp),
            "only Spot on, SH used, special frame on": ({0x9F91: 0, 0x9821: 0, 0x9699: 2}, sp),
            "HI/SH value 3": ({0x9699: 3}, sp),
            "ESP, special frame on": ({0x80A1: 2}, sp),
            "centre-weighted, special frame on": ({0x80A1: 0}, sp),
            "C-AF+TR, special frame on": ({0x6761: 1}, sp),
            "C-AF+TR, special frame off": ({0x6761: 1}, None),
            "all targets, special frame off": ({0x84D1: 2}, None),
            "k = 35": ({0x88B2: 35}, None),
            "k = 0xFFFF": ({0x88B2: 0xFFFF}, None),
        }
        for name, (d, s) in keep.items():
            got, asked = zones(emu, grid, {**on, 0x88B2: 0, **d}, special=s)
            ok = got == centre
            bad += not ok
            print(f"4. keep centre, {name}: {'ok' if ok else 'MISMATCH'} "
                  f"(asked {[hex(t) if isinstance(t, int) else t for t in asked]})")
        keep_mode = {"movie HSHR (4)": (4, 0, 0), "LSSC (3)": (3, 0, 0), "CLIP (5)": (5, 0, 0), "mode 9": (9, 0, 0),
                     "MODE_NON 0xFFFF": (0xFFFF, 0, 0), "HSSC with the HS3D crop": (1, 1, 0),
                     "clip (magnified) view in HS": (0, 0, 1), "clip view in MSSC": (2, 0, 1)}
        for name, (mode, h, c) in keep_mode.items():
            for s in (sp, None):
                got, asked = zones(emu, grid, {**on, 0x88B2: 0}, mode=mode, hs3d=h, clip=c, special=s)
                ok = got == centre and not any(isinstance(t, int) for t in asked)
                bad += not ok
                print(f"4. keep centre, {name}, special frame {'on' if s else 'off'}: {'ok' if ok else 'MISMATCH'} "
                      f"(asked {asked})")
        # only one variant on moves only that variant, at a special-frame point
        r0, c0, _ = touch_window(-100, -100)
        for hs, tag in ((0, 0x94D1), (1, 0x9F91), (2, 0x9821)):
            got, _ = zones(emu, grid, {**on, 0x94D1: 0, 0x9F91: 0, 0x9821: 0, tag: 1, 0x9699: hs}, special=sp)
            ok = got == window(emu, grid, (r0 - 7) * 18 + (c0 - 7), MAPA)
            bad += not ok
            print(f"4. only 0x{tag:04X} on, hisht {hs}, special frame: moved {'ok' if ok else 'MISMATCH'}")
        # variant B (map B: struct byte (6) = 1 and halfword (8) = 200) keeps the centre and asks nothing
        got, asked = zones(emu, grid, {**on, 0x88B2: 0}, f6=1, f8=200, special=sp)
        ok = got == window(emu, grid, 0, MAPB) and not asked
        bad += not ok
        print(f"4. variant B (tele-converter map), special frame on: centre {'ok' if ok else 'MISMATCH'} (asked {asked})")
    spec = json.load(open(os.path.join(ROOT, "data", "specs", "spot-core-2.json")))
    new = {int(o["_addr"], 16): bytes.fromhex(o["new"]) for o in spec["ops"]}
    same = new.get(AT) == code and new.get(HOOK) == jmp
    bad += not same
    print(f"data/specs/spot-core-2.json holds these bytes: {'yes' if same else 'NO (run gen/spot-core/mkspec.py)'}")
    print("FAIL" if bad else "PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

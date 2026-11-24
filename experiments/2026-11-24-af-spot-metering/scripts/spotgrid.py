#!/usr/bin/env python3
"""Run the stock metering-zone code of the exp module in the function harness and show where the spot window is.

    uv run python experiments/2026-11-24-af-spot-metering/scripts/spotgrid.py

1. Calls 0x7E6908CE (the zone builder of 0x7E6907F0) on stock block 0 with a synthetic clipped 18x18 BV grid,
   once per variant (A: normal, B: the (6)==1 && (8)==200 case), and prints the table pointers it picks.
2. Finds the spot window: one bright cell at a time, the spot BV (0x7E691007 on the two spot zones) changes
   only for the cells of the window. Prints the 18x18 map of those cells and their weight.
3. Calls the spot-zone routine 0x7E690A62 with the grid pointer moved by the delta of each of the 35 AF targets
   (the proposed change) and checks that the bright cell under each AF target is the one that counts most.
Exit status 1 on any mismatch with the Python model.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import omemu  # noqa: E402
from omemu import DATA  # noqa: E402

ZONES_FN, SPOTZ_FN, SPOT_FN = 0x7E6908CE, 0x7E690A62, 0x7E691007
X, Y, F, ZOUT, WOUT, MOUT, GRID = (DATA + o for o in (0x000, 0x100, 0x200, 0x300, 0x340, 0x380, 0x400))
AF_CENTRES = 0x7E7A1C60          # 35 x (x, y) u16 in a 640x480 frame, index = row*7 + col
PRM_ORDER = 0x7E79167C           # prm 0x88B2 value of each AF area (column-major)


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def rd(img, a, n):
    return img[a - omemu.BASE:a - omemu.BASE + n]


def window_delta(area, img):
    """Proposed spot window for AF area (row*7+col): top-left cell (r0, c0) and the cell delta to the stock (7, 7)."""
    x, y = struct.unpack("<HH", rd(img, AF_CENTRES + 4 * area, 4))
    c0 = round(x * 18 / 640) - 2
    r0 = round(y * 18 / 480) - 2
    return r0, c0, (r0 - 7) * 18 + (c0 - 7)


def zones(emu, grid, flags=0, f6=0, f8=0):
    emu.write(GRID, b"".join(struct.pack("<h", v) for v in grid))
    emu.write(X, bytes(16) + struct.pack("<I", Y))
    emu.write(X + 10, bytes([flags]))
    emu.write(Y + 116, struct.pack("<I", GRID))
    emu.write(F, bytes(6) + bytes([f6, 0]) + struct.pack("<H", f8))
    emu.write(ZOUT, bytes(32))
    emu.call(ZONES_FN, {"d0": ZOUT, "a0": X, "a1": F, "d1": WOUT}, stack=[MOUT], trace=False)
    z = [s16(v) for v in struct.unpack("<8H", emu.read(ZOUT, 16))]
    w = struct.unpack("<4I", emu.read(WOUT, 16))
    m = struct.unpack("<2I", emu.read(MOUT, 8))
    r = emu.call(SPOT_FN, {"a0": ZOUT + 12, "a1": w[0]}, trace=False)
    return z, w, m, s16(r["regs"]["d0"])


def main():
    bad = 0
    with omemu.Emu() as emu:
        emu.load(omemu.STOCK_BLOCK0)
        img = emu.image
        base = 0x100                                  # 1 EV in Q8
        for name, f6, f8 in (("A", 0, 0), ("B", 1, 200)):
            z, w, m, spot0 = zones(emu, [base] * 324, f6=f6, f8=f8)
            print(f"variant {name}: maps 0x{m[0]:08X} (18x18) 0x{m[1]:08X} (4x4); weights spot/ave/cntr/arnd "
                  + " ".join(f"0x{v:08X}" for v in w) + f"; flat grid spot {spot0}")
            wsp = struct.unpack("<2h", rd(img, w[0], 4))
            hit = {}
            for cell in range(324):
                g = [base] * 324
                g[cell] = base + 0x800                # +8 EV in one cell
                _, _, _, spot = zones(emu, g, f6=f6, f8=f8)
                if spot != spot0:
                    hit[cell] = spot - spot0
            print("  cells that move the spot BV (row, col: delta Q8):")
            for r in range(18):
                print("   " + " ".join(f"{hit.get(r * 18 + c, 0):4d}" for c in range(18)))
            # model: 4x4 at rows 7..10, cols 7..10 with the 4x4 map; zone 5 -> spot weight 0, zone 4 -> weight 1
            m4 = rd(img, m[1], 16)
            n5, n4 = list(m4).count(5), list(m4).count(4)
            for cell, d in hit.items():
                r, c = divmod(cell, 18)
                v = m4[(r - 7) * 4 + (c - 7)] if 7 <= r <= 10 and 7 <= c <= 10 else 0
                exp = (0x800 // (n5 if v == 5 else n4)) * (wsp[0] if v == 5 else wsp[1]) / 256 if v else 0
                if v == 0 or abs(d - exp) > 2:
                    print(f"  MISMATCH cell {r},{c}: {d} model {exp:.1f}")
                    bad += 1
            if len(hit) != n5 + n4 - (0 if wsp[1] else n4):
                print(f"  MISMATCH: {len(hit)} cells, model {n5 + n4}")
                bad += 1
        # proposed change: the grid pointer moves by delta cells; the bright cell is the 2x2 centre under the target
        print("proposed window per AF target (prm 0x88B2 value k, area = row*7+col):")
        order = list(rd(img, PRM_ORDER, 35))
        _, w, m, _ = zones(emu, [base] * 324)
        for area in range(35):
            r0, c0, delta = window_delta(area, img)
            assert 0 <= r0 <= 14 and 0 <= c0 <= 14, (area, r0, c0)
            g = [base] * 324
            g[(r0 + 1) * 18 + c0 + 1] = base + 0x800  # a centre cell of the moved window
            emu.write(GRID, b"".join(struct.pack("<h", v) for v in g))
            emu.write(ZOUT, bytes(32))
            emu.call(SPOTZ_FN, {"d0": ZOUT + 12, "a0": GRID + 2 * delta, "a1": m[1]}, trace=False)
            z = [s16(v) for v in struct.unpack("<2H", emu.read(ZOUT + 12, 4))]
            ok = z[0] == base + 0x800 // 4 and z[1] == base
            bad += not ok
            k = order[area]                  # init 0x7E5880D9: RAM table [prm k] = area i where k = ROM[i]
            print(f"  area {area:2d} k {k:2d}: window rows {r0}-{r0 + 3} cols {c0}-{c0 + 3} delta {delta:4d}"
                  f" zones {z} {'ok' if ok else 'MISMATCH'}")
    print("FAIL" if bad else "PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

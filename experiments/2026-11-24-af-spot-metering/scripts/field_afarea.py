#!/usr/bin/env python3
"""Run the spot AF-area setup 0x7E5E6063 in the scenario harness and compare its window with the AE grid.

    uv run python experiments/2026-11-24-af-spot-metering/scripts/field_afarea.py

0x7E5E6063 takes an AF area (0..34), reads its centre in the 640x480 AF frame (0x7E5E7EAE, table 0x7E7A1C60) and the
geometry record of the readout (0x7E5E6BE0: 13 halfwords, HS = 0x7E7A101C: still 4606x3451, frame 640x480,
bayer 1536x691, offsets, origin 34/15), and writes the AF window in readout coordinates. With debug mask 0x2000 it
prints its `Spot:` lines (0x7E5ED36B). Inputs that need live view are given: the context struct, the area number
(sub-struct +5), geometry index (sub +44). The AE grid of the HS readout comes from field_aeparam.py:
hs 82, vs 36, 18 x 80 px by 18 x 36 lines.

Exit status 1 when the harness AF window centre differs from the model x*1536/640 + 34, y*691/480 + 15 by > 1 px.
"""
import os, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
from scenario import Scenario  # noqa: E402
import omemu  # noqa: E402

CTX, SUB = omemu.DATA + 0x1000, omemu.DATA + 0x100
AE_HS, AE_VS, AE_HW, AE_VW = 82, 36, 80, 36        # HS ae_param record (field_aeparam.py)
GEO_INDEX = {0: "HS", 2: "MSSC", 3: "LSSC", 4: "HSHR", 5: "full"}


def run(sc, area, geo, log):
    sc.write(CTX, bytes(0x600))
    sc.write(SUB, bytes(0x40))
    sc.w32(CTX + 4, SUB)
    sc.w8(SUB + 5, area)
    sc.w32(SUB + 44, geo)
    log.clear()
    r = sc.call(0x7E5E6063, {"a0": CTX}, frame=(0, 0x88))   # frame from the ret at 0x7E5E645B
    vals = {}
    for line in log:
        k, _, v = line.partition("=")
        vals[k.replace("Spot:", "").strip()] = int(v)
    return r, vals


def main():
    bad = 0
    log = []
    with Scenario(omemu.STOCK_BLOCK0) as sc:
        cstr = lambda a: sc.read(a, 64).split(b"\0")[0].decode("latin1")
        sc.stub(0x7E627500, lambda sc, g: {"d0": 1}, "debug mask")
        sc.stub(0x7E5ED36B, lambda sc, g: log.append(f"{cstr(g['a0'])}{(g['d0'] ^ 0x8000) - 0x8000 if g['d0'] & 0xFFFF0000 == 0 else g['d0']}") or {}, "print")
        sc.stub(0x7E611BA5, lambda sc, g: {"d0": 0}, "area from sub+5")
        geo = 0
        table = []
        for area in range(35):
            r, v = run(sc, area, geo, log)
            if r.fault or "single_area[0].hs" not in v:
                print(f"area {area}: {r.summary()} {v}")
                bad += 1
                continue
            hs, vs, hw, vw = (v[f"single_area[0].{k}"] for k in ("hs", "vs", "hw", "vw"))
            cx, cy = hs + hw / 2, vs + vw / 2
            ax, ay = struct.unpack("<HH", sc.read(0x7E7A1C60 + 4 * area, 4))   # centre in the 640x480 AF frame
            mx, my = ax * 1536 / 640 + 34, ay * 691 / 480 + 15
            u, w = (cx - AE_HS) / AE_HW, (cy - AE_VS) / AE_VW        # AE cell coordinates of the AF window centre
            un, wn = ax * 18 / 640, ay * 18 / 480                    # the NOTES assumption (grid = AF frame)
            c0, r0 = round(u) - 2, round(w) - 2                       # 4x4 window whose centre is nearest
            nc0, nr0 = round(un) - 2, round(wn) - 2
            table.append((area, r0, c0, (r0 - 7) * 18 + (c0 - 7), nr0, nc0))
            ok = abs(cx - mx) <= 1.5 and abs(cy - my) <= 1.5
            bad += not ok
            print(f"area {area:2d} frame ({ax},{ay}): AF window hs {hs} vs {vs} hw {hw} vw {vw}, centre ({cx:.1f},{cy:.1f})"
                  f" model ({mx:.1f},{my:.1f}) {'ok' if ok else 'MISMATCH'}; AE cell col {u:.2f} row {w:.2f}"
                  f" (NOTES {un:.2f}, {wn:.2f})")
        print("4x4 window top-left (r0, c0) per AF area on the measured field, and the NOTES values:")
        for area, r0, c0, d, nr0, nc0 in table:
            flag = "" if (r0, c0) == (nr0, nc0) else "  <- differs"
            print(f"  area {area:2d}: r0 {r0:2d} c0 {c0:2d} delta {d:4d}   NOTES r0 {nr0:2d} c0 {nc0:2d}{flag}")
            bad += not (0 <= r0 <= 14 and 0 <= c0 <= 14)
        print("full print of area 0:")
        run(sc, 0, geo, log)
        print("  " + "\n  ".join(log))
    print("FAIL" if bad else "PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

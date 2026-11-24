#!/usr/bin/env python3
"""Check the byte-level facts of donor.md in the E-M5 II 4.1 and PEN-F 3.1 firmware, and compare window placement.

    uv run python experiments/2026-11-24-af-spot-metering/scripts/donor_check.py EM5II.BIN PENF.BIN

The donor files are not in the repository (sha256 in ../../2026-11-15-feature-survey/firmware-diff.md, section 8).
Block 0 is cached outside the repository, next to each donor file. Runtime base of both donors: 0x60021020.
1. For each donor: the spot 4x4 maps, the per-cell weights, the 9x9 AF target centres, and the code bytes that load
   the three link settings (prm 0x9681, 0xF931, 0xF941) and the setting prm 0x6761 in the [TakeExp] routine.
2. The E-PM2 7x5 AF targets placed with the donor's arithmetic (truncating) and with the rounding of NOTES.md.
Exit status 1 when a byte check fails.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools"))
import disasm  # noqa: E402  (block_file)

BASE = 0x60021020
MAP_A = bytes([0, 4, 4, 0, 4, 5, 5, 4, 4, 5, 5, 4, 0, 4, 4, 0])
MAP_B = bytes([0, 0, 0, 0, 0, 5, 5, 0, 0, 5, 5, 0, 0, 0, 0, 0])
# per donor: map A, weights, AF centres, TakeExp routine, spot routine
ADDR = {
    "E-M5 II": dict(map_a=0x606604E6, weights=0x60660398, centres=0x605E54B4, takeexp=0x605DCE7E, spot=0x605B001D),
    "PEN-F": dict(map_a=0x60652D20, weights=0x60652BD2, centres=0x605E6E8C, takeexp=0x605DE6AB, spot=0x605B4B4F),
}
# (offset in the TakeExp routine, tag): `mov tag,d0` is fc cc + imm32, or 2c + imm16 for tags below 0x8000
TAG_LOADS = [(0x08, 0x6761, "2c"), (0xA0, 0x9681, "fccc"), (0xBD, 0xF931, "fccc"), (0xDB, 0xF941, "fccc")]


def check_donor(name, path):
    blk = open(disasm.block_file(path, 0, os.path.join(os.path.dirname(path), "blocks")), "rb").read()
    a = ADDR[name]
    at = lambda addr, n: blk[addr - BASE:addr - BASE + n]
    ok = at(a["map_a"], 16) == MAP_A and at(a["map_a"] + 16, 16) == MAP_B
    weights = struct.unpack("<5H", at(a["weights"], 10))
    ok &= weights == (13, 12, 9, 6, 4)
    cen = struct.unpack("<162H", at(a["centres"], 324))
    xs, ys = sorted(set(cen[0::2])), sorted(set(cen[1::2]))
    ok &= xs == [91 + 57 * i for i in range(9)] and ys == [91 + 37 * i for i in range(9)]
    for off, tag, form in TAG_LOADS:
        code = at(a["takeexp"] + off, 6)
        want = bytes.fromhex("fccc") + struct.pack("<I", tag) if form == "fccc" else bytes.fromhex("2c") + struct.pack("<H", tag)
        good = code.startswith(want)
        ok &= good
        print(f"  {name}: mov 0x{tag:04X},d0 at 0x{a['takeexp'] + off:08X}: {'ok' if good else 'MISMATCH ' + code.hex()}")
    # spot routine: `mov 133,d1` (stock top-left cell 7*18+7) and `mul 18,d1` of the AF-position branch
    good = at(a["spot"] + 0x1B3, 3) == bytes.fromhex("2d8500") and at(a["spot"] + 0x1C3, 3) == bytes.fromhex("f90112")
    ok &= good
    print(f"  {name}: spot routine 0x{a['spot']:08X}: mov 133,d1 / mul 18,d1: {'ok' if good else 'MISMATCH'}")
    print(f"  {name}: maps A/B at 0x{a['map_a']:08X}, weights {weights}, AF centres x {xs[0]}..{xs[-1]} step 57,"
          f" y {ys[0]}..{ys[-1]} step 37: {'ok' if ok else 'MISMATCH'}")
    return ok


def donor_window(fx, fy):
    """Window top-left (r0, c0) of the donor for a target centre in the 640x480 frame (scale 100 %)."""
    x = fx * 200 // 640 - 100            # 605DCE7E: to -100..+100 (divu)
    y = fy * 200 // 480 - 100
    col = int((x + 100) * 18 / 200)      # 605B001D: signed div, truncates towards zero
    row = int((y + 100) * 18 / 200)
    return max(row - 2, 0), max(col - 2, 0)


def notes_window(fx, fy):
    """Window top-left used in NOTES.md section 4."""
    return round(fy * 18 / 480) - 2, round(fx * 18 / 640) - 2


def main():
    ok = all(check_donor(n, p) for n, p in zip(ADDR, sys.argv[1:3]))
    print("E-PM2 targets (x = 103 + 72 col, y = 95 + 72 row): window top-left r0,c0  donor | NOTES")
    for row in range(5):
        cells = []
        for col in range(7):
            fx, fy = 103 + 72 * col, 95 + 72 * row
            d, n = donor_window(fx, fy), notes_window(fx, fy)
            cells.append(f"{d[0]:2},{d[1]:2}|{n[0]:2},{n[1]:2}")
        print("  " + "  ".join(cells))
    print("unlinked (stock) window: 7,7.  Centre target: donor", donor_window(319, 239), "NOTES", notes_window(319, 239))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assemble gen/spot-core/spot.s and write data/specs/spot-core-2.json: spot metering at the AF target, exposure part.

    uv run python gen/spot-core/mkspec.py [WORKDIR]

Two byte edits, both in segment 1 (experiments/2026-11-24-af-spot-metering/NOTES.md, E6, E7, "Build spot-af" and
"Build spot-af-2"):
  1. the code of spot.s in the free end of the exp debug printers, after lss-core and pana-ring-probe;
  2. 0x7E690920, in the zone builder 0x7E6908CE: `call 0x7E690A62,[d2,d3,a2,a3],56` -> `jmp STUB`.
The function harness experiments/2026-11-24-af-spot-metering/scripts/spot_stub.py runs the same source.
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "gen", "lss-core"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import oetool  # noqa: E402
from mkspec import asm  # noqa: E402  (gen/lss-core: as + ld + objcopy with --defsym)

BASE = 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
AREA, AREA_END = 0x7E69ED8B, 0x7E69EEAF      # exp debug printers, after lss-core (to 0x7E69EC6B) and pana-ring-probe
HOOK, HOOK_STOCK = 0x7E690920, bytes.fromhex("cd4201f038")
EXT = {"PRM": 0x7E457C75, "SPOTZ": 0x7E690A62, "MAPB": 0x7E7DA8F8, "SMODE": 0x605A7254, "HS3D": 0x7E6A2680,
       "CLIP": 0x7E5871C0, "TFP": 0x60515FA8}


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else "/dev/shm/spot-core-asm"
    os.makedirs(work, exist_ok=True)
    code, syms = asm(work, "spot", open(os.path.join(HERE, "spot.s")).read(), AREA, EXT)
    if len(code) > AREA_END - AREA:
        sys.exit(f"{len(code)} bytes do not fit in {AREA_END - AREA}")
    jmp = b"\xdc" + struct.pack("<I", (syms["STUB"] - HOOK) & 0xFFFFFFFF)
    raw = open(os.path.join(ROOT, STOCK), "rb").read()
    b0 = oetool.parse(raw)[0][0]["payload"]
    assert b0[HOOK - BASE:HOOK - BASE + 5] == HOOK_STOCK

    def op(addr, new, note):
        old = b0[addr - BASE:addr - BASE + len(new)]
        return {"type": "bytes", "block": 0, "offset": "%#x" % (addr - BASE), "expect": old.hex(), "new": new.hex(),
                "_addr": "%#X" % addr, "_note": note}

    spec = {
        "name": "spot-core-2",
        "description": "Spot metering at the AF target, exposure part, as the E-M5 II 4.1 does it: with metering Spot, "
                       "Spot HI or Spot SH (prm 0x80A1 = 1, prm 0x9699 = 0/1/2) and that variant On (settings 593 / 660 / "
                       "621 = prm 0x94D1 / 0x9F91 / 0x9821, u8, 0 = Off), no C-AF+TR (prm 0x6761 = 0), the live-view "
                       "sensor modes HS, HSSC (not its HS3D crop) or MSSC and no clip (magnified) view, the 4x4 spot "
                       "window of the 18x18 BV grid moves to the special AF frame when it is on (a touch on the screen or "
                       "the MAGNIFY key's frame: TAKE_FOCUS +54, x/y at +58/+60), else in single-target AF (prm 0x84D1 = "
                       "0) to the selected AF target (prm 0x88B2, 0..34); the window is kept inside the grid. Elsewhere, "
                       "and with the tele-converter map B, it stays at the centre. Code in the exp debug printers "
                       "(segment 1). See experiments/2026-11-24-af-spot-metering/NOTES.md.",
        "base": STOCK, "base_sha256": hashlib.sha256(raw).hexdigest(),
        "_symbols": {k: "%#X" % v for k, v in sorted(syms.items()) if k in ("STUB", "GETP", "TAGS", "CELL", "GO")},
        "_interface": "settings 593 (prm 0x94D1), 660 (prm 0x9F91), 621 (prm 0x9821): MODE bank, u8, ROM and full-reset "
                      "default 0; 1 = the variant meters at the AF target. data/specs/spot-menu.json gives them the rows "
                      "of the page Spot Metering",
        "ops": [
            op(AREA, code, f"new code, {len(code)} B of {AREA_END - AREA} (exp debug printers, segment 1)"),
            op(HOOK, jmp, "zone builder 0x7E6908CE: `call 0x7E690A62,[d2,d3,a2,a3],56` -> jmp STUB (STUB makes the call "
                          "and returns with the builder's frame)"),
        ],
    }
    p = os.path.join(ROOT, "data", "specs", "spot-core-2.json")
    with open(p, "w") as fh:
        json.dump(spec, fh, indent=1)
        fh.write("\n")
    print("wrote", os.path.relpath(p, ROOT), len(code), "bytes;", spec["_symbols"])


if __name__ == "__main__":
    main()

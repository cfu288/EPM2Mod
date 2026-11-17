"""Write the look files of the camera test of builds/card-looks.json (design.md section 9.3, step 4).

    uv run python experiments/2026-11-17-card-looks/scripts/mktests.py [OUTDIR]     (default build/card-looks/test)
    uv run python experiments/2026-11-17-card-looks/scripts/mktests.py --v2 [OUTDIR] (default build/card-looks/test-2)

--v2 (builds/card-looks-2.json, twelve colour slots): SWAP.BIN exchanges the looks of Pro 400H (slot 2) and Double-X
(slot 4): the Double-X entry shows Pro 400H in colour, the Pro 400H entry Double-X in black and white; DEFAULT.BIN
holds the looks of looks/card-looks.json.

Each file holds the twelve looks of looks/card-looks.json; GREY and SWAP change Pro 400H (Pale&Light Color, slot 2)
so that a photo and live view show at once whether a file was loaded:
  GREY.BIN     Pro 400H with saturation gain 0: a black-and-white picture
  SWAP.BIN     Pro 400H with an art matrix that swaps red and blue: blue sky turns orange
  BAD.BIN      GREY with one byte damaged: the camera must refuse it (the picture does not turn grey)
  DEFAULT.BIN  the built-in looks: back to normal
"""

import dataclasses
import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from epm2mod.hashing import sha256_bytes  # noqa: E402
from epm2mod.looks import lookfile, lookpack  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

paths = RepoPaths(Path(ROOT))
V2 = "--v2" in sys.argv
V3 = "--v3" in sys.argv
args = [a for a in sys.argv[1:] if a not in ("--v2", "--v3")]
if V3:      # builds/card-looks-3.json: CYAN.BIN = the built-in looks, Pro 400H (slot 2) named "Cyan Test" with a red
            # tone curve of 0 (photo and live view cyan, without half-press if the live tables work)
    default = lookpack.load_list(paths, paths.card_looks)
    looks = list(default)
    looks[2] = dataclasses.replace(default[2], name="Cyan Test", curves=((0,) * 1024,) + default[2].curves[1:])
    out = args[0] if args else os.path.join(ROOT, "build", "card-looks", "test-3")
    os.makedirs(out, exist_ok=True)
    for name, data in {"CYAN.BIN": lookfile.pack(looks)}.items():
        open(os.path.join(out, name), "wb").write(data)
        print(name, len(data), sha256_bytes(data))
    sys.exit(0)
if V2:
    default = lookpack.load_list(paths, paths.card_looks)
    swap = list(default)
    swap[2], swap[4] = (dataclasses.replace(default[4], slot=2, name="Double-X in 2"),
                        dataclasses.replace(default[2], slot=4, name="Pro 400H in 4"))
    out = args[0] if args else os.path.join(ROOT, "build", "card-looks", "test-2")
    os.makedirs(out, exist_ok=True)
    for name, data in {"SWAP.BIN": lookfile.pack(swap), "DEFAULT.BIN": lookfile.pack(default)}.items():
        open(os.path.join(out, name), "wb").write(data)
        print(name, len(data), sha256_bytes(data))
    sys.exit(0)
default = lookpack.load_list(paths, Path(os.path.join(ROOT, "build", "card-looks", "list-card-looks.json")))


def with_slot2(**changes):
    looks = list(default)
    looks[2] = dataclasses.replace(looks[2], **changes)
    return lookfile.pack(looks)


grey = with_slot2(name="Grey test", gain=0)
bad = bytearray(grey)
bad[5000] ^= 1
files = {"GREY.BIN": grey, "SWAP.BIN": with_slot2(name="Swap test", matrix=(0, 0, 256, 0, 256, 0, 256, 0, 0)),
         "BAD.BIN": bytes(bad), "DEFAULT.BIN": lookfile.pack(default)}
out = args[0] if args else os.path.join(ROOT, "build", "card-looks", "test")
os.makedirs(out, exist_ok=True)
for name, data in files.items():
    open(os.path.join(out, name), "wb").write(data)
    print(name, len(data), sha256_bytes(data))

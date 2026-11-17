"""Write the look files of the camera test of builds/card-looks.json (design.md section 9.3, step 4).

    uv run python experiments/2026-11-17-card-looks/scripts/mktests.py [OUTDIR]     (default build/card-looks/test)

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
default = lookpack.load_list(paths, paths.card_looks)


def with_slot2(**changes):
    looks = list(default)
    looks[2] = dataclasses.replace(looks[2], **changes)
    return lookfile.pack(looks)


grey = with_slot2(name="Grey test", gain=0)
bad = bytearray(grey)
bad[5000] ^= 1
files = {"GREY.BIN": grey, "SWAP.BIN": with_slot2(name="Swap test", matrix=(0, 0, 256, 0, 256, 0, 256, 0, 0)),
         "BAD.BIN": bytes(bad), "DEFAULT.BIN": lookfile.pack(default)}
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "card-looks", "test")
os.makedirs(out, exist_ok=True)
for name, data in files.items():
    open(os.path.join(out, name), "wb").write(data)
    print(name, len(data), sha256_bytes(data))

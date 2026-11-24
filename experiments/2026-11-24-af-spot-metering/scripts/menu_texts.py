"""List the English menu texts of the stock E-PM2 that contain a pattern (regex), with their string ids.

    uv run python experiments/2026-11-24-af-spot-metering/scripts/menu_texts.py PATTERN
"""

import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "gen", "lss-menu"))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from blob import N_IDS, Blob  # noqa: E402
from epm2mod.container import parse  # noqa: E402

b1 = bytes(parse(open(os.path.join(ROOT, "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"), "rb").read()).blocks[1].payload)
eng = next(b for b in (Blob(b1, e) for e in range(1, 35)) if b.code.upper().startswith("EN"))
pat = re.compile(sys.argv[1], re.I)
for i in range(N_IDS):
    t = eng.text(i)
    if pat.search(t):
        print(i, repr(t))

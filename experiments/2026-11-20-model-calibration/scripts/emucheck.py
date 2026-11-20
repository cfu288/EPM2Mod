"""Emulator check of calib-probe: each film code selects its table (the probe's emucheck.verify). Research code.

    OMP_NUM_THREADS=2 uv run --with colour-science python experiments/2026-11-20-model-calibration/scripts/emucheck.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402
import emucheck as E  # noqa: E402  (experiments/2026-11-20-twelve-region/scripts, on the path through design)

if __name__ == "__main__":
    tb = design.tables()
    entries = [(a, design.ENTRIES[a - 1], design.CODES[a - 1], design.TABLE_OF[a][0] if a in design.TABLE_OF else None)
               for a in range(1, 13)]
    tables = {c: (tb[t], tb[t]) for c, t in (design.TABLE_OF[a] for a in design.TABLE_OF) if c}
    sys.exit(1 if E.verify("data/builds/calib-probe.json", entries, tables, "calib") else 0)

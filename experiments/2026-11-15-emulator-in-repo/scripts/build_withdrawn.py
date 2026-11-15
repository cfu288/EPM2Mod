#!/usr/bin/env python3
"""build_withdrawn.py OUT.BIN: build the withdrawn image "level build + peaking-direct-2" for the boot test.

    .venv/bin/python experiments/2026-11-15-emulator-in-repo/scripts/build_withdrawn.py /tmp/scratch/peaking-direct-2.BIN

The image is the one that crashed at start-up in the emulator on 2026-11-14 (sha256 b5493233...): the
specs of builds/seven-films-6-interval-240-level.json, then
experiments/2026-11-14-focus-peaking/specs/peaking-direct-2.json. `epm2mod apply` refuses it now,
because the spec changes a byte that interval-timelapse-v2 covers and keeps (a check added after that
day). This script switches that one check off and calls the same library. It writes only OUT.BIN.
Never flash the result.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
from epm2mod import cli, spec  # noqa: E402

spec._check_kept_bytes = lambda *a, **k: None  # the withdrawn spec predates this check
specs = json.loads((REPO / "builds/seven-films-6-interval-240-level.json").read_text())["specs"]
specs.append("experiments/2026-11-14-focus-peaking/specs/peaking-direct-2.json")
sys.exit(cli.main(["apply", *[str(REPO / s) for s in specs], "-o", sys.argv[1]]))

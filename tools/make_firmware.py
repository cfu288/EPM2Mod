#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Make a firmware build: download the stock firmware, apply the patch specs, check the result.

    uv run tools/make_firmware.py                               the pinned build
    uv run tools/make_firmware.py --card /Volumes/NAME          the same, copied to that SD card
    uv run tools/make_firmware.py builds/NAME.json              another build
    uv run tools/make_firmware.py builds/NAME.json --pin DATE   record a passed camera test and pin

This is `epm2mod make` (src/epm2mod/cli.py) for people who have not installed the package.
Python standard library only; `uv run` gets a Python for you, or use `python3` in its place.
"""
import sys

import _package  # noqa: F401
from epm2mod.cli import main

if __name__ == "__main__":
    sys.exit(main(["make", *sys.argv[1:]]))

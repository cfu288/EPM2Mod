#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Download the stock Olympus E-PM2 v1.6 firmware from the maker's update catalog and check it.

    uv run tools/fetch_stock.py     -> firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN

This is `epm2mod fetch-stock` (src/epm2mod/stock.py) for people who have not installed the package.
Python standard library only; `uv run` gets a Python for you, or use `python3` (3.10 or newer).
"""
import sys

import _package  # noqa: F401
from epm2mod.cli import main

if __name__ == "__main__":
    sys.exit(main(["fetch-stock", *sys.argv[1:]]))

"""Run the EXP helper calc_r (0x7E698AC6) in om-emu: readout-domain width = (use width x resize) >> 16, made even.

Usage: uv run python experiments/2026-11-19-movie-sampling/scripts/geom_calc_r.py
Compares the stock HSHR pair (1662, 91750 = 1.4 in Q16) with candidate 1920-wide pairs (resize 78643 = 1.2).
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../emulator"))
import omemu  # noqa: E402

DEBUG_FLAGS = 0x7E69F188  # returns the [exp] debug-print mask; 0 = no prints
PRINT = 0x7E50652F
cases = [(1662, 91750), (1548, 65536), (1938, 78643), (1936, 78643), (1920, 78643)]
with omemu.Emu() as e:
    e.load(omemu.STOCK_BLOCK0)
    for use, resize in cases:
        r = e.call(0x7E698AC6, regs={"d0": use, "d1": resize},
                   stubs={DEBUG_FLAGS: lambda emu, rg: {"d0": 0}, PRINT: lambda emu, rg: {}})
        got = r["regs"]["d0"] & 0xFFFF
        model = (use * resize) >> 16
        model += model & 1
        print(f"use {use:5d} resize {resize:6d} -> {got:5d} (model {model})")
        assert got == model, (use, resize, got, model)

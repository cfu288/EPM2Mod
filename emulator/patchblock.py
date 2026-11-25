#!/usr/bin/env python3
"""Build a patched E-PM2 block 0 (the descrambled payload om-emu loads) from patch specs.

    python3 emulator/patchblock.py data/specs/film-portra.json [more.json ...] -o OUT.block0.bin

Uses the same spec format and the same checks as epm2mod make (base sha256, every op's expected bytes, bytes that
an earlier spec keeps), through the package's apply_specs. Only block 0 is written; ops on other blocks are still
checked and applied, then reported as "not emulated". Prints the changed block-0 ranges as runtime addresses.
"""
import argparse, hashlib, os, sys
import pathlib
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod import container  # noqa: E402
from epm2mod.errors import SpecError  # noqa: E402
from epm2mod.spec import apply_specs, load_spec  # noqa: E402

BASE = 0x7E421020


def patched_block0(spec_paths):
    specs = [load_spec(Path(p)) for p in spec_paths]
    raw = pathlib.Path(os.path.join(ROOT, specs[0].base)).read_bytes()
    try:
        image = apply_specs(raw, specs).image
    except SpecError as error:
        raise SystemExit(str(error))
    other = [f"{s.name}: block {op.block} {type(op).__name__}" for s in specs for op in s.ops if op.block != 0]
    return container.parse(raw).blocks[0].payload, container.parse(image).blocks[0].payload, other


def ranges(a, b):
    out, i, n = [], 0, len(a)
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            out.append((i, j))
            i = j
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    stock, new, other = patched_block0(a.specs)
    pathlib.Path(a.out).write_bytes(new)
    rs = ranges(stock, new)
    print(f"wrote {a.out}  sha256={hashlib.sha256(new).hexdigest()}")
    print(f"{sum(e - s for s, e in rs)} bytes differ in {len(rs)} runs:")
    for s, e in rs[:40]:
        print(f"  0x{BASE + s:08x}..0x{BASE + e:08x} (offset 0x{s:x}, {e - s} B)")
    if len(rs) > 40:
        print(f"  ... {len(rs) - 40} more")
    for o in other:
        print(f"  not emulated: {o}")


if __name__ == "__main__":
    main()

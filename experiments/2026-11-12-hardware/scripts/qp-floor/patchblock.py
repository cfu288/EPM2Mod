#!/usr/bin/env python3
"""Build a patched E-PM2 block 0 (the descrambled payload om-emu loads) from patch specs.

    python3 tools/emu/patchblock.py patches/film-portra.json [more.json ...] -o OUT.block0.bin

Uses the same spec format and the same checks as tools/build.py (base sha256, every op's expected bytes), through
build.apply_op and oetool.parse. Only block 0 is written; ops on other blocks are still checked and applied, then
reported as "not emulated". Prints the changed block-0 ranges as runtime addresses.
"""
import argparse, contextlib, hashlib, io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build, oetool  # noqa: E402

BASE = 0x7E421020


def patched_block0(spec_paths):
    specs = [json.load(open(p)) for p in spec_paths]
    if len({s["base"] for s in specs}) != 1:
        raise SystemExit("specs use different bases")
    raw = open(os.path.join(ROOT, specs[0]["base"]), "rb").read()
    for s in specs:
        if hashlib.sha256(raw).hexdigest() != s["base_sha256"]:
            raise SystemExit(f"{s['name']}: base sha256 mismatch")
    blocks, _ = oetool.parse(raw)
    stock = blocks[0]["payload"]
    other = []
    for s in specs:
        for op in s["ops"]:
            with contextlib.redirect_stdout(io.StringIO()):
                build.apply_op(blocks, op)          # SystemExit on a wrong expected byte
            if op["block"] != 0:
                other.append(f"{s['name']}: block {op['block']} {op['type']}")
    return stock, blocks[0]["payload"], other


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
    open(a.out, "wb").write(new)
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

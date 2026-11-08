#!/usr/bin/env python3
"""Build a flashable E-PM2 firmware image from a stock BIN plus one or more patch specs.

    python3 tools/build.py patches/pixel-hacking.json [patches/other.json ...] [-o build/NAME.BIN]

Each spec is JSON:
  {
    "name": "pixel-hacking",
    "description": "...",
    "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",   # path relative to repo root
    "base_sha256": "...",                                            # build refuses a different base
    "ops": [ ...see below... ],
    "expected_sha256": "..."    # optional; set once a build has been camera-tested
  }

Ops (all edits keep sizes; every op checks the bytes it replaces):
  {"type": "bytes", "block": 0, "offset": "0x2CCEC0", "expect": "hex", "new": "hex"}
  {"type": "utf16-replace-all", "block": 1, "old": "text", "new": "same-length text", "count": 16}

When several specs are given they are applied in order. All specs must share the same base.
"""
import argparse, hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import oetool  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def apply_op(blocks, op):
    blk = op["block"]
    p = bytearray(blocks[blk]["payload"])
    if op["type"] == "bytes":
        off = int(op["offset"], 0) if isinstance(op["offset"], str) else op["offset"]
        old, new = bytes.fromhex(op["expect"]), bytes.fromhex(op["new"])
        if len(old) != len(new):
            raise SystemExit(f"bytes op at block{blk}+{off:#x}: expect/new length differ")
        cur = bytes(p[off:off + len(old)])
        if cur != old:
            raise SystemExit(f"block{blk}+{off:#x}: found {cur.hex()}, expected {old.hex()}")
        p[off:off + len(new)] = new
        print(f"  block{blk}+{off:#x}: {old.hex()} -> {new.hex()}")
    elif op["type"] == "utf16-replace-all":
        old, new = op["old"].encode("utf-16le"), op["new"].encode("utf-16le")
        if len(old) != len(new):
            raise SystemExit(f"utf16 op '{op['old']}' -> '{op['new']}': lengths differ")
        hits, i = [], p.find(old)
        while i >= 0:
            if i % 2 == 0:
                hits.append(i)
            i = p.find(old, i + 1)
        if "count" in op and len(hits) != op["count"]:
            raise SystemExit(f"'{op['old']}': found {len(hits)} aligned copies, spec expects {op['count']}")
        for h in hits:
            p[h:h + len(new)] = new
        print(f"  block{blk}: '{op['old']}' -> '{op['new']}' x{len(hits)}")
    else:
        raise SystemExit(f"unknown op type {op['type']}")
    blocks[blk]["payload"] = bytes(p)


def build(spec_paths, out=None):
    specs = [json.load(open(s)) for s in spec_paths]
    bases = {s["base"] for s in specs}
    if len(bases) != 1:
        raise SystemExit(f"specs use different bases: {bases}")
    base_path = os.path.join(ROOT, specs[0]["base"])
    raw = open(base_path, "rb").read()
    for s in specs:
        if sha(raw) != s["base_sha256"]:
            raise SystemExit(f"{s['name']}: base sha256 {sha(raw)} != {s['base_sha256']}")
    blocks, tail = oetool.parse(raw)
    for s in specs:
        print(f"[{s['name']}]")
        for op in s["ops"]:
            apply_op(blocks, op)
    img = oetool.build(blocks, tail)
    out = out or os.path.join(ROOT, "build", "+".join(s["name"] for s in specs) + ".BIN")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(img)
    ok = oetool.info(out)
    digest = sha(img)
    if len(specs) == 1 and specs[0].get("expected_sha256"):
        match = digest == specs[0]["expected_sha256"]
        print(f"expected_sha256: {'MATCH' if match else 'MISMATCH'}")
        ok = ok and match
    diff = sum(a != b for a, b in zip(raw, img))
    print(f"wrote {os.path.relpath(out, ROOT)}  ({diff} bytes differ from base)")
    print(f"flash as DCOLYMP/E1019999.BIN")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    sys.exit(0 if build(a.specs, a.out) else 1)

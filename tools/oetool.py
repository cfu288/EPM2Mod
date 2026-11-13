#!/usr/bin/env python3
"""Olympus "OE" firmware container tool (the older command-line form).

    oetool.py info   FW.BIN
    oetool.py unpack FW.BIN OUTDIR          -> OUTDIR/manifest.json, blockN_<kind>.bin, tail.bin
    oetool.py pack   OUTDIR NEW.BIN         -> rebuilds the container, recomputes the checksums
    oetool.py patch  FW.BIN NEW.BIN BLOCK OFFSET HEXBYTES [--expect HEXBYTES] ...

The format and the code are in the `epm2mod` package (src/epm2mod/container.py). This file keeps
the command and the functions that older scripts in tools/ and experiments/ call. Blocks are
dicts here: `off`, `header`, `trailer`, `payload` (unscrambled), `ok`, `addr`, `kind`.
"""
import hashlib
import json
import os
import sys

import _package  # noqa: F401
from epm2mod import container as _c

LANES = _c.LANES
decode = _c.descramble
encode = _c.scramble
wsum = _c.word_sum


def parse(d):
    """Return (blocks as dicts, tail) of a firmware file."""
    parsed = _c.parse(d)
    blocks = [
        dict(off=b.offset, header=b.header, trailer=b.trailer, payload=b.payload, ok=b.checksum_ok, addr=b.load_address, kind=b.kind)
        for b in parsed.blocks
    ]
    return blocks, parsed.tail


def build(blocks, tail):
    """Return the firmware file of blocks (dicts with header, trailer, payload) and a tail."""
    made = [_c.Block(b.get("off", 0), b["header"], b["trailer"], b["payload"], False) for b in blocks]
    try:
        return _c.serialize(_c.Container(made, tail))
    except _c.ContainerError as error:
        raise ValueError(str(error)) from None


def info(path):
    """Print a description of a firmware file. Return True if every checksum is right."""
    d = open(path, "rb").read()
    lines = _c.describe(d)
    print(f"{path}  size={len(d)}  sha256={hashlib.sha256(d).hexdigest()}")
    print("\n".join("  " + line for line in lines))
    return all("checksum=BAD" not in line for line in lines)


def unpack(path, outdir):
    """Write the blocks (unscrambled), the tail and a manifest to a folder."""
    blocks, tail = parse(open(path, "rb").read())
    os.makedirs(outdir, exist_ok=True)
    man = {"source": os.path.basename(path), "blocks": []}
    for n, b in enumerate(blocks):
        fn = f"block{n}_{b['kind']:04x}.bin"
        open(os.path.join(outdir, fn), "wb").write(b["payload"])
        man["blocks"].append(dict(file=fn, header=b["header"].hex(), trailer=b["trailer"].hex()))
    open(os.path.join(outdir, "tail.bin"), "wb").write(tail)
    json.dump(man, open(os.path.join(outdir, "manifest.json"), "w"), indent=1)
    print(f"unpacked {len(blocks)} blocks + tail to {outdir}")


def pack(indir, outpath):
    """Rebuild a firmware file from a folder that `unpack` wrote."""
    man = json.load(open(os.path.join(indir, "manifest.json")))
    blocks = [
        dict(header=bytes.fromhex(b["header"]), trailer=bytes.fromhex(b["trailer"]), payload=open(os.path.join(indir, b["file"]), "rb").read())
        for b in man["blocks"]
    ]
    tail = open(os.path.join(indir, "tail.bin"), "rb").read()
    image = build(blocks, tail)  # may raise: build first, so no empty file is left
    open(outpath, "wb").write(image)
    return info(outpath)


def patch(src, dst, specs):
    """Replace bytes: specs are (block, offset, new bytes, expected bytes or None)."""
    blocks, tail = parse(open(src, "rb").read())
    for blk, off, new, expect in specs:
        p = bytearray(blocks[blk]["payload"])
        cur = bytes(p[off:off + len(new)])
        if expect is not None and cur != expect:
            raise SystemExit(f"block{blk}+0x{off:x}: found {cur.hex()}, expected {expect.hex()}; refusing")
        p[off:off + len(new)] = new
        blocks[blk]["payload"] = bytes(p)
        print(f"block{blk}+0x{off:x}: {cur.hex()} -> {new.hex()}")
    image = build(blocks, tail)  # may raise: build first, so no empty file is left
    open(dst, "wb").write(image)
    return info(dst)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "info":
        sys.exit(0 if info(a[1]) else 1)
    elif cmd == "unpack":
        unpack(a[1], a[2])
    elif cmd == "pack":
        sys.exit(0 if pack(a[1], a[2]) else 1)
    elif cmd == "patch":
        src, dst, rest, specs = a[1], a[2], a[3:], []
        while rest:
            blk, off, new = int(rest[0]), int(rest[1], 0), bytes.fromhex(rest[2])
            rest, expect = rest[3:], None
            if rest[:1] == ["--expect"]:
                expect, rest = bytes.fromhex(rest[1]), rest[2:]
            specs.append((blk, off, new, expect))
        sys.exit(0 if patch(src, dst, specs) else 1)
    else:
        sys.exit(__doc__)

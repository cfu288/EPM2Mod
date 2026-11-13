#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
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


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


def _write(path, data):
    with open(path, "wb") as handle:
        handle.write(data)


def parse(d):
    """Return (blocks as dicts, tail) of a firmware file.

    Data that does not start with a block gives no blocks and the whole data as the tail, as
    this tool always did. Data that ends inside a block raises ValueError.
    """
    if d[:2] != _c.MAGIC:
        return [], d
    try:
        parsed = _c.parse(d)
    except _c.ContainerError as error:
        raise ValueError(str(error)) from None
    blocks = [
        dict(off=b.offset, header=b.header, trailer=b.trailer, payload=b.payload, ok=b.checksum_ok, addr=b.load_address, kind=b.kind)
        for b in parsed.blocks
    ]
    return blocks, parsed.tail


def build(blocks, tail):
    """Return the firmware file of blocks (dicts with header, trailer, payload) and a tail."""
    try:
        made = tuple(_c.Block(b.get("off", 0), b["header"], b["trailer"], b["payload"], False) for b in blocks)
        return _c.serialize(_c.Container(made, tail))
    except _c.ContainerError as error:
        raise ValueError(str(error)) from None


def info(path):
    """Print a description of a firmware file. Return True if every checksum is right."""
    d = _read(path)
    blocks, tail = parse(d)
    print(f"{path}  size={len(d)}  sha256={hashlib.sha256(d).hexdigest()}")
    for n, b in enumerate(blocks):
        print(f"  block{n} @0x{b['off']:08x} kind=0x{b['kind']:04x} addr=0x{b['addr']:08x} len={len(b['payload'])} checksum={'OK' if b['ok'] else 'BAD'}")
    print(f"  tail len={len(tail)} sha256={hashlib.sha256(tail).hexdigest()[:16]}")
    return all(b["ok"] for b in blocks)


def unpack(path, outdir):
    """Write the blocks (unscrambled), the tail and a manifest to a folder."""
    blocks, tail = parse(_read(path))
    os.makedirs(outdir, exist_ok=True)
    man = {"source": os.path.basename(path), "blocks": []}
    for n, b in enumerate(blocks):
        fn = f"block{n}_{b['kind']:04x}.bin"
        _write(os.path.join(outdir, fn), b["payload"])
        man["blocks"].append(dict(file=fn, header=b["header"].hex(), trailer=b["trailer"].hex()))
    _write(os.path.join(outdir, "tail.bin"), tail)
    _write(os.path.join(outdir, "manifest.json"), json.dumps(man, indent=1).encode())
    print(f"unpacked {len(blocks)} blocks + tail to {outdir}")


def pack(indir, outpath):
    """Rebuild a firmware file from a folder that `unpack` wrote."""
    man = json.loads(_read(os.path.join(indir, "manifest.json")))
    blocks = [
        dict(header=bytes.fromhex(b["header"]), trailer=bytes.fromhex(b["trailer"]), payload=_read(os.path.join(indir, b["file"])))
        for b in man["blocks"]
    ]
    tail = _read(os.path.join(indir, "tail.bin"))
    image = build(blocks, tail)  # may raise: build first, so no empty file is left
    _write(outpath, image)
    return info(outpath)


def patch(src, dst, specs):
    """Replace bytes: specs are (block, offset, new bytes, expected bytes or None)."""
    blocks, tail = parse(_read(src))
    for blk, off, new, expect in specs:
        p = bytearray(blocks[blk]["payload"])
        cur = bytes(p[off:off + len(new)])
        if expect is not None and cur != expect:
            raise SystemExit(f"block{blk}+0x{off:x}: found {cur.hex()}, expected {expect.hex()}; refusing")
        p[off:off + len(new)] = new
        blocks[blk]["payload"] = bytes(p)
        print(f"block{blk}+0x{off:x}: {cur.hex()} -> {new.hex()}")
    image = build(blocks, tail)  # may raise: build first, so no empty file is left
    _write(dst, image)
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

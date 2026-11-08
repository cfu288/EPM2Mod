#!/usr/bin/env python3
"""Olympus "OE" firmware container tool (tested on E-PM2 / model 1010).

Container layout, repeated per block, then an opaque tail (H8 sub-MCU "OM" image):
  header  32 bytes  'OE' | model(2) | ... | load addr @8 (LE) | payload len @12 (LE) | kind @20
  payload len bytes, scrambled: 16-byte lanes permuted by LANES, then XOR 0xFF
  trailer 32 bytes  = header[0:28] + checksum word
  checksum: sum of all LE u32 words of header + DECODED payload + trailer == 0 (mod 2^32)

Usage:
  oetool.py info   FW.BIN
  oetool.py unpack FW.BIN OUTDIR          -> OUTDIR/manifest.json, blockN_<kind>.bin, tail.bin
  oetool.py pack   OUTDIR NEW.BIN         -> rebuilds container, recomputes checksums
  oetool.py patch  FW.BIN NEW.BIN BLOCK OFFSET HEXBYTES [--expect HEXBYTES] ...
"""
import json, struct, sys, os, hashlib

LANES = (1, 3, 0, 2, 6, 4, 7, 5, 11, 10, 9, 8, 13, 14, 12, 15)
MASK = 0xFFFFFFFF


def decode(enc):
    out = bytearray(len(enc))
    for o, i in enumerate(LANES):
        out[o::16] = bytes(x ^ 0xFF for x in enc[i::16])
    return bytes(out)


def encode(dec):
    out = bytearray(len(dec))
    for o, i in enumerate(LANES):
        out[i::16] = bytes(x ^ 0xFF for x in dec[o::16])
    return bytes(out)


def wsum(b):
    return sum(struct.unpack(f"<{len(b)//4}I", b)) & MASK


def parse(d):
    blocks, off = [], 0
    while off + 64 <= len(d) and d[off:off + 2] == b"OE":
        h = d[off:off + 32]
        L = struct.unpack_from("<I", h, 12)[0]
        if L % 16:
            raise ValueError(f"block @0x{off:x}: length {L} not a multiple of 16")
        t = d[off + 32 + L:off + 64 + L]
        dec = decode(d[off + 32:off + 32 + L])
        ok = (wsum(h) + wsum(dec) + wsum(t)) & MASK == 0
        blocks.append(dict(off=off, header=h, trailer=t, payload=dec, ok=ok,
                           addr=struct.unpack_from("<I", h, 8)[0],
                           kind=struct.unpack_from("<H", h, 20)[0]))
        off += 64 + L
    return blocks, d[off:]


def build(blocks, tail):
    out = bytearray()
    for b in blocks:
        h, dec = b["header"], b["payload"]
        if struct.unpack_from("<I", h, 12)[0] != len(dec):
            raise ValueError("payload size changed; resizing blocks is not supported")
        t = bytearray(b["trailer"])
        t[28:32] = b"\0\0\0\0"
        ck = (-(wsum(h) + wsum(dec) + wsum(bytes(t)))) & MASK
        struct.pack_into("<I", t, 28, ck)
        out += h + encode(dec) + t
    return bytes(out + tail)


def info(path):
    d = open(path, "rb").read()
    blocks, tail = parse(d)
    print(f"{path}  size={len(d)}  sha256={hashlib.sha256(d).hexdigest()}")
    for n, b in enumerate(blocks):
        print(f"  block{n} @0x{b['off']:08x} kind=0x{b['kind']:04x} addr=0x{b['addr']:08x} "
              f"len={len(b['payload'])} checksum={'OK' if b['ok'] else 'BAD'}")
    print(f"  tail len={len(tail)} sha256={hashlib.sha256(tail).hexdigest()[:16]}")
    return all(b["ok"] for b in blocks)


def unpack(path, outdir):
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
    man = json.load(open(os.path.join(indir, "manifest.json")))
    blocks = [dict(header=bytes.fromhex(b["header"]), trailer=bytes.fromhex(b["trailer"]),
                   payload=open(os.path.join(indir, b["file"]), "rb").read()) for b in man["blocks"]]
    tail = open(os.path.join(indir, "tail.bin"), "rb").read()
    open(outpath, "wb").write(build(blocks, tail))
    return info(outpath)


def patch(src, dst, specs):
    blocks, tail = parse(open(src, "rb").read())
    for blk, off, new, expect in specs:
        p = bytearray(blocks[blk]["payload"])
        cur = bytes(p[off:off + len(new)])
        if expect is not None and cur != expect:
            raise SystemExit(f"block{blk}+0x{off:x}: found {cur.hex()}, expected {expect.hex()}; refusing")
        p[off:off + len(new)] = new
        blocks[blk]["payload"] = bytes(p)
        print(f"block{blk}+0x{off:x}: {cur.hex()} -> {new.hex()}")
    open(dst, "wb").write(build(blocks, tail))
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

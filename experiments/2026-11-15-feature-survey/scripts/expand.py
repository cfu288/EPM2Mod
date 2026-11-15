"""Expand the olycompress containers of an unpacked firmware block.

    python3 expand.py BLOCK.bin OUT.bin        (needs the `lz4` package)

A container is: 16 bytes "olycompress     ", u32 packed size, u32 raw size, 8 zero bytes, one
LZ4 block (format described in the om-emu project, src/fw/expand.mjs; this is our own code).
Main block (name ends in 0100.bin): each container is expanded in place, offsets stay valid.
Other blocks (resources): the expanded containers are written one after the other.
"""
import re, struct, sys
import lz4.block

src = open(sys.argv[1], "rb").read()
in_place = sys.argv[1].endswith("0100.bin")
out = bytearray(src) if in_place else bytearray()
for m in re.finditer(b"olycompress     ", src):
    h = m.start()
    packed, raw_size = struct.unpack_from("<2I", src, h + 16)
    raw = lz4.block.decompress(src[h + 32:h + 32 + packed], uncompressed_size=raw_size)
    if in_place:
        out[h:h + raw_size] = raw
    else:
        out += raw + b"\0" * (-len(raw) % 16)
open(sys.argv[2], "wb").write(out)

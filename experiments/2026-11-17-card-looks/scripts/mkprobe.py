"""Write the card files of the probe harness (build debug-log-card-probe; design.md section 8).

    python3 experiments/2026-11-17-card-looks/scripts/mkprobe.py OUTDIR

An LKP1 file is "LKP1", u16 record count, u16 flags (bit 0: make the look stages recompute), then records
{u32 address, u16 length, u16 0, the bytes, padded to 4}, little-endian. The camera writes a record only when it
lies inside one of the tables of the Pale&Light Color slot (Pro 400H). Copy one file to the card root as
EPM2LOOK.BIN; it is applied once per session, at the first menu, playback or power-off.

Files (each changes one thing of the Pro 400H look, so a photo shows whether it took effect):
  sat0.bin           the saturation pair 0x7E7696A4 = 0, 0 (no colour if it takes effect), no refresh
  sat0-force.bin     the same with flag bit 0: the look stages recompute
  toner0-force.bin   the red tone table 0x7F033B7C all 0 (red crushed: a cyan picture), with the refresh
  toner0.bin         the same without the refresh
  refused.bin        emulator only: a record at code (refused), then a grey matrix record (written)
  edge.bin           emulator only: a record that runs 2 bytes past the saturation pair (refused), a grey matrix
                     record (written), and a count of 4 for the 2 records the file holds (the walk stops)
"""

import os
import struct
import sys

SAT, TONE_R, MATRIX = 0x7E7696A4, 0x7F033B7C, 0x7ECB0988
GREY = struct.pack("<9h", *([77, 150, 29] * 3))


def record(address: int, data: bytes) -> bytes:
    """One record, padded to 4 bytes."""
    body = struct.pack("<IHH", address, len(data), 0) + data
    return body + b"\0" * (-len(body) % 4)


def lkp1(records: list[bytes], force: bool) -> bytes:
    """A whole file."""
    return b"LKP1" + struct.pack("<HH", len(records), 1 if force else 0) + b"".join(records)


FILES = {
    "sat0.bin": lkp1([record(SAT, b"\0" * 4)], False),
    "sat0-force.bin": lkp1([record(SAT, b"\0" * 4)], True),
    "toner0-force.bin": lkp1([record(TONE_R, b"\0" * 512)], True),
    "toner0.bin": lkp1([record(TONE_R, b"\0" * 512)], False),
    "refused.bin": lkp1([record(0x7E421020, b"\xcb" * 4), record(MATRIX, GREY)], False),
    "edge.bin": b"LKP1" + struct.pack("<HH", 4, 0) + record(SAT + 2, b"\0" * 4) + record(MATRIX, GREY),
}

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for name, data in FILES.items():
        assert len(data) <= 2048, name
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)
        print(name, len(data), "bytes")

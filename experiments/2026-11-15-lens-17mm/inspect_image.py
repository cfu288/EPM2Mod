#!/usr/bin/env python3
"""Inspect the stock 17mm F2.8 image; do not change or repackage it."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

EXPECTED = "990d94c8578da7a1c041aa3c7300e78a5b4d0d0a8fe548b3c6acdb685d0be7dc"


def inspect(path):
    image = path.read_bytes()
    if hashlib.sha256(image).hexdigest() != EXPECTED:
        raise ValueError("Input is not the inspected stock OL100211.BIN")
    header, payload, trailer = image[:32], image[32:-32], image[-32:]
    assert header[:2] == b"OL"
    assert len(payload) == struct.unpack_from("<I", header, 12)[0] == 0x30000
    assert trailer[:28] == header[:28]
    checksum = sum(struct.unpack(f"<{len(image) // 4}I", image)) & 0xFFFFFFFF
    assert checksum == 0
    base = struct.unpack_from("<I", header, 8)[0]
    # These 15 aligned patterns match JSR.A, RTS, then three NOPs if R32C.
    # Continuous decoding is in r32c.py and flow.py.
    # The R32C manual defines the displacement relative to opcode address + 1.
    stubs = []
    for offset in range(4, 0x7C, 8):
        assert payload[offset] == 0xFB
        assert payload[offset + 4 : offset + 8] == b"\xdf\x9f\x9f\x9f"
        displacement = int.from_bytes(
            payload[offset + 1 : offset + 4], "little", signed=True
        )
        target = offset + 1 + displacement
        assert 0 <= target < len(payload)
        stubs.append({"payload_offset": hex(offset), "target_offset": hex(target)})
    # These are byte-pattern references, not proven decoded instructions.
    references = []
    for offset in (0x28800, 0x29800):
        address = (base + offset) & 0xFFFFFFFF
        needle = struct.pack("<I", address)
        hits = [i for i in range(0x9400) if payload.startswith(needle, i)]
        references.append({
            "table_offset": hex(offset),
            "header_based_address": hex(address),
            "candidate_reference_offsets": [hex(i) for i in hits],
        })
    pages = []
    for offset in range(0, len(payload), 0x1000):
        count = sum(b != 0xFF for b in payload[offset : offset + 0x1000])
        if count:
            pages.append({"offset": hex(offset), "non_ff_bytes": count})
    return {
        "file": path.name,
        "sha256": EXPECTED,
        "file_bytes": len(image),
        "header_hex": header.hex(),
        "payload_bytes": len(payload),
        "header_load_address": hex(base),
        "checksum_sum_u32le": checksum,
        "payload_scrambled": False,
        "non_ff_bytes": sum(b != 0xFF for b in payload),
        "non_ff_pages": pages,
        "candidate_r32c_call_stubs": stubs,
        "table_reference_candidates": references,
        "limits": [
            "R32C decoder and focus path are in r32c.py and NOTES.md; exact MCU is unknown",
            "Partial decoder: flow.py reports gaps; outside-image calls are unresolved",
            "Driver field effects are modeled; chip bit meanings need verification",
            "No measured speed or noise improvement; no patch produced",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.image), indent=2))

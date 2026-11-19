"""Look for the HSHR geometry constants in another body's block 0 (E-P5, E-PL5 ...).

Usage: uv run python experiments/2026-11-19-movie-sampling/scripts/geom_otherbody.py BLOCK0.bin [BASE]
Prints file offsets of `mov imm,dN` encodings of 91750 (Q16 1.4) and of the HSHR sizes, and the u16 words
that follow each 'mov 1662' (the AE-parameter-set pattern of the E-PM2: 1662, 1312, ..., resize).
"""
import struct, sys

b = open(sys.argv[1], "rb").read()
base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0


def find_all(pat):
    i = b.find(pat)
    while i >= 0:
        yield i
        i = b.find(pat, i + 1)


# mov imm32,dN = fc cc+N imm32 ; mov imm16,dN = 2c+N imm16
for v in (91750, 78643, 65536):
    hits = [o for n in range(4) for o in find_all(bytes([0xFC, 0xCC + n]) + struct.pack("<I", v))]
    print(f"mov {v},dN (imm32): {len(hits)}", [hex(base + o) for o in sorted(hits)][:12])
for v in (1646, 1662, 1680, 1312, 1296, 1920, 1936, 1952):
    hits = [o for n in range(4) for o in find_all(bytes([0x2C + n]) + struct.pack("<H", v))]
    print(f"mov {v},dN (imm16): {len(hits)}", [hex(base + o) for o in sorted(hits)][:12])

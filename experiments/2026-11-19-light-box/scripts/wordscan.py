"""wordscan.py IMAGE LO HI [LO HI ...]: every byte offset of block 0 whose u32 (any of the four aliases) falls in [LO, HI)."""
import struct, sys
B = 0x7E421020
D = open(sys.argv[1], 'rb').read()
rngs = [(int(a, 16), int(b, 16)) for a, b in zip(sys.argv[2::2], sys.argv[3::2])]
alias = {'runtime': 0, 'uncached': 0x40000000, 'flash': 0x402C0020 - B, 'flash-uncached': 0x402C0020 - B + 0x40000000}
hits = []
for name, d in alias.items():
    for lo, hi in rngs:
        l, h = (lo + d) & 0xFFFFFFFF, (hi + d) & 0xFFFFFFFF
        # fast: search for the top 2 bytes of the value range
        tops = {(v >> 16) for v in (l, h - 1)} | set(range(l >> 16, ((h - 1) >> 16) + 1))
        for t in tops:
            pat = struct.pack('<H', t)
            i = D.find(pat)
            while i != -1:
                if i >= 2:
                    v = struct.unpack_from('<I', D, i - 2)[0]
                    if l <= v < h: hits.append((B + i - 2, name, hex(v - d)))
                i = D.find(pat, i + 1)
for h in sorted(set(hits)): print(hex(h[0]), h[1], h[2])
print(len(set(hits)), 'hits')

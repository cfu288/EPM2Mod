#!/usr/bin/env python3
"""List the sensor register programs of a firmware block and compare two bodies.

A program is a run of 8-byte entries {0x18000000, word}. The word is
(value << 16) | (register << 8) | length, as the serial driver of cam_imgdev sends it
(inferred from the entries: length 2 with 8-bit values, length 4 for two registers).
A program header that follows the entries is {count, pointer to the first entry}.

Usage:
    sensor_programs.py BLOCK0 BASE                 # list every program
    sensor_programs.py BLOCK0 BASE ADDR            # one program (ADDR = first entry)
    sensor_programs.py A_BLOCK0 A_BASE --cmp B_BLOCK0 B_BASE   # register use in A and B
"""
import struct
import sys


def programs(data, base):
    """Yield (address of first entry, [(reg, length, value)])."""
    out = []
    n = len(data) // 4
    words = struct.unpack_from("<%dI" % n, data, 0)
    # the block base is 0x...020, so runtime-aligned words are file-aligned too
    i = 0
    while i < n - 1:
        if words[i] == 0x18000000 and (words[i + 1] & 0xFF) in (1, 2, 3, 4):
            j = i
            ent = []
            while j < n - 1 and words[j] == 0x18000000:
                w = words[j + 1]
                ent.append(((w >> 8) & 0xFF, w & 0xFF, w >> 16))
                j += 2
            if j < n - 1 and words[j] == len(ent) and words[j + 1] == base + 4 * i:
                out.append((base + 4 * i, ent))
            i = j
        else:
            i += 1
    return out


def show(addr, ent):
    print("%08x  %2d writes: " % (addr, len(ent)) + " ".join("%02x=%0*x" % (r, 2 * (l - 1) if l > 1 else 2, v) for r, l, v in ent))


def main():
    a = sys.argv[1:]
    data = open(a[0], "rb").read()
    base = int(a[1], 16)
    pa = programs(data, base)
    if "--cmp" in a:
        k = a.index("--cmp")
        db = open(a[k + 1], "rb").read()
        pb = programs(db, int(a[k + 2], 16))
        sa = {}
        sb = {}
        for progs, s in ((pa, sa), (pb, sb)):
            for _, ent in progs:
                for r, l, v in ent:
                    s.setdefault(r, set()).add(v)
        print("programs: A %d, B %d" % (len(pa), len(pb)))
        ta = sorted(tuple(e) for _, e in pa)
        tb = sorted(tuple(e) for _, e in pb)
        print("programs with identical content in both: %d" % len(set(ta) & set(tb)))
        print("registers written: A %d, B %d, only A: %s, only B: %s" % (
            len(sa), len(sb),
            " ".join("%02x" % r for r in sorted(set(sa) - set(sb))),
            " ".join("%02x" % r for r in sorted(set(sb) - set(sa)))))
        for r in sorted(set(sa) & set(sb)):
            if sa[r] != sb[r]:
                print("  reg %02x  only A: %s   only B: %s" % (
                    r, " ".join("%x" % v for v in sorted(sa[r] - sb[r])), " ".join("%x" % v for v in sorted(sb[r] - sa[r]))))
        return
    if len(a) > 2:
        want = int(a[2], 16)
        pa = [p for p in pa if p[0] == want]
    for addr, ent in pa:
        show(addr, ent)


main()

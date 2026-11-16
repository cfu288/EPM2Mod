#!/usr/bin/env python3
"""Compare the sensor register programs of several bodies.

Usage: sensor_families.py NAME=BLOCK0 [NAME=BLOCK0 ...]

BLOCK0 is the unpacked main block of an update file (tools/oetool.py unpack).
For each body: the number of programs, the number of registers written, the values
written to register 0x01, and how many programs are byte-identical with each other body.
The block base is not needed: a program header is accepted when the low 12 bits of its
pointer match the file offset (all bodies load block 0 at an address that ends in 0x020).
"""
import struct
import sys


def programs(data):
    n = len(data) // 4
    w = struct.unpack_from("<%dI" % n, data, 0)
    out = []
    i = 0
    while i < n - 1:
        if w[i] == 0x18000000 and (w[i + 1] & 0xFF) in (1, 2, 3, 4):
            j = i
            ent = []
            while j < n - 1 and w[j] == 0x18000000:
                x = w[j + 1]
                ent.append(((x >> 8) & 0xFF, x & 0xFF, x >> 16))
                j += 2
            if j < n - 1 and w[j] == len(ent) and (w[j + 1] & 0xFFF) == ((4 * i + 0x20) & 0xFFF):
                out.append(tuple(ent))
            i = j
        else:
            i += 1
    return out


def main():
    res = {}
    for arg in sys.argv[1:]:
        name, path = arg.split("=", 1)
        p = programs(open(path, "rb").read())
        regs = {}
        for ent in p:
            for r, _, v in ent:
                regs.setdefault(r, set()).add(v)
        res[name] = (p, regs)
    names = list(res)
    print("%-8s %4s %4s  %-16s %s" % ("body", "prog", "regs", "reg 0x01 values", "identical programs with: " + " ".join(names)))
    for a in names:
        p, regs = res[a]
        same = " ".join("%*d" % (len(b), len(set(p) & set(res[b][0]))) for b in names)
        print("%-8s %4d %4d  %-16s %s" % (a, len(p), len(regs), ",".join("%02x" % v for v in sorted(regs.get(1, []))), same))


main()

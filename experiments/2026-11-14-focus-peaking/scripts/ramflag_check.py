"""Evidence that RAM 0x602BE8C4-0x602BE8C7 is unused, on one block-0 image.

The four bytes are slot 20 of the 37-slot table of menu value-list pointers at RAM 0x602BE874 (.data).
The interval patch uses slot 1 of the same table (0x602BE878) by the same argument.

Checks:
  1. every 4-byte constant in block 0 (any byte offset) whose value is inside the table: only the table base may
     occur, apart from addresses that the given spec list itself adds;
  2. the row index at each call of the two formatters that read the table (the interval work's fmtindex.py);
  3. the .data initial value of slot 20 (the .data image is copied from 0x7E8DA000 to RAM 0x602A9B40);
  4. the stock "MF Assist is running" word 0x602B0DA8: every constant reference in block 0.

Usage: ramflag_check.py BLOCK0 [LABEL]
"""
import os, struct, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
B = 0x7E421020
TAB, SLOTS, SLOT = 0x602BE874, 37, 20
d = open(sys.argv[1], "rb").read()
print("image:", sys.argv[2] if len(sys.argv) > 2 else os.path.basename(sys.argv[1]))


def consts(lo, hi):
    out = {}
    for i in range(len(d) - 3):
        if d[i + 3] == 0x60 and d[i + 2] == 0x2B:
            v = struct.unpack_from("<I", d, i)[0]
            if lo <= v < hi:
                out.setdefault(v, []).append(B + i)
    return out


c = consts(TAB, TAB + 4 * SLOTS)
print("1. constants inside the table 0x%X-0x%X:" % (TAB, TAB + 4 * SLOTS))
for v, at in sorted(c.items()):
    print("   0x%X (slot %d, byte %d) at %s" % (v, (v - TAB) // 4, (v - TAB) % 4, ", ".join("0x%X" % a for a in at)))
mine = [v for v in c if TAB + 4 * SLOT <= v < TAB + 4 * SLOT + 4]
other = [v for v in c if v not in mine and v not in (TAB, TAB + 4)]
print("   slot %d constants: %s; unexplained constants: %s" % (SLOT, ["0x%X" % v for v in sorted(mine)] or "none",
                                                              ["0x%X" % v for v in other] or "none"))
r = subprocess.run([sys.executable, os.path.join(ROOT, "experiments/2026-11-13-intervalometer/scripts/fmtindex.py"), sys.argv[1]],
                   capture_output=True, text=True, check=True).stdout.splitlines()
idx = sorted({int(l.split("mov ")[1].split(",")[0]) for l in r if "-> call" in l})
print("2. row index constants at the %d formatter calls: %s" % (sum("-> call" in l for l in r), idx))
for l in r[-2:]:
    print("   " + l)
tail = eval(r[-2].split("rows")[1])
print("   slot %d is %s" % (SLOT, "NOT indexed" if SLOT not in idx and SLOT not in tail else "INDEXED"))
off = 0x7E8DA000 - B + (TAB - 0x602A9B40)
tab = struct.unpack_from("<%dI" % SLOTS, d, off)
print("3. .data initial values: non-zero slots %s; slot %d = 0x%08X (flash 0x%X)" %
      ([i for i, v in enumerate(tab) if v], SLOT, tab[SLOT], B + off + 4 * SLOT))
m = consts(0x602B0DA8, 0x602B0DAC)
print("4. stock word 0x602B0DA8: constants at", {("0x%X" % v): ["0x%X" % a for a in at] for v, at in sorted(m.items())})

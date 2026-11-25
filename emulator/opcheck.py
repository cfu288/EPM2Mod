#!/usr/bin/env python3
"""Static checks of the ops of a whole build (all its specs, in order). No emulator.

    python3 emulator/opcheck.py data/builds/NAME.json
    python3 emulator/opcheck.py SPEC.json [SPEC.json ...]

Check 1, silent overlap. Every spec makes its `expect` bytes from the stock file. When an op of spec A ends in a
byte that equals the stock byte (0xFF, the last byte of a jump displacement, a filler), and an op of a later spec B
changes that byte, B's `expect` still matches and no other tool sees it. This happened: seven-fixes-1 wrote 17
bytes at 0x7E880FD4, the last one 0xFF (the top byte of the displacement of `jmp 0x7E56D8D8`); peaking-direct-1,
-2 and -3 put a routine at 0x7E880FE4 and turned the jump into `jmp 0x5C56D8D8`. tools/freespace.py counts only
the bytes of an op that differ from stock, so it called 0x7E880FE4 free. FAIL: a byte that an earlier spec's op
covers without changing it, changed by a later spec.

Check 2, callers that the function map cannot see. The boot code copies the sram-image of block 0 to SRAM
0x47001000 and runs it there. Its `call` instructions are pc-relative to the SRAM address, so the map (decoded at
the flash address) gives them wrong targets, and a function that only SRAM code calls looks unreferenced. This
happened: peaking-direct-3 put code over 0x7E53A55C ("pwr_standby start", called from SRAM 0x470010F7 when the
camera goes to sleep). FAIL: a constant call or jump of the SRAM code, decoded at its SRAM address, whose target is
inside an op that changes bytes. The copy's source and destination come from tools/freespace.py's load model.

Exit status 1 on any FAIL.
"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bootmem  # noqa: E402
import hookcheck  # noqa: E402

BASE = 0x7E421020
ROOT = bootmem.ROOT


def spec_list(args):
    if len(args) == 1:
        d = json.load(open(args[0]))
        if "specs" in d:
            return [os.path.join(ROOT, p) for p in d["specs"]]
    return args


def ops_of(paths):
    """[(spec name, block, offset, expect, new)] of the byte ops, in build order."""
    out = []
    for p in paths:
        for op in json.load(open(p))["ops"]:
            if op.get("type") == "bytes":
                out.append((os.path.basename(p), op.get("block", 0), int(op["offset"], 16),
                            bytes.fromhex(op["expect"]), bytes.fromhex(op["new"])))
    return out


def silent_overlaps(ops):
    """Bytes that one spec covers and leaves as they are, and a later spec changes."""
    kept = {}                                   # (block, offset) -> (spec, op offset, op length)
    hits = []
    for name, blk, off, exp, new in ops:        # build order
        for i, (e, n) in enumerate(zip(exp, new)):
            k = kept.get((blk, off + i))
            if e != n and k and k[0] != name:
                hits.append((blk, off + i, name, off, len(new), k))
        for i, (e, n) in enumerate(zip(exp, new)):
            if e == n:
                kept.setdefault((blk, off + i), (name, off, len(new)))
            else:
                kept.pop((blk, off + i), None)  # the byte now belongs to an op that changes it
    return hits


def sram_calls():
    """[(SRAM address of the instruction, mnemonic, target)] for the code that the boot copies to SRAM."""
    m = bootmem.model()
    L = next(x for x in m.loads if x.name == "sram-image")
    dst = m.f["boot_sram_copy"]["dst"]
    code = m.b[L.lo - BASE:L.hi - BASE]
    fd, p = tempfile.mkstemp(suffix=".bin")
    os.write(fd, code)
    os.close(fd)
    try:
        txt = subprocess.run([hookcheck.toolchain.binutils("objdump"), "-D", "-b", "binary", "-m", "am33-2", "-EL", "--adjust-vma=%#x" % dst, p],
                             capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(p)
    rx = re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2} )+\s*\t(jmp|call)\t(?:0x)?([0-9a-f]{8})\b")
    out = []
    for line in txt.splitlines():
        g = rx.match(line)
        if g:
            out.append((int(g.group(1), 16), g.group(2), int(g.group(3), 16)))
    return out, L.lo, dst


def check(paths, out=print):
    ops = ops_of(paths)
    fails = 0
    for blk, off, name, o_off, o_len, (kname, k_off, k_len) in silent_overlaps(ops):
        fails += 1
        where = "0x%08X" % (BASE + off) if blk == 0 else "block %d offset 0x%X" % (blk, off)
        out("FAIL  silent overlap at %s: %s (op at offset 0x%X, %d B) changes a byte that %s covers and keeps "
            "(op at offset 0x%X, %d B)" % (where, name, o_off, o_len, kname, k_off, k_len))
    calls, src, dst = sram_calls()
    changed = [(name, BASE + off, BASE + off + len(new)) for name, blk, off, exp, new in ops if blk == 0 and exp != new]
    n = 0
    for ia, mn, tgt in calls:
        if not BASE <= tgt < BASE + len(bootmem.model().b):
            continue
        n += 1
        for name, lo, hi in changed:
            if lo <= tgt < hi:
                fails += 1
                out("FAIL  SRAM code 0x%08X (flash 0x%08X): %s 0x%08X is inside the op of %s at 0x%08X-0x%08X" % (
                    ia, ia - dst + src, mn, tgt, name, lo, hi))
    out("op check: %d specs, %d byte ops, %d calls from SRAM code into block 0 looked at, %d FAIL" % (
        len(paths), len(ops), n, fails))
    return fails == 0


if __name__ == "__main__":
    sys.exit(0 if check(spec_list(sys.argv[1:])) else 1)

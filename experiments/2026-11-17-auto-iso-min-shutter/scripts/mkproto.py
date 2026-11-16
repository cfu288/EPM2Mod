#!/usr/bin/env python3
"""Assemble scripts/th.s and write specs/proto-threshold-inplace.json (a harness prototype, not a camera build).

    python3 experiments/2026-11-17-auto-iso-min-shutter/scripts/mkproto.py [WORKDIR]

WORKDIR is a scratch folder for the assembler files (default /dev/shm/aiso-asm). The binutils for mn10300 are
found as tools/disasm.py finds objdump.
"""
import hashlib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import disasm, oetool  # noqa: E402

ADDR, END, BASE = 0x7E69400C, 0x7E69403E, 0x7E421020
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else "/dev/shm/aiso-asm"
    os.makedirs(work, exist_ok=True)
    bindir = os.path.dirname(disasm.objdump_path())
    o, elf, out = (os.path.join(work, n) for n in ("th.o", "th.elf", "th.bin"))
    subprocess.check_call([bindir + "/mn10300-elf-as", "-o", o, os.path.join(HERE, "th.s")])
    subprocess.check_call([bindir + "/mn10300-elf-ld", "-Ttext=%#x" % ADDR, "-o", elf, o])
    subprocess.check_call([bindir + "/mn10300-elf-objcopy", "-O", "binary", elf, out])
    code = open(out, "rb").read()
    room = END - ADDR
    if len(code) > room:
        sys.exit(f"{len(code)} bytes do not fit in {room}")
    code += b"\xcb" * (room - len(code))                    # nop
    raw = open(os.path.join(ROOT, STOCK), "rb").read()
    blocks, _ = oetool.parse(raw)
    old = blocks[0]["payload"][ADDR - BASE:END - BASE]
    spec = {
        "name": "proto-threshold-inplace",
        "description": "HARNESS PROTOTYPE, not a camera build. The tail of the tv_th function 0x7E694001 written again "
                       "in place (50 bytes, no new code area): tv_th = max(1/(2 x focal length), Flash Slow Limit, "
                       "1/30 x 2^k), k = the byte of the dormant setting 447 at RAM 0x60413275; the X-Sync cap stays "
                       "only when the flash is on. See experiments/2026-11-17-auto-iso-min-shutter/NOTES.md.",
        "base": STOCK, "base_sha256": hashlib.sha256(raw).hexdigest(),
        "ops": [{"type": "bytes", "block": 0, "offset": "%#x" % (ADDR - BASE), "expect": old.hex(), "new": code.hex(),
                 "_addr": "%#X" % ADDR, "_note": f"{len(code)} B, {room - len(code.rstrip(bytes([0xcb])))} B of nop at the end"}],
    }
    p = os.path.join(HERE, "..", "specs", "proto-threshold-inplace.json")
    json.dump(spec, open(p, "w"), indent=1)
    print("wrote", os.path.relpath(p, ROOT), len(code), "bytes")


if __name__ == "__main__":
    main()

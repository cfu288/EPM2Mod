#!/usr/bin/env python3
"""Disassemble part of a firmware block with GNU objdump (mn10300/am33-2).

    python3 tools/disasm.py 0x2CCEC0 --len 0x80            # block-0 file offset
    python3 tools/disasm.py 0x7E6EDEE0 --len 0x80          # runtime address (auto-detected: >= base)
    python3 tools/disasm.py 0x2CCEC0 --before 0x40         # start 0x40 bytes earlier

Notes:
- MN103 has variable-length instructions, so starting mid-instruction gives garbage until it resyncs.
  Use --before to start earlier, and trust output only after the first clean line.
- The runtime base (BASE) is an estimate from a string-pointer scan (see docs/firmware-format.md).
"""
import argparse, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import oetool  # noqa: E402

DEFAULT_FW = os.path.join(ROOT, "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN")
BASE = 0x7E421020  # E-PM2 v1.6 block 0 runtime base (estimate)
OBJDUMP_CANDIDATES = [os.path.expanduser("~/opt/mn10300/bin/mn10300-elf-objdump"), "mn10300-elf-objdump"]


def objdump_path():
    for c in OBJDUMP_CANDIDATES:
        p = shutil.which(c) or (c if os.path.exists(c) else None)
        if p:
            return p
    sys.exit("mn10300 objdump not found; run scripts/build-binutils-mn10300.sh")


def block_file(fw, blk):
    cache = os.path.join(ROOT, "build", "blocks", f"{os.path.basename(fw)}.block{blk}.bin")
    if not os.path.exists(cache) or os.path.getmtime(cache) < os.path.getmtime(fw):
        blocks, _ = oetool.parse(open(fw, "rb").read())
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        open(cache, "wb").write(blocks[blk]["payload"])
    return cache


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("where", help="block file offset or runtime address (hex ok)")
    ap.add_argument("--len", default="0x100")
    ap.add_argument("--before", default="0")
    ap.add_argument("--fw", default=DEFAULT_FW)
    ap.add_argument("--block", type=int, default=0)
    ap.add_argument("--base", default=hex(BASE))
    ap.add_argument("--arch", default="am33-2")
    a = ap.parse_args()
    base = int(a.base, 0)
    where = int(a.where, 0)
    off = where - base if where >= base else where
    start = max(0, off - int(a.before, 0))
    stop = off + int(a.len, 0)
    print(f"; block{a.block} offset {off:#x} = runtime {base + off:#x} (base {base:#x})", file=sys.stderr)
    cmd = [objdump_path(), "-D", "-b", "binary", "-m", a.arch, "-EL",
           f"--adjust-vma={base:#x}", f"--start-address={base + start:#x}", f"--stop-address={base + stop:#x}",
           block_file(a.fw, a.block)]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()

"""Disassemble ranges of a block-0 file at their run-time addresses (MN103, build/toolchain's objdump).

Usage (from the repository root):
    uv run python experiments/2026-11-24-slow-boot/scripts/disasm_ranges.py BLOCK0.bin 0xADDR:LEN [0xADDR:LEN ...]
"""

import os
import subprocess
import sys
import tempfile

BASE = 0x7E421020
OBJDUMP = os.path.join("build", "toolchain", "bin", "mn10300-elf-objdump")
block = open(sys.argv[1], "rb").read()
for arg in sys.argv[2:]:
    a, n = (int(x, 0) for x in arg.split(":"))
    with tempfile.NamedTemporaryFile(suffix=".bin") as f:
        f.write(block[a - BASE : a - BASE + n])
        f.flush()
        out = subprocess.run(
            [OBJDUMP, "-D", "-b", "binary", "-m", "am33-2", "-EL", f"--adjust-vma={a:#x}", f.name],
            capture_output=True, text=True, check=True,
        ).stdout
    print(f"== {a:#010x} +{n}")
    print("\n".join(line for line in out.splitlines() if line.startswith("7")))

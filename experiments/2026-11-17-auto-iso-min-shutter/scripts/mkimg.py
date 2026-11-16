#!/usr/bin/env python3
"""Make a folder of unpacked blocks for the full-boot emulator: stock (or another unpacked folder) + prototype specs.

    python3 experiments/2026-11-17-auto-iso-min-shutter/scripts/mkimg.py OUTDIR SPEC.json [SPEC.json ...]
    tools/emu/emu-run OUTDIR play.mjs ...

Only `bytes` ops; each `expect` is checked. The source folder is `tools/emu/emu-run --blocks stock`
(or the folder in the environment variable SRC_BLOCKS). Put OUTDIR in a scratch folder, not in the repository.
"""
import glob, json, os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def main():
    out, specs = sys.argv[1], sys.argv[2:]
    src = os.environ.get("SRC_BLOCKS") or subprocess.check_output(
        [sys.executable, os.path.join(ROOT, "tools/emu/emu-run"), "--blocks", "stock"], text=True).strip()
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(src, out)
    for sp in specs:
        for op in json.load(open(sp))["ops"]:
            if op["type"] != "bytes":
                sys.exit(f"{sp}: op type {op['type']} not handled")
            f = glob.glob(os.path.join(out, f"block{op['block']}_*.bin"))[0]
            off, new, exp = int(op["offset"], 0), bytes.fromhex(op["new"]), bytes.fromhex(op["expect"])
            with open(f, "r+b") as h:
                h.seek(off)
                if h.read(len(exp)) != exp:
                    sys.exit(f"{sp}: expect mismatch at block {op['block']} {op['offset']}")
                h.seek(off)
                h.write(new)
    print("wrote", out)


if __name__ == "__main__":
    main()

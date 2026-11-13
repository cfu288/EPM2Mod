#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Apply patch specs to the stock firmware (the older command-line form).

    python3 tools/build.py SPEC [SPEC ...] [-o build/NAME.BIN]

The work is done by the `epm2mod` package (src/epm2mod/spec.py); the spec format is described
there. This file keeps the command and the two functions that older scripts in tools/ and
experiments/ call: `apply_op(blocks, op)` and `build(spec_paths, out)`.

To make firmware for a camera, use tools/make_firmware.py with a build description.
"""
import argparse
import os
import sys

import _package  # noqa: F401
from epm2mod.container import describe
from epm2mod.errors import Epm2ModError
from epm2mod.fileio import read_bytes, write_bytes
from epm2mod.hashing import sha256_bytes
from epm2mod.spec import apply_op as _apply_op
from epm2mod.spec import apply_specs, load_spec, op_from_json
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def apply_op(blocks, op):
    """Apply one operation (its JSON form) to blocks in the form `oetool.parse` returns.

    Exits with a message if the operation does not fit, as the older tool did.
    """
    payloads = [bytearray(block["payload"]) for block in blocks]
    try:
        line = _apply_op(payloads, op_from_json(op, "op"))
    except Epm2ModError as error:
        raise SystemExit(str(error)) from None
    blocks[op["block"]]["payload"] = bytes(payloads[op["block"]])
    print("  " + line)


def build(spec_paths, out=None):
    """Apply specs to the stock firmware and write the result. Return True if all checks pass.

    If there is one spec and it has an `expected_sha256` that the result does not have, nothing
    is written and the return value is False.
    """
    try:
        specs = [load_spec(Path(path)) for path in spec_paths]
        bases = {spec.base for spec in specs}
        if len(bases) != 1:
            raise SystemExit(f"specs use different bases: {sorted(bases)}")
        stock = read_bytes(Path(ROOT) / specs[0].base)
        applied = apply_specs(stock, specs)
    except Epm2ModError as error:
        raise SystemExit(str(error)) from None
    print("\n".join(applied.log))
    digest = sha256_bytes(applied.image)
    lines = describe(applied.image)
    out = out or os.path.join(ROOT, "build", "+".join(spec.name for spec in specs) + ".BIN")
    print(f"{out}  size={len(applied.image)}  sha256={digest}")
    print("\n".join("  " + line for line in lines))
    if len(specs) == 1 and specs[0].expected_sha256:
        if digest != specs[0].expected_sha256:
            print("expected_sha256: MISMATCH; nothing was written")
            return False
        print("expected_sha256: MATCH")
    try:
        write_bytes(Path(out), applied.image)
    except Epm2ModError as error:
        raise SystemExit(str(error)) from None
    print(f"wrote {os.path.relpath(out, ROOT)}  ({applied.changed_bytes} bytes differ from base)")
    print("flash as DCOLYMP/E1019999.BIN")
    return all("checksum=BAD" not in line for line in lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("specs", nargs="+")
    parser.add_argument("-o", "--out")
    arguments = parser.parse_args()
    sys.exit(0 if build(arguments.specs, arguments.out) else 1)

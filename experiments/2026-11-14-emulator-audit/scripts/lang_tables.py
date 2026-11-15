"""Print the text tables of block 1 and the film-name ids in every language.

Run from the repository root:

    .venv/bin/python experiments/2026-11-14-emulator-audit/scripts/lang_tables.py BUILD.BIN [--ids 60,61,764]

Per language: directory entry, language code, block offset of the blob and of the pointer array,
the format checks, and the text of each id. Without --ids: the 16 film-name ids and id 764.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from film_names_spec import BLOCK1_LOAD, EFFECT_ID, IDS, N_IDS, RUNTIME, Blob  # noqa: E402

from epm2mod.container import parse  # noqa: E402


def main() -> None:
    """Print the tables."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("firmware")
    parser.add_argument("--ids", default=",".join(str(i) for i in [*sorted(IDS), EFFECT_ID]))
    args = parser.parse_args()
    ids = [int(i) for i in args.ids.split(",")]
    data = parse(Path(args.firmware).read_bytes()).blocks[1].payload
    for entry in range(1, 35):
        blob = Blob(data, entry)
        address, size = struct.unpack_from("<2I", data, 16 * entry)
        order = sorted(range(N_IDS), key=lambda i: blob.pointers[i])
        ends = {blob.offset(i) + 2 * (len(blob.text(i)) + 1) for i in range(N_IDS)}
        packed = sum(blob.offset(i) in ends for i in range(N_IDS))  # strings that start where another ends
        facts = [
            f"entry {entry} {blob.code}",
            f"directory {address - BLOCK1_LOAD:#x}+{size:#x}",
            f"blob {blob.head:#x}",
            f"pointers {blob.array:#x}",
            "pool in id order" if order == list(range(N_IDS)) else "pool NOT in id order",
            f"{packed + 1} of {N_IDS} strings follow another with no gap",
            f"first pointer {blob.pointers[0] - RUNTIME:#x}",
        ]
        print("; ".join(facts))
        for string_id in ids:
            print(f"  {string_id}\t{blob.offset(string_id):#x}\t{blob.text(string_id)!r}")


if __name__ == "__main__":
    main()

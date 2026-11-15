"""Make a test image that shows which string id a screen uses: each film-name id reads "id<N>".

Run from the repository root, on an unpacked block 1 (tools/oetool.py unpack BUILD.BIN /tmp/scratch/idtag):

    .venv/bin/python experiments/2026-11-14-emulator-audit/scripts/id_tags.py /tmp/scratch/idtag/block1_0101.bin

Only the English table is changed, in place. The file is for the emulator only. Do not build firmware from it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from film_names_spec import ENGLISH, ICON, IDS, Blob  # noqa: E402

path = Path(sys.argv[1])
data = bytearray(path.read_bytes())
blob = Blob(bytes(data), ENGLISH)
for string_id in IDS:
    old = blob.text(string_id)
    new = (old[:ICON] if old.startswith("@") else "") + f"id{string_id}"
    if len(new) > len(old):
        raise SystemExit(f"id {string_id}: {new!r} does not fit {old!r}")
    raw = (new + "\0" * (len(old) - len(new))).encode("utf-16-le")
    data[blob.offset(string_id) : blob.offset(string_id) + len(raw)] = raw
path.write_bytes(data)
print("tagged ids:", ", ".join(str(i) for i in sorted(IDS)))

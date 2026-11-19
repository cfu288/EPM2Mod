"""Helpers that the test modules share."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from epm2mod import container  # noqa: E402
from epm2mod.paths import MANIFEST  # noqa: E402


def write_manifest(folder: Path, **changes: Any) -> Path:
    """Write into ``folder`` the checkout's project manifest with ``changes``; return the folder."""
    raw = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8")) | changes
    folder.mkdir(parents=True, exist_ok=True)
    (folder / MANIFEST).write_text(json.dumps(raw, indent=1) + "\n", encoding="utf-8")
    return folder


def make_container(payloads: list[bytes], tail: bytes = b"TAIL") -> bytes:
    """Return a valid firmware container with the given unscrambled payloads.

    Block ``i`` gets the load address ``0x1000 * (i + 1)`` and the kind
    ``0x0100 + i``. Every header names the E-PM2's model, ``10 10``.
    """
    blocks = []
    for index, payload in enumerate(payloads):
        header = bytearray(container.HEADER_SIZE)
        header[0:2] = container.MAGIC
        header[2:4] = b"\x10\x10"
        struct.pack_into("<I", header, 8, 0x1000 * (index + 1))
        struct.pack_into("<I", header, 12, len(payload))
        struct.pack_into("<H", header, 20, 0x0100 + index)
        trailer = bytes(header[:28]) + bytes(4)
        blocks.append(container.Block(0, bytes(header), trailer, payload, False))
    return container.serialize(container.Container(tuple(blocks), tail))

"""SHA-256 helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

_BLOCK_SIZE = 1 << 20


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 of ``data`` as lower-case hexadecimal."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file as lower-case hexadecimal.

    The file is read in blocks, so its size does not matter.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_BLOCK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()

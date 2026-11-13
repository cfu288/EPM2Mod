"""SHA-256 helpers."""

from __future__ import annotations

import hashlib
import re

_SHA256 = re.compile(r"[0-9a-f]{64}")


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 of ``data`` as lower-case hexadecimal."""
    return hashlib.sha256(data).hexdigest()


def is_sha256(text: object) -> bool:
    """Return True if ``text`` is a SHA-256 written as 64 lower-case hexadecimal digits."""
    return isinstance(text, str) and _SHA256.fullmatch(text) is not None

"""File reading and writing with the package's guarantees.

Two rules hold for every file the package writes:

* **All or nothing.** Data goes to a temporary file in the same folder, is
  flushed to the device, and only then takes the final name. A failure removes
  the temporary file. The final name therefore never holds a part of a file,
  and a file that was there before stays until the new one is complete.
* **No bare ``OSError``.** A failure is reported as a ``FileError`` (or the
  error type the caller asks for) with the path in the message.

Text is written as UTF-8 with ``\\n`` line ends on every platform.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from .errors import Epm2ModError, FileError

#: A function that takes one line of progress text.
Log = Callable[[str], None]

#: How many bytes are read or written at a time.
BLOCK_SIZE = 1 << 20

_PART_SUFFIX = ".part"


def silent(line: str) -> None:
    """Discard a line of progress text."""


def _describe(error: OSError) -> str:
    """Return the reason of an ``OSError`` as text."""
    return error.strerror or str(error)


def read_bytes(path: Path, error: type[Epm2ModError] = FileError) -> bytes:
    """Return the content of a file.

    Raises:
        Epm2ModError: of type ``error``, if the file cannot be read.
    """
    try:
        return path.read_bytes()
    except OSError as reason:
        raise error(f"{path}: cannot be read: {_describe(reason)}") from None


def read_text(path: Path, error: type[Epm2ModError] = FileError) -> str:
    """Return the content of a UTF-8 text file, with its line ends unchanged.

    Raises:
        Epm2ModError: of type ``error``, if the file cannot be read or is not UTF-8.
    """
    try:
        return read_bytes(path, error).decode("utf-8")
    except UnicodeDecodeError as reason:
        raise error(f"{path}: is not UTF-8 text: {reason}") from None


def read_json(path: Path, error: type[Epm2ModError] = FileError) -> Any:
    """Return the parsed content of a JSON file.

    Raises:
        Epm2ModError: of type ``error``, if the file cannot be read or is not JSON.
    """
    text = read_text(path, error)
    try:
        return json.loads(text)
    except ValueError as reason:
        raise error(f"{path}: not JSON: {reason}") from None


def part_path(path: Path) -> Path:
    """Return the temporary name that ``write_bytes`` uses for ``path``."""
    return path.with_name(path.name + _PART_SUFFIX)


def _sync_folder(folder: Path) -> None:
    """Flush a folder's entry table to the device, where the platform can."""
    if not hasattr(os, "O_DIRECTORY"):
        return
    try:
        handle = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)


def write_bytes(path: Path, data: bytes, error: type[Epm2ModError] = FileError) -> None:
    """Write a file, all or nothing, and flush it to the device.

    The folder is made if it is missing.

    Raises:
        Epm2ModError: of type ``error``, if the file cannot be written. The
            final name is untouched then.
    """
    temporary = part_path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _sync_folder(path.parent)
    except OSError as reason:
        remove(temporary)
        raise error(f"{path}: cannot be written: {_describe(reason)}") from None


def write_text(path: Path, text: str, error: type[Epm2ModError] = FileError) -> None:
    """Write a UTF-8 text file, all or nothing, with the line ends as given."""
    write_bytes(path, text.encode("utf-8"), error)


def write_json(path: Path, raw: Any, error: type[Epm2ModError] = FileError) -> None:
    """Write JSON with the repository's layout: one-space indent, final newline."""
    write_text(path, json.dumps(raw, indent=1) + "\n", error)


def remove(path: Path) -> None:
    """Remove a file if it is there. A file that cannot be removed is left."""
    try:
        path.unlink()
    except OSError:
        pass

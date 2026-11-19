"""File reading and writing with the package's guarantees.

Two rules hold for every file the package writes:

* **All or nothing.** Data goes to a temporary file in the same folder, is
  flushed to the device, and only then takes the final name. A failure removes
  the temporary file. The final name therefore never holds a part of a file,
  and a file that was there before stays until the new one is complete. The
  last step, a flush of the folder, comes after the rename: if it fails, the
  error says that the final name already holds the new data.
* **No bare ``OSError``.** A failure is reported as a ``FileError`` (or the
  error type the caller asks for) with the path in the message.

Text is written as UTF-8 with the line ends it is given, on every platform.
"""

from __future__ import annotations

import errno
import json
import os
from pathlib import Path
from typing import Any, Callable

from .errors import Epm2ModError, FileError, NotFoundError

#: A function that takes one line of progress text.
Log = Callable[[str], None]

_PART_SUFFIX = ".part"
#: Reasons for which a folder cannot be flushed on some platforms and file
#: systems. They do not mean that data was lost.
_NO_FOLDER_SYNC = {
    errno.EINVAL,
    errno.ENOTSUP,
    errno.EBADF,
    errno.EACCES,
    errno.EPERM,
    errno.EISDIR,
}


def silent(line: str) -> None:
    """Discard a line of progress text."""


def describe_os_error(error: OSError) -> str:
    """Return the reason of an ``OSError`` as text."""
    return error.strerror or str(error)


def read_bytes(path: Path, error: type[Epm2ModError] = FileError) -> bytes:
    """Return the content of a file.

    Raises:
        Epm2ModError: of type ``error``, if the file cannot be read; its exit status is not-found (3) if the file
            does not exist.
    """
    try:
        return path.read_bytes()
    except FileNotFoundError as reason:
        missing = error(f"{path}: cannot be read: {describe_os_error(reason)}")
        missing.exit_status, missing.code = (
            NotFoundError.exit_status,
            NotFoundError.code,
        )
        raise missing from None
    except OSError as reason:
        raise error(f"{path}: cannot be read: {describe_os_error(reason)}") from None


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
        return json.loads(text, object_pairs_hook=_no_duplicates)
    except (ValueError, RecursionError) as reason:
        raise error(f"{path}: not JSON: {reason}") from None


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Return a JSON object as a dict, or raise if it gives a key twice."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"the key '{key}' is there twice")
        result[key] = value
    return result


def part_path(path: Path) -> Path:
    """Return the temporary name that ``write_bytes`` uses for ``path``."""
    return path.with_name(path.name + _PART_SUFFIX)


def sync_folder(folder: Path) -> None:
    """Flush a folder's entry table to the device, where the platform can.

    Raises:
        OSError: if the flush fails for a reason that can mean lost data (for
            example an input/output error or a full device). A platform or
            file system that cannot flush a folder is not an error.
    """
    if not hasattr(os, "O_DIRECTORY"):
        return
    try:
        handle = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as reason:
        if reason.errno in _NO_FOLDER_SYNC:
            return
        raise
    try:
        os.fsync(handle)
    except OSError as reason:
        if reason.errno not in _NO_FOLDER_SYNC:
            raise
    finally:
        os.close(handle)


def write_bytes(
    path: Path,
    data: bytes,
    error: type[Epm2ModError] = FileError,
    *,
    read_back: bool = False,
    flush_folder: bool = True,
) -> None:
    """Write a file, all or nothing, and flush it to the device.

    The folder is made if it is missing. The temporary file is always a new
    file: something that already has its name is removed first, and a symbolic
    link there is not followed.

    Args:
        path: the file to write.
        data: its content.
        error: the type of error to raise.
        read_back: if True, the temporary file is read again after the flush
            and must hold ``data`` before it takes the final name. The read
            goes through the operating system, which may answer from its own
            memory: it shows that the device accepted the data, not that the
            device stores it without error.
        flush_folder: if False, the folder is not flushed after the rename.
            The caller then calls ``sync_folder`` itself, to report a failure
            of that last step in its own words.

    Raises:
        Epm2ModError: of type ``error``, if the file cannot be written or the
            data read back differs. The final name is untouched then, with one
            exception: if the flush of the folder fails after the new file took
            its name, the final name holds the new, complete data and the
            message says so.
    """
    if not path.name:
        raise error(f"{path}: is not a file name")
    temporary = part_path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        remove(temporary)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        with os.fdopen(os.open(temporary, flags, 0o666), "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if read_back and temporary.read_bytes() != data:
            raise error(f"{path}: the data read back differs from the data written")
        os.replace(temporary, path)
    except OSError as reason:
        raise error(f"{path}: cannot be written: {describe_os_error(reason)}") from None
    finally:
        remove(temporary)
    if not flush_folder:
        return
    try:
        sync_folder(path.parent)
    except OSError as reason:
        raise error(
            f"{path}: holds the new data, but the folder could not be flushed "
            f"to the device: {describe_os_error(reason)}"
        ) from None


def write_text(path: Path, text: str, error: type[Epm2ModError] = FileError) -> None:
    """Write a UTF-8 text file, all or nothing, with the line ends as given.

    Raises:
        Epm2ModError: of type ``error``, as ``write_bytes``, and if the text
            cannot be written as UTF-8.
    """
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError as reason:
        raise error(f"{path}: the text cannot be written as UTF-8: {reason}") from None
    write_bytes(path, data, error)


def write_json(path: Path, raw: Any, error: type[Epm2ModError] = FileError) -> None:
    """Write JSON with the repository's layout: one-space indent, final newline."""
    write_text(path, json.dumps(raw, indent=1) + "\n", error)


def remove(path: Path) -> None:
    """Remove a file if it is there. A file that cannot be removed is left."""
    try:
        path.unlink()
    except OSError:
        pass

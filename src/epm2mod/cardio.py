"""Writing to an SD card: the checks, the write, the read-back and the eject. Every command that writes to a card uses it.

Rules (``plan`` checks them before anything is written; ``write`` does the work):

- The folder must be a camera card: a card that ``cards.cards`` lists (removable, FAT or exFAT) with a ``DCIM``
  folder, which the camera makes when it formats the card. Else ``CardError`` (exit status 5).
- The card must have room for the new files, less the files they replace.
- The camera's updater needs the firmware to be the only file in ``DCOLYMP``. Every other file there (the ``._``
  files that macOS writes, a temporary file of an interrupted run, any other file) is removed when the firmware is
  written. A folder in ``DCOLYMP`` stops the write: it is not removed.
- Each file goes to a temporary name, is flushed to the card, takes its name, and is read back from the card: the
  sha256 of what is read must be the sha256 of what was written (``CheckError``, exit status 4).
- Firmware whose model is not the E-PM2 is refused (``check_model``): the updater would accept an E-PL5 file.
- No backup files go on the card: they would break the one-file rule of ``DCOLYMP``.
- ``eject`` ejects the card after the write.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import cards as card_list
from .container import parse
from .errors import CardError, CheckError, ContainerError, Epm2ModError
from .fileio import describe_os_error, read_bytes, write_bytes
from .hashing import sha256_bytes
from .looks.lookfile import CARD_NAME
from .stock import CARD_FOLDER, EPM2_V16

#: The firmware file's path on the card.
FIRMWARE = f"{CARD_FOLDER}/{EPM2_V16.card_name}"
#: The film file's path on the card.
FILMS = CARD_NAME
#: The folder that the camera makes on a card it formats.
CAMERA_FOLDER = "DCIM"
#: The model bytes of each block header of E-PM2 firmware (an E-PL5 file has 10 00).
MODEL_BYTES = bytes.fromhex(EPM2_V16.model_id)
#: How the roles of the files are named in results.
ROLES = {FIRMWARE: "firmware", FILMS: "films"}


@dataclass(frozen=True)
class Content:
    """The content of a file that is written, or, for ``--dry-run``, what is known of it before it is made.

    Attributes:
        size: its size in bytes (for a dry run, the expected size).
        sha256: its sha256, or None if it is not known before the file is made.
        data: the bytes, or None in a dry run.
    """

    size: int
    sha256: str | None
    data: bytes | None = None

    @classmethod
    def of(cls, data: bytes) -> Content:
        """Return the content of ``data``."""
        return cls(len(data), sha256_bytes(data), data)


@dataclass(frozen=True)
class Planned:
    """A file that a command writes (or, with ``--dry-run``, would write).

    Attributes:
        path: where it goes.
        role: ``firmware`` or ``films``.
        content: what it holds.
        replaces: True if a file of that name is there already.
    """

    path: Path
    role: str
    content: Content
    replaces: bool

    def to_json(self) -> dict[str, Any]:
        """Return the file for ``--json``."""
        return {
            "path": str(self.path),
            "role": self.role,
            "size": self.content.size,
            "sha256": self.content.sha256,
            "replaced": self.replaces,
        }


def planned_file(path: Path, role: str, content: Content) -> Planned:
    """Return a file that is written outside a card (``-o PATH``)."""
    return Planned(path, role, content, path.is_file())


@dataclass(frozen=True)
class Plan:
    """What a write to a card does.

    Attributes:
        card: the card's top folder.
        files: the files that are written, in order.
        removed: the extra files in ``DCOLYMP`` that are removed.
    """

    card: Path
    files: tuple[Planned, ...]
    removed: tuple[Path, ...]


def is_card(folder: Path) -> bool:
    """Return True if ``cards.cards`` lists ``folder`` as an SD card."""
    try:
        wanted = folder.resolve()
        return any(card.path.resolve() == wanted for card in card_list.cards())
    except OSError:
        return False


def check_model(firmware: bytes) -> None:
    """Refuse firmware that is not for the E-PM2.

    Raises:
        CheckError: if a block header names another model, or the data is not a firmware container.
    """
    try:
        blocks = parse(firmware).blocks
    except ContainerError as error:
        raise CheckError(f"the firmware is not a firmware file: {error}") from None
    models = {block.header[2:4] for block in blocks}
    if models != {MODEL_BYTES}:
        found = ", ".join(sorted(model.hex(" ") for model in models))
        raise CheckError(
            f"the firmware is not for the E-PM2 (model {found}, the E-PM2 is "
            f"{MODEL_BYTES.hex(' ')}); nothing was written"
        )


def output_path(text: str, usual_name: str) -> Path:
    """Return the file that ``-o PATH`` names (rule 1 of the command line).

    An existing folder, or a path that ends in a slash, gets the usual file name; anything else is the file.

    Raises:
        Epm2ModError: if the text is empty.
    """
    if not text:
        raise Epm2ModError("-o needs a path")
    path = Path(text)
    if text.endswith(("/", os.sep)) or path.is_dir():
        return path / usual_name
    return path


def _extra_files(card: Path) -> list[Path]:
    """Return the files in ``DCOLYMP`` that are not the firmware file.

    Raises:
        CardError: if the folder cannot be read or holds a folder.
    """
    folder = card / CARD_FOLDER
    if not folder.is_dir():
        return []
    try:
        entries = sorted(folder.iterdir())
    except OSError as error:
        raise CardError(
            f"{folder}: cannot be read: {describe_os_error(error)}"
        ) from None
    folders = [entry.name for entry in entries if entry.is_dir()]
    if folders:
        raise CardError(
            f"{folder} holds a folder ({', '.join(folders[:4])}). The firmware must be the only file there. "
            "Move it away and run this again."
        )
    return [entry for entry in entries if entry.name != EPM2_V16.card_name]


def plan(
    card: Path,
    files: dict[str, Content],
    is_card: Callable[[Path], bool] = is_card,
) -> Plan:
    """Check a card and return what a write of ``files`` (by their path on the card) does.

    Nothing is written. The extra files in ``DCOLYMP`` are removed only if the firmware is written.

    Raises:
        CardError: if the folder is not a camera card or has no room.
        CheckError: if the firmware is not for the E-PM2.
    """
    card = card.absolute()
    if not card.is_dir():
        raise CardError(f"{card}: no such folder (the top folder of the SD card)")
    if not is_card(card):
        raise CardError(
            f"{card}: is not an SD card in this computer ('epm2mod cards' lists them)"
        )
    if not (card / CAMERA_FOLDER).is_dir():
        raise CardError(
            f"{card}: has no {CAMERA_FOLDER} folder. Format the card in the camera first, then run this again."
        )
    firmware = files.get(FIRMWARE)
    if firmware is not None and firmware.data is not None:
        check_model(firmware.data)
    planned = []
    replaced_bytes = 0
    for name, content in files.items():
        target = card / name
        replaces = target.is_file()
        if replaces:
            replaced_bytes += target.stat().st_size
        planned.append(Planned(target, ROLES.get(name, "file"), content, replaces))
    removed = _extra_files(card) if FIRMWARE in files else []
    need = sum(content.size for content in files.values()) - replaced_bytes
    try:
        free = shutil.disk_usage(card).free
    except OSError as error:
        raise CardError(f"{card}: cannot be read: {describe_os_error(error)}") from None
    if need > free:
        raise CardError(
            f"{card}: the card is full ({free} bytes free, {need} needed). Make room on it, then run this again."
        )
    return Plan(card, tuple(planned), tuple(removed))


def write_file(target: Path, data: bytes) -> None:
    """Write one file to the card: a temporary name, a flush, the final name, then a read-back of its sha256.

    Raises:
        CardError: if the card cannot take the file.
        CheckError: if what is read back is not what was written.
    """
    try:
        write_bytes(target, data, CardError, read_back=True)
    except CardError as error:
        raise CardError(
            f"{error}\nThe new file is NOT on the card. If the card holds a {target.name}, it is an older file."
        ) from None
    if sha256_bytes(read_bytes(target, CardError)) != sha256_bytes(data):
        raise CheckError(
            f"{target}: what the card gives back is not what was written. Do not use the card."
        )


def write(plan: Plan) -> None:
    """Do a write that ``plan`` returned: remove the extra files of ``DCOLYMP``, then write each file.

    Raises:
        CardError: if a file cannot be removed or written.
        CheckError: if a read-back differs.
    """
    for extra in plan.removed:
        try:
            extra.unlink()
        except FileNotFoundError:
            pass
        except OSError as error:
            raise CardError(
                f"{extra}: cannot be removed: {describe_os_error(error)}"
            ) from None
    for planned in plan.files:
        if planned.content.data is None:
            raise ValueError(f"{planned.path}: a plan of a dry run cannot be written")
        write_file(planned.path, planned.content.data)


def eject(card: Path) -> None:
    """Eject the card, so it can be taken out.

    Raises:
        CardError: if the system does not eject it.
    """
    if sys.platform == "darwin":
        command = ["diskutil", "eject", str(card)]
    elif sys.platform == "win32":
        drive = str(card)[:2]
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "(New-Object -ComObject Shell.Application).Namespace(17).ParseName("
            f"'{drive}').InvokeVerb('Eject')",
        ]
    else:
        command = ["udisksctl", "unmount", "--block-device", _linux_device(card)]
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise CardError(f"{card}: cannot be ejected: {error}") from None
    if done.returncode != 0:
        reason = (done.stderr or done.stdout).strip() or f"exit {done.returncode}"
        raise CardError(f"{card}: cannot be ejected: {reason}")


def _linux_device(card: Path) -> str:
    """Return the device that is mounted at ``card`` on Linux (``findmnt``), or the folder if it is not known."""
    try:
        done = subprocess.run(
            ["findmnt", "-n", "-o", "SOURCE", "--target", str(card)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return str(card)
    return done.stdout.strip() or str(card)

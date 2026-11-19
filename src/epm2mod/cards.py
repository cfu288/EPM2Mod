"""The SD cards plugged into this computer (``epm2mod cards``).

A card is a mounted volume on a removable or external device with a FAT or exFAT file system, the file systems the
camera uses. Fixed disks are never listed, so a user who picks from this list can't write the firmware to one.

- macOS: each folder of ``/Volumes``, checked with ``diskutil info -plist``.
- Windows: each drive letter of the type ``DRIVE_REMOVABLE``.
- Linux: ``lsblk``, a device with RM or HOTPLUG set, or an SD slot (``mmcblk``) that does not hold the system.

The local app lists cards with the same function.
"""

from __future__ import annotations

import json
import os
import plistlib
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The file systems of a camera's card, as each system names them.
_FAT = {"vfat", "fat", "fat16", "fat32", "msdos", "exfat"}

#: Mount points of a Linux system's own partitions; an SD slot that holds one is the system disk.
_SYSTEM_MOUNTS = ("/", "/boot", "/boot/efi", "/boot/firmware", "/efi", "/home")


@dataclass(frozen=True)
class Card:
    """A mounted SD card.

    Attributes:
        path: the card's top folder.
        name: the volume's name, or "" when it has none.
        size: the card's size in bytes.
        free: the free space in bytes.
    """

    path: Path
    name: str
    size: int
    free: int


def _is_fat(file_system: str) -> bool:
    """Return True for a FAT or exFAT file system name."""
    return file_system.strip().lower() in _FAT


def _card(path: Path, name: str) -> Card | None:
    """Return the card at a mounted folder, or None if its size can't be read."""
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    return Card(path, name, usage.total, usage.free)


def linux_mounts(lsblk: str) -> list[tuple[Path, str]]:
    """Return the mount points and names of the cards in ``lsblk -J`` output.

    The output needs the columns NAME, RM, HOTPLUG, FSTYPE, LABEL and MOUNTPOINT. A partition counts as on a card
    when it or its disk is removable or hot-plugged, or its disk is an SD slot (``mmcblk``) that holds none of the
    system's mount points.
    """
    out: list[tuple[Path, str]] = []

    def flag(value: Any) -> bool:
        """Return the truth of an lsblk flag (true, "1" or 1)."""
        return value in (True, 1, "1", "true")

    def walk(devices: list[Any], parent: dict[str, Any] | None) -> Iterator[Any]:
        """Yield each device with its disk."""
        for device in devices:
            disk = parent or device
            yield device, disk
            yield from walk(device.get("children") or [], disk)

    devices = json.loads(lsblk).get("blockdevices") or []
    system_disks = {
        disk["name"]
        for device, disk in walk(devices, None)
        if device.get("mountpoint") in _SYSTEM_MOUNTS
    }
    for device, disk in walk(devices, None):
        mount = device.get("mountpoint")
        if not mount or not _is_fat(device.get("fstype") or ""):
            continue
        slot = str(disk.get("name", "")).startswith("mmcblk")
        removable = any(
            flag(item.get(key)) for item in (device, disk) for key in ("rm", "hotplug")
        )
        if (removable or slot) and disk.get("name") not in system_disks:
            out.append((Path(mount), device.get("label") or ""))
    return out


def mac_is_card(info: dict[str, Any]) -> bool:
    """Return True if ``diskutil info -plist`` describes a card: removable or external, and FAT or exFAT."""
    outside = (
        info.get("Removable") or info.get("RemovableMedia") or info.get("Ejectable")
    )
    return bool(outside or info.get("Internal") is False) and _is_fat(
        str(info.get("FilesystemType", ""))
    )


def _linux() -> Iterator[Card]:
    """Yield the cards of a Linux computer."""
    try:
        done = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,RM,HOTPLUG,FSTYPE,LABEL,MOUNTPOINT"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        mounts = linux_mounts(done.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return
    for path, name in mounts:
        card = _card(path, name)
        if card is not None:
            yield card


def _mac() -> Iterator[Card]:
    """Yield the cards of a Mac."""
    volumes = Path("/Volumes")
    try:
        folders = sorted(volumes.iterdir())
    except OSError:
        return
    for folder in folders:
        if folder.is_symlink() or not os.path.ismount(folder):
            continue  # the system volume is a link to /
        try:
            done = subprocess.run(
                ["diskutil", "info", "-plist", str(folder)],
                capture_output=True,
                check=True,
                timeout=10,
            )
            info = plistlib.loads(done.stdout)
        except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException):
            continue
        if isinstance(info, dict) and mac_is_card(info):
            card = _card(folder, str(info.get("VolumeName") or folder.name))
            if card is not None:
                yield card


def windows_letters(
    mask: int,
    drive_type: Callable[[str], int],
    volume: Callable[[str], tuple[str, str] | None],
) -> list[tuple[Path, str]]:
    """Return the top folders and names of the cards among Windows drive letters.

    Args:
        mask: the bits of the drive letters (``GetLogicalDrives``), bit 0 for A.
        drive_type: the type of a root like ``E:\\`` (``GetDriveTypeW``).
        volume: the name and file system of a root, or None if they can't be read.
    """
    removable = 2  # DRIVE_REMOVABLE
    out = []
    for number in range(26):
        if not mask & (1 << number):
            continue
        root = f"{chr(ord('A') + number)}:\\"
        if drive_type(root) != removable:
            continue
        found = volume(root)
        if found is not None and _is_fat(found[1]):
            out.append((Path(root), found[0]))
    return out


def _windows() -> Iterator[Card]:  # pragma: no cover - needs Windows
    """Yield the cards of a Windows computer."""
    import ctypes

    kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]

    def volume(root: str) -> tuple[str, str] | None:
        """Return the name and file system of a drive."""
        name = ctypes.create_unicode_buffer(261)
        system = ctypes.create_unicode_buffer(261)
        if not kernel.GetVolumeInformationW(
            root, name, 261, None, None, None, system, 261
        ):
            return None
        return name.value, system.value

    letters = windows_letters(
        kernel.GetLogicalDrives(), lambda root: kernel.GetDriveTypeW(root), volume
    )
    for path, name in letters:
        card = _card(path, name)
        if card is not None:
            yield card


#: Environment variable with folders (separated by ``os.pathsep``) that are listed as cards: for tests, such as the
#: release smoke test, on a computer with no SD card.
TEST_CARDS_ENV = "EPM2MOD_TEST_CARDS"


def _test_cards() -> Iterator[Card]:
    """Yield the folders that ``TEST_CARDS_ENV`` names, as cards."""
    for text in os.environ.get(TEST_CARDS_ENV, "").split(os.pathsep):
        if text:
            card = _card(Path(text).absolute(), "TEST")
            if card is not None:
                yield card


def cards() -> list[Card]:
    """Return the SD cards plugged into this computer, in path order."""
    if sys.platform == "darwin":
        found = list(_mac())
    elif sys.platform == "win32":
        found = list(_windows())
    else:
        found = list(_linux())
    found += _test_cards()
    return sorted(found, key=lambda card: str(card.path))


def describe(card: Card) -> str:
    """Return a line that names a card for a user: its name, size and folder."""
    name = card.name or "SD card"
    return (
        f"{name}, {card.size / 1e9:.1f} GB ({card.free / 1e9:.1f} GB free), {card.path}"
    )

"""Tests of the card list, ``epm2mod.cards``.

uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import support  # noqa: E402,F401

from epm2mod import cards, cli  # noqa: E402


def device(name: str, **fields: Any) -> dict[str, Any]:
    """Return one lsblk device; flags default to off."""
    item: dict[str, Any] = {
        "name": name,
        "rm": False,
        "hotplug": False,
        "fstype": None,
        "label": None,
        "mountpoint": None,
    }
    item.update(fields)
    return item


def lsblk(*devices: dict[str, Any]) -> str:
    """Return lsblk JSON output."""
    return json.dumps({"blockdevices": list(devices)})


class LinuxTests(unittest.TestCase):
    def test_a_laptop_with_a_usb_reader_and_an_sd_slot(self) -> None:
        output = lsblk(
            device(
                "nvme0n1",
                children=[
                    device("nvme0n1p1", fstype="vfat", mountpoint="/boot/efi"),
                    device("nvme0n1p2", fstype="ext4", mountpoint="/"),
                ],
            ),
            device(
                "sda",
                rm=True,
                children=[
                    device(
                        "sda1",
                        fstype="exfat",
                        label="EOS_DIGITAL",
                        mountpoint="/media/u/EOS_DIGITAL",
                    )
                ],
            ),
            device(
                "mmcblk0",
                children=[
                    device("mmcblk0p1", fstype="vfat", mountpoint="/media/u/3A1F-0C2B")
                ],
            ),
            device(
                "sdb",
                hotplug=True,
                children=[
                    device("sdb1", fstype="ext4", mountpoint="/media/u/backup"),
                    device("sdb2", fstype="vfat", label="STICK"),
                ],
            ),
        )
        self.assertEqual(
            cards.linux_mounts(output),
            [
                (Path("/media/u/EOS_DIGITAL"), "EOS_DIGITAL"),
                (Path("/media/u/3A1F-0C2B"), ""),
            ],
        )

    def test_a_system_on_an_sd_slot_is_not_a_card(self) -> None:
        output = lsblk(
            device(
                "mmcblk0",
                children=[
                    device("mmcblk0p1", fstype="vfat", mountpoint="/boot/firmware"),
                    device("mmcblk0p2", fstype="ext4", mountpoint="/"),
                ],
            )
        )
        self.assertEqual(cards.linux_mounts(output), [])

    def test_old_lsblk_writes_flags_as_text(self) -> None:
        output = lsblk(
            device("sdc", rm="1", hotplug="1", fstype="vfat", mountpoint="/mnt/card")
        )
        self.assertEqual(cards.linux_mounts(output), [(Path("/mnt/card"), "")])
        output = lsblk(device("sdd", rm="0", fstype="vfat", mountpoint="/mnt/disk"))
        self.assertEqual(cards.linux_mounts(output), [])


class MacTests(unittest.TestCase):
    def test_a_removable_or_external_fat_volume_is_a_card(self) -> None:
        reader = {"Internal": True, "RemovableMedia": True, "FilesystemType": "msdos"}
        usb = {"Internal": False, "Ejectable": True, "FilesystemType": "exfat"}
        self.assertTrue(cards.mac_is_card(reader))
        self.assertTrue(cards.mac_is_card(usb))

    def test_an_internal_or_other_volume_is_not(self) -> None:
        system = {"Internal": True, "Removable": False, "FilesystemType": "apfs"}
        fixed_fat = {"Internal": True, "FilesystemType": "msdos"}
        usb_hfs = {"Internal": False, "Ejectable": True, "FilesystemType": "hfs"}
        for info in (system, fixed_fat, usb_hfs, {}):
            self.assertFalse(cards.mac_is_card(info), info)


class WindowsTests(unittest.TestCase):
    def test_removable_fat_drives_are_cards(self) -> None:
        types = {"C:\\": 3, "D:\\": 5, "E:\\": 2, "F:\\": 2, "G:\\": 2}
        volumes = {
            "E:\\": ("EOS_DIGITAL", "exFAT"),
            "F:\\": ("STICK", "NTFS"),
            "G:\\": None,
        }
        mask = sum(1 << (ord(root[0]) - ord("A")) for root in types)
        found = cards.windows_letters(mask, types.__getitem__, volumes.get)
        self.assertEqual(found, [(Path("E:\\"), "EOS_DIGITAL")])


class CommandTests(unittest.TestCase):
    def test_the_command_lists_each_card(self) -> None:
        card = cards.Card(Path("/media/u/CARD"), "CARD", 31_900_000_000, 31_000_000_000)
        out = io.StringIO()
        with mock.patch.object(cards, "cards", return_value=[card]):
            with redirect_stdout(out):
                self.assertEqual(cli.main(["cards"]), 0)
        self.assertEqual(
            out.getvalue(), "CARD, 31.9 GB (31.0 GB free), /media/u/CARD\n"
        )
        err = io.StringIO()
        with mock.patch.object(cards, "cards", return_value=[]):
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                self.assertEqual(cli.main(["cards"]), 0)
        self.assertIn("no SD card found", err.getvalue())

    def test_folders_for_tests_are_listed_as_cards(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.dict(os.environ, {cards.TEST_CARDS_ENV: folder}):
                self.assertIn(Path(folder), [card.path for card in cards.cards()])

    def test_this_computer_lists_without_an_error(self) -> None:
        for card in cards.cards():
            self.assertTrue(card.path.is_dir())


if __name__ == "__main__":
    unittest.main()

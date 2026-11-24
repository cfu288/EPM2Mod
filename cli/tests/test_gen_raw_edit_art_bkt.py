"""Tests of gen/raw-edit-art-bkt/mkspec.py: the checks that keep its spec on its base.

The whole generator runs in gen/run.sh --check, which needs the MN103 binutils and
Olympus's firmware; these tests need neither.
"""

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def load() -> ModuleType:
    """Import the generator from its file (gen/ is not a package)."""
    path = ROOT / "gen" / "raw-edit-art-bkt" / "mkspec.py"
    spec = importlib.util.spec_from_file_location("mkspec_raw_edit_art_bkt", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MK = load()
HEAD: bytes = MK.FILMNAME_HEAD
BASE: int = MK.BASE


class FindFilmnameTests(unittest.TestCase):
    def test_new_code_that_starts_with_the_head(self) -> None:
        stock = bytes(64)
        base = bytes(8) + HEAD + bytes(64 - 8 - len(HEAD))
        self.assertEqual(MK.find_filmname(base, stock), BASE + 8)

    def test_the_head_in_stock_code_does_not_count(self) -> None:
        stock = bytes(40) + HEAD + bytes(24 - len(HEAD))
        base = bytes(8) + HEAD + stock[8 + len(HEAD) :]
        self.assertEqual(MK.find_filmname(base, stock), BASE + 8)

    def test_none_or_two_is_an_error(self) -> None:
        stock = bytes(64)
        with self.assertRaises(ValueError):
            MK.find_filmname(stock, stock)
        two = HEAD + bytes(8) + HEAD + bytes(64 - 8 - 2 * len(HEAD))
        with self.assertRaises(ValueError):
            MK.find_filmname(two, stock)


class CheckStockTests(unittest.TestCase):
    def test_a_changed_byte_in_a_range_is_an_error(self) -> None:
        stock = bytes(32)
        base = bytes(16) + b"\x01" + bytes(15)
        MK.check_stock(base, stock, [(BASE, BASE + 16), (BASE + 17, BASE + 32)])
        with self.assertRaises(ValueError):
            MK.check_stock(base, stock, [(BASE + 10, BASE + 20)])


class BytesOpTests(unittest.TestCase):
    def test_the_op_expects_the_stock_bytes(self) -> None:
        stock = bytes(range(16))
        op = MK.bytes_op(stock, BASE + 4, b"\xaa\xbb", "note")
        self.assertEqual(op["offset"], "0x4")
        self.assertEqual(op["expect"], "0405")
        self.assertEqual(op["new"], "aabb")
        self.assertEqual(op["_addr"], f"{BASE + 4:#X}")


if __name__ == "__main__":
    unittest.main()

"""Tests of the film list with a black-and-white film, ``epm2mod.looks.mono``.

    uv run python -m unittest discover -s tests

They need numpy. ``RealFirmwareMonoTests`` needs the stock firmware file and
is skipped without it.
"""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT  # noqa: E402

try:
    import numpy as np
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("numpy is not installed") from None

from epm2mod import stock  # noqa: E402
from epm2mod.container import parse  # noqa: E402
from epm2mod.errors import BuildError  # noqa: E402
from epm2mod.looks import extra, films, generate, mono, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS).is_file()


class ChainTests(unittest.TestCase):
    def test_the_tail_tests_each_code_and_holds_its_matrix(self) -> None:
        at = 0x7EBF2F40
        tail = mono.chain_tail(at, (74, 83), tuple(range(1, 10)))
        # cmp 74 / beq load, cmp 83 / beq load, jmp none, load, mov d3,a0, jmp use
        self.assertEqual(tail[:8], bytes.fromhex("a04ac80ba053c807"))
        self.assertEqual(tail[8:13], extra.jump(at + 8, slots.MATRIX_NONE))
        table = at + 26
        self.assertEqual(tail[13:21], extra.load_a1(table) + b"\xf1\xec")
        self.assertEqual(tail[21:26], extra.jump(at + 21, slots.MATRIX_USE))
        self.assertEqual(tail[26:], struct.pack("<9h", *range(1, 10)))
        self.assertEqual(table % 2, 0)

    def test_a_tone_table_is_256_rising_10_bit_values(self) -> None:
        good = {"T": np.arange(256) * 4}
        self.assertEqual(len(mono.pack_tone(good, "T", "x")), slots.TABLE_BYTES)
        for bad in (
            np.arange(255),
            np.arange(256) * 5,
            np.arange(256)[::-1],
            np.arange(256) + 0.5,
        ):
            with self.assertRaises(BuildError):
                mono.pack_tone({"T": bad}, "T", "x")
        with self.assertRaises(BuildError):
            mono.pack_tone(good, "L", "x")


class ListTests(unittest.TestCase):
    def test_the_film_list(self) -> None:
        film_list = films.load_bw_films(PATHS)
        self.assertEqual(film_list.mono.entry, slots.MONO_SLOT.entry)
        self.assertEqual(len(set(film_list.spec_paths)), 2)
        for change in (
            {"moved_to": film_list.mono.entry},
            {"moved_to": "Pop Art"},
            {"mono_spec": film_list.entry_spec},
        ):
            fields = {
                "mono": film_list.mono,
                "moved_to": film_list.moved_to,
                "entry_spec": film_list.entry_spec,
                "mono_spec": film_list.mono_spec,
                **change,
            }
            with self.assertRaises(BuildError):
                films.BwFilmList(**fields)  # type: ignore[arg-type]

    def test_the_slot_keeps_the_stock_codes_of_its_entry(self) -> None:
        shared = slots.EXTRA_SLOTS[0]
        self.assertEqual(slots.MONO_SLOT.entry, shared.entry)
        self.assertEqual(slots.MONO_SLOT.art_codes[0], shared.art_mode_code)
        codes = [slot.art_code for slot in slots.EXTRA_SLOTS]
        self.assertFalse(set(slots.MONO_SLOT.art_codes) & set(codes))


@unittest.skipUnless(HAVE_STOCK, "the stock firmware is not in firmware/stock/")
class RealFirmwareMonoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = parse(stock.read_stock(PATHS)).blocks[generate.PROGRAM_BLOCK].payload
        cls.program = generate.Program(payload)
        cls.layout = extra.Layout(
            slots.EXTRA_SLOTS, cls.program.record(slots.DEFAULT_RECORD)
        )

    def test_the_chain_of_the_extra_slots_ends_in_the_new_part(self) -> None:
        exit_op, tail_op = mono.chain_ops(
            self.program, self.layout, (74, 83), tuple(range(9))
        )
        end = self.layout.chain + len(self.layout.code)
        at = slots.BLOCK0_BASE + exit_op.offset
        self.assertEqual(exit_op.expect, extra.jump(at, slots.MATRIX_NONE))
        self.assertEqual(exit_op.new, extra.jump(at, end))
        self.assertEqual(slots.BLOCK0_BASE + tail_op.offset, end)
        self.assertLessEqual(end + len(tail_op.new), slots.EXTRA_CODE_AREA[1])
        # no other spec of the extra slots writes where the new part goes
        for op in extra.structure_ops(self.program, self.layout):
            start = slots.BLOCK0_BASE + op.offset
            self.assertFalse(
                start < end + len(tail_op.new) and end < start + len(op.new)
            )

    def test_the_tables_are_loaded_once_and_only_by_the_two_codes(self) -> None:
        slot = slots.MONO_SLOT
        image = self.program.read(slots.BLOCK0_BASE, 0xD00000)
        for table in (slot.grain_table, slot.live_look):
            self.assertEqual(image.count(struct.pack("<I", table)), 1)
        # the look handler of both codes is the one that loads the live-view table
        table, first = slots.LOOK_JUMP
        handlers = {
            self.program.read(table + 4 * (code - first), 4) for code in slot.art_codes
        }
        self.assertEqual(len(handlers), 1)
        handler = struct.unpack("<I", handlers.pop())[0]
        self.assertTrue(handler < slot.live_load < handler + 16)

    def test_the_moved_entry_gets_the_value_and_its_own_name(self) -> None:
        source, target = slots.EXTRA_SLOTS[0], slots.EXTRA_SLOTS[1]
        ops = mono.moved_entry_ops(self.program, source, target)
        self.assertEqual(len(ops), 14)
        for op in ops[:13]:
            self.assertEqual((op.expect, op.new), (bytes((108,)), bytes((111,))))
        own = extra.hash_ops(self.program, slots.COLOUR_TONE_HASH, [(112, 108)])[0]
        self.assertEqual(ops[13].new, own.new[4:])
        self.assertNotEqual(ops[13].expect, ops[13].new)

    def test_the_committed_specs_are_the_generated_ones(self) -> None:
        paths = [spec.path for spec in mono.generate(PATHS)]
        self.assertEqual(paths, list(films.load_bw_films(PATHS).spec_paths))
        self.assertEqual(generate.stale(PATHS), [], "run: uv run epm2mod looks --write")


if __name__ == "__main__":
    unittest.main()

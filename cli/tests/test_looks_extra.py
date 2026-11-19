"""Tests of the film slots beyond the first seven, ``epm2mod.looks.extra``.

    uv run python -m unittest discover -s cli/tests

They need numpy. ``RealFirmwareExtraTests`` needs the stock firmware file and
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
    import numpy  # noqa: F401
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("numpy is not installed") from None

from epm2mod import stock  # noqa: E402
from epm2mod.container import parse  # noqa: E402
from epm2mod.errors import BuildError  # noqa: E402
from epm2mod.looks import extra, films, generate, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()


class EncoderTests(unittest.TestCase):
    def test_jump_is_relative_to_its_own_address(self) -> None:
        # the last jump of the first matrix chain, as the firmware build has it
        self.assertEqual(
            extra.jump(slots.MATRIX_CHAIN_EXIT, slots.MATRIX_NONE),
            slots.MATRIX_CHAIN_EXIT_BYTES,
        )

    def test_loads_and_compares_take_the_long_form_from_128(self) -> None:
        self.assertEqual(extra.load_d2(94), bytes((0x8A, 94)))
        self.assertEqual(extra.load_d2(144), bytes((0x2E, 144, 0)))
        self.assertEqual(extra.compare_d0(98), bytes((0xA0, 98)))
        self.assertEqual(extra.compare_d0(156), bytes((0xFA, 0xC8, 156, 0)))
        self.assertEqual(extra.load_a1(0x7E112233), bytes.fromhex("fcdd3322117e"))
        for call in (extra.load_d2, extra.compare_d0):
            with self.assertRaises(BuildError):
                call(256)

    def test_a_short_branch_has_a_range(self) -> None:
        self.assertEqual(extra.branch(0xC8, 0x100, 0x140), bytes((0xC8, 0x40)))
        self.assertEqual(extra.branch(0xCA, 0x100, 0xF0), bytes((0xCA, 0xF0)))
        with self.assertRaises(BuildError):
            extra.branch(0xCA, 0x100, 0x180)


class SlotTests(unittest.TestCase):
    def test_the_extra_slots_share_nothing(self) -> None:
        first = slots.SLOTS
        more = slots.EXTRA_SLOTS
        for attribute in ("value", "art_code", "gamma_entry", "place", "stock_value"):
            values = [getattr(slot, attribute) for slot in more]
            self.assertEqual(len(set(values)), len(values), attribute)
        tables: list[int] = []
        for slot in [s.look for s in more] + list(first):
            tables += [slot.saturation, *slot.six_axis, slot.matrix, slot.chroma]
            tables += list(slot.tone.addresses)
        self.assertEqual(len(set(tables)), len(tables))
        for slot in more:
            self.assertTrue(110 <= slot.value <= 118)
            self.assertNotIn(slot.value, (116, 117))  # tested in code by the firmware
            self.assertNotIn(slot.entry, [s.entry for s in first])

    def test_the_layout_stays_in_its_areas(self) -> None:
        layout = extra.Layout(slots.EXTRA_SLOTS, list(range(0x1000, 0x1020, 4)))
        start, end = slots.EXTRA_DATA_AREA
        self.assertLessEqual(start + len(layout.data), slots.EXTRA_MATRICES)
        self.assertLessEqual(
            slots.EXTRA_MATRICES + len(slots.EXTRA_SLOTS) * slots.MATRIX_BYTES, end
        )
        self.assertLessEqual(layout.chain + len(layout.code), slots.EXTRA_CODE_AREA[1])
        # a record: the default table and the film's table in turn
        record = layout.records[0] - start
        words = struct.unpack_from("<8I", layout.data, record)
        table = slots.EXTRA_SLOTS[0].look.tone.addresses[0]
        self.assertEqual(
            words, (0x1000, table, 0x1008, table, 0x1010, table, 0x1018, table)
        )

    def test_the_film_list(self) -> None:
        film_list = films.load_more_films(PATHS)
        self.assertEqual(
            [film.entry for film in film_list.films],
            [slot.entry for slot in slots.EXTRA_SLOTS],
        )
        self.assertEqual(len(film_list.spec_paths), 2 + len(slots.EXTRA_SLOTS))
        with self.assertRaises(BuildError):
            films.MoreFilmList(
                films=film_list.films[:-1],
                structure_spec=film_list.structure_spec,
                looks_spec=film_list.looks_spec,
                entry_specs=film_list.entry_specs[:-1],
            )
        with self.assertRaises(BuildError):
            films.MoreFilmList(
                films=film_list.films,
                structure_spec=film_list.looks_spec,
                looks_spec=film_list.looks_spec,
                entry_specs=film_list.entry_specs,
            )


@unittest.skipUnless(HAVE_STOCK, "the stock firmware is not in firmware/stock/")
class RealFirmwareExtraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = (
            parse(stock.read_stock(PATHS, stock.EPM2_V16))
            .blocks[generate.PROGRAM_BLOCK]
            .payload
        )
        cls.program = generate.Program(payload)

    def test_hash_ops_put_a_key_where_the_firmware_finds_it(self) -> None:
        ops = extra.hash_ops(self.program, slots.COLOUR_TONE_HASH, [(111, 104)])
        self.assertEqual(len(ops), 1)
        # 111 & 31 = 15; entries 15 and 16 hold 108 and 109; 17 is the first empty one
        base = slots.COLOUR_TONE_HASH - slots.BLOCK0_BASE
        self.assertEqual(ops[0].offset, base + 8 * 17)
        target = self.program.read(slots.COLOUR_TONE_HASH + 8 * 11 + 4, 4)
        self.assertEqual(ops[0].new, struct.pack("<I", 111) + target)
        with self.assertRaises(BuildError):
            extra.hash_ops(self.program, slots.COLOUR_TONE_HASH, [(104, 100)])
        with self.assertRaises(BuildError):
            extra.hash_ops(self.program, slots.COLOUR_TONE_HASH, [(111, 99)])

    def test_the_stock_firmware_has_what_the_slots_name(self) -> None:
        for slot in slots.EXTRA_SLOTS:
            self.assertEqual(len(extra.entry_ops(self.program, slot)), 13)
            # the hash entry is empty, the handlers load the slot's tables
            entry = self.program.read(slots.GAMMA_HASH + 8 * slot.gamma_entry, 8)
            self.assertEqual(
                struct.unpack("<2I", entry), (0, slots.GAMMA_DEFAULT_HANDLER)
            )
            load = self.program.read(slot.saturation_handler, 6)
            self.assertEqual(
                load, b"\xfc\xdf" + struct.pack("<I", slot.look.saturation)
            )
            loads = self.program.read(slot.six_axis_handler, 12)
            self.assertEqual(
                loads,
                b"\xfc\xdf"
                + struct.pack("<I", slot.look.six_axis[0])
                + b"\xfc\xde"
                + struct.pack("<I", slot.look.six_axis[1]),
            )
            chroma = self.program.read(slot.chroma_handler + 2, 6)
            self.assertEqual(chroma, b"\xfc\xcc" + struct.pack("<I", slot.look.chroma))
            # no stock table entry leads to the new art code's row yet
            for table, first in (slots.SATURATION_JUMP, slots.SIX_AXIS_JUMP):
                other = self.program.read(table + 4 * (slot.art_code - first), 4)
                self.assertNotEqual(other, struct.pack("<I", slot.saturation_handler))

    def test_the_committed_specs_are_the_generated_ones(self) -> None:
        paths = [spec.path for spec in extra.generate(PATHS, stock.EPM2_V16)]
        self.assertEqual(paths, list(films.load_more_films(PATHS).spec_paths))
        self.assertEqual(
            generate.stale(PATHS, stock.EPM2_V16), [], "run: uv run epm2mod generate"
        )


if __name__ == "__main__":
    unittest.main()

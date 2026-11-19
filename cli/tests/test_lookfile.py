"""Tests of the look file for the SD card: ``epm2mod.looks.lookfile``, ``records`` and ``lookpack``.

    uv run python -m unittest discover -s cli/tests

``lookpack`` needs numpy. ``RealFirmwareLookTests`` needs the stock firmware
file and is skipped without it.
"""

from __future__ import annotations

import dataclasses
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT, write_manifest  # noqa: E402

from epm2mod import cards, cli, stock  # noqa: E402
from epm2mod.errors import BuildError, LookFileError, UsageError  # noqa: E402
from epm2mod.hashing import sha256_bytes  # noqa: E402
from epm2mod.looks import lookfile, records  # noqa: E402
from epm2mod.looks.lookfile import ColourLook, MonoLook  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()
try:
    import numpy as np

    from epm2mod.looks import generate, lookpack, slots
    from epm2mod.container import parse

    HAVE_NUMPY = True
except ImportError:  # pragma: no cover
    HAVE_NUMPY = False

#: The look file of ``data/films/card-looks.json`` (the twelve looks of the pinned
#: films, all colour looks): the test vector of docs/reference/look-file-format.md.
CARD_LOOKS_SHA256 = "5d5df335dc14100a3fb7c90265ca07470419f12f52f806cc6b80f1bc09cae7ad"

CURVE = tuple(min(1023, k + k // 2) for k in range(1024))
GREY = (77, 150, 29) * 3


def colour(slot: int = 2, **changes: object) -> ColourLook:
    """Return a valid colour look, with some fields changed."""
    chroma = bytes(range(16)) + bytes(16) + bytes(17) + bytes(range(16)) + bytes(32)
    look = ColourLook(
        slot=slot,
        name="Test",
        gain=300,
        saturation=(1, 2, 3, 4, 5, 6),
        hue=(-1, -2, -3, -4, -5, -6),
        matrix=(256, 0, 0, 0, 256, 0, 0, 0, 256),
        chroma=chroma,
        curves=(CURVE, CURVE, tuple(range(1024))),
    )
    return dataclasses.replace(look, **changes)  # type: ignore[arg-type]


def mono(slot: int = 4) -> MonoLook:
    """Return a valid black-and-white look."""
    return MonoLook(slot, "Mono", GREY, tuple(range(256)), tuple(range(0, 1024, 4)))


class CurveTests(unittest.TestCase):
    def test_a_curve_is_its_first_value_and_4_bit_steps(self) -> None:
        data = lookfile.encode_curve(CURVE)
        self.assertEqual(len(data), lookfile.CURVE_BYTES)
        self.assertEqual(data[:2], b"\0\0")
        # steps 1, 2 (low nibble first), 1, 2, ...
        self.assertEqual(data[2], 0x21)
        self.assertEqual(data[-1] >> 4, 0)
        self.assertEqual(lookfile.decode_curve(data), CURVE)

    def test_a_curve_that_falls_steps_too_far_or_leaves_10_bits_is_refused(
        self,
    ) -> None:
        for bad in (
            (5,) + (4,) * 1023,
            tuple(range(0, 16 * 1024, 16))[:1024],
            (1024,) * 1024,
            CURVE[:-1],
        ):
            with self.assertRaises(LookFileError):
                lookfile.encode_curve(bad)
        data = bytearray(lookfile.encode_curve(CURVE))
        data[-1] |= 0x10
        with self.assertRaises(LookFileError):
            lookfile.decode_curve(bytes(data))
        with self.assertRaises(LookFileError):
            lookfile.decode_curve(b"\xff\x03" + b"\x11" * 512)


class FileTests(unittest.TestCase):
    def test_round_trip_and_header(self) -> None:
        looks = [colour(), mono()]
        data = lookfile.pack(looks)
        self.assertEqual(len(data), 32 + 2 * 1708)
        self.assertEqual(data[:8], b"EPLK\x01\x02" + struct.pack("<H", 1708))
        length, crc, model, firmware = struct.unpack_from("<IIHH", data, 8)
        self.assertEqual((length, model, firmware), (len(data), 0x0101, 0x0160))
        self.assertEqual(crc, zlib.crc32(data[16:]))
        self.assertEqual(data[20:32], bytes(12))
        self.assertEqual(lookfile.unpack(data), looks)
        self.assertEqual(lookfile.unpack(lookfile.pack([])), [])

    def test_record_layout(self) -> None:
        record = lookfile.encode_record(colour())
        self.assertEqual(record[:4], b"\x02\x01\0\0")
        self.assertEqual(record[4:20], b"Test".ljust(16, b"\0"))
        self.assertEqual(struct.unpack_from("<H6h6h9h", record, 20)[:2], (300, 1))
        self.assertEqual(record[64:161], colour().chroma)
        self.assertEqual(record[164:678], lookfile.encode_curve(CURVE))
        self.assertEqual(record[161:164] + record[1706:], bytes(5))
        record = lookfile.encode_record(mono())
        self.assertEqual(record[:2], b"\x04\x02")
        self.assertEqual(record[20:46] + record[64:164] + record[1188:], bytes(646))
        self.assertEqual(struct.unpack_from("<256H", record, 676)[1], 4)

    def test_damaged_or_foreign_files_are_refused(self) -> None:
        good = lookfile.pack([colour()])

        def changed(at: int, new: bytes, fix_crc: bool = True) -> bytes:
            """Return the good file with bytes replaced, its CRC made right."""
            data = bytearray(good)
            data[at : at + len(new)] = new
            if fix_crc:
                struct.pack_into("<I", data, 12, zlib.crc32(bytes(data[16:])))
            return bytes(data)

        for bad in (
            good[:31],
            changed(0, b"EPLX"),
            changed(4, b"\x02"),
            changed(5, b"\x02"),
            changed(6, struct.pack("<H", 1700)),
            changed(8, struct.pack("<I", 1000)),
            good + b"\0",
            changed(100, b"\x55", fix_crc=False),
            changed(16, struct.pack("<H", 0x0143)),
            changed(18, struct.pack("<H", 0x0150)),
            changed(32, b"\x0c"),
            changed(33, b"\x03"),
            changed(32 + 164, b"\xff\x03"),
            changed(32 + 46, struct.pack("<h", 300)),
        ):
            with self.assertRaises(LookFileError):
                lookfile.unpack(bad)
        twice = lookfile.pack([colour(), colour(3)])
        record_3 = twice[32 + 1708 :]
        data = bytearray(twice[: 32 + 1708] + b"\x02" + record_3[1:])
        struct.pack_into("<I", data, 12, zlib.crc32(bytes(data[16:])))
        with self.assertRaises(LookFileError):
            lookfile.unpack(bytes(data))

    def test_looks_that_do_not_fit_are_refused(self) -> None:
        for changes in (
            {"slot": 12},
            {"name": "x" * 17},
            {"name": "Tri-Xé"},
            {"gain": -1},
            {"saturation": (1, 2, 3)},
            {"matrix": (300, 0, 0, 0, 256, 0, 0, 0, 256)},
            {"chroma": bytes(96)},
            {"chroma": bytes([5, 4]) + bytes(95)},
            {"curves": (CURVE, CURVE)},
        ):
            with self.assertRaises(LookFileError, msg=str(changes)):
                colour(**changes)
        with self.assertRaises(LookFileError):
            MonoLook(4, "Mono", GREY, tuple(range(255, -1, -1)), tuple(range(256)))
        with self.assertRaises(LookFileError):
            lookfile.pack([colour(), colour()])
        with self.assertRaises(LookFileError):
            lookfile.pack([colour(slot) for slot in range(12)] + [mono(4)])

    def test_json_round_trip(self) -> None:
        for look in (colour(), mono()):
            raw = json.loads(json.dumps(lookfile.look_to_json(look)))
            self.assertEqual(lookfile.look_from_json(raw), look)
        raw = lookfile.look_to_json(colour())
        self.assertEqual(raw["entry"], "Pale&Light Color")
        self.assertEqual(len(raw["chroma"]["Cb"]["slope"]), 17)
        self.assertEqual(len(raw["chroma"]["Cr"]["slope"]), 16)
        for broken in (
            {**raw, "kind": "sepia"},
            {key: value for key, value in raw.items() if key != "gain"},
            {**raw, "hue": [1.5] * 6},
            {**raw, "chroma": {"Cb": raw["chroma"]["Cb"]}},
        ):
            with self.assertRaises(LookFileError):
                lookfile.look_from_json(broken)


@unittest.skipUnless(HAVE_NUMPY, "numpy is not installed")
class PackTests(unittest.TestCase):
    def test_the_look_list_of_the_pinned_build(self) -> None:
        looks = lookpack.load_list(PATHS, PATHS.card_looks)
        self.assertEqual([look.slot for look in looks], list(range(12)))
        self.assertTrue(all(isinstance(look, ColourLook) for look in looks))
        double_x = looks[4]
        assert isinstance(double_x, ColourLook)
        self.assertEqual(double_x.gain, 0)  # black and white
        self.assertEqual(double_x.curves[0], double_x.curves[2])
        data = lookfile.pack(looks)
        self.assertEqual(len(data), lookfile.MAX_FILE_BYTES)
        self.assertEqual(sha256_bytes(data), CARD_LOOKS_SHA256)
        self.assertEqual(lookfile.unpack(data), looks)

    def test_films_pack_writes_a_look_list_of_fit_files(self) -> None:
        with tempfile.TemporaryDirectory() as folder, redirect_stderr(io.StringIO()):
            out = Path(folder) / lookfile.CARD_NAME
            argv = ["films", "pack", str(PATHS.card_looks), "-o", str(out)]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main([*argv, "--dry-run"]), 0)
                self.assertFalse(out.exists())
                self.assertEqual(cli.main(argv), 0)
            self.assertEqual(sha256_bytes(out.read_bytes()), CARD_LOOKS_SHA256)

    def test_the_film_records_are_current(self) -> None:
        self.assertEqual(
            json.loads(PATHS.film_records.read_text()),
            lookpack.web_data(PATHS),
            "run: uv run python web/scripts/export_films.py",
        )

    def test_a_fit_with_a_matrix_and_two_tables_gives_a_black_and_white_look(
        self,
    ) -> None:
        fit = lookpack.load_fit(PATHS.resolve("data/films/fits/doublex2.npz"))
        look = lookpack.look_of_fit(fit, "Grainy Film", "Double-X", "doublex2")
        self.assertIsInstance(look, MonoLook)
        assert isinstance(look, MonoLook)
        self.assertEqual(list(look.grain), fit["T"].tolist())

    def test_a_list_with_a_bad_entry_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "list.json"
            for raw in (
                [],
                {"looks": [{"entry": "Pop Art", "name": "x"}]},
                {
                    "looks": [
                        {
                            "entry": "Art Bracket",
                            "name": "x",
                            "fit": "data/films/fits/portra.npz",
                        }
                    ]
                },
                {"looks": [{"entry": "Pop Art", "name": "x", "fit": "/etc/passwd"}]},
            ):
                path.write_text(json.dumps(raw))
                with self.assertRaises((LookFileError, BuildError)):
                    lookpack.load_list(PATHS, path)

    def test_the_commands(self) -> None:
        with tempfile.TemporaryDirectory() as folder, redirect_stderr(io.StringIO()):
            out = io.StringIO()
            path = Path(folder) / lookfile.CARD_NAME
            with redirect_stdout(out):
                argv = ["films", "pack", str(PATHS.card_looks), "-o", str(path)]
                self.assertEqual(cli.main(argv), 0)
                self.assertEqual(sha256_bytes(path.read_bytes()), CARD_LOOKS_SHA256)
                self.assertEqual(cli.main(["inspect", str(path)]), 0)
            self.assertIn("Double-X", out.getvalue())
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(cli.main(["inspect", "--json", str(path)]), 0)
            films = json.loads(out.getvalue())["files"][0]["films"]
            self.assertEqual(films[0]["name"], "Portra 400")
            path.write_bytes(path.read_bytes()[:-1])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["inspect", str(path)]), 1)


class ChoiceTests(unittest.TestCase):
    """Look files from the film records: no numpy."""

    def test_every_film_of_the_records_makes_a_look(self) -> None:
        films = records.load(PATHS)
        self.assertEqual(len(films.films), 22)
        choices = [f"ART{n % 12 + 1}={film}" for n, film in enumerate(films.films)]
        for start in (0, 12):
            looks = records.looks_of_choices(films, choices[start : start + 12])
            self.assertTrue(all(isinstance(look, ColourLook) for look in looks))
            lookfile.unpack(lookfile.pack(looks))

    def test_a_choice_names_an_art_number_and_a_film(self) -> None:
        films = records.load(PATHS)
        looks = records.looks_of_choices(films, ["ART2=velvia", "art12=vision3-500t"])
        self.assertEqual(
            [(look.slot, look.name) for look in looks],
            [(1, "Velvia"), (11, "Vis 500T")],
        )
        self.assertEqual(films.slots[6].entry, "Diorama")
        same = records.looks_of_choices(films, ["ART7=velvia"])[0]
        self.assertEqual(dataclasses.replace(looks[0], slot=6), same)
        for bad in (
            ["ART0=velvia"],
            ["ART13=velvia"],
            ["ART2=velvia", "ART2=c200"],
            ["ART2=nofilm"],
            ["ART2=velvia:My Velvia"],
            ["Velvia"],
        ):
            with self.assertRaises(UsageError, msg=str(bad)):
                records.looks_of_choices(films, bad)

    def test_pack_and_list_work_without_numpy(self) -> None:
        program = (
            "import sys; sys.modules['numpy'] = None\n"
            "from epm2mod import cli\n"
            "assert cli.main(['films']) == 0\n"
            "assert cli.main(['films', 'set', '--film', 'ART2=velvia', '-o', sys.argv[1]]) == 0\n"
            "assert 'numpy' not in [name for name in sys.modules if sys.modules[name]]\n"
        )
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run(
                [sys.executable, "-c", program, str(Path(folder) / lookfile.CARD_NAME)],
                env={**os.environ, "PYTHONPATH": str(ROOT / "cli" / "src")},
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            data = (Path(folder) / lookfile.CARD_NAME).read_bytes()
            self.assertEqual([look.slot for look in lookfile.unpack(data)], [1])

    def test_a_bad_records_file_is_refused(self) -> None:
        raw = json.loads(PATHS.film_records.read_text())
        broken_record = json.loads(json.dumps(raw))
        broken_record["films"][0]["record"] = "AAAA"
        wrong_name = json.loads(json.dumps(raw))
        wrong_name["films"][0]["name"] = "Other"
        wrong_entry = json.loads(json.dumps(raw))
        wrong_entry["slots"][0]["entry"] = "Soft Focus"
        a_preset = json.loads(json.dumps(raw))
        a_preset["slots"][0]["builtIn"] = "portra-400"
        eleven = json.loads(json.dumps(raw))
        del eleven["slots"][11]
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "data" / "films").mkdir(parents=True)
            paths = RepoPaths(write_manifest(Path(folder)))
            for bad in (broken_record, wrong_name, wrong_entry, a_preset, eleven, []):
                paths.film_records.write_text(json.dumps(bad))
                with self.assertRaises(BuildError, msg=str(bad)[:60]):
                    records.load(paths)

    def test_set_on_a_card_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as folder, redirect_stderr(io.StringIO()):
            (Path(folder) / "DCIM").mkdir()
            out = io.StringIO()
            env = {cards.TEST_CARDS_ENV: folder}
            with redirect_stdout(out), mock.patch.dict(os.environ, env):
                argv = [
                    "films",
                    "set",
                    "--film",
                    "ART2=velvia",
                    "--film",
                    "ART6=double-x",
                ]
                self.assertEqual(cli.main([*argv, "--card", folder]), 0)
                self.assertEqual(cli.main(["films"]), 0)
                missing = str(Path(folder) / "missing")
                self.assertEqual(cli.main([*argv, "--card", missing]), 6)
            looks = lookfile.unpack((Path(folder) / lookfile.CARD_NAME).read_bytes())
            self.assertEqual([look.slot for look in looks], [1, 5])
            self.assertIn("vision3-500t", out.getvalue())
            self.assertIn("ART12     Watercolor", out.getvalue())


@unittest.skipUnless(HAVE_NUMPY and HAVE_STOCK, "needs numpy and the stock firmware")
class RealFirmwareLookTests(unittest.TestCase):
    def test_the_camera_makes_the_tables_of_the_built_in_looks(self) -> None:
        container = parse(stock.read_stock(PATHS, stock.EPM2_V16))
        program = generate.Program(container.blocks[generate.PROGRAM_BLOCK].payload)
        defaults = [
            program.read(table, slots.TABLE_BYTES)
            for table in program.record(slots.DEFAULT_RECORD)
        ]
        grid = np.arange(slots.CURVE_POINTS, dtype=np.float64)
        items = json.loads(PATHS.card_looks.read_text())["looks"]
        for item, look in zip(items, lookpack.load_list(PATHS, PATHS.card_looks)):
            fit = generate.load_fit(PATHS.resolve(item["fit"]))
            assert isinstance(look, ColourLook)
            for channel, curve in enumerate(look.curves):
                for default in defaults:
                    values = np.frombuffer(default, "<u2").astype(np.float64)
                    built = generate.pack_table(
                        np.interp(values, grid, fit["G"][channel])
                    )
                    self.assertEqual(lookpack.camera_table(curve, default), built)


if __name__ == "__main__":
    unittest.main()

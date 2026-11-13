"""Tests of the film-spec generator, ``epm2mod.looks``.

    uv run python -m unittest discover -s tests

They need numpy. The unit tests use made-up data; ``RealFirmwareLooksTests``
needs the stock firmware file and is skipped without it.
"""

from __future__ import annotations

import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    import numpy as np
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("numpy is not installed") from None

from epm2mod import builds, container, pipeline, stock  # noqa: E402
from epm2mod.errors import BuildError  # noqa: E402
from epm2mod.fileio import read_json  # noqa: E402
from epm2mod.looks import films, generate, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402
from epm2mod.spec import BytesOp  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS).is_file()
UTF16 = "utf-16-le"


def good_fit() -> dict[str, Any]:
    """Return the arrays of a well-formed fit."""
    knots = np.array([np.arange(16) * 17, np.arange(16) * 17, np.full(16, 128)])
    return {
        "G": np.tile(np.arange(1024, dtype=float), (3, 1)),
        "gain": np.array(260),
        "S": np.zeros(6),
        "H": np.zeros(6),
        "A": np.array([[256, 0, 0], [0, 256, 0], [0, 0, 256]]),
        "Cb": knots,
        "Cr": knots,
        "Cb_slope17": np.full(17, 128),
        "Cr_slope17": np.full(17, 128),
    }


class UnitTests(unittest.TestCase):
    def test_pack_table_rounds_rises_and_limits(self) -> None:
        curve = np.array([0.4, 5.6, 3.0, 2000.0] + [2000.0] * 252)
        values = struct.unpack("<256H", generate.pack_table(curve))
        self.assertEqual(values[:4], (0, 6, 6, 1023))
        self.assertEqual(len(generate.pack_table(curve)), slots.TABLE_BYTES)

    def test_whole_numbers(self) -> None:
        self.assertEqual(
            generate.whole_numbers(np.array([1.0, -2.0]), 2, -5, 5, "x", "w"), [1, -2]
        )
        for values, count in (([1.5, 2.0], 2), ([1.0], 2), ([1.0, 9.0], 2)):
            with self.subTest(values=values), self.assertRaises(BuildError):
                generate.whole_numbers(np.array(values), count, -5, 5, "x", "w")

    def test_chroma_record(self) -> None:
        record = generate.chroma_record(good_fit(), "w")
        self.assertEqual(len(record), 97)
        self.assertEqual(list(record[:3]), [0, 17, 34])
        self.assertEqual(list(record[32:49]), [128] * 17)
        self.assertEqual(list(record[81:97]), [128] * 16)
        for change in (
            {"Cb_slope17": np.full(17, 256)},
            {"Cr": np.zeros((2, 15))},
            {"Cb": np.zeros(16)},
            {"Cr_slope17": np.full(16, 1)},
        ):
            with self.subTest(change=list(change)), self.assertRaises(BuildError):
                generate.chroma_record({**good_fit(), **change}, "w")
        missing = {k: v for k, v in good_fit().items() if k != "Cb"}
        with self.assertRaises(BuildError):
            generate.chroma_record(missing, "w")

    def test_label_ops_change_whole_strings_only(self) -> None:
        def text(value: str) -> bytes:
            return value.encode(UTF16)

        block = (
            text("\0Diorama\0")  # a whole string: counts
            + text("Add Diorama Effect\0")  # part of a longer text: stays
            + text("@Diorama\0")  # after a tag's '@': counts
            + b"\0"
            + text("Diorama\0")  # on an odd offset: stays
        )
        film = films.Film("Diorama", "Fuji Velvia 100", "slide", "Velvia", "x.npz")
        ops = generate.label_ops(block, [film])
        self.assertEqual([op.offset for op in ops], [2, 58])
        self.assertTrue(all(op.new == text("Velvia\0") for op in ops))
        self.assertTrue(all(len(op.new) == len(op.expect) for op in ops))
        with self.assertRaises(BuildError):
            generate.label_ops(text("\0Nothing here\0"), [film])

    def test_a_slot_has_tables_or_records(self) -> None:
        common: dict[str, Any] = dict(
            entry="X",
            saturation=1,
            six_axis=(2, 3),
            matrix=4,
            matrix_is_new=True,
            chroma=5,
        )
        slots.Slot(tables=(1, 2, 3), **common)
        slots.Slot(records=(1, 2, 3), **common)
        both: dict[str, Any] = {"tables": (1, 2, 3), "records": (1, 2, 3)}
        neither: dict[str, Any] = {}
        for bad in (neither, both):
            with self.assertRaises(ValueError):
                slots.Slot(**common, **bad)
        self.assertEqual(slots.slot_for("Diorama").entry, "Diorama")
        with self.assertRaises(KeyError):
            slots.slot_for("Grainy Film")

    def test_generated_fields(self) -> None:
        op = BytesOp(0, 16, b"\x00", b"\x01")
        made = generate.GeneratedSpec("patches/x-1.json", "text", (op,), "credit")
        fields = made.generated_fields(stock.EPM2_V16)
        self.assertEqual(
            list(fields),
            ["name", "attribution", "description", "ops", "base", "base_sha256"],
        )
        self.assertEqual(fields["name"], "x-1")
        plain = generate.GeneratedSpec("patches/y.json", "text", (op,))
        self.assertNotIn("attribution", plain.generated_fields(stock.EPM2_V16))


class FilmListTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.paths = RepoPaths(Path(folder))
        self.paths.films.parent.mkdir(parents=True)
        self.good = json.loads(PATHS.films.read_text(encoding="utf-8"))

    def load(self, raw: Any) -> films.FilmList:
        self.paths.films.write_text(json.dumps(raw), encoding="utf-8")
        return films.load_films(self.paths)

    def test_the_repository_film_list(self) -> None:
        loaded = films.load_films(PATHS)
        self.assertEqual(
            [f.entry for f in loaded.films], [s.entry for s in slots.SLOTS]
        )
        self.assertEqual(self.load(self.good), loaded)
        for film in loaded.films:
            self.assertTrue(PATHS.resolve(film.fit).is_file(), film.fit)

    def test_refusals(self) -> None:
        def changed(index: int, **fields: Any) -> dict[str, Any]:
            raw: dict[str, Any] = json.loads(json.dumps(self.good))
            raw["films"][index].update(fields)
            return raw

        bad: list[Any] = [
            [],
            {"films": self.good["films"]},
            {**self.good, "films": self.good["films"][:-1]},
            {**self.good, "films": self.good["films"][::-1]},
            {**self.good, "films": self.good["films"] + [self.good["films"][0]]},
            changed(0, entry="Grainy Film"),
            changed(0, label="A label that is far too long"),
            changed(0, label=""),
            changed(0, fit="../outside.npz"),
            changed(0, fit="/abs/fit.npz"),
            {**self.good, "specs": {**self.good["specs"], "films": "elsewhere/x.json"}},
            {**self.good, "specs": {**self.good["specs"], "labels": "../x.json"}},
            {**self.good, "specs": {"films": "patches/a.json"}},
        ]
        for raw in bad:
            with self.subTest(raw=str(raw)[:60]), self.assertRaises(BuildError):
                self.load(raw)
        self.paths.films.unlink()
        with self.assertRaises(BuildError):
            films.load_films(self.paths)


@unittest.skipUnless(HAVE_STOCK, "stock firmware not present")
class RealFirmwareLooksTests(unittest.TestCase):
    def copy_of_the_repository(self) -> RepoPaths:
        """Return a temporary repository with its own looks/ and patches/."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        paths = RepoPaths(Path(folder))
        (paths.root / "firmware").symlink_to(ROOT / "firmware")
        for name in ("looks", "builds"):
            shutil.copytree(ROOT / name, paths.root / name)
        shutil.copytree(
            ROOT / "patches",
            paths.root / "patches",
            ignore=shutil.ignore_patterns("history"),
        )
        shutil.copy(PATHS.pinned, paths.pinned)
        return paths

    def test_the_committed_specs_are_the_generated_ones(self) -> None:
        self.assertEqual(generate.stale(PATHS), [], "run: uv run epm2mod looks --write")
        self.assertEqual(generate.write(self.copy_of_the_repository()), [])

    def test_film_ops_refuse_a_bad_fit(self) -> None:
        program = generate.Program(
            container.parse(stock.read_stock(PATHS)).blocks[0].payload
        )
        film = films.load_films(PATHS).films[0]
        self.assertEqual(len(generate.film_ops(program, film, good_fit())), 3 + 5)
        for change in (
            {"G": np.zeros((3, 100))},
            {"gain": np.array(70000)},
            {"gain": np.array(260.5)},
            {"S": np.zeros(5)},
            {"A": np.full((3, 3), 40000)},
        ):
            with self.subTest(change=list(change)), self.assertRaises(BuildError):
                generate.film_ops(program, film, {**good_fit(), **change})
        with self.assertRaises(BuildError):
            generate.film_ops(
                program, film, {k: v for k, v in good_fit().items() if k != "H"}
            )
        with self.assertRaises(BuildError):
            program.read(0, 4)

    def test_a_changed_look_loses_its_test_status_and_breaks_the_tested_build(
        self,
    ) -> None:
        paths = self.copy_of_the_repository()
        film_list = films.load_films(paths)
        fit_path = paths.resolve(film_list.films[0].fit)
        with np.load(fit_path) as archive:
            arrays = {key: archive[key] for key in archive.files}
        arrays["gain"] = arrays["gain"] + 1
        np.savez(fit_path, **arrays)

        self.assertEqual(generate.stale(paths), [film_list.films_spec])
        before = read_json(paths.resolve(film_list.labels_spec))
        self.assertEqual(generate.write(paths), [film_list.films_spec])
        written = read_json(paths.resolve(film_list.films_spec))
        self.assertEqual(written["status"], generate.NEW_STATUS)
        self.assertEqual(read_json(paths.resolve(film_list.labels_spec)), before)
        self.assertEqual(generate.stale(paths), [])

        pinned = builds.pinned_description(paths)
        with self.assertRaises(BuildError):  # the recorded sha256 no longer fits
            pipeline.build_image(paths, pinned, stock.read_stock(paths))

    def test_a_missing_or_broken_fit_file(self) -> None:
        paths = self.copy_of_the_repository()
        fit_path = paths.resolve(films.load_films(paths).films[0].fit)
        fit_path.write_bytes(b"not an archive")
        with self.assertRaises(BuildError):
            generate.generate(paths)
        fit_path.unlink()
        with self.assertRaises(BuildError):
            generate.generate(paths)


if __name__ == "__main__":
    unittest.main()

"""Tests of the film-spec generator, ``epm2mod.looks``.

    uv run python -m unittest discover -s tests

They need numpy. Most tests use a made-up firmware (``SyntheticRepo``) that has
tables at the addresses of the film slots, so they run on a clean clone.
``RealFirmwareLooksTests`` needs the stock firmware file and is skipped
without it.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT, make_container  # noqa: E402

try:
    import numpy as np
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("numpy is not installed") from None

from epm2mod import builds, cli, container, paths as paths_module  # noqa: E402
from epm2mod import pipeline, spec, stock  # noqa: E402
from epm2mod.errors import BuildError, StockError  # noqa: E402
from epm2mod.fileio import read_json, write_json  # noqa: E402
from epm2mod.hashing import sha256_bytes  # noqa: E402
from epm2mod.looks import films, generate, slots  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402
from epm2mod.spec import BytesOp  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()
UTF16 = "utf-16-le"


def good_fit() -> dict[str, Any]:
    """Return the arrays of a well-formed fit."""
    knots = np.array([np.arange(16) * 17, np.arange(16) * 17, np.full(16, 128)])
    return {
        "G": np.tile(np.arange(1024, dtype=float), (3, 1)) * 0.9,
        "gain": np.array(260),
        "S": np.arange(6),
        "H": -np.arange(6),
        "A": np.array([[250, 3, 3], [3, 250, 3], [3, 3, 250]]),
        "Cb": knots,
        "Cr": knots,
        "Cb_slope17": np.full(17, 128),
        "Cr_slope17": np.full(17, 128),
    }


def synthetic_firmware() -> bytes:
    """Return a made-up firmware that the generator can work on.

    Block 0 is as large as the generator needs and holds, at the real
    addresses: the record of the default tone tables, the tone records of the
    two slots that use records, the identity matrix where an earlier spec
    creates a matrix table, and the identity look table. Every tone table is a
    rising ramp. Block 1 holds the seven menu names as whole strings.
    """
    base = slots.BLOCK0_BASE
    highest = max(max(slot.tone.addresses) for slot in slots.SLOTS)
    size = (highest + slots.TABLE_BYTES - base + 0xFFF) & ~0xFFF
    program = bytearray(size)
    ramp = struct.pack(f"<{slots.TABLE_ENTRIES}H", *range(0, 1024, 4))

    def put(address: int, data: bytes) -> None:
        offset = address - base
        program[offset : offset + len(data)] = data

    free = base + 0x10000  # below every address that the slots use
    records = [slots.DEFAULT_RECORD]
    for slot in slots.SLOTS:
        if isinstance(slot.tone, slots.Records):
            records += slot.tone.addresses
        if slot.matrix_is_new:
            put(slot.matrix, struct.pack("<9h", *slots.IDENTITY_MATRIX))
    for record in records:
        tables = [free + slots.TABLE_BYTES * i for i in range(slots.RECORD_TABLES)]
        free += slots.TABLE_BYTES * slots.RECORD_TABLES
        put(record, struct.pack(f"<{slots.RECORD_TABLES}I", *tables))
        for table in tables:
            put(table, ramp)
    put(slots.IDENTITY_LOOK, ramp)

    names = "\0" + "\0".join(slot.entry for slot in slots.SLOTS) + "\0\0"
    text = names.encode(UTF16)
    text += bytes(-len(text) % container.ROW)
    return make_container([bytes(program), text])


class SyntheticRepo:
    """A repository in a temporary folder: made-up firmware, film list and fits."""

    firmware: bytes | None = None

    def __init__(self, folder: Path) -> None:
        if SyntheticRepo.firmware is None:
            SyntheticRepo.firmware = synthetic_firmware()
        data = SyntheticRepo.firmware
        self.paths = RepoPaths(folder)
        self.stock = stock.StockFirmware(
            file_name="SYNTHETIC.BIN",
            relative_path="firmware/SYNTHETIC.BIN",
            size=len(data),
            sha256=sha256_bytes(data),
            model_id="1010",
            hard_code="OLYE101000000000",
            card_name="E1019999.BIN",
        )
        stock_file = self.paths.resolve(self.stock.relative_path)
        stock_file.parent.mkdir(parents=True)
        stock_file.write_bytes(data)
        self.paths.films.parent.mkdir(parents=True)
        shutil.copy(PATHS.films, self.paths.films)
        self.film_list = films.load_films(self.paths)
        for film in self.film_list.films:
            self.save_fit(film, good_fit())

    def save_fit(self, film: films.Film, arrays: dict[str, Any]) -> None:
        """Write a fit file for a film."""
        path = self.paths.resolve(film.fit)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, **arrays)

    def spec_json(self, relative: str) -> dict[str, Any]:
        """Return the JSON of a spec file of this repository."""
        raw: dict[str, Any] = read_json(self.paths.resolve(relative))
        return raw


class SyntheticCase(unittest.TestCase):
    """A test case with a fresh synthetic repository."""

    def setUp(self) -> None:
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.repo = SyntheticRepo(Path(folder))
        self.paths = self.repo.paths

    def generate(self) -> list[generate.GeneratedSpec]:
        return generate.generate(self.paths, self.repo.stock)

    def stale(self) -> list[str]:
        return generate.stale(self.paths, self.repo.stock)

    def write(self) -> list[str]:
        return generate.write(self.paths, self.repo.stock)


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
        bad: list[tuple[list[Any], int]] = [
            ([1.5, 2.0], 2),
            ([1.0], 2),
            ([1.0, 9.0], 2),
            ([1.0, float("nan")], 2),
            ([1.0, float("inf")], 2),
            (["a", "b"], 2),
        ]
        for values, count in bad:
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
            {"Cb": np.full((2, 16), np.nan)},
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
        wide = films.Film("Diorama", "x", "slide", "\U0001f39e", "x.npz")
        self.assertEqual(
            generate.label_ops(block, [wide])[0].new, text("\U0001f39e\0\0\0\0\0")
        )

    def test_the_slots(self) -> None:
        self.assertEqual(slots.slot_for("Diorama").entry, "Diorama")
        with self.assertRaises(KeyError):
            slots.slot_for("Grainy Film")
        entries = [slot.entry for slot in slots.SLOTS]
        self.assertEqual(len(set(entries)), len(entries))
        used: list[range] = []
        for slot in slots.SLOTS:
            used += [range(slot.saturation, slot.saturation + 4)]
            used += [range(a, a + 12) for a in slot.six_axis]
            used += [range(slot.matrix, slot.matrix + 18)]
            used += [range(slot.chroma, slot.chroma + 97)]
            if isinstance(slot.tone, slots.Tables):
                used += [range(a, a + slots.TABLE_BYTES) for a in slot.tone.addresses]
        used.sort(key=lambda r: r.start)
        for first, second in zip(used, used[1:]):
            self.assertLessEqual(first.stop, second.start, hex(second.start))

    def test_generated_fields(self) -> None:
        op = BytesOp(0, 16, b"\x00", b"\x01")
        made = generate.GeneratedSpec(
            "data/specs/x-1.json", "text", (op,), "a" * 64, "credit"
        )
        fields = made.generated_fields(stock.EPM2_V16)
        self.assertEqual(
            list(fields),
            [
                "name",
                "attribution",
                "description",
                "ops",
                "base",
                "base_sha256",
                "inputs_sha256",
            ],
        )
        self.assertEqual(fields["name"], "x-1")
        plain = generate.GeneratedSpec("data/specs/y.json", "text", (op,), "a" * 64)
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

        specs = self.good["specs"]
        bad: list[Any] = [
            [],
            {"films": self.good["films"]},
            {**self.good, "films": self.good["films"][:-1]},
            {**self.good, "films": self.good["films"][::-1]},
            {**self.good, "films": self.good["films"] + [self.good["films"][0]]},
            {**self.good, "films": ["not an object"]},
            {**self.good, "note": "an unknown key"},
            changed(0, entry="Grainy Film"),
            changed(0, label="A label that is far too long"),
            changed(0, label=""),
            changed(0, label="Por\0tra"),
            changed(0, label="\ud800"),
            changed(0, label="Portra\U0001f39e"),  # 7 characters, 8 UTF-16 units
            changed(3, label="\U0001f39e" * 6),  # 6 characters, 12 units, entry 10
            changed(0, medium=5),
            changed(0, fit="../outside.npz"),
            changed(0, fit="/abs/fit.npz"),
            changed(0, fits="data/films/fits/portra.npz"),
            {**self.good, "specs": {**specs, "films": "elsewhere/x.json"}},
            {**self.good, "specs": {**specs, "labels": "../x.json"}},
            {**self.good, "specs": {**specs, "labels": specs["films"]}},
            {**self.good, "specs": {**specs, "extra": "data/specs/x.json"}},
            {**self.good, "specs": {"films": "data/specs/a.json"}},
        ]
        for raw in bad:
            with self.subTest(raw=str(raw)[:60]), self.assertRaises(BuildError):
                self.load(raw)
        self.paths.films.unlink()
        with self.assertRaises(BuildError):
            films.load_films(self.paths)

    def test_a_label_as_long_as_the_entry_is_accepted(self) -> None:
        raw: dict[str, Any] = json.loads(json.dumps(self.good))
        raw["films"][0]["label"] = "Portra!"  # 'Pop Art' has 7 characters
        self.assertEqual(self.load(raw).films[0].label, "Portra!")


class GeneratorTests(SyntheticCase):
    def test_three_specs_that_fit_the_firmware(self) -> None:
        made = self.generate()
        film_list = self.repo.film_list
        self.assertEqual([s.path for s in made], list(film_list.spec_paths))
        looks, labels, structure = made
        digest = films.inputs_digest(self.paths, film_list)
        self.assertTrue(all(s.inputs_sha256 == digest for s in made))
        # Tables slots: 3 tables; Records slots: 3 records of 8 tables; 5 more each.
        self.assertEqual(len(looks.ops), 5 * (3 + 5) + 2 * (24 + 5))
        self.assertEqual(len(labels.ops), len(slots.SLOTS))
        self.assertEqual(len(structure.ops), 3 + 2)
        self.assertEqual(looks.attribution, generate.ATTRIBUTION)

        self.assertEqual(self.write(), list(film_list.spec_paths))
        loaded = [spec.load_spec(self.paths.resolve(s.path)) for s in made]
        assert SyntheticRepo.firmware is not None
        applied = spec.apply_specs(SyntheticRepo.firmware, loaded)
        parsed = container.parse(applied.image)
        self.assertTrue(parsed.checksums_ok)
        program = generate.Program(parsed.blocks[generate.PROGRAM_BLOCK].payload)
        pop_art = slots.slot_for("Pop Art")
        self.assertEqual(
            struct.unpack("<9h", program.read(pop_art.matrix, 18)),
            (250, 3, 3, 3, 250, 3, 3, 3, 250),
        )
        self.assertEqual(
            struct.unpack("<2H", program.read(pop_art.saturation, 4)), (260, 260)
        )
        assert isinstance(pop_art.tone, slots.Tables)
        table = program.table(pop_art.tone.addresses[0])
        # the default ramp 0, 4, 8, ... through the fit's curve y = 0.9 x
        self.assertEqual(list(table[:4]), [0.0, 4.0, 7.0, 11.0])
        text = parsed.blocks[generate.TEXT_BLOCK].payload.decode(UTF16)
        for film in film_list.films:
            self.assertIn(f"\0{film.label}\0", text)
            self.assertNotIn(f"\0{film.entry}\0", text)

    def test_an_operation_that_changes_nothing_is_left_out(self) -> None:
        film = self.repo.film_list.films[0]
        fit = good_fit()
        fit["A"] = np.array(slots.IDENTITY_MATRIX)  # what is there already
        self.repo.save_fit(film, fit)
        looks = self.generate()[0]
        matrix_offset = slots.slot_for(film.entry).matrix - slots.BLOCK0_BASE
        self.assertNotIn(
            matrix_offset, [op.offset for op in looks.ops if isinstance(op, BytesOp)]
        )

    def test_write_keeps_notes_and_resets_the_status_when_operations_change(
        self,
    ) -> None:
        film_list = self.repo.film_list
        self.assertEqual(self.stale(), list(film_list.spec_paths))
        self.write()
        self.assertEqual(self.stale(), [])
        self.assertEqual(self.write(), [])
        for spec_path in film_list.spec_paths:
            raw = self.repo.spec_json(spec_path)
            self.assertEqual(raw["status"], generate.NEW_STATUS)
            raw.update(status="camera-tested", expected_sha256="a" * 64, _note="kept")
            write_json(self.paths.resolve(spec_path), raw)
        self.assertEqual(self.stale(), [])  # notes are not generated fields

        fit = good_fit()
        fit["gain"] = np.array(300)
        self.repo.save_fit(film_list.films[0], fit)
        # The inputs changed, so every spec records a new digest ...
        self.assertEqual(self.write(), list(film_list.spec_paths))
        looks = self.repo.spec_json(film_list.films_spec)
        labels = self.repo.spec_json(film_list.labels_spec)
        # ... but only the spec whose operations changed loses its test record.
        self.assertEqual(looks["status"], generate.NEW_STATUS)
        self.assertNotIn("expected_sha256", looks)
        self.assertEqual(looks["_note"], "kept")
        self.assertEqual(labels["status"], "camera-tested")
        self.assertEqual(labels["expected_sha256"], "a" * 64)
        self.assertEqual(films.specs_with_other_inputs(self.paths), [])

    def test_a_bad_fit_is_refused(self) -> None:
        film = self.repo.film_list.films[0]
        missing_h = {k: v for k, v in good_fit().items() if k != "H"}
        changes: list[dict[str, Any]] = [
            {"G": np.zeros((3, 100))},
            {"G": np.full((3, 1024), np.nan)},
            {"G": np.full((3, 1024), "text")},
            {"gain": np.array(70000)},
            {"gain": np.array(260.5)},
            {"gain": np.array(np.inf)},
            {"S": np.zeros(5)},
            {"A": np.full((3, 3), 40000)},
        ]
        for arrays in [{**good_fit(), **change} for change in changes] + [missing_h]:
            self.repo.save_fit(film, arrays)
            with self.subTest(keys=sorted(arrays)), self.assertRaises(BuildError):
                self.generate()

    def test_a_fit_file_that_is_not_an_archive_is_refused(self) -> None:
        path = self.paths.resolve(self.repo.film_list.films[0].fit)
        single = io.BytesIO()
        np.save(single, np.zeros(3))
        for content in (b"not an archive", b"PK\x03\x04 cut short", single.getvalue()):
            path.write_bytes(content)
            with self.subTest(content=content[:8]), self.assertRaises(BuildError):
                self.generate()
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("Cb", b"not an array")
        with self.assertRaisesRegex(BuildError, "not a numpy array"):
            self.generate()
        path.unlink()
        with self.assertRaises(BuildError):
            self.generate()

    def test_an_address_outside_the_program_is_refused(self) -> None:
        program = generate.Program(bytes(64))
        self.assertEqual(program.read(slots.BLOCK0_BASE + 60, 4), bytes(4))
        for address in (0, slots.BLOCK0_BASE - 1, slots.BLOCK0_BASE + 61):
            with self.subTest(address=address), self.assertRaises(BuildError):
                program.read(address, 4)

    def test_the_stock_firmware_is_needed(self) -> None:
        self.paths.resolve(self.repo.stock.relative_path).unlink()
        with self.assertRaises(StockError):
            self.generate()

    def test_the_generate_command_writes_the_specs(self) -> None:
        pinned = mock.Mock(stock_firmware=self.repo.stock)

        def run(*argv: str) -> tuple[int, str]:
            out = io.StringIO()
            env = {paths_module.ROOT_ENV: str(self.paths.root)}
            with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
                with (
                    mock.patch.object(RepoPaths, "pinned_build", return_value=pinned),
                    mock.patch("epm2mod.readme.rewrite", return_value=[]),
                    mock.patch("epm2mod.readme.stale", return_value=[]),
                    mock.patch("epm2mod.readme.feature_problems", return_value=[]),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    return cli.main(["generate", *argv]), out.getvalue()

        self.paths.pinned.write_text("{}")  # marks the top of the repository
        status, text = run("--check")
        self.assertEqual(status, 1, text)
        self.assertIn("differs from the generated spec", text)
        status, text = run()
        self.assertEqual(status, 0, text)
        self.assertEqual(text.count("wrote data/specs/"), 3)
        self.assertEqual(run("--check")[0], 0)
        self.assertEqual(run(), (0, "no spec changed\ndocuments: no change\n"))


@unittest.skipUnless(HAVE_STOCK, "stock firmware not present")
class RealFirmwareLooksTests(unittest.TestCase):
    def copy_of_the_repository(self) -> RepoPaths:
        """Return a temporary repository with its own data/films/ and data/specs/."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        paths = RepoPaths(Path(folder))
        (paths.root / "firmware").symlink_to(ROOT / "firmware")
        for name in ("films", "builds"):
            shutil.copytree(ROOT / "data" / name, paths.root / "data" / name)
        shutil.copytree(
            ROOT / "data" / "specs",
            paths.root / "data" / "specs",
            ignore=shutil.ignore_patterns("history"),
        )
        shutil.copy(PATHS.pinned, paths.pinned)
        return paths

    def test_the_committed_specs_are_the_generated_ones(self) -> None:
        self.assertEqual(
            generate.stale(PATHS, stock.EPM2_V16), [], "run: uv run epm2mod generate"
        )
        self.assertEqual(
            generate.write(self.copy_of_the_repository(), stock.EPM2_V16), []
        )

    def test_a_changed_look_loses_its_test_status_and_breaks_the_tested_build(
        self,
    ) -> None:
        paths = self.copy_of_the_repository()
        film_list = films.load_films(paths)
        fit_path = paths.resolve(film_list.films[0].fit)
        arrays: dict[str, Any] = dict(generate.load_fit(fit_path))
        arrays["gain"] = arrays["gain"] + 1
        np.savez(fit_path, **arrays)

        self.assertEqual(
            generate.stale(paths, stock.EPM2_V16), list(film_list.spec_paths)
        )
        self.assertEqual(
            generate.write(paths, stock.EPM2_V16), list(film_list.spec_paths)
        )
        written = read_json(paths.resolve(film_list.films_spec))
        self.assertEqual(written["status"], generate.NEW_STATUS)
        labels = read_json(paths.resolve(film_list.labels_spec))
        committed = read_json(PATHS.resolve(film_list.labels_spec))
        self.assertEqual(labels["ops"], committed["ops"])
        self.assertEqual(labels["status"], committed["status"])
        self.assertEqual(generate.stale(paths, stock.EPM2_V16), [])

        # log-menu: the last tested build with the films in the firmware (the pinned one loads them from the card)
        tested = builds.load_description(builds.description_path(paths, "log-menu"))
        specs = pipeline.load_specs(paths, tested)
        with self.assertRaises(BuildError):  # the recorded sha256 no longer fits
            pipeline.build_image(tested, specs, stock.read_stock(paths, stock.EPM2_V16))


if __name__ == "__main__":
    unittest.main()

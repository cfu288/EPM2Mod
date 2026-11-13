"""Tests of the ``epm2mod`` package.

    uv run python -m unittest discover -s tests

Tests that need the stock firmware file are skipped when it is absent; the
others use a small container that the tests build themselves.
"""

from __future__ import annotations

import datetime
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from epm2mod import builds, container, pipeline, readme, spec, stock  # noqa: E402
from epm2mod.errors import (
    BuildError,
    ContainerError,
    SpecError,
    StockError,
)  # noqa: E402
from epm2mod.hashing import sha256_bytes, sha256_file  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
STOCK_FILE = stock.stock_path(PATHS)
HAVE_STOCK = STOCK_FILE.is_file()


def tiny_container(payloads: List[bytes], tail: bytes = b"TAIL") -> bytes:
    """Return a valid container file with the given unscrambled payloads."""
    blocks = []
    for index, payload in enumerate(payloads):
        header = bytearray(32)
        header[0:2] = container.MAGIC
        struct.pack_into("<I", header, 8, 0x1000 * (index + 1))
        struct.pack_into("<I", header, 12, len(payload))
        struct.pack_into("<H", header, 20, 0x0100 + index)
        trailer = bytes(header[:28]) + bytes(4)
        blocks.append(container.Block(0, bytes(header), trailer, payload, False))
    return container.serialize(container.Container(blocks, tail))


def write_spec(folder: Path, name: str, stock_bytes: bytes, ops: list) -> Path:
    """Write a patch spec for ``stock_bytes`` and return its path."""
    path = folder / f"{name}.json"
    raw = {
        "name": name,
        "base": "x",
        "base_sha256": sha256_bytes(stock_bytes),
        "ops": ops,
    }
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


class ContainerTests(unittest.TestCase):
    def test_scramble_is_the_inverse_of_descramble(self) -> None:
        data = bytes(range(256)) * 4
        self.assertEqual(container.descramble(container.scramble(data)), data)
        self.assertNotEqual(container.scramble(data), data)

    def test_round_trip_of_a_built_container(self) -> None:
        payloads = [bytes(range(64)), b"\xff" * 32]
        data = tiny_container(payloads)
        parsed = container.parse(data)
        self.assertEqual([block.payload for block in parsed.blocks], payloads)
        self.assertEqual(parsed.tail, b"TAIL")
        self.assertTrue(parsed.checksums_ok)
        self.assertEqual(parsed.blocks[1].kind, 0x0101)
        self.assertEqual(parsed.blocks[1].load_address, 0x2000)
        self.assertEqual(parsed.blocks[1].offset, 64 + 64)
        self.assertEqual(container.serialize(parsed), data)

    def test_a_changed_byte_makes_the_checksum_wrong(self) -> None:
        data = bytearray(tiny_container([bytes(32)]))
        data[40] ^= 1
        self.assertFalse(container.parse(bytes(data)).checksums_ok)

    def test_serialize_makes_the_checksum_right_again(self) -> None:
        parsed = container.parse(tiny_container([bytes(32)]))
        changed = parsed.with_payloads([b"\x01" * 32])
        self.assertFalse(changed.checksums_ok)
        self.assertTrue(container.parse(container.serialize(changed)).checksums_ok)

    def test_errors(self) -> None:
        good = tiny_container([bytes(32)])
        with self.assertRaises(ContainerError):
            container.parse(b"not a container")
        with self.assertRaises(ContainerError):
            container.parse(good[:70])  # cut inside the block
        bad_length = bytearray(good)
        struct.pack_into("<I", bad_length, 12, 30)
        with self.assertRaises(ContainerError):
            container.parse(bytes(bad_length))
        with self.assertRaises(ContainerError):
            container.parse(good).blocks[0].with_payload(bytes(16))
        with self.assertRaises(ContainerError):
            container.parse(good).with_payloads([])
        with self.assertRaises(ContainerError):
            container.word_sum(b"abc")

    def test_describe(self) -> None:
        lines = container.describe(tiny_container([bytes(32)]))
        self.assertIn("checksum=OK", lines[0])
        self.assertTrue(lines[-1].startswith("tail len=4"))


class SpecTests(unittest.TestCase):
    def setUp(self) -> None:
        text = "Pop Art\0\0".encode("utf-16-le")
        self.stock = tiny_container([bytes(range(48)), (text * 2).ljust(48, b"\0")])

    def test_bytes_op_and_utf16_op(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = write_spec(
                Path(folder),
                "s",
                self.stock,
                [
                    {
                        "type": "bytes",
                        "block": 0,
                        "offset": "0x10",
                        "expect": "1011",
                        "new": "aabb",
                    },
                    {
                        "type": "utf16-replace-all",
                        "block": 1,
                        "old": "Pop Art",
                        "new": "Portra\0",
                        "count": 2,
                    },
                ],
            )
            applied = spec.apply_specs(self.stock, [spec.load_spec(path)])
        parsed = container.parse(applied.image)
        self.assertTrue(parsed.checksums_ok)
        self.assertEqual(parsed.blocks[0].payload[0x10:0x12], b"\xaa\xbb")
        self.assertEqual(
            parsed.blocks[1].payload.count("Portra".encode("utf-16-le")), 2
        )
        self.assertEqual(len(applied.image), len(self.stock))
        self.assertEqual(applied.log[0], "[s]")

    def test_a_later_spec_sees_the_bytes_of_an_earlier_one(self) -> None:
        first = spec.spec_from_json(
            {
                "name": "a",
                "base": "x",
                "base_sha256": sha256_bytes(self.stock),
                "ops": [
                    {
                        "type": "bytes",
                        "block": 0,
                        "offset": 0,
                        "expect": "00",
                        "new": "07",
                    }
                ],
            }
        )
        second = spec.spec_from_json(
            {
                "name": "b",
                "base": "x",
                "base_sha256": sha256_bytes(self.stock),
                "ops": [
                    {
                        "type": "bytes",
                        "block": 0,
                        "offset": 0,
                        "expect": "07",
                        "new": "09",
                    }
                ],
            }
        )
        image = spec.apply_specs(self.stock, [first, second]).image
        self.assertEqual(container.parse(image).blocks[0].payload[0], 9)
        with self.assertRaises(SpecError):
            spec.apply_specs(self.stock, [second, first])

    def test_refusals(self) -> None:
        base = {"name": "s", "base": "x", "base_sha256": sha256_bytes(self.stock)}
        cases = {
            "wrong bytes": [
                {"type": "bytes", "block": 0, "offset": 0, "expect": "ff", "new": "00"}
            ],
            "past the end": [
                {
                    "type": "bytes",
                    "block": 0,
                    "offset": 47,
                    "expect": "2f30",
                    "new": "0000",
                }
            ],
            "no such block": [
                {"type": "bytes", "block": 5, "offset": 0, "expect": "00", "new": "01"}
            ],
            "wrong count": [
                {
                    "type": "utf16-replace-all",
                    "block": 1,
                    "old": "Pop Art",
                    "new": "Portra\0",
                    "count": 3,
                }
            ],
        }
        for name, ops in cases.items():
            with self.subTest(name), self.assertRaises(SpecError):
                spec.apply_specs(
                    self.stock, [spec.spec_from_json({**base, "ops": ops})]
                )
        with self.assertRaises(SpecError):
            spec.apply_specs(self.stock, [])
        other_base = spec.spec_from_json({**base, "base_sha256": "0" * 64, "ops": []})
        with self.assertRaises(SpecError):
            spec.apply_specs(self.stock, [other_base])

    def test_malformed_specs(self) -> None:
        ok = {"type": "bytes", "block": 0, "offset": 0, "expect": "00", "new": "01"}
        bad_ops = [
            {**ok, "new": "0102"},
            {**ok, "expect": "zz"},
            {**ok, "offset": -1},
            {**ok, "offset": "x"},
            {**ok, "block": -1},
            {**ok, "block": True},
            {**ok, "type": "nope"},
            {**ok, "expect": "", "new": ""},
            {"type": "utf16-replace-all", "block": 0, "old": "ab", "new": "a"},
            {"type": "utf16-replace-all", "block": 0, "old": "", "new": ""},
            {
                "type": "utf16-replace-all",
                "block": 0,
                "old": "a",
                "new": "b",
                "count": -1,
            },
            "not an object",
        ]
        for op in bad_ops:
            with self.subTest(op=op), self.assertRaises(SpecError):
                spec.spec_from_json(
                    {"name": "s", "base": "x", "base_sha256": "0", "ops": [op]}
                )
        for raw in (
            {},
            {"name": "s"},
            [],
            {"name": 1, "base": "x", "base_sha256": "0", "ops": []},
        ):
            with self.subTest(raw=raw), self.assertRaises(SpecError):
                spec.spec_from_json(raw)  # type: ignore[arg-type]
        with self.assertRaises(SpecError):
            spec.load_spec(Path("/no/such/spec.json"))

    def test_op_json_round_trip(self) -> None:
        ops = [
            {
                "type": "bytes",
                "block": 0,
                "offset": "0x10",
                "expect": "00",
                "new": "01",
            },
            {
                "type": "utf16-replace-all",
                "block": 1,
                "old": "a",
                "new": "b",
                "count": 2,
            },
            {"type": "utf16-replace-all", "block": 1, "old": "a", "new": "b"},
        ]
        for raw in ops:
            self.assertEqual(spec.op_to_json(spec.op_from_json(raw, "op")), raw)


class BuildDescriptionTests(unittest.TestCase):
    GOOD = {"what": "Something", "specs": ["patches/a.json"]}

    def test_candidate_and_tested(self) -> None:
        candidate = builds.description_from_json("my-build", self.GOOD)
        self.assertFalse(candidate.tested)
        self.assertEqual(candidate.to_json(), self.GOOD)
        tested = candidate.as_tested("a" * 64, "2026-11-13")
        self.assertTrue(tested.tested)
        self.assertEqual(
            builds.description_from_json("my-build", tested.to_json()), tested
        )

    def test_refusals(self) -> None:
        bad = [
            {},
            {"what": "", "specs": ["a"]},
            {"what": "x", "specs": []},
            {"what": "x", "specs": ["a", "a"]},
            {"what": "x", "specs": ["a"], "sha256": "a" * 64},
            {
                "what": "x",
                "specs": ["a"],
                "sha256": "A" * 64,
                "camera_tested": "2026-11-13",
            },
            {
                "what": "x",
                "specs": ["a"],
                "sha256": "a" * 64,
                "camera_tested": "13/11/2026",
            },
            {"what": "x", "specs": ["a"], "name": "other"},
            ["not", "an", "object"],
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(BuildError):
                builds.description_from_json("b", raw)
        with self.assertRaises(BuildError):
            builds.description_from_json("Bad Name", self.GOOD)
        candidate = builds.description_from_json("b", self.GOOD)
        for sha, date in (("short", "2026-11-13"), ("a" * 64, "2026-13-40")):
            with self.assertRaises(BuildError):
                candidate.as_tested(sha, date)

    def test_pin_writes_the_description_and_the_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(Path(folder))
            candidate = builds.description_from_json("b", self.GOOD)
            with self.assertRaises(BuildError):
                builds.pin(paths, candidate)
            tested = candidate.as_tested("a" * 64, "2026-11-13")
            builds.pin(paths, tested)
            self.assertEqual(
                json.loads(paths.pinned.read_text()), {"build": "builds/b.json"}
            )
            self.assertEqual(builds.pinned_description(paths), tested)
            self.assertEqual(builds.all_descriptions(paths), [tested])
            paths.pinned.write_text(json.dumps({"build": "../elsewhere.json"}))
            with self.assertRaises(BuildError):
                builds.pinned_description(paths)

    def test_spec_paths_stay_inside_the_repository(self) -> None:
        for bad in (
            "../x.json",
            "/etc/x.json",
            "patches/../../x.json",
            "patches\\x.json",
        ):
            build = builds.description_from_json("b", {"what": "x", "specs": [bad]})
            with self.subTest(bad=bad), self.assertRaises(BuildError):
                pipeline.load_specs(PATHS, build)

    def test_the_repository_descriptions(self) -> None:
        pinned = builds.pinned_description(PATHS)
        names = [build.name for build in builds.all_descriptions(PATHS)]
        self.assertIn(pinned.name, names)
        for build in builds.all_descriptions(PATHS):
            for path in build.specs:
                self.assertTrue(PATHS.resolve(path).is_file(), f"{build.name}: {path}")
            pipeline.load_specs(PATHS, build)


class StockTests(unittest.TestCase):
    def test_catalog_request(self) -> None:
        when = datetime.datetime(2026, 1, 2, 3, 4, 5)
        body = stock.catalog_request(stock.EPM2_V16, when).decode()
        self.assertIn("<hard_code>OLYE101000000000</hard_code>", body)
        self.assertIn("<time>20260102030405</time>", body)
        self.assertIn("<serial_no>000000000</serial_no>", body)

    def test_download_url(self) -> None:
        def answer(model: str, name: str, url: str) -> bytes:
            return (
                "<r><firmware_info><model_id>%s</model_id><file_name>%s</file_name>"
                "<url>%s</url></firmware_info></r>" % (model, name, url)
            ).encode()

        name = stock.EPM2_V16.file_name
        good = answer("1010", name, "https://example.invalid/f.BIN")
        self.assertEqual(
            stock.download_url(good, stock.EPM2_V16), "https://example.invalid/f.BIN"
        )
        for bad in (
            answer("1420", name, "https://example.invalid/f.BIN"),
            answer("1010", "OTHER.BIN", "https://example.invalid/f.BIN"),
            answer("1010", name, "http://example.invalid/f.BIN"),
            b"<r></r>",
            b"not xml",
        ):
            with self.subTest(bad=bad), self.assertRaises(StockError):
                stock.download_url(bad, stock.EPM2_V16)

    def test_a_wrong_file_in_the_way_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(Path(folder))
            target = stock.stock_path(paths)
            target.parent.mkdir(parents=True)
            target.write_bytes(b"something else")
            with self.assertRaises(StockError):
                stock.fetch(paths)
            self.assertEqual(target.read_bytes(), b"something else")


class CardTests(unittest.TestCase):
    def test_copy_to_card(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "fw.BIN"
            image.write_bytes(b"firmware")
            card = Path(folder) / "card"
            card.mkdir()
            digest = sha256_file(image)
            target = pipeline.copy_to_card(image, digest, card, stock.EPM2_V16)
            self.assertEqual(target, card / "DCOLYMP" / "E1019999.BIN")
            self.assertEqual(target.read_bytes(), b"firmware")
            pipeline.copy_to_card(image, digest, card, stock.EPM2_V16)  # again: allowed
            (card / "DCOLYMP" / "OTHER.BIN").write_bytes(b"x")
            with self.assertRaises(BuildError):
                pipeline.copy_to_card(image, digest, card, stock.EPM2_V16)
            self.assertTrue((card / "DCOLYMP" / "OTHER.BIN").exists())
            with self.assertRaises(BuildError):
                pipeline.copy_to_card(
                    image, digest, Path(folder) / "none", stock.EPM2_V16
                )

    def test_a_copy_that_differs_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "fw.BIN"
            image.write_bytes(b"firmware")
            card = Path(folder) / "card"
            card.mkdir()
            with self.assertRaises(BuildError):
                pipeline.copy_to_card(image, "0" * 64, card, stock.EPM2_V16)
            self.assertFalse((card / "DCOLYMP" / "E1019999.BIN").exists())


class ReadmeTests(unittest.TestCase):
    def test_the_readme_is_up_to_date(self) -> None:
        self.assertTrue(readme.is_current(PATHS), "run: uv run epm2mod readme")

    def test_unknown_and_missing_blocks(self) -> None:
        with self.assertRaises(BuildError):
            readme.update(
                "<!-- BEGIN GENERATED: nope -->\n<!-- END GENERATED: nope -->", PATHS
            )
        with self.assertRaises(BuildError):
            readme.update("no markers at all", PATHS)

    def test_text_outside_the_markers_is_kept(self) -> None:
        text = PATHS.readme.read_text(encoding="utf-8")
        marked = "BEFORE\n" + text + "\nAFTER"
        fresh = readme.update(marked, PATHS)
        self.assertTrue(fresh.startswith("BEFORE\n") and fresh.endswith("\nAFTER"))


@unittest.skipUnless(HAVE_STOCK, "stock firmware not present")
class StockFirmwareTests(unittest.TestCase):
    def test_the_stock_file_round_trips(self) -> None:
        data = STOCK_FILE.read_bytes()
        self.assertEqual(sha256_bytes(data), stock.EPM2_V16.sha256)
        self.assertEqual(len(data), stock.EPM2_V16.size)
        parsed = container.parse(data)
        self.assertTrue(parsed.checksums_ok)
        self.assertEqual(container.serialize(parsed), data)

    def test_every_tested_build_gives_its_sha256(self) -> None:
        data = STOCK_FILE.read_bytes()
        for build in builds.all_descriptions(PATHS):
            if not build.tested:
                continue
            with self.subTest(build=build.name):
                image = spec.apply_specs(data, pipeline.load_specs(PATHS, build)).image
                self.assertEqual(sha256_bytes(image), build.sha256)

    def test_make_refuses_a_result_with_another_sha256(self) -> None:
        pinned = builds.pinned_description(PATHS)
        wrong = pinned.as_tested("0" * 64, "2026-01-01")
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(Path(folder))
            (paths.root / "firmware").symlink_to(ROOT / "firmware")
            (paths.root / "patches").symlink_to(ROOT / "patches")
            (paths.root / "experiments").symlink_to(ROOT / "experiments")
            with self.assertRaises(BuildError):
                pipeline.make(paths, wrong)
            self.assertFalse(paths.output.exists())
            result = pipeline.make(paths, pinned)
            self.assertEqual(sha256_file(result.image), pinned.sha256)
            self.assertEqual(sha256_file(result.card_copy), pinned.sha256)
            self.assertIsNone(result.on_card)

    def test_the_film_specs_are_the_generated_ones(self) -> None:
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy not installed")
        from epm2mod.looks import generate

        self.assertEqual(generate.stale(PATHS), [])


if __name__ == "__main__":
    unittest.main()

"""Tests of the ``epm2mod`` package.

    uv run python -m unittest discover -s tests

Most tests need nothing but the repository: they build a small firmware
container and a small repository in a temporary folder. The tests in
``RealFirmwareTests`` need the stock firmware file and are skipped without it.
"""

from __future__ import annotations

import contextlib
import datetime
import http.client
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Iterator
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from epm2mod import (  # noqa: E402
    builds,
    cli,
    container,
    fileio,
    paths as paths_module,
    pipeline,
    readme,
    spec,
    stock,
)
from epm2mod.errors import (  # noqa: E402
    BuildError,
    ContainerError,
    Epm2ModError,
    FileError,
    RepositoryError,
    SpecError,
    StockError,
)
from epm2mod.hashing import is_sha256, sha256_bytes  # noqa: E402
from epm2mod.paths import RepoPaths, is_repo_relative  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS).is_file()
TODAY = datetime.date(2026, 11, 20)


def tiny_container(payloads: list[bytes], tail: bytes = b"TAIL") -> bytes:
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


TINY = tiny_container(
    [bytes(range(48)), ("Pop Art\0\0".encode("utf-16-le") * 2).ljust(48, b"\0")]
)
TINY_STOCK = stock.StockFirmware(
    file_name="TINY.BIN",
    relative_path="firmware/TINY.BIN",
    size=len(TINY),
    sha256=sha256_bytes(TINY),
    model_id="1010",
    hard_code="OLYE101000000000",
    card_name="E1019999.BIN",
)
BYTE_OP = {
    "type": "bytes",
    "block": 0,
    "offset": "0x10",
    "expect": "1011",
    "new": "aabb",
}


def spec_json(name: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the JSON of a patch spec for the tiny firmware."""
    return {"name": name, "base": "x", "base_sha256": TINY_STOCK.sha256, "ops": ops}


class TinyRepo:
    """A small repository in a temporary folder: tiny stock, one spec, one build."""

    def __init__(self, folder: Path) -> None:
        self.paths = RepoPaths(folder)
        self.write("firmware/TINY.BIN", TINY)
        self.write_json("patches/a.json", spec_json("a", [BYTE_OP]))
        applied = spec.apply_specs(
            TINY, [spec.spec_from_json(spec_json("a", [BYTE_OP]))]
        )
        self.image = applied.image
        self.sha256 = sha256_bytes(self.image)
        self.tested = builds.BuildDescription(
            "good", "A tiny build", ("patches/a.json",), self.sha256, "2026-11-13"
        )
        self.candidate = builds.BuildDescription(
            "new", "A tiny candidate", ("patches/a.json",)
        )
        builds.pin(self.paths, self.tested)
        builds.save_description(self.paths, self.candidate)

    def write(self, relative: str, data: bytes) -> Path:
        path = self.paths.resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def write_json(self, relative: str, raw: Any) -> Path:
        return self.write(relative, json.dumps(raw).encode())

    def free_space_tool(self, status: int) -> None:
        """Install a stand-in for tools/freespace.py that exits with ``status``."""
        script = f"import sys\nprint('check: stand-in')\nsys.exit({status})\n"
        self.write("tools/freespace.py", script.encode())

    def outputs(self) -> list[str]:
        """Return the files under build/, relative to it."""
        out = self.paths.output
        return sorted(
            p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()
        )


class RepoCase(unittest.TestCase):
    """A test case with a fresh tiny repository."""

    def setUp(self) -> None:
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.repo = TinyRepo(Path(folder) / "repo")
        self.card = Path(folder) / "card"
        self.card.mkdir()

    def make(
        self, description: builds.BuildDescription, **kw: Any
    ) -> pipeline.MakeResult:
        return pipeline.make(self.repo.paths, description, stock=TINY_STOCK, **kw)


@contextlib.contextmanager
def answers(*bodies: Any) -> Iterator[mock.MagicMock]:
    """Make ``urlopen`` in the stock module return the given bodies, in order.

    A body is bytes, or an exception to raise from ``read``, or an exception
    class to raise from ``urlopen`` itself.
    """
    responses = []
    for body in bodies:
        if isinstance(body, type):
            responses.append(body("refused"))
            continue
        response = mock.MagicMock()
        response.__enter__.return_value = response
        if isinstance(body, BaseException):
            response.read.side_effect = body
        else:
            response.read.side_effect = io.BytesIO(body).read
        responses.append(response)
    with mock.patch(
        "epm2mod.stock.urllib.request.urlopen", side_effect=responses
    ) as opened:
        yield opened


def catalog_answer(
    model: str = "1010", name: str = "TINY.BIN", url: str = "https://example.invalid/f"
) -> bytes:
    return (
        f"<r><firmware_info><model_id>{model}</model_id><file_name>{name}</file_name>"
        f"<url>{url}</url></firmware_info></r>"
    ).encode()


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
        two = tiny_container([bytes(32), bytes(32)])
        bad_length = bytearray(good)
        struct.pack_into("<I", bad_length, 12, 30)
        for data in (
            b"not a container",
            b"",
            good[:70],  # cut inside the payload
            two[: 96 + 40],  # cut inside the second block's header
            bytes(bad_length),
        ):
            with self.subTest(length=len(data)), self.assertRaises(ContainerError):
                container.parse(data)
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
    def apply(self, *ops: dict[str, Any]) -> spec.Applied:
        return spec.apply_specs(TINY, [spec.spec_from_json(spec_json("s", list(ops)))])

    def test_bytes_op_and_utf16_op(self) -> None:
        text_op = {
            "type": "utf16-replace-all",
            "block": 1,
            "old": "Pop Art",
            "new": "Portra\0",
            "count": 2,
        }
        applied = self.apply(BYTE_OP, text_op)
        parsed = container.parse(applied.image)
        self.assertTrue(parsed.checksums_ok)
        self.assertEqual(parsed.blocks[0].payload[0x10:0x12], b"\xaa\xbb")
        self.assertEqual(
            parsed.blocks[1].payload.count("Portra".encode("utf-16-le")), 2
        )
        self.assertEqual(len(applied.image), len(TINY))
        self.assertEqual(applied.log[0], "[s]")
        self.assertEqual(
            applied.changed_bytes, spec.count_differences(TINY, applied.image)
        )
        self.assertGreater(applied.changed_bytes, 0)

    def test_a_later_spec_sees_the_bytes_of_an_earlier_one(self) -> None:
        def one(name: str, expect: str, new: str) -> spec.PatchSpec:
            op = {
                "type": "bytes",
                "block": 0,
                "offset": 0,
                "expect": expect,
                "new": new,
            }
            return spec.spec_from_json(spec_json(name, [op]))

        first, second = one("a", "00", "07"), one("b", "07", "09")
        image = spec.apply_specs(TINY, [first, second]).image
        self.assertEqual(container.parse(image).blocks[0].payload[0], 9)
        with self.assertRaises(SpecError):
            spec.apply_specs(TINY, [second, first])

    def test_text_copies_do_not_overlap(self) -> None:
        text = "AAAAAA".encode("utf-16-le").ljust(32, b"\0")
        data = tiny_container([text])
        raw = {
            "name": "s",
            "base": "x",
            "base_sha256": sha256_bytes(data),
            "ops": [
                {"type": "utf16-replace-all", "block": 0, "old": "AAAA", "new": "WXYZ"}
            ],
        }
        applied = spec.apply_specs(data, [spec.spec_from_json(raw)])
        payload = container.parse(applied.image).blocks[0].payload
        self.assertTrue(payload.startswith("WXYZAA".encode("utf-16-le")))
        self.assertTrue(applied.log[1].endswith("x1"))

    def test_refusals(self) -> None:
        cases: dict[str, dict[str, Any]] = {
            "wrong bytes": {
                "type": "bytes",
                "block": 0,
                "offset": 0,
                "expect": "ff",
                "new": "00",
            },
            "past the end": {
                "type": "bytes",
                "block": 0,
                "offset": 47,
                "expect": "2f30",
                "new": "0000",
            },
            "no such block": {
                "type": "bytes",
                "block": 5,
                "offset": 0,
                "expect": "00",
                "new": "01",
            },
            "wrong count": {
                "type": "utf16-replace-all",
                "block": 1,
                "old": "Pop Art",
                "new": "Portra\0",
                "count": 3,
            },
            "no copy": {
                "type": "utf16-replace-all",
                "block": 1,
                "old": "Diorama",
                "new": "Velvia\0",
            },
        }
        for name, op in cases.items():
            with self.subTest(name), self.assertRaises(SpecError):
                self.apply(op)
        with self.assertRaises(SpecError):
            spec.apply_specs(TINY, [])
        other = spec.spec_from_json({**spec_json("s", []), "base_sha256": "0" * 64})
        with self.assertRaises(SpecError):
            spec.apply_specs(TINY, [other])
        damaged = bytearray(TINY)
        damaged[40] ^= 1
        for_damaged = spec.spec_from_json(
            {**spec_json("s", [BYTE_OP]), "base_sha256": sha256_bytes(bytes(damaged))}
        )
        with self.assertRaises(ContainerError):
            spec.apply_specs(bytes(damaged), [for_damaged])

    def test_malformed_specs(self) -> None:
        ok: dict[str, Any] = {
            "type": "bytes",
            "block": 0,
            "offset": 0,
            "expect": "00",
            "new": "01",
        }
        text: dict[str, Any] = {
            "type": "utf16-replace-all",
            "block": 0,
            "old": "a",
            "new": "b",
        }
        bad_ops: list[Any] = [
            {**ok, "new": "0102"},
            {**ok, "expect": "zz"},
            {**ok, "offset": -1},
            {**ok, "offset": "x"},
            {**ok, "offset": 1.9},
            {**ok, "offset": 1e999},
            {**ok, "offset": True},
            {**ok, "offset": None},
            {k: v for k, v in ok.items() if k != "offset"},
            {**ok, "block": -1},
            {**ok, "block": True},
            {**ok, "type": "nope"},
            {**ok, "expect": "", "new": ""},
            {**text, "old": "ab", "new": "a"},
            {**text, "old": "", "new": ""},
            {**text, "count": 0},
            {**text, "count": 1.5},
            {**text, "old": "\ud800", "new": "b"},
            "not an object",
        ]
        for op in bad_ops:
            with self.subTest(op=op), self.assertRaises(SpecError):
                spec.spec_from_json(spec_json("s", [op]))
        good = spec_json("s", [])
        bad_specs: list[Any] = [
            {},
            [],
            {k: v for k, v in good.items() if k != "name"},
            {**good, "name": 1},
            {**good, "base_sha256": "0"},
            {**good, "expected_sha256": "ABC"},
            {**good, "description": 5},
            {**good, "ops": "none"},
        ]
        for raw in bad_specs:
            with self.subTest(raw=raw), self.assertRaises(SpecError):
                spec.spec_from_json(raw)
        with self.assertRaises(SpecError):
            spec.load_spec(Path("/no/such/spec.json"))

    def test_op_json_round_trip(self) -> None:
        ops: list[dict[str, Any]] = [
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

    def test_count_differences(self) -> None:
        a = bytes(200_000)
        b = bytearray(a)
        b[5] = b[70_000] = b[199_999] = 1
        self.assertEqual(spec.count_differences(a, bytes(b)), 3)
        with self.assertRaises(ValueError):
            spec.count_differences(b"a", b"ab")


class PathAndFileTests(unittest.TestCase):
    def test_is_repo_relative(self) -> None:
        for good in ("patches/a.json", "a", "looks/fits/x.npz"):
            self.assertTrue(is_repo_relative(good), good)
        for bad in (
            "",
            "/etc/x",
            "../x",
            "a/../b",
            "./a",
            "a//b",
            "a\\b",
            "C:/x",
            "a/",
        ):
            self.assertFalse(is_repo_relative(bad), bad)

    def test_relative_is_for_messages_and_never_fails(self) -> None:
        self.assertEqual(PATHS.relative(ROOT / "build" / "x.BIN"), "build/x.BIN")
        self.assertEqual(
            PATHS.relative(Path("/elsewhere/x")), str(Path("/elsewhere/x"))
        )

    def test_find_root(self) -> None:
        self.assertEqual(paths_module.find_root(ROOT / "src"), ROOT)
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.dict(os.environ, {paths_module.ROOT_ENV: folder}):
                with self.assertRaises(RepositoryError):
                    paths_module.find_root()
            (Path(folder) / paths_module.ROOT_MARKER).write_text("{}")
            with mock.patch.dict(os.environ, {paths_module.ROOT_ENV: folder}):
                self.assertEqual(paths_module.find_root(), Path(folder).absolute())

    def test_a_failed_write_keeps_the_old_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "sub" / "f.bin"
            fileio.write_bytes(target, b"old")
            with mock.patch(
                "epm2mod.fileio.os.replace", side_effect=OSError(28, "No space")
            ):
                with self.assertRaises(FileError):
                    fileio.write_bytes(target, b"new")
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(sorted(p.name for p in target.parent.iterdir()), ["f.bin"])

    def test_reading(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "f.json"
            for missing in (fileio.read_bytes, fileio.read_text, fileio.read_json):
                with self.assertRaises(FileError):
                    missing(path)
            with self.assertRaises(FileError):
                fileio.read_bytes(Path(folder))
            path.write_bytes(b"\xff\xfe")
            with self.assertRaises(FileError):
                fileio.read_text(path)
            path.write_text("{not json")
            with self.assertRaises(BuildError):
                fileio.read_json(path, BuildError)
            fileio.write_json(path, {"a": 1})
            self.assertEqual(path.read_bytes(), b'{\n "a": 1\n}\n')
            self.assertEqual(fileio.read_json(path), {"a": 1})

    def test_is_sha256(self) -> None:
        self.assertTrue(is_sha256("a" * 64))
        for bad in ("A" * 64, "a" * 63, "a" * 64 + "\n", 5, None):
            self.assertFalse(is_sha256(bad))


class BuildDescriptionTests(unittest.TestCase):
    GOOD: dict[str, Any] = {"what": "Something", "specs": ["patches/a.json"]}

    def test_candidate_and_tested(self) -> None:
        candidate = builds.description_from_json("my-build", self.GOOD)
        self.assertFalse(candidate.tested)
        self.assertEqual(candidate.to_json(), self.GOOD)
        tested = candidate.as_tested("a" * 64, "2026-11-13")
        self.assertTrue(tested.tested)
        self.assertEqual(
            builds.description_from_json("my-build", tested.to_json()), tested
        )

    def test_a_test_record_is_never_rewritten(self) -> None:
        tested = builds.description_from_json("b", self.GOOD).as_tested(
            "a" * 64, "2026-11-13"
        )
        self.assertIs(tested.as_tested("a" * 64, "2026-11-13"), tested)
        for sha, date in (("b" * 64, "2026-11-13"), ("a" * 64, "2026-11-14")):
            with self.assertRaises(BuildError):
                tested.as_tested(sha, date)

    def test_refusals(self) -> None:
        record = {"sha256": "a" * 64, "camera_tested": "2026-11-13"}
        bad: list[Any] = [
            {},
            {**self.GOOD, "what": ""},
            {**self.GOOD, "what": "two\nlines"},
            {**self.GOOD, "what": 5},
            {**self.GOOD, "specs": []},
            {**self.GOOD, "specs": "patches/a.json"},
            {**self.GOOD, "specs": ["patches/a.json", "patches/a.json"]},
            {**self.GOOD, "specs": ["../a.json"]},
            {**self.GOOD, "specs": ["/etc/a.json"]},
            {**self.GOOD, "specs": ["patches/../x/a.json"]},
            {**self.GOOD, "specs": ["./patches/a.json"]},
            {**self.GOOD, "specs": ["patches\\a.json"]},
            {**self.GOOD, "specs": ["experiments/x/patches/a.json"]},
            {**self.GOOD, "specs": ["patches/a.txt"]},
            {**self.GOOD, "specs": [5]},
            {**self.GOOD, "sha256": "a" * 64},
            {**self.GOOD, "camera_tested": "2026-11-13"},
            {**self.GOOD, **record, "sha256": "A" * 64},
            {**self.GOOD, **record, "camera_tested": "13/11/2026"},
            {**self.GOOD, **record, "camera_tested": "2026-13-40"},
            {**self.GOOD, "name": "other"},
            ["not", "an", "object"],
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(BuildError):
                builds.description_from_json("b", raw)
        for name in ("Bad Name", "", "-x", "a/b"):
            with self.subTest(name=name), self.assertRaises(BuildError):
                builds.description_from_json(name, self.GOOD)
        with self.assertRaises(BuildError):
            builds.BuildDescription("b", "w", ("patches/a.json",), sha256="a" * 64)
        candidate = builds.description_from_json("b", self.GOOD)
        for sha, date in (("short", "2026-11-13"), ("a" * 64, "2026-13-40")):
            with self.assertRaises(BuildError):
                candidate.as_tested(sha, date)

    def test_test_date(self) -> None:
        self.assertEqual(builds.check_test_date("2026-11-20", TODAY), "2026-11-20")
        for bad in ("2026-11-21", "20/11/2026", "2026-11-2"):
            with self.subTest(bad=bad), self.assertRaises(BuildError):
                builds.check_test_date(bad, TODAY)

    def test_pin_writes_the_description_and_the_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(Path(folder))
            candidate = builds.description_from_json("b", self.GOOD)
            with self.assertRaises(BuildError):
                builds.pin(paths, candidate)
            self.assertFalse(paths.pinned.exists())
            tested = candidate.as_tested("a" * 64, "2026-11-13")
            builds.pin(paths, tested)
            self.assertEqual(
                json.loads(paths.pinned.read_text()), {"build": "builds/b.json"}
            )
            self.assertEqual(builds.pinned_description(paths), tested)
            self.assertEqual(builds.all_descriptions(paths), [tested])
            pointers: list[Any] = [
                {"build": "../elsewhere.json"},
                {"build": "builds/sub/b.json"},
                {"build": "patches/b.json"},
                {"build": 5},
                [],
            ]
            for pointer in pointers:
                paths.pinned.write_text(json.dumps(pointer))
                with self.subTest(pointer=pointer), self.assertRaises(BuildError):
                    builds.pinned_description(paths)
            builds.save_description(paths, builds.description_from_json("c", self.GOOD))
            paths.pinned.write_text(json.dumps({"build": "builds/c.json"}))
            with self.assertRaises(BuildError):
                builds.pinned_description(
                    paths
                )  # a candidate cannot be the pinned build

    def test_the_repository_descriptions(self) -> None:
        pinned = builds.pinned_description(PATHS)
        every = builds.all_descriptions(PATHS)
        self.assertIn(pinned, every)
        for build in every:
            pipeline.load_specs(PATHS, build)


class StockTests(RepoCase):
    def test_catalog_request(self) -> None:
        when = datetime.datetime(2026, 1, 2, 3, 4, 5)
        body = stock.catalog_request(stock.EPM2_V16, when).decode()
        self.assertIn("<hard_code>OLYE101000000000</hard_code>", body)
        self.assertIn("<time>20260102030405</time>", body)
        self.assertIn("<serial_no>000000000</serial_no>", body)
        self.assertIn("<mac_address>00-00-00-00-00-00</mac_address>", body)

    def test_download_url(self) -> None:
        good = catalog_answer()
        self.assertEqual(
            stock.download_url(good, TINY_STOCK), "https://example.invalid/f"
        )
        for bad in (
            catalog_answer(model="1420"),
            catalog_answer(name="OTHER.BIN"),
            catalog_answer(url="http://example.invalid/f"),
            catalog_answer(url=""),
            b"<r></r>",
            b"not xml",
        ):
            with self.subTest(bad=bad), self.assertRaises(StockError):
                stock.download_url(bad, TINY_STOCK)

    def test_read_stock(self) -> None:
        self.assertEqual(stock.read_stock(self.repo.paths, TINY_STOCK), TINY)
        path = stock.stock_path(self.repo.paths, TINY_STOCK)
        path.write_bytes(b"something else")
        with self.assertRaises(StockError):
            stock.read_stock(self.repo.paths, TINY_STOCK)
        with self.assertRaises(StockError):
            stock.fetch(self.repo.paths, TINY_STOCK)  # a wrong file in the way
        self.assertEqual(path.read_bytes(), b"something else")
        path.unlink()
        with self.assertRaises(StockError):
            stock.read_stock(self.repo.paths, TINY_STOCK)

    def test_fetch_downloads_checks_and_keeps(self) -> None:
        path = stock.stock_path(self.repo.paths, TINY_STOCK)
        path.unlink()
        lines: list[str] = []
        with answers(catalog_answer(), TINY) as opened:
            self.assertEqual(
                stock.fetch(self.repo.paths, TINY_STOCK, lines.append), path
            )
            self.assertEqual(opened.call_count, 2)
        self.assertEqual(path.read_bytes(), TINY)
        self.assertIn("example.invalid", lines[0])
        with answers() as opened:
            self.assertEqual(stock.obtain_stock(self.repo.paths, TINY_STOCK), TINY)
            opened.assert_not_called()

    def test_fetch_keeps_nothing_when_the_download_is_wrong(self) -> None:
        path = stock.stock_path(self.repo.paths, TINY_STOCK)
        failures: list[tuple[Any, ...]] = [
            (catalog_answer(), TINY[:-1]),
            (catalog_answer(), TINY[:-1] + b"\0"),
            (catalog_answer(), TINY + b"extra"),
            (catalog_answer(), http.client.IncompleteRead(b"x")),
            (catalog_answer(), OSError("reset")),
            (http.client.IncompleteRead(b"x"),),
            (OSError,),
            (catalog_answer(name="OTHER.BIN"),),
            (b"x" * (2 << 20),),
        ]
        for bodies in failures:
            path.unlink(missing_ok=True)
            with self.subTest(bodies=[type(b).__name__ for b in bodies]):
                with answers(*bodies), self.assertRaises(StockError):
                    stock.obtain_stock(self.repo.paths, TINY_STOCK)
                self.assertEqual(list(path.parent.iterdir()), [])


class MakeTests(RepoCase):
    def test_a_tested_build(self) -> None:
        lines: list[str] = []
        result = self.make(self.repo.tested, log=lines.append)
        self.assertEqual(result.sha256, self.repo.sha256)
        self.assertEqual(result.image.read_bytes(), self.repo.image)
        self.assertEqual(result.card_copy.read_bytes(), self.repo.image)
        self.assertIsNone(result.on_card)
        self.assertEqual(self.repo.outputs(), ["card/DCOLYMP/E1019999.BIN", "good.BIN"])
        self.assertTrue(any("tested on 2026-11-13" in line for line in lines))

    def test_a_wrong_result_leaves_no_output_and_removes_the_old_one(self) -> None:
        self.make(self.repo.tested)
        self.repo.write_json(
            "patches/a.json", spec_json("a", [{**BYTE_OP, "new": "cccc"}])
        )
        with self.assertRaises(BuildError):
            self.make(self.repo.tested)
        self.assertEqual(self.repo.outputs(), [])

    def test_a_failure_removes_the_card_folder_of_another_build(self) -> None:
        self.make(self.repo.tested)
        self.repo.free_space_tool(1)
        with self.assertRaises(BuildError):
            self.make(self.repo.candidate)
        self.assertEqual(
            self.repo.outputs(), ["good.BIN"]
        )  # no card folder, no new.BIN

    def test_a_candidate_runs_the_free_space_check(self) -> None:
        lines: list[str] = []
        self.repo.free_space_tool(0)
        result = self.make(self.repo.candidate, log=lines.append)
        self.assertEqual(result.sha256, self.repo.sha256)
        text = "\n".join(lines)
        self.assertIn("check: stand-in", text)
        self.assertIn("NOT camera-tested", text)
        self.repo.paths.free_space_tool.unlink()
        with self.assertRaises(BuildError):
            self.make(self.repo.candidate)

    def test_the_card(self) -> None:
        lines: list[str] = []
        result = self.make(self.repo.tested, card=self.card, log=lines.append)
        target = self.card / "DCOLYMP" / "E1019999.BIN"
        self.assertEqual(result.on_card, target)
        self.assertEqual(target.read_bytes(), self.repo.image)
        self.assertEqual([p.name for p in target.parent.iterdir()], ["E1019999.BIN"])
        (target.parent / "._E1019999.BIN").write_bytes(b"x")
        self.make(self.repo.tested, card=self.card, log=lines.append)  # again: allowed
        self.assertTrue(any("._E1019999.BIN" in line for line in lines))

    def test_a_card_problem_is_found_before_any_work(self) -> None:
        folder = self.card / "DCOLYMP"
        folder.mkdir()
        (folder / "OTHER.BIN").write_bytes(b"x")
        for card in (self.card, self.card / "none", folder / "OTHER.BIN"):
            with self.subTest(card=card.name), self.assertRaises(BuildError):
                self.make(self.repo.tested, card=card)
            self.assertEqual(self.repo.outputs(), [])
        self.assertEqual((folder / "OTHER.BIN").read_bytes(), b"x")

    def test_a_failed_card_write_keeps_the_file_that_was_there(self) -> None:
        target = pipeline.card_target(self.card, TINY_STOCK)
        target.parent.mkdir()
        target.write_bytes(b"older firmware")
        with self.assertRaises(BuildError):  # the read-back differs
            pipeline.copy_to_card(self.repo.image, "0" * 64, self.card, TINY_STOCK)
        self.assertEqual(target.read_bytes(), b"older firmware")
        self.assertEqual([p.name for p in target.parent.iterdir()], [target.name])

        real_write = fileio.write_bytes

        def fail_on_card(
            path: Path, data: bytes, error: type[Epm2ModError] = FileError
        ) -> None:
            if self.card in path.parents:
                raise error("card full")
            real_write(path, data, error)

        with mock.patch("epm2mod.pipeline.write_bytes", side_effect=fail_on_card):
            with self.assertRaises(BuildError):
                self.make(self.repo.tested, card=self.card)
        self.assertEqual(target.read_bytes(), b"older firmware")
        self.assertEqual(self.repo.outputs(), [])


class RecordTestTests(RepoCase):
    def record(
        self, description: builds.BuildDescription, sha: str, date: str
    ) -> builds.BuildDescription:
        return pipeline.record_test(
            self.repo.paths, description, sha, date, stock=TINY_STOCK, today=TODAY
        )

    def test_a_candidate_becomes_the_pinned_build(self) -> None:
        tested = self.record(self.repo.candidate, self.repo.sha256, "2026-11-19")
        self.assertEqual(tested.camera_tested, "2026-11-19")
        self.assertEqual(builds.pinned_description(self.repo.paths), tested)
        self.assertEqual(self.repo.outputs(), [])  # recording a test writes no firmware
        self.assertEqual(self.record(tested, self.repo.sha256, "2026-11-19"), tested)

    def test_refusals_change_nothing(self) -> None:
        before = builds.pinned_description(self.repo.paths)
        cases = [
            (self.repo.candidate, "0" * 64, "2026-11-19"),  # not what the build gives
            (self.repo.candidate, self.repo.sha256, "2026-11-21"),  # in the future
            (self.repo.candidate, self.repo.sha256, "19/11/2026"),
            (self.repo.candidate, "short", "2026-11-19"),
            (self.repo.tested, self.repo.sha256, "2026-11-19"),  # another record
        ]
        for description, sha, date in cases:
            with self.subTest(sha=sha[:5], date=date), self.assertRaises(BuildError):
                self.record(description, sha, date)
        self.assertEqual(builds.pinned_description(self.repo.paths), before)
        self.assertEqual(
            builds.load_description(builds.description_path(self.repo.paths, "new")),
            self.repo.candidate,
        )

    def test_a_spec_changed_after_the_flash_cannot_be_recorded(self) -> None:
        flashed = self.repo.sha256
        self.repo.write_json(
            "patches/a.json", spec_json("a", [{**BYTE_OP, "new": "cccc"}])
        )
        with self.assertRaises(BuildError):
            self.record(self.repo.candidate, flashed, "2026-11-19")


class CommandLineTests(RepoCase):
    def run_cli(self, *argv: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        env = {paths_module.ROOT_ENV: str(self.repo.paths.root)}
        with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
            with contextlib.redirect_stderr(err):
                status = cli.main(list(argv))
        return status, out.getvalue() + err.getvalue()

    def test_builds(self) -> None:
        status, text = self.run_cli("builds")
        self.assertEqual(status, 0)
        self.assertIn("good (pinned): A tiny build [tested 2026-11-13, 1 specs]", text)
        self.assertIn("new: A tiny candidate [candidate, 1 specs]", text)

    def test_errors_are_one_message_and_status_1(self) -> None:
        outside = self.repo.write_json("elsewhere.json", self.repo.candidate.to_json())
        image = self.repo.write("fw.BIN", TINY)
        cases = [
            ("make", "builds/none.json"),
            ("make", str(outside)),
            ("pin", "builds/new.json", "--date", "2026-13-40", "--sha256", "0" * 64),
            (
                "pin",
                "builds/new.json",
                "--date",
                "2999-01-01",
                "--sha256",
                self.repo.sha256,
            ),
            ("info", str(self.repo.paths.root)),
            ("info", "no-such-file"),
            ("apply", "no-such-spec.json", "-o", "out.BIN"),
            ("make", "--card", str(image)),
        ]
        os.chdir(self.repo.paths.root)
        self.addCleanup(os.chdir, ROOT)
        for argv in cases:
            with self.subTest(argv=argv):
                status, text = self.run_cli(*argv)
                self.assertEqual(status, 1, text)
                self.assertTrue(text.startswith("epm2mod: "), text)
                self.assertNotIn("Traceback", text)
        self.assertEqual(self.repo.outputs(), [])

    def test_a_wrong_command_line_is_status_2(self) -> None:
        for argv in ((), ("nope",), ("pin", "builds/new.json")):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised:
                self.run_cli(*argv)
            self.assertEqual(raised.exception.code, 2)

    def test_not_in_a_repository(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.dict(os.environ, {paths_module.ROOT_ENV: folder}):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(cli.main(["builds"]), 1)
        self.assertIn("is not the repository", err.getvalue())

    def test_info(self) -> None:
        good = self.repo.write("fw.BIN", TINY)
        status, text = self.run_cli("info", str(good))
        self.assertEqual(status, 0)
        self.assertIn(TINY_STOCK.sha256, text)
        damaged = bytearray(TINY)
        damaged[40] ^= 1
        status, _ = self.run_cli(
            "info", str(self.repo.write("bad.BIN", bytes(damaged)))
        )
        self.assertEqual(status, 1)

    def test_the_readme_check_of_this_repository(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["readme", "--check"]), 0)


class ReadmeTests(unittest.TestCase):
    def test_the_readme_is_up_to_date(self) -> None:
        self.assertTrue(readme.is_current(PATHS), "run: uv run epm2mod readme")

    def test_marker_problems(self) -> None:
        text = fileio.read_text(PATHS.readme)
        begin, end = "<!-- BEGIN GENERATED: films -->", "<!-- END GENERATED: films -->"
        block = text[text.index(begin) : text.index(end) + len(end)]
        broken = {
            "unknown block": text
            + "\n<!-- BEGIN GENERATED: nope -->\n<!-- END GENERATED: nope -->",
            "no markers": "no markers at all",
            "missing end": text.replace(end, ""),
            "missing begin": text.replace(begin, ""),
            "twice": text + "\n" + block,
        }
        for name, bad in broken.items():
            with self.subTest(name), self.assertRaises(BuildError):
                readme.update(bad, PATHS)

    def test_text_outside_the_markers_is_kept(self) -> None:
        text = fileio.read_text(PATHS.readme)
        fresh = readme.update("BEFORE\n" + text + "\nAFTER", PATHS)
        self.assertTrue(fresh.startswith("BEFORE\n") and fresh.endswith("\nAFTER"))

    def test_cell(self) -> None:
        self.assertEqual(readme.cell("a | b\nc"), "a \\| b c")

    def test_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(Path(folder))
            for name in ("builds", "looks"):
                shutil.copytree(
                    ROOT / name,
                    paths.root / name,
                    ignore=shutil.ignore_patterns("*.npz"),
                )
            shutil.copy(PATHS.pinned, paths.pinned)
            stale = "".join(
                f"<!-- BEGIN GENERATED: {name} -->\nold\n<!-- END GENERATED: {name} -->\n"
                for name in readme.BLOCKS
            )
            fileio.write_text(paths.readme, stale)
            self.assertFalse(readme.is_current(paths))
            self.assertTrue(readme.rewrite(paths))
            self.assertTrue(readme.is_current(paths))
            self.assertFalse(readme.rewrite(paths))
            self.assertNotIn("old", fileio.read_text(paths.readme))


@unittest.skipUnless(HAVE_STOCK, "stock firmware not present")
class RealFirmwareTests(unittest.TestCase):
    def test_the_stock_file_round_trips(self) -> None:
        data = stock.read_stock(PATHS)
        self.assertEqual(len(data), stock.EPM2_V16.size)
        parsed = container.parse(data)
        self.assertTrue(parsed.checksums_ok)
        self.assertEqual(container.serialize(parsed), data)

    def test_every_tested_build_gives_its_sha256(self) -> None:
        data = stock.read_stock(PATHS)
        tested = [build for build in builds.all_descriptions(PATHS) if build.tested]
        self.assertTrue(tested)
        for build in tested:
            with self.subTest(build=build.name):
                _, digest = pipeline.build_image(PATHS, build, data)
                self.assertEqual(digest, build.sha256)

    def test_make_and_the_command_line_on_the_pinned_build(self) -> None:
        pinned = builds.pinned_description(PATHS)
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(Path(folder))
            for name in ("firmware", "patches", "builds"):
                (paths.root / name).symlink_to(ROOT / name)
            shutil.copy(PATHS.pinned, paths.pinned)
            out, env = io.StringIO(), {paths_module.ROOT_ENV: folder}
            with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
                self.assertEqual(cli.main(["make"]), 0)
            image = paths.output / f"{pinned.name}.BIN"
            self.assertEqual(sha256_bytes(image.read_bytes()), pinned.sha256)
            self.assertIn(f"sha256 {pinned.sha256}", out.getvalue())


if __name__ == "__main__":
    unittest.main()

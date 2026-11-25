"""Tests of the ``epm2mod`` package.

    uv run python -m unittest discover -s cli/tests

Most tests need nothing but the repository: they build a small firmware
container and a small repository in a temporary folder. The tests in
``RealFirmwareTests`` need the stock firmware file and are skipped without it.
"""

from __future__ import annotations

import ast
import contextlib
import datetime
import errno
import http.client
import io
import json
import os
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from typing import Any, Iterator
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import support  # noqa: E402
from support import ROOT, make_container, write_manifest  # noqa: E402

import epm2mod  # noqa: E402
import epm2mod.looks  # noqa: E402
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
    UnavailableError,
)
from epm2mod.hashing import is_sha256, sha256_bytes  # noqa: E402
from epm2mod.paths import MANIFEST, RepoPaths, is_repo_relative  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()
TODAY = datetime.date(2026, 11, 20)


TINY = make_container(
    [bytes(range(48)), ("Pop Art\0\0".encode("utf-16-le") * 2).ljust(48, b"\0")]
)
TINY_STOCK = stock.StockFirmware(
    file_name="TINY.BIN",
    size=len(TINY),
    sha256=sha256_bytes(TINY),
    model_id="1010",
    hard_code="OLYE101000000000",
    card_name="E1019999.BIN",
)
# The tiny builds name it as their stock firmware.
stock.STOCK_FIRMWARE[TINY_STOCK.file_name] = TINY_STOCK
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
        self.paths = RepoPaths(write_manifest(folder, cache="firmware"))
        self.write("firmware/TINY.BIN", TINY)
        self.write_json("data/specs/a.json", spec_json("a", [BYTE_OP]))
        applied = spec.apply_specs(
            TINY, [spec.spec_from_json(spec_json("a", [BYTE_OP]))]
        )
        self.image = applied.image
        self.sha256 = sha256_bytes(self.image)
        self.tested = builds.BuildDescription(
            "good",
            "A tiny build",
            ("data/specs/a.json",),
            self.sha256,
            "2026-11-13",
            stock=TINY_STOCK.file_name,
        )
        self.candidate = builds.BuildDescription(
            "new",
            "A tiny candidate",
            ("data/specs/a.json",),
            stock=TINY_STOCK.file_name,
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
        """Install a stand-in for tools/freespace.py that exits with ``status``.

        Its last output line holds the arguments it was given.
        """
        script = (
            "import sys\nprint('check: stand-in', *sys.argv[1:])\n"
            f"sys.exit({status})\n"
        )
        self.write("tools/freespace.py", script.encode())
        if status == 0:  # a candidate that passes it is then started in the emulator
            for tool in self.paths.emulator_checks:
                if not tool.exists():
                    self.emulator_check(tool.name, 0)

    def emulator_check(self, name: str, status: int) -> None:
        """Install a stand-in for emulator/NAME that exits with ``status``."""
        script = (
            f"import sys\nprint('{name}: stand-in', sys.argv[1])\nsys.exit({status})\n"
        )
        self.write(f"emulator/{name}", script.encode())

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
        return pipeline.make(self.repo.paths, description, **kw)


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
        data = make_container(payloads)
        parsed = container.parse(data)
        self.assertEqual([block.payload for block in parsed.blocks], payloads)
        self.assertEqual(parsed.tail, b"TAIL")
        self.assertTrue(parsed.checksums_ok)
        self.assertEqual(parsed.blocks[1].kind, 0x0101)
        self.assertEqual(parsed.blocks[1].load_address, 0x2000)
        self.assertEqual(parsed.blocks[1].offset, 64 + 64)
        self.assertEqual(container.serialize(parsed), data)

    def test_a_changed_byte_makes_the_checksum_wrong(self) -> None:
        data = bytearray(make_container([bytes(32)]))
        data[40] ^= 1
        self.assertFalse(container.parse(bytes(data)).checksums_ok)

    def test_serialize_makes_the_checksum_right_again(self) -> None:
        parsed = container.parse(make_container([bytes(32)]))
        changed = parsed.with_payloads([b"\x01" * 32])
        self.assertFalse(changed.checksums_ok)
        self.assertTrue(container.parse(container.serialize(changed)).checksums_ok)

    def test_errors(self) -> None:
        good = make_container([bytes(32)])
        two = make_container([bytes(32), bytes(32)])
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

    def test_a_block_that_cannot_be_written_cannot_be_made(self) -> None:
        good = container.parse(make_container([bytes(32)])).blocks[0]
        for header, trailer, payload in (
            (good.header[:-1], good.trailer, good.payload),
            (good.header, good.trailer + b"\0", good.payload),
            (good.header, good.trailer, bytes(24)),
        ):
            with self.assertRaises(ContainerError):
                container.Block(0, header, trailer, payload, False)
        with self.assertRaisesRegex(ContainerError, "header says 32"):
            container.Block(0, good.header, good.trailer, bytes(48), False)

    def test_describe(self) -> None:
        lines = container.describe(container.parse(make_container([bytes(32)])))
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

    def test_a_later_spec_cannot_change_a_byte_an_earlier_one_keeps(self) -> None:
        def one(name: str, expect: str, new: str, offset: int) -> spec.PatchSpec:
            op = {
                "type": "bytes",
                "block": 0,
                "offset": offset,
                "expect": expect,
                "new": new,
            }
            return spec.spec_from_json(spec_json(name, [op]))

        # "a" writes two bytes; its second byte is equal to the stock byte.
        first = one("a", "0001", "0701", 0)
        second = one("b", "01", "09", 1)
        with self.assertRaises(SpecError) as caught:
            spec.apply_specs(TINY, [first, second])
        self.assertIn("a covers and keeps", str(caught.exception))
        spec.apply_specs(
            TINY, [first]
        )  # alone, and with its own later edit, it is fine
        spec.apply_specs(TINY, [first, one("a", "01", "09", 1)])

    def test_text_copies_do_not_overlap(self) -> None:
        text = "AAAAAA".encode("utf-16-le").ljust(32, b"\0")
        data = make_container([text])
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

    def test_only_text_on_an_even_offset_counts(self) -> None:
        def utf16(text: str) -> bytes:
            return text.encode("utf-16-le")

        def run(payload: bytes, count: int | None) -> bytes:
            data = make_container([payload.ljust(48, b"\xff")])
            op: dict[str, Any] = {
                "type": "utf16-replace-all",
                "block": 0,
                "old": "AB",
                "new": "xy",
            }
            if count is not None:
                op["count"] = count
            raw = {
                "name": "s",
                "base": "x",
                "base_sha256": sha256_bytes(data),
                "ops": [op],
            }
            image = spec.apply_specs(data, [spec.spec_from_json(raw)]).image
            return container.parse(image).blocks[0].payload

        even, odd = utf16("AB"), b"\xff" + utf16("AB") + b"\xff"
        both = even + b"\xff\xff" + odd
        changed = run(both, 1)
        self.assertEqual(changed[:4], utf16("xy"))
        self.assertEqual(changed[6:12], odd)
        with self.assertRaisesRegex(SpecError, "found 1 copies"):
            run(both, 2)
        with self.assertRaisesRegex(SpecError, "no copy found"):
            run(odd, None)

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

    def test_unknown_keys_are_refused_and_notes_are_accepted(self) -> None:
        good = spec_json("s", [BYTE_OP])
        text_op = {"type": "utf16-replace-all", "block": 1, "old": "a", "new": "b"}
        notes = {
            **good,
            "status": "tested",
            "attribution": "someone",
            "inputs_sha256": "a digest",
            "_why": ["any", "value"],
            "ops": [{**BYTE_OP, "_note": "text"}, {**text_op, "_note": 1}],
        }
        self.assertEqual(len(spec.spec_from_json(notes).ops), 2)
        misspelt: list[dict[str, Any]] = [
            {**good, "expected_sha": "0" * 64},
            {**good, "ops": [{**BYTE_OP, "expected": "00"}]},
            {**good, "ops": [{**text_op, "offset": 0}]},
            {**good, "ops": [{**BYTE_OP, "count": 1}]},
        ]
        for raw in misspelt:
            with self.subTest(raw=raw), self.assertRaises(SpecError) as raised:
                spec.spec_from_json(raw)
            self.assertIn("unknown key", str(raised.exception))

    def test_an_operation_is_valid_when_it_is_made(self) -> None:
        bad_bytes: list[tuple[int, int, bytes, bytes]] = [
            (-1, 0, b"a", b"b"),
            (0, -1, b"a", b"b"),
            (0, 0, b"a", b"bc"),
            (0, 0, b"", b""),
        ]
        for block, offset, expect, new in bad_bytes:
            with self.subTest(expect=expect, new=new), self.assertRaises(SpecError):
                spec.BytesOp(block, offset, expect, new)
        bad_text: list[tuple[int, str, str, int | None]] = [
            (-1, "a", "b", None),
            (0, "a", "bc", None),
            (0, "", "", None),
            (0, "a", "b", 0),
            (0, "\ud800", "b", None),
        ]
        for block, old, new_text, count in bad_text:
            with self.subTest(old=old, new=new_text), self.assertRaises(SpecError):
                spec.Utf16ReplaceAllOp(block, old, new_text, count)

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
        for good in ("data/specs/a.json", "a", "data/films/fits/x.npz"):
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
            "a\0b",
            "a\nb",
            "a\x1fb",
            "a\ud800b",
        ):
            self.assertFalse(is_repo_relative(bad), repr(bad))
        with self.assertRaises(RepositoryError):
            PATHS.resolve("../outside")

    def test_relative_is_for_messages_and_never_fails(self) -> None:
        self.assertEqual(PATHS.relative(ROOT / "build" / "x.BIN"), "build/x.BIN")
        self.assertEqual(
            PATHS.relative(Path("/elsewhere/x")), str(Path("/elsewhere/x"))
        )

    def test_find_root(self) -> None:
        self.assertEqual(paths_module.find_root(ROOT / "cli" / "src" / "epm2mod"), ROOT)
        with tempfile.TemporaryDirectory() as folder:
            # Outside a project there is no fallback: not even the package's own checkout.
            with self.assertRaises(RepositoryError):
                paths_module.find_root(Path(folder))
            with self.assertRaises(RepositoryError):
                paths_module.find_root(project=Path(folder))
            write_manifest(Path(folder))
            self.assertEqual(
                paths_module.find_root(project=Path(folder)), Path(folder).absolute()
            )
            (Path(folder) / "sub" / "deeper").mkdir(parents=True)
            self.assertEqual(
                paths_module.find_root(Path(folder) / "sub" / "deeper"),
                Path(folder).absolute(),
            )

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

    def test_a_read_back_that_differs_keeps_the_old_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "f.bin"
            fileio.write_bytes(target, b"old", read_back=True)
            with mock.patch.object(Path, "read_bytes", return_value=b"other"):
                with self.assertRaises(FileError) as raised:
                    fileio.write_bytes(target, b"new", read_back=True)
            self.assertIn("read back", str(raised.exception))
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual([p.name for p in target.parent.iterdir()], ["f.bin"])

    def test_a_failed_folder_flush_says_that_the_new_file_is_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "f.bin"
            target.write_bytes(b"old")
            failing = OSError(errno.EIO, "Input/output error")
            with mock.patch("epm2mod.fileio.sync_folder", side_effect=failing) as sync:
                with self.assertRaisesRegex(FileError, "holds the new data"):
                    fileio.write_bytes(target, b"new")
            sync.assert_called_once_with(target.parent)
            self.assertEqual(target.read_bytes(), b"new")
            self.assertEqual([p.name for p in target.parent.iterdir()], ["f.bin"])

    def test_a_path_or_text_that_cannot_be_written_is_a_package_error(self) -> None:
        for path in (Path(""), Path("/")):
            with self.assertRaisesRegex(FileError, "not a file name"):
                fileio.write_bytes(path, b"data")
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(FileError, "UTF-8"):
                fileio.write_text(Path(folder) / "f.txt", "\ud800")
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_an_interrupted_write_leaves_the_old_file_and_no_temporary_file(
        self,
    ) -> None:
        for step in ("fsync", "replace"):
            with self.subTest(step=step), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "f.bin"
                target.write_bytes(b"old")
                with mock.patch(
                    f"epm2mod.fileio.os.{step}", side_effect=KeyboardInterrupt
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        fileio.write_bytes(target, b"new", read_back=True)
                self.assertEqual(target.read_bytes(), b"old")
                self.assertEqual([p.name for p in Path(folder).iterdir()], ["f.bin"])

    def test_the_folder_flush_can_be_left_to_the_caller(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch("epm2mod.fileio.sync_folder") as sync:
                fileio.write_bytes(Path(folder) / "a", b"x", flush_folder=False)
                sync.assert_not_called()
                fileio.write_bytes(Path(folder) / "b", b"x")
                sync.assert_called_once()

    def test_a_write_is_flushed_to_the_device(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch("epm2mod.fileio.os.fsync", wraps=os.fsync) as flush:
                fileio.write_bytes(Path(folder) / "f.bin", b"data")
            self.assertGreaterEqual(flush.call_count, 1)
            failing = OSError(errno.EIO, "Input/output error")
            with mock.patch("epm2mod.fileio.os.fsync", side_effect=failing):
                with self.assertRaisesRegex(FileError, "Input/output error"):
                    fileio.write_bytes(Path(folder) / "g.bin", b"data")
            self.assertFalse((Path(folder) / "g.bin").exists())

    @unittest.skipUnless(hasattr(os, "O_DIRECTORY"), "no folder flush here")
    def test_a_folder_flush_reports_lost_data_only(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            for code, raises in ((errno.EINVAL, False), (errno.ENOSPC, True)):
                error = OSError(code, os.strerror(code))
                with mock.patch("epm2mod.fileio.os.fsync", side_effect=error):
                    if raises:
                        with self.assertRaises(OSError):
                            fileio.sync_folder(Path(folder))
                    else:
                        fileio.sync_folder(Path(folder))

    @unittest.skipUnless(hasattr(os, "symlink"), "no symbolic links here")
    def test_a_link_at_the_temporary_name_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            victim, target = Path(folder) / "victim.txt", Path(folder) / "f.bin"
            victim.write_bytes(b"keep me")
            fileio.part_path(target).symlink_to(victim)
            fileio.write_bytes(target, b"data")
            self.assertEqual(victim.read_bytes(), b"keep me")
            self.assertEqual(target.read_bytes(), b"data")
            self.assertFalse(target.is_symlink())

    def test_a_json_key_that_is_there_twice_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "f.json"
            path.write_text('{"a": 1, "b": {"c": 1, "c": 2}}')
            with self.assertRaisesRegex(FileError, "'c' is there twice"):
                fileio.read_json(path)

    def test_line_ends_are_written_as_given(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "f.txt"
            fileio.write_text(path, "a\r\nb\n")
            self.assertEqual(path.read_bytes(), b"a\r\nb\n")
            self.assertEqual(fileio.read_text(path), "a\r\nb\n")

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
    GOOD: dict[str, Any] = {
        "what": "Something",
        "stock": "x",
        "specs": ["data/specs/a.json"],
    }

    def test_candidate_and_tested(self) -> None:
        candidate = builds.description_from_json("my-build", self.GOOD)
        self.assertFalse(candidate.tested)
        self.assertEqual(candidate.to_json(), self.GOOD)
        tested = candidate.as_tested("a" * 64, "2026-11-13")
        self.assertTrue(tested.tested)
        self.assertEqual(
            builds.description_from_json("my-build", tested.to_json()), tested
        )

    def test_first_code_is_true_or_absent(self) -> None:
        marked = builds.description_from_json("b", {**self.GOOD, "first_code": True})
        self.assertTrue(marked.first_code)
        self.assertEqual(marked.to_json(), {**self.GOOD, "first_code": True})
        self.assertFalse(builds.description_from_json("b", self.GOOD).first_code)
        self.assertTrue(marked.as_tested("a" * 64, "2026-11-13").first_code)
        for bad in (False, "yes", 1, None):
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(BuildError, "first_code"),
            ):
                builds.description_from_json("b", {**self.GOOD, "first_code": bad})

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
            {**self.GOOD, "specs": "data/specs/a.json"},
            {**self.GOOD, "specs": ["data/specs/a.json", "data/specs/a.json"]},
            {**self.GOOD, "specs": ["../a.json"]},
            {**self.GOOD, "specs": ["/etc/a.json"]},
            {**self.GOOD, "specs": ["data/specs/../x/a.json"]},
            {**self.GOOD, "specs": ["./patches/a.json"]},
            {**self.GOOD, "specs": ["patches\\a.json"]},
            {**self.GOOD, "specs": ["data/specs/a.txt"]},
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
            builds.BuildDescription(
                "b", "w", ("data/specs/a.json",), sha256="a" * 64, stock="x"
            )
        candidate = builds.description_from_json("b", self.GOOD)
        for sha, date in (("short", "2026-11-13"), ("a" * 64, "2026-13-40")):
            with self.assertRaises(BuildError):
                candidate.as_tested(sha, date)

    def test_a_spec_outside_the_patch_spec_folder_is_refused(self) -> None:
        self.assertEqual(PATHS.spec_file("data/specs/a.json"), PATHS.specs / "a.json")
        for relative in ("experiments/x/patches/a.json", "data/builds/a.json"):
            with self.subTest(relative=relative), self.assertRaises(BuildError):
                PATHS.spec_file(relative)

    def test_reading_a_description_does_not_use_the_clock(self) -> None:
        record = {**self.GOOD, "sha256": "a" * 64}
        far = {**record, "camera_tested": "2999-01-01"}
        # Reading does not look at the clock: a recorded build stays readable.
        self.assertTrue(builds.description_from_json("b", far).tested)
        with self.assertRaisesRegex(BuildError, "future"):
            builds.check_test_date("2999-01-01", TODAY)
        for what in ("a <b> c", "<!-- x -->"):
            with self.assertRaisesRegex(BuildError, "plain text"):
                builds.description_from_json("b", {**self.GOOD, "what": what})

    def test_a_description_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(write_manifest(Path(folder)))
            saved = builds.save_description(
                paths, builds.description_from_json("my-build", self.GOOD)
            )
            self.assertEqual(saved, paths.builds / "my-build.json")
            self.assertEqual(builds.load_description(saved).name, "my-build")
            other = saved.with_suffix(".txt")
            other.write_bytes(saved.read_bytes())
            for bad in (other, paths.builds / "none.json"):
                with self.subTest(bad=bad.name), self.assertRaises(BuildError):
                    builds.load_description(bad)

    def test_test_date(self) -> None:
        self.assertEqual(builds.check_test_date("2026-11-20", TODAY), "2026-11-20")
        for bad in ("2026-11-21", "20/11/2026", "2026-11-2", "20261120"):
            with self.subTest(bad=bad), self.assertRaises(BuildError):
                builds.check_test_date(bad, TODAY)

    def test_pin_writes_the_description_and_the_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(write_manifest(Path(folder)))
            candidate = builds.description_from_json("b", self.GOOD)
            with self.assertRaises(BuildError):
                builds.pin(paths, candidate)
            self.assertFalse(paths.pinned.exists())
            tested = candidate.as_tested("a" * 64, "2026-11-13")
            with mock.patch("epm2mod.builds.write_json", wraps=fileio.write_json) as w:
                builds.pin(paths, tested)
            written = [call.args[0].name for call in w.call_args_list]
            self.assertEqual(written, ["b.json", "pinned-build.json"])
            self.assertEqual(
                json.loads(paths.pinned.read_text()), {"build": "data/builds/b.json"}
            )
            self.assertEqual(builds.pinned_description(paths), tested)
            self.assertEqual(builds.all_descriptions(paths), [tested])
            longer = builds.description_from_json("b-2", self.GOOD)
            builds.save_description(paths, longer)
            self.assertEqual(
                [d.name for d in builds.all_descriptions(paths)], ["b", "b-2"]
            )
            builds.description_path(paths, "b-2").unlink()
            pointers: list[Any] = [
                {"build": "../elsewhere.json"},
                {"build": "data/builds/sub/b.json"},
                {"build": "data/builds/../builds/b.json"},
                {"build": "b.json"},
                {"build": "data/specs/b.json"},
                {"build": 5},
                {"build": "data/builds/b.json", "other": 1},
                [],
            ]
            # Each of these would name a readable, tested description if the
            # pointer were not held to "a file directly in data/builds/".
            (paths.builds / "sub").mkdir()
            for copy in (paths.builds / "sub" / "b.json", paths.root / "b.json"):
                shutil.copy(paths.builds / "b.json", copy)
            (paths.root / "data" / "specs").mkdir()
            shutil.copy(
                paths.builds / "b.json", paths.root / "data" / "specs" / "b.json"
            )
            for pointer in pointers:
                paths.pinned.write_text(json.dumps(pointer))
                with self.subTest(pointer=pointer), self.assertRaises(BuildError):
                    builds.pinned_description(paths)
            builds.save_description(paths, builds.description_from_json("c", self.GOOD))
            paths.pinned.write_text(json.dumps({"build": "data/builds/c.json"}))
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
        with answers(catalog_answer(), TINY) as opened:
            with self.assertRaises(StockError):
                stock.fetch(self.repo.paths, TINY_STOCK)  # a wrong file in the way
            with self.assertRaises(StockError):
                stock.obtain_stock(self.repo.paths, TINY_STOCK)
            opened.assert_not_called()
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

    def test_an_answer_that_is_too_large_is_refused(self) -> None:
        request = urllib.request.Request("https://example.invalid/f")
        with answers(b"12345"):
            self.assertEqual(stock.http_get(request, 5), b"12345")
        with answers(b"123456"), self.assertRaisesRegex(StockError, "larger than 5"):
            stock.http_get(request, 5)

    def test_an_address_that_cannot_be_used_is_a_download_error(self) -> None:
        request = urllib.request.Request("https://example.invalid/f")
        with mock.patch(
            "epm2mod.stock.urllib.request.urlopen",
            side_effect=UnicodeEncodeError("idna", "x", 0, 1, "label too long"),
        ):
            with self.assertRaisesRegex(StockError, "download failed"):
                stock.http_get(request, 5)

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
        self.assertEqual(self.repo.outputs(), ["DCOLYMP/E1019999.BIN", "good.BIN"])
        self.assertTrue(any("tested on 2026-11-13" in line for line in lines))

    def test_a_wrong_result_leaves_no_output_and_removes_the_old_one(self) -> None:
        self.make(self.repo.tested)
        self.repo.write_json(
            "data/specs/a.json", spec_json("a", [{**BYTE_OP, "new": "cccc"}])
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

    def test_a_failed_check_shows_its_fail_lines(self) -> None:
        script = (
            "import sys\nprint('FAIL  the reason')\n"
            "for n in range(200): print('PASS ', 'x' * 60)\n"
            "print('check: FAIL (1 FAIL)')\nsys.exit(7)\n"
        )
        self.repo.write("tools/freespace.py", script.encode())
        with self.assertRaises(BuildError) as caught:
            self.make(self.repo.candidate)
        self.assertIn("FAIL  the reason\ncheck: FAIL (1 FAIL)", str(caught.exception))

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

    def test_make_downloads_the_stock_firmware_if_it_is_absent(self) -> None:
        stock.stock_path(self.repo.paths, TINY_STOCK).unlink()
        with answers(catalog_answer(), TINY):
            result = self.make(self.repo.tested)
        self.assertEqual(result.sha256, self.repo.sha256)
        stock.stock_path(self.repo.paths, TINY_STOCK).unlink()
        with answers(catalog_answer(), TINY[:-1]), self.assertRaises(StockError):
            self.make(self.repo.tested)
        self.assertEqual(self.repo.outputs(), [])

    def test_a_card_folder_that_is_a_link_is_removed_not_followed(self) -> None:
        elsewhere = self.card.parent / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "keep.txt").write_bytes(b"keep")
        self.repo.paths.output.mkdir()
        card = pipeline.card_folder(self.repo.paths)
        card.symlink_to(elsewhere, target_is_directory=True)
        self.make(self.repo.tested)
        self.assertFalse(card.is_symlink())
        self.assertEqual([p.name for p in elsewhere.iterdir()], ["keep.txt"])

    def test_a_candidate_is_started_in_the_emulator(self) -> None:
        self.repo.free_space_tool(0)
        lines: list[str] = []
        self.make(self.repo.candidate, log=lines.append)
        text = "\n".join(lines)
        self.assertIn("boot-test: stand-in", text)
        self.assertIn("update-path-test: stand-in", text)
        self.assertIn("new.BIN", text)

    def test_a_candidate_is_not_made_when_a_start_up_check_cannot_run(self) -> None:
        self.repo.free_space_tool(0)
        self.repo.emulator_check("update-path-test", 3)  # 3: not set up
        with self.assertRaises(UnavailableError) as caught:
            self.make(self.repo.candidate)
        self.assertIn("update-path-test cannot run", str(caught.exception))
        self.assertEqual(self.repo.outputs(), [])
        self.repo.paths.emulator_checks[0].unlink()  # no emulator folder at all
        with self.assertRaises(UnavailableError) as caught:
            self.make(self.repo.candidate)
        self.assertIn("boot-test cannot run", str(caught.exception))
        self.assertEqual(self.repo.outputs(), [])

    def test_a_candidate_that_fails_in_the_emulator_is_removed(self) -> None:
        self.repo.free_space_tool(0)
        self.repo.emulator_check("boot-test", 1)
        with self.assertRaises(BuildError) as caught:
            self.make(self.repo.candidate)
        self.assertIn("boot-test failed", str(caught.exception))
        self.assertEqual(self.repo.outputs(), [])

    def test_a_tested_build_is_not_started_in_the_emulator(self) -> None:
        self.repo.emulator_check("boot-test", 1)
        self.make(self.repo.tested)  # no error: its sha256 is the check

    def test_a_first_code_build_tells_the_free_space_check_so(self) -> None:
        self.repo.free_space_tool(0)
        lines: list[str] = []
        self.make(self.repo.candidate, log=lines.append)
        self.assertNotIn("--first-code", "\n".join(lines))
        first = builds.BuildDescription(
            "probe",
            "A probe",
            ("data/specs/a.json",),
            first_code=True,
            stock=TINY_STOCK.file_name,
        )
        lines.clear()
        self.make(first, log=lines.append)
        text = "\n".join(lines)
        self.assertIn("check data/specs/a.json --first-code", text)
        self.assertIn("FIRST CODE", text)

    def test_a_missing_spec_is_found_before_the_free_space_check(self) -> None:
        self.repo.free_space_tool(1)
        self.repo.paths.resolve("data/specs/a.json").unlink()
        with self.assertRaises(SpecError):
            self.make(self.repo.candidate)

    def test_an_interrupted_run_leaves_no_output(self) -> None:
        real_write = fileio.write_bytes
        written: list[Path] = []

        def interrupt_the_second_write(
            path: Path,
            data: bytes,
            error: type[Epm2ModError] = FileError,
            *,
            read_back: bool = False,
        ) -> None:
            if written:
                raise KeyboardInterrupt
            written.append(path)
            real_write(path, data, error, read_back=read_back)

        with mock.patch(
            "epm2mod.pipeline.write_bytes", side_effect=interrupt_the_second_write
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.make(self.repo.tested)
        self.assertEqual(len(written), 1)
        self.assertEqual(self.repo.outputs(), [])

    def test_out_writes_one_file(self) -> None:
        folder = self.card.parent / "elsewhere"
        folder.mkdir()
        named = folder / "mod.bin"
        result = self.make(self.repo.tested, output=named)
        self.assertEqual(named.read_bytes(), result.image.read_bytes())
        self.assertEqual([p.name for p in folder.iterdir()], ["mod.bin"])

    def test_what_an_interrupted_run_left_is_ours_and_is_replaced(self) -> None:
        image = pipeline.image_path(self.repo.paths, "good")
        image.parent.mkdir()
        fileio.part_path(image).write_bytes(b"half a file")
        self.make(self.repo.tested)
        self.assertEqual(self.repo.outputs(), ["DCOLYMP/E1019999.BIN", "good.BIN"])
        fileio.part_path(image).write_bytes(b"half a file")
        pipeline.clear_outputs(self.repo.paths, "good")
        self.assertEqual(self.repo.outputs(), [])

    def test_every_firmware_file_is_read_back(self) -> None:
        with mock.patch(
            "epm2mod.pipeline.write_bytes", wraps=fileio.write_bytes
        ) as write:
            self.make(self.repo.tested, output=self.card / "x.BIN")
        self.assertEqual(write.call_count, 3)
        for call in write.call_args_list:
            self.assertIs(call.kwargs.get("read_back"), True, call)

    def test_a_dry_run_writes_nothing(self) -> None:
        result = self.make(self.repo.tested, dry_run=True)
        self.assertEqual(result.sha256, self.repo.sha256)
        self.assertEqual(len(result.files), 2)
        self.assertEqual(self.repo.outputs(), [])


class RecordTestTests(RepoCase):
    def record(
        self, description: builds.BuildDescription, sha: str, date: str
    ) -> builds.BuildDescription:
        return pipeline.record_test(
            self.repo.paths, description, sha, date, today=TODAY
        )

    def test_a_candidate_becomes_the_pinned_build(self) -> None:
        tested = self.record(self.repo.candidate, self.repo.sha256, "2026-11-10")
        self.assertEqual(tested.camera_tested, "2026-11-10")
        self.assertEqual(builds.pinned_description(self.repo.paths), tested)
        self.assertEqual(self.repo.outputs(), [])  # recording a test writes no firmware
        self.assertEqual(self.record(tested, self.repo.sha256, "2026-11-10"), tested)

    def test_refusals_change_nothing(self) -> None:
        before = builds.pinned_description(self.repo.paths)
        cases = [
            (self.repo.candidate, "0" * 64, "2026-11-10"),  # not what the build gives
            (self.repo.candidate, self.repo.sha256, "2026-11-21"),  # in the future
            (self.repo.candidate, self.repo.sha256, "10/11/2026"),
            (self.repo.candidate, "short", "2026-11-10"),
            (self.repo.tested, self.repo.sha256, "2026-11-10"),  # another record
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
            "data/specs/a.json", spec_json("a", [{**BYTE_OP, "new": "cccc"}])
        )
        with self.assertRaises(BuildError):
            self.record(self.repo.candidate, flashed, "2026-11-10")


class CommandLineTests(RepoCase):
    def setUp(self) -> None:
        super().setUp()
        # ``epm2mod pin`` asks the clock; give it a fixed day.
        clock = mock.patch.object(pipeline, "current_date", return_value=TODAY)
        clock.start()
        self.addCleanup(clock.stop)

    def run_cli(self, *argv: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cli.main(["--project", str(self.repo.paths.root), *argv])
        return status, out.getvalue() + err.getvalue()

    def test_builds(self) -> None:
        status, text = self.run_cli("builds")
        self.assertEqual(status, 0)
        self.assertIn("good (pinned): A tiny build [tested 2026-11-13, 1 specs]", text)
        self.assertIn("new: A tiny candidate [candidate, 1 specs]", text)

    def test_make_a_build(self) -> None:
        status, text = self.run_cli("make", "good")
        self.assertEqual(status, 0, text)
        self.assertIn(f"sha256 {self.repo.sha256}", text)
        self.assertEqual(self.repo.outputs(), ["DCOLYMP/E1019999.BIN", "good.BIN"])

    def test_make_a_candidate_by_its_name(self) -> None:
        self.repo.free_space_tool(0)
        out = self.card / "x.BIN"
        status, text = self.run_cli("make", "new", "-o", str(out))
        self.assertEqual(status, 0, text)
        self.assertIn("NOT camera-tested", text)
        self.assertIn("install --card DIR --build new --allow-untested", text)
        self.assertEqual(out.read_bytes(), self.repo.image)

    def test_lint_warnings_do_not_fail_and_a_report_that_cannot_be_made_does(
        self,
    ) -> None:
        for status, expected in (
            (0, 0),
            (2, 6),
        ):  # 2: the tool could not make its report
            script = (
                f"import sys\nprint('WARN  stand-in', sys.argv[1])\nsys.exit({status})"
            )
            self.repo.write("tools/buildlint.py", script.encode())
            code, text = self.run_cli("lint", "new")
            self.assertEqual(code, expected, text)
        self.assertIn("new is not linted", text)
        self.assertEqual(self.run_cli("lint", "none")[0], 3)

    def test_init_check_reports_an_incomplete_map_and_a_toolchain_of_another_source(
        self,
    ) -> None:
        from epm2mod import init

        paths = self.repo.paths
        objdump = init._objdump(paths)
        objdump.parent.mkdir(parents=True)
        objdump.write_text("#!/bin/sh\necho 'GNU objdump (stand-in)'\n")
        objdump.chmod(0o755)
        paths.firmware_map.parent.mkdir(parents=True, exist_ok=True)
        paths.firmware_map.write_text("x")  # the first file of the map only

        def missing(map_status: int, built_from: str) -> list[str]:
            self.repo.write(
                "tools/fwmap.py", f"import sys\nsys.exit({map_status})".encode()
            )
            init._source_record(paths).write_text(built_from + "\n")
            lines: list[str] = []
            with mock.patch.object(init, "_pinned_commit", return_value="abc"):
                return init.init(paths, True, lines.append)

        both = missing(1, "def")
        self.assertIn("the firmware map", both)
        self.assertIn("MN103 binutils", both)
        neither = missing(0, "abc")
        self.assertNotIn("the firmware map", neither)
        self.assertNotIn("MN103 binutils", neither)
        for (
            name
        ) in (
            init.OVERRIDES
        ):  # with CI set, a variable that replaces a pinned tool is refused here too
            with mock.patch.dict(os.environ, {"CI": "1", name: "/x/elsewhere"}):
                with self.assertRaisesRegex(UnavailableError, name):
                    init.init(paths, True, lambda line: None)

    def test_init_does_not_take_an_edited_emulator_for_the_pinned_one(self) -> None:
        from epm2mod import init

        paths = self.repo.paths
        marker = paths.location("emulator").joinpath(*init._BOOT_LAB)
        marker.parent.mkdir(parents=True)
        marker.write_text("x")
        answers = {"rev-parse": "abc", "status": " M emu/bin/boot.mjs"}
        with (
            mock.patch.object(init, "_pinned_commit", return_value="abc"),
            mock.patch.object(
                init,
                "_run",
                lambda command, cwd, what, env=None: answers[str(command[1])],
            ),
        ):
            with self.assertRaisesRegex(
                UnavailableError, "changes that are not in its commit"
            ):
                init._emulator(paths, False)
            answers["status"] = ""
            self.assertEqual(init._emulator(paths, False), "abc")

    def test_a_build_is_named_not_given_as_a_path(self) -> None:
        for argv in (
            ("make", "data/builds/new.json"),
            ("make", "none"),
            ("pin", "nope", "--date", "2026-11-10", "--sha256", "0" * 64),
        ):
            with self.subTest(argv=argv):
                status, text = self.run_cli(*argv)
                self.assertEqual(status, 3, text)
                self.assertIn("'epm2mod builds' lists them", text)

    def test_make_removes_the_old_outputs_before_it_reads_the_description(
        self,
    ) -> None:
        self.assertEqual(self.run_cli("make", "good")[0], 0)
        self.assertTrue(self.repo.outputs())
        builds.description_path(self.repo.paths, "good").write_text("{broken")
        status, text = self.run_cli("make", "good")
        self.assertEqual(status, 7, text)
        self.assertEqual(self.repo.outputs(), [])

    def test_a_failed_pinned_run_removes_the_image_of_the_earlier_run(self) -> None:
        for damage in ("<<<<<<< HEAD\n", '{"what": "x"}'):
            self.assertEqual(self.run_cli("make", "good")[0], 0)
            good = builds.description_path(self.repo.paths, "good")
            saved = good.read_text()
            good.write_text(damage)  # not JSON; then: not a valid description
            status, text = self.run_cli("make", "good")
            self.assertEqual(status, 7, text)
            self.assertEqual(self.repo.outputs(), [])
            good.write_text(saved)

    def test_make_needs_the_build(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stderr(io.StringIO()):
                self.run_cli("make")
        self.assertEqual(raised.exception.code, 2)

    def test_an_empty_argument_is_an_error(self) -> None:
        record = ("--date", "2026-11-10", "--sha256", self.repo.sha256)
        spec_file = str(self.repo.paths.resolve("data/specs/a.json"))
        cases: list[tuple[tuple[str, ...], int]] = [
            (("make", ""), 3),
            (("make", "good", "-o", ""), 2),
            (("apply", spec_file, "--from", spec_file, "-o", ""), 2),
            (("apply", spec_file, "--from", spec_file, "-o", "/"), 2),
            (("pin", "", *record), 3),
            (("install", "--card", ""), 2),
        ]
        for argv, wanted in cases:
            with self.subTest(argv=argv):
                status, text = self.run_cli(*argv)
                self.assertEqual(status, wanted, text)
                self.assertTrue(text.startswith("epm2mod: "), text)

    def test_pin(self) -> None:
        argv = ("pin", "new", "--date", "2026-11-10", "--sha256")
        status, text = self.run_cli(*argv, "0" * 64)
        self.assertEqual(status, 5, text)
        self.assertEqual(builds.pinned_description(self.repo.paths).name, "good")
        status, text = self.run_cli(*argv, self.repo.sha256, "--dry-run")
        self.assertEqual(status, 0, text)
        self.assertEqual(builds.pinned_description(self.repo.paths).name, "good")
        status, text = self.run_cli(*argv, self.repo.sha256)
        self.assertEqual(status, 0, text)
        self.assertIn("pinned: new", text)
        pinned = builds.pinned_description(self.repo.paths)
        self.assertEqual(
            (pinned.name, pinned.sha256, pinned.camera_tested),
            ("new", self.repo.sha256, "2026-11-10"),
        )

    def test_pin_no_pin_records_the_test_and_keeps_the_pinned_build(self) -> None:
        pointer = self.repo.paths.pinned.read_bytes()
        argv = ("pin", "new", "--date", "2026-11-10", "--sha256", self.repo.sha256)
        status, text = self.run_cli(*argv, "--no-pin")
        self.assertEqual(status, 0, text)
        self.assertIn("recorded: new", text)
        self.assertEqual(self.repo.paths.pinned.read_bytes(), pointer)
        recorded = self.repo.paths.build("new")
        self.assertEqual(
            (recorded.sha256, recorded.camera_tested), (self.repo.sha256, "2026-11-10")
        )
        status, text = self.run_cli(*argv[:3], "2026-11-11", *argv[4:], "--no-pin")
        self.assertEqual(status, 7, text)  # a test record is never rewritten

    def test_fetch_stock(self) -> None:
        path = stock.stock_path(self.repo.paths, TINY_STOCK)
        path.unlink()
        with answers(catalog_answer(), TINY):
            status, text = self.run_cli("fetch-stock")
        self.assertEqual(status, 0, text)
        self.assertEqual(path.read_bytes(), TINY)
        with answers() as opened:
            status, text = self.run_cli("fetch-stock")
            opened.assert_not_called()
        self.assertEqual(status, 0, text)
        self.assertIn("already there", text)
        path.unlink()
        with answers(catalog_answer(), TINY[:-1]):
            status, text = self.run_cli("fetch-stock")
        self.assertEqual(status, 5, text)
        self.assertFalse(path.exists())
        with answers(OSError):
            status, text = self.run_cli("fetch-stock")
        self.assertEqual(status, 6, text)

    def test_apply(self) -> None:
        spec_file = str(self.repo.paths.resolve("data/specs/a.json"))
        out = self.repo.paths.root / "out" / "x.BIN"
        start = self.repo.write("start.BIN", TINY)
        with mock.patch("epm2mod.cli.write_bytes", wraps=fileio.write_bytes) as write:
            status, text = self.run_cli(
                "apply", spec_file, "--from", str(start), "-o", str(out), "-v"
            )
        self.assertIs(write.call_args.kwargs.get("read_back"), True)
        self.assertEqual(status, 0, text)
        self.assertEqual(out.read_bytes(), self.repo.image)
        self.assertIn("[a]", text)
        self.assertIn(f"sha256 {self.repo.sha256}", text)
        status, text = self.run_cli(
            "apply", spec_file, "-o", str(out), "--from", str(start) + ".missing"
        )
        self.assertEqual(status, 3, text)
        with self.assertRaises(SystemExit) as raised:  # --from is needed
            with contextlib.redirect_stderr(io.StringIO()):
                self.run_cli("apply", spec_file, "-o", str(out))
        self.assertEqual(raised.exception.code, 2)

    def test_apply_checks_the_sha256_that_a_single_spec_states(self) -> None:
        out = self.repo.paths.root / "x.BIN"
        start = str(stock.stock_path(self.repo.paths, TINY_STOCK))
        for expected, status_wanted in (("0" * 64, 5), (self.repo.sha256, 0)):
            raw = {**spec_json("b", [BYTE_OP]), "expected_sha256": expected}
            spec_file = str(self.repo.write_json("data/specs/b.json", raw))
            status, text = self.run_cli(
                "apply", spec_file, "--from", start, "-o", str(out)
            )
            self.assertEqual(status, status_wanted, text)
            self.assertEqual(out.exists(), status_wanted == 0)

    def test_apply_of_several_specs_does_not_use_a_single_spec_sha256(self) -> None:
        first = {**spec_json("b", [BYTE_OP]), "expected_sha256": "0" * 64}
        other_op = {**BYTE_OP, "offset": "0x20", "expect": "2021"}
        files = [
            str(self.repo.write_json("data/specs/b.json", first)),
            str(self.repo.write_json("data/specs/c.json", spec_json("c", [other_op]))),
        ]
        out = self.repo.paths.root / "x.BIN"
        start = str(stock.stock_path(self.repo.paths, TINY_STOCK))
        status, text = self.run_cli("apply", *files, "--from", start, "-o", str(out))
        self.assertEqual(status, 0, text)
        self.assertTrue(out.exists())

    def test_apply_does_not_write_over_the_stock_firmware(self) -> None:
        spec_file = str(self.repo.paths.resolve("data/specs/a.json"))
        stock_file = stock.stock_path(self.repo.paths, TINY_STOCK)
        link = self.repo.paths.root / "link.BIN"
        link.symlink_to(stock_file)
        for out in (stock_file, stock_file.parent / ".." / stock_file, link):
            with self.subTest(out=out.name):
                status, text = self.run_cli(
                    "apply", spec_file, "--from", str(stock_file), "-o", str(out)
                )
                self.assertEqual(status, 2, text)
                self.assertEqual(stock_file.read_bytes(), TINY)

    @unittest.skipUnless(hasattr(signal, "SIGTERM"), "no SIGTERM here")
    def test_a_termination_signal_is_an_interrupt(self) -> None:
        before = signal.getsignal(signal.SIGTERM)
        cleaned_up = []
        with self.assertRaises(KeyboardInterrupt):
            with cli.interruptible():
                try:
                    signal.raise_signal(signal.SIGTERM)
                finally:  # further signals, during the clean-up, are ignored
                    signal.raise_signal(signal.SIGTERM)
                    signal.raise_signal(signal.SIGINT)
                    cleaned_up.append(True)
        self.assertEqual(cleaned_up, [True])
        self.assertIs(signal.getsignal(signal.SIGTERM), before)

    def test_an_interrupted_command_leaves_no_output_and_says_so(self) -> None:
        self.assertEqual(self.run_cli("make", "good")[0], 0)

        def terminate(*args: Any, **kw: Any) -> None:
            signal.raise_signal(signal.SIGTERM)

        with mock.patch("epm2mod.pipeline.write_bytes", side_effect=terminate):
            status, text = self.run_cli("make", "good")
        self.assertEqual(status, 130, text)
        self.assertIn("interrupted", text)
        self.assertEqual(self.repo.outputs(), [])

    def test_python_m_epm2mod(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(ROOT / "cli" / "src")}
        done = subprocess.run(
            [sys.executable, "-m", "epm2mod", "--version"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), epm2mod.__version__)

    def test_errors_are_one_message_and_their_status(self) -> None:
        cases = [
            (("pin", "new", "--date", "2026-13-40", "--sha256", "0" * 64), 2),
            (("pin", "new", "--date", "2999-01-01", "--sha256", self.repo.sha256), 2),
            (("inspect", str(self.repo.paths.root)), 3),
            (("inspect", "no-such-file"), 3),
            (("apply", "no-such-spec.json", "--from", "x", "-o", "out.BIN"), 3),
        ]
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.repo.paths.root)
        for argv, wanted in cases:
            with self.subTest(argv=argv):
                status, text = self.run_cli(*argv)
                self.assertEqual(status, wanted, text)
                self.assertTrue(text.startswith("epm2mod: "), text)
                self.assertNotIn("Traceback", text)
        self.assertEqual(self.repo.outputs(), [])

    def test_a_wrong_command_line_is_status_2(self) -> None:
        for argv in (
            (),
            ("nope",),
            ("pin", "new"),
            ("readme",),
            ("info", "x"),
            ("make", "--card", "x"),
            ("install",),
            ("restore",),
        ):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stderr(io.StringIO()):
                    self.run_cli(*argv)
            self.assertEqual(raised.exception.code, 2)

    def test_not_in_a_project(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(cli.main(["--project", folder, "builds"]), 6)
            self.assertIn(f"{folder}: no {MANIFEST} there", err.getvalue())
            # no --project: the search goes up from the current folder and finds none
            here = os.getcwd()
            os.chdir(folder)
            try:
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    status = cli.main(["builds", "--json"])
            finally:
                os.chdir(here)
            self.assertEqual(status, 6)
            self.assertIn("give --project DIR", err.getvalue())

    def test_the_project_is_found_above_the_current_folder(self) -> None:
        inside = self.repo.paths.root / "deep" / "er"
        inside.mkdir(parents=True)
        here = os.getcwd()
        os.chdir(inside)
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(cli.main(["builds"]), 0)
        finally:
            os.chdir(here)
        self.assertIn("good (pinned): A tiny build", out.getvalue())

    def test_out_dir_names_the_output_folder(self) -> None:
        out = self.card.parent / "elsewhere"
        status, text = self.run_cli("make", "good", "--out-dir", str(out))
        self.assertEqual(status, 0, text)
        self.assertEqual((out / "good.BIN").read_bytes(), self.repo.image)
        self.assertEqual(
            (out / "DCOLYMP" / "E1019999.BIN").read_bytes(), self.repo.image
        )
        self.assertEqual(self.repo.outputs(), [])

    def test_a_renamed_output_folder_in_the_manifest(self) -> None:
        write_manifest(self.repo.paths.root, cache="firmware", output="made")
        status, text = self.run_cli("make", "good")
        self.assertEqual(status, 0, text)
        made = self.repo.paths.root / "made"
        self.assertEqual((made / "good.BIN").read_bytes(), self.repo.image)
        self.assertTrue((made / "DCOLYMP" / "E1019999.BIN").is_file())
        self.assertFalse((self.repo.paths.root / "build").exists())

    def test_cache_names_the_folder_of_the_stock_firmware(self) -> None:
        cache = self.card.parent / "cache"
        status, text = self.run_cli("make", "good", "--cache", str(cache), "--dry-run")
        self.assertEqual(status, 0, text)
        with answers(catalog_answer(), TINY):
            status, text = self.run_cli("fetch-stock", "--cache", str(cache))
        self.assertEqual(status, 0, text)
        self.assertIn(f"kept at {cache / TINY_STOCK.file_name}", text)
        self.assertEqual((cache / TINY_STOCK.file_name).read_bytes(), TINY)
        stock.stock_path(self.repo.paths, TINY_STOCK).unlink()
        status, text = self.run_cli("make", "good", "--cache", str(cache))
        self.assertEqual(status, 0, text)

    def test_stock_uses_a_copy_and_downloads_nothing(self) -> None:
        copy = self.repo.write("copy.BIN", TINY)
        stock.stock_path(self.repo.paths, TINY_STOCK).unlink()
        with answers() as opened:
            status, text = self.run_cli("make", "good", "--stock", str(copy))
            self.assertEqual(status, 0, text)
            status, text = self.run_cli("fetch-stock", "--stock", str(copy))
            self.assertEqual(status, 0, text)
            self.assertIn(f"kept at {copy}", text)
            missing = self.repo.paths.root / "none.BIN"
            status, text = self.run_cli("make", "good", "--stock", str(missing))
            self.assertEqual(status, 3, text)
            wrong = self.repo.write("wrong.BIN", TINY[:-1] + b"\0")
            for argv in (
                ("make", "good"),
                ("fetch-stock",),
                ("restore", "-o", str(self.card.parent / "x.BIN")),
            ):
                with self.subTest(argv=argv):
                    status, text = self.run_cli(*argv, "--stock", str(wrong))
                    self.assertEqual(status, 5, text)
                    self.assertIn("the sha256 differs", text)
        opened.assert_not_called()
        self.assertFalse(stock.stock_path(self.repo.paths, TINY_STOCK).exists())

    def test_inspect(self) -> None:
        good = self.repo.write("fw.BIN", TINY)
        status, text = self.run_cli("inspect", str(good))
        self.assertEqual(status, 0, text)
        self.assertIn(TINY_STOCK.sha256, text)
        self.assertIn("model E-PM2, build Olympus original", text)
        damaged = bytearray(TINY)
        damaged[40] ^= 1
        status, text = self.run_cli(
            "inspect", str(self.repo.write("bad.BIN", bytes(damaged)))
        )
        self.assertEqual(status, 1, text)
        self.assertIn("will not work", text)

    def test_every_command_has_help_with_examples(self) -> None:
        for name in cli.COMMANDS:
            with self.subTest(name=name):
                out = io.StringIO()
                with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                    cli.main([*name.split(), "--help"])
                text = out.getvalue()
                self.assertIn("examples:", text)
                self.assertIn("Needs:", text)
                self.assertIn("Network:", text)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            cli.main(["--help"])
        for group in cli.GROUPS:
            self.assertIn(group, out.getvalue())

    def test_the_docs_check_of_this_repository(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            argv = ["--project", str(ROOT), "generate", "--check"]
            self.assertEqual(cli.main(argv), 0)


class ReadmeTests(unittest.TestCase):
    def test_the_readme_is_up_to_date(self) -> None:
        self.assertTrue(readme.is_current(PATHS), "run: uv run epm2mod generate")

    def test_marker_problems(self) -> None:
        text = readme.generated_text(PATHS)
        begin, end = "<!-- BEGIN GENERATED: films -->", "<!-- END GENERATED: films -->"
        block = text[text.index(begin) : text.index(end) + len(end)]
        broken = {
            "unknown block": text
            + "\n<!-- BEGIN GENERATED: nope -->\n<!-- END GENERATED: nope -->",
            "no markers": "no markers at all",
            "missing end": text.replace(end, ""),
            "missing begin": text.replace(begin, ""),
            "twice": text + "\n" + block,
            "an end without a begin": text + "\n" + end,
            "a begin without an end": text + "\n" + begin + "\n",
        }
        for name, bad in broken.items():
            with self.subTest(name), self.assertRaises(BuildError):
                readme.update(bad, PATHS)

    def test_text_outside_the_markers_is_kept(self) -> None:
        text = readme.generated_text(PATHS)
        fresh = readme.update("BEFORE\n" + text + "\nAFTER", PATHS)
        self.assertTrue(fresh.startswith("BEFORE\n") and fresh.endswith("\nAFTER"))

    def test_windows_line_ends(self) -> None:
        text = readme.generated_text(PATHS).replace("\n", "\r\n")
        stale = text.replace(stock.EPM2_V16.sha256, "0" * 64)
        fresh = readme.update(stale, PATHS)
        self.assertIn(stock.EPM2_V16.sha256, fresh)
        self.assertEqual(readme.update(fresh, PATHS), fresh)
        self.assertIn("-->\r\n", fresh)

    def test_the_builds_table_lists_tested_builds_only(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = TinyRepo(Path(folder))
            table = readme.builds_block(repo.paths, repo.paths.root)
        self.assertIn("| `good` (pinned) | A tiny build | 1 | 2026-11-13 |", table)
        self.assertNotIn("new", table)

    def test_cell(self) -> None:
        self.assertEqual(readme.cell("a | b\nc"), "a \\| b c")
        self.assertEqual(readme.cell("<!-- x --> & y"), "&lt;!-- x --&gt; &amp; y")

    def stale_copy(self) -> RepoPaths:
        """Return a temporary repository whose README has out-of-date blocks."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        paths = RepoPaths(write_manifest(Path(folder)))
        for name in ("builds", "films"):
            shutil.copytree(
                ROOT / "data" / name,
                paths.root / "data" / name,
                ignore=shutil.ignore_patterns("*.npz", "*.md"),
            )
        shutil.copy(PATHS.pinned, paths.pinned)
        stale = "".join(
            f"<!-- BEGIN GENERATED: {name} -->\nSTALE TEXT\n<!-- END GENERATED: {name} -->\n"
            for name in readme.BLOCKS
        )
        fileio.write_text(paths.readme, "# Title\n" + stale)
        return paths

    def test_rewrite(self) -> None:
        paths = self.stale_copy()
        self.assertFalse(readme.is_current(paths))
        self.assertTrue(readme.rewrite(paths))
        self.assertTrue(readme.is_current(paths))
        self.assertFalse(readme.rewrite(paths))
        text = fileio.read_text(paths.readme)
        self.assertNotIn("STALE TEXT", text)
        self.assertTrue(text.startswith("# Title\n"))

    def test_blocks_can_be_in_several_documents(self) -> None:
        paths = self.stale_copy()
        text = fileio.read_text(paths.readme)
        marker = "<!-- BEGIN GENERATED: builds -->"
        cut = text.index(marker)
        fileio.write_text(paths.readme, text[:cut])
        fileio.write_text(
            paths.resolve("data/builds/README.md"), "# Builds\n" + text[cut:]
        )
        self.assertTrue(readme.rewrite(paths))
        self.assertTrue(readme.is_current(paths))
        self.assertNotIn(
            "STALE TEXT", fileio.read_text(paths.resolve("data/builds/README.md"))
        )
        self.assertNotIn(marker, fileio.read_text(paths.readme))
        # The same block in two documents is refused.
        fileio.write_text(paths.resolve("docs/user/install.md"), text[cut:])
        with self.assertRaisesRegex(BuildError, "found 2 times"):
            readme.is_current(paths)

    def test_the_generate_command_writes_the_documents(self) -> None:
        paths = self.stale_copy()

        def run(*argv: str) -> tuple[int, str]:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                with contextlib.redirect_stderr(io.StringIO()):
                    project = ["--project", str(paths.root)]
                    return cli.main([*project, "generate", *argv]), out.getvalue()

        status, text = run("--check")
        self.assertEqual(status, 1)
        self.assertIn(f"{paths.readme}: the generated parts are out of date", text)
        self.assertEqual(
            run(),
            (
                0,
                f"wrote {paths.readme}\n"
                f"wrote {paths.resolve('docs/reference/cli.md')}\n",
            ),
        )
        self.assertEqual(run(), (0, "documents: no change\n"))
        self.assertEqual(run("--check")[0], 0)
        self.assertEqual(
            fileio.read_text(paths.resolve("docs/reference/cli.md")),
            fileio.read_text(ROOT / "docs" / "reference" / "cli.md"),
        )


class SourceTests(unittest.TestCase):
    def test_every_module_class_and_function_has_a_docstring(self) -> None:
        missing = []
        for path in sorted((ROOT / "cli" / "src" / "epm2mod").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            kinds = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            named = [node for node in ast.walk(tree) if isinstance(node, kinds)]
            if ast.get_docstring(tree) is None:
                missing.append(f"{path.name}: the module")
            missing += [
                f"{path.name}: {node.name}"
                for node in named
                if ast.get_docstring(node) is None
            ]
        self.assertEqual(missing, [])


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class RealFirmwareTests(unittest.TestCase):
    def test_the_stock_file_round_trips(self) -> None:
        data = stock.read_stock(PATHS, stock.EPM2_V16)
        self.assertEqual(len(data), stock.EPM2_V16.size)
        parsed = container.parse(data)
        self.assertTrue(parsed.checksums_ok)
        self.assertEqual(container.serialize(parsed), data)

    def test_every_tested_build_gives_its_sha256(self) -> None:
        data = stock.read_stock(PATHS, stock.EPM2_V16)
        tested = [build for build in builds.all_descriptions(PATHS) if build.tested]
        self.assertTrue(tested)
        for build in tested:
            with self.subTest(build=build.name):
                specs = pipeline.load_specs(PATHS, build)
                _, digest = pipeline.build_image(build, specs, data)
                self.assertEqual(digest, build.sha256)

    def test_make_and_the_command_line_on_the_pinned_build(self) -> None:
        pinned = builds.pinned_description(PATHS)
        with tempfile.TemporaryDirectory() as folder:
            paths = RepoPaths(write_manifest(Path(folder)))
            (paths.root / "firmware").symlink_to(ROOT / "firmware")
            (paths.root / "data").mkdir()
            for name in ("specs", "builds", "films"):
                (paths.root / "data" / name).symlink_to(ROOT / "data" / name)
            shutil.copy(PATHS.pinned, paths.pinned)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(
                    cli.main(["--project", folder, "make", pinned.name]), 0
                )
            image = paths.output / f"{pinned.name}.BIN"
            self.assertEqual(sha256_bytes(image.read_bytes()), pinned.sha256)
            self.assertIn(f"sha256 {pinned.sha256}", out.getvalue())
            # make writes the firmware only
            self.assertFalse((paths.output / "EPM2LOOK.BIN").exists())


if __name__ == "__main__":
    unittest.main()

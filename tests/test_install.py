"""Tests of the commands for camera owners: ``install``, ``films``, ``films set``, ``restore``, ``inspect``, ``cards``.

    uv run python -m unittest discover -s tests

They run on the tiny firmware of ``test_package`` and need nothing but the repository. ``NoCheckoutTests`` lays
out a folder as the release zip does (``release.data_files``) and runs every command for camera owners there, to
show that they need no checkout. ``JsonTests`` compares the keys of real ``--json`` documents with the keys that
``cli.COMMANDS`` (and so ``docs/cli.md``) lists.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT, make_container  # noqa: E402
from test_package import (  # noqa: E402
    BYTE_OP,
    TINY,
    TINY_STOCK,
    TinyRepo,
    answers,
    catalog_answer,
    spec_json,
)

from epm2mod import (  # noqa: E402
    builds,
    camera_steps,
    cardio,
    cards,
    catalogue,
    cli,
    fileio,
    pipeline,
    readme,
    release,
    spec,
)
from epm2mod.errors import (  # noqa: E402
    CardError,
    CheckError,
    NotFoundError,
    RefusedError,
    RepositoryError,
    UsageError,
)
from epm2mod.hashing import sha256_bytes  # noqa: E402
from epm2mod.looks import lookfile, records  # noqa: E402
from epm2mod.paths import ROOT_ENV, RepoPaths  # noqa: E402

FIRMWARE = "DCOLYMP/E1019999.BIN"
FILMS_OP = {**BYTE_OP, "offset": "0x20", "expect": "2021", "new": "ccdd"}
LOADER = "patches/loader.json"


class FilmRepo(TinyRepo):
    """The tiny repository with the film records and a build that loads the films from the card (``films``)."""

    def __init__(self, folder: Path) -> None:
        super().__init__(folder)
        self.write(
            "looks/film-records.json",
            (ROOT / "looks" / "film-records.json").read_bytes(),
        )
        self.write_json(LOADER, spec_json("loader", [FILMS_OP]))
        specs = ("patches/a.json", LOADER)
        loaded = spec.apply_specs(
            TINY, [spec.load_spec(self.paths.resolve(name)) for name in specs]
        )
        self.films_image = loaded.image
        self.films_build = builds.BuildDescription(
            "films",
            "A tiny build with films",
            specs,
            sha256_bytes(loaded.image),
            "2026-11-14",
            stock=TINY_STOCK.file_name,
        )
        builds.pin(self.paths, self.films_build)


class CardCase(unittest.TestCase):
    """A tiny repository with films, and a stand-in SD card that ``cards.cards`` lists."""

    def setUp(self) -> None:
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.folder = Path(folder)
        self.repo = FilmRepo(self.folder / "repo")
        self.card = self.folder / "card"
        (self.card / "DCIM").mkdir(parents=True)
        env = mock.patch.dict(os.environ, {cards.TEST_CARDS_ENV: str(self.card)})
        env.start()
        self.addCleanup(env.stop)

    def install(self, **kw: Any) -> pipeline.Outcome:
        """Run ``pipeline.install`` on the tiny repository and the card; no films unless ``choices`` names them."""
        kw.setdefault("choices", [])
        return pipeline.install(self.repo.paths, self.card, **kw)

    def run_cli(
        self, *argv: str, root: Path | None = None, prog: str | None = None
    ) -> tuple[int, str, str]:
        """Run the command line; return status, stdout and stderr."""
        out, err = io.StringIO(), io.StringIO()
        env = {ROOT_ENV: str(root or self.repo.paths.root)}
        if prog is not None:
            env[cli.PROG_ENV] = prog
        with (
            mock.patch.dict(os.environ, env),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            status = cli.main(list(argv))
        return status, out.getvalue(), err.getvalue()

    def json_of(self, *argv: str, root: Path | None = None) -> dict[str, Any]:
        """Run a command with ``--json`` and return its document; the run must succeed."""
        status, out, err = self.run_cli(*argv, "--json", root=root)
        self.assertEqual(status, 0, err)
        document: dict[str, Any] = json.loads(out)
        self.assertEqual(document["schema"], cli.SCHEMA)
        self.assertIs(document["ok"], True)
        return document

    def card_files(self) -> list[str]:
        """Return the files on the card, relative to it."""
        return sorted(
            p.relative_to(self.card).as_posix()
            for p in self.card.rglob("*")
            if p.is_file()
        )


class CardioTests(CardCase):
    def test_a_folder_that_is_not_a_camera_card_is_refused(self) -> None:
        plain = self.folder / "plain"
        (plain / "DCIM").mkdir(parents=True)
        no_dcim = self.folder / "no-dcim"
        no_dcim.mkdir()
        files = {FIRMWARE: cardio.Content.of(TINY)}
        with self.assertRaisesRegex(CardError, "not an SD card"):
            cardio.plan(plain, files)
        with self.assertRaisesRegex(CardError, "no such folder"):
            cardio.plan(self.folder / "mistyped", files)
        with self.assertRaisesRegex(CardError, "Format the card in the camera"):
            cardio.plan(no_dcim, files, is_card=lambda folder: True)
        self.assertEqual(CardError("x").exit_status, 6)

    def test_a_card_without_room_is_refused(self) -> None:
        usage = shutil.disk_usage(self.card)._replace(free=10)
        with mock.patch("epm2mod.cardio.shutil.disk_usage", return_value=usage):
            with self.assertRaisesRegex(CardError, "the card is full"):
                cardio.plan(self.card, {FIRMWARE: cardio.Content.of(TINY)})

    def test_firmware_for_another_model_is_refused(self) -> None:
        other = make_container([bytes(48)])
        other_model = bytearray(other)
        other_model[2:4] = b"\x10\x00"
        cardio.check_model(TINY)
        with self.assertRaisesRegex(CheckError, "not for the E-PM2"):
            cardio.check_model(bytes(other_model))
        with self.assertRaisesRegex(CheckError, "not a firmware file"):
            cardio.check_model(b"not firmware")
        self.assertEqual(CheckError("x").exit_status, 5)

    def test_extra_files_in_dcolymp_are_removed_and_a_folder_stops_the_write(
        self,
    ) -> None:
        folder = self.card / "DCOLYMP"
        folder.mkdir()
        for name in ("._E1019999.BIN", "OTHER.BIN", "E1019999.BIN.part"):
            (folder / name).write_bytes(b"x")
        done = cardio.plan(self.card, {FIRMWARE: cardio.Content.of(TINY)})
        self.assertEqual(
            [path.name for path in done.removed],
            ["._E1019999.BIN", "E1019999.BIN.part", "OTHER.BIN"],
        )
        cardio.write(done)
        self.assertEqual(self.card_files(), ["DCOLYMP/E1019999.BIN"])
        (folder / "sub").mkdir()
        with self.assertRaisesRegex(CardError, "holds a folder"):
            cardio.plan(self.card, {FIRMWARE: cardio.Content.of(TINY)})

    def test_a_film_file_alone_leaves_dcolymp_alone(self) -> None:
        folder = self.card / "DCOLYMP"
        folder.mkdir()
        (folder / "._E1019999.BIN").write_bytes(b"x")
        done = cardio.plan(self.card, {cardio.FILMS: cardio.Content.of(b"films")})
        self.assertEqual(done.removed, ())

    def test_unchanged_files_are_not_written_again(self) -> None:
        files = {FIRMWARE: cardio.Content.of(TINY)}
        cardio.write(cardio.plan(self.card, files))
        again = cardio.plan(self.card, files)
        self.assertEqual([p.unchanged for p in again.files], [True])
        self.assertTrue(again.files[0].to_json()["unchanged"])
        with mock.patch("epm2mod.cardio.write_file") as write:
            cardio.write(again)
        write.assert_not_called()
        other = cardio.plan(self.card, {FIRMWARE: cardio.Content.of(TINY + b"x")})
        self.assertEqual([p.unchanged for p in other.files], [False])

    def test_a_write_is_read_back_by_its_sha256(self) -> None:
        target = self.card / FIRMWARE
        target.parent.mkdir()
        target.write_bytes(b"older firmware")
        real_read = fileio.read_bytes

        def other_bytes(path: Path, error: Any = None) -> bytes:
            return b"other" if path == target else real_read(path)

        with mock.patch("epm2mod.cardio.read_bytes", side_effect=other_bytes):
            with self.assertRaisesRegex(CheckError, "gives back"):
                cardio.write_file(target, TINY)
        with mock.patch.object(Path, "read_bytes", return_value=b"other bytes"):
            with self.assertRaisesRegex(CardError, "NOT on the card"):
                cardio.write_file(target, b"new firmware")

    def test_an_interrupt_in_the_card_write_leaves_only_the_old_file_there(
        self,
    ) -> None:
        target = self.card / FIRMWARE
        target.parent.mkdir()
        target.write_bytes(b"older firmware")
        real_replace = os.replace

        def interrupt_on_card(source: Path, destination: Path) -> None:
            if Path(destination) == target:
                raise KeyboardInterrupt
            real_replace(source, destination)

        with mock.patch("epm2mod.fileio.os.replace", side_effect=interrupt_on_card):
            with self.assertRaises(KeyboardInterrupt):
                self.install()
        self.assertEqual([p.name for p in target.parent.iterdir()], [target.name])
        self.assertEqual(target.read_bytes(), b"older firmware")

    def test_output_paths(self) -> None:
        folder = self.folder / "out"
        folder.mkdir()
        self.assertEqual(cardio.output_path(str(folder / "y.bin")), folder / "y.bin")
        for text, words in (
            ("", "needs a file"),
            (str(folder), "is a folder"),
            (str(self.folder / "new") + "/", "is a folder"),
            (str(self.card / "E1019999.BIN"), "use --card"),
            (str(self.card / "DCOLYMP" / "E1019999.BIN"), "use --card"),
        ):
            with self.subTest(text=text), self.assertRaisesRegex(UsageError, words):
                cardio.output_path(text)

    def test_eject_calls_the_system(self) -> None:
        done = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("epm2mod.cardio.subprocess.run", return_value=done) as run:
            cardio.eject(self.card)
        self.assertTrue(run.called)
        failed = mock.Mock(returncode=1, stdout="", stderr="busy")
        with mock.patch("epm2mod.cardio.subprocess.run", return_value=failed):
            with self.assertRaisesRegex(CardError, "busy"):
                cardio.eject(self.card)


class InstallTests(CardCase):
    def test_no_film_writes_the_firmware_only(self) -> None:
        lines: list[str] = []
        steps: list[int] = []
        outcome = self.install(log=lines.append, step=steps.append)
        self.assertEqual(self.card_files(), [FIRMWARE])
        self.assertEqual((self.card / FIRMWARE).read_bytes(), self.repo.films_image)
        self.assertEqual(steps, [1, 2, 3, 4, 5])
        self.assertEqual([p.role for p in outcome.files], ["firmware"])
        self.assertEqual(outcome.files[0].content.sha256, self.repo.films_build.sha256)
        ids = [step.id for step in outcome.steps]
        self.assertEqual(ids[0], "eject")
        self.assertNotIn("load-films", ids)
        self.assertEqual(
            outcome.steps[-1].text,
            "Check: MENU → ART shows the art filters, such as Pop Art.",
        )
        self.assertEqual(self.repo.outputs(), [])  # install writes no output folder

    def test_only_the_named_slots_get_a_film(self) -> None:
        outcome = self.install(choices=["ART5=velvia", "ART2=c200"])
        looks = lookfile.unpack((self.card / "EPM2LOOK.BIN").read_bytes())
        self.assertEqual(
            [(look.slot, look.name) for look in looks], [(4, "Velvia"), (1, "C200")]
        )
        self.assertIn("load-films", [step.id for step in outcome.steps])
        self.assertEqual(
            outcome.steps[-1].text, "Check: MENU → ART shows C200 in ART 2."
        )

    def test_wrong_choices_are_usage_errors(self) -> None:
        for choices, words in (
            (["ART2=velvia", "ART2=c200"], "named twice"),
            (["ART13=velvia"], "1 to 12"),
            (["ART2=nofilm"], "portra-400"),
            (["velvia"], "ART<1-12>"),
        ):
            with self.subTest(choices=choices):
                with self.assertRaisesRegex(UsageError, words):
                    self.install(choices=choices)
        self.assertEqual(self.card_files(), [])

    def test_an_untested_build_needs_allow_untested(self) -> None:
        self.repo.free_space_tool(0)
        with self.assertRaises(RefusedError) as raised:
            self.install(build="new")
        self.assertEqual(raised.exception.exit_status, 4)
        self.assertEqual(raised.exception.override, "--allow-untested")
        self.assertIn("--allow-untested", str(raised.exception))
        lines: list[str] = []
        self.install(build="new", allow_untested=True, log=lines.append)
        self.assertIn("NOT camera-tested", "\n".join(lines))
        self.assertEqual(self.card_files(), [FIRMWARE])
        with self.assertRaises(NotFoundError):
            self.install(build="none")

    def test_a_dry_run_writes_nothing_and_needs_no_network(self) -> None:
        stock_file = self.repo.paths.stock_file(TINY_STOCK)
        stock_file.unlink()
        (self.card / "DCOLYMP").mkdir()
        (self.card / "DCOLYMP" / "._x").write_bytes(b"x")
        with answers() as opened:
            outcome = self.install(dry_run=True)
            opened.assert_not_called()
        self.assertTrue(outcome.dry_run)
        self.assertEqual(outcome.files[0].content.sha256, self.repo.films_build.sha256)
        self.assertEqual([p.name for p in outcome.removed], ["._x"])
        self.assertEqual(self.card_files(), ["DCOLYMP/._x"])

    def test_a_card_problem_is_found_before_any_work(self) -> None:
        plain = self.folder / "plain"
        plain.mkdir()
        with mock.patch("epm2mod.pipeline.obtain_stock") as obtain:
            with self.assertRaises(CardError):
                pipeline.install(self.repo.paths, plain, [])
            obtain.assert_not_called()

    def test_install_downloads_the_stock_firmware_if_it_is_absent(self) -> None:
        self.repo.paths.stock_file(TINY_STOCK).unlink()
        with answers(catalog_answer(), TINY):
            self.install()
        self.assertEqual((self.card / FIRMWARE).read_bytes(), self.repo.films_image)

    def test_the_stock_firmware_is_the_one_the_build_names(self) -> None:
        other = builds.BuildDescription(
            "other", "x", ("patches/a.json",), stock="NOT-KNOWN.BIN"
        )
        with self.assertRaisesRegex(Exception, "'stock' must be one of"):
            pipeline.firmware(self.repo.paths, other)

    def test_the_files_for_a_zip_and_eject(self) -> None:
        outcome = pipeline.install(self.repo.paths, None, ["ART1=velvia"])
        self.assertEqual(sorted(outcome.file_data()), [FIRMWARE, "EPM2LOOK.BIN"])
        self.assertEqual(outcome.steps[0].id, "copy")
        self.assertEqual(self.card_files(), [])
        with mock.patch("epm2mod.cardio.eject") as eject:
            outcome = self.install(eject=True)
        eject.assert_called_once_with(self.card.absolute())
        self.assertTrue(outcome.ejected)
        self.assertEqual(outcome.steps[0].text, "Take the card out of the computer.")

    def test_a_failed_eject_is_a_warning(self) -> None:
        busy = CardError(f"{self.card}: cannot be ejected: busy")
        with mock.patch("epm2mod.cardio.eject", side_effect=busy):
            outcome = self.install(eject=True)
        self.assertEqual(self.card_files(), [FIRMWARE])
        self.assertFalse(outcome.ejected)
        self.assertEqual(outcome.eject_error, str(busy))
        self.assertEqual(outcome.steps[0].id, "eject")
        self.assertTrue(outcome.steps[0].text.startswith("Eject the card"))
        with mock.patch("epm2mod.cardio.eject", side_effect=busy):
            status, out, err = self.run_cli(
                "install", "--card", str(self.card), "--eject", "--json"
            )
        self.assertEqual(status, 0, err)
        document = json.loads(out)
        self.assertEqual(
            (document["ejected"], document["eject_error"]), (False, str(busy))
        )
        self.assertIn("warning: ", err)


class FilmsAndRestoreTests(CardCase):
    def test_films_set_writes_only_the_film_file(self) -> None:
        outcome = pipeline.set_films(self.repo.paths, ["ART6=double-x"], card=self.card)
        self.assertEqual(self.card_files(), ["EPM2LOOK.BIN"])
        self.assertEqual(
            [step.id for step in outcome.steps][-2:], ["load-films", "check-art"]
        )
        self.assertEqual(
            outcome.steps[-1].text, "Check: MENU → ART shows Double-X in ART 6."
        )
        out = self.folder / "films.bin"
        pipeline.set_films(self.repo.paths, ["ART1=velvia"], out=out)
        self.assertEqual(len(lookfile.unpack(out.read_bytes())), 1)

    def test_restore_writes_the_stock_firmware_of_the_pinned_build(self) -> None:
        steps: list[int] = []
        outcome = pipeline.restore(self.repo.paths, self.card, step=steps.append)
        self.assertEqual((self.card / FIRMWARE).read_bytes(), TINY)
        self.assertEqual(steps, [1, 2])
        self.assertIn("Firmware reads Body : 1.6.", outcome.steps[-2].text)
        self.assertNotIn("load-films", [step.id for step in outcome.steps])
        out = self.folder / "o"
        out.mkdir()
        pipeline.restore(self.repo.paths, out=out / "E1019999.BIN")
        self.assertEqual((out / "E1019999.BIN").read_bytes(), TINY)


class InspectTests(CardCase):
    def test_a_firmware_file_and_a_film_file(self) -> None:
        stock_file = self.repo.paths.stock_file(TINY_STOCK)
        report = pipeline.inspect_file(self.repo.paths, stock_file).files[0]
        self.assertEqual(
            (report.kind, report.model, report.build, report.version),
            ("firmware", "E-PM2", "Olympus original", "1.6"),
        )
        built = self.repo.write("built.BIN", self.repo.films_image)
        report = pipeline.inspect_file(self.repo.paths, built).files[0]
        self.assertEqual(report.build, "films")
        films = self.repo.write(
            "f.BIN", records.pack_choices(self.repo.paths, ["ART2=velvia"])[0]
        )
        report = pipeline.inspect_file(self.repo.paths, films).files[0]
        self.assertEqual(report.films[0]["art"], 2)
        with self.assertRaises(NotFoundError):
            pipeline.inspect_file(self.repo.paths, self.repo.write("x", b"nothing"))
        with self.assertRaises(NotFoundError):
            pipeline.inspect_file(self.repo.paths, self.folder / "missing")

    def test_a_card_says_what_will_not_work(self) -> None:
        with self.assertRaises(NotFoundError):
            pipeline.inspect_card(self.repo.paths, self.card)
        pipeline.restore(self.repo.paths, self.card)
        (self.card / "EPM2LOOK.BIN").write_bytes(b"EPLK damaged")
        (self.card / "DCOLYMP" / "._E1019999.BIN").write_bytes(b"x")
        found = pipeline.inspect_card(self.repo.paths, self.card)
        text = "\n".join(found.problems)
        self.assertIn("damaged", text)
        self.assertIn("holds other files", text)
        self.assertIn("does not load the film file", text)


class CommandTests(CardCase):
    def test_install_on_the_command_line(self) -> None:
        status, out, err = self.run_cli("install", "--card", str(self.card))
        self.assertEqual(status, 0, err)
        self.assertIn(f"wrote {self.card / FIRMWARE}", out)
        self.assertIn("On the camera:", err)  # the steps go to stderr
        self.assertNotIn("On the camera", out)
        self.assertNotIn("1/5", out)  # progress too

    def test_install_with_no_film_writes_no_film_file(self) -> None:
        document = self.json_of("install", "--card", str(self.card))
        self.assertEqual(self.card_files(), [FIRMWARE])
        self.assertEqual([f["role"] for f in document["files"]], ["firmware"])
        self.assertEqual(document["films"], [])
        ids = [step["id"] for step in document["camera_steps"]]
        self.assertNotIn("load-films", ids)
        document = self.json_of(
            "install", "--card", str(self.card), "--film", "ART1=velvia"
        )
        self.assertEqual(self.card_files(), [FIRMWARE, "EPM2LOOK.BIN"])
        self.assertEqual(document["films"], [{"art": 1, "name": "Velvia"}])

    def test_films_set_with_no_film_is_a_usage_error(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            self.run_cli("films", "set", "--card", str(self.card))
        self.assertEqual(raised.exception.code, 2)
        status, out, err = self.run_cli(
            "films", "set", "--card", str(self.card), "--json"
        )
        self.assertEqual(status, 2)
        document = json.loads(out)
        self.assertEqual(document["command"], "films set")
        self.assertEqual(document["error"]["code"], "usage")
        self.assertIn("--film", document["error"]["message"])
        self.assertEqual(self.card_files(), [])

    def test_unchanged_files_are_not_rewritten(self) -> None:
        self.assertEqual(self.run_cli("install", "--card", str(self.card))[0], 0)
        firmware = self.card / FIRMWARE
        before = firmware.stat().st_mtime_ns
        with mock.patch("epm2mod.cardio.write_file") as write:
            status, out, err = self.run_cli("install", "--card", str(self.card))
            self.assertEqual(status, 0, err)
            write.assert_not_called()
        self.assertIn(f"unchanged {firmware}", out)
        self.assertEqual(firmware.stat().st_mtime_ns, before)
        document = self.json_of("install", "--card", str(self.card), "--dry-run")
        self.assertEqual([f["unchanged"] for f in document["files"]], [True])

    def test_o_is_refused_on_a_listed_card(self) -> None:
        for argv in (
            ("restore", "-o", str(self.card / "E1019999.BIN")),
            ("films", "set", "--film", "ART1=velvia", "-o", str(self.card / "F.BIN")),
            ("make", "films", "-o", str(self.card / "DCOLYMP" / "E1019999.BIN")),
        ):
            with self.subTest(argv=argv):
                status, out, err = self.run_cli(*argv)
                self.assertEqual(status, 2, err)
                self.assertIn(f"use --card {self.card}", err)
        self.assertEqual(self.card_files(), [])

    def test_the_exit_statuses(self) -> None:
        self.assertEqual(sorted(cli.EXIT_STATUSES), [0, 1, 2, 3, 4, 5, 6, 7, 70, 130])
        other_model = bytearray(self.repo.films_image)
        other_model[2:4] = b"\x10\x00"
        card = str(self.card)
        cases: list[tuple[tuple[str, ...], int, Any]] = [
            (("cards",), 0, None),
            (
                (
                    "install",
                    "--card",
                    card,
                    "--film",
                    "ART2=velvia",
                    "--film",
                    "ART2=c200",
                ),
                2,
                None,
            ),
            (("inspect",), 2, None),
            (("install", "--card", card, "--build", "nothing"), 3, None),
            (("inspect", str(self.folder / "missing")), 3, None),
            (("install", "--card", card, "--build", "new"), 4, None),
            (
                ("install", "--card", card),
                5,
                mock.patch(
                    "epm2mod.pipeline.firmware", return_value=(bytes(other_model), "x")
                ),
            ),
            (("install", "--card", str(self.folder)), 6, None),
            (
                ("install", "--card", card),
                70,
                mock.patch("epm2mod.cli.install", side_effect=RuntimeError("bug")),
            ),
            (
                ("install", "--card", card),
                130,
                mock.patch("epm2mod.cli.install", side_effect=KeyboardInterrupt),
            ),
        ]
        for argv, wanted, patch in cases:
            with self.subTest(argv=argv, wanted=wanted):
                with patch or contextlib.nullcontext():
                    status, out, err = self.run_cli(*argv)
                self.assertEqual(status, wanted, err)
                if wanted:
                    self.assertTrue(
                        err.startswith("epm2mod: ") or "Traceback" in err, err
                    )
        with mock.patch.dict(os.environ, {cards.TEST_CARDS_ENV: ""}):
            self.assertEqual(self.run_cli("cards")[0], 0)  # an empty list
        pipeline.restore(self.repo.paths, self.card)
        (self.card / "EPM2LOOK.BIN").write_bytes(b"EPLK damaged")
        self.assertEqual(self.run_cli("inspect", "--card", str(self.card))[0], 1)

    def test_json_error_documents(self) -> None:
        card = str(self.card)
        cases: list[tuple[tuple[str, ...], int, str, str | None, str | None]] = [
            (
                ("install", "--card", card, "--build", "new"),
                4,
                "refused",
                "--allow-untested",
                "install",
            ),
            (
                ("install", "--card", card, "--build", "nothing"),
                3,
                "not_found",
                None,
                "install",
            ),
            (("install", "--card", str(self.folder)), 6, "card", None, "install"),
            (("install",), 2, "usage", None, "install"),
            (("nope",), 2, "usage", None, None),
            (("restore", "--card", card, "--bad-flag"), 2, "usage", None, "restore"),
        ]
        for argv, status_wanted, code, override, command in cases:
            with self.subTest(argv=argv):
                status, out, err = self.run_cli(*argv, "--json")
                self.assertEqual(status, status_wanted, err)
                document = json.loads(out)
                self.assertEqual(
                    {
                        key: document[key]
                        for key in ("schema", "command", "version", "ok")
                    },
                    {
                        "schema": cli.SCHEMA,
                        "command": command,
                        "version": cli.__version__,
                        "ok": False,
                    },
                )
                self.assertEqual(
                    document["error"],
                    {
                        "code": code,
                        "exit": status_wanted,
                        "message": document["error"]["message"],
                        "override": override,
                    },
                )
                self.assertIn(document["error"]["message"], err)
        pipeline.restore(self.repo.paths, self.card)
        (self.card / "EPM2LOOK.BIN").write_bytes(b"EPLK damaged")
        status, out, err = self.run_cli("inspect", "--card", card, "--json")
        document = json.loads(out)
        self.assertEqual(
            (status, document["ok"], document["error"]["exit"]), (1, False, 1)
        )
        self.assertEqual(document["error"]["code"], "will_not_work")
        self.assertTrue(document["problems"])

    def test_dry_run_on_every_writing_command(self) -> None:
        out = self.folder / "out"
        out.mkdir()
        for argv in (
            ("install", "--card", str(self.card)),
            ("films", "set", "--card", str(self.card), "--film", "ART1=velvia"),
            ("films", "set", "-o", str(out / "F.BIN"), "--film", "ART1=velvia"),
            ("restore", "--card", str(self.card)),
            ("restore", "-o", str(out / "E.BIN")),
            ("make", "films"),
            ("make", "films", "-o", str(out / "M.BIN")),
            ("pin", "new", "--date", "2026-11-10", "--sha256", self.repo.sha256),
            (
                "apply",
                str(self.repo.paths.resolve("patches/a.json")),
                "--from",
                str(self.repo.paths.stock_file(TINY_STOCK)),
                "-o",
                str(out / "A.BIN"),
            ),
            ("fetch-stock",),
        ):
            with self.subTest(argv=argv):
                status, _, err = self.run_cli(*argv, "--dry-run")
                self.assertEqual(status, 0, err)
        self.assertEqual(self.card_files(), [])
        self.assertEqual(list(out.iterdir()), [])
        self.assertEqual(self.repo.outputs(), [])
        self.assertEqual(self.repo.paths.pinned_build().name, "films")

    def test_the_launcher_name_is_in_usage_lines_examples_and_hints(self) -> None:
        launcher = "./start.sh"
        out = io.StringIO()
        with (
            mock.patch.dict(
                os.environ,
                {cli.PROG_ENV: launcher, ROOT_ENV: str(self.repo.paths.root)},
            ),
            contextlib.redirect_stdout(out),
            self.assertRaises(SystemExit),
        ):
            cli.main(["install", "--help"])
        text = out.getvalue()
        self.assertTrue(text.startswith(f"usage: {launcher} install "), text)
        self.assertIn(f"  {launcher} install --card /path/to/card", text)
        self.assertNotIn("epm2mod install", text)
        err = io.StringIO()
        with (
            mock.patch.dict(os.environ, {cli.PROG_ENV: launcher}),
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit),
        ):
            cli.main(["install"])
        self.assertIn(f"usage: {launcher} install ", err.getvalue())
        plain = self.folder / "plain"
        (plain / "DCIM").mkdir(parents=True)
        status, _, err_text = self.run_cli(
            "install", "--card", str(plain), prog=launcher
        )
        self.assertEqual(status, 6)
        self.assertTrue(err_text.startswith(f"{launcher}: "), err_text)
        self.assertIn(f"'{launcher} cards' lists them", err_text)
        status, _, err_text = self.run_cli(
            "install", "--card", str(self.card), prog=launcher
        )
        self.assertEqual(status, 0, err_text)


class CameraStepsTests(unittest.TestCase):
    def test_the_steps(self) -> None:
        steps = camera_steps.flash_steps(
            films=True, firmware="Body : 1.6", art_shows="C200 in ART 2."
        )
        self.assertEqual(
            [step.id for step in steps],
            [
                "eject",
                "insert",
                "flash",
                "wait",
                "restart",
                "check-firmware",
                "load-films",
                "check-art",
            ],
        )
        copied = camera_steps.flash_steps(
            films=False,
            firmware="Body : 1.6",
            art_shows="x",
            copy="Copy X.",
            ejected=True,
        )
        self.assertEqual([step.id for step in copied][:2], ["copy", "eject"])
        self.assertEqual(camera_steps.film_steps(art_shows="x")[-2].id, "load-films")

    def test_the_check_of_the_firmware_comes_from_the_build(self) -> None:
        self.assertEqual(
            camera_steps.firmware_reads("2026.11.19"), "Body : 1.6  EPM2Mod 2026.11.19"
        )
        self.assertEqual(camera_steps.firmware_reads(None), "Body : 1.6")
        steps = camera_steps.flash_steps(
            films=False, firmware=camera_steps.firmware_reads(None), art_shows="x"
        )
        check = next(step.text for step in steps if step.id == "check-firmware")
        self.assertEqual(
            check, "To check: MENU → SETUP → wrench tab → Firmware reads Body : 1.6."
        )
        # the pinned build has a label: the README shows it
        label = RepoPaths(ROOT).pinned_build().label
        self.assertIsNotNone(label)
        self.assertIn(
            f"Firmware reads Body : 1.6  EPM2Mod {label}.",
            readme.steps_block(RepoPaths(ROOT)),
        )

    def test_the_art_check_names_the_first_film_by_slot(self) -> None:
        films = records.load(RepoPaths(ROOT))
        looks = records.looks_of_choices(films, ["ART9=velvia", "ART3=c200"])
        self.assertEqual(catalogue.art_check(looks), "C200 in ART 3.")
        self.assertEqual(catalogue.art_check([]), "the art filters, such as Pop Art.")


def flatten(value: Any, prefix: str = "") -> Iterator[str]:
    """Yield the key paths of a JSON value, as ``cli.COMMANDS`` writes them (``files[].path``, ``build.name``)."""
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            yield path
            if path not in OPAQUE:
                yield from flatten(item, path)
    elif isinstance(value, list):
        for item in value:
            yield from flatten(item, f"{prefix}[]")


#: Keys whose values have keys that the event dictionary decides (``log``).
OPAQUE = {"events"}


class JsonTests(CardCase):
    """The keys of real documents are the keys that ``cli.COMMANDS`` and ``docs/cli.md`` list."""

    def documented(self, command: str) -> set[str]:
        return {*cli.COMMON_JSON, *cli.COMMANDS[command].json}

    def test_docs_cli_md_lists_every_key(self) -> None:
        text = (ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
        for command in cli.COMMANDS:
            for key in self.documented(command):
                self.assertIn(f"- `{key}`: ", text, f"{command}: {key}")

    def test_the_keys_of_real_documents(self) -> None:
        card = str(self.card)
        films_file = self.card / "EPM2LOOK.BIN"
        runs: list[tuple[str, tuple[str, ...]]] = [
            ("cards", ("cards",)),
            ("install", ("install", "--card", card, "--film", "ART1=velvia")),
            ("films", ("films",)),
            ("films set", ("films", "set", "--card", card, "--film", "ART2=c200")),
            ("restore", ("restore", "--card", card, "--dry-run")),
            ("inspect", ("inspect", str(films_file))),
            ("inspect", ("inspect", "--card", card)),
            ("make", ("make", "films")),
            ("builds", ("builds",)),
            ("fetch-stock", ("fetch-stock", "--dry-run")),
        ]
        found: dict[str, set[str]] = {}
        for command, argv in runs:
            with self.subTest(argv=argv):
                document = self.json_of(*argv)
                keys = set(flatten(document))
                self.assertLessEqual(keys, self.documented(command))
                found.setdefault(command, set()).update(keys)
        status, out, _ = self.run_cli(
            "install", "--card", card, "--build", "new", "--json"
        )
        found["install"].update(flatten(json.loads(out)))
        for command, keys in found.items():
            with self.subTest(command=command):
                errors = {key for key in cli.COMMON_JSON if key.startswith("error")}
                wanted = self.documented(command) - (
                    set() if command == "install" else errors
                )
                self.assertEqual(keys, wanted)


class SourceTests(unittest.TestCase):
    def test_the_command_line_holds_no_repository_folder_or_file(self) -> None:
        text = (ROOT / "src" / "epm2mod" / "cli.py").read_text(encoding="utf-8")
        found = re.findall(
            r"\b(?:builds|patches|looks|logs|build|firmware|docs|tools|release)/"
            r"|pinned-build\.json|[\"'][^\"'\n(]*\b\w[\w-]*\.json\b",
            text,
        )
        self.assertEqual(found, [])


class NoCheckoutTests(unittest.TestCase):
    """The commands for camera owners in a folder laid out as the release zip: no checkout."""

    def setUp(self) -> None:
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.top = Path(folder) / "EPM2Mod-2026.11.19"
        for name, data in release.data_files(RepoPaths(ROOT), "2026.11.19"):
            target = self.top / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.card = Path(folder) / "card"
        (self.card / "DCIM").mkdir(parents=True)
        env = mock.patch.dict(
            os.environ, {ROOT_ENV: str(self.top), cards.TEST_CARDS_ENV: str(self.card)}
        )
        env.start()
        self.addCleanup(env.stop)

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cli.main(list(argv))
        return status, out.getvalue(), err.getvalue()

    def test_the_locator_is_the_release_folder(self) -> None:
        locator = catalogue.locate()
        self.assertEqual(locator.kind, "release")
        self.assertEqual(locator.pinned_build(), RepoPaths(ROOT).pinned_build())
        with self.assertRaises(RepositoryError):
            locator.checkout()

    def test_every_command_for_camera_owners_runs_without_a_checkout(self) -> None:
        films_file = self.card / "EPM2LOOK.BIN"
        cases = [
            ("cards", "--json"),
            ("films", "--json"),
            ("install", "--card", str(self.card), "--dry-run", "--json"),
            (
                "install",
                "--card",
                str(self.card),
                "--film",
                "ART2=velvia",
                "--dry-run",
                "--json",
            ),
            (
                "films",
                "set",
                "--card",
                str(self.card),
                "--film",
                "ART2=velvia",
                "--json",
            ),
            ("restore", "--card", str(self.card), "--dry-run", "--json"),
            (
                "restore",
                "-o",
                str(self.card.parent / "E1019999.BIN"),
                "--dry-run",
                "--json",
            ),
            ("inspect", str(films_file), "--json"),
            ("inspect", "--card", str(self.card), "--json"),
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                status, out, err = self.run_cli(*argv)
                self.assertEqual(status, 0, err)
                self.assertEqual(json.loads(out)["schema"], cli.SCHEMA)
        self.assertFalse((self.top / "build").exists())
        with mock.patch("epm2mod.serve.serve") as serve:
            self.assertEqual(self.run_cli("serve", "--no-browser")[0], 0)
        self.assertEqual(serve.call_args.args[0].kind, "release")

    def test_developer_commands_need_a_checkout(self) -> None:
        for argv in (
            ("make", "x"),
            ("builds",),
            ("generate",),
            ("films", "pack", "x.json", "-o", "y"),
            ("fetch-stock",),
            ("log", "x"),
            ("package", "--release-version", "2026.11.19"),
            ("release",),
            ("pin", "x", "--date", "2026-11-10", "--sha256", "0" * 64),
            ("apply", "x.json", "--from", "x", "-o", "y"),
        ):
            with self.subTest(argv=argv):
                status, _, err = self.run_cli(*argv)
                self.assertEqual(status, 6, err)
                self.assertIn("needs a checkout", err)

    def test_help_lists_the_commands_for_camera_owners_only(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            cli.main(["--help"])
        text = out.getvalue()
        self.assertIn(cli.OWNERS, text)
        self.assertNotIn(cli.DEVELOPERS, text)
        self.assertNotIn(cli.RELEASES, text)
        self.assertNotIn("  make ", text)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            cli.main(["films", "--help"])
        self.assertIn("set ", out.getvalue())
        self.assertNotIn("pack", out.getvalue())


if __name__ == "__main__":
    unittest.main()

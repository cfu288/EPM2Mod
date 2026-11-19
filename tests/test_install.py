"""Tests of the commands for camera owners: ``install``, ``films``, ``films set``, ``restore``, ``inspect``, ``cards``.

    uv run python -m unittest discover -s tests

They run on the tiny firmware of ``test_package`` and need nothing but the repository. ``NoCheckoutTests`` lays
out a folder as the release zip does (``release.data_files``) and runs every command for camera owners there, to
show that they need no checkout.
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
    release,
    spec,
)
from epm2mod.errors import (  # noqa: E402
    BuildCheckError,
    CardError,
    CheckError,
    NotFoundError,
    RepositoryError,
    UsageError,
)
from epm2mod.hashing import sha256_bytes  # noqa: E402
from epm2mod.looks import lookfile, records  # noqa: E402
from epm2mod.paths import ROOT_ENV, RepoPaths  # noqa: E402

FIRMWARE = "DCOLYMP/E1019999.BIN"
FILMS_OP = {**BYTE_OP, "offset": "0x20", "expect": "2021", "new": "ccdd"}


class FilmRepo(TinyRepo):
    """The tiny repository with the film records and a build that loads the films from the card (``films``)."""

    def __init__(self, folder: Path) -> None:
        super().__init__(folder)
        self.write(
            "looks/film-records.json",
            (ROOT / "looks" / "film-records.json").read_bytes(),
        )
        self.write_json(pipeline.FILM_LOADER, spec_json("loader", [FILMS_OP]))
        specs = ("patches/a.json", pipeline.FILM_LOADER)
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
        """Run ``pipeline.install`` on the tiny repository and the card."""
        kw.setdefault("stock", TINY_STOCK)
        return pipeline.install(self.repo.paths, self.card, **kw)

    def run_cli(self, *argv: str, root: Path | None = None) -> tuple[int, str, str]:
        """Run the command line with the tiny stock firmware; return status, stdout and stderr."""
        out, err = io.StringIO(), io.StringIO()
        env = {ROOT_ENV: str(root or self.repo.paths.root)}
        with (
            mock.patch.dict(os.environ, env),
            mock.patch.object(cli, "EPM2_V16", TINY_STOCK),
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
        self.assertEqual(CardError("x").exit_status, 5)

    def test_a_card_without_room_is_refused(self) -> None:
        usage = shutil.disk_usage(self.card)._replace(free=10)
        with mock.patch("epm2mod.cardio.shutil.disk_usage", return_value=usage):
            with self.assertRaisesRegex(CardError, "the card is full"):
                cardio.plan(self.card, {FIRMWARE: cardio.Content.of(TINY)})

    def test_firmware_for_another_model_is_refused(self) -> None:
        epl5 = bytearray(TINY)
        epl5[2:4] = b"\x10\x00"
        other = make_container([bytes(48)])
        other_model = bytearray(other)
        other_model[2:4] = b"\x10\x00"
        cardio.check_model(TINY)
        with self.assertRaisesRegex(CheckError, "not for the E-PM2"):
            cardio.check_model(bytes(other_model))
        with self.assertRaisesRegex(CheckError, "not a firmware file"):
            cardio.check_model(b"not firmware")

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
        self.assertEqual(cardio.output_path(str(folder), "X.BIN"), folder / "X.BIN")
        self.assertEqual(
            cardio.output_path(str(self.folder / "new") + "/", "X.BIN"),
            self.folder / "new" / "X.BIN",
        )
        self.assertEqual(
            cardio.output_path(str(folder / "y.bin"), "X.BIN"), folder / "y.bin"
        )
        with self.assertRaises(Exception):
            cardio.output_path("", "X.BIN")

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
    def test_the_pinned_build_and_the_default_films(self) -> None:
        lines: list[str] = []
        steps: list[int] = []
        outcome = self.install(log=lines.append, step=steps.append)
        self.assertEqual(self.card_files(), [FIRMWARE, "EPM2LOOK.BIN"])
        self.assertEqual((self.card / FIRMWARE).read_bytes(), self.repo.films_image)
        default = records.pack_choices(
            self.repo.paths, catalogue.default_choices(self.repo.paths)
        )[0]
        self.assertEqual((self.card / "EPM2LOOK.BIN").read_bytes(), default)
        self.assertEqual(steps, [1, 2, 3, 4, 5])
        self.assertEqual([p.role for p in outcome.files], ["firmware", "films"])
        self.assertEqual(outcome.files[0].content.sha256, self.repo.films_build.sha256)
        ids = [step.id for step in outcome.steps]
        self.assertEqual(ids[0], "eject")
        self.assertIn("load-films", ids)
        self.assertEqual(self.repo.outputs(), [])  # install writes no output folder

    def test_only_the_named_slots_get_a_film(self) -> None:
        outcome = self.install(choices=["ART2=c200"])
        looks = lookfile.unpack((self.card / "EPM2LOOK.BIN").read_bytes())
        self.assertEqual([(look.slot, look.name) for look in looks], [(1, "C200")])
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

    def test_an_untested_build_needs_untested(self) -> None:
        self.repo.free_space_tool(0)
        with self.assertRaises(BuildCheckError) as raised:
            self.install(build="new")
        self.assertEqual(raised.exception.exit_status, 4)
        self.assertIn("--untested", str(raised.exception))
        lines: list[str] = []
        self.install(build="new", untested=True, choices=[], log=lines.append)
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
                pipeline.install(self.repo.paths, plain, stock=TINY_STOCK)
            obtain.assert_not_called()

    def test_install_downloads_the_stock_firmware_if_it_is_absent(self) -> None:
        self.repo.paths.stock_file(TINY_STOCK).unlink()
        with answers(catalog_answer(), TINY):
            self.install()
        self.assertEqual((self.card / FIRMWARE).read_bytes(), self.repo.films_image)

    def test_the_files_for_a_zip_and_eject(self) -> None:
        outcome = pipeline.install(self.repo.paths, None, stock=TINY_STOCK)
        self.assertEqual(sorted(outcome.file_data()), [FIRMWARE, "EPM2LOOK.BIN"])
        self.assertEqual(outcome.steps[0].id, "copy")
        self.assertEqual(self.card_files(), [])
        with mock.patch("epm2mod.cardio.eject") as eject:
            outcome = self.install(eject=True)
        eject.assert_called_once_with(self.card.absolute())
        self.assertTrue(outcome.ejected)
        self.assertEqual(outcome.steps[0].text, "Take the card out of the computer.")


class FilmsAndRestoreTests(CardCase):
    def test_films_set_writes_only_the_film_file(self) -> None:
        outcome = pipeline.set_films(self.repo.paths, ["ART6=double-x"], card=self.card)
        self.assertEqual(self.card_files(), ["EPM2LOOK.BIN"])
        self.assertEqual(
            [step.id for step in outcome.steps][-2:], ["load-films", "check-art"]
        )
        out = self.folder / "films.bin"
        pipeline.set_films(self.repo.paths, None, out=out)
        self.assertEqual(len(lookfile.unpack(out.read_bytes())), 12)

    def test_restore_writes_the_stock_firmware(self) -> None:
        steps: list[int] = []
        outcome = pipeline.restore(
            self.repo.paths, self.card, stock=TINY_STOCK, step=steps.append
        )
        self.assertEqual((self.card / FIRMWARE).read_bytes(), TINY)
        self.assertEqual(steps, [1, 2])
        self.assertIn("Body : 1.6.", outcome.steps[-2].text)
        self.assertNotIn("load-films", [step.id for step in outcome.steps])
        out = self.folder / "o"
        out.mkdir()
        pipeline.restore(self.repo.paths, out=out / "E1019999.BIN", stock=TINY_STOCK)
        self.assertEqual((out / "E1019999.BIN").read_bytes(), TINY)


class InspectTests(CardCase):
    def test_a_firmware_file_and_a_film_file(self) -> None:
        stock_file = self.repo.paths.stock_file(TINY_STOCK)
        report = pipeline.inspect_file(self.repo.paths, stock_file, TINY_STOCK).files[0]
        self.assertEqual(
            (report.kind, report.model, report.build, report.version),
            ("firmware", "E-PM2", "Olympus original", "1.6"),
        )
        built = self.repo.write("built.BIN", self.repo.films_image)
        report = pipeline.inspect_file(self.repo.paths, built, TINY_STOCK).files[0]
        self.assertEqual(report.build, "films")
        films = self.repo.write(
            "f.BIN", records.pack_choices(self.repo.paths, ["ART2=velvia"])[0]
        )
        report = pipeline.inspect_file(self.repo.paths, films, TINY_STOCK).files[0]
        self.assertEqual(report.films[0]["art"], 2)
        with self.assertRaises(NotFoundError):
            pipeline.inspect_file(self.repo.paths, self.repo.write("x", b"nothing"))
        with self.assertRaises(NotFoundError):
            pipeline.inspect_file(self.repo.paths, self.folder / "missing")

    def test_a_card_says_what_will_not_work(self) -> None:
        with self.assertRaises(NotFoundError):
            pipeline.inspect_card(self.repo.paths, self.card, TINY_STOCK)
        pipeline.restore(self.repo.paths, self.card, stock=TINY_STOCK)
        (self.card / "EPM2LOOK.BIN").write_bytes(b"EPLK damaged")
        (self.card / "DCOLYMP" / "._E1019999.BIN").write_bytes(b"x")
        found = pipeline.inspect_card(self.repo.paths, self.card, TINY_STOCK)
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

    def test_json_documents(self) -> None:
        document = self.json_of("install", "--card", str(self.card), "--dry-run")
        self.assertEqual(document["command"], "install")
        self.assertTrue(document["dry_run"])
        self.assertEqual(
            set(document), {"schema", "command", *cli.COMMANDS["install"].json}
        )
        self.assertEqual(self.card_files(), [])
        document = self.json_of("install", "--card", str(self.card), "ART1=velvia")
        self.assertEqual([f["role"] for f in document["files"]], ["firmware", "films"])
        self.assertEqual(document["films"], [{"art": 1, "name": "Velvia"}])
        self.assertEqual(document["camera_steps"][0]["id"], "eject")
        films = self.json_of("films")
        self.assertIn("portra-400", [film["id"] for film in films["films"]])
        document = self.json_of("films", "set", "--card", str(self.card), "--dry-run")
        self.assertEqual(document["command"], "films set")
        self.assertEqual(
            set(document), {"schema", "command", *cli.COMMANDS["films set"].json}
        )
        document = self.json_of("restore", "--card", str(self.card), "--dry-run")
        self.assertEqual(document["files"][0]["sha256"], TINY_STOCK.sha256)
        document = self.json_of("inspect", "--card", str(self.card))
        self.assertEqual(document["files"][0]["build"], "films")
        self.assertEqual(document["problems"], [])
        cards_document = self.json_of("cards")
        self.assertEqual(cards_document["cards"][0]["path"], str(self.card))
        self.assertEqual(
            set(self.json_of("builds")), {"schema", "command", "pinned", "builds"}
        )
        make = self.json_of("make", "--dry-run")
        self.assertEqual(make["sha256"], self.repo.films_build.sha256)

    def test_exit_statuses(self) -> None:
        cases: list[tuple[tuple[str, ...], int]] = [
            (("install", "--card", str(self.card), "ART2=velvia", "ART2=c200"), 2),
            (("install", "--card", str(self.card), "--build", "nothing"), 3),
            (("inspect", str(self.folder / "missing")), 3),
            (("install", "--card", str(self.card), "--build", "new"), 4),
            (("install", "--card", str(self.folder)), 5),
            (("inspect", "--card", str(self.card), str(self.card)), 2),
        ]
        for argv, wanted in cases:
            with self.subTest(argv=argv):
                status, out, err = self.run_cli(*argv)
                self.assertEqual(status, wanted, err)
                self.assertTrue(err.startswith("epm2mod: "), err)
        with mock.patch.dict(os.environ, {cards.TEST_CARDS_ENV: ""}):
            self.assertEqual(self.run_cli("cards")[0], 3)
        pipeline.restore(self.repo.paths, self.card, stock=TINY_STOCK)
        (self.card / "EPM2LOOK.BIN").write_bytes(b"EPLK damaged")
        self.assertEqual(self.run_cli("inspect", "--card", str(self.card))[0], 4)

    def test_dry_run_on_every_writing_command(self) -> None:
        out = self.folder / "out"
        out.mkdir()
        for argv in (
            ("install", "--card", str(self.card)),
            ("films", "set", "--card", str(self.card)),
            ("films", "set", "-o", str(out)),
            ("restore", "--card", str(self.card)),
            ("restore", "-o", str(out)),
            ("make",),
            ("make", "-o", str(out)),
            ("pin", "new", "--date", "2026-11-10", "--sha256", self.repo.sha256),
            ("apply", str(self.repo.paths.resolve("patches/a.json")), "-o", str(out)),
            ("fetch-stock",),
        ):
            with self.subTest(argv=argv):
                status, _, err = self.run_cli(*argv, "--dry-run")
                self.assertEqual(status, 0, err)
        self.assertEqual(self.card_files(), [])
        self.assertEqual(list(out.iterdir()), [])
        self.assertEqual(self.repo.outputs(), [])
        self.assertEqual(self.repo.paths.pinned_build().name, "films")


class CameraStepsTests(unittest.TestCase):
    def test_the_steps(self) -> None:
        steps = camera_steps.flash_steps(films=True)
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
        copied = camera_steps.flash_steps(films=False, copy="Copy X.", ejected=True)
        self.assertEqual([step.id for step in copied][:2], ["copy", "eject"])
        self.assertEqual(camera_steps.film_steps()[-2].id, "load-films")


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
            ("install", "--card", str(self.card), "ART2=velvia", "--dry-run", "--json"),
            ("films", "set", "--card", str(self.card), "--json"),
            ("restore", "--card", str(self.card), "--dry-run", "--json"),
            ("restore", "-o", str(self.card.parent) + "/", "--dry-run", "--json"),
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
            ("make",),
            ("builds",),
            ("docs",),
            ("looks",),
            ("fetch-stock",),
            ("log", "x"),
            ("package",),
            ("release",),
            ("pin", "x", "--date", "2026-11-10", "--sha256", "0" * 64),
            ("apply", "x.json", "-o", "y"),
        ):
            with self.subTest(argv=argv):
                status, _, err = self.run_cli(*argv)
                self.assertEqual(status, 5, err)
                self.assertIn("needs a checkout", err)


if __name__ == "__main__":
    unittest.main()

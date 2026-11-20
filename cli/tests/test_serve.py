"""Tests of the local app, ``epm2mod.serve``.

    uv run python -m unittest discover -s cli/tests

``EndToEndTests`` needs the stock firmware file and is skipped without it.
"""

from __future__ import annotations

import http.client
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT, write_manifest  # noqa: E402

from epm2mod import camera_steps, cards, cli, pipeline, serve, stock  # noqa: E402
from epm2mod.builds import pinned_description  # noqa: E402
from epm2mod.cardio import Content, Planned  # noqa: E402
from epm2mod.cards import Card  # noqa: E402
from epm2mod.errors import BuildError  # noqa: E402
from epm2mod.hashing import sha256_bytes  # noqa: E402
from epm2mod.looks import lookfile, records  # noqa: E402
from epm2mod.paths import MANIFEST, RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()


class Running:
    """An app's server on a free port, in a thread."""

    def __init__(self, app: serve.App) -> None:
        self.app = app
        self.httpd = serve.server(app)
        self.port = self.httpd.server_port
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        headers: dict[str, str] | None = None,
        token: bool = True,
    ) -> tuple[int, bytes]:
        """Send a request; the token and Host are this server's unless changed."""
        sent = {"Host": f"127.0.0.1:{self.port}"}
        if token:
            sent["X-EPM2-Token"] = self.app.token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            sent["Content-Type"] = "application/json"
        sent.update(headers or {})
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            connection.request(method, path, body=data, headers=sent)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def wait(self) -> dict[str, Any]:
        """Return the state of the last job when it is done."""
        for _ in range(3000):
            status, data = self.request("GET", "/api/job")
            state = json.loads(data)
            if state and state["done"]:
                return dict(state)
            time.sleep(0.02)
        raise AssertionError("the job did not end")


def outcome(files: dict[str, bytes], films: bool) -> pipeline.Outcome:
    """Return the outcome of a job that made ``files``, by their path on the card."""
    roles = {"DCOLYMP/E1019999.BIN": "firmware", "EPM2LOOK.BIN": "films"}
    return pipeline.Outcome(
        tuple(
            Planned(Path(name), roles[name], Content.of(data), False)
            for name, data in files.items()
        ),
        steps=tuple(
            camera_steps.flash_steps(
                films=films, firmware="Body : 1.6", art_shows="Portra 400 in ART 1."
            )
        ),
    )


class FakeRunner:
    """A job runner that records its arguments and returns fixed files."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path | None]] = []
        self.release = threading.Event()
        self.release.set()

    def __call__(self, paths, choices, card, log, step):  # type: ignore[no-untyped-def]
        self.calls.append((choices, card))
        log("1/5 stock firmware: ok")
        step(1)
        self.release.wait(10)
        if choices == ["ART3=c200"]:
            raise BuildError("the card is full")
        files = {"DCOLYMP/E1019999.BIN": b"firmware", "EPM2LOOK.BIN": b"x"}
        return outcome(files, True)


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        static = Path(self.folder.name) / "app"
        static.mkdir()
        (static / "index.html").write_text("<!doctype html><title>app</title>")
        (static / "app.js").write_text("console.log(1)")
        (Path(self.folder.name) / "secret.txt").write_text("secret")
        self.card = Card(Path(self.folder.name) / "card", "CARD", 32, 16)
        self.runner = FakeRunner()
        app = serve.App(
            PATHS,
            static=static,
            list_cards=lambda: [self.card],
            job_runner=self.runner,
        )
        self.server = Running(app)
        self.out = io.StringIO()
        self.quiet = redirect_stdout(self.out)
        self.quiet.__enter__()

    def tearDown(self) -> None:
        self.quiet.__exit__(None, None, None)
        self.server.close()
        self.folder.cleanup()

    def test_the_page_and_its_files_are_served(self) -> None:
        status, data = self.server.request("GET", "/", token=False)
        self.assertEqual((status, data[:15]), (200, b"<!doctype html>"))
        status, data = self.server.request("GET", "/app.js", token=False)
        self.assertEqual((status, data), (200, b"console.log(1)"))
        for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/missing.js"):
            status, data = self.server.request("GET", path, token=False)
            self.assertEqual(status, 404, path)
            self.assertNotIn(b"secret", data)

    def test_the_api_needs_the_token_and_this_host(self) -> None:
        status, data = self.server.request("GET", "/api/build")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["name"], pinned_description(PATHS).name)
        for kwargs in (
            {"token": False},
            {"headers": {"X-EPM2-Token": "wrong"}},
            {"headers": {"Host": "evil.example:80"}},
            {"headers": {"Host": f"evil.example:{self.server.port}"}},
            {"headers": {"Origin": "https://evil.example"}},
        ):
            status, _ = self.server.request("GET", "/api/cards", **kwargs)  # type: ignore[arg-type]
            self.assertEqual(status, 403, kwargs)
        status, _ = self.server.request(
            "GET", "/", token=False, headers={"Host": "evil.example"}
        )
        self.assertEqual(status, 403)
        status, _ = self.server.request("OPTIONS", "/api/make")
        self.assertEqual(status, 403)
        status, _ = self.server.request(
            "GET", "/api/build", headers={"Host": f"localhost:{self.server.port}"}
        )
        self.assertEqual(status, 200)

    def test_a_job_makes_the_files_and_the_zip(self) -> None:
        status, data = self.server.request("GET", "/api/zip")
        self.assertEqual(status, 404)
        status, data = self.server.request(
            "POST",
            "/api/make",
            {"firmware": "epm2mod", "choices": ["ART2=velvia"], "card": None},
        )
        self.assertEqual(status, 202, data)
        state = self.server.wait()
        self.assertEqual(
            (state["error"], state["sha256"]), (None, sha256_bytes(b"firmware"))
        )
        self.assertEqual(
            [step["id"] for step in state["camera_steps"]][-2:],
            ["load-films", "check-art"],
        )
        self.assertEqual(state["lines"], ["1/5 stock firmware: ok"])
        self.assertEqual((state["step"], state["steps"]), (1, 5))
        self.assertEqual(self.runner.calls, [(["ART2=velvia"], None)])
        status, data = self.server.request("GET", "/api/zip")
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(
                archive.namelist(), ["DCOLYMP/E1019999.BIN", "EPM2LOOK.BIN"]
            )
            self.assertEqual(archive.read("DCOLYMP/E1019999.BIN"), b"firmware")

    def test_a_listed_card_is_used_and_an_unlisted_one_refused(self) -> None:
        status, data = self.server.request("GET", "/api/cards")
        self.assertEqual(json.loads(data)[0]["path"], str(self.card.path))
        for card in ("/", str(Path(self.folder.name)), 3):
            status, data = self.server.request(
                "POST",
                "/api/make",
                {"firmware": "epm2mod", "choices": [], "card": card},
            )
            self.assertEqual(status, 400, card)
        self.assertEqual(self.runner.calls, [])
        status, _ = self.server.request(
            "POST",
            "/api/make",
            {"firmware": "epm2mod", "choices": [], "card": str(self.card.path)},
        )
        self.assertEqual(status, 202)
        self.server.wait()
        self.assertEqual(self.runner.calls, [([], self.card.path)])

    def test_the_original_firmware_runs_the_restore(self) -> None:
        calls: list[Path | None] = []

        def restore(paths, card, log, step):  # type: ignore[no-untyped-def]
            calls.append(card)
            step(1)
            step(2)
            return outcome({"DCOLYMP/E1019999.BIN": b"stock"}, False)

        self.server.app.run_restore = restore
        status, _ = self.server.request(
            "POST", "/api/make", {"firmware": "original", "choices": [], "card": None}
        )
        self.assertEqual(status, 202)
        state = self.server.wait()
        self.assertEqual(
            (state["firmware"], state["step"], state["steps"], state["files"]),
            ("original", 2, 2, ["DCOLYMP/E1019999.BIN"]),
        )
        self.assertEqual((calls, self.runner.calls), ([None], []))

    def test_films_only_runs_the_film_file_job(self) -> None:
        calls: list[tuple[list[str], Path | None]] = []

        def films(paths, choices, card):  # type: ignore[no-untyped-def]
            calls.append((choices, card))
            return outcome({"EPM2LOOK.BIN": b"looks"}, True)

        self.server.app.run_films = films
        status, _ = self.server.request(
            "POST",
            "/api/make",
            {"firmware": "films", "choices": ["ART2=velvia"], "card": None},
        )
        self.assertEqual(status, 202)
        state = self.server.wait()
        self.assertEqual(
            (state["firmware"], state["step"], state["steps"], state["files"]),
            ("films", 1, 1, ["EPM2LOOK.BIN"]),
        )
        self.assertEqual((calls, self.runner.calls), ([(["ART2=velvia"], None)], []))

    def test_ping_keeps_it_alive_and_quit_stops_it(self) -> None:
        app = self.server.app
        app.last_seen = 0.0
        self.assertTrue(app.idle(1000.0, limit=10))
        status, _ = self.server.request("GET", "/api/ping")
        self.assertEqual(status, 200)
        self.assertFalse(app.idle(app.last_seen + 5, limit=10))
        status, _ = self.server.request("GET", "/api/ping", token=False)
        self.assertEqual(status, 403)
        self.assertFalse(app.quit.is_set())
        status, _ = self.server.request("POST", "/api/quit", token=False)
        self.assertEqual(status, 403)
        self.assertFalse(app.quit.is_set())
        status, _ = self.server.request("POST", "/api/quit")
        self.assertEqual(status, 200)
        self.assertTrue(app.quit.is_set())

    def test_a_running_job_is_never_idle(self) -> None:
        self.runner.release.clear()
        status, _ = self.server.request(
            "POST", "/api/make", {"firmware": "epm2mod", "choices": [], "card": None}
        )
        self.assertEqual(status, 202)
        self.assertFalse(self.server.app.idle(10**9, limit=10))
        self.runner.release.set()
        self.server.wait()

    def test_wrong_requests_are_refused(self) -> None:
        for body in (
            {"firmware": "epm2mod", "choices": ["ART2=velvia"]},
            {"firmware": "epm2mod", "choices": ["ART2=nofilm"], "card": None},
            {
                "firmware": "epm2mod",
                "choices": ["ART2=velvia", "ART2=c200"],
                "card": None,
            },
            {"firmware": "epm2mod", "choices": "ART2=velvia", "card": None},
            [],
        ):
            status, _ = self.server.request("POST", "/api/make", body)
            self.assertEqual(status, 400, body)
        status, _ = self.server.request(
            "POST", "/api/make", None, headers={"Content-Type": "text/plain"}
        )
        self.assertEqual(status, 415)
        self.assertEqual(self.runner.calls, [])

    def test_one_job_at_a_time_and_errors_are_reported(self) -> None:
        self.runner.release.clear()
        body = {"firmware": "epm2mod", "choices": ["ART3=c200"], "card": None}
        status, _ = self.server.request("POST", "/api/make", body)
        self.assertEqual(status, 202)
        status, data = self.server.request("POST", "/api/make", body)
        self.assertEqual(status, 400)
        self.assertIn(b"being made", data)
        self.runner.release.set()
        state = self.server.wait()
        self.assertEqual(state["error"], "the card is full")
        status, _ = self.server.request("GET", "/api/zip")
        self.assertEqual(status, 404)


class MessageTests(unittest.TestCase):
    def test_common_errors_say_what_to_do(self) -> None:
        from epm2mod.errors import CardError, DownloadError

        cases = [
            (
                BuildError(
                    "/Volumes/X/DCOLYMP/E1019999.BIN: cannot be written: Permission denied"
                ),
                "card is locked",
            ),
            (
                BuildError("E1019999.BIN: cannot be written: No space left on device"),
                "card is full",
            ),
            (
                CardError("/Volumes/X: has no DCIM folder. Format the card"),
                "Format the card in the camera",
            ),
            (DownloadError("download failed: timed out"), "internet connection"),
        ]
        for error, words in cases:
            self.assertIn(words, serve.plain_message(error))
            self.assertIn("Try again", serve.plain_message(error))
        self.assertEqual(
            serve.plain_message(BuildError("something else")), "something else"
        )


class CommandTests(unittest.TestCase):
    def test_serve_needs_the_built_page(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            (write_manifest(Path(folder), app="app") / "app").mkdir()
            with redirect_stderr(io.StringIO()) as err:
                argv = ["--project", folder, "serve", "--no-browser"]
                self.assertEqual(cli.main(argv), 6)
            self.assertIn("npm run build:app", err.getvalue())


def sandbox(folder: Path) -> RepoPaths:
    """Return a repository whose files are the checkout's, with its own ``build`` folder."""
    for entry in ROOT.iterdir():
        if entry.name not in ("build", MANIFEST):
            (folder / entry.name).symlink_to(entry)
    return RepoPaths(write_manifest(folder))


def stand_in_card(folder: Path) -> Path:
    """Return a folder made to look like a camera card: a DCIM folder in it."""
    (folder / "DCIM").mkdir(parents=True)
    return folder


@unittest.skipUnless(HAVE_STOCK, "needs the stock firmware")
class EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        top = Path(self.folder.name)
        (top / "repo").mkdir()
        self.paths = sandbox(top / "repo")
        self.app_card = stand_in_card(top / "app-card")
        self.cli_card = stand_in_card(top / "cli-card")
        listed = os.pathsep.join(str(card) for card in (self.app_card, self.cli_card))
        env = mock.patch.dict(
            os.environ,
            {cards.TEST_CARDS_ENV: listed},
        )
        env.start()
        self.addCleanup(env.stop)

    def cli(self, *argv: str) -> int:
        """Run the command line in the sandbox project."""
        return cli.main(["--project", str(self.paths.root), *argv])

    def files(self, card: Path) -> list[str]:
        """Return the files on a card, relative to it."""
        return sorted(
            p.relative_to(card).as_posix() for p in card.rglob("*") if p.is_file()
        )

    def test_restore_writes_the_original_firmware(self) -> None:
        (self.app_card / "DCOLYMP").mkdir()
        (self.app_card / "DCOLYMP" / "E1019999.BIN").write_bytes(b"old build")
        steps: list[int] = []
        done = serve.run_restore(
            self.paths, self.app_card, lambda line: None, steps.append
        )
        self.assertEqual(
            (done.files[0].content.sha256, steps), (stock.EPM2_V16.sha256, [1, 2])
        )
        on_card = (self.app_card / "DCOLYMP" / "E1019999.BIN").read_bytes()
        self.assertEqual(on_card, stock.read_stock(PATHS, stock.EPM2_V16))
        self.assertEqual(done.file_data()["DCOLYMP/E1019999.BIN"], on_card)
        out = Path(self.folder.name)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(self.cli("restore", "-o", str(out / "x.BIN")), 0)
            with self.assertRaises(SystemExit):
                self.cli("restore")
        self.assertEqual((out / "x.BIN").read_bytes(), on_card)

    def test_films_only_writes_what_films_set_writes(self) -> None:
        choices = ["ART2=velvia", "ART6=double-x"]
        done = serve.run_films(self.paths, choices, self.app_card)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            films = [word for choice in choices for word in ("--film", choice)]
            argv = ["films", "set", "--card", str(self.cli_card), *films]
            self.assertEqual(self.cli(*argv), 0)
        name = lookfile.CARD_NAME
        on_card = (self.cli_card / name).read_bytes()
        self.assertEqual((self.app_card / name).read_bytes(), on_card)
        self.assertEqual(self.files(self.app_card), [name])
        zipped = serve.run_films(self.paths, choices, None)
        self.assertEqual(zipped.file_data(), {name: on_card})
        self.assertEqual(
            zipped.steps[0].text, f"Copy {name} to the top of the SD card."
        )

    def test_the_app_writes_what_the_command_line_writes(self) -> None:
        choices = ["ART2=velvia", "ART6=double-x", "ART12=vision3-500t"]
        lines: list[str] = []
        steps: list[int] = []
        done = serve.run_job(
            self.paths, choices, self.app_card, lines.append, steps.append
        )
        self.assertEqual(steps, [1, 2, 3, 4, 5])
        self.assertEqual(
            done.files[0].content.sha256, pinned_description(self.paths).sha256
        )
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            films = [word for choice in choices for word in ("--film", choice)]
            argv = ["install", "--card", str(self.cli_card), *films]
            self.assertEqual(self.cli(*argv), 0)
        names = ["DCOLYMP/E1019999.BIN", lookfile.CARD_NAME]
        for name in names:
            self.assertEqual(
                (self.app_card / name).read_bytes(), (self.cli_card / name).read_bytes()
            )
            self.assertEqual(
                done.file_data()[name], (self.cli_card / name).read_bytes()
            )
        self.assertEqual(self.files(self.app_card), names)

    def test_with_no_film_install_and_make_write_the_firmware_only(self) -> None:
        serve.run_job(self.paths, [], self.app_card, lambda line: None, lambda n: None)
        pinned = pinned_description(self.paths).name
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(self.cli("install", "--card", str(self.cli_card)), 0)
            self.assertEqual(self.cli("make", pinned), 0)
        name = "DCOLYMP/E1019999.BIN"
        self.assertEqual(self.files(self.cli_card), [name])
        self.assertEqual(self.files(self.app_card), [name])
        self.assertEqual(self.files(self.paths.output), [name, f"{pinned}.BIN"])
        self.assertEqual(
            (self.app_card / name).read_bytes(), (self.cli_card / name).read_bytes()
        )
        self.assertEqual(
            (self.paths.output / name).read_bytes(),
            (self.cli_card / name).read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()

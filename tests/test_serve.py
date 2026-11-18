"""Tests of the local app, ``epm2mod.serve``.

    uv run python -m unittest discover -s tests

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

from support import ROOT  # noqa: E402

from epm2mod import cli, serve, stock  # noqa: E402
from epm2mod.builds import pinned_description  # noqa: E402
from epm2mod.cards import Card  # noqa: E402
from epm2mod.errors import BuildError  # noqa: E402
from epm2mod.looks import lookfile, records  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS).is_file()


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


class FakeRunner:
    """A job runner that records its arguments and returns fixed files."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path | None]] = []
        self.release = threading.Event()
        self.release.set()

    def __call__(self, paths, description, choices, card, log, step):  # type: ignore[no-untyped-def]
        self.calls.append((choices, card))
        log("1/5 stock firmware: ok")
        step(1)
        self.release.wait(10)
        if choices == ["ART3=c200"]:
            raise BuildError("the card is full")
        return "ab" * 32, {"DCOLYMP/E1019999.BIN": b"firmware", "EPM2LOOK.BIN": b"x"}


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
        self.assertEqual((state["error"], state["sha256"]), (None, "ab" * 32))
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
            return "cd" * 32, {"DCOLYMP/E1019999.BIN": b"stock"}

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
        from epm2mod.errors import StockError

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
                BuildError("/Volumes/X/DCOLYMP holds other files: A.BIN"),
                "holds other files",
            ),
            (StockError("download failed: timed out"), "internet connection"),
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
            original = serve.STATIC
            serve.STATIC = Path(folder)
            try:
                with redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(cli.main(["serve", "--no-browser"]), 1)
                self.assertIn("npm run build:app", err.getvalue())
            finally:
                serve.STATIC = original


def sandbox(folder: Path) -> RepoPaths:
    """Return a repository whose files are the checkout's, with its own ``build`` folder."""
    for entry in ROOT.iterdir():
        if entry.name != "build":
            (folder / entry.name).symlink_to(entry)
    return RepoPaths(folder)


@unittest.skipUnless(HAVE_STOCK, "needs the stock firmware")
class EndToEndTests(unittest.TestCase):
    def test_restore_writes_the_original_firmware(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "repo").mkdir()
            paths = sandbox(Path(folder) / "repo")
            card = Path(folder) / "card"
            (card / "DCOLYMP").mkdir(parents=True)
            (card / "DCOLYMP" / "E1019999.BIN").write_bytes(b"old build")
            steps: list[int] = []
            sha, files = serve.run_restore(paths, card, lambda line: None, steps.append)
            self.assertEqual((sha, steps), (stock.EPM2_V16.sha256, [1, 2]))
            on_card = (card / "DCOLYMP" / "E1019999.BIN").read_bytes()
            self.assertEqual(on_card, stock.read_stock(PATHS, stock.EPM2_V16))
            self.assertEqual(files["DCOLYMP/E1019999.BIN"], on_card)
            env = {"EPM2MOD_ROOT": str(paths.root)}
            with redirect_stdout(io.StringIO()), mock.patch.dict(os.environ, env):
                self.assertEqual(cli.main(["restore", "-o", folder]), 0)
                self.assertEqual(cli.main(["restore"]), 1)
            self.assertEqual((Path(folder) / "E1019999.BIN").read_bytes(), on_card)

    def test_the_app_writes_what_the_command_line_writes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "repo").mkdir()
            paths = sandbox(Path(folder) / "repo")
            app_card = Path(folder) / "app-card"
            cli_card = Path(folder) / "cli-card"
            app_card.mkdir()
            cli_card.mkdir()
            choices = ["ART2=velvia", "ART6=double-x", "ART12=vision3-500t"]
            lines: list[str] = []
            description = pinned_description(paths)
            steps: list[int] = []
            sha, files = serve.run_job(
                paths, description, choices, app_card, lines.append, steps.append
            )
            self.assertEqual(steps, [1, 2, 3, 4, 5])
            self.assertEqual(sha, description.sha256)
            env = {"EPM2MOD_ROOT": str(paths.root)}
            with redirect_stdout(io.StringIO()), mock.patch.dict(os.environ, env):
                for argv in (
                    ["make", "--card", str(cli_card)],
                    ["looks", "pack", *choices, "--card", str(cli_card)],
                ):
                    self.assertEqual(cli.main(argv), 0, argv)
            names = ["DCOLYMP/E1019999.BIN", lookfile.CARD_NAME]
            for name in names:
                self.assertEqual(
                    (app_card / name).read_bytes(), (cli_card / name).read_bytes()
                )
                self.assertEqual(files[name], (cli_card / name).read_bytes())
            self.assertEqual(
                sorted(
                    str(p.relative_to(app_card))
                    for p in app_card.rglob("*")
                    if p.is_file()
                ),
                names,
            )

    def test_make_on_a_card_writes_what_the_app_writes_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "repo").mkdir()
            paths = sandbox(Path(folder) / "repo")
            app_card = Path(folder) / "app-card"
            cli_card = Path(folder) / "cli-card"
            app_card.mkdir()
            cli_card.mkdir()
            description = pinned_description(paths)
            default = records.built_in_choices(records.load(paths))
            serve.run_job(
                paths, description, default, app_card, lambda line: None, lambda n: None
            )
            env = {"EPM2MOD_ROOT": str(paths.root)}
            with redirect_stdout(io.StringIO()), mock.patch.dict(os.environ, env):
                self.assertEqual(cli.main(["make", "--card", str(cli_card)]), 0)
            for name in ("DCOLYMP/E1019999.BIN", lookfile.CARD_NAME):
                self.assertEqual(
                    (app_card / name).read_bytes(), (cli_card / name).read_bytes()
                )
            self.assertEqual(
                (paths.card / lookfile.CARD_NAME).read_bytes(),
                (cli_card / lookfile.CARD_NAME).read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()

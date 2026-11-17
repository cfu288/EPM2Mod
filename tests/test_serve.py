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
from epm2mod.looks import lookfile  # noqa: E402
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

    def __call__(self, paths, description, choices, card, log):  # type: ignore[no-untyped-def]
        self.calls.append((choices, card))
        log("1/5 stock firmware: ok")
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
            "POST", "/api/make", {"choices": ["ART2=velvia"], "card": None}
        )
        self.assertEqual(status, 202, data)
        state = self.server.wait()
        self.assertEqual((state["error"], state["sha256"]), (None, "ab" * 32))
        self.assertEqual(state["lines"], ["1/5 stock firmware: ok"])
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
                "POST", "/api/make", {"choices": [], "card": card}
            )
            self.assertEqual(status, 400, card)
        self.assertEqual(self.runner.calls, [])
        status, _ = self.server.request(
            "POST", "/api/make", {"choices": [], "card": str(self.card.path)}
        )
        self.assertEqual(status, 202)
        self.server.wait()
        self.assertEqual(self.runner.calls, [([], self.card.path)])

    def test_wrong_requests_are_refused(self) -> None:
        for body in (
            {"choices": ["ART2=velvia"]},
            {"choices": ["ART2=nofilm"], "card": None},
            {"choices": ["ART2=velvia", "ART2=c200"], "card": None},
            {"choices": "ART2=velvia", "card": None},
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
        body = {"choices": ["ART3=c200"], "card": None}
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
            sha, files = serve.run_job(
                paths, description, choices, app_card, lines.append
            )
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


if __name__ == "__main__":
    unittest.main()

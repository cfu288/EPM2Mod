"""The local app (``epm2mod serve``): a page on this computer that makes the firmware and the film file.

The page calls the same functions as the command line, so it makes the same files and shows the same camera steps:
``pipeline.install`` (``epm2mod install``) and ``pipeline.restore`` (``epm2mod restore``), with the steps of
``camera_steps``. The result goes to an SD card from ``cards.cards`` or into a zip laid out as on the card.

Who can use it: the server listens on 127.0.0.1 only. Each API call needs the random token of the page's URL in the
header ``X-EPM2-Token``, and a Host header of ``127.0.0.1:PORT`` or ``localhost:PORT``. Another website can't send
that header without a CORS preflight, which this server never allows, and a DNS-rebinding page sends another Host.
A card path that ``cards.cards`` does not list is refused, so the page can't write to a fixed disk.

API (JSON):

- ``GET /api/build``: the pinned build (name, what, sha256).
- ``GET /api/cards``: the cards plugged in.
- ``POST /api/make`` with ``{"firmware": "epm2mod", "original" or "films", "choices": ["ART2=velvia", ...], "card": PATH or
  null}``: start a job. No choices: no film file. ``original`` is Olympus's own firmware (``pipeline.restore``), with
  no choices. ``films`` is the film file only (``pipeline.set_films``). One job at a time; a wrong request, or one while a job runs, gets 400 and the reason.
- ``GET /api/job``: the last job: its progress lines, and when it is done, the error or the result with the camera
  steps (``camera_steps``).
- ``GET /api/zip``: the files of the last finished job, as a zip.
- ``GET /api/ping``: the page is still open. ``POST /api/quit``: stop the server.

The server stops by itself on ``POST /api/quit`` (the page's Close the installer), or when no page has called it for
``IDLE_SECONDS`` and no job runs (the page was closed).

Every other path is a file of the built app page (``RepoPaths.app``, ``npm run build:app``).
"""

from __future__ import annotations

import hmac
import io
import json
import mimetypes
import secrets
import threading
import time
import webbrowser
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import cards as card_list
from .catalogue import Locator
from .errors import (
    BuildError,
    CardError,
    CheckError,
    DownloadError,
    Epm2ModError,
    UnavailableError,
)
from .fileio import Log
from .looks import records
from .pipeline import STEPS, Outcome, install, restore, set_films

#: How long the server waits for the page before it stops. Browsers slow timers in background tabs to one a minute.
IDLE_SECONDS = 180.0

#: The largest request body: a list of twelve choices and a path.
_MAX_BODY = 16 * 1024


@dataclass
class Job:
    """One run of ``install`` or ``restore``.

    Attributes:
        number: counts the jobs of this server, from 1.
        firmware: ``epm2mod``, ``original``, or ``films`` (only the film file).
        steps: the number of steps of the job.
        lines: the progress lines so far.
        step: the last step of ``make`` that ended, 0 to ``pipeline.STEPS``.
        done: True when the job has ended.
        error: the message of the error that ended it, or None.
        sha256: the firmware's SHA-256, when it is made.
        card: the card the files went to, or None.
        files: the files for the card, by their path on the card.
        camera_steps: the steps on the camera, when the job is done.
    """

    number: int
    firmware: str = "epm2mod"
    steps: int = STEPS
    lines: list[str] = field(default_factory=list)
    step: int = 0
    done: bool = False
    error: str | None = None
    sha256: str | None = None
    card: str | None = None
    files: dict[str, bytes] = field(default_factory=dict)
    camera_steps: list[dict[str, Any]] = field(default_factory=list)

    def state(self) -> dict[str, Any]:
        """Return what the page shows of the job."""
        return {
            "job": self.number,
            "firmware": self.firmware,
            "lines": list(self.lines),
            "step": self.step,
            "steps": self.steps,
            "done": self.done,
            "error": self.error,
            "sha256": self.sha256,
            "card": self.card,
            "files": sorted(self.files),
            "camera_steps": list(self.camera_steps),
        }


def run_job(
    paths: Locator,
    choices: list[str],
    card: Path | None,
    log: Log,
    step: Callable[[int], None],
) -> Outcome:
    """Make the pinned build's firmware and the film file, and write them to a card if one is given (``install``).

    Args:
        paths: the locator.
        choices: choices like ``ART2=velvia``; none for no film file.
        card: the top folder of the SD card, or None for the files only.
        log: where progress lines go.
        step: called with each step as it ends (``pipeline.STEPS``).

    Raises:
        Epm2ModError: if a step fails (the message is for the user).
    """
    return install(paths, card, choices, log=log, step=step)


def plain_message(error: Epm2ModError) -> str:
    """Return what a user who doesn't code should do about an error of a job.

    The common causes get a sentence with the next step; any other error keeps the build tool's message.
    """
    text = str(error)
    if "Permission denied" in text or "Read-only file system" in text:
        return (
            "The card is locked. Take it out, slide the switch on its side toward the metal contacts, "
            "put it back, then select Try again."
        )
    if "No space left" in text:
        return "The card is full. Make room on it, then select Try again."
    if "holds a folder" in text:
        return "The card's DCOLYMP folder holds a folder. Move it away, then select Try again."
    if "has no DCIM folder" in text:
        return "Format the card in the camera first, then select Try again."
    if isinstance(error, CheckError) and "gives back" in text:
        return (
            "The card did not keep the files. Use another card, then select Try again."
        )
    if isinstance(error, CardError) and "not an SD card" in text:
        return "Put the SD card back in this computer, then select Try again."
    if isinstance(error, DownloadError):
        return "Olympus's firmware could not be downloaded. Check the internet connection, then select Try again."
    return text


def run_restore(
    paths: Locator,
    card: Path | None,
    log: Log,
    step: Callable[[int], None],
) -> Outcome:
    """Get Olympus's original firmware, and write it to a card if one is given (``epm2mod restore``).

    Raises:
        Epm2ModError: if a step fails (the message is for the user).
    """
    return restore(paths, card, log=log, step=step)


def run_films(paths: Locator, choices: list[str], card: Path | None) -> Outcome:
    """Make only the film file, and write it to a card if one is given (``epm2mod films set``).

    Raises:
        Epm2ModError: if a step fails (the message is for the user).
    """
    return set_films(paths, choices, card=card)


def zip_files(files: dict[str, bytes]) -> bytes:
    """Return a zip of the files, by their path on the card."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    return out.getvalue()


class App:
    """The state of the local app: the token, the build and the last job."""

    def __init__(
        self,
        paths: Locator,
        static: Path | None = None,
        list_cards: Callable[[], list[card_list.Card]] = card_list.cards,
        job_runner: Callable[..., Outcome] = run_job,
        restore_runner: Callable[..., Outcome] = run_restore,
        films_runner: Callable[..., Outcome] = run_films,
    ) -> None:
        """Make the app for a locator; the token is new and random. ``static``: the app page, default the locator's."""
        self.paths = paths
        self.static = paths.app if static is None else static
        self.list_cards = list_cards
        self.run = job_runner
        self.run_restore = restore_runner
        self.run_films = films_runner
        self.token = secrets.token_urlsafe(24)
        self.description = paths.pinned_build()
        self.job: Job | None = None
        self.lock = threading.Lock()
        self.last_seen = time.monotonic()
        self.quit = threading.Event()

    def idle(self, now: float, limit: float = IDLE_SECONDS) -> bool:
        """Return True if no page has called the server for ``limit`` seconds and no job runs."""
        running = self.job is not None and not self.job.done
        return not running and now - self.last_seen > limit

    def build(self) -> dict[str, Any]:
        """Return the pinned build."""
        return {
            "name": self.description.name,
            "what": self.description.what,
            "sha256": self.description.sha256,
        }

    def cards(self) -> list[dict[str, Any]]:
        """Return the cards plugged in."""
        return [
            {
                "path": str(card.path),
                "name": card.name,
                "size": card.size,
                "free": card.free,
                "label": card_list.describe(card),
            }
            for card in self.list_cards()
        ]

    def start(self, body: Any) -> Job:
        """Start a job from the body of ``POST /api/make``.

        Raises:
            BuildError: if the body is wrong, the card is not listed, or a job runs.
        """
        if not isinstance(body, dict) or set(body) != {"firmware", "choices", "card"}:
            raise BuildError(
                "the request needs exactly 'firmware', 'choices' and 'card'"
            )
        firmware, choices, card = body["firmware"], body["choices"], body["card"]
        if firmware not in ("epm2mod", "original", "films"):
            raise BuildError("'firmware' is 'epm2mod', 'original' or 'films'")
        if firmware == "original" and choices:
            raise BuildError("Olympus's original firmware takes no film simulations")
        if not isinstance(choices, list) or not all(
            isinstance(choice, str) and records.is_choice(choice) for choice in choices
        ):
            raise BuildError("'choices' is a list like ['ART2=velvia']")
        target = None
        if card is not None:
            listed = {str(found.path): found.path for found in self.list_cards()}
            if not isinstance(card, str) or card not in listed:
                raise BuildError(
                    "Put the SD card back in this computer, then select Refresh."
                )
            target = listed[card]
        if choices:
            records.looks_of_choices(records.load(self.paths), choices)
        with self.lock:
            if self.job is not None and not self.job.done:
                raise BuildError("The firmware is being made. Wait for it to end.")
            job = Job(
                (self.job.number + 1) if self.job else 1,
                firmware=firmware,
                steps={"epm2mod": STEPS, "original": 2, "films": 1}[firmware],
                card=card,
            )
            self.job = job
        threading.Thread(
            target=self._work, args=(job, choices, target), daemon=True
        ).start()
        return job

    def _work(self, job: Job, choices: list[str], card: Path | None) -> None:
        """Run a job and record its end; its lines also go to the terminal."""

        def step(number: int) -> None:
            """Record the end of a step of ``make``."""
            job.step = number

        def log(line: str) -> None:
            """Keep a progress line for the page and print it."""
            job.lines.append(line)
            print(line, flush=True)

        try:
            if job.firmware == "original":
                outcome = self.run_restore(self.paths, card, log, step)
            elif job.firmware == "films":
                outcome = self.run_films(self.paths, choices, card)
                step(1)
            else:
                outcome = self.run(self.paths, choices, card, log, step)
            job.sha256 = outcome.files[0].content.sha256
            job.files = outcome.file_data()
            job.camera_steps = [item.to_json() for item in outcome.steps]
        except Epm2ModError as error:
            job.error = plain_message(error)
            print(f"error: {error}", flush=True)
        except Exception as error:  # the page must learn that the job ended
            job.error = f"an unexpected error: {error!r}"
            print(job.error, flush=True)
        finally:
            job.done = True


class Handler(BaseHTTPRequestHandler):
    """The requests of the page."""

    app: App
    port: int
    server_version = "epm2mod"

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal for the progress lines: requests are not logged."""

    def _send(
        self, status: int, data: bytes, kind: str, extra: dict[str, str] | None = None
    ) -> None:
        """Send a response."""
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status: int, value: Any) -> None:
        """Send a JSON response."""
        self._send(status, json.dumps(value).encode(), "application/json")

    def _host_ok(self) -> bool:
        """Return True if the Host (and an Origin, if sent) is this server."""
        hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        origin = self.headers.get("Origin")
        if origin is not None and urlsplit(origin).netloc not in hosts:
            return False
        return self.headers.get("Host") in hosts

    def _api_ok(self) -> bool:
        """Return True if the request carries the token."""
        sent = self.headers.get("X-EPM2-Token", "")
        return hmac.compare_digest(sent.encode(), self.app.token.encode())

    def _refused(self) -> bool:
        """Answer a request from elsewhere with 403 and return True."""
        path = urlsplit(self.path).path
        if self._host_ok() and (not path.startswith("/api/") or self._api_ok()):
            if path.startswith("/api/"):
                self.app.last_seen = time.monotonic()
            return False
        self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
        return True

    def do_OPTIONS(self) -> None:
        """Refuse every CORS preflight."""
        self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})

    def do_GET(self) -> None:
        """Answer the API's GET requests and the files of the page."""
        if self._refused():
            return
        path = urlsplit(self.path).path
        app = self.app
        if path == "/api/build":
            self._json(HTTPStatus.OK, app.build())
        elif path == "/api/cards":
            self._json(HTTPStatus.OK, app.cards())
        elif path == "/api/ping":
            self._json(HTTPStatus.OK, {"ok": True})
        elif path == "/api/job":
            self._json(HTTPStatus.OK, app.job.state() if app.job else None)
        elif path == "/api/zip":
            job = app.job
            if job is None or not job.done or job.error is not None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "no files made yet"})
                return
            self._send(
                HTTPStatus.OK,
                zip_files(job.files),
                "application/zip",
                {"Content-Disposition": 'attachment; filename="EPM2Mod-card.zip"'},
            )
        elif path.startswith("/api/"):
            self._json(HTTPStatus.NOT_FOUND, {"error": "no such call"})
        else:
            self._file(path)

    def do_POST(self) -> None:
        """Answer ``POST /api/make`` and ``POST /api/quit``."""
        if self._refused():
            return
        if urlsplit(self.path).path == "/api/quit":
            self.app.quit.set()
            self._json(HTTPStatus.OK, {"ok": True})
            return
        if urlsplit(self.path).path != "/api/make":
            self._json(HTTPStatus.NOT_FOUND, {"error": "no such call"})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "send JSON"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 0 < length <= _MAX_BODY:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "a body of 1 to 16 KB"})
            return
        try:
            body = json.loads(self.rfile.read(length))
            job = self.app.start(body)
        except (ValueError, Epm2ModError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._json(HTTPStatus.ACCEPTED, job.state())

    def _file(self, path: str) -> None:
        """Send a file of the page; ``/`` is ``index.html``."""
        root = self.app.static.resolve()
        name = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (root / name).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            self._json(HTTPStatus.NOT_FOUND, {"error": "no such file"})
            return
        kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._send(HTTPStatus.OK, target.read_bytes(), kind)


def server(app: App, port: int = 0) -> ThreadingHTTPServer:
    """Return the server of an app on 127.0.0.1 (a free port if ``port`` is 0)."""

    class Bound(Handler):
        """The handler of this app's server."""

    Bound.app = app
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Bound)
    Bound.port = httpd.server_port
    return httpd


def page_url(app: App, httpd: ThreadingHTTPServer) -> str:
    """Return the address of the page, with its token."""
    return f"http://127.0.0.1:{httpd.server_port}/#token={app.token}"


def serve(paths: Locator, port: int = 0, browser: bool = True) -> None:
    """Run the local app until the process is stopped.

    Raises:
        UnavailableError: if the app page is not built.
    """
    if not (paths.app / "index.html").is_file():
        raise UnavailableError(
            f"{paths.app}: the app page is not built: npm ci && npm run build:app"
        )
    app = App(paths)
    httpd = server(app, port)
    url = page_url(app, httpd)
    print(f"EPM2Mod is open in your browser: {url}", flush=True)
    print(
        "Leave this window open while you use the page. It stops when you select Close the installer.",
        flush=True,
    )
    if browser:
        webbrowser.open(url)

    def watch() -> None:
        """Stop the server on Close the installer, or when the page has been gone for ``IDLE_SECONDS``."""
        while not app.quit.wait(5.0) and not app.idle(time.monotonic()):
            pass
        httpd.shutdown()

    threading.Thread(target=watch, daemon=True).start()
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
    print("The installer has closed.", flush=True)

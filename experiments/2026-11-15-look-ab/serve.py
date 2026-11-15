"""Serve the film look A/B page and keep the votes of every screen in one file.

    ../../.venv/bin/python -I serve.py [--out out] [--votes votes] [--port 8765] [--bind 0.0.0.0]

The page is static and also works from any file server. With this server the votes go to
``VOTES/<id of the photo set>.json``, so a second device adds to the same result and the report
can compare the screens. Without it the page keeps the votes in the browser.

The API (JSON): GET api/state gives {"votes": [...], "screens": {key: label}}.
POST api/vote takes {"vote": {s, a, b, w, d, t}, "label": text}; POST api/undo and
POST api/reset take {"d": screen key} and remove the last vote, or all votes, of that screen.
Each POST answers with the new state. This is a tool for a home network: it has no login.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MAX_BODY = 4096
MAX_TEXT = 120


class BadRequest(Exception):
    """A request that the page would not send."""


class VoteStore:
    """The votes of one photo set, in a JSON file.

    A vote is {"s": scene id, "a": look, "b": look, "w": 1, 0 or 0.5, "d": screen key,
    "t": time in ms}. ``a`` was shown on the left; ``w`` is 1 when ``a`` won.
    """

    def __init__(self, path: Path, scene_ids: list[int], looks: int) -> None:
        """Open the file, or start empty if there is none."""
        self._path = path
        self._scene_ids = set(scene_ids)
        self._looks = looks
        self._lock = threading.Lock()
        self._votes: list[dict[str, Any]] = []
        self._screens: dict[str, str] = {}
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            self._votes = list(saved.get("votes", []))
            self._screens = dict(saved.get("screens", {}))

    def state(self) -> dict[str, Any]:
        """Return all votes and the label of each screen."""
        with self._lock:
            return {"votes": list(self._votes), "screens": dict(self._screens)}

    def add(self, vote: Any, label: Any) -> None:
        """Check a vote and append it.

        Raises:
            BadRequest: if a field is missing or out of range.
        """
        clean = self._checked(vote)
        with self._lock:
            self._votes.append(clean)
            if isinstance(label, str) and label.strip():
                self._screens[clean["d"]] = label.strip()[:MAX_TEXT]
            self._save()

    def undo(self, screen: Any) -> None:
        """Remove the last vote of one screen, if it has one."""
        key = _screen_key(screen)
        with self._lock:
            for index in range(len(self._votes) - 1, -1, -1):
                if self._votes[index]["d"] == key:
                    del self._votes[index]
                    break
            self._save()

    def reset(self, screen: Any) -> None:
        """Remove all votes of one screen."""
        key = _screen_key(screen)
        with self._lock:
            self._votes = [vote for vote in self._votes if vote["d"] != key]
            self._save()

    def _checked(self, vote: Any) -> dict[str, Any]:
        if not isinstance(vote, dict):
            raise BadRequest("'vote' must be an object")
        scene, first, second, won = vote.get("s"), vote.get("a"), vote.get("b"), vote.get("w")
        if scene not in self._scene_ids:
            raise BadRequest("unknown scene")
        for look in (first, second):
            if not isinstance(look, int) or isinstance(look, bool) or not 0 <= look < self._looks:
                raise BadRequest("unknown look")
        if first == second:
            raise BadRequest("a vote needs two different looks")
        if won not in (0, 0.5, 1):
            raise BadRequest("'w' must be 0, 0.5 or 1")
        taken = vote.get("t")
        return {
            "s": scene,
            "a": first,
            "b": second,
            "w": won,
            "d": _screen_key(vote.get("d")),
            "t": taken if isinstance(taken, int) and not isinstance(taken, bool) else 0,
        }

    def _save(self) -> None:
        """Write the file through a temporary file, so that a crash leaves the old one."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        text = json.dumps({"votes": self._votes, "screens": self._screens}, indent=1)
        temporary.write_text(text + "\n", encoding="utf-8")
        os.replace(temporary, self._path)


def _screen_key(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_TEXT:
        raise BadRequest("'d' must be the key of a screen")
    return value


class Handler(SimpleHTTPRequestHandler):
    """Static files of the output folder, and the vote API under ``api/``."""

    def __init__(self, *args: Any, store: VoteStore, **kwargs: Any) -> None:
        """Keep the store; the base class serves ``directory``."""
        self._store = store
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # noqa: N802 (the name is fixed by http.server)
        """Answer api/state, or serve a file."""
        if self.path.split("?")[0] == "/api/state":
            self._json(HTTPStatus.OK, self._store.state())
        else:
            super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        """Change the votes and answer with the new state."""
        try:
            body = self._body()
            action = self.path.split("?")[0]
            if action == "/api/vote":
                self._store.add(body.get("vote"), body.get("label"))
            elif action == "/api/undo":
                self._store.undo(body.get("d"))
            elif action == "/api/reset":
                self._store.reset(body.get("d"))
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "no such action"})
                return
        except BadRequest as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._json(HTTPStatus.OK, self._store.state())

    def guess_type(self, path: Any) -> str:
        """Say that text files are UTF-8: the page and its scripts hold characters such as ×."""
        kind = super().guess_type(path)
        text = kind.startswith("text/") or kind in ("application/javascript", "application/json")
        return f"{kind}; charset=utf-8" if text else kind

    def end_headers(self) -> None:
        """Tell the browser not to keep an old page or an old photo list."""
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            raise BadRequest("the request has no body, or the body is too long")
        try:
            body = json.loads(self.rfile.read(length))
        except ValueError:
            raise BadRequest("the body is not JSON") from None
        if not isinstance(body, dict):
            raise BadRequest("the body must be an object")
        return body

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def open_store(out: Path, votes: Path) -> VoteStore:
    """Make the store for the photo set that ``out/config.json`` describes."""
    config = json.loads((out / "config.json").read_text(encoding="utf-8"))
    scene_ids = [scene["id"] for scene in config["scenes"]]
    return VoteStore(votes / f"{config['id']}.json", scene_ids, len(config["looks"]))


def main() -> int:
    """Run the command line."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=HERE / "out", help="folder that build.py wrote")
    parser.add_argument("--votes", type=Path, default=HERE / "votes", help="folder for the vote files")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--bind", default="0.0.0.0", help="address to listen on; 127.0.0.1 for this machine only"
    )
    args = parser.parse_args()
    if not (args.out / "config.json").exists():
        print(f"error: {args.out} has no config.json: run build.py first", file=sys.stderr)
        return 1
    store = open_store(args.out, args.votes)
    handler = partial(Handler, store=store, directory=str(args.out))
    with ThreadingHTTPServer((args.bind, args.port), handler) as server:
        print(f"serving {args.out} on port {args.port}; votes in {args.votes}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

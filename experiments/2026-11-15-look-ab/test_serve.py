"""Tests of serve.py.   ../../.venv/bin/python -m unittest test_serve.py"""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

import serve


def vote(
    scene: int = 1, first: int = 0, second: int = 1, won: float = 1, screen: str = "phone"
) -> dict[str, object]:
    return {"s": scene, "a": first, "b": second, "w": won, "d": screen, "t": 5}


class VoteStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "votes" / "set.json"
        self.store = serve.VoteStore(self.path, [1, 2], 3)

    def test_votes_are_kept_in_the_file(self) -> None:
        self.store.add(vote(), "Phone")
        self.store.add(vote(2, 1, 2, 0.5, "desk"), "Desk")
        again = serve.VoteStore(self.path, [1, 2], 3)
        self.assertEqual(again.state(), self.store.state())
        self.assertEqual(again.state()["screens"], {"phone": "Phone", "desk": "Desk"})
        self.assertEqual(len(again.state()["votes"]), 2)

    def test_undo_and_reset_touch_one_screen_only(self) -> None:
        for screen in ("phone", "desk", "phone"):
            self.store.add(vote(screen=screen), screen)
        self.store.undo("phone")
        self.assertEqual([v["d"] for v in self.store.state()["votes"]], ["phone", "desk"])
        self.store.reset("phone")
        self.assertEqual([v["d"] for v in self.store.state()["votes"]], ["desk"])
        self.store.undo("nobody")  # no vote of that screen: nothing happens
        self.assertEqual(len(self.store.state()["votes"]), 1)

    def test_a_wrong_vote_is_refused(self) -> None:
        wrong = [
            vote(scene=9),
            vote(first=3),
            vote(first=1, second=1),
            vote(won=2),
            vote(screen=""),
            {**vote(), "a": True},
            "text",
        ]
        for item in wrong:
            with self.subTest(item=item), self.assertRaises(serve.BadRequest):
                self.store.add(item, "x")
        self.assertEqual(self.store.state()["votes"], [])
        self.assertFalse(self.path.exists())


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        out = Path(folder.name) / "out"
        out.mkdir()
        config = {"id": "abc", "looks": [{}, {}, {}], "scenes": [{"id": 1}, {"id": 2}]}
        (out / "config.json").write_text(json.dumps(config))
        (out / "index.html").write_text("page")
        store = serve.open_store(out, Path(folder.name) / "votes")
        handler = partial(serve.Handler, store=store, directory=str(out))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}/"

    def call(self, path: str, body: object = None) -> tuple[int, object]:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data)
        try:
            with urllib.request.urlopen(request) as answer:
                raw = answer.read()
                return answer.status, json.loads(raw) if path.startswith("api/") else raw.decode()
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_the_page_and_the_votes_are_served(self) -> None:
        self.assertEqual(self.call("index.html"), (200, "page"))
        self.assertEqual(self.call("api/state"), (200, {"votes": [], "screens": {}}))
        status, state = self.call("api/vote", {"vote": vote(), "label": "Phone"})
        self.assertEqual(status, 200)
        self.assertEqual(state, {"votes": [vote()], "screens": {"phone": "Phone"}})
        self.assertEqual(
            self.call("api/undo", {"d": "phone"})[1], {"votes": [], "screens": {"phone": "Phone"}}
        )

    def test_a_wrong_request_gets_an_error(self) -> None:
        self.assertEqual(self.call("api/vote", {"vote": vote(scene=7)})[0], 400)
        self.assertEqual(self.call("api/vote", [1])[0], 400)
        self.assertEqual(self.call("api/other", {"d": "x"})[0], 404)


if __name__ == "__main__":
    unittest.main()

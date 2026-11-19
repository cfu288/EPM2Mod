"""Tests of the link map for the agent hook: ``tools/doc_links.json`` and ``tools/doc_links.py``.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import glob
import json
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "tools" / "doc_links.json"
SCRIPT = ROOT / "tools" / "doc_links.py"


def run_hook(payload: dict) -> str:
    """Run the hook script with payload on stdin, as Claude Code does; return its stdout."""
    done = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(payload), capture_output=True, text=True, cwd=ROOT, check=True
    )
    return done.stdout


class DocLinksTests(unittest.TestCase):
    def test_every_path_of_the_map_names_a_file(self) -> None:
        groups = json.loads(MAP.read_text())["groups"]
        missing = [
            f"{group['name']}: {pattern}"
            for group in groups
            for pattern in group.get("truth", []) + group.get("copies", [])
            if not glob.glob(str(ROOT / pattern))
        ]
        self.assertEqual(missing, [], "tools/doc_links.json names files that are gone")

    def test_an_edit_of_a_linked_file_names_the_others_once_per_session(self) -> None:
        session = f"test-{uuid.uuid4().hex}"
        event = {"session_id": session, "tool_name": "Edit", "tool_input": {"file_path": str(ROOT / "looks/catalogue.json")}}
        first = json.loads(run_hook(event))
        context = first["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(first["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("Film catalogue", context)
        self.assertIn("docs/guide/film-looks.md", context)
        self.assertEqual(run_hook(event), "")

    def test_an_unlinked_or_outside_file_gives_nothing(self) -> None:
        for path in (str(ROOT / "src/epm2mod/stock.py"), "/somewhere/else.txt"):
            with self.subTest(path):
                self.assertEqual(run_hook({"session_id": "x", "tool_input": {"file_path": path}}), "")

    def test_bad_input_gives_nothing(self) -> None:
        done = subprocess.run([sys.executable, str(SCRIPT)], input="not json", capture_output=True, text=True, cwd=ROOT)
        self.assertEqual((done.returncode, done.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()

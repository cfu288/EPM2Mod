"""Tests of ``release/publish.sh``, the last step of the release workflow, with a stand-in for ``gh``.

    uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT  # noqa: E402

SCRIPT = ROOT / "release" / "publish.sh"

#: A stand-in for gh: it logs its arguments, and ``release view`` answers as GH_VIEW says.
GH = """#!/bin/sh
echo "$*" >> "$GH_LOG"
case "$1 $2 $GH_VIEW" in
  "release view draft") echo true ;;
  "release view published") echo false ;;
  "release view none") echo "release not found" >&2; exit 1 ;;
  "release view broken") echo "HTTP 502" >&2; exit 1 ;;
esac
"""


class PublishTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        for name in ("release-zip/EPM2Mod-V.zip", "release-dmg/EPM2Mod-V.dmg", "release-notes/notes.md"):
            (self.folder / name).parent.mkdir(exist_ok=True)
            (self.folder / name).write_text("x", encoding="utf-8")
        bin_folder = self.folder / "bin"
        bin_folder.mkdir()
        (bin_folder / "gh").write_text(GH, encoding="utf-8")
        (bin_folder / "gh").chmod(0o755)
        self.log = self.folder / "gh.log"
        self.env = {**os.environ, "PATH": f"{bin_folder}{os.pathsep}{os.environ['PATH']}", "GH_LOG": str(self.log)}
        self.env["GITHUB_REPOSITORY"] = "owner/repo"

    def publish(self, view: str, checked: str = "ab", packaged: str = "ab") -> tuple[int, list[str]]:
        """Run the script with ``release view`` answering ``view``; return its exit status and the gh calls."""
        done = subprocess.run(
            ["sh", str(SCRIPT), "v1", "1", "true", "c0ffee", checked, packaged],
            cwd=self.folder,
            env={**self.env, "GH_VIEW": view},
            capture_output=True,
            text=True,
            check=False,
        )
        calls = self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []
        return done.returncode, [" ".join(call.split()[:2]) for call in calls]

    def test_a_new_release_is_a_draft_and_then_published(self) -> None:
        self.assertEqual(self.publish("none"), (0, ["release view", "release create", "release edit"]))
        create = self.log.read_text(encoding="utf-8").splitlines()[1]
        self.assertIn("--draft --prerelease=true", create)
        self.assertIn("--target c0ffee --title EPM2Mod 1", create)

    def test_a_draft_that_a_failed_run_left_is_replaced(self) -> None:
        self.assertEqual(
            self.publish("draft"), (0, ["release view", "release delete", "release create", "release edit"])
        )

    def test_a_published_release_is_not_touched(self) -> None:
        self.assertEqual(self.publish("published"), (1, ["release view"]))

    def test_another_gh_error_stops_the_step(self) -> None:
        self.assertEqual(self.publish("broken"), (1, ["release view"]))

    def test_a_zip_with_other_firmware_is_not_published(self) -> None:
        self.assertEqual(self.publish("none", checked="ab", packaged="cd"), (1, []))

    def test_a_missing_argument_prints_the_usage(self) -> None:
        done = subprocess.run(["sh", str(SCRIPT), "v1"], env=self.env, capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage: publish.sh", done.stderr)


if __name__ == "__main__":
    unittest.main()

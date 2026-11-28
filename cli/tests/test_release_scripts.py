"""Tests of ``release/plan.sh`` and ``release/publish.sh``, the steps of the release workflow, with stand-ins.

    uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT  # noqa: E402

SCRIPT = ROOT / "release" / "publish.sh"
PLAN = ROOT / "release" / "plan.sh"

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
            ["sh", str(SCRIPT), "v1", "EPM2Mod 1", "true", "c0ffee", checked, packaged],
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

    def test_a_plan_without_a_sha256_is_not_published(self) -> None:
        self.assertEqual(self.publish("none", checked="", packaged=""), (1, []))

    def test_a_missing_argument_prints_the_usage(self) -> None:
        done = subprocess.run(["sh", str(SCRIPT), "v1"], env=self.env, capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage: publish.sh", done.stderr)



#: A stand-in for uv: it logs its arguments, prints UV_PLAN and exits with UV_STATUS.
UV = """#!/bin/sh
echo "$*" >> "$UV_LOG"
printf '%s\\n' "$UV_PLAN"
exit "$UV_STATUS"
"""

READY = {
    "ready": True, "problems": [], "tag": "v1-rc.1", "release_version": "1-rc.1", "title": "EPM2Mod 1-rc.1",
    "prerelease": True, "commit": "c0ffee", "sha256": "ab", "notes": "New dial.\n\nFirmware: x.",
}  # fmt: skip


class PlanScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        bin_folder = self.folder / "bin"
        bin_folder.mkdir()
        (bin_folder / "uv").write_text(UV, encoding="utf-8")
        (bin_folder / "uv").chmod(0o755)
        self.output = self.folder / "output"
        self.env = {
            **os.environ, "PATH": f"{bin_folder}{os.pathsep}{os.environ['PATH']}", "UV_LOG": str(self.folder / "uv.log"),
            "GITHUB_OUTPUT": str(self.output), "KIND": "rc", "BUILD": "", "SUMMARY": "New dial.",
        }  # fmt: skip

    def plan(self, document: dict[str, object], status: int = 0, **env: str) -> subprocess.CompletedProcess[str]:
        """Run the script with a stand-in uv that prints ``document`` and exits with ``status``."""
        return subprocess.run(
            ["sh", str(PLAN), "notes.md"],
            cwd=self.folder,
            env={**self.env, "UV_PLAN": json.dumps(document), "UV_STATUS": str(status), **env},
            capture_output=True,
            text=True,
            check=False,
        )

    def test_a_ready_plan_gives_the_outputs_and_the_notes(self) -> None:
        done = self.plan(READY)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(
            self.output.read_text(encoding="utf-8").splitlines(),
            ["tag=v1-rc.1", "release_version=1-rc.1", "title=EPM2Mod 1-rc.1", "prerelease=true", "commit=c0ffee",
             "sha256=ab"],
        )  # fmt: skip
        self.assertEqual((self.folder / "notes.md").read_text(encoding="utf-8"), "New dial.\n\nFirmware: x.\n")
        self.assertEqual(
            (self.folder / "uv.log").read_text(encoding="utf-8"), "run epm2mod release --json --summary New dial.\n"
        )

    def test_the_kind_and_the_build_become_flags(self) -> None:
        self.plan(READY, KIND="final", BUILD="probe")
        self.assertIn("--final --build probe", (self.folder / "uv.log").read_text(encoding="utf-8"))

    def test_a_plan_that_is_not_ready_keeps_its_exit_status_and_names_the_reasons(self) -> None:
        done = self.plan({"ready": False, "problems": ["the tree has changes"]}, status=1)
        self.assertEqual(done.returncode, 1)
        self.assertIn("::error::Not ready: the tree has changes", done.stdout)
        self.assertFalse(self.output.exists())
        self.assertFalse((self.folder / "notes.md").exists())

    def test_an_error_document_gives_its_message(self) -> None:
        done = self.plan({"ok": False, "error": {"message": "no checkout"}}, status=6)
        self.assertEqual(done.returncode, 6)
        self.assertIn("::error::no checkout", done.stdout)

if __name__ == "__main__":
    unittest.main()

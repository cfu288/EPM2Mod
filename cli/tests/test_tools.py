"""The scripts that the checks rest on: what each one must refuse.

    uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import support  # noqa: E402
from support import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import toolchain  # noqa: E402

from epm2mod import readme, stock  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()


OBJDUMP = Path(toolchain.DEFAULT_DIR) / (toolchain.PREFIX + "objdump")


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
@support.needs(OBJDUMP.exists(), support.OBJDUMP_NEEDED)
class SaveGuardTests(unittest.TestCase):
    def test_the_reference_must_show_the_fault(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator" / "scenarios"))
        import scen_guard

        with mock.patch.object(scen_guard, "OUT", lambda line: None):
            self.assertTrue(scen_guard.verdict("S19", [("pinned-fast", ["art buffers refused"]), ("build", [])]))
            self.assertFalse(scen_guard.verdict("S19", [("pinned-fast", []), ("build", [])]))
            self.assertFalse(scen_guard.verdict("S19", [("pinned-fast", ["art buffers refused"]), ("build", ["no picture"])]))


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class LedgerInputTests(unittest.TestCase):
    def test_the_ledger_is_made_from_the_files_git_holds_and_the_specs_given(self) -> None:
        import freespace

        copy = ROOT / "data" / "specs" / "zz-untracked-copy-for-a-test.json"
        copy.write_bytes((ROOT / "data" / "specs" / "spot-core-2.json").read_bytes())
        try:
            name = "data/specs/" + copy.name
            self.assertNotIn(name, [spec.path for spec in freespace.all_specs()])
            self.assertIn("data/specs/spot-core-2.json", [spec.path for spec in freespace.all_specs()])
            self.assertIn(name, [spec.path for spec in freespace.all_specs(extra=[name])])  # a candidate's own spec
        finally:
            copy.unlink()

    def test_a_spec_that_cannot_be_read_stops_the_check_with_its_name(self) -> None:
        import freespace

        broken = ROOT / "data" / "specs" / "zz-broken-for-a-test.json"
        broken.write_text("{ not json")
        try:
            with self.assertRaises(freespace.SiteError) as caught:
                freespace.all_specs(extra=["data/specs/" + broken.name])
        finally:
            broken.unlink()
        self.assertIn("zz-broken-for-a-test.json cannot be read", str(caught.exception))

class TrackedFilesTests(unittest.TestCase):
    def test_the_build_table_lists_the_descriptions_git_holds(self) -> None:
        pinned = ROOT / pinned_build_path()
        copy = pinned.with_name("zz-untracked-copy-for-a-test.json")
        copy.write_bytes(pinned.read_bytes())  # a tested description that is only in the working tree
        try:
            self.assertNotIn(copy.stem, readme.builds_block(PATHS, ROOT))
            self.assertIn(pinned.stem, readme.builds_block(PATHS, ROOT))
        finally:
            copy.unlink()

    def test_a_draft_in_the_working_tree_does_not_change_a_check_or_stop_a_listing(self) -> None:
        from epm2mod import cli

        draft_guide = PATHS.guides / "zz-draft-for-a-test.md"
        malformed = PATHS.builds / "zz-malformed-for-a-test.json"
        draft_guide.write_text("# A draft\n")
        malformed.write_text("{ not a description")
        try:
            self.assertEqual(readme.feature_problems(PATHS), [])  # the draft is not a guide yet
            self.assertTrue(readme.is_current(PATHS))  # generate --check
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(cli.main(["--project", str(ROOT), "builds", "--json"]), 0)
            listed = json.loads(out.getvalue())
            self.assertEqual(len(listed["unreadable"]), 1)
            self.assertIn(malformed.name, listed["unreadable"][0])
            self.assertTrue(all(build["in_git"] for build in listed["builds"]))
        finally:
            draft_guide.unlink()
            malformed.unlink()

    def test_a_program_of_the_release_is_one_by_gits_mode(self) -> None:
        from epm2mod import release

        self.assertIn("start.sh", release.programs(PATHS))
        self.assertNotIn("README.txt", release.programs(PATHS))

    def test_the_zip_holds_the_package_files_git_holds(self) -> None:
        from epm2mod import release

        draft = PATHS.package / "zz_untracked_draft_for_a_test.py"
        draft.write_text("x = 1\n")
        try:
            names = [name for name, _ in release._package(PATHS)]
        finally:
            draft.unlink()
        self.assertNotIn(PATHS.relative(draft), names)
        self.assertIn(PATHS.relative(PATHS.package / "cli.py"), names)


class WorkingFolderTests(unittest.TestCase):
    def test_a_descriptions_specs_are_the_repositorys_wherever_the_check_runs(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import hookcheck

        description = ROOT / pinned_build_path()
        with tempfile.TemporaryDirectory() as folder:
            decoy = Path(folder) / "data" / "specs"
            decoy.mkdir(parents=True)
            for spec in json.loads(description.read_text())["specs"]:
                (Path(folder) / spec).write_text("{}")  # a file of the same relative path in the working folder
            os.chdir(folder)
            try:
                specs = hookcheck.spec_list([str(description)])
            finally:
                os.chdir(ROOT)
        self.assertTrue(specs)
        self.assertTrue(all(Path(spec).is_relative_to(ROOT) for spec in specs), specs[:2])


def pinned_build_path() -> str:
    """Return the path of the pinned build's description, relative to the root."""
    return str(json.loads((ROOT / "data" / "pinned-build.json").read_text())["build"])


if __name__ == "__main__":
    unittest.main()

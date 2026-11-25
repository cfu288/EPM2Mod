"""The scripts that the checks rest on: what each one must refuse.

    uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
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
from epm2mod.builds import pinned_description  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class FirmwareMapTests(unittest.TestCase):
    def check(self, folder: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(ROOT / "tools" / "fwmap.py"), "--out", folder, "check"]
        return subprocess.run(command, capture_output=True, text=True)

    def test_a_map_without_its_last_file_is_not_complete(self) -> None:
        import fwmap

        with tempfile.TemporaryDirectory() as folder:
            for name in fwmap.FILES[:-1]:
                (Path(folder) / name).write_text("x")
            done = self.check(folder)
            self.assertEqual(done.returncode, 1)
            self.assertIn(fwmap.FILES[-1], done.stderr)
            (Path(folder) / fwmap.FILES[-1]).write_text("firmware sha256 0\n")  # made from another firmware
            done = self.check(folder)
            self.assertEqual(done.returncode, 1)
            self.assertIn("another firmware", done.stderr)
            self.assertIn("fwmap.py sha256", fwmap.made_by())  # a map of older map code is not current
            older = fwmap.made_by().replace("fwmap.py sha256 ", "fwmap.py sha256 0")
            (Path(folder) / fwmap.FILES[-1]).write_text(older)
            self.assertEqual(self.check(folder).returncode, 1)
            (Path(folder) / fwmap.FILES[-1]).write_text(fwmap.made_by())
            self.assertEqual(self.check(folder).returncode, 0, done.stderr)
        self.assertIn("tasks.tsv", fwmap.FILES)  # emulator/liveview.py reads it


class ToolchainTests(unittest.TestCase):
    def test_an_objdump_on_path_is_never_used(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "bin" / (toolchain.PREFIX + "objdump")
            fake.parent.mkdir()
            fake.write_text("#!/bin/sh\n")
            fake.chmod(0o755)
            environment = {"PATH": str(fake.parent) + os.pathsep + os.environ["PATH"]}
            with mock.patch.object(toolchain, "REPO", folder + "/norepo"), mock.patch.dict(os.environ, environment):
                os.environ.pop("EPM2_BINUTILS", None)
                with self.assertRaises(toolchain.ToolchainError):
                    toolchain.binutils_dir()

    def test_an_override_is_honoured_or_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as folder, mock.patch("sys.stderr"):
            with mock.patch.dict(os.environ, {"EPM2_BINUTILS": folder + "/absent", "CI": ""}):
                with self.assertRaisesRegex(toolchain.ToolchainError, "EPM2_BINUTILS: no MN103 binutils"):
                    toolchain.binutils_dir()  # no fall-back to build/toolchain
            (Path(folder) / (toolchain.PREFIX + "objdump")).write_text("")
            with mock.patch.dict(os.environ, {"EPM2_BINUTILS": folder, "CI": ""}):
                self.assertEqual(toolchain.binutils_dir(), folder)
            with mock.patch.dict(os.environ, {"EPM2_BINUTILS": folder, "CI": "1"}):
                with self.assertRaisesRegex(toolchain.ToolchainError, "hard checks"):
                    toolchain.binutils_dir()

    def test_binutils_of_another_source_commit_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            objdump = Path(folder) / "build" / "toolchain" / "bin" / (toolchain.PREFIX + "objdump")
            objdump.parent.mkdir(parents=True)
            objdump.write_text("")
            record = objdump.parent.parent / "source-commit"
            with mock.patch.object(toolchain, "REPO", folder), mock.patch.object(toolchain, "pinned_commit", return_value="abc"):
                os.environ.pop("EPM2_BINUTILS", None)
                with self.assertRaisesRegex(toolchain.ToolchainError, "source commit unknown"):
                    toolchain.binutils_dir()
                record.write_text("def\n")
                with self.assertRaisesRegex(toolchain.ToolchainError, "source commit def"):
                    toolchain.binutils_dir()
                record.write_text("abc\n")
                self.assertEqual(toolchain.binutils_dir(), str(objdump.parent))
            record.unlink()  # no record and no pin that git can name: not a match
            with mock.patch.object(toolchain, "REPO", folder), mock.patch.object(toolchain, "pinned_commit", return_value=""):
                with self.assertRaises(toolchain.ToolchainError):
                    toolchain.binutils_dir()


class EmulatorPinTests(unittest.TestCase):
    def test_an_override_is_refused_in_the_hard_checks(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        for name, call in (("OM_EMU_DIR", emuenv.om_emu_dir), ("OM_EMU_NODE", emuenv.node)):
            with self.subTest(name=name), mock.patch("sys.stderr"):
                with mock.patch.dict(os.environ, {name: "/x/elsewhere", "CI": "1"}):
                    with self.assertRaisesRegex(emuenv.EmuSetupError, name):
                        call()
                with mock.patch.dict(os.environ, {name: "/x/elsewhere", "CI": ""}):
                    self.assertEqual(call(), "/x/elsewhere")

    def test_emulator_options_do_not_come_from_the_callers_shell(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        shell = {"E101_FAST": "1", "E101_STATE": "/x/state.json", "WATCH": "0x1", "NO_OK": "1", "BOOTMS": "9", "KEPT": "yes"}
        with mock.patch.dict(os.environ, shell):
            clean = emuenv.clean_environment()
        self.assertEqual({name for name in shell if name in clean}, {"KEPT"})
        self.assertIn("PATH", clean)
        source = (ROOT / "emulator" / "emuenv.py").read_text()
        self.assertIn("env = dict(os.environ) if options_from_shell else clean_environment()", source)

    def test_an_edited_submodule_is_refused(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        def run(command: list[str], **keywords: object) -> mock.Mock:
            answers = {"ls-files": "160000 abc 0\temulator/om-emu\n", "rev-parse": "abc\n", "status": " M emu/bin/boot.mjs\n"}
            return mock.Mock(stdout=answers[command[1]])

        with mock.patch.dict(os.environ, {"OM_EMU_DIR": ""}), mock.patch.object(emuenv.os.path, "exists", return_value=True):
            with mock.patch.object(emuenv.subprocess, "run", run):
                with self.assertRaisesRegex(emuenv.EmuSetupError, "changes that are not in its commit"):
                    emuenv.require_om_emu()

    def test_a_submodule_at_another_commit_is_refused(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        other = mock.Mock(stdout="160000 0000000000000000000000000000000000000000 0\temulator/om-emu\n")
        with mock.patch.dict(os.environ, {"OM_EMU_DIR": ""}), mock.patch.object(emuenv.os.path, "exists", return_value=True):
            with mock.patch.object(emuenv.subprocess, "run", return_value=other):
                with self.assertRaisesRegex(emuenv.EmuSetupError, "the repository pins 0000000"):
                    emuenv.require_om_emu()


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class UnpackedImageTests(unittest.TestCase):
    def test_changed_blocks_in_the_folder_of_unpacked_images_are_not_reused(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"EMU_IMAGES": folder}):
            block = Path(emuenv.blocks("stock")) / "block0_0100.bin"
            good = block.read_bytes()
            sums = (block.parent / emuenv.SUMS).read_text()
            self.assertTrue(sums.splitlines()[0].endswith("the unpacker"))  # blocks of an older unpacker are not reused
            self.assertIn(emuenv.sha256(str(ROOT / "tools" / "oetool.py")), sums)
            block.write_bytes(bytes([good[0] ^ 1]) + good[1:])
            self.assertEqual((Path(emuenv.blocks("stock")) / "block0_0100.bin").read_bytes(), good)


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

    def test_the_map_records_the_objdump_that_made_it(self) -> None:
        import fwmap

        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / (toolchain.PREFIX + "objdump")).write_text("another objdump")
            pinned = fwmap.made_by()
            with mock.patch.object(toolchain, "binutils_dir", return_value=folder):
                other = fwmap.made_by()
        self.assertNotEqual(pinned, other)
        self.assertIn("objdump sha256", pinned)


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

    def test_ci_does_not_pick_up_descriptions_that_git_does_not_hold(self) -> None:
        script = (ROOT / "tools" / "ci.sh").read_text()
        builds = next(line for line in script.splitlines() if line.startswith("builds="))
        self.assertIn("$pinned", builds)
        self.assertIn("$named", builds)
        self.assertNotIn("unheld", builds)
        self.assertIn("Not checked, because git does not hold them", script)

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


class FirmwareMapUseTests(unittest.TestCase):
    def test_the_free_space_check_refuses_a_map_that_is_not_current(self) -> None:
        import freespace
        import fwmap

        with tempfile.TemporaryDirectory() as folder:
            for name in ("linear.txt", "functions.tsv", fwmap.FILES[-1]):
                (Path(folder) / name).write_text("addr\n")
            with mock.patch.object(freespace, "LINEAR", folder + "/linear.txt"), mock.patch.object(freespace, "FUNCTIONS", folder + "/functions.tsv"):
                with mock.patch.object(fwmap, "made_by", return_value="now\n"):
                    with self.assertRaises(freespace.SiteError):
                        freespace.Linear()


def pinned_build_path() -> str:
    """Return the path of the pinned build's description, relative to the root."""
    return str(json.loads((ROOT / "data" / "pinned-build.json").read_text())["build"])


class NodeVersionTests(unittest.TestCase):
    def test_one_full_version_everywhere(self) -> None:
        version = (ROOT / ".nvmrc").read_text().strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        engines = json.loads((ROOT / "web" / "package.json").read_text())["engines"]["node"]
        self.assertEqual(engines, version)


class DocumentTests(unittest.TestCase):
    def test_the_documents_do_not_promise_the_pinned_label_or_sha256_for_a_release(self) -> None:
        build = pinned_description(PATHS)
        text = readme.pinned_block(PATHS, ROOT)
        self.assertNotIn(f"EPM2Mod {build.label}", text)
        self.assertIn("the day of the release", text)
        self.assertIn("Pinned build as tested", text)


if __name__ == "__main__":
    unittest.main()

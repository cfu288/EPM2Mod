"""The scripts that the checks rest on: what each one must refuse.

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
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import support  # noqa: E402
from support import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import checks  # noqa: E402
import toolchain  # noqa: E402

from epm2mod import pipeline, readme, stock  # noqa: E402
from epm2mod.builds import pinned_description  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()


#: A path of the kind the rule refuses, put together here so that this file passes the rule.
REAL = "/ho" + "me/realuser/"


class MachinePathTests(unittest.TestCase):
    def refused(self, line: str) -> bool:
        done = subprocess.run([str(ROOT / ".githooks" / "machine-paths")], input=line + "\n", capture_output=True, text=True)
        return done.returncode == 1

    def test_a_real_path_is_refused_also_beside_an_allowed_token(self) -> None:
        for line in (f"+ see {REAL}notes", f"+ scp {REAL}secret USER@HOST:/x", f"+ a /home/user/x b {REAL}y"):
            with self.subTest(line=line):
                self.assertTrue(self.refused(line))

    def test_placeholders_and_removed_lines_pass(self) -> None:
        for line in ("+ scp USER@HOST:/x /home/user/y", "+ git@github.com:cfu288/EPM2Mod.git", f"- old {REAL}x", "+++ b/home/x"):
            with self.subTest(line=line):
                self.assertFalse(self.refused(line))


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
            block.write_bytes(bytes([good[0] ^ 1]) + good[1:])
            self.assertEqual((Path(emuenv.blocks("stock")) / "block0_0100.bin").read_bytes(), good)


class PrintedFailTests(unittest.TestCase):
    def test_a_script_that_prints_a_failed_result_and_exits_0_has_failed(self) -> None:
        def status(text: str) -> str:
            check = checks.Check("s", "full", (sys.executable, "-c", f"print({text!r})"), judged=False)
            return checks.run(check, Path("image.BIN")).status

        self.assertEqual(status("  S6 RESULT [build]: FAIL: art codes [9]"), "FAIL")
        self.assertEqual(status("  S6 RESULT [build]: PASS"), "WARN")

    def test_a_failure_without_a_failed_result_line_shows_how_it_ended(self) -> None:
        check = checks.Check("s", "full", (sys.executable, "-c", "print('S1 RESULT [b]: PASS'); raise SystemExit('boom')"))
        result = checks.run(check, Path("image.BIN"))
        self.assertEqual(result.status, "FAIL")
        self.assertIn("boom", checks.summary(check, result))
        self.assertIn("exit status 1", checks.summary(check, result))


class StrictTimesTests(unittest.TestCase):
    def test_the_hard_tier_fails_a_start_whose_times_moved(self) -> None:
        build = ROOT / pinned_build_path()
        with mock.patch.object(checks, "current_image", return_value=Path("image.BIN")):
            plan = {check.name: check for check in checks.plan(build, "quick")}
        self.assertIn("--strict-times", plan["boot-test"].command)
        self.assertTrue(all(check.judged for check in plan.values()))


def pinned_build_path() -> str:
    """Return the path of the pinned build's description, relative to the root."""
    return str(json.loads((ROOT / "data" / "pinned-build.json").read_text())["build"])


class MachinePathHistoryTests(unittest.TestCase):
    def test_a_path_that_one_commit_adds_and_a_later_one_removes_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as folder:

            def git(*args: str) -> None:
                identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null"]
                subprocess.run(["git", *identity, *args], cwd=folder, check=True, capture_output=True)

            def commit(text: str) -> None:
                (Path(folder) / "notes.txt").write_text(text)
                git("add", "notes.txt")
                git("commit", "-q", "-m", "x")

            git("init", "-q")
            commit("start\n")
            git("tag", "base")
            commit(f"see {REAL}notes\n")
            git("tag", "added")
            commit("see /path/to/notes\n")
            tool = str(ROOT / ".githooks" / "machine-paths")
            net = subprocess.run(["git", "diff", "-U0", "base", "HEAD"], cwd=folder, capture_output=True, text=True).stdout
            self.assertEqual(subprocess.run([tool], input=net, capture_output=True, text=True).returncode, 0)
            self.assertEqual(subprocess.run([tool, "--since", "base"], cwd=folder, capture_output=True).returncode, 1)
            self.assertEqual(subprocess.run([tool, "--since", "added"], cwd=folder, capture_output=True).returncode, 0)


class NodeVersionTests(unittest.TestCase):
    def test_one_full_version_everywhere(self) -> None:
        version = (ROOT / ".nvmrc").read_text().strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        engines = json.loads((ROOT / "web" / "package.json").read_text())["engines"]["node"]
        self.assertEqual(engines, version)


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class CurrentImageTests(unittest.TestCase):
    def test_an_image_of_other_bytes_stops_the_checks(self) -> None:
        build = pinned_description(PATHS)
        specs = pipeline.load_specs(PATHS, build)
        image = pipeline.build_image(build, specs, stock.read_stock(PATHS, build.stock_firmware))[0].image
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.BIN"
            path.write_bytes(image)
            self.assertEqual(checks.current_image(build.name, path), path)
            path.write_bytes(image[:-1] + bytes([image[-1] ^ 1]))  # yesterday's image
            with self.assertRaisesRegex(ValueError, "not what the description and its specs make now"):
                checks.current_image(build.name, path)
            path.unlink()
            with self.assertRaisesRegex(ValueError, "is absent"):
                checks.current_image(build.name, path)


class DocumentTests(unittest.TestCase):
    def test_the_documents_do_not_promise_the_pinned_label_or_sha256_for_a_release(self) -> None:
        build = pinned_description(PATHS)
        text = readme.pinned_block(PATHS, ROOT)
        self.assertNotIn(f"EPM2Mod {build.label}", text)
        self.assertIn("the day of the release", text)
        self.assertIn("Pinned build as tested", text)


if __name__ == "__main__":
    unittest.main()

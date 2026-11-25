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
            (Path(folder) / fwmap.FILES[-1]).write_text("x")
            self.assertEqual(self.check(folder).returncode, 0)
        self.assertEqual(fwmap.FILES[-1], "tasks.tsv")  # what build writes last, and emulator/liveview.py reads


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

    def test_no_result_is_kept(self) -> None:
        self.assertFalse(hasattr(checks, "CACHE"))


class DocumentTests(unittest.TestCase):
    def test_the_documents_do_not_promise_the_pinned_label_or_sha256_for_a_release(self) -> None:
        build = pinned_description(PATHS)
        text = readme.pinned_block(PATHS, ROOT)
        self.assertNotIn(f"EPM2Mod {build.label}", text)
        self.assertIn("the day of the release", text)
        self.assertIn("Pinned build as tested", text)


if __name__ == "__main__":
    unittest.main()

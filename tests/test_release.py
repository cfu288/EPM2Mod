"""Tests of the release zip, ``epm2mod.release``.

    uv run python -m unittest discover -s tests

The tests need the built app page (``npm run build:app`` in web/); ``FromTheZipTests`` also needs the stock firmware.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT  # noqa: E402

from epm2mod import release, stock  # noqa: E402
from epm2mod.builds import pinned_description  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_APP = (ROOT / "src" / "epm2mod" / "app" / "index.html").is_file()
HAVE_STOCK = stock.stock_path(PATHS).is_file()


@unittest.skipUnless(HAVE_APP, "needs the built app page (npm run build:app)")
class ZipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.zip = release.make_release(PATHS, Path(self.folder.name))
        self.top = f"EPM2Mod-{pinned_description(PATHS).name}/"

    def tearDown(self) -> None:
        self.folder.cleanup()

    def test_it_holds_the_pinned_build_and_no_firmware(self) -> None:
        with zipfile.ZipFile(self.zip) as archive:
            names = archive.namelist()
        self.assertTrue(all(name.startswith(self.top) for name in names))
        inside = {name[len(self.top) :] for name in names}
        for spec in pinned_description(PATHS).specs:
            self.assertIn(spec, inside)
        for name in (
            "pinned-build.json",
            "looks/film-records.json",
            "src/epm2mod/__main__.py",
            "src/epm2mod/app/index.html",
            "Start (Mac).command",
            "Start (Windows).bat",
        ):
            self.assertIn(name, inside)
        self.assertEqual([name for name in inside if name.lower().endswith(".bin")], [])
        self.assertEqual([name for name in inside if "__pycache__" in name], [])

    def test_the_launchers_are_programs_and_the_batch_file_has_crlf(self) -> None:
        with zipfile.ZipFile(self.zip) as archive:
            for info in archive.infolist():
                mode = (info.external_attr >> 16) & 0o777
                want = (
                    0o755
                    if info.filename[len(self.top) :] in release.LAUNCHERS
                    else 0o644
                )
                self.assertEqual(mode, want, info.filename)
            batch = archive.read(self.top + "Start (Windows).bat")
        self.assertIn(b"\r\n", batch)
        self.assertNotIn(b"\n", batch.replace(b"\r\n", b""))

    def test_the_same_files_give_the_same_zip(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            again = release.make_release(PATHS, Path(other))
            self.assertEqual(again.read_bytes(), self.zip.read_bytes())


@unittest.skipUnless(
    HAVE_APP and HAVE_STOCK, "needs the built app page and the stock firmware"
)
class FromTheZipTests(unittest.TestCase):
    def test_the_unpacked_release_makes_the_pinned_build(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            archive = release.make_release(PATHS, Path(folder))
            with zipfile.ZipFile(archive) as unpack:
                unpack.extractall(folder)
            top = Path(folder) / f"EPM2Mod-{pinned_description(PATHS).name}"
            local = stock.stock_path(RepoPaths(top))
            local.parent.mkdir(parents=True)
            shutil.copyfile(stock.stock_path(PATHS), local)
            env = {
                key: value for key, value in os.environ.items() if key != "EPM2MOD_ROOT"
            }
            done = subprocess.run(
                [sys.executable, "-m", "epm2mod", "make"],
                cwd=top,
                env={**env, "PYTHONPATH": str(top / "src")},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn(str(pinned_description(PATHS).sha256), done.stdout)
            self.assertTrue(
                (top / "build" / "card" / "DCOLYMP" / "E1019999.BIN").is_file()
            )


if __name__ == "__main__":
    unittest.main()

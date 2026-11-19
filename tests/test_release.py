"""Tests of the release zip, ``epm2mod.release``.

    uv run python -m unittest discover -s tests

The tests need the built app page (``npm run build:app`` in web/); ``FromTheZipTests`` also needs the stock firmware.
"""

from __future__ import annotations

import json
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

from epm2mod import cards, catalogue, release, stock  # noqa: E402
from epm2mod.builds import pinned_description  # noqa: E402
from epm2mod.errors import BuildError  # noqa: E402
from epm2mod.paths import MANIFEST, RELEASE_KEY, RepoPaths  # noqa: E402

#: The files of the release folder that are programs.
LAUNCHERS = {"start.sh", "Start (Mac).command", "start.ps1"}

PATHS = RepoPaths(ROOT)
HAVE_APP = (ROOT / "src" / "epm2mod" / "app" / "index.html").is_file()
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()


@unittest.skipUnless(HAVE_APP, "needs the built app page (npm run build:app)")
class ZipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.zip = release.make_release(
            PATHS, Path(self.folder.name), "2026.11.18-rc.1"
        )
        self.top = "EPM2Mod-2026.11.18-rc.1/"

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
            "data/pinned-build.json",
            "epm2mod.json",
            "data/films/film-records.json",
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
                    if info.filename[len(self.top) :] in LAUNCHERS
                    else 0o644
                )
                self.assertEqual(mode, want, info.filename)
            batch = archive.read(self.top + "Start (Windows).bat")
        self.assertIn(b"\r\n", batch)
        self.assertNotIn(b"\n", batch.replace(b"\r\n", b""))

    def test_the_manifest_names_the_release_and_what_it_holds(self) -> None:
        with zipfile.ZipFile(self.zip) as archive:
            inside = {name[len(self.top) :] for name in archive.namelist()}
            manifest = json.loads(archive.read(self.top + MANIFEST))
        self.assertEqual(manifest[RELEASE_KEY], "2026.11.18-rc.1")
        self.assertEqual(
            set(manifest) - {RELEASE_KEY},
            {"pinned", "builds", "specs", "label_spec", "film_records", "cache", "app"},
        )
        for key in ("pinned", "film_records", "label_spec"):
            self.assertIn(manifest[key], inside, key)
        for key in ("builds", "specs", "app"):
            self.assertTrue(
                any(name.startswith(manifest[key] + "/") for name in inside), key
            )
        self.assertEqual(manifest["cache"], PATHS.relative(PATHS.cache_folder))

    def test_the_version_is_a_date(self) -> None:
        self.assertEqual(self.zip.name, "EPM2Mod-2026.11.18-rc.1.zip")
        for bad in ("card-looks-4", "0.1.0", "2026.11.18-final", "../x"):
            with self.assertRaises(BuildError, msg=bad):
                release.make_release(PATHS, Path(self.folder.name), bad)

    def test_the_same_files_give_the_same_zip(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            again = release.make_release(PATHS, Path(other), "2026.11.18-rc.1")
            self.assertEqual(again.read_bytes(), self.zip.read_bytes())


@unittest.skipUnless(
    HAVE_APP and HAVE_STOCK, "needs the built app page and the stock firmware"
)
class FromTheZipTests(unittest.TestCase):
    def test_the_unpacked_release_installs_the_pinned_build(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            archive = release.make_release(PATHS, Path(folder), "2026.11.18")
            with zipfile.ZipFile(archive) as unpack:
                unpack.extractall(folder)
            top = Path(folder) / "EPM2Mod-2026.11.18"
            local = stock.stock_path(catalogue.locate(project=top), stock.EPM2_V16)
            local.parent.mkdir(parents=True)
            shutil.copyfile(stock.stock_path(PATHS, stock.EPM2_V16), local)
            card = Path(folder) / "card"
            (card / "DCIM").mkdir(parents=True)
            env = dict(os.environ)
            env.update({"PYTHONPATH": str(top / "src"), cards.TEST_CARDS_ENV: str(card)})

            def run(*argv: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, "-m", "epm2mod", *argv],
                    cwd=top,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )

            done = run("install", "--card", str(card), "--json")
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            files = json.loads(done.stdout)["files"]
            self.assertEqual(files[0]["sha256"], pinned_description(PATHS).sha256)
            self.assertTrue((card / "DCOLYMP" / "E1019999.BIN").is_file())
            self.assertFalse((card / "EPM2LOOK.BIN").exists())  # no --film
            self.assertFalse((top / "build").exists())
            self.assertEqual(run("inspect", "--card", str(card)).returncode, 0)
            self.assertEqual(run("make", "x").returncode, 6)


if __name__ == "__main__":
    unittest.main()

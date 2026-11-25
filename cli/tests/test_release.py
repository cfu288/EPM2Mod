"""Tests of the release zip, ``epm2mod.release``.

    uv run python -m unittest discover -s cli/tests

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

import support  # noqa: E402
from support import ROOT, write_manifest  # noqa: E402

from epm2mod import builds, cards, catalogue, release, stock  # noqa: E402
from epm2mod.builds import pinned_description  # noqa: E402
from epm2mod.errors import BuildError, NotFoundError  # noqa: E402
from epm2mod.paths import MANIFEST, RELEASE_KEY, RepoPaths  # noqa: E402

#: The files of the release folder that are programs.
LAUNCHERS = {"start.sh", "Start (Mac).command", "start.ps1"}

PATHS = RepoPaths(ROOT)
HAVE_APP = (ROOT / "cli" / "src" / "epm2mod" / "app" / "index.html").is_file()
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()


@support.needs(HAVE_APP, support.APP_NEEDED)
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
            "cli/src/epm2mod/__main__.py",
            "cli/src/epm2mod/app/index.html",
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


class VersionTests(unittest.TestCase):
    def test_a_version_may_name_the_build_it_holds(self) -> None:
        cases = {
            "2026.11.20": None,
            "2026.11.20.2": None,
            "2026.11.20-rc.3": None,
            "2026.11.20-dev": None,
            "2026.11.20-pana-ring-probe.1": "pana-ring-probe",
            "2026.11.20-rc-probe.2": "rc-probe",
            "2026.11.20.2-x2.10": "x2",
        }
        for version, build in cases.items():
            self.assertEqual(release.version_build(version), build, version)

    def test_a_bad_build_name_or_number_is_refused(self) -> None:
        for bad in (
            "2026.11.20-dev.1",  # dev and rc are never build names
            "2026.11.20-rc.x",
            "2026.11.20-Probe.1",
            "2026.11.20-probe_x.1",
            "2026.11.20-a.b.1",
            "2026.11.20--probe.1",
            "2026.11.20-probe",
            "2026.11.20-probe.0",
        ):
            with self.assertRaises(BuildError, msg=bad):
                release.check_version(bad)


class NamedBuildTests(unittest.TestCase):
    """The data of a release whose version names a build, in a repository with no pinned build."""

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.paths = RepoPaths(write_manifest(Path(folder.name)))
        for path in (self.paths.film_records, self.paths.specs / "a.json"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}")
        self.probe = builds.BuildDescription(
            "probe", "A probe", ("data/specs/a.json",), "ab" * 32, "2026-11-20",
            stock=stock.EPM2_V16.file_name,
        )  # fmt: skip
        builds.save_description(self.paths, self.probe)
        untested = builds.BuildDescription(
            "untested", "No test", ("data/specs/a.json",), stock=stock.EPM2_V16.file_name
        )  # fmt: skip
        builds.save_description(self.paths, untested)

    def test_the_release_holds_the_named_build_and_pins_it(self) -> None:
        self.assertFalse(self.paths.pinned.exists())
        files = dict(release.data_files(self.paths, "2026.11.20-probe.1"))
        self.assertIn("data/builds/probe.json", files)
        self.assertIn("data/specs/a.json", files)
        self.assertNotIn("data/builds/untested.json", files)
        pointer = json.loads(files[self.paths.relative(self.paths.pinned)])
        self.assertEqual(pointer, {"build": "data/builds/probe.json"})
        builds.pin(self.paths, self.probe)  # the same build, pinned: the same files
        pinned = dict(release.data_files(self.paths, "2026.11.20"))
        self.assertEqual(
            {k: v for k, v in files.items() if k != MANIFEST},
            {k: v for k, v in pinned.items() if k != MANIFEST},
        )

    def test_an_untested_or_unknown_build_is_refused(self) -> None:
        with self.assertRaises(BuildError):
            release.data_files(self.paths, "2026.11.20-untested.1")
        with self.assertRaises(NotFoundError):
            release.data_files(self.paths, "2026.11.20-none.1")


@support.needs(HAVE_APP, support.APP_NEEDED)
@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
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
            env.update({"PYTHONPATH": str(top / "cli" / "src"), cards.TEST_CARDS_ENV: str(card)})

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

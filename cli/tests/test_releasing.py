"""Tests of starting a release, ``epm2mod.releasing``, and the feature-list check of ``epm2mod.readme``.

    uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT, write_manifest  # noqa: E402

from epm2mod import builds, cli, readme, releasing, stock  # noqa: E402
from epm2mod.errors import BuildError  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402
from epm2mod.releasing import next_version, release_notes  # noqa: E402


class NextVersionTests(unittest.TestCase):
    def test_the_first_test_release_of_a_day_is_rc_1(self) -> None:
        self.assertEqual(next_version("2026.11.20", ["v2026.11.19-rc.1"], final=False), "2026.11.20-rc.1")

    def test_the_next_test_release_counts_up_from_the_highest(self) -> None:
        tags = ["v2026.11.19-rc.1", "v2026.11.19-rc.3", "v2026.11.19-rc.2", "v2026.11.18-rc.9"]
        self.assertEqual(next_version("2026.11.19", tags, final=False), "2026.11.19-rc.4")

    def test_a_final_release_is_the_date(self) -> None:
        self.assertEqual(next_version("2026.11.19", ["v2026.11.19-rc.1"], final=True), "2026.11.19")

    def test_a_final_release_is_tagged_once(self) -> None:
        with self.assertRaises(BuildError):
            next_version("2026.11.19", ["v2026.11.19"], final=True)

    def test_a_named_build_counts_its_own_releases(self) -> None:
        tags = ["v2026.11.20-rc.5", "v2026.11.20-probe.2", "v2026.11.20-probe-2.7", "v2026.11.19-probe.9"]
        self.assertEqual(next_version("2026.11.20", tags, final=False, build="probe"), "2026.11.20-probe.3")
        self.assertEqual(next_version("2026.11.20", tags, final=False, build="other"), "2026.11.20-other.1")
        self.assertEqual(next_version("2026.11.20", tags, final=False), "2026.11.20-rc.6")


class PlanTests(unittest.TestCase):
    """``release --build``: the checks and the notes for a named build, with git, the documents and CI faked."""

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.paths = RepoPaths(write_manifest(Path(folder.name)))
        label_spec = self.paths.relative(self.paths.label_spec)
        for name, sha, date in (("probe", "ab" * 32, "2026-11-20"), ("untested", None, None)):
            builds.save_description(self.paths, builds.BuildDescription(
                name, f"The {name} build", ("data/specs/a.json", label_spec), sha, date,
                label="2026.11.20", stock=stock.EPM2_V16.file_name,
            ))  # fmt: skip
        self.paths.camera_log.mkdir(parents=True)
        (self.paths.camera_log / "2026-11-20-probe.md").write_text("sha256 " + "ab" * 32 + "\n")
        answers = {
            "status": "", "fetch": "", "rev-parse": "c0ffee", "describe": "v2026.11.20-rc.5",
            "tag": "v2026.11.20-rc.5 v2026.11.20-probe.1", "log": "feat: a probe\nchore: x",
        }  # fmt: skip
        for fake in (
            mock.patch.object(releasing, "_git", lambda paths, *args, given=None: answers[args[0]]),
            mock.patch.object(releasing, "_ci_problems", return_value=[]),
            mock.patch.object(readme, "is_current", return_value=True),
            mock.patch.object(readme, "feature_problems", return_value=[]),
        ):
            fake.start()
            self.addCleanup(fake.stop)

    def test_a_named_build_is_a_test_release_with_its_notes(self) -> None:
        self.assertFalse(self.paths.pinned.exists())  # the pinned build is not needed
        release, problems = releasing.plan(self.paths, final=False, build="probe")
        self.assertEqual(problems, [])
        assert release is not None
        self.assertEqual((release.tag, release.commit), ("v2026.11.20-probe.2", "c0ffee"))
        self.assertIn("Firmware: The probe build.", release.notes)
        self.assertIn("- feat: a probe\n", release.notes)
        self.assertIn("Firmware sha256 `" + "ab" * 32 + "`.", release.notes)

    def test_an_untested_build_is_not_released(self) -> None:
        self.assertEqual(
            releasing.plan(self.paths, final=False, build="untested"),
            (None, ["the build untested has no camera test"]),
        )

    def test_a_named_build_is_never_a_final_release(self) -> None:
        argv = ["--project", str(self.paths.root), "release", "--build", "probe", "--final", "--dry-run"]
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(argv), 2)
        self.assertIn("--build makes a test release", err.getvalue())


class ReleaseNotesTests(unittest.TestCase):
    def test_the_notes_name_the_version_build_changes_and_sha(self) -> None:
        notes = release_notes("2026.11.19-rc.2", "Film looks", "ab" * 32, "v2026.11.19-rc.1", ["feat: x"])
        self.assertTrue(notes.startswith("EPM2Mod 2026.11.19-rc.2\n"))
        self.assertIn("Firmware: Film looks.", notes)
        self.assertIn("Changes since v2026.11.19-rc.1:\n\n- feat: x\n", notes)
        self.assertIn("Firmware sha256 `" + "ab" * 32 + "`.", notes)

    def test_no_changes_no_change_list(self) -> None:
        self.assertNotIn("Changes", release_notes("2026.11.19", "Looks", "ab" * 32, None, []))


class FeatureListTests(unittest.TestCase):
    def test_the_repository_lists_every_feature_everywhere(self) -> None:
        self.assertEqual(readme.feature_problems(RepoPaths(ROOT)), [])

    def test_a_guide_missing_from_the_readme_and_the_site_is_found(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = write_manifest(Path(folder))
            (root / "docs" / "guide").mkdir(parents=True)
            (root / "docs" / "guide" / "level-gauge.md").write_text("# Level gauge\n")
            (root / "docs" / "guide" / "new-thing.md").write_text("# New\n")
            (root / "README.md").write_text("| [Level gauge](docs/guide/level-gauge.md) |\n")
            site = RepoPaths(root).site_features
            site.parent.mkdir(parents=True)
            site.write_text("export const features = [{ id: 'film-looks' }]\n")
            problems = readme.feature_problems(RepoPaths(root))
        self.assertIn("README.md does not link docs/guide/new-thing.md", problems)
        self.assertIn("docs/guide/new-thing.md is not in readme.SITE_IDS: add its site id, or None", problems)
        self.assertIn("web/apps/site/src/features.ts has no feature 'level'", problems)


if __name__ == "__main__":
    unittest.main()


class ReleaseTagTests(unittest.TestCase):
    def test_named_build_tags_are_not_releases_of_the_pinned_build(self):
        from fnmatch import fnmatchcase

        def matches(tag):
            return any(fnmatchcase(tag, pattern) for pattern in releasing.RELEASE_TAGS)

        for tag in ("v2026.11.19", "v2026.11.19.2", "v2026.11.20-rc.5"):
            self.assertTrue(matches(tag), tag)
        for tag in ("v2026.11.20-pana-ring-probe.1", "v2026.11.20-dev"):
            self.assertFalse(matches(tag), tag)

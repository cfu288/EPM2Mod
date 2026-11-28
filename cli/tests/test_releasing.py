"""Tests of starting a release, ``epm2mod.releasing``, and the feature-list check of ``epm2mod.readme``.

    uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
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
    """``release --build``: the checks and the notes for a named build, with git and the documents faked."""

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.paths = RepoPaths(write_manifest(Path(folder.name)))
        self.paths.release_notes.parent.mkdir(parents=True)
        self.paths.release_notes.write_text("**Install**\n", encoding="utf-8")
        label_spec = self.paths.relative(self.paths.label_spec)
        for name, sha, date in (("probe", "ab" * 32, "2026-11-20"), ("untested", None, None)):
            builds.save_description(self.paths, builds.BuildDescription(
                name, f"The {name} build", ("data/specs/a.json", label_spec), sha, date,
                label="2026.11.20", stock=stock.EPM2_V16.file_name,
            ))  # fmt: skip
        answers = {
            "status": "", "fetch": "", "rev-parse": "c0ffee", "describe": "v2026.11.20-rc.5",
            "tag": "v2026.11.20-rc.5 v2026.11.20-probe.9 v2026.11.25-probe.1", "log": "feat: a probe\nchore: x",
        }  # fmt: skip
        for fake in (
            mock.patch.object(releasing, "_git", lambda paths, *args: answers[args[0]]),
            mock.patch.object(releasing, "stamp", self.stamp),
            mock.patch.object(releasing, "check_free_space", lambda paths, build: self.checked.append(build.label)),
            mock.patch.object(releasing, "check_in_emulator", lambda paths, image: self.checked.append(image.name)),
            mock.patch.object(readme, "is_current", return_value=True),
            mock.patch.object(readme, "feature_problems", return_value=[]),
        ):
            fake.start()
            self.addCleanup(fake.stop)

    def stamp(self, paths: RepoPaths, build: builds.BuildDescription, day: str) -> tuple[builds.BuildDescription, bytes]:
        """Stand in for ``release.stamp``: the build with the label ``day`` and another sha256."""
        return dataclasses.replace(build, label=day, sha256="cd" * 32), b"image"

    def test_a_named_build_is_a_test_release_with_its_notes(self) -> None:
        self.checked: list[str] = []
        self.assertFalse(self.paths.pinned.exists())  # the pinned build is not needed
        release, problems = releasing.plan(self.paths, final=False, build="probe", day="2026.11.25")
        self.assertEqual(problems, [])
        assert release is not None
        self.assertEqual((release.tag, release.commit), ("v2026.11.25-probe.2", "c0ffee"))
        # the release holds the build with the day of the release as its label, checked as a candidate is
        self.assertIn("Firmware: EPM2Mod 2026.11.25, sha256 `" + "cd" * 32 + "`.", release.notes)
        self.assertIn("camera-tested build (sha256 `" + "ab" * 32 + "`)", release.notes)
        self.assertEqual(self.checked, ["2026.11.25", "probe.BIN"])
        self.assertNotIn("The probe build.", release.notes)  # the build description is not in the notes
        self.assertIn("- a probe\n", release.notes)
        self.assertTrue(release.notes.endswith("\n**Install**\n"))  # release/NOTES.md comes last

    def test_a_build_with_the_label_of_the_day_is_released_as_tested_and_still_checked(self) -> None:
        self.checked = []
        with mock.patch.object(releasing, "stamp", lambda paths, build, day: (build, b"image")):
            release, problems = releasing.plan(
                self.paths, final=False, build="probe", day="2026.11.25"
            )
        self.assertEqual(problems, [])
        assert release is not None
        self.assertEqual(release.sha256, "ab" * 32)
        self.assertNotIn("camera-tested build", release.notes)
        self.assertEqual(self.checked, ["2026.11.20", "probe.BIN"])  # the start-up and load-order checks ran

    def test_a_failed_start_up_check_stops_the_release(self) -> None:
        def failed(paths: RepoPaths, image: Path) -> list[str]:
            raise BuildError("boot-test: TIMES MOVED: 2 time stamp(s)\nboot-test failed")

        self.checked = []
        with mock.patch.object(releasing, "check_in_emulator", failed):
            release, problems = releasing.plan(self.paths, final=False, build="probe", day="2026.11.25")
        self.assertIsNone(release)
        self.assertEqual(len(problems), 1)
        self.assertIn("TIMES MOVED", problems[0])

    def test_the_hint_is_the_command_for_the_release_that_was_planned(self) -> None:
        self.checked = []
        argv = ["--project", str(self.paths.root), "release", "--build", "probe"]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(cli.main(argv), 0, err.getvalue())
        self.assertIn("release -f kind=rc -f build=probe -f dry_run=false", err.getvalue())

    def test_the_hint_passes_the_summary_quoted(self) -> None:
        self.checked = []
        argv = ["--project", str(self.paths.root), "release", "--build", "probe", "--summary", "It's new."]
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(cli.main(argv), 0, err.getvalue())
        self.assertIn("""-f build=probe -f summary='It'"'"'s new.' -f dry_run=false""", err.getvalue())
        self.assertTrue(out.getvalue().startswith("EPM2Mod 2026.11"))  # the preview shows the title
        self.assertIn("\nIt's new.\n\n", out.getvalue())

    def test_the_json_of_a_plan_that_is_not_ready_has_no_prerelease(self) -> None:
        argv = ["--project", str(self.paths.root), "release", "--build", "untested", "--json"]
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(argv), 1)
        document = json.loads(out.getvalue())
        self.assertEqual((document["ready"], document["prerelease"]), (False, None))

    def test_an_untested_build_is_not_released(self) -> None:
        self.assertEqual(
            releasing.plan(self.paths, final=False, build="untested"),
            (None, ["the build untested has no camera test"]),
        )

    def test_a_named_build_is_never_a_final_release(self) -> None:
        argv = ["--project", str(self.paths.root), "release", "--build", "probe", "--final"]
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(argv), 2)
        self.assertIn("--build makes a test release", err.getvalue())


class ReleaseNotesTests(unittest.TestCase):
    def test_the_notes_name_the_changes_and_the_firmware_without_a_title(self) -> None:
        notes = release_notes("2026.11.20", "ab" * 32, "v2026.11.25-rc.1", ["feat: x", "fix(films): y (#13)"])
        self.assertNotIn("EPM2Mod 2026.11.25", notes)  # the release page shows the title
        self.assertTrue(notes.startswith("Changes since v2026.11.25-rc.1:\n"))
        self.assertIn("Firmware: EPM2Mod 2026.11.20, sha256 `" + "ab" * 32 + "`.\n", notes)
        self.assertIn("Changes since v2026.11.25-rc.1:\n\n- x\n- y (#13)\n", notes)

    def test_the_notes_of_a_stamped_build_give_both_sha256(self) -> None:
        notes = release_notes("2026.11.26", "cd" * 32, None, [], tested=("ab" * 32, "2026.11.20"))
        self.assertIn(
            "Firmware: EPM2Mod 2026.11.26, sha256 `" + "cd" * 32 + "`. It is the camera-tested build (sha256 `"
            + "ab" * 32 + "`) with the release's date on the Firmware screen.\n",
            notes,
        )

    def test_the_summary_comes_first_and_the_install_steps_last(self) -> None:
        notes = release_notes(
            "2026.11.28", "ab" * 32, None, ["feat: x"], summary=" New dial. \n", install="**Install**\n"
        )
        self.assertTrue(notes.startswith("New dial.\n\nChanges:\n"))
        self.assertTrue(notes.endswith("`.\n\n**Install**\n"))

    def test_no_summary_no_empty_paragraph(self) -> None:
        self.assertTrue(release_notes("2026.11.28", "ab" * 32, None, []).startswith("Firmware"))

    def test_no_changes_no_change_list(self) -> None:
        self.assertNotIn("Changes", release_notes("2026.11.19", "ab" * 32, None, []))


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
        self.assertIn("web/apps/site/src/features.ts has no feature 'level-gauge'", problems)


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

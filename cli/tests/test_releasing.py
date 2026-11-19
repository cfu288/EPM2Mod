"""Tests of starting a release, ``epm2mod.releasing``, and the feature-list check of ``epm2mod.readme``.

    uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT, write_manifest  # noqa: E402

from epm2mod import readme  # noqa: E402
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

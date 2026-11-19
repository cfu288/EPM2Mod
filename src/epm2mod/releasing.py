"""Start a release (``epm2mod release``): check, name and tag the pinned build.

The tag is the release. ``.github/workflows/release.yml`` sees it, makes the
zip with ``epm2mod package``, tests it on three systems and publishes it with
the tag's message as the release notes. This module only decides whether the
repository is ready, which version comes next, and what the notes say.

The version is the pinned build's label, the date its Firmware screen shows:
``2026.11.19`` for a final release, ``2026.11.19-rc.N`` for a test release, N
one more than the highest existing for that date.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import readme
from .builds import pinned_description
from .errors import BuildError
from .fileio import read_text
from .paths import RepoPaths

#: The workflows whose runs on the release commit must have passed.
WORKFLOWS = ("release.yml", "web.yml")


def next_version(label: str, tags: list[str], final: bool) -> str:
    """Return the next calendar version for a build labelled ``label``.

    Args:
        label: the build's label, like ``2026.11.19``.
        tags: the existing tag names, like ``v2026.11.19-rc.1``.
        final: True for a release for everyone, False for a test release.

    Raises:
        BuildError: if the final release of that date is already tagged.
    """
    day = label
    if final:
        if f"v{day}" in tags:
            raise BuildError(f"v{day} is already tagged")
        return day
    numbers = [
        int(m.group(1))
        for tag in tags
        if (m := re.fullmatch(rf"v{re.escape(day)}-rc\.(\d+)", tag))
    ]
    return f"{day}-rc.{max(numbers, default=0) + 1}"


def release_notes(
    version: str, what: str, sha256: str, previous: str | None, changes: list[str]
) -> str:
    """Return the release notes: what is in the build and what changed.

    Args:
        version: the calendar version.
        what: the pinned build's description.
        sha256: the firmware file's SHA-256.
        previous: the tag of the release before, if any.
        changes: the subjects of the feat and fix commits since ``previous``.
    """
    lines = [f"EPM2Mod {version}", "", f"Firmware: {what}.", ""]
    if changes:
        lines += [f"Changes since {previous}:" if previous else "Changes:", ""]
        lines += [f"- {change}" for change in changes]
        lines.append("")
    lines.append(f"Firmware sha256 `{sha256}`.")
    return "\n".join(lines) + "\n"


def _git(paths: RepoPaths, *args: str) -> str:
    """Run git in the repository and return its output, stripped."""
    done = subprocess.run(
        ["git", *args], cwd=paths.root, capture_output=True, text=True, check=False
    )
    if done.returncode:
        raise BuildError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout.strip()


def _ci_problems(paths: RepoPaths, commit: str) -> list[str]:
    """Return why CI does not count as passed for ``commit``, if it doesn't.

    Each workflow runs on main only for the paths it watches, so the commit
    itself may have no run (a change to the documents only). What counts is the
    newest run of each workflow on main: it must be finished, passed, and on
    ``commit`` or one of its ancestors.
    """
    gh = shutil.which("gh")
    if gh is None:
        return ["the GitHub command gh is not installed: cannot check the CI runs"]
    problems = []
    for workflow in WORKFLOWS:
        done = subprocess.run(
            [gh, "run", "list", "--workflow", workflow, "--branch", "main",
             "--event", "push", "--json", "conclusion,status,headSha", "--limit", "1"],
            cwd=paths.root, capture_output=True, text=True, check=False,
        )  # fmt: skip
        runs = json.loads(done.stdout) if done.returncode == 0 else []
        if not runs:
            problems.append(f"{workflow}: no run on main found")
            continue
        run = runs[0]
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", run["headSha"], commit],
            cwd=paths.root, capture_output=True, check=False,
        )  # fmt: skip
        if ancestor.returncode != 0:
            problems.append(
                f"{workflow}: the newest run is not on this commit's history"
            )
        elif run["status"] != "completed":
            problems.append(
                f"{workflow}: the run for {run['headSha'][:7]} is {run['status']}"
            )
        elif run["conclusion"] != "success":
            problems.append(
                f"{workflow}: the run for {run['headSha'][:7]} {run['conclusion']}"
            )
    return problems


@dataclass(frozen=True)
class Plan:
    """A release that is ready to tag.

    Attributes:
        tag: the tag name, like ``v2026.11.19-rc.1``.
        commit: the commit to tag.
        notes: the tag message, which the workflow publishes as the notes.
    """

    tag: str
    commit: str
    notes: str


def plan(paths: RepoPaths, final: bool) -> tuple[Plan | None, list[str]]:
    """Check the repository and return the release to make, or the problems."""
    problems: list[str] = []
    pinned = pinned_description(paths)
    if pinned.sha256 is None or pinned.camera_tested is None:
        problems.append(f"the pinned build {pinned.name} has no camera test")
        return None, problems
    if pinned.label is None:
        problems.append(f"the pinned build {pinned.name} has no label")
        return None, problems
    if pinned.sha256 not in read_text(paths.resolve("docs/camera-log.md")):
        problems.append(f"docs/camera-log.md has no row for {pinned.sha256[:8]}")
    if _git(paths, "status", "--porcelain", "--untracked-files=no"):
        problems.append("the working tree has changes: commit or stash them")
    _git(paths, "fetch", "--quiet", "--tags", "origin")
    commit = _git(paths, "rev-parse", "HEAD")
    if commit != _git(paths, "rev-parse", "origin/main"):
        problems.append("HEAD is not origin/main: push, or check out main")
    if not readme.is_current(paths):
        problems.append(
            "the generated documents are out of date: run 'epm2mod generate'"
        )
    problems += [f"feature list: {p}" for p in readme.feature_problems(paths)]
    problems += _ci_problems(paths, commit)
    tags = _git(paths, "tag", "--list", "v*").split()
    try:
        version = next_version(pinned.label, tags, final)
    except BuildError as error:
        return None, problems + [str(error)]
    if problems:
        return None, problems
    try:
        previous: str | None = _git(
            paths, "describe", "--tags", "--abbrev=0", "--match", "v*", "HEAD"
        )
    except BuildError:
        previous = None
    since = f"{previous}..HEAD" if previous else "HEAD"
    subjects = _git(paths, "log", "--format=%s", since).splitlines()
    changes = [s for s in subjects if re.match(r"(feat|fix)\b", s)]
    notes = release_notes(version, pinned.what, pinned.sha256, previous, changes)
    return Plan(f"v{version}", commit, notes), []


def tag(paths: RepoPaths, release: Plan, push: bool) -> None:
    """Create the annotated tag of ``release``; push it if ``push``."""
    message = Path(paths.output, f"{release.tag}.notes.md")
    message.parent.mkdir(parents=True, exist_ok=True)
    message.write_text(release.notes, encoding="utf-8")
    _git(paths, "tag", "-a", release.tag, "-F", str(message), release.commit)
    if push:
        _git(paths, "push", "origin", release.tag)

"""Start a release (``epm2mod release``): check, name and tag the pinned build.

The tag is the release. The release workflow sees it, makes the
zip with ``epm2mod package``, tests it on three systems and publishes it with
the tag's message as the release notes. This module only decides whether the
repository is ready, which version comes next, and what the notes say.

The version is the pinned build's label, the date its Firmware screen shows:
``2026.11.19`` for a final release, ``2026.11.19-rc.N`` for a test release, N
one more than the highest existing for that date. A test release of another
camera-tested build (``--build NAME``) is ``LABEL-NAME.N``, with that build's label.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass

from . import readme
from .builds import pinned_description
from .errors import BuildError
from .fileio import read_text
from .paths import RepoPaths
from .release import check_version

#: The tags of the pinned build's releases (final, second of a day, rc), as git globs. A test release of a named
#: build (``vLABEL-NAME.N``) matches none, so the next release's changes are counted from the last of these.
RELEASE_TAGS = ("v????.??.??", "v????.??.??.*", "v????.??.??-rc.*")


def next_version(
    label: str, tags: list[str], final: bool, build: str | None = None
) -> str:
    """Return the next calendar version for a build labelled ``label``.

    Args:
        label: the build's label, like ``2026.11.19``.
        tags: the existing tag names, like ``v2026.11.19-rc.1``.
        final: True for a release for everyone, False for a test release.
        build: the name of the build of a test release that is not the pinned build.

    Raises:
        BuildError: if the final release of that date is already tagged.
    """
    day = label
    if final:
        if f"v{day}" in tags:
            raise BuildError(f"v{day} is already tagged")
        return day
    kind = build or "rc"
    numbers = [
        int(m.group(1))
        for tag in tags
        if (m := re.fullmatch(rf"v{re.escape(day)}-{re.escape(kind)}\.(\d+)", tag))
    ]
    return f"{day}-{kind}.{max(numbers, default=0) + 1}"


def release_notes(
    version: str, what: str, sha256: str, previous: str | None, changes: list[str]
) -> str:
    """Return the release notes: what is in the build and what changed.

    Args:
        version: the calendar version.
        what: the build's description.
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


def _git(paths: RepoPaths, *args: str, given: str | None = None) -> str:
    """Run git in the repository, with ``given`` on its standard input, and return its output, stripped."""
    done = subprocess.run(
        ["git", *args],
        cwd=paths.root,
        input=given,
        capture_output=True,
        text=True,
        check=False,
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
    for workflow in (path.name for path in paths.workflows):
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


def plan(
    paths: RepoPaths, final: bool, build: str | None = None
) -> tuple[Plan | None, list[str]]:
    """Check the repository and return the release to make, or the problems.

    ``build`` names the build of a test release in place of the pinned build.
    """
    problems: list[str] = []
    chosen = pinned_description(paths) if build is None else paths.build(build)
    which = "the pinned build" if build is None else "the build"
    if chosen.sha256 is None or chosen.camera_tested is None:
        problems.append(f"{which} {chosen.name} has no camera test")
        return None, problems
    if chosen.label is None:
        problems.append(f"{which} {chosen.name} has no label")
        return None, problems
    log = paths.camera_log
    if not any(chosen.sha256 in read_text(entry) for entry in sorted(log.glob("*.md"))):
        problems.append(f"{paths.relative(log)}/ has no file for {chosen.sha256[:8]}")
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
        version = next_version(chosen.label, tags, final, build)
        check_version(version)
    except BuildError as error:
        return None, problems + [str(error)]
    if problems:
        return None, problems
    try:
        matches = [arg for pattern in RELEASE_TAGS for arg in ("--match", pattern)]
        previous: str | None = _git(
            paths, "describe", "--tags", "--abbrev=0", *matches, "HEAD"
        )
    except BuildError:
        previous = None
    since = f"{previous}..HEAD" if previous else "HEAD"
    subjects = _git(paths, "log", "--format=%s", since).splitlines()
    changes = [s for s in subjects if re.match(r"(feat|fix)\b", s)]
    notes = release_notes(version, chosen.what, chosen.sha256, previous, changes)
    return Plan(f"v{version}", commit, notes), []


def tag(paths: RepoPaths, release: Plan, push: bool) -> None:
    """Create the annotated tag of ``release``; push it if ``push``."""
    _git(
        paths, "tag", "-a", release.tag, "-F", "-", release.commit, given=release.notes
    )
    if push:
        _git(paths, "push", "origin", release.tag)

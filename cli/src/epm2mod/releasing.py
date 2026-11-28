"""Plan a release (``epm2mod release``): check and name the next release of the pinned build.

The release workflow on GitHub (started by hand, ``workflow_dispatch``) runs
the hard checks and this, makes the zip with ``epm2mod package``, tests it on
three systems, and then publishes the GitHub release, which creates the tag. No
person pushes a tag. This module only decides whether the repository is ready,
which version comes next, and what the notes say.

The version is a calendar version: the day of the release in UTC, and a
number. ``2026.11.25-rc.N`` is a test release, N one more than the highest
existing tag of that day (1 for the first); ``2026.11.25`` is a final release.
A test release of another camera-tested build (``--build NAME``) is
``2026.11.25-NAME.N``.

The camera's Firmware screen shows the same date: the release holds the
camera-tested build with its label set to the day of the release
(``release.stamp``). That image is checked before it is released: it differs
from the tested one only in the date (``release.check_only_the_label_differs``),
and it passes the free-space and start-up checks. The notes give both sha256.
"""

from __future__ import annotations

import datetime
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import readme
from .builds import pinned_description
from .errors import BuildError, Epm2ModError
from .fileio import read_text, write_bytes
from .paths import RepoPaths
from .pipeline import check_free_space, check_in_emulator, no_stabilizer_image
from .release import check_version, stamp

#: The tags of the pinned build's releases (final, second of a day, rc), as git globs. A test release of a named
#: build (``vLABEL-NAME.N``) matches none, so the next release's changes are counted from the last of these.
RELEASE_TAGS = ("v????.??.??", "v????.??.??.*", "v????.??.??-rc.*")

#: The type and scope of a commit subject, which the notes leave out: "fix(films): x (#13)" becomes "x (#13)".
_TYPE = re.compile(r"^[a-z]+(\([^)]*\))?!?: ")


def next_version(
    day: str, tags: list[str], final: bool, build: str | None = None
) -> str:
    """Return the next calendar version for a release made on ``day``.

    Args:
        day: the day of the release in UTC, like ``2026.11.19``.
        tags: the existing tag names, like ``v2026.11.19-rc.1``.
        final: True for a release for everyone, False for a test release.
        build: the name of the build of a test release that is not the pinned build.

    Raises:
        BuildError: if the final release of that date is already tagged.
    """
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
    label: str,
    sha256: str,
    previous: str | None,
    changes: list[str],
    tested: tuple[str, str] | None = None,
    summary: str = "",
    install: str = "",
) -> str:
    """Return the release notes: the summary, the changes, the firmware and the install steps.

    The release page shows the title (``Plan.title``) above them, so the notes do not repeat it.

    Args:
        label: the build's label, which the camera's Firmware screen shows.
        sha256: the firmware file's SHA-256.
        previous: the tag of the release before, if any.
        changes: the subjects of the feat and fix commits since ``previous``.
        tested: the sha256 and the label of the camera-tested build, if the release holds it with another label.
        summary: what is new, in sentences that a person writes. It comes first.
        install: the install steps (the manifest's ``release_notes`` file). They come last.
    """
    lines: list[str] = []
    if summary.strip():
        lines += [summary.strip(), ""]
    if changes:
        lines += [f"Changes since {previous}:" if previous else "Changes:", ""]
        lines += [f"- {_TYPE.sub('', change)}" for change in changes]
        lines.append("")
    firmware = f"Firmware: EPM2Mod {label}, sha256 `{sha256}`."
    if tested is not None:
        firmware += (
            f" It is the camera-tested build (sha256 `{tested[0]}`) with the release's date on the"
            " Firmware screen."
        )
    lines += [firmware, ""]
    if install:
        lines += [install.rstrip("\n"), ""]
    return "\n".join(lines)


def _git(paths: RepoPaths, *args: str) -> str:
    """Run git in the repository and return its output, stripped."""
    done = subprocess.run(
        ["git", *args],
        cwd=paths.root,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode:
        raise BuildError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout.strip()


@dataclass(frozen=True)
class Plan:
    """A release that is ready to make.

    Attributes:
        tag: the tag name, like ``v2026.11.19-rc.1``.
        commit: the commit to tag.
        notes: the release notes.
        sha256: the sha256 of the firmware that the release installs.
    """

    tag: str
    commit: str
    notes: str
    sha256: str

    @property
    def title(self) -> str:
        """The title of the release page, like ``EPM2Mod 2026.11.19-rc.1``."""
        return f"EPM2Mod {self.tag[1:]}"


def plan(
    paths: RepoPaths,
    final: bool,
    build: str | None = None,
    day: str | None = None,
    summary: str = "",
) -> tuple[Plan | None, list[str]]:
    """Check the repository and return the release to make, or the problems.

    ``build`` names the build of a test release in place of the pinned build.
    ``day`` is the day of the release, like ``2026.11.25`` (default: today in UTC).
    ``summary`` is what is new, in sentences that a person writes. The notes show it under the title.
    """
    if day is None:
        day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y.%m.%d")
    problems: list[str] = []
    chosen = pinned_description(paths) if build is None else paths.build(build)
    which = "the pinned build" if build is None else "the build"
    if chosen.sha256 is None or chosen.camera_tested is None:
        problems.append(f"{which} {chosen.name} has no camera test")
        return None, problems
    if chosen.label is None:
        problems.append(f"{which} {chosen.name} has no label")
        return None, problems
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
    tags = _git(paths, "tag", "--list", "v*").split()
    try:
        version = next_version(day, tags, final, build)
        check_version(version)
    except BuildError as error:
        return None, problems + [str(error)]
    released, tested = chosen, None
    if not problems:
        # the image that is released, with the label of the day or as tested: checked here, on this computer
        try:
            released, image = stamp(paths, chosen, day)
            check_free_space(paths, released)
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / f"{released.name}.BIN"
                write_bytes(path, image, BuildError)
                check_in_emulator(paths, path)
                if released.no_stabilizer is not None:
                    variant = released.with_no_stabilizer()
                    check_free_space(paths, variant)
                    write_bytes(
                        path, no_stabilizer_image(paths, released)[0], BuildError
                    )
                    check_in_emulator(paths, path, variant.boot_differs)
            if released.sha256 != chosen.sha256:
                tested = (chosen.sha256, chosen.label)
        except Epm2ModError as error:
            problems.append(f"the build with the label {day}: {error}")
    if problems or released.sha256 is None or released.label is None:
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
    notes = release_notes(
        released.label,
        released.sha256,
        previous,
        changes,
        tested,
        summary,
        read_text(paths.release_notes, BuildError),
    )
    return Plan(f"v{version}", commit, notes, released.sha256), []

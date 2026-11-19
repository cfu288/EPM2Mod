"""The release zip (``epm2mod package``): what a user who doesn't code downloads.

The zip holds one folder, ``EPM2Mod-<version>/``, with what the commands for camera owners (``epm2mod install``,
``films``, ``restore``, ``inspect``, ``serve``) need for the pinned build, and nothing else:

- the package (``src/epm2mod``, with the built app page ``src/epm2mod/app``);
- the data (``data_files``): the pinned build description and its patch specs, the film records, and the marker
  ``paths.RELEASE_MARKER`` with the version, by which ``catalogue.locate`` knows a release folder;
- the launchers and their README (``release/``), and the licence files.

It never holds firmware: ``install`` downloads Olympus's file from OM Digital Solutions on the user's computer. A
file ending in ``.BIN`` stops the release.

The launchers get a pinned uv and a Python 3.12 from it into the folder's ``.uv``; the package needs only the
standard library, so it runs from ``src`` with no install step.
"""

from __future__ import annotations

import json
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path

from .builds import pinned_description
from .errors import BuildError
from .fileio import read_bytes
from .paths import RELEASE_MARKER, ROOT_MARKER, RepoPaths

#: The launchers, from ``release/``; the first three are run as programs.
LAUNCHERS = ("start.sh", "Start (Mac).command", "start.ps1")
#: The other files of ``release/``.
RELEASE_TEXTS = ("Start (Windows).bat", "README.txt")
#: The licence files of the repository.
LICENCES = ("LICENSE", "NOTICE.md")

#: The time stamp of every file in the zip, so that the same files give the same zip.
_STAMP = (2026, 1, 1, 0, 0, 0)


def data_files(paths: RepoPaths, version: str) -> list[tuple[str, bytes]]:
    """Return the data that the release's commands read: their path in the folder, and their content.

    These are the pinned build and its specs, the film records and the release marker, at the paths that
    ``catalogue.ReleaseLocator`` reads.

    Raises:
        BuildError: if a file is missing.
    """
    description = pinned_description(paths)
    sources = [
        (ROOT_MARKER, paths.pinned),
        (f"builds/{description.name}.json", paths.builds / f"{description.name}.json"),
        ("looks/film-records.json", paths.film_records),
    ]
    sources += [(spec, paths.resolve(spec)) for spec in description.specs]
    missing = [str(source) for _, source in sources if not source.is_file()]
    if missing:
        raise BuildError("missing for the release: " + ", ".join(missing))
    marker = json.dumps({"version": version}, indent=1) + "\n"
    files = [(name, read_bytes(source, BuildError)) for name, source in sources]
    return files + [(RELEASE_MARKER, marker.encode())]


def release_files(paths: RepoPaths, version: str) -> list[tuple[str, bytes]]:
    """Return the files of the release: their path in the folder, and their content.

    Raises:
        BuildError: if the app page is not built or a file is missing.
    """
    app = paths.root / "src" / "epm2mod" / "app"
    if not (app / "index.html").is_file():
        raise BuildError(
            f"{app}: the app page is not built. In web/: npm ci && npm run build:app"
        )
    sources = [(name, paths.root / name) for name in LICENCES]
    sources += [
        (name, paths.root / "release" / name) for name in LAUNCHERS + RELEASE_TEXTS
    ]
    sources += list(_package(paths.root / "src"))
    missing = [str(source) for _, source in sources if not source.is_file()]
    if missing:
        raise BuildError("missing for the release: " + ", ".join(missing))
    files = data_files(paths, version)
    files += [(name, read_bytes(source, BuildError)) for name, source in sources]
    firmware = [name for name, _ in files if name.lower().endswith(".bin")]
    if firmware:
        raise BuildError("a release never holds firmware: " + ", ".join(firmware))
    return sorted(files)


def _package(src: Path) -> Iterator[tuple[str, Path]]:
    """Yield the files of the package under ``src``: its code, its type marker and the app page."""
    for source in sorted((src / "epm2mod").rglob("*")):
        if source.is_file() and "__pycache__" not in source.parts:
            yield source.relative_to(src.parent).as_posix(), source


#: A release's version: calendar date (``2026.11.18``), a number for a second release that day (``.2``), and
#: ``-rc.N`` for a pre-release or ``-dev`` for a test build.
_VERSION = re.compile(r"^\d{4}\.\d{2}\.\d{2}(\.\d+)?(-rc\.\d+|-dev)?$")


def check_version(version: str) -> None:
    """Refuse a version that is not a calendar version.

    Raises:
        BuildError: if it is not.
    """
    if not _VERSION.match(version):
        raise BuildError(
            f"'{version}': a version is a date, like 2026.11.18 or 2026.11.18-rc.1"
        )


def zip_path(out: Path, version: str) -> Path:
    """Return the path of the release zip of ``version`` in the folder ``out``."""
    return out / f"EPM2Mod-{version}.zip"


def make_release(paths: RepoPaths, out: Path, version: str) -> Path:
    """Write the release zip ``EPM2Mod-<version>.zip`` into the folder ``out`` and return its path.

    Raises:
        BuildError: if the version is not a calendar version, a file is missing (``release_files``) or the zip
            can't be written.
    """
    check_version(version)
    name = f"EPM2Mod-{version}"
    target = zip_path(out, version)
    files = release_files(paths, version)
    try:
        out.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, data in files:
                info = zipfile.ZipInfo(f"{name}/{path}", _STAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = 0o755 if path in LAUNCHERS else 0o644
                info.external_attr = (
                    0o100000 | mode
                ) << 16  # a regular file and its permissions
                info.create_system = 3  # Unix, so that unzip tools keep the permissions
                archive.writestr(info, data)
    except OSError as error:
        raise BuildError(f"{target}: {error.strerror or error}") from None
    return target

"""The release zip (``epm2mod package``): what a user who doesn't code downloads.

The zip holds one folder, ``EPM2Mod-<version>/``, with what the commands for camera owners (``epm2mod install``,
``films``, ``restore``, ``inspect``, ``serve``) need for the pinned build, and nothing else:

- the package (``RepoPaths.package``, with the built app page ``RepoPaths.app``);
- the data (``data_files``): the pinned build description and its patch specs, the film records, and the release's
  manifest (``paths.MANIFEST``), which names these locations and holds the version under ``paths.RELEASE_KEY``, by
  which ``catalogue.locate`` knows a release folder;
- the files of ``RepoPaths.release_files`` at the top: the launchers, their README and the licence files. A file that
  is a program in the checkout is a program in the zip.

Every file but those at the top has the path it has in the checkout.

It never holds firmware: ``install`` downloads Olympus's file from OM Digital Solutions on the user's computer. A
file ending in ``.BIN`` stops the release.

The launchers get a pinned uv and a Python 3.12 from it into the release folder; the package needs only the
standard library, so it runs from the folder above the package with no install step.
"""

from __future__ import annotations

import json
import re
import stat
import zipfile
from collections.abc import Iterator
from pathlib import Path

from .builds import description_path, pinned_description
from .errors import BuildError
from .fileio import read_bytes
from .paths import MANIFEST, RELEASE_KEY, RepoPaths

#: The time stamp of every file in the zip, so that the same files give the same zip.
_STAMP = (2026, 1, 1, 0, 0, 0)


def data_files(paths: RepoPaths, version: str) -> list[tuple[str, bytes]]:
    """Return the data that the release's commands read: their path in the folder, and their content.

    These are the pinned build and its specs, the film records, and the release's manifest, which names the
    locations that ``catalogue.ReleaseLocator`` reads: the checkout's, and the checkout's cache folder.

    Raises:
        BuildError: if a file is missing.
    """
    description = pinned_description(paths)
    sources = [
        paths.pinned,
        description_path(paths, description.name),
        paths.film_records,
    ]
    sources += [paths.spec_file(spec) for spec in description.specs]
    missing = [str(source) for source in sources if not source.is_file()]
    if missing:
        raise BuildError("missing for the release: " + ", ".join(missing))
    manifest = {RELEASE_KEY: version} | {
        key: paths.relative(path)
        for key, path in (
            ("pinned", paths.pinned),
            ("builds", paths.builds),
            ("specs", paths.specs),
            ("label_spec", paths.label_spec),
            ("film_records", paths.film_records),
            ("cache", paths.location("cache")),
            ("app", paths.app),
        )
    }
    text = json.dumps(manifest, indent=1) + "\n"
    files = [
        (paths.relative(source), read_bytes(source, BuildError)) for source in sources
    ]
    return files + [(MANIFEST, text.encode())]


def release_files(paths: RepoPaths, version: str) -> list[tuple[str, bytes]]:
    """Return the files of the release: their path in the folder, and their content.

    Raises:
        BuildError: if the app page is not built or a file is missing.
    """
    app = paths.app
    if not (app / "index.html").is_file():
        raise BuildError(
            f"{app}: the app page is not built: npm ci && npm run build:app"
        )
    sources = [(path.name, path) for path in paths.release_files]
    sources += list(_package(paths))
    missing = [str(source) for _, source in sources if not source.is_file()]
    if missing:
        raise BuildError("missing for the release: " + ", ".join(missing))
    files = data_files(paths, version)
    files += [(name, read_bytes(source, BuildError)) for name, source in sources]
    firmware = [name for name, _ in files if name.lower().endswith(".bin")]
    if firmware:
        raise BuildError("a release never holds firmware: " + ", ".join(firmware))
    return sorted(files)


def programs(paths: RepoPaths) -> set[str]:
    """Return the names, at the top of the release folder, of the files that are programs."""
    return {
        path.name
        for path in paths.release_files
        if path.is_file() and path.stat().st_mode & stat.S_IXUSR
    }


def _package(paths: RepoPaths) -> Iterator[tuple[str, Path]]:
    """Yield the files of the package: its code, its type marker and the app page."""
    for source in sorted(paths.package.rglob("*")):
        if source.is_file() and "__pycache__" not in source.parts:
            yield paths.relative(source), source


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
    run = programs(paths)
    try:
        out.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, data in files:
                info = zipfile.ZipInfo(f"{name}/{path}", _STAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = 0o755 if path in run else 0o644
                info.external_attr = (
                    0o100000 | mode
                ) << 16  # a regular file and its permissions
                info.create_system = 3  # Unix, so that unzip tools keep the permissions
                archive.writestr(info, data)
    except OSError as error:
        raise BuildError(f"{target}: {error.strerror or error}") from None
    return target

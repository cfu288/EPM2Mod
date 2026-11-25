"""The release zip (``epm2mod package``): what a user who doesn't code downloads.

The zip holds one folder, ``EPM2Mod-<version>/``, with what the commands for camera owners (``epm2mod install``,
``films``, ``restore``, ``inspect``, ``serve``) need for the release's build (``release_build``), and nothing else:

- the package (``RepoPaths.package``, with the built app page ``RepoPaths.app``);
- the data (``data_files``): the build description and its patch specs, the pointer that pins it, the film records,
  and the release's manifest (``paths.MANIFEST``), which names these locations and holds the version under ``paths.RELEASE_KEY``, by
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
from dataclasses import replace
from pathlib import Path

from .builds import BuildDescription, description_path, pinned_description
from .container import parse
from .errors import BuildError
from .fileio import read_bytes
from .label import PLACEHOLDER
from .paths import MANIFEST, RELEASE_KEY, TESTED_KEY, RepoPaths
from .spec import BytesOp, load_spec

#: The time stamp of every file in the zip, so that the same files give the same zip.
_STAMP = (2026, 1, 1, 0, 0, 0)


def data_files(paths: RepoPaths, version: str) -> list[tuple[str, bytes]]:
    """Return the data that the release's commands read: their path in the folder, and their content.

    These are the build of ``version`` (``release_build``) and its specs, a pinned file that names that build, the
    film records, and the release's manifest, which names the locations that ``catalogue.ReleaseLocator`` reads: the
    checkout's, and the checkout's cache folder.

    Raises:
        BuildError: if a file is missing, or as ``release_build``.
    """
    tested = release_build(paths, version)
    description = release_description(paths, version)
    build = description_path(paths, description.name)
    sources = [build, paths.film_records]
    sources += [paths.spec_file(spec) for spec in description.specs]
    missing = [str(source) for source in sources if not source.is_file()]
    if missing:
        raise BuildError("missing for the release: " + ", ".join(missing))
    record = {}
    if (
        description != tested
    ):  # the release record: which camera-tested build the stamped build is
        record = {TESTED_KEY: {"sha256": tested.sha256, "label": tested.label}}
    manifest = (
        {RELEASE_KEY: version}
        | record
        | {
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
    )
    text = json.dumps(manifest, indent=1) + "\n"
    pointer = json.dumps({"build": paths.relative(build)}, indent=1) + "\n"
    files = [
        (paths.relative(source), read_bytes(source, BuildError)) for source in sources
    ]
    if description != tested:
        stamped = json.dumps(description.to_json(), indent=1) + "\n"
        files[0] = (paths.relative(build), stamped.encode())
    return files + [
        (MANIFEST, text.encode()),
        (paths.relative(paths.pinned), pointer.encode()),
    ]


#: The line of the package that holds its version.
_VERSION_LINE = re.compile(rb'^__version__ = "[^"]*"$', re.MULTILINE)


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
    # the package in the zip says the release's version (the checkout's package has a fixed one)
    stamp = f'__version__ = "{version}"'.encode()
    files = [
        (name, _VERSION_LINE.sub(stamp, data) if name.endswith(".py") else data)
        for name, data in files
    ]
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
#: ``-rc.N`` for a pre-release, ``-dev`` for a test build, or ``-NAME.N`` for a test release of the build NAME in
#: place of the pinned one. NAME is never ``rc`` or ``dev``.
_VERSION = re.compile(
    r"^\d{4}\.\d{2}\.\d{2}(\.\d+)?"
    r"(-rc\.\d+|-dev|-(?!(?:rc|dev)\.)(?P<build>[a-z0-9][a-z0-9-]*)\.[1-9]\d*)?$"
)


def check_version(version: str) -> None:
    """Refuse a version that is not a calendar version.

    Raises:
        BuildError: if it is not.
    """
    version_build(version)


def version_build(version: str) -> str | None:
    """Return the name of the build that ``version`` names (``2026.11.20-NAME.1``), or None for the pinned build.

    Raises:
        BuildError: if ``version`` is not a calendar version.
    """
    match = _VERSION.match(version)
    if match is None:
        raise BuildError(
            f"'{version}': a version is a date, like 2026.11.18, 2026.11.18-rc.1 "
            "or 2026.11.18-NAME.1 for the build NAME"
        )
    return match.group("build")


def release_build(paths: RepoPaths, version: str) -> BuildDescription:
    """Return the build that the release ``version`` holds: the build it names, or the pinned build.

    Raises:
        BuildError: if the version is not a calendar version, or the build has no camera test.
        NotFoundError: if there is no build of the name the version gives.
    """
    name = version_build(version)
    if name is None:
        return pinned_description(paths)
    description = paths.build(name)
    if not description.tested:
        raise BuildError(
            f"{name} has no camera test: record it with 'epm2mod pin {name} --no-pin'"
        )
    return description


def label_range(paths: RepoPaths) -> tuple[int, int, int]:
    """Return where the label spec writes the label's date: the block, and the first and the end offset in it.

    Raises:
        BuildError: if the spec does not hold the placeholder date exactly once.
    """
    old = PLACEHOLDER.encode("utf-16-le")
    spec = load_spec(paths.label_spec)
    found = [op for op in spec.ops if isinstance(op, BytesOp) and old in op.new]
    if len(found) != 1 or found[0].new.count(old) != 1:
        raise BuildError(
            f"{spec.name}: the placeholder {PLACEHOLDER} must be there once"
        )
    start = found[0].offset + found[0].new.index(old)
    return found[0].block, start, start + len(old)


def check_only_the_label_differs(
    paths: RepoPaths, tested: bytes, stamped: bytes
) -> None:
    """Refuse a stamped image that differs from the camera-tested image outside the label's date.

    The two may differ in the bytes of the date (``label_range``) and in the checksum of that block, which the
    container format recomputes. Headers, every other block, every other byte of the block and the tail are equal.

    Raises:
        BuildError: if anything else differs.
    """
    block, start, end = label_range(paths)
    old, new = parse(tested), parse(stamped)
    same = len(old.blocks) == len(new.blocks) and old.tail == new.tail
    same = (
        same and new.checksums_ok
    )  # the one word that may differ must be the right checksum
    for index, (a, b) in enumerate(zip(old.blocks, new.blocks)):
        same = same and a.header == b.header and len(a.payload) == len(b.payload)
        if index == block:
            same = same and a.payload[:start] == b.payload[:start]
            same = same and a.payload[end:] == b.payload[end:]
            # the trailer is a copy of the header with the checksum in its last word: only that word may differ
            same = same and a.trailer[:-4] == b.trailer[:-4]
        else:
            same = same and a.payload == b.payload and a.trailer == b.trailer
    if not same:
        raise BuildError(
            "the build with the release's date differs from the camera-tested build outside the date of "
            "the Firmware screen: it is not released"
        )


def stamp(
    paths: RepoPaths, description: BuildDescription, day: str
) -> tuple[BuildDescription, bytes]:
    """Return a camera-tested build with the label ``day``, and its image.

    The camera's Firmware screen then shows the date of the release. The result
    has the sha256 of the new image; it is released only because
    ``check_only_the_label_differs`` passed. Its text (``what``) names the new
    label where it named the old one. A build whose label is ``day`` already
    is returned as it is, with the image that was tested.

    Raises:
        BuildError: if the build has no label or no camera test, if it does not give its recorded sha256, or if the
            new image differs outside the date.
        StockError: if Olympus's firmware is not downloaded.
    """
    from .pipeline import build_image, load_specs
    from .stock import read_stock

    if description.label is None or not description.tested:
        raise BuildError(f"{description.name} has no label or no camera test")
    stock_data = read_stock(paths, description.stock_firmware)
    tested, _ = build_image(description, load_specs(paths, description), stock_data)
    if description.label == day:
        return description, tested.image
    relabelled = replace(
        description,
        label=day,
        sha256=None,
        camera_tested=None,
        what=description.what.replace(description.label, day),
    )
    applied, digest = build_image(relabelled, load_specs(paths, relabelled), stock_data)
    check_only_the_label_differs(paths, tested.image, applied.image)
    stamped = replace(
        relabelled, sha256=digest, camera_tested=description.camera_tested
    )
    return stamped, applied.image


def release_description(paths: RepoPaths, version: str) -> BuildDescription:
    """Return the description of the build that the release ``version`` installs.

    This is ``release_build`` with the label set to the day of the version (``stamp``), so that the camera's
    Firmware screen and the release show one date. A ``-dev`` version and a build without a label are not stamped,
    and a build whose label is that day already is released as it is.

    Raises:
        BuildError, NotFoundError, StockError: as ``release_build`` and ``stamp``.
    """
    description = release_build(paths, version)
    day = version[:10]
    if version.endswith("-dev") or description.label is None:
        return description
    return stamp(paths, description, day)[0]


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

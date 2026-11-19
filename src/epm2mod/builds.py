"""Build descriptions and the pinned build.

A build description is a JSON file in ``builds/``::

    {
      "what": "Seven film looks as art filters",
      "specs": ["patches/a.json", "patches/b.json"],
      "sha256": "...",                 (only after a camera test)
      "camera_tested": "2026-11-13",   (only after a camera test)
      "first_code": true               (optional; see below)
    }

The name of a build is the name of its file without ``.json``; it is not
written inside the file. The specs are files in ``patches/``, written relative
to the repository root, and are applied in the order given. ``sha256`` and
``camera_tested`` are either both present (a tested build) or both absent (a
candidate).

``first_code`` is for a build that runs new code in an area of the firmware
where no camera-tested build runs code yet. The free-space check refuses such
a build unless the description says so, because only the flash can show that
code runs there. The key is either absent or ``true``.

``pinned-build.json`` at the top of the repository holds
``{"build": "builds/NAME.json"}``: the description of the last build that
passed a camera test.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .errors import BuildError
from .fileio import read_json, write_json
from .hashing import is_sha256
from .label import LABEL_SPEC, check_label
from .paths import SPEC_FOLDER, RepoPaths, is_repo_relative

_NAME = re.compile(r"[a-z0-9][a-z0-9._-]*")
_KEYS = {"what", "specs", "sha256", "camera_tested", "first_code", "label"}
_SUFFIX = ".json"


def _check_sha256(value: object, where: str) -> str:
    """Return ``value`` if it is 64 lower-case hexadecimal digits, else raise."""
    if not is_sha256(value):
        raise BuildError(f"{where}: 'sha256' must be 64 lower-case hexadecimal digits")
    return value


def _parse_date(value: object, where: str) -> datetime.date:
    """Return the date that ``value`` writes as YYYY-MM-DD, else raise."""
    if isinstance(value, str):
        try:
            parsed = datetime.date.fromisoformat(value)
        except ValueError:
            parsed = None
        if parsed is not None and parsed.isoformat() == value:
            return parsed
    raise BuildError(f"{where}: the date must be written YYYY-MM-DD, got {value!r}")


def _check_date(value: object, where: str) -> str:
    """Return ``value`` if it is a date written as YYYY-MM-DD, else raise."""
    return _parse_date(value, where).isoformat()


def check_spec_path(text: object, where: str) -> str:
    """Return ``text`` if it names a patch spec file in ``patches/``, else raise.

    A spec path is relative to the repository root, has forward slashes, no
    ``.`` or ``..`` parts, starts with ``patches/`` and ends with ``.json``.
    """
    if (
        not isinstance(text, str)
        or not is_repo_relative(text)
        or not text.startswith(SPEC_FOLDER + "/")
        or not text.endswith(_SUFFIX)
    ):
        raise BuildError(
            f"{where}: {text!r} is not a patch spec: it must be a .json file in "
            f"{SPEC_FOLDER}/, written relative to the repository root with "
            "forward slashes"
        )
    return text


@dataclass(frozen=True)
class BuildDescription:
    """One firmware build.

    Attributes:
        name: the build's name (the description's file name without ``.json``).
        what: one line that says what the build gives the user.
        specs: the patch specs, relative to the repository root, in order.
        sha256: SHA-256 of the firmware file, if the build passed a camera test.
        camera_tested: ISO date of that test; present exactly when ``sha256`` is.
        first_code: True if the build runs code in an area where no
            camera-tested build runs code yet.
        label: the date ``YYYY.MM.DD`` that the camera's Firmware screen shows
            after "EPM2Mod"; present exactly when ``specs`` lists the label spec.
    """

    name: str
    what: str
    specs: tuple[str, ...]
    sha256: str | None = None
    camera_tested: str | None = None
    first_code: bool = False
    label: str | None = None

    def __post_init__(self) -> None:
        """Check the description. Every instance is valid.

        Raises:
            BuildError: if a field is not valid.
        """
        if not _NAME.fullmatch(self.name):
            raise BuildError(
                f"{self.name!r}: a build name has lower-case letters, digits, "
                "'.', '_' and '-' only, and starts with a letter or a digit"
            )
        if (
            not self.what.strip()
            or any(ord(char) < 0x20 for char in self.what)
            or "<" in self.what
            or ">" in self.what
        ):
            raise BuildError(
                f"{self.name}: 'what' must be one line of plain text, "
                "without '<' or '>'"
            )
        if not self.specs:
            raise BuildError(f"{self.name}: 'specs' must name one or more specs")
        for spec in self.specs:
            check_spec_path(spec, self.name)
        if len(set(self.specs)) != len(self.specs):
            raise BuildError(f"{self.name}: 'specs' names a spec more than once")
        if (self.sha256 is None) != (self.camera_tested is None):
            raise BuildError(
                f"{self.name}: 'sha256' and 'camera_tested' must both be present "
                "or both absent"
            )
        if self.sha256 is not None:
            _check_sha256(self.sha256, self.name)
            _check_date(self.camera_tested, self.name)
        if self.label is not None:
            check_label(self.label, self.name)
        if (self.label is None) == (LABEL_SPEC in self.specs):
            raise BuildError(
                f"{self.name}: 'label' and the spec {LABEL_SPEC} go together: "
                "give both or neither"
            )

    @property
    def tested(self) -> bool:
        """True if the build passed a camera test and its SHA-256 is recorded."""
        return self.sha256 is not None

    def as_tested(self, sha256: str, date: str) -> BuildDescription:
        """Return a copy that records a passed camera test.

        A description that already has a test record is returned unchanged if
        the record is the same one. A different record is refused: a test
        record is never rewritten.

        Raises:
            BuildError: if ``sha256`` or ``date`` is malformed, or the
                description has another test record.
        """
        if self.tested:
            if (self.sha256, self.camera_tested) == (sha256, date):
                return self
            raise BuildError(
                f"{self.name}: already has a test record "
                f"({self.camera_tested}, sha256 {self.sha256}); it is not changed. "
                "A changed build needs a description with a new name."
            )
        return replace(self, sha256=sha256, camera_tested=date)

    def to_json(self) -> dict[str, Any]:
        """Return the JSON form of the description."""
        raw: dict[str, Any] = {"what": self.what, "specs": list(self.specs)}
        if self.sha256 is not None:
            raw["sha256"] = self.sha256
            raw["camera_tested"] = self.camera_tested
        if self.first_code:
            raw["first_code"] = True
        if self.label is not None:
            raw["label"] = self.label
        return raw


def description_from_json(name: str, raw: Any) -> BuildDescription:
    """Build a description from its JSON form.

    The test date is checked for its form only. That it is not in the future
    is checked when a test is recorded (``pipeline.record_test``), not here: a
    recorded build must stay readable on a computer whose clock is wrong.

    Args:
        name: the build's name.
        raw: the parsed JSON.

    Raises:
        BuildError: if the name or the JSON is not valid.
    """
    if not isinstance(raw, dict):
        raise BuildError(f"{name}: a build description must be a JSON object")
    unknown = sorted(set(raw) - _KEYS)
    if unknown:
        raise BuildError(f"{name}: unknown key(s): {', '.join(unknown)}")
    what, specs = raw.get("what"), raw.get("specs")
    if not isinstance(what, str):
        raise BuildError(f"{name}: 'what' must be one line of text")
    if not isinstance(specs, list):
        raise BuildError(f"{name}: 'specs' must be a list of paths")
    sha256, tested = raw.get("sha256"), raw.get("camera_tested")
    if raw.get("first_code", True) is not True:
        raise BuildError(f"{name}: 'first_code' must be true, or absent")
    return BuildDescription(
        name=name,
        what=what.strip(),
        specs=tuple(check_spec_path(spec, name) for spec in specs),
        sha256=None if sha256 is None else _check_sha256(sha256, name),
        camera_tested=None if tested is None else _check_date(tested, name),
        first_code="first_code" in raw,
        label=None if raw.get("label") is None else check_label(raw["label"], name),
    )


def load_description(path: Path) -> BuildDescription:
    """Read a build description file.

    Raises:
        BuildError: if the file is missing, is not JSON, or is not valid.
    """
    if path.suffix != _SUFFIX:
        raise BuildError(f"{path}: a build description is a {_SUFFIX} file")
    return description_from_json(path.stem, read_json(path, BuildError))


def description_path(paths: RepoPaths, name: str) -> Path:
    """Return the path of the description of the build called ``name``."""
    return paths.builds / f"{name}{_SUFFIX}"


def save_description(paths: RepoPaths, description: BuildDescription) -> Path:
    """Write a description to ``builds/NAME.json`` and return the path."""
    path = description_path(paths, description.name)
    write_json(path, description.to_json(), BuildError)
    return path


def all_descriptions(paths: RepoPaths) -> list[BuildDescription]:
    """Return every description in ``builds/``, sorted by name."""
    found = [load_description(path) for path in paths.builds.glob("*" + _SUFFIX)]
    return sorted(found, key=lambda description: description.name)


def pinned_path(paths: RepoPaths) -> Path:
    """Return the path of the description that ``pinned-build.json`` names.

    The description itself is not read.

    Raises:
        BuildError: if the pointer file is missing or malformed, or does not
            name a file directly in ``builds/``.
    """
    raw = read_json(paths.pinned, BuildError)
    target = raw.get("build") if isinstance(raw, dict) and len(raw) == 1 else None
    prefix = paths.builds.name + "/"
    if (
        not isinstance(target, str)
        or not is_repo_relative(target)
        or not target.startswith(prefix)
        or "/" in target[len(prefix) :]
    ):
        raise BuildError(
            f'{paths.pinned}: must be {{"build": "{prefix}NAME{_SUFFIX}"}}'
        )
    return paths.resolve(target)


def pinned_description(paths: RepoPaths) -> BuildDescription:
    """Return the description that ``pinned-build.json`` names.

    Raises:
        BuildError: as ``pinned_path``, and if the description cannot be read
            or is not a tested build.
    """
    path = pinned_path(paths)
    description = load_description(path)
    if not description.tested:
        raise BuildError(
            f"{paths.pinned}: {paths.relative(path)} is not a camera-tested "
            "build (it has no sha256)"
        )
    return description


def check_test_date(date: str, today: datetime.date) -> str:
    """Return ``date`` if it is a well-formed date that is not after ``today``.

    Raises:
        BuildError: if it is malformed or in the future.
    """
    if _parse_date(date, "the test date") > today:
        raise BuildError(f"the test date {date} is in the future")
    return date


def pin(paths: RepoPaths, description: BuildDescription) -> None:
    """Make ``description`` the pinned build.

    The description is saved first, so the pointer never names a file that
    does not hold the test record.

    Raises:
        BuildError: if the description is not a tested build.
    """
    if not description.tested:
        raise BuildError(
            f"{description.name}: only a camera-tested build can be pinned"
        )
    path = save_description(paths, description)
    write_json(paths.pinned, {"build": paths.relative(path)}, BuildError)

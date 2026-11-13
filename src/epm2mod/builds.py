"""Build descriptions and the pinned build.

A build description is a JSON file in ``builds/``::

    {
      "what": "Seven film looks as art filters",
      "specs": ["patches/a.json", "patches/b.json"],
      "sha256": "...",                 (only after a camera test)
      "camera_tested": "2026-11-13"    (only after a camera test)
    }

The name of a build is the name of its file without ``.json``; it is not
written inside the file. The spec paths are relative to the repository root and
are applied in the order given. ``sha256`` and ``camera_tested`` are either both
present (a tested build) or both absent (a candidate).

``pinned-build.json`` at the top of the repository holds ``{"build": "builds/NAME.json"}``:
the description of the last build that passed a camera test.
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .errors import BuildError
from .paths import RepoPaths

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class BuildDescription:
    """One firmware build.

    Attributes:
        name: the build's name (the description's file name without ``.json``).
        what: one line that says what the build gives the user.
        specs: the patch specs, relative to the repository root, in order.
        sha256: SHA-256 of the firmware file, if the build passed a camera test.
        camera_tested: ISO date of that test, if any.
    """

    name: str
    what: str
    specs: Tuple[str, ...]
    sha256: Optional[str] = None
    camera_tested: Optional[str] = None

    @property
    def tested(self) -> bool:
        """True if the build passed a camera test and its SHA-256 is recorded."""
        return self.sha256 is not None

    def as_tested(self, sha256: str, date: str) -> "BuildDescription":
        """Return a copy that records a passed camera test.

        Raises:
            BuildError: if ``sha256`` or ``date`` is malformed.
        """
        _check_sha256(sha256, self.name)
        _check_date(date, self.name)
        return replace(self, sha256=sha256, camera_tested=date)

    def to_json(self) -> Dict[str, Any]:
        """Return the JSON form of the description."""
        raw: Dict[str, Any] = {"what": self.what, "specs": list(self.specs)}
        if self.sha256 is not None and self.camera_tested is not None:
            raw["sha256"] = self.sha256
            raw["camera_tested"] = self.camera_tested
        return raw


def _check_sha256(value: str, where: str) -> None:
    """Raise unless ``value`` is 64 lower-case hexadecimal digits."""
    if not _SHA256.match(value):
        raise BuildError(f"{where}: 'sha256' must be 64 lower-case hexadecimal digits")


def _check_date(value: str, where: str) -> None:
    """Raise unless ``value`` is a date written as YYYY-MM-DD."""
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        parsed = None
    if parsed is None or parsed.isoformat() != value:
        raise BuildError(f"{where}: the date must be written YYYY-MM-DD, got {value!r}")


def description_from_json(name: str, raw: Any) -> BuildDescription:
    """Build a description from its JSON form.

    Args:
        name: the build's name.
        raw: the parsed JSON.

    Raises:
        BuildError: if the name or the JSON is not valid.
    """
    if not _NAME.match(name):
        raise BuildError(
            f"{name!r}: a build name has lower-case letters, digits, '.', '_' "
            "and '-' only, and starts with a letter or a digit"
        )
    if not isinstance(raw, dict):
        raise BuildError(f"{name}: a build description must be a JSON object")
    unknown = sorted(set(raw) - {"what", "specs", "sha256", "camera_tested"})
    if unknown:
        raise BuildError(f"{name}: unknown key(s): {', '.join(unknown)}")
    what, specs = raw.get("what"), raw.get("specs")
    if not isinstance(what, str) or not what.strip():
        raise BuildError(f"{name}: 'what' must be a line of text")
    if (
        not isinstance(specs, list)
        or not specs
        or not all(isinstance(spec, str) and spec for spec in specs)
    ):
        raise BuildError(f"{name}: 'specs' must be a list of one or more paths")
    if len(set(specs)) != len(specs):
        raise BuildError(f"{name}: 'specs' names a spec more than once")
    sha256, tested = raw.get("sha256"), raw.get("camera_tested")
    if (sha256 is None) != (tested is None):
        raise BuildError(
            f"{name}: 'sha256' and 'camera_tested' must both be present or both absent"
        )
    if sha256 is not None:
        if not isinstance(sha256, str) or not isinstance(tested, str):
            raise BuildError(f"{name}: 'sha256' and 'camera_tested' must be text")
        _check_sha256(sha256, name)
        _check_date(tested, name)
    return BuildDescription(name, what.strip(), tuple(specs), sha256, tested)


def load_description(path: Path) -> BuildDescription:
    """Read a build description file.

    Raises:
        BuildError: if the file is missing, is not JSON, or is not valid.
    """
    if path.suffix != ".json":
        raise BuildError(f"{path}: a build description is a .json file")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise BuildError(f"{path}: cannot be read: {error.strerror}") from None
    except ValueError as error:
        raise BuildError(f"{path}: not JSON: {error}") from None
    return description_from_json(path.stem, raw)


def save_description(paths: RepoPaths, description: BuildDescription) -> Path:
    """Write a description to ``builds/NAME.json`` and return the path."""
    path = description_path(paths, description.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, description.to_json())
    return path


def description_path(paths: RepoPaths, name: str) -> Path:
    """Return the path of the description of the build called ``name``."""
    return paths.builds / f"{name}.json"


def all_descriptions(paths: RepoPaths) -> List[BuildDescription]:
    """Return every description in ``builds/``, sorted by name."""
    return [load_description(path) for path in sorted(paths.builds.glob("*.json"))]


def pinned_description(paths: RepoPaths) -> BuildDescription:
    """Return the description that ``pinned-build.json`` names.

    Raises:
        BuildError: if the pointer file is malformed, points outside ``builds/``,
            or names a build that is not tested.
    """
    try:
        raw = json.loads(paths.pinned.read_text(encoding="utf-8"))
    except OSError as error:
        raise BuildError(f"{paths.pinned}: cannot be read: {error.strerror}") from None
    except ValueError as error:
        raise BuildError(f"{paths.pinned}: not JSON: {error}") from None
    target = raw.get("build") if isinstance(raw, dict) else None
    if not isinstance(target, str):
        raise BuildError(f'{paths.pinned}: must be {{"build": "builds/NAME.json"}}')
    path = paths.resolve(target)
    if path.parent.resolve() != paths.builds.resolve():
        raise BuildError(f"{paths.pinned}: {target} is not a file in builds/")
    description = load_description(path)
    if not description.tested:
        raise BuildError(
            f"{paths.pinned}: {target} is not a camera-tested build "
            "(it has no sha256)"
        )
    return description


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
    _write_json(paths.pinned, {"build": paths.relative(path)})


def _write_json(path: Path, raw: Dict[str, Any]) -> None:
    """Write JSON with the repository's layout: one-space indent, final newline."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(raw, indent=1) + "\n", encoding="utf-8")
    temporary.replace(path)

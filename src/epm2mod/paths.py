"""Where the repository's files are.

``RepoPaths`` holds the layout of a checkout: every folder and file that the
package looks for by a fixed name is a property here. Paths that come from data
(a patch spec named by a build description, a fit file named by the film list)
are turned into absolute paths with ``RepoPaths.resolve``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import RepositoryError

#: The file that marks the top of the repository.
ROOT_MARKER = "pinned-build.json"
#: Environment variable that names the repository root explicitly.
ROOT_ENV = "EPM2MOD_ROOT"
#: The folder that holds the patch specs a build may use.
SPEC_FOLDER = "patches"


@dataclass(frozen=True)
class RepoPaths:
    """Paths inside one checkout of the repository.

    Attributes:
        root: the top of the repository.
    """

    root: Path

    @property
    def pinned(self) -> Path:
        """The file that names the pinned build description."""
        return self.root / ROOT_MARKER

    @property
    def builds(self) -> Path:
        """The folder of build descriptions."""
        return self.root / "builds"

    @property
    def output(self) -> Path:
        """The folder that built firmware is written to (not in git)."""
        return self.root / "build"

    @property
    def card(self) -> Path:
        """A folder laid out like the SD card, ready to copy."""
        return self.output / "card"

    @property
    def readme(self) -> Path:
        """The top-level README."""
        return self.root / "README.md"

    @property
    def films(self) -> Path:
        """The list of film looks and the menu entries they replace."""
        return self.root / "looks" / "films.json"

    @property
    def free_space_tool(self) -> Path:
        """The script that checks where patch specs put new bytes."""
        return self.root / "tools" / "freespace.py"

    @property
    def emulator_checks(self) -> tuple[Path, ...]:
        """The scripts that start a firmware image in the emulator, in order."""
        folder = self.root / "tools" / "emu"
        return (folder / "boot-test", folder / "update-path-test")

    @property
    def firmware_map(self) -> Path:
        """A file the free-space check needs; it is made by ``tools/fwmap.py``."""
        return self.output / "map" / "linear.txt"

    def resolve(self, relative: str) -> Path:
        """Return the absolute path of a plain path written relative to the root.

        Raises:
            RepositoryError: if ``relative`` is not a plain path inside the
                repository (see ``is_repo_relative``).
        """
        if not is_repo_relative(relative):
            raise RepositoryError(
                f"{relative!r} is not a plain path inside the repository"
            )
        return self.root / relative

    def relative(self, path: Path) -> str:
        """Return ``path`` as text for a message: relative to the root if it is inside.

        Symbolic links are not followed, so a folder of the repository that is
        a link to another place is still shown by its name in the repository.
        """
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)


def is_repo_relative(text: str) -> bool:
    """Return True if ``text`` is a plain path inside the repository.

    Plain means: written with forward slashes, not absolute on any platform
    (no leading slash, no drive letter), with no ``.`` or ``..`` parts, and
    without control characters.
    """
    if not text or "\\" in text or ":" in text:
        return False
    if any(ord(char) < 0x20 or 0xD800 <= ord(char) <= 0xDFFF for char in text):
        return False
    path = PurePosixPath(text)
    if path.is_absolute() or path.as_posix() != text:
        return False
    return all(part not in (".", "..") for part in path.parts)


def find_root(start: Path | None = None) -> Path:
    """Find the top of the repository.

    The root is the folder named by the ``EPM2MOD_ROOT`` environment variable,
    if it is set. Otherwise it is the nearest parent of ``start`` (default: the
    current folder) that holds ``pinned-build.json``, or else the nearest such
    parent of this source file.

    Args:
        start: where to start the search.

    Returns:
        The root folder.

    Raises:
        RepositoryError: if no folder with the marker file is found, or the
            folder that ``EPM2MOD_ROOT`` names does not hold it.
    """
    env = os.environ.get(ROOT_ENV)
    if env:
        root = Path(env).absolute()
        if not (root / ROOT_MARKER).is_file():
            raise RepositoryError(
                f"{ROOT_ENV}={env} is not the repository: no {ROOT_MARKER} there"
            )
        return root
    for origin in (start or Path.cwd(), Path(__file__)):
        here = origin.absolute()
        for folder in (here, *here.parents):
            if (folder / ROOT_MARKER).is_file():
                return folder
    raise RepositoryError(
        f"no {ROOT_MARKER} found above the current folder; "
        f"run the command inside the repository or set {ROOT_ENV}"
    )


def repo_paths(start: Path | None = None) -> RepoPaths:
    """Return the paths of the repository that holds ``start``."""
    return RepoPaths(find_root(start))

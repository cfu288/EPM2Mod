"""Where the repository's files are.

All paths that the package uses come from ``RepoPaths``. Nothing else in the
package builds a path from a string literal.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: The file that marks the top of the repository.
ROOT_MARKER = "pinned-build.json"
#: Environment variable that names the repository root explicitly.
ROOT_ENV = "EPM2MOD_ROOT"


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
    def firmware_map(self) -> Path:
        """A file the free-space check needs; it is made by ``tools/fwmap.py``."""
        return self.output / "map" / "linear.txt"

    def resolve(self, relative: str) -> Path:
        """Return the absolute path of a path written relative to the root."""
        return self.root / relative

    def relative(self, path: Path) -> str:
        """Return ``path`` relative to the root, with forward slashes."""
        return path.resolve().relative_to(self.root.resolve()).as_posix()


def find_root(start: Path | None = None) -> Path:
    """Find the top of the repository.

    The root is, in this order: the folder named by the ``EPM2MOD_ROOT``
    environment variable; the nearest parent of ``start`` (default: the current
    folder) that holds ``pinned-build.json``; the nearest such parent of this
    source file.

    Args:
        start: where to start the search.

    Returns:
        The root folder.

    Raises:
        FileNotFoundError: if no folder with the marker file is found.
    """
    env = os.environ.get(ROOT_ENV)
    if env:
        return Path(env).resolve()
    for origin in (start or Path.cwd(), Path(__file__)):
        here = origin.resolve()
        for folder in (here, *here.parents):
            if (folder / ROOT_MARKER).is_file():
                return folder
    raise FileNotFoundError(
        f"no {ROOT_MARKER} found above the current folder; "
        f"run the command inside the repository or set {ROOT_ENV}"
    )


def repo_paths(start: Path | None = None) -> RepoPaths:
    """Return the paths of the repository that holds ``start``."""
    return RepoPaths(find_root(start))

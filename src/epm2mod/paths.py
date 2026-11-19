"""Where the repository's files are.

``RepoPaths`` holds the layout of a checkout: every folder and file that the
package looks for by a fixed name is a property here. Paths that come from data
(a patch spec named by a build description, a fit file named by the film list)
are turned into absolute paths with ``RepoPaths.resolve``.

``RepoPaths`` is also the checkout's implementation of the locator
(``catalogue.Locator``): the methods after the properties are the ones that
commands use. The release folder has the same layout for the files it holds
(``catalogue.ReleaseLocator``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, ClassVar

from .errors import NotFoundError, RepositoryError

if TYPE_CHECKING:
    from .builds import BuildDescription
    from .stock import StockFirmware

#: The file that marks the top of the repository.
ROOT_MARKER = "pinned-build.json"
#: Environment variable that names the repository root explicitly.
ROOT_ENV = "EPM2MOD_ROOT"
#: The folder that holds the patch specs a build may use.
SPEC_FOLDER = "patches"
#: The file that marks an unpacked release folder (``epm2mod package`` writes it).
RELEASE_MARKER = "release.json"


@dataclass(frozen=True)
class RepoPaths:
    """Paths inside one checkout of the repository.

    Attributes:
        root: the top of the repository.
    """

    root: Path

    #: What kind of source this is, for messages and ``--json``.
    kind: ClassVar[str] = "checkout"

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
    def more_films(self) -> Path:
        """The list of the film looks beyond the first seven."""
        return self.root / "looks" / "more-films.json"

    @property
    def bw_films(self) -> Path:
        """The film list with a black-and-white film in the Grainy Film entry."""
        return self.root / "looks" / "films-12-bw.json"

    @property
    def card_looks(self) -> Path:
        """The look list of the default look file for the SD card."""
        return self.root / "looks" / "card-looks.json"

    @property
    def catalogue(self) -> Path:
        """The fitted films that a look file can hold."""
        return self.root / "looks" / "catalogue.json"

    @property
    def film_records(self) -> Path:
        """The films with their look records, which look files are packed from."""
        return self.root / "looks" / "film-records.json"

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

    @property
    def events(self) -> Path:
        """The event dictionary of the debug log."""
        return self.root / "logs" / "events.json"

    # The locator (``catalogue.Locator``).

    def where(self) -> str:
        """Return the source's folder, for messages."""
        return str(self.root)

    def output_folder(self) -> Path:
        """Return the folder that commands write their outputs to."""
        return self.output

    def stock_file(self, stock: StockFirmware) -> Path:
        """Return where the downloaded stock firmware is kept."""
        return self.resolve(stock.relative_path)

    def spec_file(self, relative: str) -> Path:
        """Return the file of a patch spec that a build description names."""
        return self.resolve(relative)

    def film_records_file(self) -> Path:
        """Return the file of the film records."""
        return self.film_records

    def pinned_build(self) -> BuildDescription:
        """Return the pinned build description."""
        from .builds import pinned_description

        return pinned_description(self)

    def build(self, name: str) -> BuildDescription:
        """Return the build description called ``name``.

        Raises:
            NotFoundError: if there is no description of that name.
            BuildError: if the description is malformed.
        """
        from .builds import description_path, is_build_name, load_description

        path = description_path(self, name) if is_build_name(name) else None
        if path is None or not path.is_file():
            raise NotFoundError(
                f"no build description '{name}'; 'epm2mod builds' lists them"
            )
        return load_description(path)

    def all_builds(self) -> list[BuildDescription]:
        """Return every build description, in name order."""
        from .builds import all_descriptions

        return all_descriptions(self)

    def event_dictionaries(self) -> list[Path]:
        """Return the event dictionaries of the debug log: the current one, then those of older builds."""
        return [self.events, *sorted(self.events.parent.glob("events-*.json"))]

    def checkout(self) -> RepoPaths:
        """Return the checkout: this one."""
        return self

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

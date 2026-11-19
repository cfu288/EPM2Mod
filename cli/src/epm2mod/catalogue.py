"""The one place that knows where the package's data is: the locator, and the film catalogue.

Commands never build a project path. They ask a ``Locator`` for each resource: the film records, the build
descriptions (by name) and the pinned build, the patch specs a build names, the downloaded Olympus firmware, the
output folder, and the event dictionaries of the debug log. The locations come from the project manifest
(``paths.MANIFEST``) and from arguments (``Locator.with_locations``). ``locate`` finds the project and picks the
source:

- a checkout of the repository (``paths.RepoPaths``): every resource, and ``checkout()`` for the developer and
  release commands;
- an unpacked release folder (``ReleaseLocator``, whose manifest has ``paths.RELEASE_KEY``): the files that
  ``release.data_files`` bundles. ``checkout()`` refuses (exit status 6).

A third source, such as an installed package (data from ``importlib.resources`` and a cache folder for the user), is
one more class with the methods of ``Locator`` and one more case in ``locate``. No command changes.

The catalogue functions below (``films``, ``build_to_install``, ``art_check``) are what user commands, the installer
page and the document generator read.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .builds import BuildDescription
from .errors import RefusedError, RepositoryError
from .paths import RELEASE_KEY, RepoPaths, find_root

if TYPE_CHECKING:
    from .looks.lookfile import Look
    from .looks.records import Records
    from .stock import StockFirmware


class Locator(Protocol):
    """Where the package's data is. Every command gets its resources through these methods."""

    @property
    def kind(self) -> str:
        """What kind of source this is: ``checkout`` or ``release``."""

    def where(self) -> str:
        """Return the source's folder (or other origin), for messages."""

    def with_locations(
        self,
        cache: Path | None = None,
        stock: Path | None = None,
        out_dir: Path | None = None,
    ) -> Locator:
        """Return this locator with the locations that arguments give: ``--cache``, ``--stock``, ``--out-dir``."""

    def output_folder(self) -> Path:
        """Return the folder that commands write their outputs to."""

    def stock_file(self, stock: StockFirmware) -> Path:
        """Return where the stock firmware is: the ``--stock`` file, or the file in the cache folder."""

    def downloads(self) -> bool:
        """Return True if the stock firmware may be downloaded into the cache folder (no ``--stock``)."""

    def spec_file(self, relative: str) -> Path:
        """Return the file of a patch spec that a build description names."""

    def film_records_file(self) -> Path:
        """Return the file of the film records."""

    @property
    def label_spec(self) -> Path:
        """The patch spec that shows a build's label on the camera's Firmware screen."""

    @property
    def app(self) -> Path:
        """The folder of the built installer page."""

    def pinned_build(self) -> BuildDescription:
        """Return the pinned build: the one that ``install`` writes."""

    def build(self, name: str) -> BuildDescription:
        """Return the build description called ``name`` (``NotFoundError`` if there is none)."""

    def all_builds(self) -> list[BuildDescription]:
        """Return every build description this source holds, in name order."""

    def event_dictionaries(self) -> list[Path]:
        """Return the event dictionaries of the debug log, the current one first."""

    def checkout(self) -> RepoPaths:
        """Return the checkout, for developer and release commands (``RepositoryError`` without one)."""

    def relative(self, path: Path) -> str:
        """Return ``path`` as text for a message, short if it is inside the source."""


#: What a command outside a checkout says.
NO_CHECKOUT = (
    "this command needs a checkout of the repository "
    "(git clone https://github.com/cfu288/EPM2Mod.git); "
    "the release folder has the commands for camera owners only"
)


class ReleaseLocator(RepoPaths):
    """An unpacked release folder: the pinned build, its specs, the film records, the installer page, and a cache for the download."""

    kind = "release"

    def event_dictionaries(self) -> list[Path]:
        """Refuse: the release has no event dictionaries.

        Raises:
            RepositoryError: always.
        """
        raise RepositoryError(NO_CHECKOUT)

    def checkout(self) -> RepoPaths:
        """Refuse: a release folder is not a checkout.

        Raises:
            RepositoryError: always.
        """
        raise RepositoryError(NO_CHECKOUT)


def locate(start: Path | None = None, project: Path | None = None) -> Locator:
    """Return the locator of the project ``project``, or of the project that holds ``start`` (default: the current folder).

    Raises:
        RepositoryError: if no project is found.
    """
    found = RepoPaths(find_root(start, project))
    if RELEASE_KEY in found.manifest:
        return ReleaseLocator(found.root)
    return found


def films(locator: Locator) -> Records:
    """Return the film records: every film a film file can hold, and the twelve ART entries with their Olympus names.

    Raises:
        BuildError: if the records are missing or malformed.
    """
    from .looks import records

    return records.load(locator)


def build_to_install(
    locator: Locator, name: str | None = None, allow_untested: bool = False
) -> BuildDescription:
    """Return the build that ``install`` writes: the pinned one, or the one called ``name``.

    Raises:
        NotFoundError: if there is no build of that name.
        RefusedError: if the build has no passed camera test and ``allow_untested`` is False.
    """
    description = locator.pinned_build() if name is None else locator.build(name)
    if not description.tested and not allow_untested:
        raise RefusedError(
            f"{description.name} has no passed camera test: give --allow-untested to write it anyway",
            "--allow-untested",
        )
    return description


def art_check(looks: Sequence[Look]) -> str:
    """Return what the camera's ART menu shows after a write, for the last camera step.

    The first film by slot names the change ("C200 in ART 2."), so a user sees that the file was loaded; with no
    films, the ART menu shows the art filters.
    """
    if not looks:
        return "the art filters, such as Pop Art."
    first = min(looks, key=lambda look: look.slot)
    return f"{first.name} in ART {first.slot + 1}."

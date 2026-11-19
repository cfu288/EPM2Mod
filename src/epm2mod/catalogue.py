"""The one place that knows where the package's data is: the locator, and the film catalogue.

Commands never build a repository path. They ask a ``Locator`` for each resource: the film records, the build
descriptions (by name) and the pinned build, the patch specs a build names, the downloaded Olympus firmware, the
output folder, and the event dictionaries of the debug log. ``locate`` picks the source:

- a checkout of the repository (``paths.RepoPaths``): every resource, and ``checkout()`` for the developer and
  release commands;
- an unpacked release folder (``ReleaseLocator``, marked by ``paths.RELEASE_MARKER``): the files that
  ``release.data_files`` bundles, with the same layout. ``checkout()`` refuses (exit status 5).

A third source, such as an installed package (data from ``importlib.resources`` and a cache folder for the user), is
one more class with the methods of ``Locator`` and one more case in ``locate``. No command changes.

The catalogue functions below (``films``, ``default_choices``, ``build_to_install``, ``art_check``) are what user
commands, the installer page and the document generator read.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .builds import BuildDescription
from .errors import BuildCheckError, RepositoryError
from .paths import RELEASE_MARKER, RepoPaths, find_root

if TYPE_CHECKING:
    from .looks.records import Records
    from .stock import StockFirmware


class Locator(Protocol):
    """Where the package's data is. Every command gets its resources through these methods."""

    @property
    def kind(self) -> str:
        """What kind of source this is: ``checkout`` or ``release``."""

    def where(self) -> str:
        """Return the source's folder (or other origin), for messages."""

    def output_folder(self) -> Path:
        """Return the folder that commands write their outputs to."""

    def stock_file(self, stock: StockFirmware) -> Path:
        """Return where the downloaded stock firmware is kept."""

    def spec_file(self, relative: str) -> Path:
        """Return the file of a patch spec that a build description names."""

    def film_records_file(self) -> Path:
        """Return the file of the film records."""

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
    """An unpacked release folder: the pinned build, its specs, the film records, and a cache for the download."""

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


def locate(start: Path | None = None) -> Locator:
    """Return the locator of the source that holds ``start`` (default: the current folder, then this package).

    Raises:
        RepositoryError: if no source is found.
    """
    root = find_root(start)
    if (root / RELEASE_MARKER).is_file():
        return ReleaseLocator(root)
    return RepoPaths(root)


def films(locator: Locator) -> Records:
    """Return the film records: every film a film file can hold, and the twelve ART entries.

    Raises:
        BuildError: if the records are missing or malformed.
    """
    from .looks import records

    return records.load(locator)


def default_choices(locator: Locator) -> list[str]:
    """Return the choices of the 12 default films, like ``ART1=portra-400``."""
    from .looks import records

    return records.built_in_choices(films(locator))


def build_to_install(
    locator: Locator, name: str | None = None, untested: bool = False
) -> BuildDescription:
    """Return the build that ``install`` writes: the pinned one, or the one called ``name``.

    Raises:
        NotFoundError: if there is no build of that name.
        BuildCheckError: if the build has no passed camera test and ``untested`` is False.
    """
    description = locator.pinned_build() if name is None else locator.build(name)
    if not description.tested and not untested:
        raise BuildCheckError(
            f"{description.name} has no passed camera test: give --untested to write it anyway"
        )
    return description


def art_check(
    locator: Locator, choices: Sequence[str] | None, original: bool = False
) -> str:
    """Return what the camera's ART menu shows after the install, for the last camera step.

    The first slot whose film is not its default names the change ("C200 in ART 2."), so a user sees that the
    file was loaded.
    """
    if original:
        return "the art filters, such as Pop Art."
    if choices:
        from .looks import records

        catalogue = films(locator)
        defaults = {slot.art: slot.built_in for slot in catalogue.slots}
        looks = zip(records.looks_of_choices(catalogue, choices), choices)
        for look, text in sorted(looks, key=lambda pair: pair[0].slot):
            film = text.split("=", 1)[1].lower()
            if defaults.get(look.slot + 1) != film:
                return f"{look.name} in ART {look.slot + 1}."
    return "film names, such as Portra 400."

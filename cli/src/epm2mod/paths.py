"""Where a project's files are: the project manifest.

A project folder (a checkout, or the unpacked release zip) holds ``MANIFEST`` at its top. The manifest names each
file and folder that the package reads or writes, as a path relative to the manifest's folder. The package knows no
other name of the project: ``RepoPaths`` reads every location from the manifest. Paths that come from data (a patch
spec named by a build description, a fit file named by a film list) are relative to the same folder and are turned
into absolute paths with ``RepoPaths.resolve``.

``RepoPaths`` is also the checkout's implementation of the locator (``catalogue.Locator``): the methods after the
properties are the ones that commands use. A release folder's manifest names fewer locations
(``catalogue.ReleaseLocator``).

``find_root`` finds the project: the folder that ``--project`` names, else the nearest folder at or above the current
folder that holds the manifest.
"""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, ClassVar

from .errors import BuildError, NotFoundError, RepositoryError

if TYPE_CHECKING:
    from .builds import BuildDescription
    from .stock import StockFirmware

#: The project manifest, at the top of a project folder.
MANIFEST = "epm2mod.json"
#: The manifest key that marks a release folder; its value is the release's version.
RELEASE_KEY = "release"


@dataclass(frozen=True)
class RepoPaths:
    """The locations of one project, from its manifest, and the locations that arguments give.

    Attributes:
        root: the project folder: the folder of the manifest.
        cache: the folder that keeps Olympus's firmware (``--cache``), or None for the manifest's.
        stock: a copy of Olympus's firmware to use (``--stock``), or None: the file in the cache folder, downloaded
            when it is not there.
        out_dir: the output folder (``make --out-dir``), or None for the manifest's.
    """

    root: Path
    cache: Path | None = None
    stock: Path | None = None
    out_dir: Path | None = None

    #: What kind of source this is, for messages and ``--json``.
    kind: ClassVar[str] = "checkout"

    @cached_property
    def manifest(self) -> dict[str, Any]:
        """The manifest's keys and values.

        Raises:
            RepositoryError: if the manifest is missing or is not a JSON object.
        """
        from .fileio import read_json

        path = self.root / MANIFEST
        if not path.is_file():
            raise RepositoryError(f"{self.root}: no {MANIFEST} there")
        raw = read_json(path, RepositoryError)
        if not isinstance(raw, dict):
            raise RepositoryError(f"{path}: must be a JSON object")
        return raw

    def location(self, key: str) -> Path:
        """Return the location that the manifest names by ``key``.

        Raises:
            RepositoryError: if the manifest has no such key, or its value is not a plain relative path.
        """
        value = self.manifest.get(key)
        if value is None:
            raise RepositoryError(f"{self.root / MANIFEST}: no '{key}'")
        if not isinstance(value, str) or not is_repo_relative(value):
            raise RepositoryError(
                f"{self.root / MANIFEST}: '{key}' must be a path relative to its folder"
            )
        return self.root / value

    def locations(self, key: str) -> tuple[Path, ...]:
        """Return the locations that the manifest lists by ``key``.

        Raises:
            RepositoryError: if the manifest has no such key, or its value is not a list of plain relative paths.
        """
        value = self.manifest.get(key)
        if value is None:
            raise RepositoryError(f"{self.root / MANIFEST}: no '{key}'")
        if not isinstance(value, list) or not all(
            isinstance(item, str) and is_repo_relative(item) for item in value
        ):
            raise RepositoryError(
                f"{self.root / MANIFEST}: '{key}' must be a list of paths relative to its folder"
            )
        return tuple(self.root / item for item in value)

    @property
    def pinned(self) -> Path:
        """The file that names the pinned build description."""
        return self.location("pinned")

    @property
    def builds(self) -> Path:
        """The folder of build descriptions."""
        return self.location("builds")

    @property
    def specs(self) -> Path:
        """The folder of patch specs: every spec a build or a film list names is in it."""
        return self.location("specs")

    @property
    def label_spec(self) -> Path:
        """The patch spec that shows a build's label on the camera's Firmware screen."""
        return self.location("label_spec")

    @property
    def output(self) -> Path:
        """The folder that built firmware is written to (not in git)."""
        return self.out_dir if self.out_dir is not None else self.location("output")

    @property
    def cache_folder(self) -> Path:
        """The folder that keeps Olympus's firmware."""
        return self.cache if self.cache is not None else self.location("cache")

    @property
    def readme(self) -> Path:
        """The top-level README."""
        return self.location("readme")

    @property
    def card_looks(self) -> Path:
        """A developer look list of fit files (the input of ``films pack``)."""
        return self.location("card_looks")

    @property
    def catalogue(self) -> Path:
        """The fitted films that a look file can hold."""
        return self.location("catalogue")

    @property
    def film_records(self) -> Path:
        """The films with their look records, which look files are packed from."""
        return self.location("film_records")

    @property
    def free_space_tool(self) -> Path:
        """The script that checks where patch specs put new bytes."""
        return self.location("free_space_tool")

    @property
    def lint_tool(self) -> Path:
        """The script that prints the soft report of a build: what may be harmful and is not proven safe."""
        return self.location("lint_tool")

    @property
    def emulator_checks(self) -> tuple[Path, ...]:
        """The scripts that start a firmware image in the emulator, in order."""
        return self.locations("emulator_checks")

    @property
    def firmware_map(self) -> Path:
        """A file the free-space check needs; the firmware map tool makes it."""
        return self.location("firmware_map")

    @property
    def events(self) -> Path:
        """The event dictionary of the debug log; the other JSON files in its folder are those of older builds."""
        return self.location("events")

    @property
    def documents(self) -> tuple[Path, ...]:
        """The documents that may hold generated blocks."""
        return self.locations("documents")

    @property
    def cli_reference(self) -> Path:
        """The command-line reference, generated whole."""
        return self.location("cli_reference")

    @property
    def guides(self) -> Path:
        """The folder of the feature guides."""
        return self.location("guides")

    @property
    def site_features(self) -> Path:
        """The site's feature list."""
        return self.location("site_features")

    @property
    def camera_log(self) -> Path:
        """The folder of the camera log: one file for each flash on the camera."""
        return self.location("camera_log")

    @property
    def workflows(self) -> tuple[Path, ...]:
        """The CI workflows whose runs on the release commit must have passed."""
        return self.locations("workflows")

    @property
    def app(self) -> Path:
        """The folder of the built installer page."""
        return self.location("app")

    @property
    def package(self) -> Path:
        """The folder of this package's source, which the release zip holds."""
        return self.location("package")

    @property
    def release_files(self) -> tuple[Path, ...]:
        """The files that the release zip holds at its top: the launchers, their README and the licences."""
        return self.locations("release_files")

    # The locator (``catalogue.Locator``).

    def where(self) -> str:
        """Return the source's folder, for messages."""
        return str(self.root)

    def with_locations(
        self,
        cache: Path | None = None,
        stock: Path | None = None,
        out_dir: Path | None = None,
    ) -> RepoPaths:
        """Return this locator with the locations that arguments give (None: keep the one it has)."""
        changes = {"cache": cache, "stock": stock, "out_dir": out_dir}
        return dataclasses.replace(
            self, **{key: value for key, value in changes.items() if value is not None}
        )

    def output_folder(self) -> Path:
        """Return the folder that commands write their outputs to."""
        return self.output

    def stock_file(self, stock: StockFirmware) -> Path:
        """Return where the stock firmware is: the ``--stock`` file, or the file in the cache folder."""
        if self.stock is not None:
            return self.stock
        return self.cache_folder / stock.file_name

    def downloads(self) -> bool:
        """Return True if the stock firmware may be downloaded into the cache folder (no ``--stock``)."""
        return self.stock is None

    def spec_file(self, relative: str) -> Path:
        """Return the file of a patch spec that a build description or a film list names.

        Raises:
            BuildError: if the spec is not in the patch spec folder.
        """
        path = self.resolve(relative)
        if not path.is_relative_to(self.specs):
            raise BuildError(
                f"{relative!r} is not a patch spec: it must be in {self.relative(self.specs)}/"
            )
        return path

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
        from .builds import description_path, is_build_name, load_checked

        path = description_path(self, name) if is_build_name(name) else None
        if path is None or not path.is_file():
            raise NotFoundError(
                f"no build description '{name}'; 'epm2mod builds' lists them"
            )
        return load_checked(self, path)

    def all_builds(self) -> list[BuildDescription]:
        """Return every build description, in name order."""
        from .builds import all_descriptions

        return all_descriptions(self)

    def event_dictionaries(self) -> list[Path]:
        """Return the event dictionaries of the debug log: the current one, then those of older builds."""
        current = self.events
        older = sorted(p for p in current.parent.glob("*.json") if p != current)
        return [current, *older]

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


def find_root(start: Path | None = None, project: Path | None = None) -> Path:
    """Find the project folder.

    It is ``project`` (``--project``) if given. Otherwise it is the nearest folder at or above ``start`` (default:
    the current folder) that holds the manifest.

    Raises:
        RepositoryError: if ``project`` holds no manifest, or none is found.
    """
    if project is not None:
        root = Path(project).absolute()
        if not (root / MANIFEST).is_file():
            raise RepositoryError(f"{project}: no {MANIFEST} there")
        return root
    here = (start or Path(os.getcwd())).absolute()
    for folder in (here, *here.parents):
        if (folder / MANIFEST).is_file():
            return folder
    raise RepositoryError(
        f"no {MANIFEST} in {here} or a folder above it: "
        "run the command in the project folder, or give --project DIR"
    )


def repo_paths(start: Path | None = None) -> RepoPaths:
    """Return the paths of the project that holds ``start``."""
    return RepoPaths(find_root(start))

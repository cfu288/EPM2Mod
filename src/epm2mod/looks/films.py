"""The film list: ``looks/films.json``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..builds import check_spec_path
from ..errors import BuildError
from ..fileio import read_bytes, read_json
from ..hashing import sha256_bytes
from ..paths import RepoPaths, is_repo_relative
from ..spec import UTF16
from .slots import SLOTS


@dataclass(frozen=True)
class Film:
    """One film look and the menu entry it replaces.

    Attributes:
        entry: the stock name of the art-filter menu entry.
        film: the name of the film.
        medium: how the film was simulated (slide, or negative and print material).
        label: the name shown in the camera's menu. In UTF-16 it is not longer
            than ``entry``, because it is written over that text in place.
        fit: path of the fit file, relative to the repository root.
    """

    entry: str
    film: str
    medium: str
    label: str
    fit: str

    def __post_init__(self) -> None:
        """Check the film. Every instance is valid.

        Raises:
            BuildError: if the entry is not a film slot, the label is empty,
                cannot be written as UTF-16 or is longer than the entry, or
                the fit path is not a plain path in the repository.
        """
        if self.entry not in {slot.entry for slot in SLOTS}:
            raise BuildError(f"'{self.entry}' is not a film slot")
        try:
            label, entry = self.label.encode(UTF16), self.entry.encode(UTF16)
        except UnicodeEncodeError as error:
            raise BuildError(
                f"the label cannot be written as UTF-16: {error}"
            ) from None
        if not label or "\0" in self.label or len(label) > len(entry):
            raise BuildError(
                f"the label '{self.label}' must be 1 to {len(self.entry)} "
                f"characters, not longer than the menu entry '{self.entry}'"
            )
        if not is_repo_relative(self.fit):
            raise BuildError(
                "'fit' must be a path inside the repository, written with "
                "forward slashes"
            )


@dataclass(frozen=True)
class FilmList:
    """The content of ``looks/films.json``.

    Attributes:
        films: the films: one per film slot, in menu order.
        films_spec: path of the patch spec that holds the looks.
        labels_spec: path of the patch spec that holds the menu labels.
        structure_spec: path of the patch spec with what the slots share.
    """

    films: tuple[Film, ...]
    films_spec: str
    labels_spec: str
    structure_spec: str

    def __post_init__(self) -> None:
        """Check the list. Every instance is valid.

        Raises:
            BuildError: if the films are not one per slot in menu order, or two
                of the three specs are the same file.
        """
        expected = [slot.entry for slot in SLOTS]
        if [film.entry for film in self.films] != expected:
            raise BuildError(
                "the films must be one per film slot, in menu order: "
                + ", ".join(expected)
            )
        if len({self.films_spec, self.labels_spec, self.structure_spec}) != 3:
            raise BuildError("the three generated specs must be three files")

    @property
    def spec_paths(self) -> tuple[str, str, str]:
        """The paths of the looks spec, the labels spec and the structure spec."""
        return (self.films_spec, self.labels_spec, self.structure_spec)


_TOP_KEYS = {"specs", "films"}
_SPEC_KEYS = {"films", "labels", "structure"}
_FILM_KEYS = {"entry", "film", "medium", "label", "fit"}


def _closed(raw: dict[str, Any], allowed: set[str], where: str) -> None:
    """Raise if ``raw`` has a key that is not allowed."""
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise BuildError(f"{where}: unknown key(s): {', '.join(unknown)}")


def _text(raw: dict[str, Any], key: str, where: str) -> str:
    """Return a non-empty text field."""
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise BuildError(f"{where}: '{key}' must be text")
    return value


def load_films(paths: RepoPaths) -> FilmList:
    """Read and check the film list.

    Raises:
        BuildError: if the file is missing or malformed, has an unknown key, or
            does not describe a valid ``FilmList``.
    """
    path = paths.films
    raw = read_json(path, BuildError)
    if not isinstance(raw, dict) or not isinstance(raw.get("films"), list):
        raise BuildError(f"{path}: must be an object with a 'films' list")
    specs = raw.get("specs")
    if not isinstance(specs, dict):
        raise BuildError(f"{path}: must have a 'specs' object")
    _closed(raw, _TOP_KEYS, str(path))
    _closed(specs, _SPEC_KEYS, f"{path} specs")
    films = []
    for index, item in enumerate(raw["films"]):
        where = f"{path} film {index}"
        if not isinstance(item, dict):
            raise BuildError(f"{where}: must be an object")
        _closed(item, _FILM_KEYS, where)
        try:
            films.append(
                Film(
                    entry=_text(item, "entry", where),
                    film=_text(item, "film", where),
                    medium=_text(item, "medium", where),
                    label=_text(item, "label", where),
                    fit=_text(item, "fit", where),
                )
            )
        except BuildError as error:
            text = str(error)
            raise BuildError(
                text if text.startswith(where) else f"{where}: {text}"
            ) from None
    try:
        return FilmList(
            films=tuple(films),
            films_spec=check_spec_path(specs.get("films"), f"{path} specs"),
            labels_spec=check_spec_path(specs.get("labels"), f"{path} specs"),
            structure_spec=check_spec_path(specs.get("structure"), f"{path} specs"),
        )
    except BuildError as error:
        text = str(error)
        raise BuildError(
            text if text.startswith(str(path)) else f"{path}: {text}"
        ) from None


def inputs_digest(paths: RepoPaths, film_list: FilmList) -> str:
    """Return one SHA-256 over the generator's data: the film list and the fit files.

    The generated specs record this value. It lets a test see, without the
    stock firmware and without numpy, that a spec was generated from the data
    that is in the repository now.

    Raises:
        BuildError: if a fit file cannot be read.
    """
    parts = [read_bytes(paths.films, BuildError)]
    parts += [
        read_bytes(paths.resolve(film.fit), BuildError) for film in film_list.films
    ]
    return sha256_bytes(b"".join(sha256_bytes(part).encode() for part in parts))


def specs_with_other_inputs(paths: RepoPaths) -> list[str]:
    """Return the generated specs that were not made from the current data.

    A spec is listed if it is missing, or the ``inputs_sha256`` that it records
    is not ``inputs_digest`` of the film list and fit files as they are now.
    This check needs neither the stock firmware nor numpy.
    """
    film_list = load_films(paths)
    digest = inputs_digest(paths, film_list)
    other = []
    for spec_path in film_list.spec_paths:
        path = paths.resolve(spec_path)
        raw = read_json(path, BuildError) if path.exists() else None
        if not isinstance(raw, dict) or raw.get("inputs_sha256") != digest:
            other.append(spec_path)
    return other

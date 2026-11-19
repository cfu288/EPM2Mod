"""The film list: ``data/films/films.json``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..builds import check_spec_path
from ..errors import BuildError
from ..fileio import read_bytes, read_json
from ..hashing import sha256_bytes
from ..paths import RepoPaths, is_repo_relative
from ..spec import UTF16
from .slots import EXTRA_SLOTS, MONO_SLOT, SLOTS


@dataclass(frozen=True)
class Film:
    """One film look and the menu entry it replaces.

    Attributes:
        entry: the stock name of the art-filter menu entry.
        film: the name of the film.
        medium: how the film was simulated (slide, or negative and print material).
        label: the name shown in the camera's menu. In UTF-16 it is not longer
            than ``entry``: for the first seven films it is written over that
            text in place.
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
        entries = {slot.entry for slot in SLOTS} | {slot.entry for slot in EXTRA_SLOTS}
        if self.entry not in entries:
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
                f"UTF-16 units, not longer than the menu entry '{self.entry}'"
            )
        if not is_repo_relative(self.fit):
            raise BuildError(
                "'fit' must be a path inside the repository, written with "
                "forward slashes"
            )


@dataclass(frozen=True)
class FilmList:
    """The content of ``data/films/films.json``.

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
    This check needs neither the stock firmware nor numpy, so the tests can
    make it on a clean clone; ``generate.stale`` is the full check.
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


@dataclass(frozen=True)
class MoreFilmList:
    """The content of ``data/films/more-films.json``: the films beyond the first seven.

    Attributes:
        films: the films: one per extra slot, in menu order.
        structure_spec: path of the patch spec with the code and table entries
            that make the extra slots.
        looks_spec: path of the patch spec that holds the looks.
        entry_specs: one path per film: the patch spec that gives the film's
            menu entry its hidden stored value. Without that spec the entry is
            the stock art filter.
    """

    films: tuple[Film, ...]
    structure_spec: str
    looks_spec: str
    entry_specs: tuple[str, ...]

    def __post_init__(self) -> None:
        """Check the list. Every instance is valid.

        Raises:
            BuildError: if the films are not one per extra slot in menu order,
                there is not one entry spec per film, or two specs are the
                same file.
        """
        expected = [slot.entry for slot in EXTRA_SLOTS]
        if [film.entry for film in self.films] != expected:
            raise BuildError(
                "the films must be one per extra film slot, in menu order: "
                + ", ".join(expected)
            )
        if len(self.entry_specs) != len(self.films):
            raise BuildError("there must be one entry spec per film")
        if len(set(self.spec_paths)) != len(self.spec_paths):
            raise BuildError("the generated specs must be different files")

    @property
    def spec_paths(self) -> tuple[str, ...]:
        """The paths of the structure spec, the looks spec and the entry specs."""
        return (self.structure_spec, self.looks_spec, *self.entry_specs)


_MORE_SPEC_KEYS = {"structure", "looks", "entries"}


def _load_film(item: Any, where: str) -> Film:
    """Return one film of a film list file."""
    if not isinstance(item, dict):
        raise BuildError(f"{where}: must be an object")
    _closed(item, _FILM_KEYS, where)
    try:
        return Film(
            entry=_text(item, "entry", where),
            film=_text(item, "film", where),
            medium=_text(item, "medium", where),
            label=_text(item, "label", where),
            fit=_text(item, "fit", where),
        )
    except BuildError as error:
        text = str(error)
        raise BuildError(
            text if text.startswith(where) else f"{where}: {text}"
        ) from None


def load_more_films(paths: RepoPaths) -> MoreFilmList:
    """Read and check the list of the films beyond the first seven.

    Raises:
        BuildError: if the file is missing or malformed, has an unknown key, or
            does not describe a valid ``MoreFilmList``.
    """
    path = paths.more_films
    raw = read_json(path, BuildError)
    if not isinstance(raw, dict) or not isinstance(raw.get("films"), list):
        raise BuildError(f"{path}: must be an object with a 'films' list")
    specs = raw.get("specs")
    if not isinstance(specs, dict) or not isinstance(specs.get("entries"), list):
        raise BuildError(f"{path}: must have a 'specs' object with an 'entries' list")
    _closed(raw, _TOP_KEYS, str(path))
    _closed(specs, _MORE_SPEC_KEYS, f"{path} specs")
    films = [
        _load_film(item, f"{path} film {index}")
        for index, item in enumerate(raw["films"])
    ]
    where = f"{path} specs"
    try:
        return MoreFilmList(
            films=tuple(films),
            structure_spec=check_spec_path(specs.get("structure"), where),
            looks_spec=check_spec_path(specs.get("looks"), where),
            entry_specs=tuple(
                check_spec_path(entry, where) for entry in specs["entries"]
            ),
        )
    except BuildError as error:
        text = str(error)
        raise BuildError(
            text if text.startswith(str(path)) else f"{path}: {text}"
        ) from None


def more_inputs_digest(paths: RepoPaths, film_list: MoreFilmList) -> str:
    """Return one SHA-256 over ``data/films/more-films.json`` and its fit files.

    Raises:
        BuildError: if a fit file cannot be read.
    """
    parts = [read_bytes(paths.more_films, BuildError)]
    parts += [
        read_bytes(paths.resolve(film.fit), BuildError) for film in film_list.films
    ]
    return sha256_bytes(b"".join(sha256_bytes(part).encode() for part in parts))


@dataclass(frozen=True)
class BwFilmList:
    """The content of ``data/films/films-12-bw.json``.

    The list is a variant of ``MoreFilmList``. The entry of the
    black-and-white slot holds a black-and-white film and keeps its stock
    stored value. The colour film that ``MoreFilmList`` has in that entry
    moves to another entry of the extra slots, and the film of that entry
    leaves the list.

    Attributes:
        mono: the black-and-white film.
        moved_to: the stock name of the entry that the colour film moves to.
        entry_spec: path of the patch spec that gives ``moved_to`` the colour film.
        mono_spec: path of the patch spec that holds the black-and-white look.
        refits: later fits of the black-and-white film, in order: (path of
            the fit file, path of its patch spec). A build takes the spec of
            one refit after ``mono_spec``.
    """

    mono: Film
    moved_to: str
    entry_spec: str
    mono_spec: str
    refits: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        """Check the list. Every instance is valid.

        Raises:
            BuildError: if the black-and-white film is not in the entry of the
                black-and-white slot, ``moved_to`` is not another extra slot,
                or the two specs are the same file.
        """
        if self.mono.entry != MONO_SLOT.entry:
            raise BuildError(
                f"the black-and-white film must be in the entry '{MONO_SLOT.entry}'"
            )
        others = [slot.entry for slot in EXTRA_SLOTS if slot.entry != MONO_SLOT.entry]
        if self.moved_to not in others:
            raise BuildError("'moved_to' must be one of: " + ", ".join(others))
        if len(set(self.spec_paths)) != len(self.spec_paths):
            raise BuildError("the generated specs must be different files")
        if len(self.refits) > len(MONO_SLOT.spare_tables):
            raise BuildError(
                f"the slot has a table for {len(MONO_SLOT.spare_tables)} refit(s) only"
            )
        for fit, _ in self.refits:
            if not is_repo_relative(fit):
                raise BuildError("the fit of a refit must be a path in the repository")

    @property
    def spec_paths(self) -> tuple[str, ...]:
        """The paths of the entry spec, the black-and-white spec and the refit specs."""
        return (self.entry_spec, self.mono_spec, *(spec for _, spec in self.refits))


_BW_TOP_KEYS = {"specs", "mono", "moved_to", "refits"}
_REFIT_KEYS = {"fit", "spec"}
_BW_SPEC_KEYS = {"entry", "mono"}


def load_bw_films(paths: RepoPaths) -> BwFilmList:
    """Read and check the film list with a black-and-white film.

    Raises:
        BuildError: if the file is missing or malformed, has an unknown key, or
            does not describe a valid ``BwFilmList``.
    """
    path = paths.bw_films
    raw = read_json(path, BuildError)
    if not isinstance(raw, dict):
        raise BuildError(f"{path}: must be an object")
    specs = raw.get("specs")
    if not isinstance(specs, dict):
        raise BuildError(f"{path}: must have a 'specs' object")
    _closed(raw, _BW_TOP_KEYS, str(path))
    _closed(specs, _BW_SPEC_KEYS, f"{path} specs")
    where = f"{path} specs"
    listed = raw.get("refits", [])
    if not isinstance(listed, list):
        raise BuildError(f"{path}: 'refits' must be a list")
    refits = []
    for index, item in enumerate(listed):
        here = f"{path} refit {index}"
        if not isinstance(item, dict):
            raise BuildError(f"{here}: must be an object")
        _closed(item, _REFIT_KEYS, here)
        refits.append(
            (_text(item, "fit", here), check_spec_path(item.get("spec"), here))
        )
    try:
        return BwFilmList(
            mono=_load_film(raw.get("mono"), f"{path} mono"),
            moved_to=_text(raw, "moved_to", str(path)),
            entry_spec=check_spec_path(specs.get("entry"), where),
            mono_spec=check_spec_path(specs.get("mono"), where),
            refits=tuple(refits),
        )
    except BuildError as error:
        text = str(error)
        raise BuildError(
            text if text.startswith(str(path)) else f"{path}: {text}"
        ) from None


def bw_inputs_digest(paths: RepoPaths, film_list: BwFilmList) -> str:
    """Return one SHA-256 over the data of the list with a black-and-white film.

    The data: ``data/films/films-12-bw.json``, the fit of its film, the list of the
    films beyond the first seven (its labels name the film that moves), and
    the fits of the refits.

    Raises:
        BuildError: if a file cannot be read.
    """
    parts = [
        read_bytes(paths.bw_films, BuildError),
        read_bytes(paths.resolve(film_list.mono.fit), BuildError),
        read_bytes(paths.more_films, BuildError),
    ]
    parts += [read_bytes(paths.resolve(fit), BuildError) for fit, _ in film_list.refits]
    return sha256_bytes(b"".join(sha256_bytes(part).encode() for part in parts))

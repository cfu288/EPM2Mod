"""The film list: ``looks/films.json``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

from ..errors import BuildError
from ..paths import RepoPaths
from .slots import SLOTS


@dataclass(frozen=True)
class Film:
    """One film look and the menu entry it replaces.

    Attributes:
        entry: the stock name of the art-filter menu entry.
        film: the name of the film.
        medium: how the film was simulated (slide, or negative and print material).
        label: the name shown in the camera's menu; not longer than ``entry``.
        fit: path of the fit file, relative to the repository root.
    """

    entry: str
    film: str
    medium: str
    label: str
    fit: str


@dataclass(frozen=True)
class FilmList:
    """The content of ``looks/films.json``.

    Attributes:
        films: the films, in menu order.
        films_spec: path of the patch spec that holds the looks.
        labels_spec: path of the patch spec that holds the menu labels.
        structure_spec: path of the patch spec with what the slots share.
    """

    films: Tuple[Film, ...]
    films_spec: str
    labels_spec: str
    structure_spec: str


def _text(raw: Dict[str, Any], key: str, where: str) -> str:
    """Return a non-empty text field."""
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise BuildError(f"{where}: '{key}' must be text")
    return value


def load_films(paths: RepoPaths) -> FilmList:
    """Read and check the film list.

    Raises:
        BuildError: if the file is missing or malformed, an entry is not a film
            slot or appears twice, a slot has no film, or a label is longer
            than the entry it replaces.
    """
    path: Path = paths.films
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise BuildError(f"{path}: cannot be read: {error.strerror}") from None
    except ValueError as error:
        raise BuildError(f"{path}: not JSON: {error}") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("films"), list):
        raise BuildError(f"{path}: must be an object with a 'films' list")
    specs = raw.get("specs")
    if not isinstance(specs, dict):
        raise BuildError(f"{path}: must have a 'specs' object")
    films = []
    for index, item in enumerate(raw["films"]):
        where = f"{path} film {index}"
        if not isinstance(item, dict):
            raise BuildError(f"{where}: must be an object")
        film = Film(
            entry=_text(item, "entry", where),
            film=_text(item, "film", where),
            medium=_text(item, "medium", where),
            label=_text(item, "label", where),
            fit=_text(item, "fit", where),
        )
        if len(film.label) > len(film.entry):
            raise BuildError(
                f"{where}: the label '{film.label}' is longer than the menu "
                f"entry '{film.entry}' that it replaces"
            )
        films.append(film)
    entries = [film.entry for film in films]
    expected = [slot.entry for slot in SLOTS]
    if entries != expected:
        raise BuildError(
            f"{path}: the films must be one per film slot, in menu order: "
            f"{', '.join(expected)}"
        )
    return FilmList(
        films=tuple(films),
        films_spec=_text(specs, "films", f"{path} specs"),
        labels_spec=_text(specs, "labels", f"{path} specs"),
        structure_spec=_text(specs, "structure", f"{path} specs"),
    )

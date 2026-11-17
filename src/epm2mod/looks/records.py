"""The film records: ``looks/film-records.json``.

The one list of films that look files are packed from: by ``epm2mod looks pack``, the local app and the web site
(which reads the same file). Each film has its look record (1,708 bytes, base64) for slot 0 under the film's name;
a look file sets the slot and packs the records (``lookfile.pack``). ``slots`` gives the twelve ART entries in menu
order, with the id of the film each holds when no look is loaded.

``lookpack.web_data`` makes the file from the fit files (``web/scripts/export_films.py``); a test fails when it is
out of date. This module needs only the standard library.
"""

from __future__ import annotations

import base64
import binascii
import dataclasses
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ..errors import BuildError, LookFileError
from ..fileio import read_json
from ..paths import RepoPaths
from .lookfile import MENU_ENTRIES, Look, decode_record


@dataclass(frozen=True)
class Film:
    """A film that a look file can hold.

    Attributes:
        id: the short name used on the command line, for example ``velvia``.
        name: the name the camera shows, at most 16 characters.
        film: the film's full name.
        kind: what kind of film it is, in a few words (for example "Slide").
        medium: how the film was simulated.
        note: a remark for the list (where it is built in, its accuracy), or "".
        look: the film's look, in slot 0 under ``name``.
    """

    id: str
    name: str
    film: str
    kind: str
    medium: str
    note: str
    look: Look


@dataclass(frozen=True)
class Slot:
    """An ART entry of the camera's menu.

    Attributes:
        art: the entry's number in the camera's menus, 1 to 12.
        entry: the entry's stock Olympus name.
        built_in: the id of the film the entry holds when no look is loaded.
    """

    art: int
    entry: str
    built_in: str


@dataclass(frozen=True)
class Records:
    """The content of ``looks/film-records.json``.

    Attributes:
        films: the films by id, in file order.
        slots: the twelve ART entries, in menu order.
    """

    films: dict[str, Film]
    slots: tuple[Slot, ...]


_TEXTS = ("id", "name", "film", "kind", "medium", "note")


def _film(item: Any, where: str) -> Film:
    """Return one film of the file.

    Raises:
        BuildError: if the item is malformed or its record is not a valid look.
    """
    if not isinstance(item, dict) or set(item) != {*_TEXTS, "record"}:
        raise BuildError(f"{where}: needs exactly {sorted({*_TEXTS, 'record'})}")
    if not all(isinstance(item[key], str) for key in item):
        raise BuildError(f"{where}: every field is a text")
    try:
        look = decode_record(base64.b64decode(item["record"], validate=True))
    except (binascii.Error, LookFileError) as error:
        raise BuildError(f"{where}: a bad record ({error})") from None
    if look.slot != 0 or look.name != item["name"]:
        raise BuildError(
            f"{where}: the record is not for slot 0 under '{item['name']}'"
        )
    return Film(**{key: item[key] for key in _TEXTS}, look=look)


def load(paths: RepoPaths) -> Records:
    """Return the film records.

    Raises:
        BuildError: if the file is missing or malformed.
    """
    path = paths.film_records
    raw: Any = read_json(path, BuildError)
    if not isinstance(raw, dict) or set(raw) != {"films", "slots"}:
        raise BuildError(f"{path}: an object with 'films' and 'slots'")
    if not isinstance(raw["films"], list) or not isinstance(raw["slots"], list):
        raise BuildError(f"{path}: 'films' and 'slots' are lists")
    films: dict[str, Film] = {}
    for number, item in enumerate(raw["films"], start=1):
        film = _film(item, f"{path}, film {number}")
        if film.id in films:
            raise BuildError(f"{path}: film '{film.id}' twice")
        films[film.id] = film
    slots = []
    for number, item in enumerate(raw["slots"], start=1):
        if not isinstance(item, dict) or set(item) != {"art", "entry", "builtIn"}:
            raise BuildError(f"{path}, slot {number}: needs 'art', 'entry', 'builtIn'")
        if number > len(MENU_ENTRIES) or item["art"] != number:
            raise BuildError(f"{path}, slot {number}: 'art' must be {number}")
        if item["entry"] != MENU_ENTRIES[number - 1] or item["builtIn"] not in films:
            raise BuildError(f"{path}, slot {number}: a wrong entry or film")
        slots.append(Slot(number, item["entry"], item["builtIn"]))
    if len(slots) != len(MENU_ENTRIES):
        raise BuildError(f"{path}: {len(MENU_ENTRIES)} slots")
    return Records(films, tuple(slots))


#: A choice on the command line: ART<n>=<film id>.
_CHOICE = re.compile(r"^ART(\d{1,2})=([a-z0-9-]+)$", re.IGNORECASE)


def is_choice(text: str) -> bool:
    """Return True if a command-line argument is a choice like ``ART2=velvia``."""
    return _CHOICE.match(text) is not None


def looks_of_choices(records: Records, choices: Sequence[str]) -> list[Look]:
    """Return the looks of choices like ``ART2=velvia``, in the order given.

    ART<n> is the art filter's number in the camera's menus (1 to 12); the film is an id of the records. The camera
    shows the film's own name.

    Raises:
        BuildError: if a choice is malformed, names an unknown film or an ART number twice.
    """
    looks: list[Look] = []
    seen: set[int] = set()
    for text in choices:
        match = _CHOICE.match(text)
        if match is None:
            raise BuildError(
                f"'{text}': write ART<1-12>=<film>, for example ART2=velvia"
            )
        number, film_id = int(match.group(1)), match.group(2).lower()
        if not 1 <= number <= len(MENU_ENTRIES) or number in seen:
            raise BuildError(f"'{text}': ART 1 to {len(MENU_ENTRIES)}, each once")
        if film_id not in records.films:
            raise BuildError(
                f"'{text}': no film '{film_id}'; 'epm2mod looks list' shows them"
            )
        seen.add(number)
        looks.append(dataclasses.replace(records.films[film_id].look, slot=number - 1))
    return looks


def built_in_choices(records: Records) -> list[str]:
    """Return the choices of the look file that holds each slot's built-in film."""
    return [f"ART{slot.art}={slot.built_in}" for slot in records.slots]

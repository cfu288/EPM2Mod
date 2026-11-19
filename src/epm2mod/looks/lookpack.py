"""Make look files for the SD card from the fit files (``web/scripts/export_films.py`` makes the film records with it).

A look list (``data/films/card-looks.json``) names, for each menu entry, a fit file
and the name of the look::

    {"looks": [{"entry": "Pop Art", "name": "Portra", "fit": "data/films/fits/portra.npz"}, ...]}

A fit with tone curves (``G``) gives a colour look; a fit with an art matrix
and two tone tables (``A``, ``T``, ``L``) gives a black-and-white look. The
tone curves of a colour look are the fit's curves rounded and kept rising. The
camera makes each tone table from them as the film generator does
(``camera_table``), so a look loaded from the card gives the same tables as a
look built into the firmware.

This module needs numpy.
"""

from __future__ import annotations

import base64
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..errors import BuildError, LookFileError
from ..fileio import read_json
from ..paths import RepoPaths, is_repo_relative
from .generate import Fit, _array, chroma_record, load_fit, whole_numbers
from .lookfile import (
    CURVE_MAX,
    encode_record,
    CURVE_POINTS,
    MENU_ENTRIES,
    TABLE_ENTRIES,
    ColourLook,
    Look,
    MonoLook,
)

_I16 = (-0x8000, 0x7FFF)


def colour_look(fit: Fit, slot: int, name: str, where: str) -> ColourLook:
    """Return the colour look of a fit with tone curves.

    Raises:
        BuildError: if the fit lacks an array or holds values that do not fit.
        LookFileError: if the look does not fit the file format.
    """
    try:
        curves = np.asarray(_array(fit, "G", where), dtype=np.float64)
    except (TypeError, ValueError):
        raise BuildError(f"{where}: 'G' must be numbers") from None
    if curves.shape != (3, CURVE_POINTS) or not np.all(np.isfinite(curves)):
        raise BuildError(f"{where}: 'G' must be 3 curves of {CURVE_POINTS} numbers")
    rising = np.clip(np.round(np.maximum.accumulate(curves, axis=1)), 0, CURVE_MAX)
    return ColourLook(
        slot=slot,
        name=name,
        gain=whole_numbers(_array(fit, "gain", where), 1, 0, 0xFFFF, "'gain'", where)[
            0
        ],
        saturation=tuple(
            whole_numbers(_array(fit, "S", where), 6, *_I16, "'S'", where)
        ),
        hue=tuple(whole_numbers(_array(fit, "H", where), 6, *_I16, "'H'", where)),
        matrix=tuple(whole_numbers(_array(fit, "A", where), 9, *_I16, "'A'", where)),
        chroma=chroma_record(fit, where),
        curves=tuple(tuple(int(v) for v in curve) for curve in rising),
    )


def mono_look(fit: Fit, slot: int, name: str, where: str) -> MonoLook:
    """Return the black-and-white look of a fit with ``A``, ``T`` and ``L``.

    Raises:
        BuildError: if the fit lacks an array or holds values that do not fit.
        LookFileError: if the look does not fit the file format.
    """

    def table(key: str) -> tuple[int, ...]:
        """Return a 256-entry tone table of the fit."""
        values = _array(fit, key, where)
        return tuple(
            whole_numbers(values, TABLE_ENTRIES, 0, CURVE_MAX, f"'{key}'", where)
        )

    matrix = whole_numbers(_array(fit, "A", where), 9, *_I16, "'A'", where)
    return MonoLook(slot, name, tuple(matrix), table("T"), table("L"))


def look_of_fit(fit: Fit, entry: str, name: str, where: str) -> Look:
    """Return the look of a fit for a menu entry: colour if it has tone curves.

    Raises:
        BuildError: if the entry is not an art-filter menu entry or the fit is wrong.
        LookFileError: if the look does not fit the file format.
    """
    if entry not in MENU_ENTRIES:
        raise BuildError(f"'{entry}' is not an art-filter menu entry")
    slot = MENU_ENTRIES.index(entry)
    if "G" in fit:
        return colour_look(fit, slot, name, where)
    return mono_look(fit, slot, name, where)


def load_list(paths: RepoPaths, path: Path) -> list[Look]:
    """Return the looks of a look list, in its order.

    Raises:
        BuildError: if the list or a fit file is wrong.
        LookFileError: if a look does not fit the file format.
    """
    raw: Any = read_json(path, BuildError)
    looks = raw.get("looks") if isinstance(raw, dict) else None
    if not isinstance(looks, list):
        raise BuildError(f"{path}: a look list is an object with a list 'looks'")
    result = []
    for number, item in enumerate(looks, start=1):
        where = f"{path}, look {number}"
        if not isinstance(item, dict) or set(item) != {"entry", "name", "fit"}:
            raise BuildError(f"{where}: needs exactly 'entry', 'name' and 'fit'")
        entry, name, fit = item["entry"], item["name"], item["fit"]
        if not all(isinstance(text, str) for text in (entry, name, fit)):
            raise BuildError(f"{where}: 'entry', 'name' and 'fit' are texts")
        if not is_repo_relative(fit):
            raise BuildError(f"{where}: 'fit' must be a path inside the repository")
        try:
            result.append(look_of_fit(load_fit(paths.resolve(fit)), entry, name, fit))
        except LookFileError as error:
            raise LookFileError(f"{where}: {error}") from None
    return result


@dataclass(frozen=True)
class CatalogueFilm:
    """A fitted film that a look file can hold (``data/films/catalogue.json``).

    Attributes:
        id: the short name used on the command line, for example ``velvia``.
        name: the name the camera shows, at most 16 characters.
        film: the film's full name.
        kind: what kind of film it is, in a few words (for example "Slide").
        medium: how the film was simulated.
        fit: path of the fit file, relative to the repository root.
        note: a remark for the list (its accuracy, or how it was fitted), or "".
    """

    id: str
    name: str
    film: str
    kind: str
    medium: str
    fit: str
    note: str


def load_catalogue(paths: RepoPaths) -> dict[str, CatalogueFilm]:
    """Return the fitted films of ``data/films/catalogue.json`` by id, in file order.

    Raises:
        BuildError: if the catalogue is missing or malformed.
    """
    raw: Any = read_json(paths.catalogue, BuildError)
    films = raw.get("films") if isinstance(raw, dict) else None
    if not isinstance(films, list):
        raise BuildError(f"{paths.catalogue}: an object with a list 'films'")
    out: dict[str, CatalogueFilm] = {}
    keys = {"id", "name", "film", "kind", "medium", "fit", "note"}
    for item in films:
        if not isinstance(item, dict) or set(item) != keys:
            raise BuildError(f"{paths.catalogue}: each film has exactly {sorted(keys)}")
        if not all(isinstance(item[k], str) for k in keys):
            raise BuildError(f"{paths.catalogue}: every field is a text")
        film = CatalogueFilm(**item)
        if film.id in out or not is_repo_relative(film.fit):
            raise BuildError(f"{paths.catalogue}: '{film.id}' twice, or a bad fit path")
        out[film.id] = film
    return out


def web_data(paths: RepoPaths) -> dict[str, Any]:
    """Return the film records (``data/films/film-records.json``, read by ``records.load``).

    ``films``: the catalogue, each film with its look record (1,708 bytes, base64) for slot 0 under the film's name.
    ``slots``: the twelve ART entries in menu order, with the Olympus art filter that each one keeps when a look
    file names no film for it.

    Raises:
        BuildError: if the catalogue is wrong.
    """
    catalogue = load_catalogue(paths)
    films = []
    for film in catalogue.values():
        look = look_of_fit(
            load_fit(paths.resolve(film.fit)), MENU_ENTRIES[0], film.name, film.fit
        )
        record = encode_record(look)
        films.append(
            {
                "id": film.id,
                "name": film.name,
                "film": film.film,
                "kind": film.kind,
                "medium": film.medium,
                "note": film.note,
                "record": base64.b64encode(record).decode("ascii"),
            }
        )
    slots = [
        {"art": number, "entry": entry}
        for number, entry in enumerate(MENU_ENTRIES, start=1)
    ]
    return {"films": films, "slots": slots}


def camera_table(curve: tuple[int, ...], default: bytes) -> bytes:
    """Return the tone table the camera makes from a curve and a default table.

    Entry k is the curve at the default table's entry k, kept rising: what
    ``generate.pack_table`` gives for the same curve.
    """
    values = struct.unpack(f"<{TABLE_ENTRIES}H", default)
    out, top = [], 0
    for value in values:
        top = max(top, curve[min(value, CURVE_MAX)])
        out.append(top)
    return struct.pack(f"<{TABLE_ENTRIES}H", *out)

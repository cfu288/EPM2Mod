"""Generate the film-look patch specs from the film list and the fit files.

Three specs come out:

* the looks: for every film slot, its tone tables, saturation gains, six-axis
  values, matrix and chroma curves;
* the labels: the names of the seven menu entries, in every language table
  that holds the stock name as a whole string;
* the structure: what the slots share (the identity look table copied over
  three look tables, and the tone-curve handler of the Light Tone codes).

Every operation states the bytes it replaces. They are the bytes of the stock
firmware, except for a matrix table that an earlier spec creates: there the
expected bytes are the identity matrix that the earlier spec writes.

A spec file holds generated fields (name, attribution, description, operations,
base, base_sha256 and inputs_sha256, a digest of the film list and the fit
files) and notes that people write, above all ``status``, the note about the
camera test. ``write`` replaces the generated fields. It keeps the notes if
the operations did not change; if they changed, ``status`` is reset and
``expected_sha256`` is dropped, because they describe other bytes.

This module needs numpy.
"""

from __future__ import annotations

import re
import struct
import zipfile
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..container import parse
from ..errors import BuildError
from ..fileio import read_json, write_json
from ..paths import RepoPaths
from ..spec import UTF16, BytesOp, Op, op_to_json
from ..stock import EPM2_V16, StockFirmware, read_stock
from . import slots
from .films import Film, inputs_digest, load_films

FloatArray = NDArray[np.float64]
#: A fit file: arrays by name.
Fit = Mapping[str, NDArray[Any]]

ATTRIBUTION = (
    "Film look data derived from spektrafilm by Andrea Volpato, "
    "https://github.com/andreavolpato/spektrafilm. Licensed CC BY-SA 4.0. "
    "Modified: fitted to the Olympus E-PM2's adjustable stages. See NOTICE.md."
)
NEW_STATUS = "built, NOT camera-tested"
#: Index of the container block that holds the menu texts.
TEXT_BLOCK = 1
#: Index of the container block that holds the program and its tables.
PROGRAM_BLOCK = 0
#: A menu text is a whole string if it follows a string end or the '@' of a tag.
_STRING_STARTS = (b"\0\0", "@".encode(UTF16))
_STRING_END = b"\0\0"
_CHROMA_KNOTS = 16
#: How many slope bytes each chroma curve stores: Cb, then Cr.
_CHROMA_SLOPES = {"Cb": 17, "Cr": 16}
_CHROMA_SLOPE_ARRAY = 17
#: The spec fields that the generator owns. ``status`` is written by people.
_GENERATED_KEYS = (
    "name",
    "attribution",
    "description",
    "ops",
    "base",
    "base_sha256",
    "inputs_sha256",
)


@dataclass(frozen=True)
class GeneratedSpec:
    """A patch spec made by the generator.

    Attributes:
        path: where the spec belongs, relative to the repository root.
        description: text for the spec's ``description`` field.
        ops: the operations.
        inputs_sha256: digest of the film list and fit files it was made from.
        attribution: text for an ``attribution`` field, or None.
    """

    path: str
    description: str
    ops: tuple[Op, ...]
    inputs_sha256: str
    attribution: str | None = None

    @property
    def name(self) -> str:
        """The spec's name: its file name without ``.json``."""
        return Path(self.path).stem

    def generated_fields(self, stock: StockFirmware) -> dict[str, Any]:
        """Return the JSON fields that the generator owns, in file order."""
        fields: dict[str, Any] = {"name": self.name}
        if self.attribution is not None:
            fields["attribution"] = self.attribution
        fields.update(
            description=self.description,
            ops=[op_to_json(op) for op in self.ops],
            base=stock.relative_path,
            base_sha256=stock.sha256,
            inputs_sha256=self.inputs_sha256,
        )
        return fields


class Program:
    """Read access to block 0 of the stock firmware by run-time address."""

    def __init__(self, payload: bytes) -> None:
        """Wrap the unscrambled payload of block 0."""
        self._payload = payload

    def read(self, address: int, length: int) -> bytes:
        """Return ``length`` bytes at a run-time address.

        Raises:
            BuildError: if the range is not inside block 0.
        """
        offset = address - slots.BLOCK0_BASE
        if offset < 0 or offset + length > len(self._payload):
            raise BuildError(f"address {address:#x} is outside block 0")
        return self._payload[offset : offset + length]

    def record(self, address: int) -> tuple[int, ...]:
        """Return the eight table addresses of a tone record."""
        raw = self.read(address, 4 * slots.RECORD_TABLES)
        return tuple(struct.unpack(f"<{slots.RECORD_TABLES}I", raw))

    def table(self, address: int) -> FloatArray:
        """Return the 256 values of a tone table."""
        raw = self.read(address, slots.TABLE_BYTES)
        values = struct.unpack(f"<{slots.TABLE_ENTRIES}H", raw)
        return np.array(values, dtype=np.float64)

    def op(self, address: int, new: bytes, expect: bytes | None = None) -> BytesOp:
        """Return an operation that writes ``new`` at a run-time address.

        ``expect`` defaults to the stock bytes at that address.
        """
        old = self.read(address, len(new)) if expect is None else expect
        return BytesOp(PROGRAM_BLOCK, address - slots.BLOCK0_BASE, old, new)


def pack_table(curve: FloatArray) -> bytes:
    """Pack a tone table: values rounded, kept rising and limited to 10 bits."""
    values = np.clip(
        np.round(np.maximum.accumulate(curve)), 0, slots.CURVE_POINTS - 1
    ).astype(int)
    return struct.pack(f"<{slots.TABLE_ENTRIES}H", *values.tolist())


def _array(fit: Fit, key: str, where: str) -> NDArray[Any]:
    """Return an array of a fit file, or raise if it is not there."""
    try:
        return fit[key]
    except KeyError:
        raise BuildError(f"{where}: the fit has no '{key}'") from None


def whole_numbers(
    values: NDArray[Any], count: int, low: int, high: int, what: str, where: str
) -> list[int]:
    """Return ``count`` whole numbers in ``low..high`` from a fit array.

    Raises:
        BuildError: if the array has another size, holds a value that is not a
            finite whole number, or holds a value outside the range.
    """
    try:
        array = np.asarray(values, dtype=np.float64).ravel()
    except (TypeError, ValueError):
        raise BuildError(f"{where}: {what} must be numbers") from None
    if (
        array.size != count
        or not np.all(np.isfinite(array))
        or not np.array_equal(array, np.round(array))
    ):
        raise BuildError(f"{where}: {what} must be {count} whole numbers")
    numbers = [int(value) for value in array]
    if any(not low <= number <= high for number in numbers):
        raise BuildError(f"{where}: {what} must be in {low}..{high}")
    return numbers


def chroma_record(fit: Fit, where: str) -> bytes:
    """Return the 97-byte chroma-curve record of a fit.

    The record is x[16], y[16], slope[17] for Cb, then x[16], y[16], slope[16]
    for Cr. The first stored curve is Cb (measured: NOTES section 44).
    """
    parts: list[int] = []
    for name, slopes in _CHROMA_SLOPES.items():
        knots = _array(fit, name, where)
        if knots.ndim != 2 or knots.shape[0] < 2:
            raise BuildError(f"{where}: '{name}' must hold an x row and a y row")
        slope_key = f"{name}_slope17"
        stored = whole_numbers(
            _array(fit, slope_key, where),
            _CHROMA_SLOPE_ARRAY,
            0,
            255,
            f"'{slope_key}'",
            where,
        )
        parts += whole_numbers(knots[0], _CHROMA_KNOTS, 0, 255, f"'{name}' x", where)
        parts += whole_numbers(knots[1], _CHROMA_KNOTS, 0, 255, f"'{name}' y", where)
        parts += stored[:slopes]
    return bytes(parts)


def film_ops(program: Program, film: Film, fit: Fit) -> list[BytesOp]:
    """Return the operations that write one film into its slot.

    Raises:
        BuildError: if the fit lacks an array or holds values that do not fit.
    """
    where = film.fit
    slot = slots.slot_for(film.entry)
    try:
        curves = np.asarray(_array(fit, "G", where), dtype=np.float64)
    except (TypeError, ValueError):
        raise BuildError(f"{where}: 'G' must be numbers") from None
    if curves.shape != (3, slots.CURVE_POINTS) or not np.all(np.isfinite(curves)):
        raise BuildError(
            f"{where}: 'G' must be 3 curves of {slots.CURVE_POINTS} finite numbers"
        )
    defaults = program.record(slots.DEFAULT_RECORD)
    grid = np.arange(slots.CURVE_POINTS, dtype=np.float64)

    targets: list[tuple[int, int, int]]  # (table, default table, channel)
    if isinstance(slot.tone, slots.Tables):
        targets = [
            (table, defaults[slots.STILLS_TABLE], channel)
            for channel, table in enumerate(slot.tone.addresses)
        ]
    else:
        targets = [
            (table, default, channel)
            for channel, record in enumerate(slot.tone.addresses)
            for table, default in zip(program.record(record), defaults)
        ]
    ops = [
        program.op(
            table,
            pack_table(np.interp(program.table(default), grid, curves[channel])),
        )
        for table, default, channel in targets
    ]

    u16, i16 = (0, 0xFFFF), (-0x8000, 0x7FFF)
    gain = whole_numbers(_array(fit, "gain", where), 1, *u16, "'gain'", where)[0]
    saturation = whole_numbers(_array(fit, "S", where), 6, *i16, "'S'", where)
    hue = whole_numbers(_array(fit, "H", where), 6, *i16, "'H'", where)
    matrix = whole_numbers(_array(fit, "A", where), 9, *i16, "'A'", where)
    identity = struct.pack("<9h", *slots.IDENTITY_MATRIX)
    ops += [
        program.op(slot.saturation, struct.pack("<2H", gain, gain)),
        program.op(slot.six_axis[0], struct.pack("<6h", *saturation)),
        program.op(slot.six_axis[1], struct.pack("<6h", *hue)),
        program.op(
            slot.matrix,
            struct.pack("<9h", *matrix),
            identity if slot.matrix_is_new else None,
        ),
        program.op(slot.chroma, chroma_record(fit, where)),
    ]
    return ops


def label_ops(text_block: bytes, films: Sequence[Film]) -> list[BytesOp]:
    """Return the operations that rename the menu entries.

    Only whole strings are changed: a copy of the stock name counts if it
    starts on an even offset, follows a string end or a tag's '@', and is
    followed by a string end. Longer texts that contain the name stay.

    Raises:
        BuildError: if a menu entry's name is not found as a whole string.
    """
    ops = []
    for film in films:
        old = film.entry.encode(UTF16)
        padded = film.label + "\0" * (len(film.entry) - len(film.label))
        new = padded.encode(UTF16)
        found = [
            BytesOp(TEXT_BLOCK, match.start(), old, new)
            for match in re.finditer(re.escape(old), text_block)
            if match.start() % 2 == 0
            and match.start() >= 2
            and text_block[match.end() : match.end() + 2] == _STRING_END
            and text_block[match.start() - 2 : match.start()] in _STRING_STARTS
        ]
        if not found:
            raise BuildError(
                f"the menu text '{film.entry}' was not found in the firmware"
            )
        ops += found
    return ops


def structure_ops(program: Program) -> list[BytesOp]:
    """Return the operations for what the film slots share."""
    identity_look = program.read(slots.IDENTITY_LOOK, slots.TABLE_BYTES)
    ops = [program.op(address, identity_look) for address in slots.LOOK_TABLES]
    handler = struct.pack("<I", slots.THREE_RECORD_HANDLER)
    ops += [
        program.op(slots.GAMMA_HASH + 8 * entry + 4, handler)
        for entry in slots.LIGHT_TONE_ENTRIES
    ]
    return ops


def _changing(ops: Sequence[BytesOp]) -> tuple[Op, ...]:
    """Drop the operations that would write the bytes that are already there."""
    return tuple(op for op in ops if op.expect != op.new)


def load_fit(path: Path) -> dict[str, NDArray[Any]]:
    """Return the arrays of a fit file.

    Raises:
        BuildError: if the file is missing or is not a numpy ``.npz`` archive
            of plain arrays.
    """
    try:
        with path.open("rb") as handle:
            loaded = np.load(handle)
            if not isinstance(loaded, np.lib.npyio.NpzFile):
                raise BuildError(f"{path}: is not a numpy .npz archive")
            with loaded as archive:
                return {key: archive[key] for key in archive.files}
    except (
        OSError,
        ValueError,
        EOFError,
        NotImplementedError,
        zipfile.BadZipFile,
        zlib.error,
    ) as error:
        raise BuildError(f"{path}: cannot be read as a fit file: {error}") from None


def generate(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> list[GeneratedSpec]:
    """Generate the three film-look patch specs.

    Args:
        paths: the repository; the stock firmware must be in it.
        stock: the stock firmware.

    Returns:
        The looks spec, the labels spec and the structure spec.

    Raises:
        BuildError: if the film list or a fit file is wrong.
        StockError: if the stock firmware is missing or is another file.
    """
    film_list = load_films(paths)
    digest = inputs_digest(paths, film_list)
    container = parse(read_stock(paths, stock))
    program = Program(container.blocks[PROGRAM_BLOCK].payload)

    looks: list[BytesOp] = []
    for film in film_list.films:
        looks += film_ops(program, film, load_fit(paths.resolve(film.fit)))

    films_text = "; ".join(f"{film.entry} = {film.film}" for film in film_list.films)
    labels_text = ", ".join(
        f"'{film.entry}' -> '{film.label}'" for film in film_list.films
    )
    return [
        GeneratedSpec(
            path=film_list.films_spec,
            description=(
                "Seven film looks, one per film slot, in menu order: " f"{films_text}."
            ),
            ops=_changing(looks),
            inputs_sha256=digest,
            attribution=ATTRIBUTION,
        ),
        GeneratedSpec(
            path=film_list.labels_spec,
            description=(
                f"Menu labels of the seven film slots: {labels_text}. Only whole "
                "strings; longer texts that contain a name are left alone."
            ),
            ops=tuple(label_ops(container.blocks[TEXT_BLOCK].payload, film_list.films)),
            inputs_sha256=digest,
        ),
        GeneratedSpec(
            path=film_list.structure_spec,
            description=(
                "What the film slots share: the stock identity look table for "
                "Cross Process I, Light Tone and Pop Art I, and the three-record "
                "tone-curve handler for the Light Tone codes."
            ),
            ops=_changing(structure_ops(program)),
            inputs_sha256=digest,
        ),
    ]


def _on_disk(paths: RepoPaths, spec: GeneratedSpec) -> dict[str, Any] | None:
    """Return the JSON of the spec file in the repository, or None if it is absent."""
    path = paths.resolve(spec.path)
    if not path.exists():
        return None
    raw = read_json(path, BuildError)
    if not isinstance(raw, dict):
        raise BuildError(f"{path}: a spec must be a JSON object")
    return raw


def _is_current(on_disk: dict[str, Any] | None, fields: dict[str, Any]) -> bool:
    """Return True if a spec file holds exactly the generated fields."""
    if on_disk is None:
        return False
    return {key: on_disk.get(key) for key in _GENERATED_KEYS} == {
        key: fields.get(key) for key in _GENERATED_KEYS
    }


def stale(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> list[str]:
    """Return the paths of the spec files whose generated fields are out of date."""
    return [
        spec.path
        for spec in generate(paths, stock)
        if not _is_current(_on_disk(paths, spec), spec.generated_fields(stock))
    ]


def write(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> list[str]:
    """Bring the spec files up to date and return the paths that changed.

    The generated fields are replaced. Notes that people added are kept. If the
    operations changed, ``status`` becomes "built, NOT camera-tested" and
    ``expected_sha256`` is removed: they described other bytes.
    """
    changed = []
    for spec in generate(paths, stock):
        fields = spec.generated_fields(stock)
        on_disk = _on_disk(paths, spec)
        if _is_current(on_disk, fields):
            continue
        extra = {
            key: value
            for key, value in (on_disk or {}).items()
            if key not in _GENERATED_KEYS
        }
        if on_disk is None or on_disk.get("ops") != fields["ops"]:
            extra["status"] = NEW_STATUS
            extra.pop("expected_sha256", None)
        write_json(paths.resolve(spec.path), {**fields, **extra}, BuildError)
        changed.append(spec.path)
    return changed

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
"""

from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Sequence, Tuple

from ..container import parse
from ..errors import BuildError
from ..hashing import sha256_bytes
from ..paths import RepoPaths
from ..spec import BytesOp, Op, op_to_json, spec_from_json
from ..stock import EPM2_V16, StockFirmware, stock_path
from . import slots as S
from .films import Film, FilmList, load_films

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

    FloatArray = NDArray[np.float64]

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
_UTF16 = "utf-16-le"
#: A menu text is a whole string if it follows a string end or a '@' of a tag.
_STRING_STARTS = (b"\0\0", "@".encode(_UTF16))
_STRING_END = b"\0\0"
_CHROMA_KNOTS = 16
_CHROMA_SLOPES = (17, 16)


@dataclass(frozen=True)
class GeneratedSpec:
    """A patch spec made by the generator.

    Attributes:
        path: where the spec belongs, relative to the repository root.
        name: the spec's name (the file name without ``.json``).
        description: text for the spec's ``description`` field.
        ops: the operations.
        attribution: text for an ``attribution`` field, or None.
    """

    path: str
    name: str
    description: str
    ops: Tuple[Op, ...]
    attribution: "str | None" = None

    def to_json(self, stock: StockFirmware, status: str) -> Dict[str, Any]:
        """Return the JSON form of the spec, with the given status text."""
        raw: Dict[str, Any] = {"name": self.name}
        if self.attribution:
            raw["attribution"] = self.attribution
        raw.update(
            description=self.description,
            ops=[op_to_json(op) for op in self.ops],
            base=stock.relative_path,
            base_sha256=stock.sha256,
            status=status,
        )
        return raw


class _Program:
    """Read access to block 0 of the stock firmware by run-time address."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, address: int, length: int) -> bytes:
        """Return ``length`` bytes at a run-time address."""
        offset = address - S.BLOCK0_BASE
        if offset < 0 or offset + length > len(self._payload):
            raise BuildError(f"address {address:#x} is outside block 0")
        return self._payload[offset : offset + length]

    def record(self, address: int) -> Tuple[int, ...]:
        """Return the eight table addresses of a tone record."""
        raw = self.read(address, 4 * S.RECORD_TABLES)
        return tuple(struct.unpack(f"<{S.RECORD_TABLES}I", raw))

    def table(self, address: int) -> "FloatArray":
        """Return the 256 values of a tone table."""
        import numpy as np

        raw = self.read(address, S.TABLE_BYTES)
        return np.array(struct.unpack(f"<{S.TABLE_ENTRIES}H", raw), dtype=np.float64)

    def op(self, address: int, new: bytes, expect: "bytes | None" = None) -> BytesOp:
        """Return an operation that writes ``new`` at a run-time address.

        ``expect`` defaults to the stock bytes at that address.
        """
        old = self.read(address, len(new)) if expect is None else expect
        return BytesOp(PROGRAM_BLOCK, address - S.BLOCK0_BASE, old, new)


def _pack_table(curve: "FloatArray") -> bytes:
    """Pack a tone table: values rounded, kept rising and limited to 10 bits."""
    import numpy as np

    values = np.clip(
        np.round(np.maximum.accumulate(curve)), 0, S.CURVE_POINTS - 1
    ).astype(int)
    return struct.pack(f"<{S.TABLE_ENTRIES}H", *values.tolist())


def _integers(values: Any, count: int, what: str, where: str) -> List[int]:
    """Return ``count`` whole numbers from a fit array, or raise."""
    import numpy as np

    array = np.asarray(values, dtype=np.float64).ravel()
    if array.size != count or not np.array_equal(array, np.round(array)):
        raise BuildError(f"{where}: {what} must be {count} whole numbers")
    return [int(value) for value in array]


def _chroma_record(fit: Any, where: str) -> bytes:
    """Return the 97-byte chroma-curve record of a fit.

    The record is x[16], y[16], slope[17] for Cb, then x[16], y[16], slope[16]
    for Cr. The first stored curve is Cb (measured: NOTES section 44).
    """
    parts: List[int] = []
    for name, slopes in zip(("Cb", "Cr"), _CHROMA_SLOPES):
        knots = fit[name]
        parts += _integers(knots[0], _CHROMA_KNOTS, f"{name} x", where)
        parts += _integers(knots[1], _CHROMA_KNOTS, f"{name} y", where)
        slope17 = _integers(fit[f"{name}_slope17"], 17, f"{name} slopes", where)
        parts += slope17[:slopes]
    if any(not 0 <= value <= 255 for value in parts):
        raise BuildError(f"{where}: a chroma-curve value is outside 0..255")
    return bytes(parts)


def _film_ops(program: _Program, film: Film, fit: Any) -> List[BytesOp]:
    """Return the operations that write one film into its slot."""
    import numpy as np

    where = film.fit
    slot = S.slot_for(film.entry)
    curves = np.asarray(fit["G"], dtype=np.float64)
    if curves.shape != (3, S.CURVE_POINTS):
        raise BuildError(f"{where}: 'G' must be 3 curves of {S.CURVE_POINTS} points")
    defaults = program.record(S.DEFAULT_RECORD)
    grid = np.arange(S.CURVE_POINTS, dtype=np.float64)

    targets: List[Tuple[int, int, int]] = []  # (table, default table, channel)
    if slot.tables is not None:
        targets = [
            (table, defaults[S.STILLS_TABLE], channel)
            for channel, table in enumerate(slot.tables)
        ]
    elif slot.records is not None:
        for channel, record in enumerate(slot.records):
            targets += [
                (table, default, channel)
                for table, default in zip(program.record(record), defaults)
            ]
    ops = [
        program.op(
            table,
            _pack_table(np.interp(program.table(default), grid, curves[channel])),
        )
        for table, default, channel in targets
    ]

    gain = _integers(fit["gain"], 1, "gain", where)[0]
    saturation = _integers(fit["S"], 6, "S", where)
    hue = _integers(fit["H"], 6, "H", where)
    matrix = _integers(fit["A"], 9, "A", where)
    try:
        ops.append(program.op(slot.saturation, struct.pack("<2H", gain, gain)))
        ops.append(program.op(slot.six_axis[0], struct.pack("<6h", *saturation)))
        ops.append(program.op(slot.six_axis[1], struct.pack("<6h", *hue)))
        identity = struct.pack("<9h", *S.IDENTITY_MATRIX)
        ops.append(
            program.op(
                slot.matrix,
                struct.pack("<9h", *matrix),
                identity if slot.matrix_is_new else None,
            )
        )
    except struct.error as error:
        raise BuildError(f"{where}: a value does not fit its field: {error}") from None
    ops.append(program.op(slot.chroma, _chroma_record(fit, where)))
    return ops


def _label_ops(text_block: bytes, films: Sequence[Film]) -> List[BytesOp]:
    """Return the operations that rename the menu entries.

    Only whole strings are changed: a copy of the stock name counts if it
    starts on an even offset, follows a string end or a tag's '@', and is
    followed by a string end. Longer texts that contain the name stay.
    """
    ops = []
    for film in films:
        old = film.entry.encode(_UTF16)
        padded = film.label + "\0" * (len(film.entry) - len(film.label))
        new = padded.encode(_UTF16)
        for match in re.finditer(re.escape(old), text_block):
            start, end = match.start(), match.end()
            if (
                start % 2 == 0
                and start >= 2
                and text_block[end : end + 2] == _STRING_END
                and text_block[start - 2 : start] in _STRING_STARTS
            ):
                ops.append(BytesOp(TEXT_BLOCK, start, old, new))
    return ops


def _structure_ops(program: _Program) -> List[BytesOp]:
    """Return the operations for what the film slots share."""
    identity_look = program.read(S.IDENTITY_LOOK, S.TABLE_BYTES)
    ops = [program.op(address, identity_look) for address in S.LOOK_TABLES]
    handler = struct.pack("<I", S.THREE_RECORD_HANDLER)
    ops += [
        program.op(S.GAMMA_HASH + 8 * entry + 4, handler)
        for entry in S.LIGHT_TONE_ENTRIES
    ]
    return ops


def _changing(ops: Sequence[BytesOp]) -> Tuple[Op, ...]:
    """Drop the operations that would write the bytes that are already there."""
    return tuple(op for op in ops if op.expect != op.new)


def _name(path: str) -> str:
    """Return the spec name of a spec path."""
    return Path(path).stem


def generate(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> List[GeneratedSpec]:
    """Generate the three film-look patch specs.

    Args:
        paths: the repository; the stock firmware must be in it.
        stock: the stock firmware.

    Returns:
        The looks spec, the labels spec and the structure spec.

    Raises:
        BuildError: if the film list or a fit file is wrong, or numpy is missing.
        StockError: if the stock firmware is not there.
    """
    try:
        import numpy as np
    except ImportError:
        raise BuildError(
            "numpy is needed to generate the film specs: "
            "uv run --extra looks epm2mod looks"
        ) from None
    from ..errors import StockError

    film_list: FilmList = load_films(paths)
    source = stock_path(paths, stock)
    if not source.is_file():
        raise StockError(f"{stock.relative_path} is missing: run 'epm2mod fetch-stock'")
    data = source.read_bytes()
    if sha256_bytes(data) != stock.sha256:
        raise StockError(f"{stock.relative_path} is not {stock.file_name}")
    container = parse(data)
    program = _Program(container.blocks[PROGRAM_BLOCK].payload)

    film_ops: List[BytesOp] = []
    for film in film_list.films:
        try:
            with np.load(paths.resolve(film.fit)) as fit:
                film_ops += _film_ops(program, film, fit)
        except (OSError, KeyError, ValueError) as error:
            raise BuildError(f"{film.fit}: cannot be used: {error}") from None

    films_text = "; ".join(f"{film.entry} = {film.film}" for film in film_list.films)
    labels_text = ", ".join(
        f"'{film.entry}' -> '{film.label}'" for film in film_list.films
    )
    return [
        GeneratedSpec(
            path=film_list.films_spec,
            name=_name(film_list.films_spec),
            description=f"Seven film looks, one per film slot, in menu order: {films_text}.",
            ops=_changing(film_ops),
            attribution=ATTRIBUTION,
        ),
        GeneratedSpec(
            path=film_list.labels_spec,
            name=_name(film_list.labels_spec),
            description=(
                f"Menu labels of the seven film slots: {labels_text}. Only whole "
                "strings; longer texts that contain a name are left alone."
            ),
            ops=tuple(
                _label_ops(container.blocks[TEXT_BLOCK].payload, film_list.films)
            ),
        ),
        GeneratedSpec(
            path=film_list.structure_spec,
            name=_name(film_list.structure_spec),
            description=(
                "What the film slots share: the stock identity look table for "
                "Cross Process I, Light Tone and Pop Art I, and the three-record "
                "tone-curve handler for the Light Tone codes."
            ),
            ops=_changing(_structure_ops(program)),
        ),
    ]


def committed_ops(
    paths: RepoPaths, generated: GeneratedSpec
) -> "Tuple[Op, ...] | None":
    """Return the operations of the committed copy of a spec, or None if absent."""
    path = paths.resolve(generated.path)
    if not path.is_file():
        return None
    return spec_from_json(json.loads(path.read_text(encoding="utf-8")), path).ops


def stale(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> List[str]:
    """Return the paths of the committed specs that differ from the generated ones."""
    return [
        spec.path
        for spec in generate(paths, stock)
        if committed_ops(paths, spec) != spec.ops
    ]


def write(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> List[str]:
    """Write the generated specs to ``patches/`` and return the paths that changed.

    A spec whose operations did not change is left as it is, so its ``status``
    stays. A spec whose operations changed gets the status "built, NOT
    camera-tested": the old test record does not apply to the new bytes.
    """
    changed = []
    for spec in generate(paths, stock):
        if committed_ops(paths, spec) == spec.ops:
            continue
        path = paths.resolve(spec.path)
        text = json.dumps(spec.to_json(stock, NEW_STATUS), indent=1) + "\n"
        path.write_text(text, encoding="utf-8")
        changed.append(spec.path)
    return changed

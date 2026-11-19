"""The look file: film looks that the camera loads from the SD card.

A look file holds up to twelve looks, one per art-filter menu entry. The camera
reads it from the card root (``CARD_NAME``), checks it, writes the looks into
the slots' tables and keeps a copy in its settings memory, so the looks stay
after a restart and without the card. The specification is the look file
format document. This module writes and reads the format; it does
not need numpy.

Two kinds of look:

* ``ColourLook``: the numbers of a colour film slot. Its tone curves are kept
  as 1,024-point curves; the camera makes each tone table from a curve and the
  stock default table, as the film generator does.
* ``MonoLook``: the black-and-white slot (Grainy Film in the twelve-film
  build): the art matrix and the two tone tables of the slot.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Sequence
from dataclasses import dataclass

from ..errors import LookFileError

#: The file name on the card, in the card's top folder.
CARD_NAME = "EPM2LOOK.BIN"
MAGIC = b"EPLK"
VERSION = 1
HEADER_BYTES = 32
RECORD_BYTES = 1708
#: The camera model code and the firmware version that version 1 is for.
MODEL = 0x0101
FIRMWARE = 0x0160
#: The art-filter menu entries, in menu order: a look's slot is its index here.
MENU_ENTRIES = (
    "Pop Art",
    "Soft Focus",
    "Pale&Light Color",
    "Light Tone",
    "Grainy Film",
    "Pin Hole",
    "Diorama",
    "Cross Process",
    "Gentle Sepia",
    "Dramatic Tone",
    "Key Line",
    "Watercolor",
)
MAX_LOOKS = len(MENU_ENTRIES)
MAX_FILE_BYTES = HEADER_BYTES + MAX_LOOKS * RECORD_BYTES
KIND_COLOUR = 1
KIND_MONO = 2
NAME_BYTES = 16
CURVE_POINTS = 1024
CURVE_MAX = CURVE_POINTS - 1
#: A curve is a 16-bit first value and 1,023 steps of 4 bits, low nibble first.
CURVE_BYTES = 2 + CURVE_POINTS // 2
STEP_MAX = 15
TABLE_ENTRIES = 256
CHROMA_BYTES = 97
CHROMA_KNOTS = 16
#: Slope bytes of each chroma curve: Cb, then Cr.
CHROMA_SLOPES = {"Cb": 17, "Cr": 16}
#: A matrix row may sum to 256 plus or minus this.
ROW_SUM_SLACK = 8

#: Record layout (offsets in a record).
_SLOT, _KIND, _NAME = 0, 1, 4
_GAIN, _SATURATION, _HUE, _MATRIX, _CHROMA = 20, 22, 34, 46, 64
_CURVES = 164
_MONO_TABLES = 164
_CRC_START = 16


@dataclass(frozen=True)
class ColourLook:
    """A colour look: the numbers of one colour film slot.

    Attributes:
        slot: the menu entry, an index into ``MENU_ENTRIES``.
        name: up to 16 ASCII characters (kept in the file; the menu shows the
            name of the entry).
        gain: the saturation gain (both values of the slot's pair).
        saturation: the six-axis saturation values.
        hue: the six-axis hue values.
        matrix: the art matrix, 3 x 3 by rows; each row sums to 256.
        chroma: the 97-byte chroma-curve record.
        curves: the tone curves of red, green and blue: 1,024 rising values
            in 0..1023 each.
    """

    slot: int
    name: str
    gain: int
    saturation: tuple[int, ...]
    hue: tuple[int, ...]
    matrix: tuple[int, ...]
    chroma: bytes
    curves: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        """Check the look. Every instance can be written.

        Raises:
            LookFileError: if a value does not fit the format.
        """
        _check_common(self.slot, self.name, self.matrix)
        _check_range(self.gain, 0, 0xFFFF, "the gain")
        _check_values(self.saturation, 6, -0x8000, 0x7FFF, "six-axis saturation")
        _check_values(self.hue, 6, -0x8000, 0x7FFF, "six-axis hue")
        _check_chroma(self.chroma)
        if len(self.curves) != 3:
            raise LookFileError("a colour look has three tone curves")
        for curve in self.curves:
            _check_curve(curve)


@dataclass(frozen=True)
class MonoLook:
    """A black-and-white look: the numbers of the black-and-white slot.

    Attributes:
        slot: the menu entry, an index into ``MENU_ENTRIES``.
        name: up to 16 ASCII characters.
        matrix: the art matrix, 3 x 3 by rows: how colours turn into grey.
        grain: the grain program's contrast table (the tone of still
            pictures): 256 values in 0..1023 that do not fall.
        live: the look table of live view and movies, the same kind of table.
    """

    slot: int
    name: str
    matrix: tuple[int, ...]
    grain: tuple[int, ...]
    live: tuple[int, ...]

    def __post_init__(self) -> None:
        """Check the look. Every instance can be written.

        Raises:
            LookFileError: if a value does not fit the format.
        """
        _check_common(self.slot, self.name, self.matrix)
        for what, table in (
            ("the grain table", self.grain),
            ("the live table", self.live),
        ):
            _check_values(table, TABLE_ENTRIES, 0, CURVE_MAX, what)
            if any(b < a for a, b in zip(table, table[1:])):
                raise LookFileError(f"{what} must not fall")


Look = ColourLook | MonoLook


def _check_range(value: int, low: int, high: int, what: str) -> None:
    """Raise if a whole number is outside ``low..high``."""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not low <= value <= high
    ):
        raise LookFileError(f"{what} must be a whole number in {low}..{high}")


def _check_values(
    values: Sequence[int], count: int, low: int, high: int, what: str
) -> None:
    """Raise if ``values`` is not ``count`` whole numbers in ``low..high``."""
    if len(values) != count:
        raise LookFileError(f"{what} must be {count} numbers, not {len(values)}")
    for value in values:
        _check_range(value, low, high, what)


def _check_common(slot: int, name: str, matrix: Sequence[int]) -> None:
    """Check the fields that both kinds of look have."""
    _check_range(slot, 0, MAX_LOOKS - 1, "the slot")
    if (
        not name.isascii()
        or not name.isprintable()
        or len(name.encode("ascii")) > NAME_BYTES
    ):
        raise LookFileError(
            f"the name '{name}' must be at most {NAME_BYTES} printable ASCII characters"
        )
    _check_values(matrix, 9, -0x8000, 0x7FFF, "the matrix")
    for row in range(3):
        total = sum(matrix[3 * row : 3 * row + 3])
        if abs(total - 256) > ROW_SUM_SLACK:
            raise LookFileError(
                f"row {row + 1} of the matrix sums to {total}, not 256 +/- {ROW_SUM_SLACK}"
            )


def _check_chroma(chroma: bytes) -> None:
    """Check a chroma record: its size, and x values that do not fall."""
    if len(chroma) != CHROMA_BYTES:
        raise LookFileError(f"the chroma record must be {CHROMA_BYTES} bytes")
    at = 0
    for name, slopes in CHROMA_SLOPES.items():
        x = chroma[at : at + CHROMA_KNOTS]
        if any(b < a for a, b in zip(x, x[1:])):
            raise LookFileError(f"the {name} chroma x values must not fall")
        at += 2 * CHROMA_KNOTS + slopes


def _check_curve(curve: Sequence[int]) -> None:
    """Check a tone curve: 1,024 values in 0..1023, steps of 0 to 15."""
    _check_values(curve, CURVE_POINTS, 0, CURVE_MAX, "a tone curve")
    for a, b in zip(curve, curve[1:]):
        if not 0 <= b - a <= STEP_MAX:
            raise LookFileError(
                f"a tone curve must rise by 0 to {STEP_MAX} per point, not {b - a}"
            )


def encode_curve(curve: Sequence[int]) -> bytes:
    """Return the 514 bytes of a tone curve: the first value, then the steps."""
    _check_curve(curve)
    steps = [b - a for a, b in zip(curve, curve[1:])] + [0]
    packed = bytes(low | high << 4 for low, high in zip(steps[0::2], steps[1::2]))
    return struct.pack("<H", curve[0]) + packed


def decode_curve(data: bytes) -> tuple[int, ...]:
    """Return the 1,024 values of an encoded tone curve.

    Raises:
        LookFileError: if the curve leaves 0..1023 or its last nibble is not 0.
    """
    if len(data) != CURVE_BYTES:
        raise LookFileError(f"a tone curve is {CURVE_BYTES} bytes")
    (value,) = struct.unpack_from("<H", data)
    values = [value]
    for byte in data[2:]:
        values += [values[-1] + (byte & 0xF), values[-1] + (byte & 0xF) + (byte >> 4)]
    if data[-1] >> 4:
        raise LookFileError("the last step of a tone curve must be 0")
    curve = tuple(values[:CURVE_POINTS])
    if curve[-1] > CURVE_MAX:
        raise LookFileError(f"a tone curve goes above {CURVE_MAX}")
    return curve


def encode_record(look: Look) -> bytes:
    """Return the 1,708 bytes of a look record."""
    record = bytearray(RECORD_BYTES)
    kind = KIND_COLOUR if isinstance(look, ColourLook) else KIND_MONO
    struct.pack_into("<BB", record, _SLOT, look.slot, kind)
    record[_NAME : _NAME + NAME_BYTES] = look.name.encode("ascii").ljust(
        NAME_BYTES, b"\0"
    )
    struct.pack_into("<9h", record, _MATRIX, *look.matrix)
    if isinstance(look, ColourLook):
        struct.pack_into("<H", record, _GAIN, look.gain)
        struct.pack_into("<6h", record, _SATURATION, *look.saturation)
        struct.pack_into("<6h", record, _HUE, *look.hue)
        record[_CHROMA : _CHROMA + CHROMA_BYTES] = look.chroma
        for channel, curve in enumerate(look.curves):
            at = _CURVES + channel * CURVE_BYTES
            record[at : at + CURVE_BYTES] = encode_curve(curve)
    else:
        struct.pack_into(f"<{TABLE_ENTRIES}H", record, _MONO_TABLES, *look.grain)
        struct.pack_into(
            f"<{TABLE_ENTRIES}H", record, _MONO_TABLES + 2 * TABLE_ENTRIES, *look.live
        )
    return bytes(record)


def decode_record(record: bytes) -> Look:
    """Return the look of a 1,708-byte record.

    Raises:
        LookFileError: if the record is not a valid look.
    """
    if len(record) != RECORD_BYTES:
        raise LookFileError(f"a look record is {RECORD_BYTES} bytes")
    slot, kind = struct.unpack_from("<BB", record, _SLOT)
    raw_name = record[_NAME : _NAME + NAME_BYTES].rstrip(b"\0")
    try:
        name = raw_name.decode("ascii")
    except UnicodeDecodeError:
        raise LookFileError("a look's name must be ASCII") from None
    matrix = struct.unpack_from("<9h", record, _MATRIX)
    if kind == KIND_COLOUR:
        return ColourLook(
            slot=slot,
            name=name,
            gain=struct.unpack_from("<H", record, _GAIN)[0],
            saturation=struct.unpack_from("<6h", record, _SATURATION),
            hue=struct.unpack_from("<6h", record, _HUE),
            matrix=matrix,
            chroma=bytes(record[_CHROMA : _CHROMA + CHROMA_BYTES]),
            curves=tuple(
                decode_curve(record[at : at + CURVE_BYTES])
                for at in range(_CURVES, _CURVES + 3 * CURVE_BYTES, CURVE_BYTES)
            ),
        )
    if kind == KIND_MONO:
        return MonoLook(
            slot=slot,
            name=name,
            matrix=matrix,
            grain=struct.unpack_from(f"<{TABLE_ENTRIES}H", record, _MONO_TABLES),
            live=struct.unpack_from(
                f"<{TABLE_ENTRIES}H", record, _MONO_TABLES + 2 * TABLE_ENTRIES
            ),
        )
    raise LookFileError(f"a look of kind {kind} is not known (1 colour, 2 mono)")


def pack(looks: Sequence[Look]) -> bytes:
    """Return a look file with the given looks, in the given order.

    Raises:
        LookFileError: if there are more than twelve looks or two for one slot.
    """
    if len(looks) > MAX_LOOKS:
        raise LookFileError(f"a look file holds at most {MAX_LOOKS} looks")
    slots = [look.slot for look in looks]
    if len(set(slots)) != len(slots):
        raise LookFileError("two looks are for the same menu entry")
    body = b"".join(encode_record(look) for look in looks)
    length = HEADER_BYTES + len(body)
    tail = struct.pack("<HH12x", MODEL, FIRMWARE) + body
    head = struct.pack("<4sBBHI", MAGIC, VERSION, len(looks), RECORD_BYTES, length)
    return head + struct.pack("<I", zlib.crc32(tail)) + tail


def unpack(data: bytes) -> list[Look]:
    """Return the looks of a look file, after every check the camera makes.

    Raises:
        LookFileError: if the file is not a valid look file of version 1 for
            the E-PM2 with firmware 1.6.
    """
    if len(data) < HEADER_BYTES:
        raise LookFileError("the file is shorter than the 32-byte header")
    magic, version, count, size, length, crc, model, firmware = struct.unpack_from(
        "<4sBBHIIHH", data
    )
    if magic != MAGIC:
        raise LookFileError("not a look file (the first bytes are not EPLK)")
    if version != VERSION or size != RECORD_BYTES:
        raise LookFileError(
            f"format version {version} with records of {size} bytes; this tool "
            f"reads version {VERSION}"
        )
    if count > MAX_LOOKS or length != HEADER_BYTES + count * RECORD_BYTES:
        raise LookFileError(f"{count} looks do not fit a file length of {length}")
    if len(data) != length:
        raise LookFileError(f"the file is {len(data)} bytes, its header says {length}")
    if zlib.crc32(data[_CRC_START:]) != crc:
        raise LookFileError("the CRC-32 does not match: the file is damaged")
    if (model, firmware) != (MODEL, FIRMWARE):
        raise LookFileError(
            f"the file is for camera {model:#06x} firmware {firmware:#06x}, not the "
            f"E-PM2 ({MODEL:#06x}) with firmware 1.6 ({FIRMWARE:#06x})"
        )
    looks = [
        decode_record(data[at : at + RECORD_BYTES])
        for at in range(HEADER_BYTES, length, RECORD_BYTES)
    ]
    slots = [look.slot for look in looks]
    if len(set(slots)) != len(slots):
        raise LookFileError("two looks are for the same menu entry")
    return looks

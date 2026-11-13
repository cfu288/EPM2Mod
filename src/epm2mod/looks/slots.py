"""Where each film slot keeps its numbers in the firmware.

A film slot is an art-filter menu entry whose processing was made colour-only.
Its look is seven things in block 0 of the firmware. All addresses here are run-time
addresses of E-PM2 firmware 1.6; ``BLOCK0_BASE`` turns them into payload offsets.
How they were found: ``docs/art-filter-slots.md`` and
``experiments/2026-11-09-film-portra/NOTES.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Run-time address of the first payload byte of block 0.
BLOCK0_BASE = 0x7E421020

#: A tone-curve table: 256 unsigned 16-bit values.
TABLE_ENTRIES = 256
TABLE_BYTES = 2 * TABLE_ENTRIES
#: Tone-curve values are 10-bit.
CURVE_POINTS = 1024

#: The record of the eight stock default tone tables. A slot's table is the
#: film curve applied after one of them.
DEFAULT_RECORD = 0x7E78B39C
RECORD_TABLES = 8
#: Index, in a record, of the table that still pictures use.
STILLS_TABLE = 1

#: The stock "identity" look table, copied over the look tables of three slots.
IDENTITY_LOOK = 0x7E75B8F0
#: The look tables of Cross Process I, Light Tone and Pop Art I.
LOOK_TABLES = (0x7E75F2F0, 0x7E75EAF0, 0x7E75E6F0)

#: Hash table that selects the tone-curve handler by art code; entries are 8 bytes.
GAMMA_HASH = 0x7E78C154
#: The handler that uses three records (one per channel).
THREE_RECORD_HANDLER = 0x7E56B82A
#: Entries of the Light Tone codes (72 and 81) in ``GAMMA_HASH``.
LIGHT_TONE_ENTRIES = (2, 11)

#: A matrix that earlier specs put in the slots they create: the identity, as 9 x int16.
IDENTITY_MATRIX = (256, 0, 0, 0, 256, 0, 0, 0, 256)


@dataclass(frozen=True)
class Slot:
    """The firmware addresses of one film slot.

    Exactly one of ``tables`` and ``records`` is used. ``tables`` gives three
    table addresses (red, green, blue), each written from the stills default
    table. ``records`` gives three record addresses; each record holds eight
    table addresses, and every table is written from the default table of the
    same index.

    Attributes:
        entry: the stock name of the menu entry.
        saturation: address of the pair of saturation gains.
        six_axis: addresses of the six saturation values and the six hue values.
        matrix: address of the 3 x 3 matrix.
        matrix_is_new: True if an earlier spec created the matrix table (then
            it holds the identity); False if the stock firmware has it.
        chroma: address of the 97-byte chroma-curve record.
        tables: three tone-table addresses, or None.
        records: three tone-record addresses, or None.
    """

    entry: str
    saturation: int
    six_axis: tuple[int, int]
    matrix: int
    matrix_is_new: bool
    chroma: int
    tables: tuple[int, int, int] | None = None
    records: tuple[int, int, int] | None = None

    def __post_init__(self) -> None:
        """Check that the slot has tables or records, and not both."""
        if (self.tables is None) == (self.records is None):
            raise ValueError(
                f"slot {self.entry!r}: exactly one of 'tables' and 'records' is needed"
            )


#: The seven film slots, in menu order.
SLOTS: tuple[Slot, ...] = (
    Slot(
        entry="Pop Art",
        tables=(0x7E74F1BC, 0x7E74F5BC, 0x7E7505BC),
        saturation=0x7E7696A0,
        six_axis=(0x7E769486, 0x7E769492),
        matrix=0x7E880FC2,
        matrix_is_new=True,
        chroma=0x7E74B8BA,
    ),
    Slot(
        entry="Soft Focus",
        tables=(0x7E75FAF0, 0x7E75F8F0, 0x7E7616F0),
        saturation=0x7E7696BC,
        six_axis=(0x7E76952E, 0x7E76953A),
        matrix=0x7ECB099A,
        matrix_is_new=True,
        chroma=0x7E74BBCA,
    ),
    Slot(
        entry="Pale&Light Color",
        tables=(0x7F033B7C, 0x7F033D7C, 0x7E75E8F0),
        saturation=0x7E7696A4,
        six_axis=(0x7E76949E, 0x7E7694AA),
        matrix=0x7ECB0988,
        matrix_is_new=True,
        chroma=0x7E74B91C,
    ),
    Slot(
        entry="Light Tone",
        records=(0x7E78B49C, 0x7E78B4BC, 0x7E78B4DC),
        saturation=0x7E7696A8,
        six_axis=(0x7E7694B6, 0x7E7694C2),
        matrix=0x7E768F58,
        matrix_is_new=False,
        chroma=0x7E74B97E,
    ),
    Slot(
        entry="Pin Hole",
        tables=(0x7E74EFBC, 0x7E751FBC, 0x7E7521BC),
        saturation=0x7E7696B8,
        six_axis=(0x7E769516, 0x7E769522),
        matrix=0x7ECB09AC,
        matrix_is_new=True,
        chroma=0x7E74BB68,
    ),
    Slot(
        entry="Diorama",
        tables=(0x7E754FBC, 0x7E7551BC, 0x7E757FBC),
        saturation=0x7E7696EC,
        six_axis=(0x7E769622, 0x7E76962E),
        matrix=0x7ECB09BE,
        matrix_is_new=True,
        chroma=0x7E74BE16,
    ),
    Slot(
        entry="Cross Process",
        records=(0x7E78B41C, 0x7E78B43C, 0x7E78B45C),
        saturation=0x7E7696B4,
        six_axis=(0x7E7694FE, 0x7E76950A),
        matrix=0x7E768F46,
        matrix_is_new=False,
        chroma=0x7E74BAA4,
    ),
)


def slot_for(entry: str) -> Slot:
    """Return the slot of a menu entry.

    Raises:
        KeyError: if the entry is not a film slot.
    """
    for slot in SLOTS:
        if slot.entry == entry:
            return slot
    raise KeyError(entry)

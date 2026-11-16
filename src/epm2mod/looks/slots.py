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
class Tables:
    """Three tone tables of a slot: red, green, blue.

    Each table is written from the default table that still pictures use.

    Attributes:
        addresses: the three table addresses.
    """

    addresses: tuple[int, int, int]


@dataclass(frozen=True)
class Records:
    """Three tone records of a slot: red, green, blue.

    Each record holds eight table addresses. Every table is written from the
    default table of the same index.

    Attributes:
        addresses: the three record addresses.
    """

    addresses: tuple[int, int, int]


@dataclass(frozen=True)
class Slot:
    """The firmware addresses of one film slot.

    Attributes:
        entry: the stock name of the menu entry.
        tone: where the slot's tone curves go: three tables, or three records.
        saturation: address of the pair of saturation gains.
        six_axis: addresses of the six saturation values and the six hue values.
        matrix: address of the 3 x 3 matrix.
        matrix_is_new: True if an earlier spec created the matrix table (then
            it holds the identity); False if the stock firmware has it.
        chroma: address of the 97-byte chroma-curve record.
    """

    entry: str
    tone: Tables | Records
    saturation: int
    six_axis: tuple[int, int]
    matrix: int
    matrix_is_new: bool
    chroma: int


#: The seven film slots, in menu order.
SLOTS: tuple[Slot, ...] = (
    Slot(
        entry="Pop Art",
        tone=Tables((0x7E74F1BC, 0x7E74F5BC, 0x7E7505BC)),
        saturation=0x7E7696A0,
        six_axis=(0x7E769486, 0x7E769492),
        matrix=0x7E880FC2,
        matrix_is_new=True,
        chroma=0x7E74B8BA,
    ),
    Slot(
        entry="Soft Focus",
        tone=Tables((0x7E75FAF0, 0x7E75F8F0, 0x7E7616F0)),
        saturation=0x7E7696BC,
        six_axis=(0x7E76952E, 0x7E76953A),
        matrix=0x7ECB099A,
        matrix_is_new=True,
        chroma=0x7E74BBCA,
    ),
    Slot(
        entry="Pale&Light Color",
        tone=Tables((0x7F033B7C, 0x7F033D7C, 0x7E75E8F0)),
        saturation=0x7E7696A4,
        six_axis=(0x7E76949E, 0x7E7694AA),
        matrix=0x7ECB0988,
        matrix_is_new=True,
        chroma=0x7E74B91C,
    ),
    Slot(
        entry="Light Tone",
        tone=Records((0x7E78B49C, 0x7E78B4BC, 0x7E78B4DC)),
        saturation=0x7E7696A8,
        six_axis=(0x7E7694B6, 0x7E7694C2),
        matrix=0x7E768F58,
        matrix_is_new=False,
        chroma=0x7E74B97E,
    ),
    Slot(
        entry="Pin Hole",
        tone=Tables((0x7E74EFBC, 0x7E751FBC, 0x7E7521BC)),
        saturation=0x7E7696B8,
        six_axis=(0x7E769516, 0x7E769522),
        matrix=0x7ECB09AC,
        matrix_is_new=True,
        chroma=0x7E74BB68,
    ),
    Slot(
        entry="Diorama",
        tone=Tables((0x7E754FBC, 0x7E7551BC, 0x7E757FBC)),
        saturation=0x7E7696EC,
        six_axis=(0x7E769622, 0x7E76962E),
        matrix=0x7ECB09BE,
        matrix_is_new=True,
        chroma=0x7E74BE16,
    ),
    Slot(
        entry="Cross Process",
        tone=Records((0x7E78B41C, 0x7E78B43C, 0x7E78B45C)),
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


# --------------------------------------------------------------------------
# The film slots beyond the first seven.
#
# The first seven slots keep the stored Picture Mode value of their menu
# entry. The five other art entries (Grainy Film, Gentle Sepia, Dramatic
# Tone, Key Line, Watercolor) cannot: the firmware tests their stored
# values (104, 108, 109, 119, 120) in code, in many places. So an extra slot
# gives its menu entry another stored value, one of the hidden values
# 110 to 118 that the firmware already accepts and tests nowhere, and a new
# art code that no table and no compare of the firmware knows. The stock
# filter keeps its value, its art code and all its tables: focus peaking
# uses the Key Line ones.
# How this was found: experiments/2026-11-16-films-max/NOTES.md.

#: The stock default handler of the tone-curve hash: an entry with key 0 is empty.
GAMMA_DEFAULT_HANDLER = 0x7E56B861
#: Entries in the tone-curve hash.
GAMMA_HASH_ENTRIES = 32
#: The key of an art code in the tone-curve hash is the code minus this.
GAMMA_KEY_BASE = 70
#: The shared part of the tone-curve stubs (in an earlier spec): a1 = three record addresses.
GAMMA_COMMON = 0x7ECB08A6
#: The look-curve handler that loads the identity table.
IDENTITY_LOOK_HANDLER = 0x7E56E94A

#: Jump tables that the image library reads with (art code - first code).
LOOK_JUMP = (0x7E78C8E4, 8)
SATURATION_JUMP = (0x7E78C514, 69)
SIX_AXIS_JUMP = (0x7E78C254, 9)
CHROMA_JUMP = (0x7E78AEA4, 69)

#: The last jump of the art-matrix compare chain of an earlier spec ("no film
#: code": back to the stock code), and the two places the chain goes to.
MATRIX_CHAIN_EXIT = 0x7ECB094C
MATRIX_CHAIN_EXIT_BYTES = bytes.fromhex("dc1fbe8bff")
MATRIX_USE = 0x7E56C764
MATRIX_NONE = 0x7E56C76B

#: Tables with one entry per stored Picture Mode value 100 to 120.
FIRST_ART_VALUE = 100
LAST_ART_VALUE = 120
#: art_GetFilterType: its jump table, and where a stub goes with the code in d2.
FILTER_TYPE_JUMP = 0x7E854A24
FILTER_TYPE_TAIL = 0x7E71BEA3
#: The two live-view functions: (still table, movie table, where a stub goes).
LIVE_VIEW = (
    (0x7E7FF05C, 0x7E7FF008, 0x7E6CC14E),
    (0x7E807880, 0x7E80782C, 0x7E6DBBC4),
)
#: The record code's class of a Picture Mode, and the entry "colour only".
KIND_JUMP = 0x7E8522AC
KIND_COLOUR_ONLY = 0x7E70DBF4
#: The EXIF writer's case per Picture Mode, and the case of Pop Art.
EXIF_JUMP = 0x7E852300
EXIF_POP_ART = 0x7E70DC9F
#: "Is this Picture Mode an art filter" of the shooting application, and its "yes".
IS_ART_JUMP = 0x7EBBAA10
IS_ART_YES = 0x7E9416F4

#: Hash tables with the stored Picture Mode as key (32 entries of key, target;
#: the first place of a key is key & 31). An extra slot's value gets the
#: target of the named value: its own stock entry for the colour-tone name,
#: Pop Art for the two classes that are the same for every art filter.
VALUE_HASH_ENTRIES = 32
COLOUR_TONE_HASH = 0x7EC4A864
MOVIE_TAG_HASH = 0x7E810200
RECORD_CLASS_HASH = 0x7E851A94
POP_ART_VALUE = 100

#: The Picture Mode value lists of settings 111, 509 and 510: 64 bytes per
#: entry, the stored value in the first byte.
VALUE_LISTS = (0x7E844CC0, 0x7E846F40, 0x7E847400)
VALUE_LIST_STEP = 64
#: Lists "the Picture Mode is an art filter" of the same three settings: 8
#: bytes per entry, the stored value in the first byte; the first entry is value 100.
ART_VALUE_LISTS = (0x7E818EFA, 0x7E82405E, 0x7E82417E)
ART_VALUE_LIST_STEP = 8
#: The presets of the shooting modes: 12-byte rows of (mode code, kind, list
#: address, count) up to a row with code 0; a list holds (setting, value)
#: pairs of 32-bit words. The preset of an ART filter (kind 1) sets setting
#: 111, the Picture Mode, to the stored value of the filter's menu entry.
MODE_PRESETS = 0x7E834794
MODE_PRESET_ROW = 12
ART_PRESET_KIND = 1
PICTURE_MODE_SETTING = 111
#: Place of the first art entry (Pop Art) in a Picture Mode value list.
FIRST_ART_PLACE = 7

#: Free space for the new code and data of the extra slots: two runs of the
#: area 0x7EBF1090-0x7EBF3BAD in segment 2 (camera-tested code and data are in
#: that area), next to what the pinned build and the debug log keep there.
EXTRA_DATA_AREA = (0x7EBF38BC, 0x7EBF3BAD)
EXTRA_CODE_AREA = (0x7EBF2E80, 0x7EBF3000)


@dataclass(frozen=True)
class BracketSites:
    """Where the three ART bracket routines hold a stored value as a constant.

    Each address is the value byte of a ``cmp`` or ``mov`` instruction: the
    two list builders of the menu (0x7EA7633A, 0x7EA9528D) and the frame
    routine of the capture code (0x7E5A75AE and its helper).

    Attributes:
        addresses: the six byte addresses.
    """

    addresses: tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class ExtraSlot:
    """A film slot that gives its menu entry a hidden stored value.

    Attributes:
        look: where the look's numbers go. ``look.entry`` is the stock name of
            the menu entry. The saturation, six-axis and chroma tables are the
            stock tables of an art code that no menu entry reaches. The matrix
            is in free space: the looks spec writes it there.
        place: the place of the entry in a Picture Mode value list (Pop Art is 7).
        stock_value: the stored Picture Mode value of the stock entry.
        value: the hidden stored value that the entry stores instead.
        art_code: the new art code, for still pictures, live view and movies.
        gamma_entry: the entry of the tone-curve hash that the code takes.
        saturation_handler: the stock handler that loads ``look.saturation``.
        six_axis_handler: the stock handler that loads ``look.six_axis``.
        chroma_handler: the stock handler that loads ``look.chroma``.
        bracket: the constants of the ART bracket routines for the entry.
        art_mode_code: the code of the entry in ART shooting mode (setting 281).
        preset_value: address of the stored value in the preset of that ART
            filter: what the camera stores when the entry is chosen in ART mode.
    """

    look: Slot
    place: int
    stock_value: int
    value: int
    art_code: int
    gamma_entry: int
    saturation_handler: int
    six_axis_handler: int
    chroma_handler: int
    bracket: BracketSites
    art_mode_code: int
    preset_value: int

    @property
    def entry(self) -> str:
        """The stock name of the menu entry."""
        return self.look.entry


def _extra(
    entry: str,
    place: int,
    values: tuple[int, int],
    code: tuple[int, int],
    tone: tuple[int, int, int],
    saturation: tuple[int, int],
    six_axis: tuple[int, int, int],
    chroma: tuple[int, int],
    matrix: int,
    bracket: tuple[int, int, int, int, int, int],
    art_mode: tuple[int, int],
) -> ExtraSlot:
    """Return an extra slot from its numbers (handler first, then its tables)."""
    return ExtraSlot(
        look=Slot(
            entry=entry,
            tone=Tables(tone),
            saturation=saturation[1],
            six_axis=(six_axis[1], six_axis[2]),
            matrix=matrix,
            matrix_is_new=False,
            chroma=chroma[1],
        ),
        place=place,
        stock_value=values[0],
        value=values[1],
        art_code=code[0],
        gamma_entry=code[1],
        saturation_handler=saturation[0],
        six_axis_handler=six_axis[0],
        chroma_handler=chroma[0],
        bracket=BracketSites(bracket),
        art_mode_code=art_mode[0],
        preset_value=art_mode[1],
    )


#: Bytes of an art matrix (9 x int16).
MATRIX_BYTES = 18
#: Where the matrices of the extra slots are: at the end of the data area.
EXTRA_MATRICES = EXTRA_DATA_AREA[1] - 5 * MATRIX_BYTES - 1

#: The extra film slots, in menu order. Tone tables: fifteen stock tables that
#: no record points at since the first film specs. The other tables are those
#: of Pin Hole I, Diorama, Pin Hole II, Pin Hole III and of art code 153.
EXTRA_SLOTS: tuple[ExtraSlot, ...] = (
    _extra(
        "Grainy Film",
        place=11,
        values=(104, 111),
        code=(94, 24),
        tone=(0x7E74F3BC, 0x7E7503BC, 0x7E7523BC),
        saturation=(0x7E56DCB9, 0x7E7696AC),
        six_axis=(0x7E56D593, 0x7E7694CE, 0x7E7694DA),
        chroma=(0x7E566418, 0x7E74B9E0),
        matrix=EXTRA_MATRICES,
        bracket=(
            0x7EA76424,
            0x7EA76443,
            0x7EA9536D,
            0x7EA9538D,
            0x7E5A7665,
            0x7E5A7A2E,
        ),
        art_mode=(74, 0x7E82B810),
    ),
    _extra(
        "Gentle Sepia",
        place=15,
        values=(108, 112),
        code=(98, 28),
        tone=(0x7E7525BC, 0x7E7533BC, 0x7E7535BC),
        saturation=(0x7E56DCC2, 0x7E7696B0),
        six_axis=(0x7E56D5A2, 0x7E7694E6, 0x7E7694F2),
        chroma=(0x7E56645C, 0x7E74BA42),
        matrix=EXTRA_MATRICES + MATRIX_BYTES,
        bracket=(
            0x7EA764C6,
            0x7EA764E6,
            0x7EA9540D,
            0x7EA9542D,
            0x7E5A76FE,
            0x7E5A7AFB,
        ),
        art_mode=(91, 0x7E82C1C0),
    ),
    _extra(
        "Dramatic Tone",
        place=16,
        values=(109, 114),
        code=(144, 18),
        tone=(0x7E7553BC, 0x7E7555BC, 0x7E7563BC),
        saturation=(0x7E56DCE6, 0x7E7696C0),
        six_axis=(0x7E56D715, 0x7E769546, 0x7E769552),
        chroma=(0x7E5665B0, 0x7E74BC2C),
        matrix=EXTRA_MATRICES + 2 * MATRIX_BYTES,
        bracket=(
            0x7EA764EF,
            0x7EA7650E,
            0x7EA95435,
            0x7EA95455,
            0x7E5A7725,
            0x7E5A7B18,
        ),
        art_mode=(96, 0x7E82C4F8),
    ),
    _extra(
        "Key Line",
        place=17,
        values=(119, 115),
        code=(156, 22),
        tone=(0x7E7565BC, 0x7E7581BC, 0x7E7583BC),
        saturation=(0x7E56DCEF, 0x7E7696C4),
        six_axis=(0x7E56D724, 0x7E76955E, 0x7E76956A),
        chroma=(0x7E5665F4, 0x7E74BC8E),
        matrix=EXTRA_MATRICES + 3 * MATRIX_BYTES,
        bracket=(
            0x7EA76517,
            0x7EA76537,
            0x7EA9545D,
            0x7EA9547C,
            0x7E5A774C,
            0x7E5A7B6E,
        ),
        art_mode=(163, 0x7E82C830),
    ),
    _extra(
        "Watercolor",
        place=18,
        values=(120, 118),
        code=(159, 25),
        tone=(0x7E7585BC, 0x7E7593BC, 0x7E7595BC),
        saturation=(0x7E56DD08, 0x7E7696E8),
        six_axis=(0x7E56D751, 0x7E76960A, 0x7E769616),
        chroma=(0x7E5666C0, 0x7E74BDB4),
        matrix=EXTRA_MATRICES + 4 * MATRIX_BYTES,
        bracket=(
            0x7EA76540,
            0x7EA7655F,
            0x7EA95484,
            0x7EA954A3,
            0x7E5A776F,
            0x7E5A7B9C,
        ),
        art_mode=(181, 0x7E82CB68),
    ),
)

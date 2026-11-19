"""Generate the patch specs of the film looks beyond the first seven.

The first seven films take over menu entries whose stored Picture Mode value
the firmware treats as a plain colour filter. The five other art entries do
not allow that: the firmware tests their stored values in code. An extra slot
(``slots.ExtraSlot``) therefore gives its menu entry a hidden stored value and
a new art code. Three kinds of spec come out:

* the structure: new code and data in free space (tone-curve stubs and
  records, a second part of the art-matrix compare chain, and one stub per
  table that turns a stored value into an art code), the
  entries of the image library's tables for the new art codes, and the entries
  of the tables and hash tables that the firmware reads with a stored value.
  Nothing of it runs or is read while no menu entry stores a hidden value;
* the looks: for every extra slot its tone tables, saturation gains, six-axis
  values, matrix and chroma curves;
* one entry spec per slot: the menu entry stores the hidden value. It changes
  one byte in each Picture Mode value list, in each constant of the ART
  bracket routines and in the preset of the entry's filter in ART shooting
  mode. Without its entry spec a menu entry is the stock filter.

The specs are deltas on the specs of the first seven films: the structure
changes one jump that ``remap7b-code`` wrote.

This module needs numpy.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

from ..container import parse
from ..errors import BuildError
from ..paths import RepoPaths
from ..spec import BytesOp
from ..stock import StockFirmware, read_stock
from . import slots
from .films import Film, MoreFilmList, load_more_films, more_inputs_digest
from .generate import (
    ATTRIBUTION,
    PROGRAM_BLOCK,
    GeneratedSpec,
    Program,
    _changing,
    film_ops,
    load_fit,
)

#: The tone-curve stub of a slot: ``mov triple,a1`` and ``jmp`` to the shared part.
_STUB_BYTES = 11
_TRIPLE_BYTES = 12
_RECORD_BYTES = 4 * slots.RECORD_TABLES


def jump(at: int, target: int) -> bytes:
    """Return ``jmp target`` (5 bytes) for the address ``at``."""
    return b"\xdc" + struct.pack("<i", target - at)


def load_a1(value: int) -> bytes:
    """Return ``mov value,a1`` (6 bytes)."""
    return b"\xfc\xdd" + struct.pack("<I", value)


def load_d2(code: int) -> bytes:
    """Return ``mov code,d2`` for an art code (2 or 3 bytes).

    The short form extends the sign of its byte, so it is for codes below 128.
    """
    if not 0 <= code <= 0xFF:
        raise BuildError(f"art code {code} is not a byte")
    if code < 0x80:
        return bytes((0x8A, code))
    return b"\x2e" + struct.pack("<H", code)


def compare_d0(code: int) -> bytes:
    """Return ``cmp code,d0`` for an art code (2 or 4 bytes)."""
    if not 0 <= code <= 0xFF:
        raise BuildError(f"art code {code} is not a byte")
    if code < 0x80:
        return bytes((0xA0, code))
    return b"\xfa\xc8" + struct.pack("<H", code)


def branch(opcode: int, at: int, target: int) -> bytes:
    """Return a 2-byte branch (``beq`` 0xC8, ``bra`` 0xCA) from ``at`` to ``target``.

    Raises:
        BuildError: if the target is too far for a 2-byte branch.
    """
    distance = target - at
    if not -128 <= distance <= 127:
        raise BuildError(f"a short branch cannot reach {target:#x} from {at:#x}")
    return bytes((opcode,)) + struct.pack("<b", distance)


class Layout:
    """Where the new code and data of the extra slots are.

    The data area holds, from its start: one tone-curve stub per slot, then
    (4-aligned) one triple of record addresses per slot and three tone records
    per slot. The matrices are at the addresses that the slots name; the looks
    spec writes them. The code
    area holds the second part of the art-matrix chain and three stubs per
    slot (for ``art_GetFilterType`` and the two live-view functions).

    Attributes:
        slots: the extra slots.
        gamma_stubs: address of each slot's tone-curve stub.
        triples: address of each slot's triple of record addresses.
        records: address of each slot's three tone records.
        chain: address of the second part of the art-matrix chain.
        value_stubs: per slot, the stubs for the three functions.
        data: the bytes of the data area up to the end of the records.
        code: the bytes of the code area.
    """

    def __init__(self, extra: Sequence[slots.ExtraSlot], defaults: Sequence[int]):
        """Lay out the areas for the slots.

        Args:
            extra: the extra slots.
            defaults: the eight table addresses of the default tone record.

        Raises:
            BuildError: if the areas are too small.
        """
        self.slots = tuple(extra)
        count = len(self.slots)
        start, end = slots.EXTRA_DATA_AREA
        self.gamma_stubs = [start + _STUB_BYTES * i for i in range(count)]
        triples = (start + _STUB_BYTES * count + 3) & ~3
        self.triples = [triples + _TRIPLE_BYTES * i for i in range(count)]
        records = triples + _TRIPLE_BYTES * count
        self.records = [records + 3 * _RECORD_BYTES * i for i in range(count)]
        data_end = records + 3 * _RECORD_BYTES * count
        matrices = [slot.look.matrix for slot in self.slots]
        if data_end > min(matrices) or max(matrices) + slots.MATRIX_BYTES > end:
            raise BuildError("the data area is too small for the extra slots")

        data = bytearray()
        for stub, triple in zip(self.gamma_stubs, self.triples):
            data += load_a1(triple) + jump(stub + 6, slots.GAMMA_COMMON)
        data += b"\0" * (triples - start - len(data))
        for record in self.records:
            data += struct.pack(
                "<3I", record, record + _RECORD_BYTES, record + 2 * _RECORD_BYTES
            )
        for slot in self.slots:
            if not isinstance(slot.look.tone, slots.Tables):
                raise BuildError("an extra slot keeps its tone curves in tables")
            for table in slot.look.tone.addresses:
                # member 0 of each of the four columns is the default table,
                # member 1 is the film's table (as the first seven slots do)
                members = [
                    table if index % 2 else defaults[index]
                    for index in range(slots.RECORD_TABLES)
                ]
                data += struct.pack(f"<{slots.RECORD_TABLES}I", *members)
        self.data = bytes(data)

        self.chain, code_end = slots.EXTRA_CODE_AREA
        tests = [compare_d0(slot.art_code) for slot in self.slots]
        loads_at = self.chain + sum(len(test) + 2 for test in tests) + 5
        use = loads_at + 8 * count
        code = bytearray()
        for index, test in enumerate(tests):
            at = self.chain + len(code) + len(test)
            code += test + branch(0xC8, at, loads_at + 8 * index)
        code += jump(self.chain + len(code), slots.MATRIX_NONE)
        for index, slot in enumerate(self.slots):
            at = loads_at + 8 * index
            code += load_a1(slot.look.matrix) + branch(0xCA, at + 6, use)
        code += b"\xf1\xec" + jump(use + 2, slots.MATRIX_USE)  # mov d3,a0
        tails = [slots.FILTER_TYPE_TAIL] + [tail for _, _, tail in slots.LIVE_VIEW]
        self.value_stubs: list[list[int]] = []
        for slot in self.slots:
            stubs = []
            for tail in tails:
                at = self.chain + len(code)
                stubs.append(at)
                load = load_d2(slot.art_code)
                code += load + jump(at + len(load), tail)
            self.value_stubs.append(stubs)
        if self.chain + len(code) > code_end:
            raise BuildError("the code area is too small for the extra slots")
        self.code = bytes(code)


def _word(program: Program, address: int, value: int) -> BytesOp:
    """Return an operation that writes one 32-bit word."""
    return program.op(address, struct.pack("<I", value))


def hash_ops(
    program: Program, table: int, keys: Sequence[tuple[int, int]]
) -> list[BytesOp]:
    """Return the operations that add keys to a hash table of the firmware.

    The table has 32 entries of (key, target). A key's first place is
    ``key & 31``; the firmware then goes on entry by entry, around the end,
    until it finds the key or an empty entry (key 0).

    Args:
        program: block 0 of the stock firmware.
        table: address of the table.
        keys: (new key, key whose target the new key gets), in order.

    Raises:
        BuildError: if a new key is in the table already, the other key is
            not in it, or the table is full.
    """
    count = slots.VALUE_HASH_ENTRIES
    raw = program.read(table, 8 * count)
    entries = [list(struct.unpack_from("<2I", raw, 8 * i)) for i in range(count)]

    def find(key: int) -> int | None:
        """Return the place of a key, as the firmware finds it, or None."""
        place = key & (count - 1)
        for _ in range(count):
            if entries[place][0] == key:
                return place
            if entries[place][0] == 0:
                return None
            place = (place + 1) % count
        return None

    ops = []
    for key, like in keys:
        source = find(like)
        if source is None:
            raise BuildError(f"hash table {table:#x}: no key {like}")
        if find(key) is not None:
            raise BuildError(f"hash table {table:#x}: key {key} is there already")
        place = key & (count - 1)
        for _ in range(count):
            if entries[place][0] == 0:
                break
            place = (place + 1) % count
        else:
            raise BuildError(f"hash table {table:#x}: full")
        entries[place] = [key, entries[source][1]]
        ops.append(program.op(table + 8 * place, struct.pack("<2I", *entries[place])))
    return ops


def structure_ops(program: Program, layout: Layout) -> list[BytesOp]:
    """Return the operations that make the extra slots.

    Raises:
        BuildError: if a slot's numbers do not fit the firmware's tables.
    """
    ops = [
        program.op(slots.EXTRA_DATA_AREA[0], layout.data),
        program.op(layout.chain, layout.code),
        program.op(
            slots.MATRIX_CHAIN_EXIT,
            jump(slots.MATRIX_CHAIN_EXIT, layout.chain),
            slots.MATRIX_CHAIN_EXIT_BYTES,
        ),
    ]
    for index, slot in enumerate(layout.slots):
        key = slot.art_code - slots.GAMMA_KEY_BASE
        if not 0 < key and slot.gamma_entry < slots.GAMMA_HASH_ENTRIES:
            raise BuildError(f"art code {slot.art_code} has no tone-curve key")
        ops.append(
            program.op(
                slots.GAMMA_HASH + 8 * slot.gamma_entry,
                struct.pack("<2I", key, layout.gamma_stubs[index]),
            )
        )
        for (table, first), handler in (
            (slots.LOOK_JUMP, slots.IDENTITY_LOOK_HANDLER),
            (slots.SATURATION_JUMP, slot.saturation_handler),
            (slots.SIX_AXIS_JUMP, slot.six_axis_handler),
            (slots.CHROMA_JUMP, slot.chroma_handler),
        ):
            ops.append(_word(program, table + 4 * (slot.art_code - first), handler))

        if not slots.FIRST_ART_VALUE <= slot.value <= slots.LAST_ART_VALUE:
            raise BuildError(f"stored value {slot.value} is not an art value")
        row = 4 * (slot.value - slots.FIRST_ART_VALUE)
        for_type, *for_live_view = layout.value_stubs[index]
        ops.append(_word(program, slots.FILTER_TYPE_JUMP + row, for_type))
        for (still, movie, _), stub in zip(slots.LIVE_VIEW, for_live_view):
            ops.append(_word(program, still + row, stub))
            ops.append(_word(program, movie + row, stub))
        ops.append(_word(program, slots.KIND_JUMP + row, slots.KIND_COLOUR_ONLY))
        ops.append(_word(program, slots.EXIF_JUMP + row, slots.EXIF_POP_ART))
        ops.append(_word(program, slots.IS_ART_JUMP + row, slots.IS_ART_YES))

    own = [(slot.value, slot.stock_value) for slot in layout.slots]
    pop_art = [(slot.value, slots.POP_ART_VALUE) for slot in layout.slots]
    ops += hash_ops(program, slots.COLOUR_TONE_HASH, own)
    ops += hash_ops(program, slots.MOVIE_TAG_HASH, pop_art)
    ops += hash_ops(program, slots.RECORD_CLASS_HASH, pop_art)
    return ops


def entry_ops(program: Program, slot: slots.ExtraSlot) -> list[BytesOp]:
    """Return the operations that give a menu entry its hidden stored value.

    Raises:
        BuildError: if a byte that should hold the stock value holds another.
    """
    row = slot.place - slots.FIRST_ART_PLACE
    addresses = [
        table + slots.VALUE_LIST_STEP * slot.place for table in slots.VALUE_LISTS
    ]
    addresses += [
        table + slots.ART_VALUE_LIST_STEP * row for table in slots.ART_VALUE_LISTS
    ]
    addresses += list(slot.bracket.addresses)
    addresses.append(slot.preset_value)
    setting = program.read(slot.preset_value - 4, 4)
    if setting != struct.pack("<I", slots.PICTURE_MODE_SETTING):
        raise BuildError(
            f"{slot.entry}: {slot.preset_value:#x} is not the Picture Mode of a preset"
        )
    old, new = bytes((slot.stock_value,)), bytes((slot.value,))
    for address in addresses:
        if program.read(address, 1) != old:
            raise BuildError(
                f"{slot.entry}: {address:#x} does not hold the stored value "
                f"{slot.stock_value}"
            )
    return [program.op(address, new) for address in addresses]


def _film_text(films: Sequence[Film]) -> str:
    """Return "entry = film" for every film, for a description."""
    return "; ".join(f"{film.entry} = {film.film}" for film in films)


def generate(paths: RepoPaths, stock: StockFirmware) -> list[GeneratedSpec]:
    """Generate the patch specs of the films beyond the first seven.

    Args:
        paths: the repository; the stock firmware must be in it.
        stock: the stock firmware.

    Returns:
        The structure spec, the looks spec and one entry spec per film.

    Raises:
        BuildError: if the film list or a fit file is wrong, or the slots do
            not fit the firmware.
        StockError: if the stock firmware is missing or is another file.
    """
    film_list: MoreFilmList = load_more_films(paths)
    digest = more_inputs_digest(paths, film_list)
    container = parse(read_stock(paths, stock))
    program = Program(container.blocks[PROGRAM_BLOCK].payload)
    layout = Layout(slots.EXTRA_SLOTS, program.record(slots.DEFAULT_RECORD))

    looks: list[BytesOp] = []
    for film, slot in zip(film_list.films, slots.EXTRA_SLOTS):
        looks += film_ops(program, film, load_fit(paths.resolve(film.fit)), slot.look)

    codes = ", ".join(
        f"{slot.entry}: stored value {slot.value}, art code {slot.art_code}"
        for slot in slots.EXTRA_SLOTS
    )
    specs = [
        GeneratedSpec(
            path=film_list.structure_spec,
            description=(
                "Film slots beyond the first seven, structure: tone-curve stubs "
                "and records and a second part of the art-matrix chain in free "
                "space of segment 2; the image library's table "
                "entries of the new art codes; and the entries of the tables "
                "that the firmware reads with a stored Picture Mode value ("
                f"{codes}). A delta on patches/remap7b-code.json: it changes the "
                "last jump of that spec's matrix chain. No menu entry stores one "
                "of these values without its entry spec."
            ),
            ops=_changing(structure_ops(program, layout)),
            inputs_sha256=digest,
        ),
        GeneratedSpec(
            path=film_list.looks_spec,
            description=(
                "Film looks beyond the first seven, one per extra slot, in menu "
                f"order: {_film_text(film_list.films)}. Needs the structure spec "
                "before it."
            ),
            ops=_changing(looks),
            inputs_sha256=digest,
            attribution=ATTRIBUTION,
        ),
    ]
    for film, slot, path in zip(
        film_list.films, slots.EXTRA_SLOTS, film_list.entry_specs
    ):
        specs.append(
            GeneratedSpec(
                path=path,
                description=(
                    f"The menu entry {slot.entry} stores the hidden Picture Mode "
                    f"value {slot.value} in place of {slot.stock_value}, so it "
                    f"selects the film look {film.film} (art code "
                    f"{slot.art_code}): one byte in each Picture Mode value list, "
                    "in each constant of the ART bracket routines and in the "
                    "preset of the filter in ART shooting mode. Needs the "
                    "structure spec and the looks spec. Leave this spec out and "
                    f"the entry is the stock filter {slot.entry} again."
                ),
                ops=_changing(entry_ops(program, slot)),
                inputs_sha256=digest,
            )
        )
    return specs

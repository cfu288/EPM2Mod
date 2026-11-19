"""Generate the patch specs of the film list with a black-and-white film.

``looks/films-12-bw.json`` is a variant of the list of the films beyond the
first seven (``extra``). The entry Grainy Film holds a black-and-white film
and keeps its stock stored value and art codes, so the firmware makes the
picture monochrome and runs its grain program (``slots.MonoSlot``). The colour
film that ``extra`` puts in that entry moves to another entry. Two specs come
out. Both are deltas on the specs of ``extra``, which all stay in the build
except the entry specs of the two entries:

* the entry spec: the other entry stores the hidden value of the colour film
  (the value that ``extra`` gives to Grainy Film), and the colour-tone name of
  that value becomes the name of the other entry;
* the black-and-white look: a third part of the art-matrix chain with the
  matrix behind it (how colours turn into grey), the grain program's
  contrast table (the tone of still pictures) and the look table for live
  view and movies.

A later fit of the film (a refit, made after a camera measurement) gets a
spec of its own, a delta on the black-and-white look: its grain table goes
into a spare table and the grain program's load instruction is pointed at it.
The spec of the first fit stays in the build and is not changed, so the
builds that were tested with it stay as they are.

This module needs numpy.
"""

from __future__ import annotations

import dataclasses
import struct

import numpy as np

from ..container import parse
from ..errors import BuildError
from ..paths import RepoPaths
from ..spec import BytesOp
from ..stock import StockFirmware, read_stock
from . import slots
from .extra import Layout, branch, compare_d0, entry_ops, hash_ops, jump, load_a1
from .films import BwFilmList, bw_inputs_digest, load_bw_films, load_more_films
from .generate import (
    ATTRIBUTION,
    PROGRAM_BLOCK,
    Fit,
    GeneratedSpec,
    Program,
    _array,
    _changing,
    load_fit,
    whole_numbers,
)

#: ``mov d3,a0``: the matrix code wants the place of the result in a0.
_MOV_D3_A0 = b"\xf1\xec"
_BEQ = 0xC8


def chain_tail(at: int, codes: tuple[int, ...], matrix: tuple[int, ...]) -> bytes:
    """Return a part of the art-matrix chain for more art codes, with its matrix.

    The part compares d0 with each code. If one is equal it loads the matrix
    and goes to the stock code that uses it; else it goes to the stock code
    for "no art matrix". The matrix (9 x int16) follows the code.

    Args:
        at: the address of the part.
        codes: the art codes.
        matrix: the nine values of the matrix.
    """
    tests = [compare_d0(code) for code in codes]
    load = at + sum(len(test) + 2 for test in tests) + 5
    table = load + 6 + len(_MOV_D3_A0) + 5
    code = bytearray()
    for test in tests:
        code += test + branch(_BEQ, at + len(code) + len(test), load)
    code += jump(at + len(code), slots.MATRIX_NONE)
    code += load_a1(table) + _MOV_D3_A0
    code += jump(at + len(code), slots.MATRIX_USE)
    return bytes(code) + struct.pack("<9h", *matrix)


def chain_ops(
    program: Program, layout: Layout, codes: tuple[int, ...], matrix: tuple[int, ...]
) -> list[BytesOp]:
    """Return the operations that add a part to the art-matrix chain.

    The last jump of the chain of the extra slots ("no film code") goes to
    the new part, which is put behind the code of the extra slots.

    Raises:
        BuildError: if the chain of ``layout`` has another shape, or the new
            part does not fit the code area.
    """
    exit_at = layout.chain + layout.code.find(b"\xdc")
    stock_exit = jump(exit_at, slots.MATRIX_NONE)
    offset = exit_at - layout.chain
    if layout.code[offset : offset + 5] != stock_exit:
        raise BuildError("the art-matrix chain of the extra slots has another shape")
    tail_at = layout.chain + len(layout.code)
    tail = chain_tail(tail_at, codes, matrix)
    if tail_at + len(tail) > slots.EXTRA_CODE_AREA[1]:
        raise BuildError("the code area is too small for the black-and-white slot")
    return [
        program.op(exit_at, jump(exit_at, tail_at), stock_exit),
        program.op(tail_at, tail),
    ]


def pack_tone(fit: Fit, key: str, where: str) -> bytes:
    """Return a 512-byte table of a fit: 256 rising 10-bit values.

    Raises:
        BuildError: if the fit lacks the array or it is not such a table.
    """
    values = whole_numbers(
        _array(fit, key, where),
        slots.TABLE_ENTRIES,
        0,
        slots.CURVE_POINTS - 1,
        f"'{key}'",
        where,
    )
    if np.any(np.diff(values) < 0):
        raise BuildError(f"{where}: '{key}' must not fall")
    return struct.pack(f"<{slots.TABLE_ENTRIES}H", *values)


def mono_ops(program: Program, layout: Layout, fit: Fit, where: str) -> list[BytesOp]:
    """Return the operations that write a black-and-white film into its slot.

    Args:
        program: block 0 of the stock firmware.
        layout: the layout of the extra slots (the structure spec of ``extra``).
        fit: the arrays of the fit file: ``A`` (the art matrix), ``T`` (the
            grain program's contrast table), ``L`` (the look table for live
            view and movies).
        where: the name of the fit file, for messages.

    Raises:
        BuildError: if the fit lacks an array or holds values that do not fit,
            or the firmware does not load the two tables where the slot says.
    """
    slot = slots.MONO_SLOT
    for load, opcode, table in (
        (slot.grain_load, b"\xfc\xcd", slot.grain_table),
        (slot.live_load, b"\xfc\xdc", slot.live_look),
    ):
        if program.read(load, 6) != opcode + struct.pack("<I", table):
            raise BuildError(f"{load:#x} does not load the table {table:#x}")
    matrix = whole_numbers(_array(fit, "A", where), 9, -0x8000, 0x7FFF, "'A'", where)
    return chain_ops(program, layout, slot.art_codes, tuple(matrix)) + [
        program.op(slot.grain_table, pack_tone(fit, "T", where)),
        program.op(slot.live_look, pack_tone(fit, "L", where)),
    ]


def refit_ops(
    program: Program, first: Fit, fit: Fit, where: str, spare: tuple[int, int]
) -> list[BytesOp]:
    """Return the operations of a later fit of the black-and-white film.

    The grain table of the fit is written into a spare table, and the
    instruction that loads the grain table gets the address of that table.

    Args:
        program: block 0 of the stock firmware.
        first: the arrays of the first fit, whose spec comes before this one.
        fit: the arrays of the later fit.
        where: the name of the later fit file, for messages.
        spare: the address of the spare table and of the stock instruction
            that loads it.

    Raises:
        BuildError: if the later fit has another matrix or live-view table
            than the first one (only the grain table can change), or the
            firmware does not load the tables where the slot says.
    """
    slot = slots.MONO_SLOT
    table, loader = spare
    for key in ("A", "L"):
        if not np.array_equal(_array(first, key, where), _array(fit, key, where)):
            raise BuildError(
                f"{where}: '{key}' differs from the first fit; a refit changes "
                "the grain table only"
            )
    old = struct.pack("<I", slot.grain_table)
    if program.read(slot.grain_load, 6) != b"\xfc\xcd" + old:
        raise BuildError(f"{slot.grain_load:#x} does not load the grain table")
    if program.read(loader, 6) != b"\xfc\xdc" + struct.pack("<I", table):
        raise BuildError(f"{loader:#x} does not load the table {table:#x}")
    return [
        program.op(slot.grain_load + 2, struct.pack("<I", table), old),
        program.op(table, pack_tone(fit, "T", where)),
    ]


def moved_entry_ops(
    program: Program, source: slots.ExtraSlot, target: slots.ExtraSlot
) -> list[BytesOp]:
    """Return the operations that give the entry of ``target`` the film of ``source``.

    The entry stores the hidden value of ``source``. The structure spec of
    ``extra`` gives that value the colour-tone name of the entry of
    ``source``; here it gets the name of the entry of ``target``.

    Raises:
        BuildError: if the firmware's tables are not as the slots say.
    """
    ops = entry_ops(program, dataclasses.replace(target, value=source.value))
    own = [(slot.value, slot.stock_value) for slot in slots.EXTRA_SLOTS]
    name_ops = hash_ops(program, slots.COLOUR_TONE_HASH, own)
    wanted = hash_ops(
        program, slots.COLOUR_TONE_HASH, [(source.value, target.stock_value)]
    )[0]
    key = struct.pack("<I", source.value)
    for op in name_ops:
        if op.new[:4] == key:
            address = slots.BLOCK0_BASE + op.offset + 4
            return ops + [program.op(address, wanted.new[4:], op.new[4:])]
    raise BuildError(f"the structure spec gives the value {source.value} no name")


def generate(paths: RepoPaths, stock: StockFirmware) -> list[GeneratedSpec]:
    """Generate the patch specs of the film list with a black-and-white film.

    Args:
        paths: the repository; the stock firmware must be in it.
        stock: the stock firmware.

    Returns:
        The entry spec, the black-and-white spec and one spec per refit.

    Raises:
        BuildError: if a film list or the fit file is wrong, or the slots do
            not fit the firmware.
        StockError: if the stock firmware is missing or is another file.
    """
    film_list: BwFilmList = load_bw_films(paths)
    digest = bw_inputs_digest(paths, film_list)
    container = parse(read_stock(paths, stock))
    program = Program(container.blocks[PROGRAM_BLOCK].payload)
    layout = Layout(slots.EXTRA_SLOTS, program.record(slots.DEFAULT_RECORD))
    by_entry = {slot.entry: slot for slot in slots.EXTRA_SLOTS}
    source, target = by_entry[slots.MONO_SLOT.entry], by_entry[film_list.moved_to]
    colour = {film.entry: film for film in load_more_films(paths).films}
    moved, gone = colour[source.entry], colour[target.entry]
    mono = film_list.mono
    still, movie = slots.MONO_SLOT.art_codes
    first = load_fit(paths.resolve(mono.fit))
    refits = [
        GeneratedSpec(
            path=spec,
            description=(
                f"Fit {number} of the black-and-white film {mono.film} in the "
                f"menu entry {mono.entry} ({fit}): its grain table, the tone of "
                f"still pictures, in the stock table {table:#x} (the look table "
                "of an art code that no menu entry reaches), and the address in "
                "the instruction that loads the grain program's table "
                f"({slots.MONO_SLOT.grain_load:#x}, 4 bytes). The matrix and the "
                "look table for live view are those of the first fit. A delta "
                f"on {film_list.mono_spec}: put it after that spec."
            ),
            ops=_changing(
                refit_ops(
                    program, first, load_fit(paths.resolve(fit)), fit, (table, loader)
                )
            ),
            inputs_sha256=digest,
            attribution=ATTRIBUTION,
        )
        for number, ((fit, spec), (table, loader)) in enumerate(
            zip(film_list.refits, slots.MONO_SLOT.spare_tables), start=2
        )
    ]
    return [
        GeneratedSpec(
            path=film_list.entry_spec,
            description=(
                f"The menu entry {target.entry} stores the hidden Picture Mode "
                f"value {source.value} in place of {target.stock_value}, so it "
                f"selects the film look {moved.film} (art code {source.art_code}), "
                f"which the twelve-film build has in the entry {source.entry}; "
                f"and the colour-tone name of the value {source.value} becomes "
                f"that of the entry {target.entry}. {gone.film} leaves the list. "
                "A delta on the structure spec of the twelve-film build. It "
                f"takes the place of the entry spec of {target.entry}; leave "
                f"the entry spec of {source.entry} out too."
            ),
            ops=_changing(moved_entry_ops(program, source, target)),
            inputs_sha256=digest,
        ),
        GeneratedSpec(
            path=film_list.mono_spec,
            description=(
                f"The black-and-white film {mono.film} ({mono.medium}) in the "
                f"menu entry {mono.entry}. The entry keeps its stored value and "
                f"its art codes {still} and {movie}: the firmware makes the "
                "picture monochrome and runs its grain program as before. The "
                "spec adds a third part to the art-matrix chain, with the "
                "matrix behind it (how colours turn into grey), and writes the "
                "contrast table of the grain program (the tone of still "
                "pictures) and the look table of the two codes for live view "
                "and movies. A delta on the structure spec of the twelve-film "
                "build: it changes the last jump of that spec's chain. Leave "
                f"the entry spec of {mono.entry} out of the build. Grainy Film "
                "II is not changed."
            ),
            ops=_changing(mono_ops(program, layout, first, mono.fit)),
            inputs_sha256=digest,
            attribution=ATTRIBUTION,
        ),
        *refits,
    ]

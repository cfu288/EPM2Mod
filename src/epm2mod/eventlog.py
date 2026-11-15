"""Decoder of the camera's structured log file ``EPM2LOG.BIN``.

A debug build of the firmware writes binary event records to the SD card. The
records hold numbers only. The meaning of each event id (its name, its level and
the names and formats of its two arguments) is in the dictionary
``logs/events.json``, which the firmware generator also reads.

The file is a list of blocks. The firmware writes blocks of 512 bytes: a header,
at most 30 records, then zero bytes. The decoder takes a block of any length
and skips zero bytes between blocks.

====== ====== =========================================================
Offset Size   Field
====== ====== =========================================================
0      4      magic ``EPLG``
4      1      format version (1)
5      1      record size (16)
6      1      CPU number (0 or 1); each CPU has its own ring
7      1      header size (32)
8      8      build id: 8 bytes of a sha256 of the dictionary's events
16     4      number of the first record of the block
20     4      number of records in the block
24     4      records lost on this CPU since the ring was started
28     4      restarts that found the ring in RAM
====== ====== =========================================================

A record is ``u16 id, u16 sequence, u32 time, u32 arg0, u32 arg1``, little
endian. The sequence is the low 16 bits of the record's number. The time is the
raw value of a 30-bit timer that counts down once per microsecond.

:func:`decode` turns the bytes into JSON-ready objects, one per record, and adds
marker objects where records are missing. It reads a file that ends in the
middle of a block, and it gives records with an unknown id as numbers.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from .errors import LogError

MAGIC = b"EPLG"
VERSION = 1
HEADER_SIZE = 32
RECORD_SIZE = 16
TIMER_MASK = 0x3FFFFFFF
BOOT_EVENT = "boot"
SEEN_RECORDS = 1024
LEVELS = ("debug", "info", "warn", "error")
FORMATS = ("hex", "dec", "sdec", "addr")

_HEADER = struct.Struct("<4sBBBB8sIIII")
_RECORD = struct.Struct("<HHIII")


@dataclass(frozen=True)
class Field:
    """A group of bits inside an argument.

    Attributes:
        name: the key of the value in the output.
        shift: the number of the lowest bit.
        bits: the width.
        format: one of ``FORMATS``.
        enum: names for values (decimal text of the value to name); may be empty.
    """

    name: str
    shift: int
    bits: int
    format: str
    enum: dict[str, str]

    def value(self, word: int) -> Any:
        """Return the field's value from the 32-bit argument."""
        raw = (word >> self.shift) & ((1 << self.bits) - 1)
        if str(raw) in self.enum:
            return self.enum[str(raw)]
        return _show(raw, self.format, self.bits)


@dataclass(frozen=True)
class Argument:
    """One of the two arguments of an event.

    Attributes:
        name: the key of the value in the output.
        format: one of ``FORMATS``.
        fields: bit groups; when there are any, the output is an object with
            the raw value and one key per field.
    """

    name: str
    format: str
    fields: tuple[Field, ...]

    def value(self, word: int) -> Any:
        """Return the JSON-ready value of the argument."""
        shown = _show(word, self.format, 32)
        if not self.fields:
            return shown
        result: dict[str, Any] = {"raw": _show(word, "hex", 32)}
        for part in self.fields:
            result[part.name] = part.value(word)
        return result


@dataclass(frozen=True)
class Event:
    """The dictionary entry of one event id.

    Attributes:
        number: the id in the record.
        name: the event's name.
        level: one of ``LEVELS``.
        args: the arguments that the event uses, at most two.
    """

    number: int
    name: str
    level: str
    args: tuple[Argument, ...]


@dataclass(frozen=True)
class Dictionary:
    """The event dictionary.

    Attributes:
        events: the entries by event id.
        build_id: the 8 bytes that a firmware built from this dictionary writes
            into each block header.
    """

    events: dict[int, Event]
    build_id: bytes


def _show(value: int, how: str, bits: int) -> Any:
    """Return a number in the form that a format names."""
    if how == "dec":
        return value
    if how == "sdec":
        return value - (1 << bits) if value >> (bits - 1) else value
    return f"0x{value:0{(bits + 3) // 4}X}"


def build_id(events: Any) -> bytes:
    """Return the build id of an event list: 8 bytes of a SHA-256.

    The id, name, level and args of each event count; other keys (the notes)
    do not. The firmware generator computes the same value from the same list,
    so a log names the dictionary that it was written with.
    """
    kept = [
        {key: event.get(key) for key in ("id", "name", "level", "args")}
        for event in events
    ]
    text = json.dumps(kept, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).digest()[:8]


def _text(raw: Any, key: str, where: str) -> str:
    """Return a string value of a dictionary object."""
    value = raw.get(key) if isinstance(raw, dict) else None
    if not isinstance(value, str) or not value:
        raise LogError(f"{where}: {key!r} must be a text")
    return value


def _number(raw: Any, key: str, where: str, low: int, high: int) -> int:
    """Return an integer value of a dictionary object, with a range check."""
    value = raw.get(key) if isinstance(raw, dict) else None
    if not isinstance(value, int) or isinstance(value, bool):
        raise LogError(f"{where}: {key!r} must be a whole number")
    if not low <= value <= high:
        raise LogError(f"{where}: {key!r} must be from {low} to {high}")
    return value


def _format(raw: dict[str, Any], where: str, default: str) -> str:
    """Return the format of an argument or field."""
    how = raw.get("format", default)
    if how not in FORMATS:
        raise LogError(f"{where}: 'format' must be one of {', '.join(FORMATS)}")
    return str(how)


def _field(raw: Any, where: str) -> Field:
    """Return one bit group from its dictionary object."""
    name = _text(raw, "name", where)
    where = f"{where}, field {name}"
    shift = _number(raw, "shift", where, 0, 31)
    bits = _number(raw, "bits", where, 1, 32 - shift)
    enum = raw.get("enum", {})
    if not isinstance(enum, dict) or not all(
        key.isdecimal() and isinstance(value, str) for key, value in enum.items()
    ):
        raise LogError(f"{where}: 'enum' must map numbers (as text) to names")
    return Field(name, shift, bits, _format(raw, where, "dec"), dict(enum))


def _argument(raw: Any, where: str) -> Argument:
    """Return one argument from its dictionary object."""
    name = _text(raw, "name", where)
    where = f"{where}, argument {name}"
    parts = raw.get("fields", [])
    if not isinstance(parts, list):
        raise LogError(f"{where}: 'fields' must be a list")
    fields = tuple(_field(part, where) for part in parts)
    return Argument(name, _format(raw, where, "hex"), fields)


def load_dictionary(raw: Any) -> Dictionary:
    """Return the dictionary that a parsed ``logs/events.json`` describes.

    Raises:
        LogError: the object is not a dictionary of format 1, an entry is
            malformed, or an id or a name is there twice.
    """
    if not isinstance(raw, dict) or raw.get("format") != 1:
        raise LogError("the event dictionary must be an object with 'format': 1")
    if raw.get("record_size") != RECORD_SIZE:
        raise LogError(f"the event dictionary must have 'record_size': {RECORD_SIZE}")
    entries = raw.get("events")
    if not isinstance(entries, list):
        raise LogError("the event dictionary has no 'events' list")
    events: dict[int, Event] = {}
    names: set[str] = set()
    for entry in entries:
        name = _text(entry, "name", "event dictionary")
        where = f"event {name}"
        number = _number(entry, "id", where, 1, 0xFFFF)
        level = _text(entry, "level", where)
        if level not in LEVELS:
            raise LogError(f"{where}: 'level' must be one of {', '.join(LEVELS)}")
        args = entry.get("args", [])
        if not isinstance(args, list) or len(args) > 2:
            raise LogError(f"{where}: 'args' must be a list of at most 2 arguments")
        if number in events or name in names:
            raise LogError(f"{where}: the id {number} or the name is there twice")
        names.add(name)
        events[number] = Event(
            number, name, level, tuple(_argument(arg, where) for arg in args)
        )
    return Dictionary(events, build_id(entries))


@dataclass
class _Cpu:
    """What the decoder remembers about one CPU's ring.

    Attributes:
        expected: the number of the record after the last one read, if any.
        drops: the drop count of the last block.
        last_time: the time of the last record, in microseconds, if any.
        wraps: how often the 30-bit timer has wrapped since the session began.
        seen: the bytes of the newest records by number, to find a block that
            the firmware wrote a second time.
    """

    expected: int | None = None
    drops: int = 0
    last_time: int | None = None
    wraps: int = 0
    seen: dict[int, bytes] = field(default_factory=dict)


@dataclass
class _State:
    """The decoder's state across blocks.

    Attributes:
        session: the number of ``boot`` events read so far.
        cpus: the state of each CPU's ring.
        warned: the build ids that already have a mismatch marker.
    """

    session: int = 0
    cpus: dict[int, _Cpu] = field(default_factory=dict)
    warned: set[bytes] = field(default_factory=set)


def _is_header(data: bytes, offset: int) -> bool:
    """Say whether a block header of this format starts at the offset."""
    return (
        data[offset : offset + 4] == MAGIC
        and len(data) >= offset + 8
        and data[offset + 4] == VERSION
        and data[offset + 5] == RECORD_SIZE
        and data[offset + 7] == HEADER_SIZE
    )


def _next_header(data: bytes, offset: int) -> int:
    """Return the offset of the next block header at or after the offset."""
    while True:
        offset = data.find(MAGIC, offset)
        if offset < 0:
            return len(data)
        if _is_header(data, offset):
            return offset
        offset += 1


def _record(
    raw: bytes, number: int, cpu: int, build: str, state: _State, words: Dictionary
) -> dict[str, Any]:
    """Return the output object of one record and update the session state."""
    ident, sequence, timer, arg0, arg1 = _RECORD.unpack(raw)
    ring = state.cpus[cpu]
    event = words.events.get(ident)
    if event is not None and event.name == BOOT_EVENT:
        state.session += 1
        for other in state.cpus.values():
            other.last_time, other.wraps = None, 0
    now = (TIMER_MASK - timer) & TIMER_MASK
    if ring.last_time is not None and now < ring.last_time:
        ring.wraps += 1
    ring.last_time = now
    line: dict[str, Any] = {
        "seq": number,
        "cpu": cpu,
        "session": state.session,
        "time_us": now + ring.wraps * (TIMER_MASK + 1),
    }
    if sequence != number & 0xFFFF:
        line["seq_in_record"] = sequence
    if event is None:
        line.update(event=f"unknown_0x{ident:04X}", id=ident, unknown=True)
        line["args"] = {"arg0": _show(arg0, "hex", 32), "arg1": _show(arg1, "hex", 32)}
    else:
        line.update(event=event.name, level=event.level)
        values = (arg0, arg1)
        line["args"] = {
            arg.name: arg.value(values[index]) for index, arg in enumerate(event.args)
        }
    line["build"] = build
    return line


def decode(data: bytes, words: Dictionary) -> Iterator[dict[str, Any]]:
    """Yield one JSON-ready object per record of a log file, in file order.

    A record object has ``seq`` (the record's number on its CPU), ``cpu``,
    ``session`` (the count of ``boot`` events read so far; 0 before the first
    one), ``time_us`` (microseconds; it goes on across timer wraps inside a
    session), ``event``, ``level``, ``args`` and ``build``. A record whose id
    is not in the dictionary has ``unknown: true``, its ``id`` and the two raw
    arguments. Records that were still in RAM after a restart and were written
    by the next session have ``recovered: true``.

    Marker objects have a ``marker`` key:

    - ``gap``: records were overwritten in the ring before a flush (``lost``).
    - ``ring_restart``: the ring began again at record 0 (RAM was clear).
    - ``repeat``: the firmware wrote records a second time, because the file
      did not seem to keep the first write; they are given once. A block
      counts as a repeat only when all its records up to the last one read
      are the same bytes.
    - ``truncated``: a block ends before its last record (``missing``).
    - ``garbage``: bytes that are not part of a block were skipped (zero bytes
      after a block are padding and give no marker).
    - ``dictionary_mismatch``: a block was written by a firmware with another
      dictionary; its events may have the wrong names.

    Raises:
        LogError: the data has no block at all.
    """
    state = _State()
    offset = _next_header(data, 0)
    if offset >= len(data):
        raise LogError("no log block found (a block starts with 'EPLG')")
    if offset:
        yield {"marker": "garbage", "offset": 0, "bytes": offset}
    while offset < len(data):
        if len(data) - offset < HEADER_SIZE:
            yield {"marker": "truncated", "offset": offset, "missing": "block header"}
            return
        _, _, _, cpu, _, ident, first, count, drops, restarts = _HEADER.unpack_from(
            data, offset
        )
        build = ident.hex()
        if ident != words.build_id and ident not in state.warned:
            state.warned.add(ident)
            yield {
                "marker": "dictionary_mismatch",
                "build": build,
                "dictionary": words.build_id.hex(),
            }
        ring = state.cpus.setdefault(cpu, _Cpu())
        offset += HEADER_SIZE
        repeated = 0
        if ring.expected is not None and first < ring.expected:
            overlap = min(count, ring.expected - first)
            whole = data[offset : offset + RECORD_SIZE * overlap]
            if whole == b"".join(
                ring.seen.get(first + index, b"") for index in range(overlap)
            ):
                repeated = overlap
        if repeated:
            yield {"marker": "repeat", "cpu": cpu, "seq": first, "records": repeated}
            offset += RECORD_SIZE * repeated
            first += repeated
            count -= repeated
        if ring.expected is not None and first < ring.expected:
            yield {"marker": "ring_restart", "cpu": cpu, "seq": first}
            ring.drops = 0
            ring.seen.clear()
        elif ring.expected is not None and first > ring.expected:
            yield {
                "marker": "gap",
                "cpu": cpu,
                "seq": first,
                "lost": first - ring.expected,
            }
        elif drops > ring.drops and ring.expected is None:
            yield {
                "marker": "gap",
                "cpu": cpu,
                "seq": first,
                "lost": drops - ring.drops,
            }
        ring.drops = drops
        lines: list[dict[str, Any]] = []
        done = 0
        while done < count and len(data) - offset >= RECORD_SIZE:
            if _is_header(data, offset):
                break
            ring.seen[first + done] = data[offset : offset + RECORD_SIZE]
            ring.seen.pop(first + done - SEEN_RECORDS, None)
            lines.append(
                _record(
                    data[offset : offset + RECORD_SIZE],
                    first + done,
                    cpu,
                    build,
                    state,
                    words,
                )
            )
            offset += RECORD_SIZE
            done += 1
        boots = [
            index
            for index, line in enumerate(lines)
            if line["event"] == BOOT_EVENT and restarts
        ]
        for line in lines[: boots[-1] if boots else 0]:
            line["recovered"] = True
        yield from lines
        ring.expected = first + done
        if done < count:
            yield {
                "marker": "truncated",
                "cpu": cpu,
                "seq": first + done,
                "missing": count - done,
            }
            ring.expected = None
        following = _next_header(data, offset)
        between = data[offset:following]
        if any(between) and not (done < count and following == len(data)):
            yield {"marker": "garbage", "offset": offset, "bytes": len(between)}
        offset = following

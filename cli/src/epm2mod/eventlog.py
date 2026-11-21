"""Decoder of the camera's structured log file ``EPM2LOG.BIN``.

A debug build of the firmware writes binary event records to the SD card. The
records hold numbers only. The meaning of each event id (its name, its level and
the names and formats of its two arguments) is in the project's event
dictionary (``RepoPaths.events``), which the firmware generator also reads.

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

The dictionary can also hold *name tables* (``tables``: value to text) and say
which argument or field of an event uses which table (``names`` of an event).
These and the ``doc`` texts are notes for the reader: they are not part of the
build id, so they can be corrected for a firmware that is already on a camera.
A change of an id, a name, a level or an argument gives a new build id. The
dictionary of a flashed build is then kept beside the current one, as a file
named by its build id, and :func:`decode` takes it for the blocks that carry its build id.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from .errors import LogError

MAGIC = b"EPLG"
VERSION = 1
HEADER_SIZE = 32
RECORD_SIZE = 16
TIMER_MASK = 0x3FFFFFFF
BOOT_EVENT = "boot"
FLUSH_EVENT = "flush"
SEEN_RECORDS = 1024
BLOCK_RECORDS = 30
EARLY_US = 1_000_000
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
        names: the name table of an argument (key ``arg``) or of a field (key
            ``arg.field``); may be empty.
    """

    number: int
    name: str
    level: str
    args: tuple[Argument, ...]
    names: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Table:
    """Names for the values of an argument or a field.

    Attributes:
        exact: the name of a value.
        groups: the name of every value with the same bits above the low 8
            (the key is the value shifted right by 8); used when ``exact`` has
            no entry.
    """

    exact: dict[int, str]
    groups: dict[int, str]

    def name(self, value: int) -> str | None:
        """Return the name of a value, or ``None``."""
        found = self.exact.get(value)
        return found if found is not None else self.groups.get(value >> 8)


@dataclass(frozen=True)
class Dictionary:
    """The event dictionary.

    Attributes:
        events: the entries by event id.
        build_id: the 8 bytes that a firmware built from this dictionary writes
            into each block header.
        tables: the name tables by name.
    """

    events: dict[int, Event]
    build_id: bytes
    tables: dict[str, Table] = field(default_factory=dict)


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


def _table(raw: Any, where: str) -> Table:
    """Return one name table from its dictionary object.

    A key is a number as text: decimal (``"259"``), hexadecimal (``"0x5B00"``)
    or hexadecimal with ``xx`` for the low byte (``"0x5Bxx"``: every value of
    that group that has no entry of its own).
    """
    if not isinstance(raw, dict):
        raise LogError(f"{where}: a table must be an object")
    exact: dict[int, str] = {}
    groups: dict[int, str] = {}
    for key, text in raw.items():
        group = key.lower().startswith("0x") and key.lower().endswith("xx")
        digits = key[:-2] if group else key
        try:
            value = int(digits, 0)
        except ValueError:
            value = -1
        if value < 0 or not isinstance(text, str) or not text:
            raise LogError(f"{where}: {key!r} must be a number with a name")
        (groups if group else exact)[value] = text
    return Table(exact, groups)


def _names(entry: Any, args: tuple[Argument, ...], where: str) -> dict[str, str]:
    """Return the ``names`` of an event: argument or field to table name."""
    raw = entry.get("names", {})
    if not isinstance(raw, dict) or not all(isinstance(v, str) for v in raw.values()):
        raise LogError(f"{where}: 'names' must map arguments to table names")
    known = {arg.name for arg in args} | {
        f"{arg.name}.{part.name}" for arg in args for part in arg.fields
    }
    for key in raw:
        if key not in known:
            raise LogError(f"{where}: 'names' has {key!r}, which is no argument")
    return dict(raw)


def load_dictionary(raw: Any, inherit: Dictionary | None = None) -> Dictionary:
    """Return the dictionary that a parsed event dictionary describes.

    Args:
        raw: the parsed JSON object.
        inherit: a dictionary whose name tables are taken when ``raw`` has no
            ``tables`` of its own (the dictionary of an older build is kept as
            its event list only).

    Raises:
        LogError: the object is not a dictionary of format 1, an entry is
            malformed, an id or a name is there twice, or an event names a
            table that does not exist.
    """
    if not isinstance(raw, dict) or raw.get("format") != 1:
        raise LogError("the event dictionary must be an object with 'format': 1")
    if raw.get("record_size") != RECORD_SIZE:
        raise LogError(f"the event dictionary must have 'record_size': {RECORD_SIZE}")
    entries = raw.get("events")
    if not isinstance(entries, list):
        raise LogError("the event dictionary has no 'events' list")
    tables: dict[str, Table] = dict(inherit.tables) if inherit else {}
    if "tables" in raw:
        if not isinstance(raw["tables"], dict):
            raise LogError("the event dictionary: 'tables' must be an object")
        tables = {
            name: _table(body, f"table {name}") for name, body in raw["tables"].items()
        }
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
        parsed = tuple(_argument(arg, where) for arg in args)
        named = _names(entry, parsed, where)
        for key, table in named.items():
            if table not in tables:
                raise LogError(f"{where}: {key!r} names the table {table!r}: not there")
        events[number] = Event(number, name, level, parsed, tuple(named.items()))
    return Dictionary(events, build_id(entries), tables)


@dataclass
class _Ring:
    """What the reader remembers about one CPU's ring.

    Attributes:
        expected: the number of the record after the last one read, if any.
        drops: the drop count of the last block.
        seen: the bytes of the newest records by number, to find a block that
            the firmware wrote a second time.
        generation: how often the ring began again at record 0.
    """

    expected: int | None = None
    drops: int = 0
    seen: dict[int, bytes] = field(default_factory=dict)
    generation: int = 0


@dataclass
class _Entry:
    """One record between the reading pass and the output.

    Attributes:
        cpu: the CPU of the ring.
        number: the record's number on its CPU.
        ident: the event id.
        sequence: the 16-bit sequence number in the record.
        now: the time in microseconds, 30 bits (the timer value turned round).
        arg0: the first argument.
        arg1: the second argument.
        build: the build id of the block, as hexadecimal text.
        words: the dictionary of the block.
        generation: the ring's generation (see ``_Ring``).
        run: the number of the write run. A flush writes the new records of
            one CPU as blocks that follow each other, all full but the last.
        session: the session number, set by ``_sessions``.
        recovered: the record was written by the session after its own.
        time_us: the time with the timer wraps of its session added.
    """

    cpu: int
    number: int
    ident: int
    sequence: int
    now: int
    arg0: int
    arg1: int
    build: str
    words: Dictionary
    generation: int
    run: int
    session: int = 0
    recovered: bool = False
    time_us: int = 0

    def named(self, name: str) -> bool:
        """Say whether the record's event has this name in its dictionary."""
        event = self.words.events.get(self.ident)
        return event is not None and event.name == name


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


def _read(
    data: bytes, words: Dictionary, others: Mapping[bytes, Dictionary]
) -> list[_Entry | dict[str, Any]]:
    """Return the records and the markers of a log file, in file order.

    This pass reads the blocks. It finds repeats, gaps, ring restarts, cut
    blocks and bytes that belong to no block. It does not know sessions.
    """
    items: list[_Entry | dict[str, Any]] = []
    rings: dict[int, _Ring] = {}
    warned: set[bytes] = set()
    run = 0
    joins: tuple[int, int] | None = None  # (cpu, next number) of a full block
    offset = _next_header(data, 0)
    if offset >= len(data):
        raise LogError("no log block found (a block starts with 'EPLG')")
    if offset:
        items.append({"marker": "garbage", "offset": 0, "bytes": offset})
    while offset < len(data):
        if len(data) - offset < HEADER_SIZE:
            items.append(
                {"marker": "truncated", "offset": offset, "missing": "block header"}
            )
            break
        _, _, _, cpu, _, ident, first, count, drops, _ = _HEADER.unpack_from(
            data, offset
        )
        build = ident.hex()
        chosen = words if ident == words.build_id else others.get(ident)
        if chosen is None:
            chosen = words
            if ident not in warned:
                warned.add(ident)
                items.append(
                    {
                        "marker": "dictionary_mismatch",
                        "build": build,
                        "dictionary": words.build_id.hex(),
                    }
                )
        ring = rings.setdefault(cpu, _Ring())
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
            items.append(
                {"marker": "repeat", "cpu": cpu, "seq": first, "records": repeated}
            )
            offset += RECORD_SIZE * repeated
            first += repeated
            count -= repeated
        if ring.expected is not None and first < ring.expected:
            items.append({"marker": "ring_restart", "cpu": cpu, "seq": first})
            ring.drops = 0
            ring.seen.clear()
            ring.generation += 1
        elif ring.expected is not None and first > ring.expected:
            items.append(
                {
                    "marker": "gap",
                    "cpu": cpu,
                    "seq": first,
                    "lost": first - ring.expected,
                }
            )
        elif drops > ring.drops and ring.expected is None:
            items.append(
                {"marker": "gap", "cpu": cpu, "seq": first, "lost": drops - ring.drops}
            )
        ring.drops = drops
        if joins != (cpu, first):
            run += 1
        known = ident == words.build_id or ident in others
        damaged = 0
        done = 0
        while done < count and len(data) - offset >= RECORD_SIZE:
            if _is_header(data, offset):
                break
            raw = data[offset : offset + RECORD_SIZE]
            ring.seen[first + done] = raw
            ring.seen.pop(first + done - SEEN_RECORDS, None)
            event, sequence, timer, arg0, arg1 = _RECORD.unpack(raw)
            # The firmware writes the low 16 bits of the record's number and only ids
            # of its own dictionary: anything else is a stale or changed slot.
            if sequence != (first + done) & 0xFFFF or (
                known and event not in chosen.events
            ):
                if not damaged:
                    mark: dict[str, Any] = {
                        "marker": "damaged",
                        "cpu": cpu,
                        "seq": first + done,
                    }
                    items.append(mark)
                damaged += 1
                mark["records"] = damaged
                offset += RECORD_SIZE
                done += 1
                continue
            items.append(
                _Entry(
                    cpu,
                    first + done,
                    event,
                    sequence,
                    (TIMER_MASK - timer) & TIMER_MASK,
                    arg0,
                    arg1,
                    build,
                    chosen,
                    ring.generation,
                    run,
                )
            )
            offset += RECORD_SIZE
            done += 1
        ring.expected = first + done
        joins = (cpu, first + done) if done == count >= BLOCK_RECORDS else None
        if done < count:
            items.append(
                {
                    "marker": "truncated",
                    "cpu": cpu,
                    "seq": first + done,
                    "missing": count - done,
                }
            )
            ring.expected = None
        following = _next_header(data, offset)
        between = data[offset:following]
        if any(between) and not (done < count and following == len(data)):
            items.append({"marker": "garbage", "offset": offset, "bytes": len(between)})
        offset = following
    return items


def _session_starts(ring: list[_Entry]) -> list[int]:
    """Return the indexes in the CPU 0 records at which a session starts.

    A session starts at its ``boot`` record, or at the records that the same
    start put before it: the firmware's error recorder can run before the boot
    task. Such a record is next to the ``boot`` record in the same ring, its
    time is not later, and it is at most ``EARLY_US`` before the ``boot``
    record. A record of the session before has a later time, because the
    timer begins again at a start.
    """
    starts: list[int] = []
    for index, entry in enumerate(ring):
        if not entry.named(BOOT_EVENT):
            continue
        first = index
        floor = starts[-1] if starts else -1
        while first - 1 > floor:
            before, after = ring[first - 1], ring[first]
            if (
                before.generation != entry.generation
                or before.number != after.number - 1
                or before.named(BOOT_EVENT)
                or before.now > after.now
                or entry.now - before.now > EARLY_US
            ):
                break
            first -= 1
        starts.append(first)
    return starts


def _recover_other(run: list[_Entry], before: _Entry, session: int) -> None:
    """Mark the old records in the first write run of a CPU other than CPU 0.

    The session that wrote the run kept the ring of the session before. The
    old records are the ones before the last point at which the time goes
    back. Without such a point nothing is marked.
    """
    split = 0
    for index, entry in enumerate(run):
        earlier = run[index - 1] if index else before
        if entry.now < earlier.now:
            split = index
    for entry in run[:split]:
        entry.session = session - 1
        entry.recovered = True


def _sessions(items: list[_Entry | dict[str, Any]]) -> None:
    """Set the session, the recovered mark and the time of every record.

    The sessions are counted on CPU 0, which has the ``boot`` records. A
    record of CPU 0 is recovered when it is from the session before and the
    new session wrote it: it is in the write run of the session's start, and
    it is later than the last ``flush`` record of its own session. A record of
    another CPU counts for the session that wrote it, but see
    ``_recover_other``.
    """
    entries = [item for item in items if isinstance(item, _Entry)]
    ring0 = [entry for entry in entries if entry.cpu == 0]
    starts = _session_starts(ring0)
    kept: dict[int, int] = {}  # id of a start record -> its session, ring kept
    session = 0
    for index, entry in enumerate(ring0):
        if session < len(starts) and starts[session] == index:
            session += 1
            if index and ring0[index - 1].generation == entry.generation:
                kept[id(entry)] = session
                for old in reversed(ring0[:index]):
                    if (
                        old.run != entry.run
                        or old.session != session - 1
                        or old.named(FLUSH_EVENT)
                    ):
                        break
                    old.recovered = True
        entry.session = session
    current = 0
    last: dict[int, _Entry] = {}
    pending: dict[int, int] = {}  # CPU -> session whose first run is to come
    runs: list[tuple[int, list[_Entry], _Entry]] = []
    open_runs: dict[int, list[_Entry]] = {}
    for entry in entries:
        if entry.cpu == 0:
            current = max(current, entry.session)
            if id(entry) in kept:
                pending = {cpu: kept[id(entry)] for cpu in last if cpu}
            continue
        entry.session = current
        before = last.get(entry.cpu)
        last[entry.cpu] = entry
        if entry.cpu in pending:
            open_runs.pop(entry.cpu, None)
            if before is not None and before.generation == entry.generation:
                open_runs[entry.cpu] = [entry]
                runs.append((pending[entry.cpu], open_runs[entry.cpu], before))
            del pending[entry.cpu]
        elif entry.cpu in open_runs and open_runs[entry.cpu][0].run == entry.run:
            open_runs[entry.cpu].append(entry)
    for number, run, before in runs:
        _recover_other(run, before, number)
    clocks: dict[int, tuple[int, int, int, int]] = {}
    for entry in entries:
        key = (entry.session, entry.generation)
        session, generation, last_now, wraps = clocks.get(entry.cpu, (*key, 0, 0))
        if (session, generation) != key:
            last_now, wraps = 0, 0
        if entry.now < last_now:
            wraps += 1
        clocks[entry.cpu] = (*key, entry.now, wraps)
        entry.time_us = entry.now + wraps * (TIMER_MASK + 1)


def _names_of(
    event: Event, values: tuple[int, int], words: Dictionary
) -> dict[str, str]:
    """Return the names that the tables give for an event's values."""
    found: dict[str, str] = {}
    for key, table in event.names:
        head, _, tail = key.partition(".")
        for index, arg in enumerate(event.args):
            if arg.name != head:
                continue
            value = values[index]
            for part in arg.fields:
                if part.name == tail:
                    value = (value >> part.shift) & ((1 << part.bits) - 1)
            name = words.tables[table].name(value)
            if name is not None:
                found[key] = name
    return found


def _line(entry: _Entry) -> dict[str, Any]:
    """Return the output object of one record."""
    line: dict[str, Any] = {
        "seq": entry.number,
        "cpu": entry.cpu,
        "session": entry.session,
        "time_us": entry.time_us,
    }
    event = entry.words.events.get(entry.ident)
    values = (entry.arg0, entry.arg1)
    if event is None:
        line.update(event=f"unknown_0x{entry.ident:04X}", id=entry.ident, unknown=True)
        line["args"] = {
            name: _show(value, "hex", 32)
            for name, value in zip(("arg0", "arg1"), values)
        }
    else:
        line.update(event=event.name, level=event.level)
        line["args"] = {
            arg.name: arg.value(values[index]) for index, arg in enumerate(event.args)
        }
        names = _names_of(event, values, entry.words)
        if names:
            line["names"] = names
    line["build"] = entry.build
    if entry.recovered:
        line["recovered"] = True
    return line


def decode(
    data: bytes, words: Dictionary, others: Mapping[bytes, Dictionary] | None = None
) -> Iterator[dict[str, Any]]:
    """Yield one JSON-ready object per record of a log file, in file order.

    A record object has ``seq`` (the record's number on its CPU), ``cpu``,
    ``session``, ``time_us`` (microseconds since the start; it goes on across
    timer wraps inside a session), ``event``, ``level``, ``args`` and
    ``build``. ``names`` is there when a name table of the dictionary has a
    name for a value: its keys are ``arg`` or ``arg.field``. A record of a
    block whose dictionary is not given, with an id that is not in ``words``,
    has ``unknown: true``, its ``id`` and the two raw arguments.

    ``session`` counts the starts of the camera in the file, from 1. A session
    begins at its ``boot`` record, or at the records that the same start put
    before it (errors that the firmware records before the boot task runs).
    Records before the first start have session 0. Records that were still in
    RAM after a restart and were written by the next session have their own
    session's number and ``recovered: true``: they are the last events before
    a crash.

    Marker objects have a ``marker`` key:

    - ``gap``: records were overwritten in the ring before a flush (``lost``).
    - ``ring_restart``: the ring began again at record 0 (RAM was clear).
    - ``repeat``: the firmware wrote records a second time, because the file
      did not seem to keep the first write; they are given once. A block
      counts as a repeat only when all its records up to the last one read
      are the same bytes.
    - ``truncated``: a block ends before its last record (``missing``).
    - ``damaged``: records that cannot be real were dropped (``records``): the
      sequence number in the record is not its place in the block, or the id
      is not in the dictionary of the block's build. A slot of the ring that
      was stale or changed in RAM gives them.
    - ``garbage``: bytes that are not part of a block were skipped (zero bytes
      after a block are padding and give no marker).
    - ``dictionary_mismatch``: a block was written by a firmware with a
      dictionary that is not given; its events may have the wrong names.

    Args:
        data: the bytes of the file.
        words: the dictionary of the repository.
        others: dictionaries of other builds by build id. A block is decoded
            with the dictionary that has its build id.

    Raises:
        LogError: the data has no block at all.
    """
    items = _read(data, words, others or {})
    _sessions(items)
    for item in items:
        yield _line(item) if isinstance(item, _Entry) else item

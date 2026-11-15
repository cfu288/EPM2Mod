"""A short report on a decoded camera log (``epm2mod log FILE --summary``).

:func:`summarize` takes the objects that :func:`epm2mod.eventlog.decode` yields
and returns lines of text: the sessions, the markers, the firmware's error
records, the flushes, the count of each event, and one line per feature of the
mod (peaking, film looks, shooting, interval shooting, level gauge).

The feature lines read events by their names in the repository's dictionary
``logs/events.json``. A file that does not have an event gives no line for it.
The report states what the records say. It does not judge them: the reader
compares the numbers with what was done on the camera.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Iterable
from typing import Any

Line = dict[str, Any]

_NO_ART = 3
_CBS_SEQUENCE = 259
_CBS_SEQUENCE_END = 260
_CBS_FRAME_TIMER = 261
_CBS_CAPTURE = 136
_CBS_HALF_PRESS = 210


def _seconds(line: Line) -> float:
    """Return the time of a record in seconds."""
    return float(line["time_us"]) / 1e6


def _count(count: int, word: str) -> str:
    """Return a count with its noun, with ``s`` for a count that is not 1."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _named(line: Line, key: str) -> str:
    """Return the value of an argument or field with its name, if it has one."""
    head, _, tail = key.partition(".")
    value = line["args"].get(head)
    if tail and isinstance(value, dict):
        value = value.get(tail)
    name = line.get("names", {}).get(key)
    return f"{name} [{value}]" if name else str(value)


def _tally(lines: list[Line], key: str) -> str:
    """Return ``name n, name n`` for the values of one argument, most first."""
    counts = Counter(_named(line, key) for line in lines)
    return ", ".join(f"{name}: {count}" for name, count in counts.most_common())


def _raw(line: Line, key: str) -> int:
    """Return the number in an argument that the decoder gave as text or int."""
    value = line["args"].get(key)
    if isinstance(value, dict):
        value = value.get("raw")
    return int(value, 16) if isinstance(value, str) else int(value)


def _sessions(records: list[Line]) -> list[str]:
    """Return one line per session."""
    out: list[str] = []
    for number in sorted({line["session"] for line in records}):
        mine = [line for line in records if line["session"] == number]
        cpus = Counter(line["cpu"] for line in mine)
        split = ", ".join(f"CPU {cpu}: {cpus[cpu]}" for cpu in sorted(cpus))
        text = f"session {number}: {max(map(_seconds, mine)):.1f} s, "
        text += f"{_count(len(mine), 'record')} ({split})"
        ring0 = [line for line in mine if line["cpu"] == 0]
        boots = [line for line in ring0 if line["event"] == "boot"]
        if number == 0 or not boots:
            out.append(text + "; no boot record")
            continue
        first = min(ring0, key=lambda line: int(line["seq"]))
        text += "; cold start (new ring)" if first["seq"] == 0 else "; RAM was kept"
        early = sum(1 for line in ring0 if line["seq"] < boots[0]["seq"])
        early -= sum(1 for line in ring0 if line.get("recovered"))
        if early > 0:
            text += f"; {_count(early, 'record')} before boot"
        recovered = sum(1 for line in mine if line.get("recovered"))
        if recovered:
            text += f"; {_count(recovered, 'record')} written by the next session"
        last = max(
            (line for line in ring0 if not line.get("recovered")),
            key=lambda line: int(line["seq"]),
        )
        off = last["event"] == "flush" and _raw(last, "gui_state") >> 12 == 2
        text += "; ends with the flush at power off" if off else "; no flush at the end"
        out.append(text)
    return out


def _markers(lines: list[Line]) -> list[str]:
    """Return the lines about markers: lost records and other notes."""
    marks = [line for line in lines if "marker" in line]
    lost = sum(int(line["lost"]) for line in marks if line["marker"] == "gap")
    gaps = sum(1 for line in marks if line["marker"] == "gap")
    out = [f"gaps: {gaps} ({_count(lost, 'record')} lost)" if gaps else "gaps: none"]
    other = Counter(line["marker"] for line in marks if line["marker"] != "gap")
    if other:
        out.append(
            "markers: " + ", ".join(f"{name} {other[name]}" for name in sorted(other))
        )
    return out


def _errors(records: list[Line]) -> list[str]:
    """Return the lines about the firmware's own error records."""
    errors = [line for line in records if line["event"] == "fw_error"]
    if not errors:
        return ["firmware errors: none"]
    out = [f"firmware errors: {len(errors)}"]
    groups: dict[tuple[str, str], list[Line]] = {}
    for line in errors:
        key = (_named(line, "code"), str(line["args"].get("caller")))
        groups.setdefault(key, []).append(line)
    for (code, caller), group in groups.items():
        times = [_seconds(line) for line in group]
        sessions = sorted({line["session"] for line in group})
        out.append(
            f"  {len(group)} x {code}, caller {caller}, "
            f"at {min(times):.3f} to {max(times):.3f} s, "
            f"sessions {', '.join(map(str, sessions))}"
        )
    return out


def _flushes(records: list[Line]) -> list[str]:
    """Return the lines about the flushes.

    A ``flush`` record holds the result of the flush before it. So the last
    flush of a session has no result in the file.
    """
    flushes = [line for line in records if line["event"] == "flush"]
    if not flushes:
        return ["flushes: none"]
    results: Counter[str] = Counter()
    for before, line in zip(flushes, flushes[1:]):
        if before["session"] == line["session"]:
            results[str(line["args"].get("previous", {}).get("result"))] += 1
    result = ", ".join(f"{name} {results[name]}" for name in sorted(results))
    text = f"flushes: {len(flushes)}; results reported by the next flush: "
    return [text + (result or "none"), "  started by: " + _tally(flushes, "gui_state")]


def _peaking(records: list[Line]) -> list[str]:
    """Return the lines about focus peaking."""
    starts = [line for line in records if line["event"] == "pk_mf_start"]
    latches = [line for line in records if line["event"] == "pk_latch"]
    if not starts and not latches:
        return []
    lengths = []
    for start in starts:
        ends = [
            _seconds(line)
            for line in records
            if line["event"] == "pk_mf_end"
            and line["session"] == start["session"]
            and line["time_us"] > start["time_us"]
        ]
        lengths.append(f"{min(ends) - _seconds(start):.1f} s" if ends else "no end")
    on = [line for line in latches if line["args"]["latch"].get("L") == 1]
    colours = list(dict.fromkeys(_named(line, "latch.C") for line in on))
    out = [
        f"peaking: {_count(len(starts), 'MF Assist run')} ({', '.join(lengths)}); "
        f"colour when the latch is set: {', '.join(colours) or 'never set'}"
    ]
    periods: list[float] = []
    for index, line in enumerate(latches):
        if line["args"]["latch"].get("L") != 1:
            continue
        later = [
            other
            for other in latches[index + 1 :]
            if other["session"] == line["session"]
        ]
        if index and latches[index - 1]["args"]["latch"].get("L") == 1:
            continue
        stop = next(
            (o["time_us"] for o in later if o["args"]["latch"].get("L") == 0), None
        )
        frames = [
            _seconds(other)
            for other in records
            if other["event"] == "film_stage"
            and other["session"] == line["session"]
            and other["args"].get("art") == _NO_ART
            and other["time_us"] > line["time_us"]
            and (stop is None or other["time_us"] < stop)
            and _raw(other, "flags") == 0
        ]
        periods += [b - a for a, b in zip(frames, frames[1:])]
    if periods:
        middle = statistics.median(periods)
        out.append(
            f"  live view while the lines show: {len(periods)} frame periods, "
            f"{min(periods) * 1000:.0f} to {max(periods) * 1000:.0f} ms, "
            f"median {middle * 1000:.0f} ms ({1 / middle:.1f} frames per second)"
        )
    passes = [line for line in records if line["event"] == "pk_pass9"]
    if passes:
        gains = sorted({line["args"]["line"].get("gain") for line in passes})
        out.append(
            f"  colour pass: {len(passes)} records, gain "
            f"{', '.join(map(str, gains))}"
        )
    return out


def _looks(records: list[Line]) -> list[str]:
    """Return the lines about the film looks and art codes."""
    stages = [
        line
        for line in records
        if line["event"] == "film_stage" and line["args"].get("art") != _NO_ART
    ]
    if not stages:
        return []
    out = ["looks in the colour stage (film_stage records): " + _tally(stages, "art")]
    tables = [line for line in records if line["event"] == "film_matrix"]
    if tables:
        out.append("  matrix tables: " + _tally(tables, "table"))
    return out


def _shooting(records: list[Line]) -> list[str]:
    """Return the line about the shooting callbacks."""
    calls = [line for line in records if line["event"] == "shoot_cbs"]
    if not calls:
        return []
    numbers = Counter(line["args"].get("cbs") for line in calls)
    return [
        f"shooting: {_count(numbers[_CBS_CAPTURE], 'capture')} "
        f"(callback {_CBS_CAPTURE}), {_count(numbers[_CBS_HALF_PRESS], 'time')} "
        f"CBS_START_SHOOTING_PICTURE (callback {_CBS_HALF_PRESS}: the shutter "
        f"button goes down), {_count(len(calls), 'callback')} in all"
    ]


def _interval(records: list[Line]) -> list[str]:
    """Return the lines about interval shooting."""
    arms = sum(1 for line in records if line["event"] == "iv_start")
    calls = [line for line in records if line["event"] == "shoot_cbs"]
    begins = [line for line in calls if line["args"].get("cbs") == _CBS_SEQUENCE]
    if not arms and not begins:
        return []
    out = [
        f"interval: armed {_count(arms, 'time')} (iv_start), "
        f"{_count(len(begins), 'sequence')} (callback {_CBS_SEQUENCE})"
    ]
    for begin in begins:
        after = [
            line
            for line in calls
            if line["session"] == begin["session"]
            and line["time_us"] > begin["time_us"]
        ]
        end = next(
            (
                line["time_us"]
                for line in after
                if line["args"].get("cbs") in (_CBS_SEQUENCE, _CBS_SEQUENCE_END)
            ),
            None,
        )
        timers = [
            _seconds(line)
            for line in after
            if line["args"].get("cbs") == _CBS_FRAME_TIMER
            and (end is None or line["time_us"] < end)
        ]
        gaps = ", ".join(f"{b - a:.2f}" for a, b in zip(timers, timers[1:]))
        logged = sum(
            1
            for line in records
            if line["event"] == "iv_frame"
            and line["session"] == begin["session"]
            and line["time_us"] > begin["time_us"]
            and (end is None or line["time_us"] < end)
        )
        text = f"  sequence at {_seconds(begin):.1f} s: {_count(len(timers), 'frame')}"
        text += f" (timer callbacks {_CBS_FRAME_TIMER})"
        if gaps:
            text += f", {gaps} s between them"
        text += f"; {_count(logged, 'iv_frame record')}"
        text += "" if end is not None else "; no end callback"
        out.append(text)
    return out


def _level(records: list[Line]) -> list[str]:
    """Return the lines about the level gauge."""
    out: list[str] = []
    for line in records:
        where = f"session {line['session']}, {_seconds(line):.1f} s"
        if line["event"] == "lv_adjust":
            out.append(f"level gauge: {_named(line, 'mode')} at {where}")
        if line["event"] == "lv_values":
            x, y = line["args"]["xy"].get("x", 0), line["args"]["xy"].get("y", 0)
            z = line["args"]["zt"].get("z", 0)
            size = (x * x + y * y + z * z) ** 0.5
            out.append(
                f"level gauge: working set x {x}, y {y}, z {z} "
                f"(length {size:.0f}; 1000 = 1 g) at {where}"
            )
    return out


def summarize(lines: Iterable[Line]) -> list[str]:
    """Return a short report on a decoded log, one text per line.

    Args:
        lines: the objects that :func:`epm2mod.eventlog.decode` yields for one
            file: records and markers.
    """
    every = list(lines)
    records = [line for line in every if "marker" not in line]
    builds = sorted({str(line["build"]) for line in records})
    sessions = {line["session"] for line in records} - {0}
    out = [
        f"{_count(len(records), 'record')}, {_count(len(sessions), 'session')}, "
        f"build id {', '.join(builds) or 'none'}"
    ]
    out += _sessions(records) + _markers(every) + _errors(records)
    out += _flushes(records)
    events = Counter(str(line["event"]) for line in records)
    out.append(
        "events: "
        + ", ".join(f"{name} {count}" for name, count in events.most_common())
    )
    screens = [line for line in records if line["event"] == "gui_state"]
    if screens:
        out.append("screens entered: " + _tally(screens, "state"))
    for part in (_peaking, _looks, _shooting, _interval, _level):
        out += part(records)
    return out

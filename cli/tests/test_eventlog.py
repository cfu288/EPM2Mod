"""Tests of the camera-log decoder (``epm2mod.eventlog`` and ``epm2mod log``).

    uv run python -m unittest discover -s cli/tests

The log files are made here, byte by byte, as the firmware's flush task writes
them. ``SessionTests`` has the patterns of the first log from a camera
(``experiments/2026-11-15-log/evaluation-1.md``). The last tests read the
repository's own dictionaries in ``data/logdict/``.
"""

from __future__ import annotations

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import ROOT  # noqa: E402

from epm2mod import cli, eventlog, logsummary  # noqa: E402
from epm2mod.errors import LogError  # noqa: E402

RAW: dict[str, Any] = {
    "format": 1,
    "record_size": 16,
    "events": [
        {
            "id": 1,
            "name": "boot",
            "level": "info",
            "args": [{"name": "session", "format": "dec"}, {"name": "why"}],
        },
        {
            "id": 2,
            "name": "mode",
            "level": "warn",
            "args": [
                {
                    "name": "bits",
                    "fields": [
                        {"name": "low", "shift": 0, "bits": 8},
                        {"name": "temp", "shift": 8, "bits": 16, "format": "sdec"},
                        {"name": "kind", "shift": 24, "bits": 8, "enum": {"2": "two"}},
                    ],
                },
                {"name": "where", "format": "addr"},
            ],
        },
        {"id": 3, "name": "tick", "level": "debug", "args": []},
    ],
}
WORDS = eventlog.load_dictionary(RAW)
TOP = eventlog.TIMER_MASK

# A dictionary with the events of the camera's start-up pattern and name tables.
CAMERA: dict[str, Any] = {
    "format": 1,
    "record_size": 16,
    "tables": {
        "screen": {"0x5100": "live view", "0x57xx": "menu", "0x5705": "live control"},
        "art": {"3": "no art filter", "167": "Diorama entry", "70": "Pop Art I"},
        "colour": {"2": "Red"},
    },
    "events": [
        {
            "id": 1,
            "name": "boot",
            "level": "info",
            "args": [{"name": "ring_found", "format": "dec"}],
        },
        {
            "id": 2,
            "name": "flush",
            "level": "debug",
            "names": {"gui_state": "screen"},
            "args": [{"name": "gui_state"}],
        },
        {"id": 3, "name": "fw_error", "level": "error", "args": [{"name": "code"}]},
        {
            "id": 5,
            "name": "gui_state",
            "level": "info",
            "names": {"state": "screen", "previous": "screen"},
            "args": [{"name": "state"}, {"name": "previous"}],
        },
        {
            "id": 6,
            "name": "stage",
            "level": "info",
            "names": {"art": "art", "latch.C": "colour"},
            "args": [
                {"name": "art", "format": "dec"},
                {
                    "name": "latch",
                    "fields": [
                        {"name": "L", "shift": 0, "bits": 8},
                        {"name": "C", "shift": 24, "bits": 8},
                    ],
                },
            ],
        },
    ],
}
CAMERA_WORDS = eventlog.load_dictionary(CAMERA)
CAMERA_ID = CAMERA_WORDS.build_id


def record(
    ident: int, number: int, time_us: int, arg0: int = 0, arg1: int = 0
) -> bytes:
    """Return one record as the firmware writes it (the timer counts down)."""
    timer = (TOP - time_us) & TOP
    return struct.pack("<HHIII", ident, number & 0xFFFF, timer, arg0, arg1)


def block(
    first: int,
    records: list[bytes],
    cpu: int = 0,
    drops: int = 0,
    restarts: int = 0,
    count: int | None = None,
    build: bytes | None = None,
) -> bytes:
    """Return one flush block: the header and the records."""
    header = struct.pack(
        "<4sBBBB8sIIII",
        b"EPLG",
        1,
        16,
        cpu,
        32,
        WORDS.build_id if build is None else build,
        first,
        len(records) if count is None else count,
        drops,
        restarts,
    )
    return header + b"".join(records)


def lines(data: bytes) -> list[dict[str, Any]]:
    """Return everything that the decoder yields for a file."""
    return list(eventlog.decode(data, WORDS))


def camera_lines(data: bytes) -> list[dict[str, Any]]:
    """Return what the decoder yields with the dictionary ``CAMERA``."""
    return list(eventlog.decode(data, CAMERA_WORDS))


def records(got: list[dict[str, Any]], cpu: int = 0) -> list[dict[str, Any]]:
    """Return the records of one CPU, without the markers."""
    return [line for line in got if "marker" not in line and line["cpu"] == cpu]


class DictionaryTests(unittest.TestCase):
    def test_the_build_id_names_the_event_list(self) -> None:
        self.assertEqual(len(WORDS.build_id), 8)
        self.assertEqual(WORDS.build_id, eventlog.build_id(RAW["events"]))
        other = json.loads(json.dumps(RAW))
        other["events"][2]["name"] = "tock"
        self.assertNotEqual(eventlog.load_dictionary(other).build_id, WORDS.build_id)
        other = json.loads(json.dumps(RAW))
        other["events"][2]["args"] = [{"name": "n", "format": "dec"}]
        self.assertNotEqual(eventlog.load_dictionary(other).build_id, WORDS.build_id)
        other = json.loads(json.dumps(RAW))
        other["note"] = "text outside the event list does not count"
        other["events"][2]["doc"] = "and a note of an event does not count"
        self.assertEqual(eventlog.load_dictionary(other).build_id, WORDS.build_id)

    def test_refusals(self) -> None:
        def changed(**keys: Any) -> dict[str, Any]:
            raw: dict[str, Any] = json.loads(json.dumps(RAW))
            raw.update(keys)
            return raw

        def event(**keys: Any) -> dict[str, Any]:
            entry = dict({"id": 9, "name": "x", "level": "info", "args": []}, **keys)
            return changed(events=[entry])

        cases = [
            ([], "'format': 1"),
            (changed(format=2), "'format': 1"),
            (changed(record_size=12), "'record_size': 16"),
            (changed(events=None), "no 'events' list"),
            (event(name=""), "'name' must be a text"),
            (event(id=0), "from 1 to 65535"),
            (event(id="1"), "must be a whole number"),
            (event(level="loud"), "'level' must be one of"),
            (event(args=[{"name": "a"}] * 3), "at most 2 arguments"),
            (event(args=[{"name": "a", "format": "oct"}]), "'format' must be one of"),
            (event(args=[{"name": "a", "fields": 1}]), "'fields' must be a list"),
            (
                event(
                    args=[
                        {"name": "a", "fields": [{"name": "f", "shift": 30, "bits": 4}]}
                    ]
                ),
                "'bits' must be from 1 to 2",
            ),
            (
                event(
                    args=[
                        {
                            "name": "a",
                            "fields": [
                                {"name": "f", "shift": 0, "bits": 4, "enum": {"x": "y"}}
                            ],
                        }
                    ]
                ),
                "'enum' must map numbers",
            ),
            (changed(events=RAW["events"] + [RAW["events"][0]]), "there twice"),
        ]
        for raw, message in cases:
            with self.subTest(message=message):
                with self.assertRaises(LogError) as caught:
                    eventlog.load_dictionary(raw)
                self.assertIn(message, str(caught.exception))


class DecodeTests(unittest.TestCase):
    def test_one_block(self) -> None:
        data = block(
            0,
            [
                record(1, 0, 1000, 0, 0x12),
                record(2, 1, 2500, 0x02FFFE07, 0x7E4C9531),
                record(3, 2, 2600),
            ],
        )
        got = lines(data)
        build = WORDS.build_id.hex()
        self.assertEqual(
            got,
            [
                {
                    "seq": 0,
                    "cpu": 0,
                    "session": 1,
                    "time_us": 1000,
                    "event": "boot",
                    "level": "info",
                    "args": {"session": 0, "why": "0x00000012"},
                    "build": build,
                },
                {
                    "seq": 1,
                    "cpu": 0,
                    "session": 1,
                    "time_us": 2500,
                    "event": "mode",
                    "level": "warn",
                    "args": {
                        "bits": {
                            "raw": "0x02FFFE07",
                            "low": 7,
                            "temp": -2,
                            "kind": "two",
                        },
                        "where": "0x7E4C9531",
                    },
                    "build": build,
                },
                {
                    "seq": 2,
                    "cpu": 0,
                    "session": 1,
                    "time_us": 2600,
                    "event": "tick",
                    "level": "debug",
                    "args": {},
                    "build": build,
                },
            ],
        )
        for line in got:
            json.dumps(line)

    def test_an_unknown_id_is_given_as_numbers(self) -> None:
        # a block of a build whose dictionary is not given
        got = lines(block(7, [record(0x7FFE, 7, 10, 1, 2)], build=b"\x01" * 8))[1:]
        self.assertEqual(got[0]["event"], "unknown_0x7FFE")
        self.assertEqual(got[0]["id"], 0x7FFE)
        self.assertIs(got[0]["unknown"], True)
        self.assertEqual(got[0]["args"], {"arg0": "0x00000001", "arg1": "0x00000002"})
        self.assertNotIn("level", got[0])

    def test_a_file_that_ends_inside_a_block(self) -> None:
        whole = block(0, [record(3, n, 10 * n) for n in range(5)])
        got = lines(whole[: 32 + 16 * 3 + 7])
        self.assertEqual([line.get("seq") for line in got[:3]], [0, 1, 2])
        self.assertEqual(
            got[3], {"marker": "truncated", "cpu": 0, "seq": 3, "missing": 2}
        )
        self.assertEqual(len(got), 4)
        got = lines(whole + whole[:20])
        self.assertEqual(got[-1]["marker"], "truncated")
        self.assertEqual(got[-1]["missing"], "block header")
        self.assertEqual(len(got), 6)

    def test_a_block_that_a_failed_write_cut_short_and_the_next_block(self) -> None:
        # fwrite failed after the header and 2 of 4 records; the next flush
        # starts a new block at the first record that is not in the file.
        cut = block(0, [record(3, n, n) for n in range(2)], count=4)
        rest = block(2, [record(3, n, n) for n in range(2, 6)])
        got = lines(cut + rest)
        self.assertEqual(
            [line.get("marker", line.get("seq")) for line in got],
            [0, 1, "truncated", 2, 3, 4, 5],
        )
        self.assertEqual(got[2]["missing"], 2)

    def test_a_ring_that_wrapped_before_the_flush(self) -> None:
        # 600 records were written, the ring holds 512: the block starts at 88.
        first = block(88, [record(3, n, n) for n in range(88, 600)], drops=88)
        got = lines(first)
        self.assertEqual(got[0], {"marker": "gap", "cpu": 0, "seq": 88, "lost": 88})
        self.assertEqual(got[1]["seq"], 88)
        self.assertEqual(got[-1]["seq"], 599)
        # a later wrap: the next block does not start where the last one ended
        second = block(700, [record(3, 700, 700)], drops=188)
        got = lines(first + second)
        self.assertEqual(got[-2], {"marker": "gap", "cpu": 0, "seq": 700, "lost": 100})
        self.assertEqual(got[-1]["seq"], 700)

    def test_the_sequence_number_is_16_bits_of_the_record_number(self) -> None:
        got = lines(block(0x1FFFE, [record(3, n, n) for n in range(0x1FFFE, 0x20001)]))
        self.assertEqual([line["seq"] for line in got], [0x1FFFE, 0x1FFFF, 0x20000])
        self.assertTrue(all("marker" not in line for line in got))

    def test_records_that_cannot_be_real_are_dropped(self) -> None:
        # a slot whose sequence is not its place, and an id that the block's own dictionary does not have
        got = lines(
            block(
                5,
                [
                    record(3, 5, 0),
                    record(3, 9, 1),
                    record(0x7FFE, 7, 2),
                    record(3, 8, 3),
                ],
            )
        )
        self.assertEqual(
            [line.get("marker") or line["seq"] for line in got], [5, "damaged", 8]
        )
        self.assertEqual(
            got[1], {"marker": "damaged", "cpu": 0, "seq": 6, "records": 2}
        )

    def test_two_sessions_after_a_power_cycle(self) -> None:
        one = block(0, [record(1, 0, 100), record(3, 1, 200)])
        two = block(0, [record(1, 0, 150), record(3, 1, 160)])
        got = lines(one + two)
        self.assertEqual(
            [(line.get("session"), line.get("marker")) for line in got],
            [(1, None), (1, None), (None, "ring_restart"), (2, None), (2, None)],
        )
        self.assertTrue(all("recovered" not in line for line in got))

    def test_records_recovered_after_a_restart(self) -> None:
        # Session 1 flushed records 0 and 1, logged 2 and 3 and crashed. The
        # ring was still in RAM: the next session's first flush writes 2 and 3
        # before its own boot record.
        one = block(0, [record(1, 0, 100), record(3, 1, 200)])
        two = block(
            2,
            [
                record(3, 2, 300),
                record(2, 3, 400),
                record(1, 4, 50, 1),
                record(3, 5, 60),
            ],
            restarts=1,
        )
        got = lines(one + two)
        self.assertEqual([line["session"] for line in got], [1, 1, 1, 1, 2, 2])
        self.assertEqual(
            [line.get("recovered") for line in got],
            [None] * 2 + [True] * 2 + [None] * 2,
        )
        self.assertEqual(got[4]["args"]["session"], 1)

    def test_the_time_goes_on_when_the_timer_wraps(self) -> None:
        got = lines(
            block(
                0,
                [
                    record(3, 0, TOP - 5),
                    record(3, 1, 10),
                    record(1, 2, 3),
                    record(3, 3, 4),
                ],
            )
        )
        self.assertEqual(
            [line["time_us"] for line in got], [TOP - 5, TOP + 1 + 10, 3, 4]
        )

    def test_each_cpu_has_its_own_numbers(self) -> None:
        got = lines(
            block(0, [record(3, 0, 5)])
            + block(0, [record(3, 0, 7)], cpu=1)
            + block(1, [record(3, 1, 9)])
        )
        self.assertEqual(
            [(line["cpu"], line["seq"]) for line in got], [(0, 0), (1, 0), (0, 1)]
        )

    def test_bytes_that_are_not_a_block_are_skipped(self) -> None:
        good = block(0, [record(3, 0, 5)])
        got = lines(b"junk" + good + b"\0\1" + b"\0" * 7 + block(1, [record(3, 1, 6)]))
        self.assertEqual(
            [line.get("marker", line.get("seq")) for line in got],
            ["garbage", 0, "garbage", 1],
        )
        self.assertEqual(got[0], {"marker": "garbage", "offset": 0, "bytes": 4})
        self.assertEqual(got[2]["bytes"], 9)

    def test_a_block_that_was_written_twice_is_given_once(self) -> None:
        # The file did not seem to keep the first write, so the next flush
        # wrote the records again, with newer ones behind them.
        first = block(0, [record(1, 0, 5), record(3, 1, 6)])
        again = block(0, [record(1, 0, 5), record(3, 1, 6), record(3, 2, 7)])
        got = lines(first + again)
        self.assertEqual(
            [line.get("marker", line.get("seq")) for line in got], [0, 1, "repeat", 2]
        )
        self.assertEqual(got[2], {"marker": "repeat", "cpu": 0, "seq": 0, "records": 2})
        self.assertEqual(
            [line["session"] for line in got if "seq" in line and "marker" not in line],
            [1, 1, 1],
        )
        # a block that differs in one of these records is a new ring, not a
        # repeat: a restart with clear RAM also begins at record 0
        other = block(0, [record(1, 0, 5), record(3, 1, 10)])
        got = lines(first + other)
        self.assertEqual(
            [line.get("marker", line.get("seq")) for line in got],
            [0, 1, "ring_restart", 0, 1],
        )

    def test_zero_bytes_after_a_block_are_padding(self) -> None:
        # the firmware writes each block as one 512-byte sector
        def sector(first: int, count: int) -> bytes:
            data = block(first, [record(3, n, n) for n in range(first, first + count)])
            return data + bytes(512 - len(data))

        data = sector(0, 30) + sector(30, 4) + sector(34, 1)
        self.assertEqual(len(data), 3 * 512)
        got = lines(data)
        self.assertEqual([line.get("seq") for line in got], list(range(35)))
        got = lines(data[: 2 * 512 - 100])
        self.assertEqual([line.get("seq") for line in got], list(range(34)))

    def test_a_block_of_another_dictionary_is_marked_once(self) -> None:
        other = b"\x01" * 8
        data = block(0, [record(3, 0, 5)], build=other) + block(
            1, [record(3, 1, 6)], build=other
        )
        got = lines(data)
        self.assertEqual(
            got[0],
            {
                "marker": "dictionary_mismatch",
                "build": other.hex(),
                "dictionary": WORDS.build_id.hex(),
            },
        )
        self.assertEqual([line.get("marker") for line in got[1:]], [None, None])
        self.assertEqual(got[1]["build"], other.hex())

    def test_a_file_without_a_block_is_an_error(self) -> None:
        for data in (b"", b"EPLG", b"no log here" * 10):
            with self.subTest(data=data[:8]):
                with self.assertRaises(LogError):
                    lines(data)


class SessionTests(unittest.TestCase):
    """Sessions, recovered records and times: the patterns of a real camera."""

    def start(self, first: int, found: int) -> list[bytes]:
        """Return the CPU 0 records of a start: 4 error records, then boot."""
        early = [record(3, first + n, 19497 + n, 0x19000C03) for n in range(4)]
        return early + [record(1, first + 4, 101070, found)]

    def test_records_before_boot_belong_to_the_start(self) -> None:
        # The camera's file of 2026-11-15. The firmware records errors at
        # 19 ms on CPU 0 and at 46 ms on CPU 1. The boot task runs at 101 ms.
        # The error records start the ring, so the boot hook finds a ring and
        # counts 1 at every power-on. Power off clears the RAM.
        one = self.start(0, 1) + [
            record(5, 5, 2_251_489, 0x5100),
            record(2, 6, 9_000_000),
        ]
        other = [record(3, n, 45688 + n, 0x19000C03) for n in range(3)]
        again = [record(3, n, 45666 + n, 0x19000C03) for n in range(3)]
        two = self.start(0, 1) + [record(2, 5, 3_146_000, 0x5700)]
        data = (
            block(0, one, build=CAMERA_ID, restarts=1)
            + block(0, other, cpu=1, build=CAMERA_ID)
            + block(0, two, build=CAMERA_ID, restarts=1)
            + block(0, again, cpu=1, build=CAMERA_ID)
        )
        got = camera_lines(data)
        self.assertEqual(
            [line.get("marker", line.get("session")) for line in got],
            [1] * 7 + [1] * 3 + ["ring_restart"] + [2] * 6 + ["ring_restart"] + [2] * 3,
        )
        self.assertTrue(all("recovered" not in line for line in got))
        # the time starts again with the session: no timer wrap is counted
        second = [line for line in got if line.get("session") == 2]
        self.assertEqual(second[0]["time_us"], 19497)
        self.assertEqual(second[4]["time_us"], 101070)
        self.assertEqual(second[-1]["time_us"], 45668)
        self.assertEqual(second[4]["args"], {"ring_found": 1})

    def test_a_restart_that_kept_the_ring(self) -> None:
        # Session 1 flushed its records 0 to 6 (CPU 0) and 0 to 1 (CPU 1),
        # logged two more records on CPU 0 and one on CPU 1, and crashed.
        # The RAM was kept. The next start put its error records and its boot
        # record behind them, and its first flush wrote all of them.
        one = self.start(0, 1) + [
            record(5, 5, 5_000_000, 0x5700),
            record(2, 6, 6_000_000),
        ]
        lost = [record(5, 7, 8_000_000, 0x5100), record(6, 8, 9_000_000, 167)]
        two = self.start(9, 2) + [record(2, 14, 4_000_000, 0x5705)]
        other_one = [record(3, 0, 46000), record(6, 1, 3_000_000, 70)]
        other_two = [
            record(6, 2, 8_500_000, 70),
            record(3, 3, 46001),
            record(6, 4, 2_000_000),
        ]
        data = (
            block(0, one, build=CAMERA_ID, restarts=1)
            + block(0, other_one, cpu=1, build=CAMERA_ID)
            + block(7, lost + two, build=CAMERA_ID, restarts=2)
            + block(2, other_two, cpu=1, build=CAMERA_ID)
        )
        got = camera_lines(data)
        self.assertTrue(all("marker" not in line for line in got))
        main = records(got)
        self.assertEqual([line["session"] for line in main], [1] * 9 + [2] * 6)
        self.assertEqual(
            [line["seq"] for line in main if line.get("recovered")], [7, 8]
        )
        self.assertEqual(main[9]["time_us"], 19497)
        self.assertEqual(main[13]["args"], {"ring_found": 2})
        other = records(got, cpu=1)
        self.assertEqual([line["session"] for line in other], [1, 1, 1, 2, 2])
        self.assertEqual(
            [line.get("recovered") for line in other][2:], [True, None, None]
        )
        self.assertEqual(
            [line["time_us"] for line in other][2:], [8_500_000, 46001, 2_000_000]
        )

    def test_recovered_records_in_more_than_one_block(self) -> None:
        # 40 records were not flushed before the crash: the next session
        # writes them as one full block and a part of the next block. The
        # records that the old session flushed itself are not recovered.
        old = [record(1, 0, 100), record(2, 1, 200, 0x5700)]
        lost = [record(5, n, 1000 + n) for n in range(2, 42)]
        new = [record(1, 42, 50, 1), record(5, 43, 60)]
        data = (
            block(0, old, build=CAMERA_ID)
            + block(2, lost[:30], build=CAMERA_ID, restarts=1)
            + block(32, lost[30:] + new, build=CAMERA_ID, restarts=1)
        )
        got = camera_lines(data)
        self.assertEqual(
            [line["seq"] for line in got if line.get("recovered")], list(range(2, 42))
        )
        self.assertEqual([line["session"] for line in got], [1] * 42 + [2] * 2)
        # without a flush record the mark stops where the write run begins
        old = [record(1, 0, 100), record(5, 1, 200)]
        data = block(0, old, build=CAMERA_ID) + block(
            2, lost[:5] + [record(1, 7, 50, 1)], build=CAMERA_ID, restarts=1
        )
        got = camera_lines(data)
        self.assertEqual(
            [line["seq"] for line in got if line.get("recovered")], [2, 3, 4, 5, 6]
        )

    def test_an_old_record_is_not_taken_for_one_of_the_start(self) -> None:
        # a record of the session before has a later time than the boot
        # record, or it is more than a second before it
        late = [record(5, 0, 5_000_000), record(1, 1, 101070, 1)]
        got = camera_lines(block(0, late, build=CAMERA_ID))
        self.assertEqual([line["session"] for line in got], [0, 1])
        self.assertIs(got[0]["recovered"], True)
        long_before = [record(5, 0, 100), record(1, 1, 100 + eventlog.EARLY_US + 1)]
        got = camera_lines(block(0, long_before, build=CAMERA_ID))
        self.assertEqual([line["session"] for line in got], [0, 1])
        near = [record(5, 0, 100), record(1, 1, 100 + eventlog.EARLY_US)]
        got = camera_lines(block(0, near, build=CAMERA_ID))
        self.assertEqual([line["session"] for line in got], [1, 1])
        self.assertNotIn("recovered", got[0])


class NameTests(unittest.TestCase):
    def test_a_record_carries_the_names_of_its_values(self) -> None:
        data = block(
            0,
            [
                record(5, 0, 10, 0x5100, 0x5705),
                record(5, 1, 20, 0x5701, 0x5200),
                record(6, 2, 30, 167, 0x02000001),
                record(6, 3, 40, 9, 0x03000001),
                record(2, 4, 50, 0x5705),
            ],
            build=CAMERA_ID,
        )
        got = camera_lines(data)
        self.assertEqual(
            got[0]["names"], {"state": "live view", "previous": "live control"}
        )
        self.assertEqual(got[0]["args"]["state"], "0x00005100")
        # 0x57xx names the group; 0x5200 has no name
        self.assertEqual(got[1]["names"], {"state": "menu"})
        self.assertEqual(got[2]["names"], {"art": "Diorama entry", "latch.C": "Red"})
        self.assertNotIn("names", got[3])
        self.assertEqual(got[4]["names"], {"gui_state": "live control"})
        self.assertEqual(
            list(got[2]),
            [
                "seq",
                "cpu",
                "session",
                "time_us",
                "event",
                "level",
                "args",
                "names",
                "build",
            ],
        )

    def test_tables_and_names_are_not_part_of_the_build_id(self) -> None:
        bare = json.loads(json.dumps(CAMERA))
        del bare["tables"]
        for event in bare["events"]:
            event.pop("names", None)
        self.assertEqual(eventlog.load_dictionary(bare).build_id, CAMERA_ID)

    def test_refusals(self) -> None:
        def changed(**keys: Any) -> dict[str, Any]:
            raw: dict[str, Any] = json.loads(json.dumps(CAMERA))
            raw.update(keys)
            return raw

        def named(names: Any) -> dict[str, Any]:
            raw = changed()
            raw["events"][1]["names"] = names
            return raw

        cases = [
            (changed(tables=[]), "'tables' must be an object"),
            (changed(tables={"screen": []}), "a table must be an object"),
            (changed(tables={"screen": {"five": "x"}}), "must be a number with a name"),
            (changed(tables={"screen": {"5": ""}}), "must be a number with a name"),
            (changed(tables={"screen": {"-5": "x"}}), "must be a number with a name"),
            (changed(tables={}), "names the table"),
            (named({"state": "screen"}), "which is no argument"),
            (named({"gui_state": 5}), "'names' must map"),
            (named({"gui_state": "none"}), "names the table 'none'"),
        ]
        for raw, text in cases:
            with self.subTest(text=text):
                with self.assertRaises(LogError) as caught:
                    eventlog.load_dictionary(raw)
                self.assertIn(text, str(caught.exception))


class OlderBuildTests(unittest.TestCase):
    """A file from a build with another dictionary, which is kept."""

    def older(self) -> eventlog.Dictionary:
        """Return ``CAMERA`` with an old argument name and without tables."""
        raw = json.loads(json.dumps(CAMERA))
        raw["events"][0]["args"][0]["name"] = "session"
        del raw["tables"]
        return eventlog.load_dictionary(raw, inherit=CAMERA_WORDS)

    def test_a_block_is_decoded_with_the_dictionary_of_its_build(self) -> None:
        older = self.older()
        self.assertNotEqual(older.build_id, CAMERA_ID)
        data = block(
            0, [record(1, 0, 5, 1), record(5, 1, 6, 0x5100)], build=older.build_id
        ) + block(0, [record(1, 0, 7, 1)], build=CAMERA_ID)
        got = list(eventlog.decode(data, CAMERA_WORDS, {older.build_id: older}))
        self.assertEqual(
            [line.get("marker", line.get("args")) for line in got],
            [
                {"session": 1},
                {"state": "0x00005100", "previous": "0x00000000"},
                "ring_restart",
                {"ring_found": 1},
            ],
        )
        self.assertEqual(got[0]["build"], older.build_id.hex())
        # the older dictionary takes the name tables of the newer one
        self.assertEqual(got[1]["names"], {"state": "live view"})
        # without the older dictionary the block is marked
        got = camera_lines(data)
        self.assertEqual(got[0]["marker"], "dictionary_mismatch")
        self.assertEqual(got[1]["args"], {"ring_found": 1})

    def test_a_dictionary_with_tables_does_not_inherit(self) -> None:
        raw = json.loads(json.dumps(CAMERA))
        raw["tables"]["screen"] = {"0x5100": "other"}
        words = eventlog.load_dictionary(raw, inherit=CAMERA_WORDS)
        self.assertEqual(words.tables["screen"].name(0x5100), "other")
        self.assertIsNone(words.tables["screen"].name(0x5705))


def repository_words() -> tuple[eventlog.Dictionary, dict[str, int]]:
    """Return the repository's dictionary and its event ids by name."""
    raw = json.loads((ROOT / "data" / "logdict" / "events.json").read_text(encoding="utf-8"))
    words = eventlog.load_dictionary(raw)
    return words, {event.name: number for number, event in words.events.items()}


class SummaryTests(unittest.TestCase):
    def session(self) -> bytes:
        """Return a file with one short session of every feature."""
        words, ids = repository_words()
        rows = [
            ("fw_error", 19_000, 0x19000C03, 0x7E4261AF),
            ("fw_error_args", 19_001, 1, 0x602A9B40),
            ("boot", 101_000, 1, 0),
            ("lv_values", 215_000, 0x03FCFFE6, 0x0131FFF7),
            ("gui_state", 2_000_000, 0x5100, 0x5000),
            ("pk_mf_start", 3_000_000, 0x00000100, 0),
            ("pk_latch", 3_020_000, 0x02000101, 0x100),
            ("film_stage", 3_100_000, 3, 0),
            ("pk_pass9", 3_150_000, 0xB596A940, 0x00000001),
            ("film_stage", 3_300_000, 3, 0),
            ("film_stage", 3_600_000, 3, 0),
            ("pk_mf_end", 4_000_000, 0x02010001, 0),
            ("pk_latch", 4_100_000, 0x02010000, 0),
            ("film_stage", 4_200_000, 167, 1),
            ("film_matrix", 4_200_001, 0x7ECB09BE, 0x604E8984),
            ("shoot_cbs", 5_000_000, 210, 0),
            ("shoot_cbs", 5_500_000, 136, 0),
            ("iv_start", 6_000_000, 0, 1),
            ("shoot_cbs", 7_000_000, 259, 0),
            ("shoot_cbs", 9_000_000, 261, 0),
            ("iv_frame", 11_000_000, 1, 0),
            ("shoot_cbs", 12_250_000, 261, 0),
            ("shoot_cbs", 14_000_000, 260, 0),
            ("iv_end", 14_500_000, 0, 1),
            ("lv_adjust", 20_000_000, 1, 1),
            ("gui_state", 30_000_000, 0x2000, 0x5100),
            ("flush", 30_010_000, 0x2000, 0),
        ]
        made = [
            record(ids[name], number, time, arg0, arg1)
            for number, (name, time, arg0, arg1) in enumerate(rows)
        ]
        return block(0, made, build=words.build_id, restarts=1)

    def test_the_report_of_a_session(self) -> None:
        words, _ = repository_words()
        text = logsummary.summarize(eventlog.decode(self.session(), words))
        for line in text:
            self.assertIsInstance(line, str)
        whole = "\n".join(text)
        for part in (
            f"27 records, 1 session, build id {words.build_id.hex()}",
            "session 1: 30.0 s, 27 records (CPU 0: 27); cold start (new ring); "
            "2 records before boot; ends with the flush at power off",
            "gaps: none",
            "firmware errors: 1",
            "[0x19000C03], caller 0x7E4261AF, at 0.019 to 0.019 s, sessions 1",
            "flushes: 1;",
            "[0x00002000]: 1",
            "film_stage 4",
            "peaking: 1 MF Assist run (1.0 s); colour when the latch is set: Red [2]",
            "2 frame periods, 200 to 300 ms, median 250 ms (4.0 frames per second)",
            "colour pass: 1 records, gain 0",
            "  run at 3.0 s, Red [2]: 2 frame periods, median 250 ms (200 to 300); "
            "frame start to the end of the colour pass: 50 ms",
            "[167]: 1",
            "[0x7ECB09BE]: 1",
            "shooting: 1 capture (callback 136), 1 time CBS_START_SHOOTING_PICTURE",
            "interval: armed 1 time (iv_start), 1 sequence (callback 259)",
            "sequence at 7.0 s: 2 frames (timer callbacks 261), 3.25 s between them; "
            "1 iv_frame record",
            "level gauge: working set x -26, y 1020, z -9 (length 1020; 1000 = 1 g) "
            "at session 1, 0.2 s",
            "level gauge: Adjust [1] at session 1, 20.0 s",
        ):
            with self.subTest(part=part):
                self.assertIn(part, whole)
        self.assertNotIn("markers:", whole)

    def test_the_timing_records_of_pass_9(self) -> None:
        # Three pk_stats records of a Red run, 0.8 s apart: 8 frames of
        # 100 ms, with 16 ms and 24 ms of colour loop per frame. Then a
        # White run: its first record is not paired with the Red ones, and a
        # record after the end of the run is not paired with it.
        words, ids = repository_words()
        rows = [
            ("boot", 101_000, 1, 0),
            ("pk_latch", 1_000_000, 0x02000101, 0x100),
            ("pk_stats", 1_500_000, 64_000, 0),
            ("pk_stats", 2_300_000, 128_000, 0),
            ("pk_stats", 3_100_000, 192_000, 0),
            ("pk_latch", 3_500_000, 0x02010000, 0x100),
            ("pk_latch", 5_000_000, 0x03000101, 0x100),
            ("pk_stats", 5_200_000, 40_000, 0x0200),
            ("pk_stats", 6_000_000, 24, 0x0200),
            ("pk_latch", 6_100_000, 0x03010000, 0x100),
            ("pk_stats", 6_800_000, 0, 0x0200),
        ]
        made = [
            record(ids[name], number, time, arg0, arg1)
            for number, (name, time, arg0, arg1) in enumerate(rows)
        ]
        data = block(0, made, build=words.build_id, restarts=1)
        text = logsummary.summarize(eventlog.decode(data, words))
        self.assertIn("  pass 9 timing: 6 pk_stats records of 8 passes each", text)
        self.assertIn(
            "    Red [2]: 2 pairs of records, frame period "
            "median 100 ms (100 to 100), 10.0 frames per second; peaking code "
            "of pass 9 per frame median 20.0 ms (16.0 to 24.0), 20 % of the "
            "frame period",
            text,
        )
        self.assertIn(
            "    White [0x00000200]: 1 pair of records, frame period "
            "median 100 ms (100 to 100), 10.0 frames per second; peaking code "
            "of pass 9 per frame median 0.0 ms (0.0 to 0.0), 0 % of the frame "
            "period",
            text,
        )
        self.assertIn("  run at 1.0 s, Red [2]: 0 frame periods", text)

    def test_gaps_markers_and_a_session_without_an_end(self) -> None:
        data = block(88, [record(3, n, n) for n in range(88, 90)], drops=88)
        data += block(0, [record(1, 0, 5), record(3, 1, 6)])
        text = logsummary.summarize(lines(data))
        self.assertEqual(text[0][:21], "4 records, 1 session,")
        self.assertIn("session 0: 0.0 s, 2 records (CPU 0: 2); no boot record", text)
        self.assertIn(
            "session 1: 0.0 s, 2 records (CPU 0: 2); cold start (new ring); "
            "no flush at the end",
            text,
        )
        self.assertIn("gaps: 1 (88 records lost)", text)
        self.assertIn("markers: ring_restart 1", text)
        self.assertIn("firmware errors: none", text)
        self.assertIn("flushes: none", text)
        self.assertFalse(any(line.startswith("peaking") for line in text))

    def test_a_session_that_wrote_the_records_of_the_one_before(self) -> None:
        old = [record(1, 0, 100), record(5, 1, 200)]
        new = [record(5, 2, 300), record(1, 3, 50, 1)]
        data = block(0, old, build=CAMERA_ID) + block(2, new, build=CAMERA_ID)
        text = logsummary.summarize(camera_lines(data))
        self.assertIn(
            "session 1: 0.0 s, 3 records (CPU 0: 3); cold start (new ring); "
            "1 record written by the next session; no flush at the end",
            text,
        )
        self.assertIn(
            "session 2: 0.0 s, 1 record (CPU 0: 1); RAM was kept; no flush at the end",
            text,
        )

    def test_a_session_whose_records_were_all_written_by_the_next(self) -> None:
        boot = {"seq": 0, "cpu": 0, "session": 1, "time_us": 100, "event": "boot"}
        boot.update(level="info", args={}, build="00", recovered=True)
        text = logsummary.summarize([boot])
        self.assertIn(
            "session 1: 0.0 s, 1 record (CPU 0: 1); cold start (new ring); "
            "1 record written by the next session; no record of its own",
            text,
        )


class CommandTests(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cli.main(list(argv))
        return status, out.getvalue(), err.getvalue()

    def test_log_prints_one_json_document(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            words = Path(folder, "events.json")
            words.write_text(json.dumps(RAW), encoding="utf-8")
            log = Path(folder, "EPM2LOG.BIN")
            log.write_bytes(block(0, [record(1, 0, 100), record(3, 1, 200)]))
            status, out, err = self.run_cli(
                "log", str(log), "--dict", str(words), "--json"
            )
            self.assertEqual((status, err), (0, ""))
            document = json.loads(out)
            self.assertEqual((document["command"], document["ok"]), ("log", True))
            got = document["events"]
            self.assertEqual([line["event"] for line in got], ["boot", "tick"])
            log.write_bytes(b"not a log")
            status, out, err = self.run_cli("log", str(log), "--dict", str(words))
            self.assertEqual((status, out), (7, ""))
            self.assertIn("no log block found", err)
            status, out, err = self.run_cli(
                "log", str(Path(folder, "none")), "--dict", str(words)
            )
            self.assertEqual(status, 3)

    def test_log_prints_a_summary(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            words = Path(folder, "events.json")
            words.write_text(json.dumps(RAW), encoding="utf-8")
            log = Path(folder, "EPM2LOG.BIN")
            log.write_bytes(block(0, [record(1, 0, 100), record(3, 1, 200)]))
            status, out, err = self.run_cli("log", str(log), "--dict", str(words))
            self.assertEqual((status, err), (0, ""))
            self.assertEqual(out.splitlines()[0][:22], "2 records, 1 session, ")
            self.assertIn("events: boot 1, tick 1", out.splitlines())

    def test_the_repository_dictionaries(self) -> None:
        raw = json.loads((ROOT / "data" / "logdict" / "events.json").read_text(encoding="utf-8"))
        words = eventlog.load_dictionary(raw)
        names = {event.name for event in words.events.values()}
        self.assertIn(eventlog.BOOT_EVENT, names)
        self.assertIn(eventlog.FLUSH_EVENT, names)
        # the dictionary of a build that was flashed is kept under its build id
        known = {words.build_id.hex()}
        for path in sorted((ROOT / "data" / "logdict").glob("events-*.json")):
            kept = eventlog.load_dictionary(
                json.loads(path.read_text(encoding="utf-8")), inherit=words
            )
            self.assertEqual(path.name, f"events-{kept.build_id.hex()}.json")
            known.add(kept.build_id.hex())
        # the two patch specs were generated from one of these dictionaries
        for name in ("log-core", "log-probes"):
            spec = json.loads(
                (ROOT / "data" / "specs" / f"{name}.json").read_text(encoding="utf-8")
            )
            self.assertIn(spec["_build_id"], known, name)
        # each id range belongs to one feature
        for event in raw["events"]:
            if event["spec"] == "log-core":
                self.assertLess(event["id"], 256, event["name"])
            else:
                self.assertGreaterEqual(event["id"], 256, event["name"])

    def test_log_reads_a_file_of_the_flashed_build(self) -> None:
        # The build that was on the camera on 2026-11-15 has the build id
        # d1ddd46b4dac2414. Its boot argument has the old name. The command
        # finds its dictionary in data/logdict/ without an option.
        flashed = bytes.fromhex("d1ddd46b4dac2414")
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder, "EPM2LOG.BIN")
            log.write_bytes(
                block(
                    0,
                    [record(1, 0, 101070, 1), record(1280, 1, 2_000_000, 167, 1)],
                    build=flashed,
                )
            )
            status, out, err = self.run_cli(
                "--project", str(ROOT), "log", str(log), "--json"
            )
            self.assertEqual((status, err), (0, ""))
            got = json.loads(out)["events"]
            self.assertEqual([line.get("marker") for line in got], [None, None])
            self.assertEqual(got[0]["args"]["session"], 1)
            self.assertEqual(got[1]["event"], "film_stage")
            self.assertEqual(got[1]["names"], {"art": "Diorama entry (stock: Cross Process II)"})
            # a block of the current dictionary in the same file
            words, ids = repository_words()
            log.write_bytes(
                block(0, [record(ids["boot"], 0, 5, 1)], build=words.build_id)
            )
            status, out, err = self.run_cli(
                "--project", str(ROOT), "log", str(log), "--json"
            )
            self.assertEqual(json.loads(out)["events"][0]["args"]["ring_found"], 1)


if __name__ == "__main__":
    unittest.main()

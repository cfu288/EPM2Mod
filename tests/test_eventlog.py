"""Tests of the camera-log decoder (``epm2mod.eventlog`` and ``epm2mod log``).

    uv run python -m unittest discover -s tests

The log files are made here, byte by byte, as the firmware's flush task writes
them. The last tests read the repository's own dictionary ``logs/events.json``.
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

from epm2mod import cli, eventlog  # noqa: E402
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
        got = lines(block(7, [record(0x7FFE, 7, 10, 1, 2)]))
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
        self.assertTrue(all("seq_in_record" not in line for line in got))
        got = lines(block(5, [record(3, 9, 0)]))
        self.assertEqual(got[0]["seq_in_record"], 9)

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


class CommandTests(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cli.main(list(argv))
        return status, out.getvalue(), err.getvalue()

    def test_log_prints_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            words = Path(folder, "events.json")
            words.write_text(json.dumps(RAW), encoding="utf-8")
            log = Path(folder, "EPM2LOG.BIN")
            log.write_bytes(block(0, [record(1, 0, 100), record(3, 1, 200)]))
            status, out, err = self.run_cli("log", str(log), "--dict", str(words))
            self.assertEqual((status, err), (0, ""))
            got = [json.loads(line) for line in out.splitlines()]
            self.assertEqual([line["event"] for line in got], ["boot", "tick"])
            log.write_bytes(b"not a log")
            status, out, err = self.run_cli("log", str(log), "--dict", str(words))
            self.assertEqual((status, out), (1, ""))
            self.assertIn("no log block found", err)
            status, out, err = self.run_cli(
                "log", str(Path(folder, "none")), "--dict", str(words)
            )
            self.assertEqual(status, 1)

    def test_the_repository_dictionary(self) -> None:
        raw = json.loads((ROOT / "logs" / "events.json").read_text(encoding="utf-8"))
        words = eventlog.load_dictionary(raw)
        names = {event.name for event in words.events.values()}
        self.assertIn(eventlog.BOOT_EVENT, names)
        # the two patch specs were generated from this dictionary
        for name in ("log-core", "log-probes"):
            spec = json.loads(
                (ROOT / "patches" / f"{name}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(spec["_build_id"], words.build_id.hex(), name)
        # each id range belongs to one feature
        for event in raw["events"]:
            if event["spec"] == "log-core":
                self.assertLess(event["id"], 256, event["name"])
            else:
                self.assertGreaterEqual(event["id"], 256, event["name"])


if __name__ == "__main__":
    unittest.main()

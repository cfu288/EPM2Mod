"""The comparison rule of emulator/boot-test, on made-up reports. No emulator is needed."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "emulator"))
import bootcheck  # noqa: E402

REPORT = """stop: {"why":"labtime","pc":2118424173} | lab ms 2000.1 | wall ms 2897 | insns cpu0 30661113 cpu1 2764094
console (2 lines, prm tag messages left out):
  CPU0!
  :-) Pr3
cpu0 tasks: {"WAI":122,"RUN":1,"DMT":24}
quick start log: 10.5 SetPermit[1] | 10.6 MainStart
firmware error log entries: 2 36.1 0x2a001001 from 7e579dcc(fn 7e579dbf) args 0x8ff00004 0x7e5075f9 ; 37.6 0x2a001001 from 7e579dcc(fn 7e579dbf) args 0x8ff00004 0x7e5075f9
stand-ins and observers hit: gio-timer-set x3216, idle x275, idle x9105, S-GIOIN x3180
I2C transfers 81 | SIO client transfers 70 | S-DIV0 1
cpu1: idle | problems: none
STAGE 2: PASS (kernel on both cores, Usr0..Usr4 done, tasks scheduled, no fault)
"""


class CompareReports(unittest.TestCase):
    def differences(self, old: str, new: str) -> list[str]:
        self.assertIn(old, REPORT)
        return bootcheck.compare_reports(REPORT, REPORT.replace(old, new))

    def test_equal_reports_pass(self) -> None:
        self.assertEqual(bootcheck.compare_reports(REPORT, REPORT), [])

    def test_wall_time_instruction_counts_and_idle_counts_are_left_out(self) -> None:
        self.assertEqual(self.differences("wall ms 2897", "wall ms 5000"), [])
        self.assertEqual(self.differences("insns cpu0 30661113 cpu1 2764094", "insns cpu0 30661683 cpu1 2762235"), [])
        self.assertEqual(self.differences("idle x9105", "idle x9111"), [])

    def test_a_time_stamp_may_move_by_the_tolerance_only(self) -> None:
        self.assertEqual(self.differences("; 37.6 0x2a001001", "; 37.7 0x2a001001"), [])
        self.assertEqual(len(self.differences("; 37.6 0x2a001001", "; 38.6 0x2a001001")), 1)

    def test_everything_else_must_be_equal(self) -> None:
        for old, new in [
            ('"pc":2118424173', '"pc":2118334195'),
            ("lab ms 2000.1", "lab ms 1999.0"),
            ("  CPU0!", "  CPU0?"),
            ('"WAI":122', '"WAI":121'),
            ("0x2a001001 from 7e579dcc(fn 7e579dbf) args 0x8ff00004 0x7e5075f9 ;", "0x2a001002 from 7e579dcc(fn 7e579dbf) args 0x8ff00004 0x7e5075f9 ;"),
            ("entries: 2 36.1", "entries: 3 36.1"),
            ("S-GIOIN x3180", "S-GIOIN x3181"),
            ("gio-timer-set x3216", "gio-timer-set x3217"),
            ("S-DIV0 1", "S-DIV0 2"),
            ("problems: none", "problems: core 1 fault 3"),
            ("10.6 MainStart", "10.6 MainStop"),
        ]:
            with self.subTest(old=old):
                self.assertEqual(len(self.differences(old, new)), 1)

    def test_a_missing_line_fails(self) -> None:
        self.assertTrue(bootcheck.compare_reports(REPORT, REPORT.replace("  CPU0!\n", "")))


if __name__ == "__main__":
    unittest.main()

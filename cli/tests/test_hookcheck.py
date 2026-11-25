"""emulator/hookcheck.py checks the built bytes of a build. Needs Olympus's firmware and the MN103 objdump."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "emulator"))
import hookcheck  # noqa: E402

BUILD = json.loads((ROOT / "data" / "builds" / "spot-af-2.json").read_text())
NEEDS = [ROOT / "firmware" / "stock" / "E-PM2" / BUILD["stock"], Path(hookcheck.OBJDUMP)]


@unittest.skipUnless(all(p.exists() for p in NEEDS), "needs Olympus's firmware and build/toolchain's objdump")
class BuiltBytes(unittest.TestCase):
    def test_a_jump_that_a_later_spec_writes_into_an_earlier_specs_code_fails(self) -> None:
        # GitHub issue #6: peaking-mf wrote `jmp T_MF` (segment 2) over the start of T_R, kernel-range code of
        # custom-menu-rows-4. The check decoded the first spec's bytes there and reported nothing.
        lines: list[str] = []
        specs = [str(ROOT / s) for s in BUILD["specs"]]
        self.assertFalse(hookcheck.check(specs, hookcheck.read_allow(), lines.append))
        fails = [line for line in lines if line.startswith("FAIL")]
        self.assertEqual(len(fails), 1, fails)
        self.assertIn("0x7E4C93A4 (kernel) jmp -> 0x7ECB0B81 (segment-2)", fails[0])

"""emulator/hookcheck.py checks the built bytes of a build. Needs Olympus's firmware and the MN103 objdump."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "emulator"))
import hookcheck  # noqa: E402
import support  # noqa: E402

BUILD = json.loads((ROOT / "data" / "builds" / "spot-af-2.json").read_text())
NEEDS = [ROOT / "firmware" / "stock" / "E-PM2" / BUILD["stock"], Path(hookcheck.OBJDUMP)]


@support.needs(NEEDS[0].exists(), support.STOCK_NEEDED)
@support.needs(NEEDS[1].exists(), support.OBJDUMP_NEEDED)
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

    def test_an_allow_entry_accepts_its_address_with_its_target_only(self) -> None:
        pinned = json.loads((ROOT / "data" / "pinned-build.json").read_text())["build"]
        allow = hookcheck.read_allow()
        used: list[tuple[int, int, str]] = []
        self.assertTrue(hookcheck.check([str(ROOT / pinned)], allow, lambda line: None, used))
        address, target, entry = used[0]
        # the same address with another target (a later spec that re-targets an accepted hook) is not accepted
        moved = {key: why for key, why in allow.items() if key != (address, target)}
        moved[(address, target + 4)] = entry
        lines: list[str] = []
        self.assertFalse(hookcheck.check([str(ROOT / pinned)], moved, lines.append))
        fails = [line for line in lines if line.startswith("FAIL")]
        self.assertEqual(len(fails), 1, fails)
        self.assertIn("0x%08X" % address, fails[0])
        self.assertIn("accepts this address only for the target 0x%08X" % (target + 4), fails[0])
        self.assertIn("5 entries of the allow list match nothing in this build", lines[-1])  # and the 4 of movie-ab
        self.assertIn("%08X>%08X" % (address, target + 4), lines[-1])

    def test_the_allow_list_names_words_and_no_address_twice(self) -> None:
        text = (ROOT / "emulator" / "hookcheck-allow.tsv").read_text()
        words = [w for line in text.splitlines() if line and not line.startswith("#") for w in line.split("\t")[0].split()]
        self.assertTrue(all(len(w) == 17 and w[8] == ">" for w in words), "an entry is ADDRESS>TARGET, never a range")
        self.assertEqual(len({w[:8] for w in words}), len(words))
        self.assertEqual(len(hookcheck.read_allow()), len(words))

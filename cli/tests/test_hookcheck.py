"""emulator/hookcheck.py checks the built bytes of a build. Needs Olympus's firmware and the MN103 objdump."""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "emulator"))
import hookcheck  # noqa: E402
import support  # noqa: E402

BUILD = json.loads((ROOT / "data" / "builds" / "spot-af-2.json").read_text())
NEEDS = [ROOT / "firmware" / "stock" / "E-PM2" / BUILD["stock"], Path(hookcheck.toolchain.DEFAULT_DIR) / "mn10300-elf-objdump"]


@support.needs(NEEDS[0].exists(), support.STOCK_NEEDED)
@support.needs(NEEDS[1].exists(), support.OBJDUMP_NEEDED)
class BuiltBytes(unittest.TestCase):
    def test_a_jump_that_a_later_spec_writes_into_an_earlier_specs_code_fails(self) -> None:
        # GitHub issue #6: peaking-mf wrote `jmp T_MF` (segment 2) over the start of T_R, kernel-range code of
        # custom-menu-rows-4. The check decoded the first spec's bytes there and reported nothing.
        lines: list[str] = []
        specs = [str(ROOT / s) for s in BUILD["specs"]]
        self.assertFalse(hookcheck.check(specs, lines.append))
        fails = [line for line in lines if line.startswith("FAIL")]
        self.assertEqual(len(fails), 1, fails)
        self.assertIn("0x7E4C93A4 (kernel) jmp -> 0x7ECB0B81 (segment-2)", fails[0])

    def test_the_pinned_build_passes_and_a_build_is_compared_with_stock_when_none_is_pinned(self) -> None:
        pinned = hookcheck.pinned_specs()
        self.assertTrue(hookcheck.check(pinned, lambda line: None))
        with mock.patch.object(hookcheck, "pinned_specs", return_value=[]):
            mine, new = hookcheck.compare(pinned)
        self.assertTrue(mine)
        self.assertEqual(new, sorted(mine))

    def test_a_stock_pointer_that_an_op_rewrites_in_part_is_seen(self) -> None:
        import tempfile

        # the table word 0x7E78AEBC holds 0x7E56677A (segment 1) in stock. An op over its two upper bytes only
        # makes it 0x7EBF677A (segment 2): the word starts before the op.
        spec = {
            "name": "partial",
            "base": "firmware/stock/E-PM2/" + BUILD["stock"],
            "base_sha256": json.loads((ROOT / BUILD["specs"][0]).read_text())["base_sha256"],
            "ops": [{"type": "bytes", "block": 0, "offset": hex(0x7E78AEBC + 2 - hookcheck.BASE), "expect": "567e", "new": "bf7e"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "partial.json"
            path.write_text(json.dumps(spec))
            lines: list[str] = []
            self.assertFalse(hookcheck.check([str(path)], lines.append))
        fails = [line for line in lines if line.startswith("FAIL")]
        self.assertEqual(len(fails), 1, lines)
        self.assertIn("0x7E78AEBC (segment-1) pointer -> 0x7EBF677A (segment-2)", fails[0])

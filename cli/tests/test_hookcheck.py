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
NEEDS = [ROOT / "firmware" / "stock" / "E-PM2" / BUILD["stock"], Path(hookcheck.toolchain.DEFAULT_DIR) / "mn10300-elf-objdump"]


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

    def test_lint_shows_a_transfer_that_the_load_order_check_fails(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        import buildlint
        from unittest import mock

        pinned = str(ROOT / json.loads((ROOT / "data" / "pinned-build.json").read_text())["build"])
        self.assertFalse([w for w in buildlint.lint(pinned) if w.startswith("load order, FAIL")])
        allow = hookcheck.read_allow()
        removed = sorted(allow)[0]
        fewer = {key: why for key, why in allow.items() if key != removed}
        with mock.patch.object(hookcheck, "read_allow", return_value=fewer):
            warnings = buildlint.lint(pinned)
        fails = [w for w in warnings if w.startswith("load order, FAIL")]
        self.assertEqual(len(fails), 1, warnings)
        self.assertIn("0x%08X" % removed[0], fails[0])

    def test_lint_lists_every_entry_that_is_not_a_proof(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        import buildlint

        pinned = str(ROOT / json.loads((ROOT / "data" / "pinned-build.json").read_text())["build"])
        used: list[tuple[int, int, hookcheck.Allowed]] = []
        hookcheck.check([pinned], hookcheck.read_allow(), lambda line: None, used)
        # the addresses of each row are on the row's own line, before its count and its reason
        listed = set()
        for line in "\n".join(buildlint.lint(pinned)).splitlines():
            if line.strip().startswith("line "):
                listed |= set(line.split(": ", 1)[1].split(" (", 1)[0].split())
        for address, _target, entry in used:
            self.assertEqual("%08X" % address in listed, entry.cls != "proof", hex(address))
        self.assertEqual(len(listed), sum(entry.cls != "proof" for _, _, entry in used))
        # the three classes add up to every accepted transfer (docs/dev/load-order.md, section 5, says so)
        classes = [entry.cls for _, _, entry in used]
        self.assertEqual(sum(classes.count(c) for c in hookcheck.CLASSES), len(used))

    def test_every_allow_entry_is_used_by_a_build_description(self) -> None:
        unused = set(hookcheck.read_allow())
        pinned = json.loads((ROOT / "data" / "pinned-build.json").read_text())["build"]
        for build in (pinned, *hookcheck.USED_BY):  # not every description: one check of a build takes seconds
            used: list[tuple[int, int, str]] = []
            hookcheck.check([str(ROOT / build)], hookcheck.read_allow(), lambda line: None, used)
            unused -= {(address, target) for address, target, _ in used}
        self.assertEqual(unused, set())

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
            self.assertFalse(hookcheck.check([str(path)], {}, lines.append))
        fails = [line for line in lines if line.startswith("FAIL")]
        self.assertEqual(len(fails), 1, lines)
        self.assertIn("0x7E78AEBC (segment-1) pointer -> 0x7EBF677A (segment-2)", fails[0])

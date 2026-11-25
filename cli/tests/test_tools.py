"""The scripts that the checks rest on: what each one must refuse.

    uv run python -m unittest discover -s cli/tests
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import support  # noqa: E402
from support import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import checks  # noqa: E402
import toolchain  # noqa: E402

from epm2mod import pipeline, readme, stock  # noqa: E402
from epm2mod.builds import pinned_description  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

PATHS = RepoPaths(ROOT)
HAVE_STOCK = stock.stock_path(PATHS, stock.EPM2_V16).is_file()


#: A path of the kind the rule refuses, put together here so that this file passes the rule.
REAL = "/ho" + "me/realuser/"


class MachinePathTests(unittest.TestCase):
    def refused(self, line: str) -> bool:
        done = subprocess.run([str(ROOT / ".githooks" / "machine-paths")], input=line + "\n", capture_output=True, text=True)
        return done.returncode == 1

    def test_a_real_path_is_refused_also_beside_an_allowed_token(self) -> None:
        bare = REAL.rstrip("/")  # a home folder with nothing after it
        for line in (f"+ see {REAL}notes", f"+ scp {REAL}secret USER@HOST:/x", f"+ a /home/user/x b {REAL}y", f"+cd {bare}",
                     f"+ see file://{REAL}x", f"+ url=/{bare}",
                     "+ssh alice" + "@box", "+ sftp -q bob" + "@host.example", "+ /home/user" + "name/x"):
            with self.subTest(line=line):
                self.assertTrue(self.refused(line))

    def test_placeholders_and_removed_lines_pass(self) -> None:
        for line in ("+ scp USER@HOST:/x /home/user/y", "+ cd /home/user", "+ ssh USER@HOST", "+ mail a@b.example", "+ git@github.com:cfu288/EPM2Mod.git", f"- old {REAL}x", "+++ b/home/x"):
            with self.subTest(line=line):
                self.assertFalse(self.refused(line))


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class FirmwareMapTests(unittest.TestCase):
    def check(self, folder: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(ROOT / "tools" / "fwmap.py"), "--out", folder, "check"]
        return subprocess.run(command, capture_output=True, text=True)

    def test_a_map_without_its_last_file_is_not_complete(self) -> None:
        import fwmap

        with tempfile.TemporaryDirectory() as folder:
            for name in fwmap.FILES[:-1]:
                (Path(folder) / name).write_text("x")
            done = self.check(folder)
            self.assertEqual(done.returncode, 1)
            self.assertIn(fwmap.FILES[-1], done.stderr)
            (Path(folder) / fwmap.FILES[-1]).write_text("firmware sha256 0\n")  # made from another firmware
            done = self.check(folder)
            self.assertEqual(done.returncode, 1)
            self.assertIn("another firmware", done.stderr)
            self.assertIn("fwmap.py sha256", fwmap.made_by())  # a map of older map code is not current
            older = fwmap.made_by().replace("fwmap.py sha256 ", "fwmap.py sha256 0")
            (Path(folder) / fwmap.FILES[-1]).write_text(older)
            self.assertEqual(self.check(folder).returncode, 1)
            (Path(folder) / fwmap.FILES[-1]).write_text(fwmap.made_by())
            self.assertEqual(self.check(folder).returncode, 0, done.stderr)
        self.assertIn("tasks.tsv", fwmap.FILES)  # emulator/liveview.py reads it


class ToolchainTests(unittest.TestCase):
    def test_an_objdump_on_path_is_never_used(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "bin" / (toolchain.PREFIX + "objdump")
            fake.parent.mkdir()
            fake.write_text("#!/bin/sh\n")
            fake.chmod(0o755)
            environment = {"PATH": str(fake.parent) + os.pathsep + os.environ["PATH"]}
            with mock.patch.object(toolchain, "REPO", folder + "/norepo"), mock.patch.dict(os.environ, environment):
                os.environ.pop("EPM2_BINUTILS", None)
                with self.assertRaises(toolchain.ToolchainError):
                    toolchain.binutils_dir()

    def test_an_override_is_honoured_or_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as folder, mock.patch("sys.stderr"):
            with mock.patch.dict(os.environ, {"EPM2_BINUTILS": folder + "/absent", "CI": ""}):
                with self.assertRaisesRegex(toolchain.ToolchainError, "EPM2_BINUTILS: no MN103 binutils"):
                    toolchain.binutils_dir()  # no fall-back to build/toolchain
            (Path(folder) / (toolchain.PREFIX + "objdump")).write_text("")
            with mock.patch.dict(os.environ, {"EPM2_BINUTILS": folder, "CI": ""}):
                self.assertEqual(toolchain.binutils_dir(), folder)
            with mock.patch.dict(os.environ, {"EPM2_BINUTILS": folder, "CI": "1"}):
                with self.assertRaisesRegex(toolchain.ToolchainError, "hard checks"):
                    toolchain.binutils_dir()

    def test_binutils_of_another_source_commit_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            objdump = Path(folder) / "build" / "toolchain" / "bin" / (toolchain.PREFIX + "objdump")
            objdump.parent.mkdir(parents=True)
            objdump.write_text("")
            record = objdump.parent.parent / "source-commit"
            with mock.patch.object(toolchain, "REPO", folder), mock.patch.object(toolchain, "pinned_commit", return_value="abc"):
                os.environ.pop("EPM2_BINUTILS", None)
                with self.assertRaisesRegex(toolchain.ToolchainError, "source commit unknown"):
                    toolchain.binutils_dir()
                record.write_text("def\n")
                with self.assertRaisesRegex(toolchain.ToolchainError, "source commit def"):
                    toolchain.binutils_dir()
                record.write_text("abc\n")
                self.assertEqual(toolchain.binutils_dir(), str(objdump.parent))
            record.unlink()  # no record and no pin that git can name: not a match
            with mock.patch.object(toolchain, "REPO", folder), mock.patch.object(toolchain, "pinned_commit", return_value=""):
                with self.assertRaises(toolchain.ToolchainError):
                    toolchain.binutils_dir()


class EmulatorPinTests(unittest.TestCase):
    def test_an_override_is_refused_in_the_hard_checks(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        for name, call in (("OM_EMU_DIR", emuenv.om_emu_dir), ("OM_EMU_NODE", emuenv.node)):
            with self.subTest(name=name), mock.patch("sys.stderr"):
                with mock.patch.dict(os.environ, {name: "/x/elsewhere", "CI": "1"}):
                    with self.assertRaisesRegex(emuenv.EmuSetupError, name):
                        call()
                with mock.patch.dict(os.environ, {name: "/x/elsewhere", "CI": ""}):
                    self.assertEqual(call(), "/x/elsewhere")

    def test_emulator_options_do_not_come_from_the_callers_shell(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        shell = {"E101_FAST": "1", "E101_STATE": "/x/state.json", "WATCH": "0x1", "NO_OK": "1", "BOOTMS": "9", "KEPT": "yes"}
        with mock.patch.dict(os.environ, shell):
            clean = emuenv.clean_environment()
        self.assertEqual({name for name in shell if name in clean}, {"KEPT"})
        self.assertIn("PATH", clean)
        source = (ROOT / "emulator" / "emuenv.py").read_text()
        self.assertIn("env = dict(os.environ) if options_from_shell else clean_environment()", source)

    def test_an_edited_submodule_is_refused(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        def run(command: list[str], **keywords: object) -> mock.Mock:
            answers = {"ls-files": "160000 abc 0\temulator/om-emu\n", "rev-parse": "abc\n", "status": " M emu/bin/boot.mjs\n"}
            return mock.Mock(stdout=answers[command[1]])

        with mock.patch.dict(os.environ, {"OM_EMU_DIR": ""}), mock.patch.object(emuenv.os.path, "exists", return_value=True):
            with mock.patch.object(emuenv.subprocess, "run", run):
                with self.assertRaisesRegex(emuenv.EmuSetupError, "changes that are not in its commit"):
                    emuenv.require_om_emu()

    def test_a_submodule_at_another_commit_is_refused(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        other = mock.Mock(stdout="160000 0000000000000000000000000000000000000000 0\temulator/om-emu\n")
        with mock.patch.dict(os.environ, {"OM_EMU_DIR": ""}), mock.patch.object(emuenv.os.path, "exists", return_value=True):
            with mock.patch.object(emuenv.subprocess, "run", return_value=other):
                with self.assertRaisesRegex(emuenv.EmuSetupError, "the repository pins 0000000"):
                    emuenv.require_om_emu()


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class UnpackedImageTests(unittest.TestCase):
    def test_changed_blocks_in_the_folder_of_unpacked_images_are_not_reused(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import emuenv

        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"EMU_IMAGES": folder}):
            block = Path(emuenv.blocks("stock")) / "block0_0100.bin"
            good = block.read_bytes()
            sums = (block.parent / emuenv.SUMS).read_text()
            self.assertTrue(sums.splitlines()[0].endswith("the unpacker"))  # blocks of an older unpacker are not reused
            self.assertIn(emuenv.sha256(str(ROOT / "tools" / "oetool.py")), sums)
            block.write_bytes(bytes([good[0] ^ 1]) + good[1:])
            self.assertEqual((Path(emuenv.blocks("stock")) / "block0_0100.bin").read_bytes(), good)


class PrintedFailTests(unittest.TestCase):
    def test_a_script_that_prints_a_failed_result_and_exits_0_has_failed(self) -> None:
        def status(text: str) -> str:
            check = checks.Check("s", "full", (sys.executable, "-c", f"print({text!r})"))
            return checks.run(check, Path("image.BIN")).status

        self.assertEqual(status("  S6 RESULT [build]: FAIL: art codes [9]"), "FAIL")
        self.assertEqual(status("  S6 RESULT [build]: PASS"), "PASS")  # PASS or FAIL: no third result

    def test_every_result_line_is_shown(self) -> None:
        lines = [f"  S{n} RESULT [b]: PASS" for n in range(1, 39)] + ["  S39 RESULT [b]: PASS " + "y" * 1000, "x" * 9000]
        check = checks.Check("s", "full", (sys.executable, "-c", f"print({chr(10).join(lines)!r})"))
        shown = checks.summary(check, checks.run(check, Path("image.BIN")))
        self.assertEqual(shown.count("RESULT"), 39)
        self.assertIn("y" * 1000, shown)  # and whole

    def test_a_failure_without_a_failed_result_line_shows_how_it_ended(self) -> None:
        check = checks.Check("s", "full", (sys.executable, "-c", "print('S1 RESULT [b]: PASS'); raise SystemExit('boom')"))
        result = checks.run(check, Path("image.BIN"))
        self.assertEqual(result.status, "FAIL")
        self.assertIn("boom", checks.summary(check, result))
        self.assertIn("exit status 1", checks.summary(check, result))


OBJDUMP = Path(toolchain.DEFAULT_DIR) / (toolchain.PREFIX + "objdump")


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
@support.needs(OBJDUMP.exists(), support.OBJDUMP_NEEDED)
class ScenarioVerdictTests(unittest.TestCase):
    """What the scenario scripts of the full tier decide, on made-up results (the runs take 20 minutes)."""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(ROOT / "emulator" / "scenarios"))
        sys.path.insert(0, str(ROOT / "emulator"))

    def test_s6_fails_a_code_that_ends_in_block_0_where_the_reference_is_ok(self) -> None:
        import scen_direct4

        reference = {50: ("ok", "reaches 0x7E56D8D8 in 13 instructions"), 85: ("n/a", "needs job data"), 9: ("ok", "13")}
        same = {50: ("ok", "reaches 0x7E56D8D8 in 66 instructions"), 85: ("n/a", "needs job data"), 9: ("ok", "66")}
        self.assertEqual(scen_direct4.s6_fails(same, reference), [])  # other instruction counts are no fault
        # the table entry of code 50 pointed at the Cross Process handler: the run stays in block 0
        self.assertEqual(scen_direct4.s6_fails(same | {50: ("n/a", "needs job data")}, reference), [50])
        self.assertEqual(scen_direct4.s6_fails(same | {9: ("FAULT", "pc 0")}, reference | {9: ("FAULT", "pc 0")}), [9])

    def test_the_save_guard_reference_must_show_the_fault(self) -> None:
        import scen_guard

        with mock.patch.object(scen_guard, "OUT", lambda line: None):
            self.assertTrue(scen_guard.verdict("S19", [("pinned-fast", ["art buffers refused"]), ("build", [])]))
            # a reference that no longer shows the fault: the scenario proves nothing
            self.assertFalse(scen_guard.verdict("S19", [("pinned-fast", []), ("build", [])]))
            self.assertFalse(scen_guard.verdict("S19", [("pinned-fast", ["art buffers refused"]), ("build", ["no picture"])]))
            self.assertFalse(scen_guard.verdict("S25", [("pinned-fast", ["a fault"]), ("build", [])]))
            # an anomaly that is not the guard's fault does not count as "the reference shows the fault"
            self.assertFalse(scen_guard.verdict("S19", [("pinned-fast", ["start: no picture"]), ("build", [])]))
            self.assertTrue(scen_guard.verdict("S21", [("pinned-fast", ["ring stopped: heap re-partitioned under live blocks (1)"]), ("build", [])]))
        # S26 is for the images that have the probe, whatever their name
        with tempfile.TemporaryDirectory() as folder:
            at = scen_guard.RING_SITE - 0x7E421020
            with_probe, without = Path(folder) / "debug-named.bin", Path(folder) / "plain.bin"
            with_probe.write_bytes(bytes(at) + b"\xdc" + bytes(8))
            without.write_bytes(bytes(at) + b"\xf1" + bytes(8))
            self.assertTrue(scen_guard.has_guard_probe(str(with_probe)))
            self.assertFalse(scen_guard.has_guard_probe(str(without)))
            said: list[str] = []
            with mock.patch.object(scen_guard, "OUT", said.append):
                self.assertTrue(scen_guard.s26([("pinned-fast", str(with_probe)), ("debug-csf", str(without))]))
            self.assertIn("no image has the probe", said[-1])  # said, and the name "debug-csf" does not select it
        self.assertTrue(all(isinstance(v, bool) for v in scen_guard.REFERENCE_SHOWS_FAULT.values()))

    def peaking(self) -> dict[str, object]:
        """Return the names of scen_peaking.py without its run (the script ends with a bare main())."""
        path = ROOT / "emulator" / "scenarios" / "scen_peaking.py"
        names: dict[str, object] = {"__file__": str(path), "__name__": "scen_peaking"}
        exec(compile(path.read_text().rstrip()[: -len("main()")], str(path), "exec"), names)
        return names

    def test_s1_states_its_exceptions_exactly(self) -> None:
        names = self.peaking()
        stated_ram, flag2 = names["stated_ram"], names["L2"]
        word, copy = 0x602A4954, 0x7E6CDA36
        stock = [(0xA02A4954, 4, 0, copy)]

        def differs(value: int) -> dict[int, tuple[int, int]]:
            return {word + i: (0, (value >> 8 * i) & 0xFF) for i in range(4) if (value >> 8 * i) & 0xFF}

        assert callable(stated_ram) and isinstance(flag2, int)
        self.assertEqual(stated_ram(differs(0x605B1CF0), stock, [(0xA02A4954, 4, 0x605B1CF0, copy)]), {})
        # mutation C: mod code writes 0x11223344 to the residue word
        self.assertTrue(stated_ram(differs(0x11223344), stock, stock + [(word, 4, 0x11223344, 0x7E4C9000)]))
        self.assertTrue(stated_ram(differs(0x11223344), stock, [(0xA02A4954, 4, 0x11223344, copy)]))
        # mutation E: the flag byte L2 set to 0x44 with the request clear
        self.assertTrue(stated_ram({flag2: (None, 0x44)}, [], []))
        self.assertEqual(stated_ram({flag2: (None, 0)}, [], []), {})

    def test_only_a_stock_return_is_excused_after_a_hook_site(self) -> None:
        names = self.peaking()
        is_return, base = names["is_return"], 0x7E421020
        assert callable(is_return)
        image = bytes(16) + b"\xdf" + b"\xc8\x11" + b"\xf0\xfc" + b"\xde"
        self.assertTrue(is_return(image, base + 16))  # ret
        self.assertFalse(is_return(image, base + 17))  # beq, as at 0x7E56C6AB
        self.assertTrue(is_return(image, base + 19))  # rets
        self.assertTrue(is_return(image, base + 21))  # retf
        self.assertEqual(names["S1_SKIPPED"], (0x7E56C6AB,))  # the one branch, stated with its reason

    def test_s4_fails_a_step_that_faults_on_the_real_pinned_image(self) -> None:
        # The reviewer's mutation: the zoom-off handler 0x7EB7DEB9 of the pinned build jumps to address 0. The last
        # step still clears R, so only the fault of the step shows it. A real run in the emulator, 30 seconds.
        sys.path.insert(0, str(ROOT / "emulator"))
        import patchblock

        specs = [str(ROOT / s) for s in json.loads((ROOT / pinned_build_path()).read_text())["specs"]]
        stock, image, _ = patchblock.patched_block0(specs)
        at = 0x7EB7DEB9 - 0x7E421020
        mutated = image[:at] + b"\xdc" + ((0 - 0x7EB7DEB9) & 0xFFFFFFFF).to_bytes(4, "little") + image[at + 5 :]
        script = str(ROOT / "emulator" / "scenarios" / "scen_peaking.py")
        with tempfile.TemporaryDirectory() as folder:
            files = {}
            for name, data in (("stock", stock), ("good", image), ("mutated", mutated)):
                files[name] = Path(folder) / f"{name}.block0.bin"
                files[name].write_bytes(data)
            for name, status in (("good", 0), ("mutated", 1)):
                command = [sys.executable, script, "s4", str(files["stock"]), f"{name}={files[name]}"]
                done = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(done.returncode, status, done.stdout[-600:] + done.stderr[-600:])
            self.assertIn("FAIL: a step ended in a fault: internal zoom-off handler", done.stdout)

    def test_no_scenario_prints_a_fault_that_it_does_not_count(self) -> None:
        peaking = (ROOT / "emulator" / "scenarios" / "scen_peaking.py").read_text()
        direct4 = (ROOT / "emulator" / "scenarios" / "scen_direct4.py").read_text()
        # S2: the frames before and after the request; S4: each step; S5: frames, chooser, piece; S6: frames; S7: the end
        for text in ("anomalies in the frames without the request", "a step ended in a fault", "frame fault in %s",
                     '"chooser: " + r.fault', '"pass 9 piece: " + g.fault'):
            self.assertIn(text, peaking, text)
        for text in ('bad.append("%s frame fault" % NAMES[pm])', "ends[name] == ends[\"pinned\"]"):
            self.assertIn(text, direct4, text)

    def test_each_failure_text_of_the_peaking_scenarios_sets_the_exit_status(self) -> None:
        source = (ROOT / "emulator" / "scenarios" / "scen_peaking.py").read_text()
        self.assertTrue(source.rstrip().endswith("sys.exit(1 if FAILED else 0)\n\n\nmain()"))
        for text in ("DIFFERENCES FOUND", "anomalies: ", " (LEFT SET", "DIFFERS from pinned"):
            self.assertIn('fail("' + text, source, text)  # the failure text goes through fail(), which counts it
        self.assertIn("verdict = fail(verdict)", source)  # S2, no picture
        self.assertNotIn("os.environ", source)  # the scope of a scenario is not taken from the environment
        self.assertIn('fail("" if name != "pinned" else None)', source)  # S3, an anomaly
        self.assertIn('fail("the reference gives no picture', source)  # S2: no vacuous pass
        self.assertIn("the reference gives no picture in %s: the comparison proves nothing", source)  # S1


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class LedgerInputTests(unittest.TestCase):
    def test_the_ledger_is_made_from_the_files_git_holds_and_the_specs_given(self) -> None:
        import freespace

        copy = ROOT / "data" / "specs" / "zz-untracked-copy-for-a-test.json"
        copy.write_bytes((ROOT / "data" / "specs" / "spot-core-2.json").read_bytes())
        try:
            name = "data/specs/" + copy.name
            self.assertNotIn(name, [spec.path for spec in freespace.all_specs()])
            self.assertIn("data/specs/spot-core-2.json", [spec.path for spec in freespace.all_specs()])
            self.assertIn(name, [spec.path for spec in freespace.all_specs(extra=[name])])  # a candidate's own spec
        finally:
            copy.unlink()

    def test_a_spec_that_cannot_be_read_stops_the_check_with_its_name(self) -> None:
        import freespace

        broken = ROOT / "data" / "specs" / "zz-broken-for-a-test.json"
        broken.write_text("{ not json")
        try:
            with self.assertRaises(freespace.SiteError) as caught:
                freespace.all_specs(extra=["data/specs/" + broken.name])
        finally:
            broken.unlink()
        self.assertIn("zz-broken-for-a-test.json cannot be read", str(caught.exception))

    def test_the_map_records_the_objdump_that_made_it(self) -> None:
        import fwmap

        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / (toolchain.PREFIX + "objdump")).write_text("another objdump")
            pinned = fwmap.made_by()
            with mock.patch.object(toolchain, "binutils_dir", return_value=folder):
                other = fwmap.made_by()
        self.assertNotEqual(pinned, other)
        self.assertIn("objdump sha256", pinned)


class TrackedFilesTests(unittest.TestCase):
    def test_the_build_table_lists_the_descriptions_git_holds(self) -> None:
        pinned = ROOT / pinned_build_path()
        copy = pinned.with_name("zz-untracked-copy-for-a-test.json")
        copy.write_bytes(pinned.read_bytes())  # a tested description that is only in the working tree
        try:
            self.assertNotIn(copy.stem, readme.builds_block(PATHS, ROOT))
            self.assertIn(pinned.stem, readme.builds_block(PATHS, ROOT))
        finally:
            copy.unlink()

    def test_a_draft_in_the_working_tree_does_not_change_a_check_or_stop_a_listing(self) -> None:
        from epm2mod import cli

        draft_guide = PATHS.guides / "zz-draft-for-a-test.md"
        malformed = PATHS.builds / "zz-malformed-for-a-test.json"
        draft_guide.write_text("# A draft\n")
        malformed.write_text("{ not a description")
        try:
            self.assertEqual(readme.feature_problems(PATHS), [])  # the draft is not a guide yet
            self.assertTrue(readme.is_current(PATHS))  # generate --check
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(cli.main(["--project", str(ROOT), "builds", "--json"]), 0)
            listed = json.loads(out.getvalue())
            self.assertEqual(len(listed["unreadable"]), 1)
            self.assertIn(malformed.name, listed["unreadable"][0])
            self.assertTrue(all(build["in_git"] for build in listed["builds"]))
        finally:
            draft_guide.unlink()
            malformed.unlink()

    def test_a_program_of_the_release_is_one_by_gits_mode(self) -> None:
        from epm2mod import release

        launcher = next(p for p in PATHS.release_files if p.name == "start.sh")
        mode = launcher.stat().st_mode
        launcher.chmod(0o644)  # a file system without executable bits
        try:
            self.assertIn("start.sh", release.programs(PATHS))
        finally:
            launcher.chmod(mode)
        self.assertNotIn("README.txt", release.programs(PATHS))

    def test_ci_does_not_pick_up_descriptions_that_git_does_not_hold(self) -> None:
        script = (ROOT / "tools" / "ci.sh").read_text()
        builds = next(line for line in script.splitlines() if line.startswith("builds="))
        self.assertIn("$pinned", builds)
        self.assertIn("$named", builds)
        self.assertNotIn("unheld", builds)
        self.assertIn("Not checked, because git does not hold them", script)

    def test_the_zip_holds_the_package_files_git_holds(self) -> None:
        from epm2mod import release

        draft = PATHS.package / "zz_untracked_draft_for_a_test.py"
        draft.write_text("x = 1\n")
        try:
            names = [name for name, _ in release._package(PATHS)]
        finally:
            draft.unlink()
        self.assertNotIn(PATHS.relative(draft), names)
        self.assertIn(PATHS.relative(PATHS.package / "cli.py"), names)


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
@support.needs(OBJDUMP.exists(), support.OBJDUMP_NEEDED)
class GeneratorCheckTests(unittest.TestCase):
    def test_the_check_keeps_a_hand_edit_to_a_generated_spec_and_fails(self) -> None:
        # The reviewer's mutation. Before, the generators wrote over the edit and the check passed.
        spec = ROOT / "data" / "specs" / "lss-menu.json"
        good = spec.read_bytes()
        raw = json.loads(good)
        edited = (json.dumps(raw | {"description": raw["description"] + " HAND EDIT"}, indent=1) + "\n").encode()
        spec.write_bytes(edited)
        try:
            before = spec.stat()
            done = subprocess.run([str(ROOT / "gen" / "run.sh"), "--check"], cwd=ROOT, capture_output=True, text=True)
            kept = spec.read_bytes()
            after = spec.stat()
        finally:
            spec.write_bytes(good)
        self.assertEqual(done.returncode, 1, done.stderr[-400:])
        self.assertIn("not what its generator writes (the file is left as it was): data/specs/lss-menu.json", done.stderr)
        self.assertEqual(kept, edited)
        # not written and put back either: a killed check would lose the edit
        self.assertEqual((after.st_mtime_ns, after.st_ctime_ns), (before.st_mtime_ns, before.st_ctime_ns))


class WorkingFolderTests(unittest.TestCase):
    def test_a_descriptions_specs_are_the_repositorys_wherever_the_check_runs(self) -> None:
        sys.path.insert(0, str(ROOT / "emulator"))
        import hookcheck

        description = ROOT / pinned_build_path()
        with tempfile.TemporaryDirectory() as folder:
            decoy = Path(folder) / "data" / "specs"
            decoy.mkdir(parents=True)
            for spec in json.loads(description.read_text())["specs"]:
                (Path(folder) / spec).write_text("{}")  # a file of the same relative path in the working folder
            os.chdir(folder)
            try:
                specs = hookcheck.spec_list([str(description)])
            finally:
                os.chdir(ROOT)
        self.assertTrue(specs)
        self.assertTrue(all(Path(spec).is_relative_to(ROOT) for spec in specs), specs[:2])


class FirmwareMapUseTests(unittest.TestCase):
    def test_the_free_space_check_refuses_a_map_that_is_not_current(self) -> None:
        import freespace
        import fwmap

        with tempfile.TemporaryDirectory() as folder:
            for name in ("linear.txt", "functions.tsv", fwmap.FILES[-1]):
                (Path(folder) / name).write_text("addr\n")
            with mock.patch.object(freespace, "LINEAR", folder + "/linear.txt"), mock.patch.object(freespace, "FUNCTIONS", folder + "/functions.tsv"):
                with mock.patch.object(fwmap, "made_by", return_value="now\n"):
                    with self.assertRaises(freespace.SiteError):
                        freespace.Linear()


class StrictTimesTests(unittest.TestCase):
    def test_the_hard_tier_fails_a_start_whose_times_moved(self) -> None:
        build = ROOT / pinned_build_path()
        with mock.patch.object(checks, "current_image", return_value=Path("image.BIN")):
            plan = {check.name: check for check in checks.plan(build, "quick")}
        self.assertIn("--strict-times", plan["boot-test"].command)

    def test_a_description_from_another_place_is_refused(self) -> None:
        # a copy with fewer specs would have its specs checked against the image of data/builds/NAME.json
        own = ROOT / pinned_build_path()
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / own.name
            raw = json.loads(own.read_text())
            copy.write_text(json.dumps(raw | {"specs": raw["specs"][:1]}))
            with mock.patch.object(checks, "current_image", return_value=Path("image.BIN")):
                with self.assertRaisesRegex(ValueError, "not a build description of this project"):
                    checks.plan(copy, "quick")
                self.assertEqual(len(checks.plan(own, "quick")), 4)

    def test_every_peaking_build_gets_the_save_guard_scenario(self) -> None:
        # also a peaking build without the guard's spec: the build that the scenario must fail
        build = ROOT / "data" / "builds" / "peaking-fast.json"
        self.assertNotIn("peaking-save-guard", build.read_text())
        with mock.patch.object(checks, "current_image", return_value=Path("image.BIN")):
            names = [check.name for check in checks.plan(build, "full")]
        self.assertIn("save-guard", names)
        self.assertIn("peaking-s1-s5", names)


def pinned_build_path() -> str:
    """Return the path of the pinned build's description, relative to the root."""
    return str(json.loads((ROOT / "data" / "pinned-build.json").read_text())["build"])


class MachinePathHistoryTests(unittest.TestCase):
    def test_a_path_that_one_commit_adds_and_a_later_one_removes_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as folder:

            def git(*args: str) -> None:
                identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null"]
                subprocess.run(["git", *identity, *args], cwd=folder, check=True, capture_output=True)

            def commit(text: str) -> None:
                (Path(folder) / "notes.txt").write_text(text)
                git("add", "notes.txt")
                git("commit", "-q", "-m", "x")

            git("init", "-q")
            commit("start\n")
            git("tag", "base")
            commit(f"see {REAL}notes\n")
            git("tag", "added")
            commit("see /path/to/notes\n")
            tool = str(ROOT / ".githooks" / "machine-paths")
            net = subprocess.run(["git", "diff", "-U0", "base", "HEAD"], cwd=folder, capture_output=True, text=True).stdout
            self.assertEqual(subprocess.run([tool], input=net, capture_output=True, text=True).returncode, 0)
            self.assertEqual(subprocess.run([tool, "--since", "base"], cwd=folder, capture_output=True).returncode, 1)
            self.assertEqual(subprocess.run([tool, "--since", "added"], cwd=folder, capture_output=True).returncode, 0)


class NodeVersionTests(unittest.TestCase):
    def test_one_full_version_everywhere(self) -> None:
        version = (ROOT / ".nvmrc").read_text().strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        engines = json.loads((ROOT / "web" / "package.json").read_text())["engines"]["node"]
        self.assertEqual(engines, version)


@support.needs(HAVE_STOCK, support.STOCK_NEEDED)
class CurrentImageTests(unittest.TestCase):
    def test_an_image_of_other_bytes_stops_the_checks(self) -> None:
        build = pinned_description(PATHS)
        specs = pipeline.load_specs(PATHS, build)
        image = pipeline.build_image(build, specs, stock.read_stock(PATHS, build.stock_firmware))[0].image
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.BIN"
            path.write_bytes(image)
            self.assertEqual(checks.current_image(build.name, path), path)
            path.write_bytes(image[:-1] + bytes([image[-1] ^ 1]))  # yesterday's image
            with self.assertRaisesRegex(ValueError, "not what the description and its specs make now"):
                checks.current_image(build.name, path)
            path.unlink()
            with self.assertRaisesRegex(ValueError, "is absent"):
                checks.current_image(build.name, path)


class DocumentTests(unittest.TestCase):
    def test_the_documents_do_not_promise_the_pinned_label_or_sha256_for_a_release(self) -> None:
        build = pinned_description(PATHS)
        text = readme.pinned_block(PATHS, ROOT)
        self.assertNotIn(f"EPM2Mod {build.label}", text)
        self.assertIn("the day of the release", text)
        self.assertIn("Pinned build as tested", text)


if __name__ == "__main__":
    unittest.main()


class PythonVersionTests(unittest.TestCase):
    def test_one_full_version_everywhere(self) -> None:
        import re

        version = (ROOT / ".python-version").read_text().strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertEqual("%d.%d.%d" % sys.version_info[:3], version)  # what `uv run` gives
        for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            for named in re.findall(r"python-version: '([^']+)'", workflow.read_text()):
                self.assertEqual(named, version, workflow.name)  # a job without the file names the same version

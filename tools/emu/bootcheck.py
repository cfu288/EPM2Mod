"""The two start-up checks of a firmware image in the emulator. Python standard library only.

boot_test(image)         boots IMAGE and a reference image (the stock firmware) from the reset vector
                         for 2000 ms of lab time (tools/emu/boot/stage2-boot.mjs: the om-emu fork's
                         bin/boot.mjs report) and compares the
                         two reports under the rule below.
update_path_test(image)  boots both with OK held and an update file on the card
                         (tools/emu/boot/update-boot.mjs: bin/boot.mjs update): the image must find
                         the file as stock does.

The comparison rule of the boot test (RULE below is printed with --rule):

  The image passes when its own run ends with "STAGE 2: PASS" and every line of its report equals
  the reference's line, after these and only these parts are taken out of both:
    1. the wall time            "wall ms N" in the first line (the host's speed);
    2. the instruction counts   "insns cpu0 N cpu1 N" in the first line (new code runs more or
                                fewer instructions; the lab time they give is compared in 4);
    3. the idle counts          the "xN" of the entries named "idle" in the line "stand-ins and
                                observers hit" (how often the idle loops ran);
    4. lab time stamps          a time stamp (lab ms with one decimal, in the lines "quick start log",
                                "camera API async calls", "file task", "firmware error log entries")
                                may differ by TIME_TOLERANCE_MS or less. A larger shift fails.
  Everything else must be equal: the stop reason and pc, the console text, the boot marks, the task
  counts per state on both CPUs, the events, the API calls, the file task's commands, the firmware
  error entries (codes, callers, arguments), every other stand-in's hit count, the transfer counts,
  S-DIV0's count and the refused MMIO accesses, CPU1's state and the problems line.
  A patch that makes the start-up do something else on purpose (one more console line, one more
  flash write) fails this rule. Read the printed lines, then decide by hand; do not widen the rule.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emuenv  # noqa: E402

TIME_TOLERANCE_MS = 0.2
TIMED_LINES = ("quick start log:", "camera API async calls:", "file task:", "firmware error log entries:")
STAMP = re.compile(r"(?<![\w.])(\d+\.\d)(?= )")
RULE = __doc__.split("The comparison rule of the boot test (RULE below is printed with --rule):")[1].strip("\n")

OK, FAIL, USAGE, SETUP = 0, 1, 2, 3


def normalise(report):
    """Return [(text without the parts the rule takes out, [time stamps])] for each report line."""
    out = []
    for line in report.rstrip("\n").split("\n"):
        stamps = []
        if line.startswith("stop:"):
            line = re.sub(r"wall ms \d+", "wall ms *", line)
            line = re.sub(r"insns cpu0 \d+ cpu1 \d+", "insns *", line)
        elif line.startswith("stand-ins and observers hit:"):
            line = re.sub(r"\bidle x\d+", "idle x*", line)
        elif line.startswith(TIMED_LINES):
            stamps = [float(x) for x in STAMP.findall(line)]
            line = STAMP.sub("T", line)
        out.append((line, stamps))
    return out


def compare_reports(ref, new):
    """Return a list of differences (strings) between two boot reports under the rule. Empty = equal."""
    a, b = normalise(ref), normalise(new)
    ra, rb = ref.rstrip("\n").split("\n"), new.rstrip("\n").split("\n")
    diffs = []
    if len(a) != len(b):
        diffs.append(f"the reports have {len(a)} and {len(b)} lines")
    for i, ((ta, sa), (tb, sb)) in enumerate(zip(a, b)):
        if ta != tb or len(sa) != len(sb):
            diffs.append(f"line {i + 1} differs:\n  reference: {_cut(ra[i], rb[i])[0]}\n  image:     {_cut(ra[i], rb[i])[1]}")
            continue
        worst = max((abs(x - y) for x, y in zip(sa, sb)), default=0.0)
        if worst > TIME_TOLERANCE_MS + 1e-9:
            diffs.append(f"line {i + 1}: a time stamp moved by {worst:.1f} ms (more than {TIME_TOLERANCE_MS} ms):\n  reference: {_cut(ra[i], rb[i])[0]}\n  image:     {_cut(ra[i], rb[i])[1]}")
    return diffs


def _cut(x, y, width=200):
    """Cut two long lines to the part around their first difference."""
    k = next((i for i, (c, d) in enumerate(zip(x, y)) if c != d), min(len(x), len(y)))
    lo = max(0, k - 60)
    return tuple(("..." if lo else "") + s[lo : lo + width] + ("..." if len(s) > lo + width else "") for s in (x, y))


def allowed_differences(ref, new):
    """Return the raw lines that differ but pass the rule (for the log)."""
    ra, rb = ref.rstrip("\n").split("\n"), new.rstrip("\n").split("\n")
    return [f"line {i + 1}" for i, (x, y) in enumerate(zip(ra, rb)) if x != y]


def _run_pair(tool, images, args, extra_env=None, timeout=900):
    """Run TOOL on each image at the same time. Return [(returncode, stdout, stderr)]."""
    procs = []
    for image in images:
        env = emuenv.tool_env(image, extra_env)
        procs.append(subprocess.Popen(emuenv.tool_command(tool, args), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    out = []
    for p in procs:
        try:
            o, e = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            o, e = p.communicate()
            e += f"\n(killed after {timeout} s of wall time)"
        out.append((p.returncode, o, e))
    return out


def _save(out_dir, name, text):
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, name), "w") as f:
            f.write(text)


def _why_no_boot(code, out, err):
    """One line that says how a boot run ended when it did not pass."""
    lines = out.strip().split("\n") if out.strip() else []
    stop = next((line for line in lines if line.startswith("stop:")), "")
    cpu1 = next((line for line in lines if line.startswith("cpu1:")), "")
    if stop or cpu1:
        return f"exit {code}; {stop.split(' | ')[0]}; {cpu1}"
    tail = (err.strip() or out.strip()).split("\n")[-1][:300] if (err.strip() or out.strip()) else "no output"
    return f"exit {code}; {tail}"


def boot_test(image, ref="stock", ms=2000, out_dir=None, say=print):
    """Run the boot test. Return OK or FAIL; raise emuenv.EmuSetupError when the emulator cannot run."""
    (rc, rout, rerr), (ic, iout, ierr) = _run_pair("stage2-boot.mjs", [ref, image], [str(ms)])
    _save(out_dir, "boot-reference.txt", rout + rerr)
    _save(out_dir, "boot-image.txt", iout + ierr)
    if rc != 0 or "STAGE 2: PASS" not in rout:
        say(f"boot-test: FAIL: the reference image {ref} did not boot ({_why_no_boot(rc, rout, rerr)}); the emulator set-up is wrong, not the image")
        return FAIL
    if ic != 0 or "STAGE 2: PASS" not in iout:
        say(f"boot-test: FAIL: {image} does not reach the end of start-up in {ms} ms of lab time ({_why_no_boot(ic, iout, ierr)})")
        return FAIL
    diffs = compare_reports(rout, iout)
    if diffs:
        say(f"boot-test: FAIL: {image} boots, but its report differs from {ref}'s in {len(diffs)} place(s) that the rule does not allow (--rule prints it):")
        for d in diffs:
            say(d)
        return FAIL
    allowed = allowed_differences(rout, iout)
    say(f"boot-test: PASS: {image} boots as {ref} does ({ms} ms of lab time; lines with allowed differences: {', '.join(allowed) or 'none'})")
    return OK


UPDATE_FILE = "DCOLYMP/E1019999.BIN"
UPDATE_MARKS = {"7e5056ab": "update flag byte cleared (OK held)", "7e54398b": "FIRMUP_SRV task body", "7e54350e": "FIRMUP_CLI task body", "7e5435bd": "firmup: binary file found"}
UPDATE_END = "[firmup]TYPE_FIRMUP_WRITE_BURE"


def _update_view(out):
    """Return (marks reached, console lines up to the body-controller step, problems line, stop reason)."""
    lines = out.split("\n")
    marks = sorted(m.group(1) for line in lines if (m := re.match(r"t=[\d.]+ ms first reach ([0-9a-f]+):", line)))
    console = []
    if "console:" in lines:
        for line in lines[lines.index("console:") + 1 :]:
            if not line.startswith("  "):
                break
            console.append(line.strip())
            if line.strip() == UPDATE_END:
                break
    problems = next((line for line in lines if line.startswith("problems:")), "problems: (no line)")
    stop = next((line.split(" lab ms")[0] for line in lines if line.startswith("stop:")), "stop: (no line)")
    return marks, console, problems, re.sub(r'"pc":\d+', '"pc":*', stop)


def update_path_test(image, ref="stock", ms=3000, out_dir=None, say=print, update_file=None):
    """Run the update-path test. Return OK or FAIL; raise emuenv.EmuSetupError when it cannot run.

    Both images start with OK held (pin 0x35 low) and a card that has DCOLYMP/E1019999.BIN (a copy
    of the stock firmware file, or UPDATE_FILE). The image passes when, as in the reference run:
    the update flag is cleared, the update tasks start, the file is found ("Binary file Hakken"),
    the console is equal up to the body-controller step (which the emulator cannot do), the run
    has no fault, and segment 2 is not loaded.
    """
    src = update_file or emuenv.STOCK_BIN
    if not os.path.isfile(src):
        raise emuenv.EmuSetupError(f"no update file at {src}")
    card = tempfile.mkdtemp(prefix="epm2-update-card-", dir=os.environ.get("EMU_TMP"))
    try:
        os.makedirs(os.path.join(card, "DCOLYMP"))
        shutil.copyfile(src, os.path.join(card, UPDATE_FILE))
        (rc, rout, rerr), (ic, iout, ierr) = _run_pair("update-boot.mjs", [ref, image], [str(ms)], {"E101_CARD": card})
    finally:
        shutil.rmtree(card, ignore_errors=True)
    _save(out_dir, "update-reference.txt", rout + rerr)
    _save(out_dir, "update-image.txt", iout + ierr)
    rm, rcon, rprob, rstop = _update_view(rout)
    im, icon, iprob, istop = _update_view(iout)
    ref_bad = [n for p, n in UPDATE_MARKS.items() if p not in rm]
    if rc != 0 or ref_bad or UPDATE_END not in rcon or rprob != "problems: none":
        say(f"update-path-test: FAIL: the reference image {ref} did not take the update path (exit {rc}; missing: {ref_bad or 'none'}; {rprob}); the emulator set-up is wrong, not the image")
        return FAIL
    reasons = []
    if ic != 0:
        reasons.append(f"the run ended with exit {ic}: {(ierr.strip() or iout.strip() or 'no output').splitlines()[-1][:300]}")
    for p, n in UPDATE_MARKS.items():
        if p not in im:
            reasons.append(f"not reached: {n} (0x{p})")
    if "7e504c18" in im:
        reasons.append("segment 2 was loaded (0x7e504c18): the image left the update path")
    if iprob != rprob:
        reasons.append(f"{iprob} (reference: {rprob})")
    if istop != rstop:
        reasons.append(f"{istop} (reference: {rstop})")
    if im != rm:
        reasons.append(f"the watched points reached differ: image {im}, reference {rm}")
    if icon != rcon:
        k = next((i for i, (x, y) in enumerate(zip(rcon, icon)) if x != y), min(len(rcon), len(icon)))
        reasons.append(f"the console differs at line {k + 1}: reference {rcon[k] if k < len(rcon) else '(end)'!r}, image {icon[k] if k < len(icon) else '(end)'!r}")
    if reasons:
        say(f"update-path-test: FAIL: {image} with OK held and an update file on the card:")
        for r in reasons:
            say("  " + r)
        return FAIL
    say(f"update-path-test: PASS: {image} finds the update file as {ref} does ({len(icon)} console lines equal up to the body-controller step, segment 2 not loaded, no fault)")
    return OK


def main(test, argv):
    """Command line of tools/emu/boot-test and tools/emu/update-path-test. Return the exit status."""
    import argparse

    name = "boot-test" if test is boot_test else "update-path-test"
    ap = argparse.ArgumentParser(prog=name, description=(test.__doc__ or "").split("\n")[0], epilog="Exit status: 0 pass, 1 fail (the reason is printed), 2 wrong arguments, 3 the emulator is not set up or the image file is missing.")
    ap.add_argument("image", nargs="?", help="stock, builds/NAME.json, a .BIN file or a folder of unpacked blocks")
    ap.add_argument("--ref", default="stock", help="the reference image (default: stock)")
    ap.add_argument("--ms", type=int, default=2000 if test is boot_test else 3000, help="lab time in ms")
    ap.add_argument("--out", help="folder for the two raw reports")
    if test is boot_test:
        ap.add_argument("--rule", action="store_true", help="print the comparison rule and stop")
    else:
        ap.add_argument("--update-file", help="the file to put on the card as DCOLYMP/E1019999.BIN (default: the stock firmware file)")
    a = ap.parse_args(argv)
    if test is boot_test and a.rule:
        print(RULE)
        return OK
    if not a.image:
        ap.print_usage(sys.stderr)
        return USAGE
    try:
        if test is boot_test:
            return boot_test(a.image, a.ref, a.ms, a.out)
        return update_path_test(a.image, a.ref, a.ms, a.out, update_file=a.update_file)
    except emuenv.EmuSetupError as e:
        print(f"{name}: cannot run: {e}", file=sys.stderr)
        return SETUP

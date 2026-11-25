#!/usr/bin/env python3
"""Run the off-camera checks of a build: only those its specs call for, in parallel.

    python3 tools/checks.py data/builds/NAME.json [--tier quick|full] [--jobs N] [--list]

quick   the static checks, the emulator start and the update path. Every result is PASS or FAIL: tools/ci.sh
        runs this tier. Run it after each change. Under a minute.
full    quick, and for a build with a peaking spec the scenario runs of emulator/scenarios/ (the save guard,
        the peaking scenarios). About 20 minutes. Run it once before a build is offered for a flash.

The image build/NAME.BIN must exist (`epm2mod make NAME`) and must be what the description and its specs make
now: the run makes the build again in memory and stops when the sha256 differs, so the emulator never runs an
image of yesterday's specs. A scenario compares with the camera-tested build peaking-fast, under the same rule: when
build/peaking-fast.BIN is absent, the run stops and names the command that makes it.

Every run does every check again. No result is kept: a result depends on the scripts in tools/ and emulator/, the
allow list, the firmware map and the emulator's commit, and a kept result could outlive a change to one of them.

boot-test runs with --strict-times: a start whose time stamps moved (TIMES MOVED) is a FAIL here, because this
tier has no result for "a person must read this". `epm2mod make` runs boot-test without it and prints the result.

Results: PASS or FAIL, by the exit status of the check's script. No scenario that ran ends without a verdict. A
line "RESULT ...: FAIL" with exit status 0 is a FAIL too. Every RESULT and REFERENCE line is printed.

The references of the scenarios: the stock firmware for the peaking scenarios (with the request clear the build
must do what stock does, but for writes to the mod's own RAM; S6 compares the verdict of each art code), and for
the save guard the camera-tested build peaking-fast, a peaking build without the guard, which must show the fault.
Exit status: 0 when no check failed, 1 when one failed, 2 for a usage error.

The scenario checks of the superseded spec families films12 and log-core (colour stages, live view of the film
entries, log scenarios) were here until 2026-11-25. No build after stock-films uses those specs; their scripts are in
experiments/ (2026-11-16-films-max, 2026-11-16-doublex, 2026-11-15-log) as a record.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PEAKING = ROOT / "emulator" / "scenarios"
TIERS = ("quick", "full")
RESULT_FAIL = re.compile(r"RESULT.*: FAIL")


@dataclasses.dataclass(frozen=True)
class Check:
    """One check of a build.

    Attributes:
        name: short name, shown in the report.
        tier: "quick" or "full".
        command: the command line, run in the repository root.
    """

    name: str
    tier: str
    command: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class Result:
    """The outcome of a check: status, seconds it took, the end of its output."""

    status: str
    seconds: float
    output: str


def current_image(name: str, image: Path | None = None) -> Path:
    """Return build/NAME.BIN (or ``image``) after a test that it is what the build's description and specs make now.

    Raises:
        ValueError: if the image is absent or is another build's bytes; the text names the command.
    """
    sys.path.insert(0, str(ROOT / "cli" / "src"))
    from epm2mod import pipeline, stock
    from epm2mod.errors import Epm2ModError
    from epm2mod.paths import RepoPaths

    image = image or ROOT / "build" / f"{name}.BIN"
    again = f"run 'epm2mod make {name}'"
    if not image.exists():
        raise ValueError(f"{image} is absent: {again}")
    paths = RepoPaths(ROOT)
    try:
        description = paths.build(name)
        specs = pipeline.load_specs(paths, description)
        _, digest = pipeline.build_image(description, specs, stock.read_stock(paths, description.stock_firmware))
    except Epm2ModError as error:
        raise ValueError(f"{name} cannot be made: {error}") from None
    if hashlib.sha256(image.read_bytes()).hexdigest() != digest:
        raise ValueError(f"{image} is not what the description and its specs make now: {again}")
    return image


def block0(image: Path) -> Path:
    """Return the unpacked block 0 of a firmware image (unpacked on first use by emulator/emu-run)."""
    done = subprocess.run(
        [sys.executable, str(ROOT / "emulator" / "emu-run"), "--blocks", str(image)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        raise RuntimeError((done.stdout + done.stderr).strip() or "emulator/emu-run failed")
    return Path(done.stdout.strip().splitlines()[-1]) / "block0_0100.bin"


def plan(description: Path, tier: str) -> list[Check]:
    """Return the checks that the specs of a build call for, in report order.

    Raises:
        ValueError: if the description cannot be read, or an image is absent or stale (``current_image``).
    """
    raw = json.loads(description.read_text(encoding="utf-8"))
    specs = [str(s) for s in raw["specs"]]
    image = current_image(description.stem)
    py = sys.executable
    has = lambda part: any(part in s for s in specs)  # noqa: E731

    first_code = ["--first-code"] if raw.get("first_code") else []
    checks = [
        Check("free-space", "quick", (py, "tools/freespace.py", "check", *specs, *first_code)),
        Check("op-check", "quick", (py, "emulator/opcheck.py", str(description))),
        Check("boot-test", "quick", (py, "emulator/boot-test", "--strict-times", str(image))),
        Check("update-path-test", "quick", (py, "emulator/update-path-test", str(image))),
    ]
    if tier == "quick":
        return checks

    peaking = has("data/specs/peaking-")
    name = description.stem
    if peaking:
        # for every peaking build, with the guard's spec or without: a build without the guard must fail here
        current_image("peaking-fast")
        script = PEAKING / "scen_guard.py"
        checks.append(Check("save-guard", "full", (py, str(script), "all", "pinned-fast={block0:peaking-fast}", f"{name}={{block0}}")))
        for label, script in (("peaking-s1-s5", PEAKING / "scen_peaking.py"), ("peaking-s6-s7", PEAKING / "scen_direct4.py")):
            checks.append(Check(label, "full", (py, str(script), "all", "{block0:stock}", f"{name}={{block0}}")))
    return checks


def resolve(command: tuple[str, ...], image: Path) -> list[str]:
    """Replace {block0} by the block 0 of the build's image and {block0:NAME} by that of build/NAME.BIN."""
    out = []
    for word in command:
        while "{block0" in word:
            start = word.index("{block0")
            end = word.index("}", start)
            inner = word[start + 1 : end]
            other = inner.split(":", 1)[1] if ":" in inner else ""
            source = image if not other else "stock" if other == "stock" else ROOT / "build" / (other + ".BIN")
            word = word[:start] + str(block0(source)) + word[end + 1 :]
        out.append(word)
    return out


def run(check: Check, image: Path) -> Result:
    """Run one check."""
    started = time.monotonic()
    try:
        done = subprocess.run(resolve(check.command, image), cwd=ROOT, capture_output=True, text=True, errors="backslashreplace", check=False)
        output, code = (done.stdout + done.stderr).strip(), done.returncode
    except (OSError, RuntimeError) as error:
        output, code = f"cannot run: {error}", 1
    printed_fail = any(RESULT_FAIL.search(line) for line in output.splitlines())
    if code != 0 or printed_fail:  # the exit status decides; a printed "RESULT ...: FAIL" with exit 0 fails all the same
        status = "FAIL"
        if code != 0:
            output += f"\nexit status {code}"
    else:
        status = "PASS"
    return Result(status, round(time.monotonic() - started, 1), output)


def summary(check: Check, result: Result) -> str:
    """Return the lines of a check's output that say its result."""
    lines = result.output.splitlines()
    marked = [line.strip() for line in lines if " RESULT" in line or " REFERENCE [" in line or line.startswith("FAIL")]
    if marked or result.status == "FAIL":  # every result line of a scenario, none cut off
        if result.status == "FAIL" and not any("FAIL" in line for line in marked):
            marked += [line.strip() for line in lines[-4:]]  # no line says why: the end of the output, with the exit status
        return "\n      ".join(marked or lines[-3:])
    return lines[-1].strip() if lines else ""


def main(argv: list[str]) -> int:
    """Run the command line."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("build", type=Path, help="build description, data/builds/NAME.json")
    parser.add_argument("--tier", choices=TIERS, default="quick")
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--list", action="store_true", help="print the checks and stop")
    args = parser.parse_args(argv)
    description = args.build if args.build.is_absolute() else Path.cwd() / args.build
    try:
        checks = plan(description.resolve(), args.tier)
    except (OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.list:
        for check in checks:
            print(f"{check.tier:5s} {check.name:18s} {' '.join(check.command)[:140]}")
        return 0
    image = ROOT / "build" / (description.stem + ".BIN")
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda c: run(c, image), checks))
    failed = 0
    for check, result in zip(checks, results):
        failed += result.status == "FAIL"
        took = f"{result.seconds:.0f} s"
        print(f"{result.status:6s} {check.name:18s} {took:>7s}  {summary(check, result)}")
    counts = {s: sum(r.status == s for r in results) for s in ("PASS", "FAIL")}
    print(f"{description.stem}, tier {args.tier}: " + ", ".join(f"{n} {s}" for s, n in counts.items() if n) + f"; {time.monotonic() - started:.0f} s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

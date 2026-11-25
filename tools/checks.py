#!/usr/bin/env python3
"""Run the off-camera checks of a build: only those its specs call for, in parallel, with a cache.

    python3 tools/checks.py data/builds/NAME.json [--tier quick|full] [--jobs N] [--no-cache] [--list]

quick   the static checks, the emulator start and the update path. Every result is PASS or FAIL: tools/ci.sh
        runs this tier. Run it after each change. Under a minute.
full    quick, and the scenario runs of emulator/scenarios/ (the peaking save guard, the peaking scenarios).
        About 20 minutes. Run it once before a build is offered for a flash.

The image build/NAME.BIN must exist (`epm2mod make NAME`). A check runs again only when its inputs
changed: the image, the patch specs, the check's own script and the files under tools/. Results are kept in
build/check-cache/ (ignored by git). A scenario compares with the camera-tested build peaking-fast: when
build/peaking-fast.BIN is absent, the run stops and names the command that makes it.

Results: PASS, FAIL, and in the full tier WARN: a scenario script that has no exit status. Read its RESULT lines,
printed here. Nothing is skipped: a check that cannot run is a FAIL.
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
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "build" / "check-cache"
PEAKING = ROOT / "emulator" / "scenarios"
TIERS = ("quick", "full")
OUTPUT_TAIL = 4000  # characters of a check's output that are kept


@dataclasses.dataclass(frozen=True)
class Check:
    """One check of a build.

    Attributes:
        name: short name, shown in the report.
        tier: "quick" or "full".
        command: the command line, run in the repository root.
        inputs: files whose content decides the result, besides the command line itself.
        judged: True when the exit status says pass or fail; False for a script that only prints results.
    """

    name: str
    tier: str
    command: tuple[str, ...] = ()
    inputs: tuple[Path, ...] = ()
    judged: bool = True


@dataclasses.dataclass(frozen=True)
class Result:
    """The outcome of a check: status, seconds it took, the end of its output, and if it came from the cache."""

    status: str
    seconds: float
    output: str
    cached: bool = False


def tool_files() -> tuple[Path, ...]:
    """Return the Python and shell files under tools/: a change to one can change any check."""
    found = [p for p in (ROOT / "tools").rglob("*") if p.suffix in (".py", ".mjs", ".sh", ".tsv") and "third_party" not in p.parts]
    return tuple(sorted(found))


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
        ValueError: if the description cannot be read or its image is absent.
    """
    raw = json.loads(description.read_text(encoding="utf-8"))
    specs = [str(s) for s in raw["specs"]]
    image = ROOT / "build" / (description.stem + ".BIN")
    if not image.exists():
        raise ValueError(f"{image.relative_to(ROOT)} is absent: run 'epm2mod make {description.stem}' first")
    spec_files = tuple(ROOT / s for s in specs)
    tools = tool_files()
    py = sys.executable
    has = lambda part: any(part in s for s in specs)  # noqa: E731

    def reference(name: str) -> Path:
        """Return the image of the camera-tested build NAME that a scenario compares with."""
        path = ROOT / "build" / f"{name}.BIN"
        if not path.exists():  # not made here: make also writes the card folder build/DCOLYMP
            raise ValueError(f"{path.relative_to(ROOT)} is absent: run 'epm2mod make {name}', then make {description.stem} again")
        return path

    first_code = ["--first-code"] if raw.get("first_code") else []
    checks = [
        Check("free-space", "quick", (py, "tools/freespace.py", "check", *specs, *first_code), spec_files + tools),
        Check("op-check", "quick", (py, "emulator/opcheck.py", str(description)), spec_files + tools),
        Check("boot-test", "quick", (py, "emulator/boot-test", str(image)), (image,) + tools),
        Check("update-path-test", "quick", (py, "emulator/update-path-test", str(image)), (image,) + tools),
    ]
    if tier == "quick":
        return checks

    peaking = has("data/specs/peaking-")
    name = description.stem
    if has("peaking-save-guard"):
        base, script = reference("peaking-fast"), PEAKING / "scen_guard.py"
        checks.append(Check("save-guard", "full", (py, str(script), "all", "pinned-fast={block0:peaking-fast}", f"{name}={{block0}}"),
                            (image, base, script) + tools))
    if peaking:
        base = reference("peaking-fast")
        for label, script in (("peaking-s1-s5", PEAKING / "scen_peaking.py"), ("peaking-s6-s7", PEAKING / "scen_direct4.py")):
            checks.append(Check(label, "full", (py, str(script), "all", "{block0:peaking-fast}", f"{name}={{block0}}"),
                                (image, base, script) + tools, judged=False))
    return checks


def cache_key(check: Check) -> str:
    """Return a key that changes when the command or the content of an input file changes."""
    digest = hashlib.sha256("\0".join(check.command).encode())
    for path in check.inputs:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.exists() else b"absent")
    return digest.hexdigest()[:24]


def resolve(command: tuple[str, ...], image: Path) -> list[str]:
    """Replace {block0} by the block 0 of the build's image and {block0:NAME} by that of build/NAME.BIN."""
    out = []
    for word in command:
        while "{block0" in word:
            start = word.index("{block0")
            end = word.index("}", start)
            inner = word[start + 1 : end]
            source = image if inner == "block0" else ROOT / "build" / (inner.split(":", 1)[1] + ".BIN")
            word = word[:start] + str(block0(source)) + word[end + 1 :]
        out.append(word)
    return out


def run(check: Check, image: Path, use_cache: bool) -> Result:
    """Run one check, or take its result from the cache."""
    record = CACHE / f"{check.name}-{cache_key(check)}.json"
    if use_cache and record.exists():
        saved = json.loads(record.read_text(encoding="utf-8"))
        return Result(saved["status"], saved["seconds"], saved["output"], cached=True)
    started = time.monotonic()
    try:
        done = subprocess.run(resolve(check.command, image), cwd=ROOT, capture_output=True, text=True, errors="backslashreplace", check=False)
        output, code = (done.stdout + done.stderr).strip(), done.returncode
    except (OSError, RuntimeError) as error:
        output, code = f"cannot run: {error}", 1
    if code != 0:
        status = "FAIL"
    else:
        status = "PASS" if check.judged else "WARN"
    result = Result(status, round(time.monotonic() - started, 1), output[-OUTPUT_TAIL:])
    CACHE.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(dataclasses.asdict(result)), encoding="utf-8")
    return result


def summary(check: Check, result: Result) -> str:
    """Return the lines of a check's output that say its result."""
    lines = result.output.splitlines()
    if result.status == "WARN" or result.status == "FAIL":
        marked = [line.strip() for line in lines if "RESULT" in line or line.startswith("FAIL")]
        return "\n      ".join(marked[-12:] or lines[-3:])
    return lines[-1].strip() if lines else ""


def main(argv: list[str]) -> int:
    """Run the command line."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("build", type=Path, help="build description, data/builds/NAME.json")
    parser.add_argument("--tier", choices=TIERS, default="quick")
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--no-cache", action="store_true", help="run every check again")
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
        results = list(pool.map(lambda c: run(c, image, not args.no_cache), checks))
    failed = 0
    for check, result in zip(checks, results):
        failed += result.status == "FAIL"
        took = "cached" if result.cached else f"{result.seconds:.0f} s"
        print(f"{result.status:6s} {check.name:18s} {took:>7s}  {summary(check, result)}")
    counts = {s: sum(r.status == s for r in results) for s in ("PASS", "FAIL", "WARN")}
    print(f"{description.stem}, tier {args.tier}: " + ", ".join(f"{n} {s}" for s, n in counts.items() if n) + f"; {time.monotonic() - started:.0f} s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

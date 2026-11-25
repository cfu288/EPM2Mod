#!/usr/bin/env python3
"""The soft report of a build: what may be harmful and is not proven safe. Static, no emulator.

    python3 tools/buildlint.py data/builds/NAME.json        (the command: uv run epm2mod lint NAME)

It prints WARN lines and one summary line. A WARN line is for a person to read before a flash and in a review;
it does not say that the build is wrong. Exit status: 0, also with warnings; 2 when the report cannot be made.

The warnings (the rule and the numbers behind them: docs/dev/load-order.md):

1. A jump or pointer from early-loaded to late-loaded code that the pinned build does not have (the hard check
   refuses it too).
2. `first_code` in the description: code in an area where none has run on a camera.
3. A candidate that changes early-loaded bytes: the camera test needs a cold start.

Needs Olympus's firmware and the MN103 objdump (uv run epm2mod init). Not the firmware map.
"""
import json
import os
import pathlib
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "tools"), os.path.join(ROOT, "emulator")]


def lint(description):
    """Return the WARN lines (without the word WARN) of the build description at the given path."""
    import freespace
    import hookcheck

    raw = json.loads(pathlib.Path(description).read_text(encoding="utf-8"))
    specs = [os.path.join(ROOT, s) for s in raw["specs"]]
    early = lambda a: hookcheck.segment(a) in hookcheck.EARLY  # noqa: E731
    warnings = []

    # 1. the load order
    _, new = hookcheck.compare(specs)
    if new:
        warnings.append("load order: the pinned build does not have these transfers from early-loaded to late-loaded code, "
                        "and the hard check refuses them: " + "; ".join("0x%08X -> 0x%08X" % pair for pair in new))

    # 2. first code
    if raw.get("first_code"):
        warnings.append("first code: the description has first_code. The build runs code in an area where no "
                        "camera-tested build runs code. Only the flash tests that area")

    # 3. the cold start
    spans = [span for s in specs for span in freespace.Spec(os.path.relpath(s, ROOT)).spans()]
    if any(early(lo) for lo, _ in spans) and not raw.get("camera_tested"):
        warnings.append("camera test: the build changes early-loaded bytes. Test a cold start: the camera off for "
                        "2 minutes, then on. A start after a short power-off keeps the RAM and hides a load-order fault")
    return warnings


def main(argv):
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__)
        return 2
    name = os.path.splitext(os.path.basename(argv[0]))[0]
    try:
        warnings = lint(argv[0])
    except (OSError, KeyError, ValueError, SystemExit) as error:  # SystemExit: how freespace.py and hookcheck.py stop
        print("lint: the report of %s cannot be made: %s" % (name, error))
        return 2
    for line in warnings:
        print("WARN  " + line)
    print("lint %s: %d warning%s. A warning does not fail a check; read each one before a flash." % (
        name, len(warnings), "" if len(warnings) == 1 else "s"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

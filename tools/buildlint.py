#!/usr/bin/env python3
"""The soft report of a build: what may be harmful and is not proven safe. Static, no emulator.

    python3 tools/buildlint.py data/builds/NAME.json        (the command: uv run epm2mod lint NAME)

It prints WARN lines and one summary line. A WARN line is for a person to read before a flash and in a review;
it does not say that the build is wrong. The hard checks are in tools/ci.sh. CI does not run this report. Exit status: 0, also with warnings; 2 when the report cannot be made (the reason is printed).

The warnings (the rule and the numbers behind them: docs/dev/load-order.md):

1. The transfers from early-loaded to late-loaded code: those that the pinned build does not have, each listed (the
   hard check refuses them), and the count of those that it has, with the document that says what is known of them.
2. Early-loaded space (kernel range, segment 1, pre-reset): the bytes that the build's specs use in each free-space
   area, and what is left there. A hook into an early-loaded function needs its routine in this space.
3. `first_code` in the description: code in an area where none has run on a camera.
4. A word in the build's new early-loaded bytes that is a late-loaded address, in one of the four address forms
   (runtime, uncached, flash, flash uncached). emulator/hookcheck.py does not see such a word: a pointer in new
   code, a table address. The scan takes every byte position, so a hit can be chance.
5. A candidate that changes early-loaded bytes: the camera test needs a cold start.

Needs Olympus's firmware and the MN103 objdump (uv run epm2mod init). Not the firmware map.
"""
import json
import pathlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "tools"), os.path.join(ROOT, "emulator")]
BASE = 0x7E421020
M32 = 0xFFFFFFFF
SHOWN = 6  # words of warning 4 that are printed
LATE = ("segment-2", "segment-3", "usr1-third")


def lint(description):
    """Return the WARN lines (without the word WARN) of the build description at the given path."""
    import freespace
    import hookcheck
    import patchblock

    raw = json.loads(pathlib.Path(description).read_text(encoding="utf-8"))
    specs = [os.path.join(ROOT, s) for s in raw["specs"]]
    early = lambda a: hookcheck.segment(a) in hookcheck.EARLY  # noqa: E731
    warnings = []

    # 1. the load order
    mine, new = hookcheck.compare(specs)
    if new:
        warnings.append("load order: the pinned build does not have these transfers from early-loaded to late-loaded code, "
                        "and the hard check refuses them: " + "; ".join("0x%08X -> 0x%08X" % pair for pair in new))
    old = [mine[pair][0] for pair in mine if pair not in new]
    if old:
        pointers = old.count("pointer")
        warnings.append("load order: %d transfers from early-loaded to late-loaded code that the pinned build has too "
                        "(%d jumps and calls, %d pointers): docs/dev/load-order.md, section 5" % (len(old), len(old) - pointers, pointers))

    # 2. early-loaded space
    space = freespace.Space(use_linear=False, extra_specs=[os.path.relpath(s, ROOT) for s in specs])
    spans = freespace.merge([span for s in specs for span in freespace.Spec(os.path.relpath(s, ROOT)).spans()])
    changes_early = any(early(lo) for lo, _ in spans)
    for area in space.areas:
        if not early(area.lo):
            continue
        cut = [(max(lo, area.lo), min(hi, area.hi)) for lo, hi in spans if lo < area.hi and hi > area.lo]
        used_bytes = sum(hi - lo for lo, hi in cut)
        if used_bytes:
            warnings.append("early-loaded space: the build uses %d B of the %d B area %s (%s); %d B are left there" % (
                used_bytes, area.size, freespace.rng(area.lo, area.hi), area.region_name(), area.size - used_bytes))

    # 3. first code
    if raw.get("first_code"):
        warnings.append("first code: the description has first_code. The build runs code in an area where no "
                        "camera-tested build runs code. Only the flash tests that area")

    # 4. words that are late-loaded addresses
    stock, image, _ = patchblock.patched_block0(specs)
    aliases = space.m.aliases()
    listed, hits = {address for address, _ in mine}, []
    for lo, hi in spans:
        if not early(lo):
            continue
        for a in range(lo - 3, hi):  # every word that overlaps the bytes, as emulator/hookcheck.py
            if a in listed:  # warning 1 has it
                continue
            word, old = (int.from_bytes(b[a - BASE:a - BASE + 4], "little") for b in (image, stock))
            if word == old:
                continue
            for form, delta in aliases:
                target = (word - delta) & M32
                where = hookcheck.segment(target)
                if where in LATE:
                    hits.append("0x%08X holds 0x%08X (%s, %s address)" % (a, word, where, form))
                    break
    if hits:
        warnings.append("%d word%s in the build's new early-loaded bytes can be a late-loaded address, which the "
                        "load-order check does not follow: %s%s" % (
                            len(hits), "" if len(hits) == 1 else "s", "; ".join(hits[:SHOWN]),
                            "; and %d more" % (len(hits) - SHOWN) if len(hits) > SHOWN else ""))

    # 5. the cold start
    if changes_early and not raw.get("camera_tested"):
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

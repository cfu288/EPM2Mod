"""The function cases of the features (interval shooting, the frame count, the menu rows) on the pinned build and on
builds/stock-films.json: every row must give the same outputs.

    python3 experiments/2026-11-18-stock-filters/scripts/features_same.py PINNED_BLOCK0 NEW_BLOCK0
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "emu"))
import cases  # noqa: E402
import emurun  # noqa: E402

CASES = ["ivl_guard", "ivl_selector", "ivl_start", "ivl_movie_guard", "frames_step", "frames_editor", "ivl_shot_done",
         "menu_help", "menu_child", "menu_value"]


def main():
    a, b = sys.argv[1:3]
    bad = 0
    for name in CASES:
        case = cases.CASES[name]
        ra, rb = emurun.run_image(case, a), emurun.run_image(case, b)
        diff = [(emurun.fmt_row(r1), emurun.public(o1), emurun.public(o2))
                for (r1, o1, _, _), (_, o2, _, _) in zip(ra, rb) if emurun.public(o1) != emurun.public(o2)]
        bad += bool(diff)
        print("%-16s %4d rows, %s" % (name, len(ra), "same" if not diff else "%d differ" % len(diff)))
        for row, o1, o2 in diff[:3]:
            print("    %s: %s -> %s" % (row, json.dumps(o1)[:100], json.dumps(o2)[:100]))
    print("ALL SAME" if not bad else "DIFFERENCES")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""Per-clip timing report from the Debug Log of the build debug-log-movie-time (NOTES.md in this folder).

    uv run epm2mod log /path/to/EPM2LOG.BIN --json > /path/to/log.json
    uv run python experiments/2026-11-19-movie-sampling/scripts/movtime_report.py /path/to/log.json

A clip is a run of mv_frame records with no gap of more than 1 s. For each clip: the number of frames, the frame
period (time between two mv_frame records), total_us and develop_us (mean, 95th percentile, largest), how many
frames took longer than one frame period (33,367 us at 29.97 fps), the return values, and on CPU 1 the mv_enc
records in the same time span (handler microseconds, ART_SUB microseconds per second).
"""

import json
import sys
from collections import Counter

FRAME_US = 1_000_000 * 1001 / 30000          # 33,366.7 us


def stats(v):
    """Mean, 95th percentile and largest value of a list, as text."""
    if not v:
        return "-"
    s = sorted(v)
    return "mean %.0f  p95 %.0f  max %.0f" % (sum(s) / len(s), s[min(len(s) - 1, int(0.95 * len(s)))], s[-1])


def clips(frames):
    """Split mv_frame events into runs separated by more than 1 s."""
    out = []
    for e in frames:
        if out and e["session"] == out[-1][-1]["session"] and e["time_us"] - out[-1][-1]["time_us"] < 1_000_000:
            out[-1].append(e)
        else:
            out.append([e])
    return out


def main():
    """Print the report."""
    ev = json.load(open(sys.argv[1]))["events"]
    frames = [e for e in ev if e.get("event") == "mv_frame"]
    enc = [e for e in ev if e.get("event") == "mv_enc"]
    gaps = [e for e in ev if e.get("marker") == "gap"]
    if gaps:
        print("records lost:", ", ".join("cpu %s: %s" % (g.get("cpu"), g.get("count", g.get("lost"))) for g in gaps))
    for n, c in enumerate(clips(frames), 1):
        t0, t1 = c[0]["time_us"] - c[0]["args"]["total_us"], c[-1]["time_us"]
        total = [e["args"]["total_us"] for e in c]
        dev = [e["args"]["dev_ret"]["develop_us"] for e in c]
        period = [b["time_us"] - a["time_us"] for a, b in zip(c, c[1:])]
        late = sum(t > FRAME_US for t in total)
        print("clip %d (session %d): %d frames in %.2f s = %.2f per s" % (
            n, c[0]["session"], len(c), (t1 - t0) / 1e6, len(c) / max((t1 - t0) / 1e6, 1e-9)))
        print("  period_us   ", stats(period), "  periods > 1.5 frames: %d" % sum(p > 1.5 * FRAME_US for p in period))
        print("  total_us    ", stats(total), "  frames > %.0f us: %d" % (FRAME_US, late))
        print("  develop_us  ", stats([d for d in dev if d]), "  frames with no develop call: %d" % dev.count(0))
        print("  ret         ", dict(Counter(e["args"]["dev_ret"]["ret"] for e in c)))
        e1 = [e for e in enc if e["session"] == c[0]["session"] and t0 <= e["time_us"] <= t1 + 100_000]
        for kind in (0, 1):
            us = [e["args"]["enc"]["us"] for e in e1 if e["args"]["enc"]["kind"] == kind]
            if us:
                print("  cpu1 enc k%d  %d records, %.1f per frame;" % (kind, len(us), len(us) / len(c)), stats(us))
        art = sum(e["args"]["art_us"] for e in e1[1:])       # the first record's art_us has no start value
        if e1:
            print("  cpu1 ART_SUB %.0f us per s of clip (%.1f %% of one CPU)" % (
                art / max((t1 - t0) / 1e6, 1e-9), art / max(t1 - t0, 1) * 100))


if __name__ == "__main__":
    main()

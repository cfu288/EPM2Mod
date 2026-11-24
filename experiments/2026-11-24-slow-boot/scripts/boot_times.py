"""One line per session of a decoded log: start kind, GUI start, live view start, first screens.

Usage (from the repository root):
    uv run epm2mod log FILE.BIN --json > /path/to/log.json
    uv run python experiments/2026-11-24-slow-boot/scripts/boot_times.py /path/to/log.json [FIRST_SESSION_OF_BODY_B]

"cold" is a session whose first CPU 0 record has sequence number 0 (the ring was new: RAM was not kept), as
`epm2mod log` decides "cold start (new ring)"; "kept" is any other. found = the boot record's ring_found.
Times are ms after the timer's zero. GUI = first gui_state record, LV = first gui_state 0x5000
(ShootingCommon: live view starts). Recovered records count for the session that logged them.
"""

import json
import statistics
import sys
from collections import defaultdict

events = json.load(open(sys.argv[1]))["events"]
body_b = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
by_session: dict[int, list[dict]] = defaultdict(list)
for e in events:
    if "session" in e and e.get("cpu") == 0 and "event" in e:
        by_session[e["session"]].append(e)

rows = []
for s, evs in sorted(by_session.items()):
    boot = next((e for e in evs if e["event"] == "boot"), None)
    if boot is None:
        continue
    found = boot["args"].get("ring_found", boot["args"].get("session"))
    guis = [e for e in evs if e["event"] == "gui_state"]
    gui = guis[0]["time_us"] / 1000 if guis else None
    lv = next((e["time_us"] / 1000 for e in guis if int(e["args"]["state"], 16) == 0x5000), None)
    seq = " ".join(e["args"]["state"][-4:] for e in guis[:4])
    heap = next((e["time_us"] / 1000 for e in evs if e["event"] == "pk_heap_mode"), None)
    errs = sum(1 for e in evs if e["event"] == "fw_error" and e["args"]["code"] not in ("0x19000C02", "0x19000C03"))
    rows.append(
        dict(
            s=s,
            body="B" if s >= body_b else "A",
            kind="cold" if evs[0]["seq"] == 0 else "kept",
            found=found,
            boot=boot["time_us"] / 1000,
            heap=heap,
            gui=gui,
            lv=lv,
            seq=seq,
            errs=errs,
            build=boot.get("build", "")[:8],
            poweron=boot["args"].get("poweron", {}).get("raw", ""),
        )
    )


def fmt(v: float | None) -> str:
    return "-" if v is None else f"{v:7.0f}"


print("sess body kind found  boot_ms  heap_ms   gui_ms    lv_ms  errs build    poweron    first screens")
for r in rows:
    print(
        f"{r['s']:4} {r['body']:>4} {r['kind']:>4} {r['found']:5} {fmt(r['boot'])}  {fmt(r['heap'])}  {fmt(r['gui'])}"
        f"  {fmt(r['lv'])} {r['errs']:5} {r['build']} {r['poweron']} {r['seq']}"
    )

print()
print("medians of sessions that reached live view (ms): body kind build n gui lv")
groups: dict[tuple, list[dict]] = defaultdict(list)
for r in rows:
    if r["lv"] is not None and r["lv"] < 20000:
        groups[(r["body"], r["kind"], r["build"])].append(r)
for k, rs in sorted(groups.items()):
    print(
        *k,
        len(rs),
        f"gui {statistics.median(r['gui'] for r in rs):.0f} ({min(r['gui'] for r in rs):.0f}-{max(r['gui'] for r in rs):.0f})",
        f"lv {statistics.median(r['lv'] for r in rs):.0f} ({min(r['lv'] for r in rs):.0f}-{max(r['lv'] for r in rs):.0f})",
    )

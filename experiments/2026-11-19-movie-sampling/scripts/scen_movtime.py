"""Scenario check of the hooks of data/specs/log-movie-time.json, as S17 of experiments/2026-11-15-log/scripts/scen_log.py.

    uv run python experiments/2026-11-19-movie-sampling/scripts/scen_movtime.py PINNED_BLOCK0 PROBE_BLOCK0
    PINNED  block0_0100.bin of build/epm2mod-2026.11.19.BIN (tools/oetool.py unpack)
    PROBE   block0_0100.bin of build/debug-log-movie-time.BIN

Each hook runs alone, from its site to the first stock instruction after the replaced ones, with set registers and
the flags N Z C V set, on both images, in the order of one movie frame (entry, develop job, end) and then the CPU 1
hooks (ART_SUB, MOV_ENCODE twice). The replaced calls are stubs. Pass = the same registers at that instruction
(mdr left out where a call was replaced; the flags left out where the stock code sets them again: see FLAGS), the same
stub calls with the same arguments, the same memory outside the log's RAM and the probe's 32 bytes, and the records
of the dictionary with the expected values. The emulator has no sensor: this shows the routines' logic, not that the
firmware reaches the sites while recording.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
import scenario  # noqa: E402
from scenario import Scenario, diff_writes  # noqa: E402
from epm2mod.eventlog import decode, load_dictionary  # noqa: E402

RING0, LOG_END = 0x7E4F9000, 0x7E4FD320          # the log's RAM and the probe's 32 bytes at 0x7E4FD300
UNCACHED = 0x40000000
WORDS = load_dictionary(json.load(open(os.path.join(ROOT, "data", "logdict", "events.json"))))
JOB = 0x7D210000                                 # scratch for a0 (the job / message pointer)
# The flags at the stop are not compared for these hooks: the replaced instructions or the routine's own call set them
# (T_MVS: `add -512,sp` sets them, as stock; T_MVE: stock ends with `ret`; the others: the callee sets them).
FLAGS = {"MVS": True, "MVE": False, "DEV": False, "ART": False, "ENCA": False, "ENCB": False}

CASES = [   # label, start, stop, registers, stubs {addr: d0}, event or None
    ("MVS", 0x7E6C6E46, 0x7E6C6E4B, {}, {}, None),
    ("DEV", 0x7E6C7490, 0x7E6C7497, {"d0": 5921, "a0": 0x605B0248, "a1": 0x7E7FD372}, {0x7E6DABAF: 0}, None),
    ("MVE", 0x7E6C721D, 0x7E6C7222, {"d0": 0x123438FB}, {}, "mv_frame"),
    ("ART", 0x7E72CC54, 0x7E72CC5A, {"a2": JOB}, {0x7E72CD3E: 7}, None),
    ("ENCA", 0x7E6D55A7, 0x7E6D55AD, {"a2": JOB}, {0x7E6D5641: 0}, "mv_enc"),
    ("ENCB", 0x7E6D55AF, 0x7E6D55B5, {"a2": JOB}, {0x7E6D564D: 3}, "mv_enc"),
]


def ring_events(sc, before):
    """The records of the CPU 0 ring after record number `before`, decoded with the package's decoder."""
    magic, w = struct.unpack("<2I", sc.read(RING0 + UNCACHED, 8))
    recs = b"".join(sc.read(RING0 + UNCACHED + 32 + 16 * (i % 512), 16) for i in range(before, w))
    data = struct.pack("<4sBBBB8sIIII", b"EPLG", 1, 16, 0, 32, WORDS.build_id, before, w - before, 0, 1) + recs
    return [e for e in decode(data, WORDS) if "event" in e], w


def main():
    """Run the cases on both images and print one line per case."""
    pinned, probe = sys.argv[1:3]
    runs = {}
    for name, path in (("pinned", pinned), ("probe", probe)):
        sc = Scenario(path, name=name)
        sc.write(RING0 + UNCACHED, struct.pack("<5I", 0x314C5045, 0, 0, 0, 0) + b"\0" * 4 + struct.pack("<I", 0xFFFFFFFF))
        sc.write(0x7E4FD042 + UNCACHED, b"\x01")      # LOGON: the Debug Log row is On
        out, w = [], 0
        for label, start, stop, regs, stubs, want in CASES:
            for a, d0 in stubs.items():
                sc.stub(a, lambda sc_, g, d0=d0: {"d0": d0})
            g = dict({"psw": 0x0F, "d0": 0x1111, "d1": 0x2222, "d2": 0x3333, "d3": 0x4444, "a0": 0x7D215550,
                      "a1": 0x7D216660, "a2": 0x7D217770, "a3": 0x7D218880, "mdr": 0x7E500000, "lir": 0x51,
                      "lar": 0x52}, **regs)
            r = sc.piece(start, [stop], g, log_writes=scenario.RAM_AND_IMAGE)
            calls = [(pc, c["d0"], c["a0"], c["a1"]) for pc, n, c, ret in r.stubs if pc != stop]
            ev, w = ring_events(sc, w) if name == "probe" else ([], 0)
            out.append((label, r, calls, ev))
            for a in stubs:
                del sc._stubs[a]
        runs[name] = out
    ok_all = True
    for (label, ra, ca, _), (_, rb, cb, ev) in zip(runs["pinned"], runs["probe"]):
        want = [c[5] for c in CASES if c[0] == label][0]
        has_call = bool(cb)
        keys = [k for k in ("pc", "sp", "d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3", "lir", "lar", "mdr")
                if not (k == "mdr" and has_call)] + (["psw"] if FLAGS[label] else [])
        regs_ok = not ra.fault and not rb.fault and all(ra.regs[k] == rb.regs[k] for k in keys)
        dw = diff_writes(ra.writes, rb.writes, skip=[(RING0, LOG_END)])
        names = [e["event"] for e in ev]
        ev_ok = names == ([want] if want else [])
        if ev_ok and want == "mv_frame":
            a = ev[0]["args"]
            ev_ok = a["dev_ret"]["ret"] == "0x38FB" and a["total_us"] >= a["dev_ret"]["develop_us"]
        if ev_ok and want == "mv_enc":
            ev_ok = ev[0]["args"]["enc"]["kind"] == (1 if label == "ENCB" else 0)
        ok = regs_ok and ca == cb and not dw and ev_ok
        ok_all &= ok
        print("  %-5s %s: registers%s as pinned %s; stub calls as pinned %s; memory outside the log as pinned %s; "
              "records %s" % (label, "ok" if ok else "FAIL", " and flags" if FLAGS[label] else "", regs_ok, ca == cb,
                              not dw, [(e["event"], e["args"]) for e in ev] or "none"))
        if ra.fault or rb.fault:
            print("      fault: pinned %s, probe %s" % (ra.fault, rb.fault))
    print("RESULT: %s" % ("PASS" if ok_all else "FAIL"))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()

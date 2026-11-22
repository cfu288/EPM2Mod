"""Emulator check of pana-ring-probe: set_stat_pana 0x7E5234D7 and set_func_flag_pana 0x7E523495, called as their
callers call them (`call ...,[],0`), and the two parser sites of the packet windows (0x7E523A5B, 0x7E521343) run from
the site to the next stock instruction, on the pinned build and on the probe, with log-menu-3's real log_chg and
log_put. Research code.

    uv run python experiments/2026-11-22-pana-aperture-ring/scripts/emu_pana.py

Pass:
  * for every input (d0, flag byte 0x604F7F64): the probe leaves the same l_stat_pana / l_func_flag_pana, flag byte,
    return value d0 and registers d1-d3, a0-a3, sp as the pinned build;
  * the probe writes no RAM outside the variables, its gates (0x7E4FD0A8-0x7E4FD0B8), the CPU-0 ring and the stack;
  * with Debug Log On (LOGON 1): one record per call whose arg0 differs from the last one, none for a repeat, and the
    record's id and arguments as data/logdict/events.json says; with the row Off (LOGON 2): no record;
  * parser sites, for windows at every alignment: the probe leaves the same registers (d0 = stat as read, a0, sp, ...;
    not mdr, see window())
    as the pinned build and writes no RAM outside its keys, its timer words and the ring;
  * windows (Debug Log On; time passes by moving the stored time of the last pair): a record pair with the 16 window bytes for a new window, none
    for the same window, none for a change within 0.5 s of the last pair, the pair at the next packet after 0.5 s.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "emulator")]
import patchblock  # noqa: E402
import scenario  # noqa: E402
from scenario import Scenario  # noqa: E402

PS, PF = 0x7E5234D7, 0x7E523495
STAT, FUNC, FLAG, AV, LENSID = 0x604F88CE, 0x604F8888, 0x604F7F64, 0x604F658C, 0x604F67B0
RING0, PST = 0xBE4F9000, 0xBE4FD040
LOGON, GATES = PST + 2, (PST + 104, PST + 120)
REGS = {"d1": 0xD1D1D1D1, "d2": 0xD2D2D2D2, "d3": 0xD3D3D3D3, "a0": 0xA0A0A0A0, "a1": 0xA1A1A1A1,
        "a2": 0xA2A2A2A2, "a3": 0xA3A3A3A3}
EVENTS = {e["name"]: e["id"] for e in json.load(open(os.path.join(ROOT, "data/logdict/events.json")))["events"]}
PKA, PKB = (0x7E523A5B, 0x7E523A63, 0), (0x7E521343, 0x7E52134B, 3)    # site, stop, window start = a2 - this
BUF, KEYS, TIMES = 0x607F0000, (PST + 120, PST + 128), (0xBE4FD300, 0xBE4FD308)
FLAGS = (0x00, 0x01, 0x02, 0x03, 0x07, 0xFC, 0xFF)
VALUES = (0x0000, 0x0001, 0x0002, 0x0003, 0x1234, 0xFFFF)


def image(build):
    _, blk, _ = patchblock.patched_block0(json.load(open(os.path.join(ROOT, "data", "builds", build + ".json")))["specs"])
    os.makedirs(os.path.join(ROOT, "build", "pana-ring-probe"), exist_ok=True)
    p = os.path.join(ROOT, "build", "pana-ring-probe", build + ".block0.bin")
    open(p, "wb").write(blk)
    return p


def ring(sc):
    """The records of the CPU-0 ring as (id, arg0, arg1), oldest first."""
    w = sc.r32(RING0 + 4)
    if sc.r32(RING0) != 0x314C5045 or (w + sc.r32(RING0 + 24) + 1) & 0xFFFFFFFF:
        return []
    return [(sc.r16(RING0 + 32 + 16 * (i % 512)), sc.r32(RING0 + 40 + 16 * (i % 512)), sc.r32(RING0 + 44 + 16 * (i % 512)))
            for i in range(w)]


def one(sc, entry, d0, flag, logon):
    """One call; returns (state after, written addresses outside the stack and the expected areas)."""
    sc.w16(STAT, 0x5A5A); sc.w16(FUNC, 0x0003); sc.w8(FLAG, flag); sc.w16(AV, 0x0188); sc.w32(LENSID, 0x00010002)
    sc.w8(LOGON, logon)
    r = sc.call(entry, regs=dict(REGS, d0=d0), frame=(0, 0), log_writes=scenario.RAM)
    allowed = [KEYS, TIMES, (STAT, STAT + 2), (FUNC, FUNC + 2), (FLAG, FLAG + 1), (GATES[0], GATES[1]), (RING0, RING0 + 0x2020),
               (GATES[0] & 0x1FFFFFFF | 0x60000000, GATES[1] & 0x1FFFFFFF | 0x60000000)]
    stray = sorted({a for a, n, v, pc in r.writes if not any(lo <= a < hi for lo, hi in allowed)
                    and not (scenario.SP0 - 0x10000 <= a < scenario.SP0 + 0x100)})
    g = r.regs
    return (r.fault, sc.r16(STAT), sc.r16(FUNC), sc.r8(FLAG), g.get("d0"),
            tuple(g.get(k) for k in REGS), g.get("sp")), stray


def window(sc, site, win, at, logon):
    """Run a parser site with a2 -> stat; the 16 window bytes are at a2 - back. Returns (state, stray writes)."""
    _, stop, back = site
    a2 = BUF + at + back
    sc.w8(LOGON, logon)
    for i, b in enumerate(win):
        sc.w8(a2 - back + i, b)
    r = sc.piece(site[0], [stop], dict(REGS, d0=0x12345678, a2=a2, sp=0x7D0F0000, mdr=0x7E000001), log_writes=scenario.RAM)
    allowed = [KEYS, TIMES, (RING0, RING0 + 0x2020)]
    stray = sorted({a for a, n, v, pc in r.writes if not any(lo <= a < hi for lo, hi in allowed)
                    and not (0x7D0E0000 <= a < 0x7D0F0000)})
    g = r.regs
    # not mdr: the replayed call sets it to its return address in T_PKA/T_PKB, and both sites' next instructions are
    # `exthu d0` / `call set_stat_pana`, which sets mdr again before anything reads it
    return (r.fault, tuple(g.get(k) for k in ("d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3", "sp"))), stray


def words(win):
    return [int.from_bytes(bytes(win[i:i + 4]), "little") for i in range(0, 16, 4)]


def run(path, name):
    out, recs = {}, {}
    with Scenario(path, name=name) as sc:
        for entry in (PS, PF):
            for flag in FLAGS:
                for v in VALUES:
                    out[(entry, flag, v)] = one(sc, entry, v, flag, 2)       # Off: no record, pure behaviour
        wins = [[(17 * k + 31 * i) & 0xFF for i in range(16)] for k in range(4)]
        for site in (PKA, PKB):
            for at in range(4):
                for k, w in enumerate(wins):
                    out[(site[0], at, k)] = window(sc, site, w, at, 2)
        if name == "probe":
            for g in range(GATES[0], KEYS[1], 4):
                sc.w32(g, 0)
            sc.w32(RING0 + 4, 0); sc.w32(RING0 + 24, 0)                         # ring not valid: log_put starts one
            seq = [(PS, 0x0000), (PS, 0x0001), (PS, 0x0001), (PS, 0x0003), (PF, 0x0003), (PF, 0x0003), (PF, 0x0001)]
            for entry, v in seq:
                one(sc, entry, v, 0x03, 1)
            recs["on"] = ring(sc)
            for entry, v in ((PS, 0x0007), (PF, 0x0002)):
                one(sc, entry, v, 0x03, 2)
            recs["off"] = ring(sc)
            n0 = len(recs["off"])
            # The emulator's timer runs (a few microseconds per step): time passes in the check by moving the stored
            # time of the last pair up, since the code takes (stored - now) as the time since it.
            for site in (PKA, PKB):
                tw = TIMES[0] + (4 if site is PKB else 0)
                for w, dt, logon in ((wins[0], 10_000_000, 1), (wins[0], 10_000, 1), (wins[1], 10_000, 1),
                                     (wins[1], 580_000, 1), (wins[1], 100_000, 1), (wins[2], 1_000_000, 2)):
                    sc.w32(tw, sc.r32(tw) + dt)
                    window(sc, site, w, 1, logon)
            recs["pk"] = ring(sc)[n0:]
    return out, recs


def main():
    os.chdir(ROOT)
    pin, _ = run(image("peaking-mf"), "pinned")
    mf, recs = run(image("pana-ring-probe"), "probe")
    ok = True
    for key in sorted(pin):
        (got, stray), (ref, _) = mf[key], pin[key]
        good = got == ref and got[0] is None and not stray
        ok &= good
        if not good:
            print("NOT OK", "site %#x" % key[0], key[1:], "probe", got, "pinned", ref, "stray writes", [hex(a) for a in stray])
    n = sum(1 for k in pin if k[0] in (PS, PF))
    print("behaviour: %d calls of the two setters (%d inputs each) and %d runs of the two parser sites (4 alignments x 4 "
          "windows each), probe = pinned: %s" % (n, n // 2, len(pin) - n, ok))
    S, F = EVENTS["pana_stat"], EVENTS["pana_func"]
    want = [(S, 0x0188 << 16 | 0x0000, 0x03 << 16 | 0x0003),     # first value: the gate holds 0, arg0 0x01880000 differs
            (S, 0x0188 << 16 | 0x0001, 0x03 << 16 | 0x0003),     # stat changed
            (S, 0x0188 << 16 | 0x0003, 0x03 << 16 | 0x0003),     # repeat of 0x0001 gave nothing; 0x0003 changed
            (F, 0x0003, 0x00010002),                             # func: first value
            (F, 0x0001, 0x00010002)]                             # repeat of 0x0003 gave nothing
    for label, r in (("Debug Log On", recs["on"]), ("Debug Log Off", recs["off"])):
        good = r == want
        ok &= good
        print("%s: %d records %s -> %s" % (label, len(r), ["%d %#010x %#010x" % x for x in r], "ok" if good else "NOT OK"))
    P = EVENTS["pana_pk84_0"], EVENTS["pana_pk34_0"]
    wins = [[(17 * k + 31 * i) & 0xFF for i in range(16)] for k in range(4)]
    want = []
    for first in P:
        for w in (wins[0], wins[1]):
            x = words(w)
            want += [(first, x[0], x[1]), (first + 1, x[2], x[3])]
    good = recs["pk"] == want
    ok &= good
    print("windows: %d records %s -> %s" % (len(recs["pk"]), ["%d %#010x %#010x" % x for x in recs["pk"]], "ok" if good else "NOT OK"))
    print("RESULT", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

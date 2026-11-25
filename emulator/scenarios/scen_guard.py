"""Scenario tests of the save guard (NOTES.md section 18). Uses emulator/liveview.py.

    python3 scen_guard.py SCENARIO NAME=BLOCK0 [NAME=BLOCK0 ...]
    SCENARIO: s19 ... s26 or all. Each image runs alone; one line per image says PASS or FAIL.
    An image whose NAME starts with "pinned" is judged as a build without the guard (use "pinned-fast", not "pinned":
    scen_peaking.py gives an image of that exact name no request).
    The block-0 files are `block0_0100.bin` of `python3 tools/oetool.py unpack build/NAME.BIN /tmp/scratch/NAME`.

What is modelled (the rig runs no capture: no TAKE_*, REC_* task, no development job):
  - "a photo is being developed": the real heap allocator 0x7E578D43 is called the way the still code calls it
    (the call at 0x7E70BE3B, 3,735,552 bytes) and the block is kept for some frames, then freed with the real
    0x7E578EBC. Which blocks the still pipeline holds, and for how long, is not known from the camera;
  - the capture itself: the mov commands Through End and Through Start, and one call of the heap-mode chooser
    the way api_rec_Notify_Rec_Mode_Change calls it (0x7E68AE4A);
  - heap mode 2 for a film look: setting 10401 = 1 (the camera log shows mode 2 there; without it the rig's
    chooser gives mode 0, a heap that gives out nothing);
  - the ART task answers at once (no pre-emption). So the firmware error 0x34000002 of the camera log (an art
    "end" command that finds the art session not started) does not show here. What shows is the state that leads
    to it: the heap re-divided under a block in use, the art buffers refused in every frame, and an art
    end / start pair in every frame.

S19  MF Assist asked for while a photo is being developed (the camera fault of 2026-11-16).
S20  The reverse order: a capture while the lines show; the request still set when live view comes back.
S21  MF Assist ends while another owner has a block in the pool of mode 1.
S22  A movie ends (movie flag 0x605B039C) while a block is in use and the request is set.
S23  Three frames of an interval sequence with the request set all the time.
S24  Back from playback / RAW Data Edit: the heap mode set directly (0x7E578C60, as 0x7E948E91 does), a block in use.
S25  Sleep and wake (Through End, Through Start) with the request set and no block in use: lines at once.
S26  The event pk_guard of the debug builds (images whose NAME starts with "debug"; others are skipped): holds as in
     S19 with focus-ring events (the first two instructions of the handler 0x7EB7DE46, where the probe is); the
     records with id 262 are read from the CPU0 ring in the emulator's memory.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scen_peaking.py")).read()
assert _src.rstrip().endswith("\nmain()")
_sp = {"__file__": os.path.join(os.path.dirname(os.path.abspath(__file__)), "scen_peaking.py"), "__name__": "scen_peaking"}
exec(compile(_src.rstrip()[:-len("main()")], "scen_peaking.py", "exec"), _sp)
open_lv, request, anomalies = (_sp[k] for k in ("open_lv", "request", "anomalies"))
from liveview import CMD_THROUGH_END, CMD_THROUGH_START, HEAP_MODE, HEAP_FLAGS  # noqa: E402

L, R, L2, C = 0x602BE8C4, 0x602BE8C5, 0x602BE8C6, 0x602BE8C7
TAG, WHITE, RED = 0x8971, 3, 2
FILM = 107                       # a film slot (Cross Process I entry, art code 85: the look of the second camera crash)
MOVIE_FLAG = 0x605B039C
POOL1, POOL02 = 0x602AC458, 0x602AC45C
ALLOC, ALLOC_SITE, FREE, FREE_SITE = 0x7E578D43, 0x7E70BE3B, 0x7E578EBC, 0x7E70BE89
CHOOSER, CHOOSER_SITE, SET_MODE, SET_MODE_SITE = 0x7E714833, 0x7E68AE4A, 0x7E578C60, 0x7E948E91
ART_CMD, ART_STATE = 0x7E72A14B, 0x605C1930
OUT = print


class Run:
    def __init__(self, path, name, colour=WHITE, pm=FILM):
        self.lv = open_lv(path, name, pm)
        self.sc = self.lv.sc
        self.lv.settings[TAG] = colour
        self.lv.settings[10401] = 1
        self.bad, self.cmds, self.name = [], [], name
        self.guard = not name.startswith("pinned")
        self.sc.probe(ART_CMD, lambda sc, g: self.cmds.append((sc.r16(sc.r32(g["a0"] + 12)), sc.r8(ART_STATE))), "art command")
        self.note(self.lv.start(), "start")
        for _ in range(2):
            self.frame()

    def close(self):
        self.lv.close()

    def used(self, pool):
        p = self.sc.r32(pool)
        return (self.sc.r16(p + 16) - self.sc.r16(p + 76)) & 0xFFFF

    def state(self):
        sc = self.sc
        return "L=%d R=%d L2=%d | heap mode %d, flags %d, in use: pool of mode 1 %d, pool of modes 0/2 %d" % (
            sc.r8(L), sc.r8(R), sc.r8(L2), sc.r16(HEAP_MODE), sc.r16(HEAP_FLAGS), self.used(POOL1), self.used(POOL02))

    def note(self, f, what, expect_lines=None):
        ev = [e for e in f.events if e[0] in ("heap re-partition", "error report") and not e[1].startswith("0 live")]
        bad = anomalies(self.lv, f)
        cmds, self.cmds = self.cmds, []
        if any(c == 4 and st != 2 for c, st in cmds) or any(c == 3 and st != 0 for c, st in cmds):
            bad.append("an art command met the wrong session state")
        gains = sorted(set(self.lv.seen["gain2"]))
        self.lv.seen["gain2"], self.lv.seen["expose7"] = [], []
        lines = bool(gains) and f.state["art_record"] == 0x2A3
        if expect_lines is not None and lines != expect_lines:
            bad.append("lines %s, expected %s" % (lines, expect_lines))
        OUT("  [%s] %-46s %s | picture %s, lines %s%s, art commands %s%s" % (
            self.name, what + ":", self.state(), f.state["picture"], lines,
            " (pass 9 gain %s)" % ", ".join("0x%04X" % g for g in gains) if gains else "",
            ",".join(str(c) for c, _ in cmds) or "-", "".join("\n        %s: %s" % e for e in ev)))
        for b in bad:
            OUT("        ANOMALY: " + b)
        self.bad += ["%s: %s" % (what, b) for b in bad]
        return f

    def frame(self, what="frame", lines=None):
        return self.note(self.lv.frame(), what, lines)

    def ask(self, on):
        request(self.lv, on)

    def call(self, entry, regs, site, what):
        r = self.sc.call(entry, regs, frame=self.sc.frame_at(site), label=what)
        ev, self.lv.events = self.lv.events, []
        assert not r.fault, r.fault
        return r, ev

    def alloc(self, size=3735552, what="the still code takes a block"):
        r, ev = self.call(ALLOC, {"d0": size, "d1": 0, "a0": 0x7E851EAA, "a1": 159}, ALLOC_SITE, "still alloc")
        err = [d for k, d in ev if k == "error report"]
        OUT("  [%s] %s: %d bytes -> 0x%08X%s | %s" % (self.name, what, size, r.regs["d0"],
                                                 " REFUSED, " + err[0] if err else "", self.state()))
        if not r.regs["d0"]:
            self.bad.append(what + ": the block was refused")
        return r.regs["d0"]

    def free(self, p):
        self.call(FREE, {"d0": p}, FREE_SITE, "still free")
        self.lv.freed.pop(p, None)       # the two pools share the memory: a later art buffer may lie there, rightly
        OUT("  [%s] the block is freed | %s" % (self.name, self.state()))

    def chooser(self, what="the rec code calls the heap-mode chooser"):
        _, ev = self.call(CHOOSER, {}, CHOOSER_SITE, "chooser")
        part = [d for k, d in ev if k == "heap re-partition" and not d.startswith("0 live")]
        OUT("  [%s] %s | %s%s" % (self.name, what, self.state(),
                                 "".join("\n        ANOMALY: heap re-divided under %s" % d for d in part)))
        self.bad += ["chooser: heap re-divided under live blocks"] * len(part)

    def capture(self):
        """Through End, the rec code's chooser call, a block for the development, Through Start."""
        self.note(self.lv.command(CMD_THROUGH_END, label="Through End"), "capture: Through End")
        self.chooser()
        p = self.alloc()
        self.note(self.lv.command(CMD_THROUGH_START, label="Through Start"), "capture: Through Start")
        return p

    def held(self):
        """A frame in which the guard should hold the latch: L = 2, the heap still in mode 2."""
        if self.guard and (self.sc.r8(L) != 2 or self.sc.r16(HEAP_MODE) != 2):
            self.bad.append("held frame: L or the heap mode is not as the guard should leave it")


def verdict(tag, runs):
    ok = True
    for name, bad in runs:
        OUT("  %s RESULT [%s]: %s" % (tag, name, "PASS" if not bad else "FAIL: " + "; ".join(sorted(set(bad)))[:700]))
        ok &= not bad
    return ok


def each(images, fn):
    runs = []
    for name, path in images:
        r = Run(path, name)
        try:
            fn(r)
        finally:
            r.close()
        runs.append((name, r.bad))
    return runs


def s19(images):
    OUT("S19. MF Assist asked for while a photo is being developed. Film slot, Peaking White. Order of the camera log:")
    OUT("     capture, live view back, the development still holds a block, the focus ring turns, the block is freed later.")

    def go(r):
        p = r.capture()
        r.frame("live view, development goes on", lines=False)
        r.ask(True)
        for i in range(3):
            r.frame("ring turned, block in use, frame %d" % (i + 1), lines=False)
            r.held()
        r.free(p)
        r.frame("block freed, frame 1", lines=True)
        r.frame("block freed, frame 2", lines=True)
        r.ask(False)
        r.frame("ring stopped", lines=False)
        r.frame("ring stopped, frame 2", lines=False)
    return verdict("S19", each(images, go))


def s20(images):
    OUT("S20. A capture while the lines show. (a) MF Assist has ended when live view comes back; (b) the request is")
    OUT("     still set (the state object did not clear it) and the development holds a block.")

    def go(r):
        r.ask(True)
        r.frame("lines on", lines=True)
        r.frame("lines on", lines=True)
        r.ask(False)                                   # the capture ends MF Assist (inferred, NOTES 12.2); L stays 1
        p = r.capture()
        if r.used(POOL1) or r.sc.r16(HEAP_FLAGS) & 2:
            r.bad.append("capture: the pool of mode 1 is in use or a switch is pending")
        r.frame("(a) live view back, no request", lines=False)
        r.free(p)
        r.frame("(a) block freed", lines=False)
        r.ask(True)
        r.frame("lines on again", lines=True)
        p = r.capture()                                # (b) R is left at 1
        for _ in range(2):
            r.frame("(b) live view back, request set, block in use", lines=False)
            r.held()
        r.free(p)
        r.frame("(b) block freed", lines=True)
    return verdict("S20", each(images, go))


def s21(images):
    OUT("S21. MF Assist ends while another owner has a block in the pool of mode 1 (it took it while the lines showed).")

    def go(r):
        r.ask(True)
        r.frame("lines on", lines=True)
        p = r.alloc(what="another owner takes a block while the lines show")
        r.frame("lines on, block in use", lines=True)
        r.ask(False)
        r.frame("ring stopped, block in use", lines=False)
        r.frame("frame 2", lines=False)
        q = r.alloc(1000000, "the owner takes a second block")
        r.frame("frame 3", lines=False)
        if q:
            r.free(q)
        r.free(p)
        r.frame("blocks freed", lines=False)
        r.chooser("the next chooser call (a capture, a look change)")
        if r.sc.r16(HEAP_MODE) != 2 or r.sc.r16(HEAP_FLAGS) & 2:
            r.bad.append("after the blocks are freed the chooser does not give mode 2")
        r.ask(True)
        r.frame("lines on again", lines=True)
    return verdict("S21", each(images, go))


def s22(images):
    OUT("S22. Movie: the request is set while a movie records (flag 0x605B039C = 1: the latch refuses, as before), and")
    OUT("     the movie stops while a block is in use.")

    def go(r):
        r.sc.w8(MOVIE_FLAG, 1)
        p = r.alloc(what="a block is taken during the movie")
        r.ask(True)
        r.frame("movie records, request set", lines=False)
        if r.sc.r8(L) != 0:
            r.bad.append("L is not 0 in a movie")
        r.sc.w8(MOVIE_FLAG, 0)
        r.frame("movie stopped, block in use", lines=False)
        r.held()
        r.frame("frame 2", lines=False)
        r.free(p)
        r.frame("block freed", lines=True)
    return verdict("S22", each(images, go))


def s23(images):
    OUT("S23. Interval sequence: three captures, the request set all the time (the ring is turned between the frames).")

    def go(r):
        r.ask(True)
        r.frame("lines on", lines=True)
        for n in range(3):
            p = r.capture()
            r.frame("frame %d of the sequence: live view back, block in use" % (n + 1), lines=False)
            r.held()
            r.frame("block in use", lines=False)
            r.free(p)
            r.frame("block freed", lines=True)
            r.frame("lines on", lines=True)
    return verdict("S23", each(images, go))


def s24(images):
    OUT("S24. Back from playback or RAW Data Edit: Through End, the heap mode set directly to 2 as play_rec_raw_edit does,")
    OUT("     a block in use, Through Start, the ring turns at once.")

    def go(r):
        r.note(r.lv.command(CMD_THROUGH_END, label="Through End"), "to playback: Through End")
        r.call(SET_MODE, {"d0": 2}, SET_MODE_SITE, "set mode")
        p = r.alloc(what="the edit code takes a block")
        r.note(r.lv.command(CMD_THROUGH_START, label="Through Start"), "back: Through Start")
        r.ask(True)
        r.frame("ring turned, block in use", lines=False)
        r.held()
        r.frame("frame 2", lines=False)
        r.free(p)
        r.frame("block freed", lines=True)
    return verdict("S24", each(images, go))


def s25(images):
    OUT("S25. Sleep and wake with the request set and no block in use: the guard is not in the way.")

    def go(r):
        r.ask(True)
        r.frame("lines on", lines=True)
        r.note(r.lv.command(CMD_THROUGH_END, label="Through End"), "sleep: Through End")
        r.note(r.lv.command(CMD_THROUGH_START, label="Through Start"), "wake: Through Start")
        r.frame("first frame after wake", lines=True)
        r.frame("frame 2", lines=True)
        r.ask(False)
        r.frame("ring stopped", lines=False)
    return verdict("S25", each(images, go))


RING0, EV_GUARD = 0xBE4F9000, 262


def ring(sc, event):
    import struct
    magic, w = struct.unpack("<2I", sc.read(RING0, 8))
    if magic != 0x314C5045:
        return []
    rows = [struct.unpack("<HHIII", sc.read(RING0 + 32 + 16 * (n % 512), 16)) for n in range(max(0, w - 512), w)]
    return [(r[3] & 0xFFFF, r[3] >> 16, r[4]) for r in rows if r[0] == event]


RING_SITE, RING_NEXT = 0x7EB7DE46, 0x7EB7DE4D      # rcvStartMFAssistIn_MFAssistOn: the hook of the probe


def ring_event(r):
    """A focus-ring event while MF Assist is on: the first two instructions of the handler, where the probe is."""
    regs = {"a0": 0x7D500000, "d0": 0x11111111, "d1": 0x22222222, "a1": 0x7D500040, "d2": 0x33333333, "d3": 0x44444444,
            "a2": 0x7D500080}
    x = r.sc.piece(RING_SITE, [RING_NEXT], regs)
    assert not x.fault, x.fault
    want = dict(regs, a3=regs["a0"], d0=0x7EC8ABB1)
    if any(x.regs[k] != v for k, v in want.items()):
        r.bad.append("ring event: a register is not as the stock instructions leave it")
    return ring(r.sc, EV_GUARD)


def s26(images):
    OUT("S26. Event pk_guard (id 262): (heap mode, mode at the last allocation, units in use) of each record.")
    images = [(n, p) for n, p in images if n.startswith("debug")]

    def go(r):
        r.ask(True)
        r.frame("lines on", lines=True)
        got = ring_event(r)
        OUT("  [%s] ring event while the lines show: records %s" % (r.name, got))
        if got:
            r.bad.append("pk_guard: a record without a hold")
        r.ask(False)
        p = r.capture()
        r.frame("live view, development goes on", lines=False)
        r.ask(True)
        r.frame("ring turned, block in use, frame 1", lines=False)
        r.held()
        units = r.used(POOL02)
        got = ring_event(r)
        r.frame("frame 2", lines=False)
        got2 = ring_event(r)
        OUT("  [%s] two ring events in the hold: records %s, then %s" % (r.name, got, got2))
        if got != [(2, 2, units)] or got2 != got:
            r.bad.append("pk_guard: not one record (2, 2, %d) for the hold" % units)
        r.free(p)
        r.frame("block freed", lines=True)
        got = ring_event(r)
        p = r.capture()                                 # the request stays set: a second hold
        r.frame("second capture, block in use", lines=False)
        r.held()
        got2 = ring_event(r)
        OUT("  [%s] ring event after the hold: %d record(s); ring event in a second hold: %d record(s)" % (r.name, len(got), len(got2)))
        if len(got) != 1 or len(got2) != 2 or got2[1] != (2, 2, r.used(POOL02)):
            r.bad.append("pk_guard: the second hold did not give one more record")
        r.free(p)
        r.frame("block freed", lines=True)
    return verdict("S26", each(images, go)) if images else True


def main():
    which = sys.argv[1]
    images = [a.split("=", 1) for a in sys.argv[2:]]
    table = {"s19": s19, "s20": s20, "s21": s21, "s22": s22, "s23": s23, "s24": s24, "s25": s25, "s26": s26}
    ok = True
    for k, fn in table.items():
        if which in (k, "all"):
            ok &= fn(images)
            OUT("")
    sys.exit(0 if ok else 1)


main()

"""Scenario tests of the focus-peaking builds (NOTES.md section 13). Uses emulator/liveview.py.

    python3 scen_peaking.py SCENARIO PINNED_BLOCK0 NAME=PATCHED_BLOCK0 [NAME=PATCHED_BLOCK0 ...]
    SCENARIO: s1 s2 s3 s4 s5 or all. The block-0 files come from emulator/patchblock.py ... -o /tmp/scratch/x.block0.bin
    A NAME that starts with "direct-1" gets the request the way direct-1 sets it (R and the stock word 0x602B0DA8);
    every other patched image gets it through its own hook at entryMfAssistOn.

Every scenario runs the pinned image and each patched image through the same steps and prints what differs.
PINNED_BLOCK0 is the reference: tools/checks.py gives the stock firmware, so "pinned" in the texts below is stock.

S1 compares what must not change with the request clear: the device accesses (every write: the output), the RAM
that the stock firmware defines, the stock instructions that run, the mov state. What the mod does on purpose is
stated and checked exactly: writes to its own RAM (MOD_RAM), reads of the log's timer from its own code, stock
instructions that its patches overwrote, a stock return after a hook site, the instructions of S1_SKIPPED, a 0
written to the flag bytes L, R and L2, and the words of S1_RESIDUE with their writer and values. Any other
difference fails. S1 also fails when the reference gives no picture or does not reach pass 9 in Key Line, and S2
when the reference gives no picture: a comparison with nothing proves nothing.

Exit status 1 when a scenario fails for a patched image: S1 "DIFFERENCES FOUND", S2 "NO PICTURE ..." or "anomalies",
S3 an anomaly, S4 "LEFT SET", S5 "DIFFERS from pinned". Each such RESULT line starts its text with FAIL.
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import scenario  # noqa: E402
from scenario import RAM_AND_IMAGE, diff_pcs, diff_writes, fmt_funcs, patch_ranges  # noqa: E402
from liveview import LiveView, CMD_THROUGH_END, HEAP_MODE, MOV_STATE  # noqa: E402

L, R, L2, MFA = 0x602BE8C4, 0x602BE8C5, 0x602BE8C6, 0x602B0DA8
PM, ART_TYPE = 38017, 17601                     # settings: Picture Mode; art filter type (1 = type I, 2 = type II)
NATURAL, KEY_LINE = 2, 119
FILM = {107: "film slot (Cross Process I entry, class 1)", 100: "film slot (Pop Art I entry, class 1)",
        103: "film slot (Light Tone entry, class 1)"}
EFFECT = {113: "Soft Focus (class 3)", 104: "Grainy Film (class 4)", 108: "Gentle Sepia (class 4)"}
# Dramatic Tone (109) is left out: its art passes wait for a task that the rig does not run (pinned gives no picture).
ENTRY_ON, ENTRY_OFF = 0x7EB7D46C, 0x7EB7D43B    # CmpSts_MfAssist::entryMfAssistOn / entryMfAssistOff
PASS9_GAIN, PASS7_EXPOSE = 0x7E72676D, 0x7E726428   # stock instructions after hooks K and J
OUT = print


MOD_RAM = (0x7E4C9800, 0x7E4FE000)
LOG_TIMER = 0x98900074  # timer channel 9, the time of the Debug Log's records (docs/reference/logging.md)
# Stock RAM words that hold stack residue in the stock firmware too, so that the mod's use of the stack changes them
# and no defined state with it. Each one is an exact expectation; any other differing word fails S1.
#   0x602A4954: word 37 of the 49-word Key Line parameter block that 0x7E6CDA36 copies to the buffer of
#   (0x605B0AF4). The block is a local of the caller, and word 37 is not written between its allocation and the
#   copy: in the stock firmware it holds what an earlier callee left on the stack (frame 1: a stack address,
#   0x7D0EFBD4; frame 2: 0 from 0x7E6CFFB6). With the Debug Log's probes the last residue is a register that
#   log_chg saved (0x7E4C9514 writes 0x605B1CF0 there). Found 2026-11-25 with a write log of the stack word.
#   The expectation is exact (stated_ram): each write to the word is the 4-byte write of the copy 0x7E6CDA36, as
#   often as in the reference, and its value is the reference's or the saved register 0x605B1CF0.
S1_RESIDUE = {0x602A4954: (0x7E6CDA36, 0x605B1CF0)}
# Stock instructions that do not run in the build although they are not overwritten, each with its reason:
#   0x7E56C6AB, the branch after the compare chain of the colour-matrix stage. The hook at 0x7E56C6A5 (6 bytes,
#   stock-films-structure-3) sends the chain to the routine CHAIN, which comes back at 0x7E56C6AD or 0x7E56C6B8
#   (gen/stock-films/structure.py, MATRIX_STOCK_REST, MATRIX_STOCK_70), never at this branch.
S1_SKIPPED = (0x7E56C6AB,)
BASE = 0x7E421020


def is_return(image, pc):
    """True when the stock instruction at pc is a return: ret (0xDF), retf (0xDE) or rets (0xF0 0xFC)."""
    at = pc - BASE
    return image[at] in (0xDF, 0xDE) or image[at:at + 2] == b"\xf0\xfc"


def _fold(a):
    return a & 0x3FFFFFFF | 0x40000000 if a & 0x80000000 else a


def stated_ram(dw, wa, wb):
    """Take out of the differing bytes dw what the request-clear build may do to stock RAM, each checked exactly:
    - the flag bytes L, R and L2: the build may write 0 to them (the request is clear), nothing else;
    - the words of S1_RESIDUE: see there.
    Every byte that is left is a difference."""
    dw = dict(dw)
    for a in (L, R, L2):
        if dw.get(a) == (None, 0):
            del dw[a]
    for word, (copy, residue) in S1_RESIDUE.items():
        base = [(s, v, pc) for a, s, v, pc in wa if _fold(a) < word + 4 and _fold(a) + s > word]
        mine = [(s, v, pc) for a, s, v, pc in wb if _fold(a) < word + 4 and _fold(a) + s > word]
        exact = len(base) == len(mine) and all(m[0] == 4 and m[2] == copy and b[2] == copy and m[1] in (b[1], residue)
                                               for b, m in zip(base, mine))
        if exact:
            for a in range(word, word + 4):
                dw.pop(a, None)
    return dw


def _self_check_ram():
    """stated_ram on made-up write logs: the reviewer's mutations C and E still differ."""
    word, copy = 0x602A4954, 0x7E6CDA36
    stock = [(0xA02A4954, 4, 0, copy)]
    diff = lambda value: {word + i: (0, (value >> 8 * i) & 0xFF) for i in range(4) if (value >> 8 * i) & 0xFF}  # noqa: E731
    assert stated_ram(diff(0x605B1CF0), stock, [(0xA02A4954, 4, 0x605B1CF0, copy)]) == {}
    assert stated_ram(diff(0x11223344), stock, [(0xA02A4954, 4, 0x11223344, copy)])  # another value
    assert stated_ram(diff(0x605B1CF0), stock, [(0xA02A4954, 4, 0x605B1CF0, 0x7E4C9000)])  # another writer
    assert stated_ram(diff(0x605B1CF0), stock, stock + [(0x602A4954, 4, 0x605B1CF0, copy)])  # one write more
    assert stated_ram({L2: (None, 0)}, [], []) == {}
    assert stated_ram({L2: (None, 0x44)}, [], [])  # a flag byte set with the request clear
    assert stated_ram({L2 + 1: (None, 0)}, [], [])  # a neighbour of the flag bytes


_self_check_ram()


def device_same(base, patched, new):
    """True when the build's device accesses are the reference's, but for reads of the log's timer from the mod's
    new code (ranges ``new``). Every write is the same, in the same order, with the same value: the output. Every
    other read is the same too."""
    extra = lambda m: m[0] == "r" and m[1] == LOG_TIMER and m[4] is not None and any(lo <= m[4] < hi for lo, hi in new)  # noqa: E731
    return [m[:4] for m in base] == [m[:4] for m in patched if not extra(m)]


def _self_check():
    """device_same on made-up accesses: only a read of the log's timer from new code is no difference."""
    new, base = [(0x7E4C9000, 0x7E4C9800)], [("w", 0x98000010, 5, 4, 0x7E700000), ("r", 0x98000020, 0, 4, 0x7E700004)]
    timer = ("r", LOG_TIMER, 0x3FFFFFFB, 4, 0x7E4C90EA)
    assert device_same(base, base + [timer], new)
    assert not device_same(base, base + [("r", LOG_TIMER, 1, 4, 0x7E700008)], new)  # the timer, read by stock code
    assert not device_same(base, base + [("r", 0x98000024, 0, 4, 0x7E4C90EA)], new)  # another register
    assert not device_same(base, base + [("w", LOG_TIMER, 0, 4, 0x7E4C90EA)], new)  # a write
    assert not device_same(base, [("w", 0x98000010, 6, 4, 0x7E700000), base[1]], new)  # another value written


_self_check()
FAILED = []


def fail(text):
    """Note a failed result and return its text with FAIL before it. None: the reference's own result, which is
    printed and not counted."""
    if text is None:
        return ""
    FAILED.append(text)
    return "FAIL: " + text.lstrip() if text else "FAIL: "


def is_d1(name):
    return name.startswith("direct-1")


def open_lv(path, name, pm, art_type=1, log=False):
    lv = LiveView(path, name=name, log_writes=RAM_AND_IMAGE if log else ())
    lv.settings[PM] = pm
    lv.settings[ART_TYPE] = art_type
    lv.seen = {"gain2": [], "expose7": []}
    lv.sc.probe(PASS9_GAIN, lambda sc, g: lv.seen["gain2"].append(g["d0"] & 0xFFFF), "pass 9 gain")
    lv.sc.probe(PASS7_EXPOSE, lambda sc, g: lv.seen["expose7"].append(sc.r8(g["a0"] + 79)), "pass 7 ucExpose")
    return lv


def request(lv, on):
    """Set or clear the peaking request as the build's own hook does."""
    sc = lv.sc
    if lv.sc.name == "pinned":
        return "pinned: no request byte"
    if is_d1(lv.sc.name):
        sc.w8(R, 1 if on else 0)
        sc.w32(MFA, 1 if on else 0)
        return "direct-1: R and the stock word 0x602B0DA8 written as startMfAssist / endMfAssist leave them"
    a = ENTRY_ON if on else ENTRY_OFF
    r = sc.piece(a, [a + 7], {"a0": 0x7D500000})
    assert not r.fault and sc.r8(R) == (1 if on else 0), r.fault
    return "R set by the hook at 0x%08X (ran %d pcs, new code: %s)" % (a, len(r.pcs), fmt_funcs(p for p in r.pcs if p >= 0x7EB80000))


def flags(lv):
    return "L=%d R=%d L2=%d" % (lv.sc.r8(L), lv.sc.r8(R), lv.sc.r8(L2))


def show(lv, f, events=("heap alloc", "heap free", "heap set mode", "heap re-partition", "error report")):
    OUT("  [%s] %s | %s" % (lv.sc.name, f.summary(), flags(lv)))
    OUT("      path: " + ", ".join(f.path()))
    ev = [e for e in f.events if e[0] in events]
    for k, d in ev[:14]:
        OUT("      %s: %s" % (k, d))
    if len(ev) > 14:
        OUT("      ... %d more heap events" % (len(ev) - 14))
    prints = sorted(set(d for k, d in f.events if k == "mov error print"))
    if prints:
        OUT("      mov error prints: " + "; ".join(prints))
    if lv.seen["gain2"] or lv.seen["expose7"]:
        OUT("      Key Line pass 9 usGain2 = %s; pass 7 ucExpose = %s" % (
            sorted(set("0x%04X" % g for g in lv.seen["gain2"])), sorted(set(lv.seen["expose7"]))))
        lv.seen["gain2"], lv.seen["expose7"] = [], []
    for s in f.stale[:3]:
        OUT("      STALE ADDRESS to device 0x%08X: value 0x%08X by pc 0x%08X, in freed block 0x%08X+%d" % s)
    for x in f.faults:
        OUT("      FAULT " + x)
    notes = sorted(set(n for r in f.results for n in r.notes))
    if notes:
        OUT("      notes: " + "; ".join(notes))


def anomalies(lv, f):
    """Things a healthy frame does not show."""
    out = []
    s = f.state
    if f.faults:
        out.append("fault")
    if s["alloc_error"]:
        out.append("art buffers refused (alloc error)")
    if f.label.startswith("frame") and not s["picture"]:
        out.append("no picture")
    for k, d in f.events:
        if k == "heap re-partition" and not d.startswith("0 live"):
            out.append("heap re-partitioned under live blocks (%s)" % d.split(":")[0])
        if k == "heap free" and "NOT A LIVE" in d:
            out.append("free of a block that is not live")
        if k == "error report":
            out.append("firmware error report " + d)
    if f.stale:
        out.append("%d device writes of addresses in freed blocks" % len(f.stale))
    if s["art_record"] == 0x2A3 and s["heap_mode"] != 1 and f.label.startswith("frame"):
        out.append("art record is Key Line but heap mode is %d" % s["heap_mode"])
    return out


def stubbed_note(lv):
    OUT("  real code ran: static constructors, 12 module inits, tasks %s." % ", ".join(lv.tasks))
    OUT("  stubbed: device registers (writes dropped, reads 0), uITRON services (emulator/osmodel.py), IMG job-done")
    OUT("  waits (met at once), settings getter (ids not set read 0), white-balance module, CPU cache control, float multiply.")


# ------------------------------------------------------------------------------------------------ S1
def s1(pinned, patched):
    OUT("S1. Live-view frames with the request clear: patched against pinned (writes to all memory but the harness")
    OUT("    stacks, and executed pcs). Picture Mode Natural and ART Key Line. Art type setting 17601 = 1.")
    base_img = open(pinned, "rb").read()
    ok_all = True
    for pm, pm_name in ((NATURAL, "Natural"), (KEY_LINE, "Key Line")):
        runs = {}
        for name, path in [("pinned", pinned)] + patched:
            with open_lv(path, name, pm, log=True) as lv:
                lv.start()
                fs = [lv.frames[-1]] + [lv.frame() for _ in range(3)]
                runs[name] = (fs, [flags(lv)], open(path, "rb").read())
                if pm == KEY_LINE and name == "pinned" and not lv.seen["gain2"]:
                    ok_all = False
                    OUT("  Key Line: pass 9 did not run in the reference: the rig does not reach the art passes")
                if name == "pinned":
                    for f in fs:
                        show(lv, f, events=())
                    stubbed_note(lv)
        bfs = runs["pinned"][0]
        for name, _ in patched:
            fs, fl, img = runs[name]
            new, hooks = patch_ranges(base_img, img)
            for k, (fb, fp) in enumerate(zip(bfs, fs)):
                wa, wb = fb.writes, fp.writes
                same_seq = [(a, s, v) for a, s, v, _ in wa] == [(a, s, v) for a, s, v, _ in wb]
                # Not a difference: the mod's own RAM, the gap between the kernel range and segment 1 that the stock
                # firmware never writes (the Debug Log's state block is there: docs/dev/load-order.md, section 4, RAM).
                dw = diff_writes(wa, wb, skip=[MOD_RAM])
                dw = stated_ram(dw, wa, wb)
                flagw = sorted(set((a, v) for a, s, v, _ in wb if L <= a <= L2))
                d = diff_pcs(fb.pcs, fp.pcs, new, hooks)
                # a stock return right after a hook site, which the routine replaces with its own return (hooks A, B),
                # and the stock instructions of S1_SKIPPED
                rets = [p for p in d["only_base"] if p in S1_SKIPPED or
                        any(hi <= p < hi + 3 for lo, hi in hooks) and is_return(base_img, p)]
                # a stock instruction that the patch overwrote cannot run: where two hooks touch, the changed run is
                # long enough to count as new code, and the stock pcs in it are not "outside hook sites"
                d["only_base"] = [p for p in d["only_base"] if p not in rets and not any(lo <= p < hi for lo, hi in new)]
                dev = device_same(fb.mmio, fp.mmio, new)
                ok = not dw and not d["only_base"] and not d["only_patched_stock"] and fb.state == fp.state and not fp.faults and dev
                if k and not fb.state["picture"]:  # a frame without a picture in the reference compares nothing
                    ok = False
                    OUT("  %-8s the reference gives no picture in %s: the comparison proves nothing" % (pm_name, fb.label))
                ok_all &= ok
                OUT("  %-8s %-9s %-13s %s: %d writes (pinned %d), same order and values: %s; bytes that differ: %d; "
                    "flag bytes written: %s" % (pm_name, name, fb.label, "SAME" if ok else "DIFFERENT", len(wb), len(wa),
                                                 same_seq or "no (see flag bytes)", len(dw), flagw))
                OUT("           device accesses: %d, same order, addresses and values as pinned: %s; stock `ret` after a hook "
                    "site done by the routine: %d" % (len(fp.mmio), dev, len(rets)))
                OUT("           pcs: %d (pinned %d); stock pcs only in pinned, outside hook sites: %d; at hook sites: %d; "
                    "new-code pcs: %d in %s; other pcs only in patched: %d" % (
                        len(fp.pcs), len(fb.pcs), len(d["only_base"]), len(d["skipped_at_hooks"]), len(d["only_patched_new"]),
                        fmt_funcs(d["only_patched_new"], 8) or "-", len(d["only_patched_stock"])))
                for a in list(dw)[:6]:
                    OUT("           differs 0x%08X: pinned %s patched %s" % (a, dw[a][0], dw[a][1]))
                if d["only_base"] or d["only_patched_stock"]:
                    OUT("           only pinned: %s | only patched: %s" % (fmt_funcs(d["only_base"]), fmt_funcs(d["only_patched_stock"])))
    OUT("  S1 RESULT: %s" % ("patched = pinned with the request clear" if ok_all else fail("DIFFERENCES FOUND")))


# ------------------------------------------------------------------------------------------------ S2
def s2(pinned, patched):
    OUT("S2. Picture Mode Natural, two frames, then the request is set, four frames, request cleared, two frames.")
    for art_type in (1, 0):  # both, always: the scope of a check is not taken from the environment
        OUT(" --- art type setting 17601[0] = %d %s" % (art_type, "(type I)" if art_type == 1 else "(no art type: what the camera holds in Natural is UNKNOWN)"))
        for name, path in [("pinned", pinned)] + patched:
            with open_lv(path, name, NATURAL, art_type) as lv:
                lv.start()
                for _ in range(2):
                    f = lv.frame()
                show(lv, f)
                if name == "pinned":
                    stubbed_note(lv)
                    if not f.state["picture"]:
                        OUT("  S2 RESULT [pinned, art type %d]: %s" % (art_type, fail("the reference gives no picture: the scenario proves nothing")))
                    continue
                OUT("  [%s] request on: %s" % (name, request(lv, True)))
                bad = []
                for _ in range(4):
                    f = lv.frame()
                    show(lv, f)
                    bad.append(anomalies(lv, f))
                OUT("  [%s] request off: %s" % (name, request(lv, False)))
                for _ in range(2):
                    f = lv.frame()
                    show(lv, f)
                if all("no picture" in b for b in bad):
                    verdict = "NO PICTURE in every frame while the request is set"
                    if all(any("refused" in x for x in b) for b in bad):
                        verdict += ": the heap refuses the art buffers in every frame (the camera fault of direct-1)"
                    verdict = fail(verdict)
                elif any(b for b in bad):
                    verdict = fail("anomalies: %s" % bad)
                else:
                    verdict = "every frame with the request gives a picture through the line job and the overlay pass"
                OUT("  S2 RESULT [%s, art type %d]: %s; last frame after the request: picture %s, heap mode %d, live blocks %d"
                    % (name, art_type, verdict, f.state["picture"], f.state["heap_mode"], len(lv.blocks)))


# ------------------------------------------------------------------------------------------------ S3
def s3(pinned, patched):
    OUT("S3. ART Key Line with the request set, then the Picture Mode setting changes to film entries and effect")
    OUT("    filters, two frames each, both orders. pinned runs the same changes without a request (control).")
    seq = [107, 113, KEY_LINE, 113, 107, KEY_LINE, 100, 104, 108, 103, KEY_LINE, NATURAL, KEY_LINE]
    names = dict(FILM)
    names.update(EFFECT)
    names.update({KEY_LINE: "Key Line", NATURAL: "Natural"})
    for name, path in [("pinned", pinned)] + patched:
        with open_lv(path, name, KEY_LINE) as lv:
            lv.start()
            lv.frame()
            f = lv.frame()
            show(lv, f)
            if name == "pinned":
                stubbed_note(lv)
            else:
                OUT("  [%s] request on: %s" % (name, request(lv, True)))
            lv.frame()
            show(lv, lv.frame())
            found = {}
            for pm in seq:
                lv.settings[PM] = pm
                OUT("  [%s] Picture Mode setting -> %d %s" % (name, pm, names[pm]))
                for k in range(2):
                    f = lv.frame()
                    show(lv, f, events=("heap set mode", "heap re-partition", "error report") if k == 0 else ("heap re-partition", "error report"))
                    for a in anomalies(lv, f):
                        found.setdefault(a.split(" (")[0].split(" code")[0], []).append("%d/%s" % (pm, f.label))
                    if f.faults:
                        break
                if f.faults:
                    break
            OUT("  S3 RESULT [%s]: %s" % (name, "no anomaly in %d filter changes" % len(seq) if not found else
                                          fail("" if name != "pinned" else None) + "; ".join("%s: %d frames (%s)" % (k, len(v), ", ".join(v[:6])) for k, v in found.items())))


# ------------------------------------------------------------------------------------------------ S4
FAKE = 0x7D500000


def fake_objects(sc):
    """A stand-in for the C++ objects that the state functions use: every pointer field leads to an object whose
    virtual functions all return 0."""
    sc.write(FAKE, struct.pack("<I", FAKE + 0x1000) * 0x400)             # object fields -> second object
    sc.write(FAKE + 0x1000, struct.pack("<I", FAKE + 0x2000) * 0x400)    # its first word: the vtable
    sc.write(FAKE + 0x2000, struct.pack("<I", FAKE + 0x3000) * 0x400)    # every virtual function -> the pad
    sc.write(FAKE + 0x3000, b"\x00\xf0\xfc")                             # clr d0 ; rets


def s4(pinned, patched):
    OUT("S4. MF Assist start / stop through the state object. The functions entryMfAssistOff 0x7EB7D43B and")
    OUT("    entryMfAssistOn 0x7EB7D46C run whole, on stand-in objects (virtual calls return 0; the debug print")
    OUT("    0x7E9670E9 and 0x7EB8537D are stubbed). The internal zoom-off handler 0x7EB7DEB9 runs with its direct")
    OUT("    callees stubbed except the stock word setter 0x7E96AFD9. Not run: the state framework that decides")
    OUT("    which entry function follows which event. Writes to L, R, L2 are logged.")
    watch = [(L, L2 + 1)]
    for name, path in [("pinned", pinned)] + patched:
        with scenario.Scenario(path, name=name) as sc:
            fake_objects(sc)
            sc.stub(0x7E9670E9, None, "debug print")
            sc.stub(0x7EB8537D, None, "0x7EB8537D")
            handler_stubs = [0x7EB7E04A, 0x7EBA62DB, 0x7E973ABD, 0x7EBA4C8D, 0x7E9712D0, 0x7E96C3A5, 0x7EB85A4C, 0x7E966B30,
                             0x7EB868D2, 0x7E971F70, 0x7EBA62EB, 0x7EBA4C9E]
            for a in handler_stubs:
                sc.stub(a, None, "handler callee 0x%08X" % a)
            sc.w8(R, 0xEE)                                                   # unknown value before the object exists
            steps = [("object created: entryMfAssistOff", ENTRY_OFF, (0x40, 12)),
                     ("ring turned: entryMfAssistOn", ENTRY_ON, (0x40, 12)),
                     ("ring stops: entryMfAssistOff", ENTRY_OFF, (0x40, 12)),
                     ("ring turned again: entryMfAssistOn", ENTRY_ON, (0x40, 12)),
                     ("internal zoom-off handler 0x7EB7DEB9 (capture, movie start)", 0x7EB7DEB9, (0xF0, 48)),
                     ("the Off state that follows: entryMfAssistOff", ENTRY_OFF, (0x40, 12))]
            if is_d1(name):
                steps = [("startMfAssist entry 0x7E9889EB (hook S; piece)", "piece", (0x7E9889EB, 0x7E9889F2)),
                         ("endMfAssist entry 0x7E9830E0 (hook N; piece)", "piece", (0x7E9830E0, 0x7E9830E6)),
                         ("startMfAssist entry again", "piece", (0x7E9889EB, 0x7E9889F2)),
                         ("internal zoom-off handler 0x7EB7DEB9 (capture, movie start)", 0x7EB7DEB9, (0xF0, 48))]
            sc.w32(MFA, 0)
            for what, entry, frame in steps:
                if is_d1(name) and "startMfAssist" in what:
                    sc.w32(MFA, 1)                                           # the stock code sets the word in the same call
                if entry == "piece":
                    r = sc.piece(frame[0], [frame[1]], {"a0": FAKE}, log_writes=watch)
                else:
                    r = sc.call(entry, {"a0": FAKE}, frame=frame, log_writes=watch)
                w = ["0x%08X=%d" % (a, v) for a, s, v, pc in r.writes]
                OUT("  [%s] %-62s %s; writes to the flag bytes: %s; after: R=%d word=%d" % (
                    name, what, "FAULT " + r.fault if r.fault else "ran %d pcs" % len(r.pcs), w or "none", sc.r8(R), sc.r32(MFA)))
            OUT("  S4 RESULT [%s]: R at the end = %d%s" % (name, sc.r8(R), "" if name == "pinned" else
                                                           " (0 = not left set)" if sc.r8(R) == 0 else fail(" (LEFT SET after an internal zoom-off)")))


# ------------------------------------------------------------------------------------------------ S5
def s5(pinned, patched):
    OUT("S5. Capture while the request is set, as far as it runs here: Natural with lines on, then the mov command")
    OUT("    Through End (what a capture sends first), then the heap mode chooser 0x7E714833 as the capture path calls")
    OUT("    it. Not run: the TAKE_* and REC_* tasks, the sensor read-out, the art passes of a still.")
    base = {}
    for name, path in [("pinned", pinned)] + patched:
        with open_lv(path, name, NATURAL) as lv:
            lv.start()
            lv.frame()
            lv.frame()
            if name != "pinned":
                request(lv, True)
                lv.frame()
                show(lv, lv.frame())
            f = lv.command(CMD_THROUGH_END, label="Through End")
            show(lv, f, events=("heap free", "heap set mode", "heap re-partition", "error report"))
            live, state = len(lv.blocks), lv.sc.r32(MOV_STATE)
            got = []
            lv.sc.probe(0x7E578C60, lambda sc, g: got.append(g["d0"] & 0xFFFF), "heap set mode (capture)")
            r = lv.sc.call(0x7E714833, frame=(0xF0, 32), label="heap mode chooser (capture)")
            new = sorted(p for p in r.pcs if p >= 0x7EBF1F00 and p < 0x7EBF2000 or 0x7ECB0EE3 <= p < 0x7ECB1000)
            # the art-task hooks with a still packet (mode 1) while L2 is set
            sc = lv.sc
            D = 0x7D600000
            sc.w8(L2, sc.r8(L2))
            sc.write(D, struct.pack("<H", 1)); sc.write(D + 0x40, bytes(64))
            g = sc.piece(0x7E726761, [0x7E726770], {"a3": D + 0x40, "a2": D})
            gain = sc.r16(D + 0x40 + 34)
            res = (state, live, got, gain)
            if name == "pinned":
                base = res
            OUT("  [%s] after Through End: mov state %d, live heap blocks %d, %s; chooser asks for heap mode %s (%s, new-code "
                "pcs run: %d); pass 9 gain for a still packet with L2=%d: 0x%04X" % (
                    name, state, live, flags(lv), got, "FAULT " + r.fault if r.fault else "ok", len(new), sc.r8(L2), gain))
            if name != "pinned":
                OUT("  S5 RESULT [%s]: %s" % (name, "same state, heap mode and still gain as pinned" if res == base else
                                              fail("DIFFERS from pinned %s" % (base,))))


def main():
    which, pinned = sys.argv[1], sys.argv[2]
    patched = [tuple(a.split("=", 1)) for a in sys.argv[3:]]
    for n, fn in (("s1", s1), ("s2", s2), ("s3", s3), ("s4", s4), ("s5", s5)):
        if which in (n, "all"):
            fn(pinned, patched)
            OUT("")
    sys.exit(1 if FAILED else 0)


main()

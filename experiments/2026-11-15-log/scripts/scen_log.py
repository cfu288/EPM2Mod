"""Scenario tests of the build debug-log (NOTES.md in this folder). Uses emulator and the decoder of the package.

    python3 scen_log.py SCENARIO PINNED_BLOCK0 DEBUG_BLOCK0
    SCENARIO: s15 s16 s17 or all
    PINNED  peaking-colours (the pinned build)
    DEBUG   debug-log
    The block-0 files are `block0_0100.bin` of `python3 tools/oetool.py unpack build/NAME.BIN /tmp/scratch/NAME`.

S15  Live-view frames with the MF Assist request set, Natural and Key Line, Peaking White (3) and Red (2): DEBUG
     against PINNED. Pass = the same memory writes outside the log's RAM (and one word that the stock code copies
     from an unset stack slot), the same device accesses in the same order
     (but the reads of the timer 0x98900074, which log_put makes), no stock pc lost outside the hook sites, the same
     pass 9 gain and pass 7 ucExpose, no anomaly. Then the ring is read from the emulator's memory and decoded with
     `epm2mod.eventlog`: the events of the probes that the mov task and the ART task reach are printed and checked.
S16  log_put, log_chg and log_cnt alone, called with known registers: every register and the flags are kept, the
     record is as the model, the ring wraps at 512 records, log_chg logs only a new value, log_cnt logs while the
     gate has budget, and a call with CPU number 1 writes to the CPU1 ring.
S17  Every hook alone: the code from the hook site to the first stock instruction after the replaced ones, with set
     registers and the flags N, Z, C, V set, on both images. Pass = the same registers and flags at that instruction,
     the replaced calls made with the same arguments, the same memory outside the log's RAM, and the records that
     the dictionary describes. The GUI hook starts the flush task only for a menu, playback or power-off state,
     while no flush runs and isMediaWriting gives 0.
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PEAK = os.path.join(ROOT, "experiments", "2026-11-14-focus-peaking", "scripts")
sys.path.insert(0, os.path.join(ROOT, "emulator"))
sys.path.insert(0, os.path.join(ROOT, "src"))
import scenario  # noqa: E402
from scenario import Scenario, diff_pcs, diff_writes, fmt_funcs, patch_ranges  # noqa: E402
from epm2mod.eventlog import decode, load_dictionary  # noqa: E402
import json  # noqa: E402

# scen_menu.py runs its main() when it is imported. Take its helpers without that last line.
_src = open(os.path.join(PEAK, "scen_menu.py")).read()
assert _src.rstrip().endswith("\nmain()")
_sm = {"__file__": os.path.join(PEAK, "scen_menu.py"), "__name__": "scen_menu"}
_argv, sys.argv = sys.argv, sys.argv[:1]
exec(compile(_src.rstrip()[:-len("main()")], "scen_menu.py", "exec"), _sm)
sys.argv = _argv
open_lv, request, anomalies, flags = (_sm[k] for k in ("open_lv", "request", "anomalies", "flags"))
NATURAL, KEY_LINE, TAG, C = _sm["NATURAL"], _sm["KEY_LINE"], _sm["TAG"], _sm["C"]

RING0, RING1, PST, RAM_END = 0x7E4F9000, 0x7E4FB020, 0x7E4FD040, 0x7E4FD2C0     # cached addresses of the log's RAM
STALE = 0x602A4954                      # a word that stock code copies from an unset stack slot (see s15)
UNCACHED = 0x40000000
TIMER = 0x98900074
MF_ON_SITE = 0x7EB7D47D                 # hook MFON of log-probes: entryMfAssistOn after its trace call
WORDS = load_dictionary(json.load(open(os.path.join(ROOT, "data", "logdict", "events.json"))))
OUT = print


def ring_events(sc, ring=RING0):
    """The records of one ring as decoded objects (the block is built here as the flush task builds it)."""
    magic, w, f, drops, session = struct.unpack("<5I", sc.read(ring + UNCACHED, 20))
    if magic != 0x314C5045:
        return []
    first = max(0, w - 512)
    data = struct.pack("<4sBBBB8sIIII", b"EPLG", 1, 16, 0 if ring == RING0 else 1, 32, WORDS.build_id, first, w - first,
                       drops, session)
    for n in range(first, w):
        data += sc.read(ring + UNCACHED + 32 + 16 * (n & 511), 16)
    return list(decode(data, WORDS))


def brief(e):
    return "%s %s" % (e["event"], json.dumps(e["args"], separators=(",", ":"))) if "event" in e else json.dumps(e)


def frames(path, name, pm, value, n=4):
    with open_lv(path, name, pm, log=True) as lv:
        lv.settings[TAG] = value
        lv.start()
        how = request(lv, True)
        if name == "debug":                 # the probe after the trace call of entryMfAssistOn: arms the pass 9 gate
            r = lv.sc.piece(MF_ON_SITE, [MF_ON_SITE + 6], {"a2": 0x7D500000})
            assert not r.fault, r.fault
        fs = [lv.frame() for _ in range(n)]
        facts = {"flags": flags(lv) + " C=%d" % lv.sc.r8(C), "gain2": sorted(set(lv.seen["gain2"])),
                 "expose7": sorted(set(lv.seen["expose7"])), "bad": [anomalies(lv, f) for f in fs], "how": how,
                 "summary": [f.summary() for f in fs],
                 "events": ring_events(lv.sc) if name == "debug" else [],
                 "allocs": [d for f in fs for k, d in f.events if k == "heap alloc"]}
        return fs, facts


def s15(pinned, debug):
    OUT("S15. Live view with the MF Assist request: DEBUG against PINNED, then the decoded ring.")
    a_img, b_img = open(pinned, "rb").read(), open(debug, "rb").read()
    new, hooks = patch_ranges(a_img, b_img)
    # The line-job set-up (0x7E6CDA36 in mov_art_set_line_yc_param) copies a struct from its stack to 0xA02A4940. The
    # word at +20 is never set: it holds what an earlier call left on the stack. A probe leaves its saved registers
    # below the stack pointer, so this word can differ. It is proven unset below: on the pinned image it holds an
    # address of the test harness's own stack in the first frame.
    skip = [(RING0, RAM_END), (STALE, STALE + 4)]
    ok_all = True
    stale = None
    for value, vname in ((3, "White"), (2, "Red")):
        for pm, pm_name in ((NATURAL, "Natural"), (KEY_LINE, "Key Line")):
            tag = "458=%d %s, %s" % (value, vname, pm_name)
            fa, xa = frames(pinned, "colours", pm, value)
            fb, xb = frames(debug, "debug", pm, value)
            OUT("  [%s] pinned: %s | %s" % (tag, xa["summary"][-1], xa["flags"]))
            OUT("  [%s] debug:  %s | %s" % (tag, xb["summary"][-1], xb["flags"]))
            if stale is None:
                vals = [v for a, size, v, pc in fa[0].writes if (a & 0x3FFFFFFF | 0x40000000) == STALE and size == 4]
                stale = bool(vals) and 0x7D000000 <= vals[-1] < 0x7D200000
                ok_all &= stale
                OUT("  the word 0x%08X in the pinned image's first frame: %s -> %s" % (
                    STALE, ", ".join("0x%08X" % v for v in vals) or "not written",
                    "an address of the harness stack: the stock code copies an unset stack slot" if stale else "NOT as expected"))
            for x, y in zip(fa, fb):
                dw = diff_writes(x.writes, y.writes, skip=skip)
                d = diff_pcs(x.pcs, y.pcs, new, hooks)
                rets = [p for p in d["only_base"] if any(hi <= p < hi + 3 for lo, hi in hooks)]
                lost = [p for p in d["only_base"] if p not in rets]
                ma = [m[:4] for m in x.mmio]
                mb = [m[:4] for m in y.mmio if m[1] != TIMER]
                timer = sum(1 for m in y.mmio if m[1] == TIMER)
                ok = not dw and not lost and not d["only_patched_stock"] and x.state == y.state and not y.faults and ma == mb
                ok_all &= ok
                OUT("  %s %-8s %s: %d writes (pinned %d), bytes that differ outside the log's RAM: %d; device accesses %d "
                    "+ %d timer reads, same order, addresses and values: %s; stock pcs lost outside hook sites: %d; stock "
                    "pcs gained: %d; new-code pcs: %d" % (tag, y.label, "SAME" if ok else "DIFFERENT", len(y.writes),
                                                        len(x.writes), len(dw), len(mb), timer, ma == mb, len(lost),
                                                        len(d["only_patched_stock"]), len(d["only_patched_new"])))
                for a in list(dw)[:6]:
                    OUT("      differs 0x%08X: pinned %s, debug %s" % (a, dw[a][0], dw[a][1]))
                if lost or d["only_patched_stock"]:
                    OUT("      lost: %s | gained: %s" % (fmt_funcs(lost), fmt_funcs(d["only_patched_stock"])))
            same = xa["gain2"] == xb["gain2"] and xa["expose7"] == xb["expose7"] and not any(xb["bad"])
            ok_all &= same
            OUT("  [%s] pass 9 gain %s, pass 7 ucExpose %s: %s; anomalies: %s" % (
                tag, ["0x%04X" % g for g in xb["gain2"]], xb["expose7"], "as pinned" if same else "NOT as pinned",
                [b for b in xb["bad"] if b] or "none"))
            ev = xb["events"]
            names = [e.get("event") for e in ev]
            for e in ev:
                OUT("      log: seq %d %s" % (e["seq"], brief(e)) if "seq" in e else "      log: " + brief(e))
            latch = [e for e in ev if e.get("event") == "pk_latch"]
            pass9 = [e for e in ev if e.get("event") == "pk_pass9"]
            want = names.count("pk_mf_start") == 1 and latch and latch[-1]["args"]["latch"]["L"] == 1 \
                and latch[-1]["args"]["latch"]["R"] == 1 and latch[-1]["args"]["latch"]["C"] == value \
                and "pk_heap_mode" in names and 1 <= len(pass9) <= 3 \
                and all("0x%04X" % int(p["args"]["line"]["gain"]) in ["0x%04X" % g for g in xb["gain2"]] for p in pass9) \
                and all(any(("0x%08X" % int(p["args"]["picture"], 16)) in a for a in xb["allocs"]) for p in pass9)
            ok_all &= bool(want)
            OUT("  [%s] events %s" % (tag, "as expected: MF start, latch with L=1 R=1 C=%d, heap mode, pass 9 with the "
                                           "picture buffer of the heap log and the gain" % value if want else "NOT as expected"))
    OUT("  S15 RESULT: %s" % ("PASS" if ok_all else "FAIL"))
    return ok_all


def s16(pinned, debug):
    OUT("S16. log_put, log_chg, log_cnt alone.")
    lst = open(os.path.join(os.path.dirname(HERE), "results", "log-listing.txt")).read()
    import re
    sym = {m.group(2): int(m.group(1), 16) for m in re.finditer(r"^([0-9a-f]{8}) <(\w+)>:", lst, re.M)}
    ok = True
    sc = Scenario(debug, name="debug")
    regs = {"d0": 0x1234, "d1": 0x11111111, "d2": 0x22222222, "d3": 0x33333333, "a0": 0xA0A0A0A0, "a1": 0x7D200010,
            "a2": 0xA2A2A2A2, "a3": 0xA3A3A3A3}
    keep = ("d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3")

    def call(fn, **over):
        r = sc.call(sym[fn], dict(regs, **over), frame=(0, 0))
        assert not r.fault, r.fault
        bad = [k for k in keep if r.regs[k] != dict(regs, **over)[k]]
        return r, bad

    def head():
        return struct.unpack("<5I", sc.read(RING0 + UNCACHED, 20))

    r, bad = call("log_put")
    rec = struct.unpack("<HHIII", sc.read(RING0 + UNCACHED + 32, 16))
    good = head()[:2] == (0x314C5045, 1) and (rec[0], rec[1], rec[3], rec[4]) == (0x1234, 0, 0x11111111, 0xA0A0A0A0) and not bad
    ok &= good
    OUT("  log_put on a clear ring: header magic 0x%08X w %d; record id 0x%04X seq %d args 0x%08X 0x%08X; registers kept "
        "%s (psw at the return: %s) -> %s" % (head()[0], head()[1], rec[0], rec[1], rec[3], rec[4], not bad,
                                              r.regs.get("psw"), "ok" if good else "FAIL"))
    for i in range(1, 600):
        r, bad = call("log_put", d1=i)
        ok &= not bad
    w = head()[1]
    slot = struct.unpack("<HHIII", sc.read(RING0 + UNCACHED + 32 + 16 * (599 & 511), 16))
    oldest = struct.unpack("<HHIII", sc.read(RING0 + UNCACHED + 32 + 16 * (600 & 511), 16))
    good = w == 600 and slot[1] == 599 and slot[3] == 599 and oldest[1] == 88 and sc.r32(RING1 + UNCACHED) == 0 \
        and sc.read(RING0 + UNCACHED + 32 + 16 * 512, 16) == bytes(16)
    ok &= good
    OUT("  600 records: w %d, newest in slot %d (seq %d), oldest kept seq %d, nothing written after the ring, CPU1 ring "
        "untouched -> %s" % (w, 599 & 511, slot[1], oldest[1], "ok" if good else "FAIL"))
    gate = 0x7D200010
    sc.write(gate, bytes(8))
    seq = []
    for v in (5, 5, 6, 6, 5):
        before = head()[1]
        r, bad = call("log_chg", d1=v, a1=gate)
        ok &= not bad
        seq.append(head()[1] - before)
    sc.write(gate + 4, bytes([2]))
    for v in (5, 5, 5):
        before = head()[1]
        call("log_chg", d1=v, a1=gate)
        seq.append(head()[1] - before)
    good = seq == [1, 0, 1, 0, 1, 1, 1, 0]
    ok &= good
    OUT("  log_chg with arg0 5, 5, 6, 6, 5, then budget 2 and 5, 5, 5: records %s -> %s" % (seq, "ok" if good else "FAIL"))
    sc.write(gate, bytes(8)); sc.write(gate + 4, bytes([3]))
    seq = []
    for v in range(5):
        before = head()[1]
        r, bad = call("log_cnt", d1=v, a1=gate)
        ok &= not bad
        seq.append(head()[1] - before)
    good = seq == [1, 1, 1, 0, 0] and sc.r8(gate + 4) == 0
    ok &= good
    OUT("  log_cnt with budget 3, five calls: records %s -> %s" % (seq, "ok" if good else "FAIL"))
    w0 = head()[1]
    sc.w32(0x8050, 1)                       # the CPU number register reads 1: the record goes to the CPU1 ring
    r, bad = call("log_put", d0=0x4321, d1=7)
    sc.w32(0x8050, 0)
    h1 = struct.unpack("<5I", sc.read(RING1 + UNCACHED, 20))
    rec = struct.unpack("<HHIII", sc.read(RING1 + UNCACHED + 32, 16))
    good = not bad and head()[1] == w0 and h1[:2] == (0x314C5045, 1) and (rec[0], rec[1], rec[3]) == (0x4321, 0, 7)
    ok &= good
    OUT("  log_put with CPU number 1: CPU0 ring unchanged (w %d), CPU1 ring magic 0x%08X w %d, record id 0x%04X seq %d "
        "-> %s" % (head()[1], h1[0], h1[1], rec[0], rec[1], "ok" if good else "FAIL"))
    OUT("  S16 RESULT: %s" % ("PASS" if ok else "FAIL"))
    return ok


def s17(pinned, debug):
    OUT("S17. Each hook from its site to the first stock instruction after it: DEBUG against PINNED, with the flags "
        "N Z C V set at the start.")
    SCR = 0x7D210000                         # scratch structs for the pointers that the replaced instructions use
    T6, T8 = 0x7E78C254, 0x7E78C8E4          # jump tables of the six-axis stage and of the curve selector
    img = open(debug, "rb").read()
    word = lambda a: struct.unpack_from("<I", img, a - 0x7E421020)[0]
    seen = {}

    def stub_ret(val):
        return lambda sc, g: {"d0": val}

    # name: (start, stop, registers, stubs {addr: d0}, [(address, bytes)] memory, expected events)
    cases = [
        ("ERR", 0x7E426D4B, 0x7E426D53, {"d0": 0x2A001001, "mdr": 0x7E579DCC}, {}, [("sp+48", struct.pack("<II", 1, 0x7102))],
         [("fw_error", {"code": "0x2A001001", "caller": "0x7E579DCC"}), ("fw_error_args", {"count": 1, "arg": "0x00007102"})]),
        ("BOOT", 0x7E503DD4, 0x7E503DDA, {}, {}, [(0x604154E6, struct.pack("<H", 0x0102)), (0x604154E9, b"\x09")],
         [("boot", {"ring_found": 1, "poweron": {"raw": "0x00090102", "factor": 258, "wake": 9}})]),
        ("GUI no trigger", 0x7ECDF6E4, 0x7ECDF6E9, {"d0": 0x5100}, {0x7ECE6333: 0, 0x7ECD360A: 0, 0x7E449541: 0}, [],
         [("gui_state", {"state": "0x00005100", "previous": "0x00000000"})]),
        ("GUI menu", 0x7ECDF6E4, 0x7ECDF6E9, {"d0": 0x5700}, {0x7ECE6333: 0, 0x7ECD360A: 0, 0x7E449541: 0}, [],
         [("gui_state", {"state": "0x00005700", "previous": "0x00005100"})]),
        ("GUI same state", 0x7ECDF6E4, 0x7ECDF6E9, {"d0": 0x5700}, {0x7ECE6333: 0, 0x7ECD360A: 0, 0x7E449541: 0}, [], []),
        ("GUI busy", 0x7ECDF6E4, 0x7ECDF6E9, {"d0": 0x3000}, {0x7ECE6333: 0, 0x7ECD360A: 0, 0x7E449541: 0}, [],
         [("gui_state", {"state": "0x00003000", "previous": "0x00005700"})]),
        ("GUI card busy", 0x7ECDF6E4, 0x7ECDF6E9, {"d0": 0x2000}, {0x7ECE6333: 0, 0x7ECD360A: 1, 0x7E449541: 0},
         [(PST + UNCACHED, b"\0")], [("gui_state", {"state": "0x00002000", "previous": "0x00003000"})]),
        ("LATCH", 0x7E6C610B, 0x7E6C6111, {"d0": 0x77}, {}, [(0x602BE8C4, bytes([1, 1, 0, 2])), (0x605B1CD4, bytes([0, 1, 0, 0]))],
         [("pk_latch", {"latch": {"raw": "0x02000101", "L": 1, "R": 1, "L2": 0, "C": 2}, "lv": {"raw": "0x00000100", "b4": 0, "art_type": 1}})]),
        ("LATCH again", 0x7E6C610B, 0x7E6C6111, {"d0": 0x77}, {}, [], []),
        ("HEAP", 0x7E578C60, 0x7E578C66, {"d0": 1, "mdr": 0x7E4C935E}, {0x7E577C32: 5}, [],
         [("pk_heap_mode", {"mode": 1, "caller": "0x7E4C935E"})]),
        ("PK9 not armed", 0x7E72676D, 0x7E726774, {"d0": 0x200, "a3": SCR}, {}, [("sp+12", struct.pack("<I", SCR + 0x100))], []),
        ("MFON", 0x7EB7D47D, 0x7EB7D483, {"a2": SCR + 0x400}, {}, [(SCR + 0x400 + 404, struct.pack("<I", 0x1234))],
         [("pk_mf_start", {"latch": {"raw": "0x02000101", "L": 1, "R": 1, "L2": 0, "C": 2}, "object": "0x%08X" % (SCR + 0x400)})]),
        ("PK9 armed", 0x7E72676D, 0x7E726774, {"d0": 0, "a3": SCR},
         {}, [("sp+12", struct.pack("<I", SCR + 0x100)), (SCR + 0x100 + 32, struct.pack("<I", SCR + 0x200)),
              (SCR + 0x200 + 16, struct.pack("<II", 0xB596A940, SCR + 0x300)), (SCR + 0x300, bytes([0, 0x80, 0, 0]))],
         [("pk_pass9", {"picture": "0xB596A940", "line": {"raw": "0x00000080", "first_pixel": 128, "gain": 0}})]),
        ("MFOFF", 0x7EB7D44C, 0x7EB7D451, {"a2": SCR + 0x400}, {}, [],
         [("pk_mf_end", {"latch": {"raw": "0x02000101", "L": 1, "R": 1, "L2": 0, "C": 2}, "object": "0x%08X" % (SCR + 0x400)})]),
        ("ART 167", 0x7E56D2BF, 0x7E56D2C5, {"d3": 167, "d0": 4 * (167 - 9)}, {}, [],
         [("art_sixaxis", {"art": 167, "handler": "0x%08X" % word(T6 + 4 * (167 - 9))})]),
        ("ART 167 again", 0x7E56D2BF, 0x7E56D2C5, {"d3": 167, "d0": 4 * (167 - 9)}, {}, [], []),
        ("STAGE", 0x7E56C68B, 0x7E56C692, {"a3": SCR + 0x500}, {}, [(SCR + 0x500 + 79, bytes([167])), (SCR + 0x500 + 20, struct.pack("<I", 0x40000))],
         [("film_stage", {"art": 167, "flags": "0x00040000"})]),
        ("MATRIX", 0x7E56C764, 0x7E56C76A, {"a1": 0x7E768F46, "d2": 0x11, "d3": 0x22}, {0x7E56C263: 3}, [],
         [("film_matrix", {"table": "0x7E768F46", "stack": "0x00000022"})]),
        ("CURVE 85", 0x7E56E860, 0x7E56E866, {"d1": 4 * (85 - 8)}, {}, [("sp+20", bytes([85]))],
         [("film_curve", {"art": 85, "handler": "0x%08X" % word(T8 + 4 * (85 - 8))})]),
        ("CBS", 0x7E995A0B, 0x7E995A13, {"a0": SCR + 0x600, "d0": 264, "d1": 0xF0000058}, {}, [],
         [("shoot_cbs", {"cbs": 264, "result": "0xF0000058"})]),
        ("ART 167 after a callback", 0x7E56D2BF, 0x7E56D2C5, {"d3": 167, "d0": 4 * (167 - 9)}, {}, [],
         [("art_sixaxis", {"art": 167, "handler": "0x%08X" % word(T6 + 4 * (167 - 9))})]),
        ("ADJ", 0x7E676261, 0x7E67626B, {"d0": 2, "d1": 11}, {}, [], [("lv_adjust", {"mode": 2, "rotate": 11})]),
        ("LVV", 0x7E459A5F, 0x7E459A64, {}, {}, [(0x603F4C22 + 12 * i, struct.pack("<h", v)) for i, v in enumerate((-3, 1000, 25, 250))],
         [("lv_values", {"xy": {"raw": "0x03E8FFFD", "x": -3, "y": 1000}, "zt": {"raw": "0x00FA0019", "z": 25, "temp": 250}})]),
        ("IVSTART", 0x7E988670, 0x7E988677, {"d2": 0, "d0": 0}, {0x7E9670E9: 0}, [(0x602B0CDC, struct.pack("<I", 0x10))],
         [("iv_start", {"result": "0x00000000", "state": "0x00000010"})]),
        ("IVSET", 0x7E969E2F, 0x7E969E34, {"d2": 0x4, "d0": 0}, {0x7E9670E9: 0}, [],
         [("iv_state_set", {"bits": "0x00000004", "state_before": "0x00000010"})]),
        ("IVFRAME 1", 0x7EA997E5, 0x7EA997EC, {"a0": SCR + 0x700}, {}, [], [("iv_frame", {"n": 1, "state": "0x00000010"})]),
        ("IVFRAME 2", 0x7EA997E5, 0x7EA997EC, {"a0": SCR + 0x700}, {}, [], [("iv_frame", {"n": 2, "state": "0x00000010"})]),
        ("IVCLR", 0x7E9698FD, 0x7E969902, {"d2": 0x4, "d0": 0}, {0x7E9670E9: 0}, [],
         [("iv_state_clear", {"bits": "0x00000004", "state_before": "0x00000010"})]),
        ("IVEND", 0x7E982E8E, 0x7E982E95, {"d2": 0xF0000001, "d0": 0}, {0x7E9670E9: 0}, [],
         [("iv_end", {"result": "0xF0000001", "iv_frames": 2})]),
    ]
    runs = {}
    for name_, path in (("pinned", pinned), ("debug", debug)):
        sc = Scenario(path, name=name_)
        if name_ == "debug":                    # a ring that a session before left: the boot hook counts a restart
            sc.write(RING0 + UNCACHED, struct.pack("<5I", 0x314C5045, 0, 0, 0, 0))
        out = []
        for label, start, stop, regs, stubs, mem, want in cases:
            for a, d0 in stubs.items():
                sc.stub(a, stub_ret(d0))
            g = dict({"psw": 0x0F, "d0": 0x1111, "d1": 0x2222, "d2": 0x3333, "d3": 0x4444, "a0": 0x7D215550, "a1": 0x7D216660,
                      "a2": 0x7D217770, "a3": 0x7D218880, "mdr": 0x7E500000, "lir": 0x51, "lar": 0x52}, **regs)
            sp = scenario.SP0 - 0x400
            for a, data in mem:
                sc.write(sp + int(a[3:]) if isinstance(a, str) else a, data)
            before = sc.r32(RING0 + UNCACHED + 4)
            r = sc.piece(start, [stop], g, log_writes=scenario.RAM_AND_IMAGE)
            started = [(n, c["d0"]) for pc, n, c, ret in r.stubs if pc == 0x7E449541]
            calls = [(pc, c["d0"], c["d1"], c["a0"], c["a1"]) for pc, n, c, ret in r.stubs if pc != stop]
            ev = ring_events(sc)[before:] if name_ == "debug" else []
            out.append((label, r, calls, started, [(e["event"], e["args"]) for e in ev], want))
            for a in stubs:
                del sc._stubs[a]
        runs[name_] = out
    ok_all = True
    for (label, ra, ca, sa, _, want), (_, rb, cb, sb, ev, _) in zip(runs["pinned"], runs["debug"]):
        has_call = any(pc not in (0x7ECD360A, 0x7E449541) for pc, *_ in cb)
        keys = [k for k in ("pc", "sp", "psw", "d0", "d1", "d2", "d3", "a0", "a1", "a2", "a3", "lir", "lar", "mdr")
                if not (k == "mdr" and has_call)]
        regs_ok = not ra.fault and not rb.fault and all(ra.regs[k] == rb.regs[k] for k in keys)
        stock_calls = [c for c in cb if c[0] not in (0x7ECD360A, 0x7E449541)]
        calls_ok = ca == stock_calls
        dw = diff_writes(ra.writes, rb.writes, skip=[(RING0, RAM_END)])
        ev_ok = ev == list(want)
        ok = regs_ok and calls_ok and not dw and ev_ok
        ok_all &= ok
        seen[label] = sb
        OUT("  %-26s %s: registers and flags at the return as pinned %s%s; stock calls with the same arguments %s; memory "
            "outside the log's RAM as pinned %s; records %s%s" % (
                label, "ok" if ok else "FAIL", regs_ok, " (mdr left out: a call was replaced)" if has_call else "", calls_ok,
                not dw, [e[0] for e in ev] or "none", "" if ev_ok else " NOT as expected: %s" % ev))
        if rb.fault or ra.fault:
            OUT("      fault: pinned %s, debug %s" % (ra.fault, rb.fault))
    trig = {k: v for k, v in seen.items() if k.startswith("GUI")}
    want_trig = {"GUI no trigger": [], "GUI menu": [0x90], "GUI same state": [], "GUI busy": [], "GUI card busy": []}
    good = {k: [d0 for n, d0 in v] for k, v in trig.items()} == want_trig
    ok_all &= good
    OUT("  the flush task is started (OlyTaSt with id 0x90) only at the entry to the menu state while no flush runs and "
        "the card is not written: %s" % ("ok" if good else "FAIL %s" % trig))
    OUT("  S17 RESULT: %s" % ("PASS" if ok_all else "FAIL"))
    return ok_all


def main():
    which, pinned, debug = sys.argv[1:4]
    todo = ["s15", "s16", "s17"] if which == "all" else [which]
    res = [{"s15": s15, "s16": s16, "s17": s17}[t](pinned, debug) for t in todo]
    sys.exit(0 if all(res) else 1)


main()

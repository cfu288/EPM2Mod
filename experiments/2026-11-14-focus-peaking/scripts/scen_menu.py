"""Scenario tests of the build peaking-menu (NOTES.md section 15). Uses tools/emu.

    python3 scen_menu.py SCENARIO BASE_BLOCK0 PINNED_BLOCK0 MENU_BLOCK0
    SCENARIO: s8 s9 s10 s11 or all
    BASE    the build without focus peaking (seven-films-6-interval-240-level-adjust)
    PINNED  peaking-gain-2x
    MENU    peaking-menu
    The block-0 files are `block0_0100.bin` of `python3 tools/oetool.py unpack build/NAME.BIN /tmp/scratch/NAME`.

S8   Peaking Off (setting 458 = 1) with the MF Assist request set (R = 1, set by the build's own hook at
     entryMfAssistOn): Natural and Key Line frames of MENU against the same frames of BASE. Pass = the same memory
     writes (but the four flag bytes), the same device accesses in the same order, no stock pc lost outside the hook
     sites, L = 0.
S9   Peaking White (setting 458 = 3, and 0 = a value outside the list): the frames of MENU against the frames of PINNED
     with the same request. Pass = the same memory writes (but the byte C), the same device accesses, pass 9 gain
     0x0200, pass 7 ucExpose 3.
S10  Peaking Black (setting 458 = 2): a picture in every frame, pass 9 gain 0xFF00 with the plain picture
     (pass 7 ucExpose 3); request cleared: as before.
S11  The changed routines alone, with the firmware's own settings getter (no stand-in): T_A from its hook site to the
     return, for R = 0 / 1 and setting values 0 to 4; T_K from its hook site, for packet mode 2 / 0, L2 and C.
     The prm index entry of tag 0x8971 is written as the full-boot emulator shows it (0x603A52F0: tag, count 1,
     pointer 0x60410F36).
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools", "emu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenario  # noqa: E402
from scenario import RAM_AND_IMAGE, Scenario, diff_pcs, diff_writes, fmt_funcs, patch_ranges  # noqa: E402

# scen_peaking.py runs its main() when it is imported. Take its helpers without that last line.
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scen_peaking.py")).read()
assert _src.rstrip().endswith("\nmain()")
_sp = {"__file__": os.path.join(os.path.dirname(os.path.abspath(__file__)), "scen_peaking.py"), "__name__": "scen_peaking"}
exec(compile(_src.rstrip()[:-len("main()")], "scen_peaking.py", "exec"), _sp)
open_lv, request, show, anomalies, flags = (_sp[k] for k in ("open_lv", "request", "show", "anomalies", "flags"))
NATURAL, KEY_LINE = _sp["NATURAL"], _sp["KEY_LINE"]

L, R, L2, C = 0x602BE8C4, 0x602BE8C5, 0x602BE8C6, 0x602BE8C7
TAG = 0x8971                      # prm tag of setting 458
OFF, BLACK, WHITE = 1, 2, 3
OUT = print


def run_frames(path, name, pm, value, ask, n=3, log=True):
    """Start live view, set the request (if the image has one), run n frames. Returns (frames, lv facts)."""
    with open_lv(path, name, pm, log=log) as lv:
        if value is not None:
            lv.settings[TAG] = value
        lv.start()
        how = request(lv, True) if ask else "no request"
        fs = [lv.frame() for _ in range(n)]
        facts = {"flags": flags(lv) + " C=%d" % lv.sc.r8(C), "gain2": sorted(set(lv.seen["gain2"])),
                 "expose7": sorted(set(lv.seen["expose7"])), "bad": [anomalies(lv, f) for f in fs], "how": how,
                 "L": lv.sc.r8(L), "summary": [f.summary() for f in fs], "path": [", ".join(f.path()) for f in fs]}
        return fs, facts


def compare(tag, a_name, fa, b_name, fb, a_img, b_img, skip):
    """Frames of image b against frames of image a. Returns True when they are the same but for the skip bytes."""
    new, hooks = patch_ranges(a_img, b_img)
    ok_all = True
    for x, y in zip(fa, fb):
        dw = diff_writes(x.writes, y.writes, skip=[skip])
        d = diff_pcs(x.pcs, y.pcs, new, hooks)
        rets = [p for p in d["only_base"] if any(hi <= p < hi + 3 for lo, hi in hooks)]
        lost = [p for p in d["only_base"] if p not in rets]
        dev = [m[1:4] for m in x.mmio] == [m[1:4] for m in y.mmio]
        ok = not dw and not lost and not d["only_patched_stock"] and x.state == y.state and not y.faults and dev
        ok_all &= ok
        OUT("  %s %-8s %s: %d writes (%s %d), bytes that differ outside 0x%08X-0x%08X: %d; device accesses %d, same "
            "order, addresses and values: %s; stock pcs lost outside hook sites: %d; stock pcs gained: %d; new-code pcs: %d "
            "in %s" % (tag, y.label, "SAME" if ok else "DIFFERENT", len(y.writes), a_name, len(x.writes), skip[0],
                       skip[1] - 1, len(dw), len(y.mmio), dev, len(lost), len(d["only_patched_stock"]),
                       len(d["only_patched_new"]), fmt_funcs(d["only_patched_new"], 8) or "-"))
        for a in list(dw)[:6]:
            OUT("      differs 0x%08X: %s %s, %s %s" % (a, a_name, dw[a][0], b_name, dw[a][1]))
        if lost or d["only_patched_stock"]:
            OUT("      lost: %s | gained: %s" % (fmt_funcs(lost), fmt_funcs(d["only_patched_stock"])))
    return ok_all


def s8(base, pinned, menu):
    OUT("S8. Peaking Off (setting 458 = 1), MF Assist request set: MENU against BASE (the build without peaking).")
    a_img, b_img = open(base, "rb").read(), open(menu, "rb").read()
    ok = True
    for pm, pm_name in ((NATURAL, "Natural"), (KEY_LINE, "Key Line")):
        fa, xa = run_frames(base, "pinned", pm, OFF, False)       # the name "pinned" = an image without a request byte
        fb, xb = run_frames(menu, "menu", pm, OFF, True)
        OUT("  [%s] base: %s" % (pm_name, xa["summary"][-1]))
        OUT("  [%s] menu: %s | %s | %s" % (pm_name, xb["summary"][-1], xb["flags"], xb["how"]))
        ok &= compare(pm_name, "base", fa, "menu", fb, a_img, b_img, (L, C + 1)) and xb["L"] == 0
        ok &= xb["gain2"] == xa["gain2"] and xb["expose7"] == xa["expose7"]
        OUT("  [%s] pass 9 gain: base %s, menu %s; pass 7 ucExpose: base %s, menu %s" % (
            pm_name, ["0x%04X" % g for g in xa["gain2"]], ["0x%04X" % g for g in xb["gain2"]], xa["expose7"], xb["expose7"]))
    OUT("  S8 RESULT: %s" % ("PASS: with Peaking Off and the request set, MENU = BASE" if ok else "FAIL"))
    return ok


def s9(base, pinned, menu):
    OUT("S9. Peaking White: MENU against PINNED, request set in both.")
    a_img, b_img = open(pinned, "rb").read(), open(menu, "rb").read()
    ok = True
    for value in (WHITE, 0):
        for pm, pm_name in ((NATURAL, "Natural"), (KEY_LINE, "Key Line")):
            fa, xa = run_frames(pinned, "gain-2x", pm, value, True)
            fb, xb = run_frames(menu, "menu", pm, value, True)
            tag = "458=%d %s" % (value, pm_name)
            OUT("  [%s] pinned: %s | %s" % (tag, xa["summary"][-1], xa["flags"]))
            OUT("  [%s] menu:   %s | %s" % (tag, xb["summary"][-1], xb["flags"]))
            OUT("  [%s] pass 9 gain: pinned %s, menu %s; pass 7 ucExpose: pinned %s, menu %s; anomalies: %s" % (
                tag, ["0x%04X" % g for g in xa["gain2"]], ["0x%04X" % g for g in xb["gain2"]], xa["expose7"],
                xb["expose7"], [b for b in xb["bad"] if b] or "none"))
            ok &= compare(tag, "pinned", fa, "menu", fb, a_img, b_img, (C, C + 1))
            ok &= xb["gain2"] == [0x0200] and xb["expose7"] == [3] and xb["L"] == 1 and not any(xb["bad"])
    OUT("  S9 RESULT: %s" % ("PASS: White = the pinned build" if ok else "FAIL"))
    return ok


def s10(base, pinned, menu):
    OUT("S10. Peaking Black (setting 458 = 2): MENU. Natural, two frames, request set, four frames, request cleared, two.")
    ok = True
    for pm, pm_name in ((NATURAL, "Natural"), (KEY_LINE, "Key Line")):
        with open_lv(menu, "menu", pm) as lv:
            lv.settings[TAG] = BLACK
            lv.start()
            for _ in range(2):
                f = lv.frame()
            show(lv, f)
            OUT("  [%s] request on: %s" % (pm_name, request(lv, True)))
            for _ in range(4):
                f = lv.frame()
                g, e = sorted(set(lv.seen["gain2"])), sorted(set(lv.seen["expose7"]))
                bad = anomalies(lv, f)
                show(lv, f)
                good = g == [0xFF00] and e == [3] and not bad and lv.sc.r8(L) == 1 and lv.sc.r8(C) == BLACK and f.state["picture"]
                ok &= good
                OUT("      -> %s: gain %s, ucExpose %s, C=%d, anomalies %s" % (
                    "ok" if good else "NOT OK", ["0x%04X" % x for x in g], e, lv.sc.r8(C), bad or "none"))
            OUT("  [%s] request off: %s" % (pm_name, request(lv, False)))
            for _ in range(2):
                f = lv.frame()
                g = sorted(set(lv.seen["gain2"]))
                show(lv, f)
            want = [] if pm == NATURAL else [0xFF00]
            ok &= lv.sc.r8(L) == 0 and g == want and not anomalies(lv, f)
    OUT("  S10 RESULT: %s" % ("PASS: Black gives the line pass the gain 0xFF00 over a plain picture" if ok else "FAIL"))
    return ok


def s11(base, pinned, menu):
    OUT("S11. T_A and T_K alone, MENU against PINNED. The settings getter 0x7E457C75 is the firmware's own code.")
    HOOK_A, RET = 0x7E6ECF91, 0x7E6C33F5          # hook A at the end of the struct refresh; its caller's next instruction
    HOOK_K, K_END = 0x7E726767, 0x7E72676D
    LV, INDEX, DATA = 0x605B1CD0, 0x603A0E38 + 8 * (TAG >> 4), 0x60410F36
    ok = True
    res = {}
    for name, path in (("pinned", pinned), ("menu", menu)):
        with Scenario(path, name=name) as sc:
            sc.unstub(scenario.SETTINGS_GETTER)
            sc.w16(INDEX, TAG); sc.w16(INDEX + 2, 1); sc.w32(INDEX + 4, DATA)
            for r in (0, 1):
                for v in range(5):
                    sp_ = 0x7D0F0000
                    sc.w8(DATA, v); sc.w8(R, r); sc.w8(L, 0xEE); sc.w8(C, 0xEE)
                    sc.w32(LV + 32, 0); sc.w8(LV + 4, 0x55); sc.w8(LV + 5, 0x66); sc.w32(LV + 36, 0)
                    sc.w32(sp_ + 32, RET)
                    x = sc.piece(HOOK_A, [RET], {"sp": sp_, "d0": 0x1234, "d2": 0xD2D2, "d3": 0xD3D3, "a2": 0xA2A2, "a3": 0xA3A3})
                    g = x.regs
                    res[(name, "A", r, v)] = (x.fault, sc.r8(L), sc.r8(C), sc.r8(LV + 4), sc.r8(LV + 5), sc.r32(LV + 36),
                                              g.get("sp", 0) - sp_, g.get("d2"), g.get("d3"), g.get("a2"), g.get("a3"))
            for mode in (2, 0):
                for l2 in (0, 1):
                    for c in range(5):
                        sc.w16(0x7D400000, mode); sc.w8(L2, l2); sc.w8(C, c)
                        x = sc.piece(HOOK_K, [K_END], {"a2": 0x7D400000})
                        res[(name, "K", mode, l2, c)] = (x.fault, x.regs.get("d0", 0) & 0xFFFF)
    for r in (0, 1):
        for v in range(5):
            p, m = res[("pinned", "A", r, v)], res[("menu", "A", r, v)]
            want_l = 1 if r and v != OFF else 0
            want = (None, want_l, v if r else 0xEE, 0 if want_l else 0x55, 1 if want_l else 0x66, 0x1234, 32, 0xD2D2, 0xD3D3, 0xA2A2, 0xA3A3)
            good = m == want and (p[1:2] + p[3:]) == ((r,) + tuple(x if r else y for x, y in zip((0, 1), (0x55, 0x66))) + want[5:])
            ok &= good
            OUT("  T_A R=%d setting=%d: menu L=%d C=0x%02X struct+4=0x%02X +5=0x%02X +36=0x%X sp+%d d2,d3,a2,a3 kept=%s fault=%s | "
                "pinned L=%d  -> %s" % (r, v, m[1], m[2], m[3], m[4], m[5], m[6], m[7:] == want[7:], m[0], p[1],
                                        "ok" if good else "NOT OK"))
    for mode in (2, 0):
        for l2 in (0, 1):
            for c in range(5):
                p, m = res[("pinned", "K", mode, l2, c)], res[("menu", "K", mode, l2, c)]
                lines = mode == 2 and l2 == 1
                want = (0xFF00 if c == BLACK else 0x0200) if lines else 0xFF00
                good = m == (None, want) and p == (None, 0x0200 if lines else 0xFF00)
                ok &= good
                OUT("  T_K packet mode %d L2=%d C=%d: menu gain 0x%04X, pinned 0x%04X -> %s" % (
                    mode, l2, c, m[1], p[1], "ok" if good else "NOT OK %s %s" % (m[0], p[0])))
    OUT("  S11 RESULT: %s" % ("PASS" if ok else "FAIL"))
    return ok


def main():
    which, base, pinned, menu = sys.argv[1:5]
    todo = ["s8", "s9", "s10", "s11"] if which == "all" else [which]
    ok = True
    for s in todo:
        ok &= globals()[s](base, pinned, menu)
        OUT("")
    sys.exit(0 if ok else 1)


main()

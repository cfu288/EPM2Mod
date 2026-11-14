"""Scenario tests S6 and S7 of the focus-peaking builds (NOTES.md section 14). Uses tools/emu.

    python3 scen_direct4.py SCENARIO PINNED_BLOCK0 NAME=PATCHED_BLOCK0 [NAME=PATCHED_BLOCK0 ...]
    SCENARIO: s6 s7 or all. The block-0 files come from tools/emu/patchblock.py ... -o /tmp/scratch/x.block0.bin

S6  Picture Mode change to the Velvia entry (ART 7, picture mode 106) and back, as the quick menu sets it: the
    setting 38017 changes between live-view frames (6 -> 7, 7 -> 8, 8 -> 7, 7 -> 6). After each frame the art code
    that the mov layer chose (0xA07507CC) and its movie variant go through the six-axis stage of the colour
    parameters: the dispatch of 0x7E56D1C3 (table 0x7E78C254, index code - 9), run as a code piece from 0x7E56D2AB
    (d3 = art code) to one of the function's own continuation points. Then the same piece for every art code 9-184.
    FAULT = the CPU leaves block 0. "n/a" = the handler needs job data that a piece does not have (Cross Process).
    The live-view rig alone does not reach this stage (it gives the IMG library no colour work), which is why S1 to
    S5 missed the fault.
S7  The sleep routine "pwr_standby start" 0x7E53A55C, called as the SRAM code calls it (frame of the call at
    flash 0x7F14B0F7 = SRAM 0x470010F7), 400 instructions. Reported: whether its first instructions are the stock
    ones and whether the run enters mov_art_set_line_yc_param (0x7E6CD9D6), which the stock routine never does.
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools", "emu"))
import scenario  # noqa: E402
from liveview import LiveView, EXPOSE  # noqa: E402

BASE = 0x7E421020
PM, ART_TYPE = 38017, 17601
NAMES = {100: "ART 1", 101: "ART 2", 102: "ART 3", 103: "ART 4", 104: "ART 5", 105: "ART 6 (Vis 250D)",
         106: "ART 7 (Velvia)", 107: "ART 8 (Superia 400)"}
SIX_AXIS_PIECE = 0x7E56D2AB        # after `movbu (16,sp),d3`: range test, table 0x7E78C254, jmp (a0)
SIX_AXIS_STOPS = [0x7E56D8D8, 0x7E56D76A, 0x7E56D92D, 0x7E56D9DA, 0x7E56D9E4]
LV_TABLE, MOVIE_TABLE = 0x7E7FF05C, 0x7E7FF008    # colour-tone getter 0x7E6CBFD3: picture mode -> art code
OUT = print


def in_block0(sc, pc):
    return BASE <= pc < BASE + len(sc.image)


def six_axis(sc, code):
    """Run the six-axis dispatch for one art code. Returns (verdict, text)."""
    r = sc.piece(SIX_AXIS_PIECE, SIX_AXIS_STOPS, {"d3": code, "a2": 0x10000, "a3": 0x7D600000}, insn_limit=3000,
                 label="six-axis %d" % code)
    pc = r.regs.get("pc", 0)
    if not r.fault:
        return "ok", "reaches 0x%08X in %d instructions" % (pc, r.insns)
    if in_block0(sc, pc):
        # Cross Process (85, 87): the handler goes on into the scene statistics code, which needs the job data of
        # a real call. The piece has none. The run stays in block 0; it counts only if it differs from pinned.
        return "n/a", "handler needs job data that the piece does not give (%s)" % r.fault.splitlines()[0][:60]
    return "FAULT", r.fault.splitlines()[0]


def movie_code(image, pm):
    """The art code that the getter's movie table gives for a picture mode: the handler is `mov imm,d2`."""
    h = struct.unpack_from("<I", image, MOVIE_TABLE - BASE + 4 * (pm - 100))[0] - BASE
    return image[h + 1] if image[h] == 0x8A else struct.unpack_from("<H", image, h + 1)[0]


def s6(pinned, patched):
    OUT("S6. Picture Mode 105 -> 106 -> 107 -> 106 -> 105 (ART 6, 7, 8, 7, 6), one frame each, request clear, art type 1.")
    OUT("    After each frame: the six-axis dispatch for the art code of the frame and for its movie code.")
    results = {}
    for name, path in [("pinned", pinned)] + patched:
        bad, sweep = [], {}
        with LiveView(path, name=name) as lv:
            lv.settings[PM] = 105
            lv.settings[ART_TYPE] = 1
            lv.start()
            for pm in (105, 106, 107, 106, 105):
                lv.settings[PM] = pm
                f = lv.frame()
                code = lv.sc.r8(EXPOSE)
                mcode = movie_code(lv.sc.image, pm)
                row = []
                for what, c in (("live view", code), ("movie", mcode)):
                    v, t = six_axis(lv.sc, c)
                    row.append("%s code %d: %s, %s" % (what, c, v, t))
                    if v == "FAULT":
                        bad.append("%s %s code %d" % (NAMES[pm], what, c))
                OUT("  [%s] %s: frame picture %s%s; %s" % (name, NAMES[pm], f.state["picture"],
                                                          ", FRAME FAULT" if f.faults else "", "; ".join(row)))
            for c in range(9, 185):
                sweep[c] = six_axis(lv.sc, c)
        faults = [c for c in sweep if sweep[c][0] == "FAULT"]
        na = [c for c in sweep if sweep[c][0] == "n/a"]
        results[name] = sweep
        diff = [c for c in sweep if sweep[c] != results["pinned"][c]]
        OUT("  [%s] all art codes 9-184: %d FAULT %s; not judged %s; codes whose result differs from pinned: %s" % (
            name, len(faults), faults or "", na or "none", diff or "none"))
        for c in faults[:4]:
            OUT("      code %d: %s" % (c, sweep[c][1]))
        OUT("  S6 RESULT [%s]: %s" % (name, "PASS" if not bad and not faults and not diff else
                                      "FAIL: " + ", ".join(bad or ["art codes %s" % (faults or diff)])))


def s7(pinned, patched):
    OUT("S7. pwr_standby start 0x7E53A55C, called with the frame of the SRAM code's call (flash 0x7F14B0F7), 400")
    OUT("    instructions; callees run as far as they get (kernel services are not modelled here).")
    base = open(pinned, "rb").read()
    for name, path in [("pinned", pinned)] + patched:
        img = open(path, "rb").read()
        same = all(img[a - BASE:b - BASE] == base[a - BASE:b - BASE] for a, b in ((0x7E53A55C, 0x7E53A700), (0x7E50A201, 0x7E50A3C2)))
        with scenario.Scenario(path, name=name) as sc:
            sc.write(0x7D600000, bytes(0x200))
            r = sc.call(0x7E53A55C, {"a0": 0x7D600000, "a1": 0x7D600100}, frame=sc.frame_at(0x7F14B0F7), insn_limit=400,
                        label="pwr_standby start")
            stock_start = {0x7E53A55C, 0x7E53A55D, 0x7E53A55E} <= r.pcs
            stray = 0x7E6CD9D6 in r.pcs
            OUT("  [%s] bytes of 0x7E53A55C-0x7E53A700 and 0x7E50A201-0x7E50A3C2 equal to pinned: %s; first three stock "
                "instructions ran: %s; entered mov_art_set_line_yc_param at 0x7E6CD9D6: %s; end: %s" % (
                    name, same, stock_start, stray, (r.fault or "returned").splitlines()[0][:110]))
            OUT("  S7 RESULT [%s]: %s" % (name, "PASS" if same and stock_start and not stray else
                                          "FAIL: the sleep routine is overwritten"))


def main():
    which, pinned = sys.argv[1], sys.argv[2]
    patched = [tuple(a.split("=", 1)) for a in sys.argv[3:]]
    for n, fn in (("s6", s6), ("s7", s7)):
        if which in (n, "all"):
            fn(pinned, patched)
            OUT("")


main()

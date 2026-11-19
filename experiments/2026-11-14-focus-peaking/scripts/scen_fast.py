"""Scenario tests of the build peaking-fast (NOTES.md section 17). Uses emulator.

    python3 scen_fast.py SCENARIO BASE_BLOCK0 PINNED_BLOCK0 FAST_BLOCK0 [PNG_DIR]
    python3 scen_fast.py s18 FAST_BLOCK0 DEBUG_FAST_BLOCK0
    SCENARIO: s12 s13 s14 or all (s18 is not part of all: it takes other files)
    BASE    the build without focus peaking (seven-films-6-interval-240-level-adjust)
    PINNED  peaking-colours (the pinned build)
    FAST    peaking-fast
    PNG_DIR folder for the pictures of S12 (outside the repository)
    The block-0 files are `block0_0100.bin` of `python3 tools/oetool.py unpack build/NAME.BIN /tmp/scratch/NAME`.

S12  Red, Yellow, Blue on the synthetic frame of scen_colours.py, PINNED and FAST. Pass = every pixel of the
     FAST picture equals the block model: rows in pairs, groups of 4 pixels; a group of the first row with a
     line byte >= 64 among its bytes 0-3 and 8-11 -> the colour over the group in both rows; else the old
     pixels. The line image is not changed, usGain2 = 0, registers kept, a picture in every frame. PINNED must
     equal the pixel model (line byte >= 64 -> the colour), as in scen_colours.py. Prints the instructions from
     the pass 9 hook to the next stock instruction for both images, for the synthetic frame and for a frame
     without lines, and how many pixels differ between the two builds.
S13  White (3, 0, 6) = PINNED and Off (1) = BASE: scen_colours.py S13 with FAST in the place of the colours build.
S14  T_K alone on small frames in scratch RAM: packet mode 2 / 0, L2, C = 0 to 6, and frames with 1, 2, 3, 4 and
     5 rows, a width that is not a multiple of 4, a row length that is not a multiple of 4 bytes (white lines,
     nothing written), buffers that are not word-aligned (white lines). Pass = the block model, sp, d2, d3, a2,
     a3 kept, no write outside the picture.
S18  The timing probe of the build debug-log-peaking-fast (spec log-peaking-time, event pk_stats). The
     emulator's timer 0x98900074 goes down by 1 per read, so the test moves the stored start time itself.
     (a) The two routines alone, each from its hook site in pass 9 to the next stock instruction, 20 passes:
     the replaced instructions have run (ucMode 2, ucBit 16), sp, d2, d3, a2, a3 kept (and d1, a0, a1 in
     T_TIME0), T_TIME0 stores the timer value; the start time is then moved back by a known number of
     microseconds; one record per 8 passes with the sum of these times (and 1 per pass from the timer) and
     usGain2 of the last pass. (b) 18 live-view frames each of Red, White and the Key Line art filter:
     DEBUG_FAST gives the same pass 9 gain as FAST and for Red the same picture on the synthetic frame; the
     ring holds two pk_stats records with the gain 0 / 0x0200 / 0xFF00. (b) does not test the times.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
from scenario import Scenario  # noqa: E402

# scen_colours.py runs its main() when it is imported. Take its helpers without that last line.
_src = open(os.path.join(HERE, "scen_colours.py")).read()
assert _src.rstrip().endswith("\nmain()")
_sc = {"__file__": os.path.join(HERE, "scen_colours.py"), "__name__": "scen_colours"}
_argv, sys.argv = sys.argv, sys.argv[:1]
exec(compile(_src.rstrip()[:-len("main()")], "scen_colours.py", "exec"), _sc)
sys.argv = _argv
open_lv, request, anomalies, synthetic, png, s13_colours = (_sc[k] for k in (
    "open_lv", "request", "anomalies", "synthetic", "png", "s13"))
NATURAL, TAG, L, L2, C = _sc["NATURAL"], _sc["TAG"], _sc["L"], _sc["L2"], _sc["C"]
COLOURS, THRESHOLD, HOOK_K, K_END = _sc["COLOURS"], _sc["THRESHOLD"], _sc["HOOK_K"], _sc["K_END"]
RED, YELLOW, BLUE, WHITE = 2, 4, 5, 3
OUT = print


def pixel_model(pic, line, w, h, mem, col):
    """The pinned build: a pixel whose line byte (the middle one) is >= THRESHOLD gets the colour."""
    want = bytearray(pic)
    for y in range(h):
        for x in range(w - w % 4):
            o = (y * mem + x) * 3
            if line[o + 1] >= THRESHOLD:
                want[o:o + 3] = bytes(col)
    return bytes(want)


def block_model(pic, line, w, h, mem, col):
    """peaking-fast: rows in pairs, groups of 4 pixels. Bytes 0-3 and 8-11 of the group in the first row decide."""
    want = bytearray(pic)
    for y in range(0, h - h % 2, 2):
        for g in range(w // 4):
            o = (y * mem + 4 * g) * 3
            if max(line[o:o + 4] + line[o + 8:o + 12]) >= THRESHOLD:
                for row in (y, y + 1):
                    p = (row * mem + 4 * g) * 3
                    want[p:p + 12] = bytes(col) * 4
    return bytes(want)


def frame(image, value, lines=True):
    """One live-view frame with the synthetic picture (and line image) written before the code of hook K runs."""
    with open_lv(image, "menu", NATURAL) as lv:
        sc = lv.sc
        lv.settings[TAG] = value
        got = {}

        def fill(sc, g):
            if not got.get("armed"):
                return
            ctx = sc.r32(sc.r32(g["sp"] + 12) + 32)
            got["pic"], got["line"] = sc.r32(ctx + 16), sc.r32(ctx + 20)
            got["mem"], got["w"], got["h"] = sc.r16(ctx + 36), sc.r16(ctx + 40), sc.r16(ctx + 42)
            p, l = synthetic(got["w"], got["h"])
            if not lines:
                l = bytes(len(l))
            got["before"], got["limg"] = p, l
            sc.write(got["pic"], p)
            sc.write(got["line"], l)
            got["regs"] = {k: g[k] for k in ("sp", "d2", "d3", "a2", "a3")}
            got["i0"] = g["insns"]

        def after(sc, g):
            if not got.get("armed") or "pic" not in got:
                return
            n = got["mem"] * got["h"] * 3
            got["after"], got["line_after"] = sc.read(got["pic"], n), sc.read(got["line"], n)
            got["gain"] = g["d0"] & 0xFFFF
            got["kept"] = got["regs"] == {k: g[k] for k in ("sp", "d2", "d3", "a2", "a3")}
            got["insns"] = g["insns"] - got["i0"]
            got["armed"] = False

        sc.probe(HOOK_K, fill, "pass 9 hook K: write the synthetic frame")
        sc.probe(K_END, after, "pass 9 after the gain: read the picture")
        lv.start()
        request(lv, True)
        f = lv.frame()
        bad = anomalies(lv, f)
        got["armed"] = True
        f = lv.frame()
        got["bad"] = bad + anomalies(lv, f)
        got["picture"] = f.state["picture"] and sc.r8(L) == 1 and sc.r8(C) == value
        return got


def s12(base, pinned, fast, outdir):
    OUT("S12. Red, Yellow, Blue on the synthetic frame: the pinned loop and the fast loop on the firmware's own buffers.")
    ok = True
    made = {}
    for value in (RED, YELLOW, BLUE):
        name, col = COLOURS[value]
        a, b = frame(pinned, value), frame(fast, value)
        w, h, mem = b["w"], b["h"], b["mem"]
        assert (a["w"], a["h"], a["mem"], a["before"], a["limg"]) == (w, h, mem, b["before"], b["limg"])
        px = lambda x, y: sum(1 for i in range(0, len(x), 3) if x[i:i + 3] != y[i:i + 3])
        want_a, want_b = pixel_model(a["before"], a["limg"], w, h, mem, col), block_model(b["before"], b["limg"], w, h, mem, col)
        good_a = a["after"] == want_a and a["gain"] == 0 and a["kept"]
        good_b = (b["after"] == want_b and b["gain"] == 0 and b["kept"] and b["line_after"] == b["limg"] and not b["bad"]
                  and b["picture"])
        ok &= good_a and good_b
        OUT("  [%s] %d x %d (row length %d pixels), picture 0x%08X, line image 0x%08X" % (name.capitalize(), w, h, mem, b["pic"], b["line"]))
        OUT("      pinned: pixels that differ from the pixel model: %d; coloured pixels %d; %d instructions -> %s" % (
            px(a["after"], want_a), px(a["after"], a["before"]), a["insns"], "ok" if good_a else "NOT OK"))
        OUT("      fast:   pixels that differ from the block model: %d; coloured pixels %d; %d instructions; usGain2 0x%04X; "
            "line image unchanged %s; sp, d2, d3, a2, a3 kept %s; anomalies %s; picture %s -> %s" % (
                px(b["after"], want_b), px(b["after"], b["before"]), b["insns"], b["gain"], b["line_after"] == b["limg"],
                b["kept"], b["bad"] or "none", b["picture"], "ok" if good_b else "NOT OK"))
        only_a = sum(1 for i in range(0, len(want_a), 3) if a["after"][i:i + 3] != a["before"][i:i + 3] and b["after"][i:i + 3] == b["before"][i:i + 3])
        only_b = sum(1 for i in range(0, len(want_a), 3) if a["after"][i:i + 3] == a["before"][i:i + 3] and b["after"][i:i + 3] != b["before"][i:i + 3])
        OUT("      the stated difference: %d pixels differ between the two builds (%d coloured only by pinned, %d only by fast)" % (
            px(a["after"], b["after"]), only_a, only_b))
        made[name], made["size"] = b["after"], (w, h)
        made["pinned-" + name] = a["after"]
    a, b = frame(pinned, RED, lines=False), frame(fast, RED, lines=False)
    good = a["after"] == a["before"] and b["after"] == b["before"] and a["gain"] == b["gain"] == 0
    ok &= good
    OUT("  [a frame without lines] pinned %d instructions, fast %d instructions; both leave the picture as it is: %s" % (
        a["insns"], b["insns"], good))
    a, b = frame(pinned, WHITE), frame(fast, WHITE)
    good = (a["after"] == a["before"] == b["after"] and a["gain"] == b["gain"] == 0x0200 and a["insns"] == b["insns"]
            and b["line_after"] == b["limg"])
    ok &= good
    OUT("  [White] pinned %d instructions, fast %d instructions; picture and line image untouched, usGain2 0x%04X: %s" % (
        a["insns"], b["insns"], b["gain"], good))
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        w, h = made["size"]
        for name in ("red", "yellow", "blue", "pinned-red"):
            png(os.path.join(outdir, "s12-fast-%s.png" % name), w, h, made[name])
            OUT("  wrote s12-fast-%s.png" % name)
    OUT("  S12 RESULT: %s" % ("PASS" if ok else "FAIL"))
    return ok


def s14(base, pinned, fast):
    OUT("S14. T_K alone, from the hook site in pass 9 to the next stock instruction. Small frames in scratch RAM.")
    ARG, CTX, PKT, PIC, LINE = 0x7D400000, 0x7D400100, 0x7D400200, 0x7D401000, 0x7D410000
    GUARD = 96
    ok = True
    with Scenario(fast, name="fast") as sc:
        def one(mode, l2, c, w=8, h=2, mem=64, pic_at=PIC, line_at=LINE, seed=1):
            n = mem * 3 * h
            pic0 = bytes((10 + 7 * i + seed) % 251 for i in range(n))
            line0 = bytearray(n)
            state = seed * 2654435761 % 2**32
            for y in range(h):
                for x in range(mem):
                    state = (state * 1103515245 + 12345) % 2**31
                    v = (0, 0, 0, 0, 0, 63, 64, 255)[(state >> 16) % 8]
                    line0[(y * mem + x) * 3:(y * mem + x) * 3 + 3] = bytes((v, v, v))
            sp_ = 0x7D0F0000
            sc.w32(sp_ + 12, ARG); sc.w32(ARG + 32, CTX)
            sc.w32(CTX + 16, pic_at); sc.w32(CTX + 20, line_at)
            sc.w16(CTX + 36, mem); sc.w16(CTX + 40, w); sc.w16(CTX + 42, h)
            sc.w16(PKT, mode); sc.w8(L2, l2); sc.w8(C, c)
            guard = bytes([0xA5]) * GUARD
            sc.write(pic_at - GUARD, guard + pic0 + guard); sc.write(line_at, bytes(line0))
            regs = {"sp": sp_, "a2": PKT, "a3": 0xA3A3A3A0, "d2": 0xD2D2, "d3": 0xD3D3}
            x = sc.piece(HOOK_K, [K_END], dict(regs))
            g = x.regs
            kept = all(g.get(k) == v for k, v in regs.items())
            around = sc.read(pic_at - GUARD, GUARD) == guard and sc.read(pic_at + n, GUARD) == guard
            return x.fault, g.get("d0", 0) & 0xFFFF, pic0, bytes(line0), sc.read(pic_at, n), sc.read(line_at, n), kept and around, x.insns

        for mode in (2, 0):
            for l2 in (0, 1):
                for c in range(7):
                    fault, gain, pic0, line0, pic, line, kept, n = one(mode, l2, c)
                    lines = mode == 2 and l2 == 1
                    if lines and c in COLOURS:
                        want, wg = block_model(pic0, line0, 8, 2, 64, COLOURS[c][1]), 0
                    else:
                        want, wg = pic0, (0x0200 if lines else 0xFF00)
                    good = fault is None and gain == wg and pic == want and line == line0 and kept
                    ok &= good
                    OUT("  packet mode %d L2=%d C=%d: gain 0x%04X, pixels changed %d, registers and guard bytes kept %s, %d insns -> %s" % (
                        mode, l2, c, gain, sum(1 for i in range(0, len(pic), 3) if pic[i:i + 3] != pic0[i:i + 3]), kept, n,
                        "ok" if good else "NOT OK %s" % fault))
        for seed in range(2, 8):
            for w, h, mem in ((8, 2, 64), (8, 3, 64), (8, 4, 8), (10, 5, 12), (16, 4, 16), (7, 2, 8), (640, 6, 640)):
                for c in (RED, YELLOW, BLUE):
                    fault, gain, pic0, line0, pic, line, kept, n = one(2, 1, c, w=w, h=h, mem=mem, seed=seed)
                    want = block_model(pic0, line0, w, h, mem, COLOURS[c][1])
                    good = fault is None and gain == 0 and pic == want and line == line0 and kept
                    ok &= good
                    if seed == 2 or not good:
                        OUT("  %s, %d x %d, row length %d: gain 0x%04X, pixels changed %d, as the block model %s, kept %s -> %s" % (
                            COLOURS[c][0], w, h, mem, gain, sum(1 for i in range(0, len(pic), 3) if pic[i:i + 3] != pic0[i:i + 3]),
                            pic == want, kept, "ok" if good else "NOT OK %s" % fault))
        OUT("  (the same seven sizes with five more line images each: %s)" % ("all ok" if ok else "see above"))
        for what, kw in (("one row", {"h": 1}), ("a row length of 9 pixels = 27 bytes", {"mem": 9, "h": 4}),
                         ("picture buffer at an odd address", {"pic_at": PIC + 1}), ("line buffer at address + 2", {"line_at": LINE + 2}),
                         ("no rows", {"h": 0}), ("a width of 3 pixels", {"w": 3})):
            fault, gain, pic0, line0, pic, line, kept, n = one(2, 1, RED, **kw)
            good = fault is None and gain == 0x0200 and pic == pic0 and kept
            ok &= good
            OUT("  Red, %s: gain 0x%04X (white lines), pixels changed %d, kept %s -> %s" % (
                what, gain, sum(1 for i in range(0, len(pic), 3) if pic[i:i + 3] != pic0[i:i + 3]), kept, "ok" if good else "NOT OK %s" % fault))
    OUT("  S14 RESULT: %s" % ("PASS" if ok else "FAIL"))
    return ok


RING0, PST, TIMER, EV_STATS = 0xBE4F9000, 0xBE4FD040, 0x98900074, 261
T0_SITE, T0_END, TICK_SITE, TICK_END = 0x7E72675C, 0x7E726761, 0x7E726774, 0x7E726779


def ring(sc, event=EV_STATS):
    import struct
    magic, w = struct.unpack("<2I", sc.read(RING0, 8))
    if magic != 0x314C5045:
        return []
    rows = [struct.unpack("<HHIII", sc.read(RING0 + 32 + 16 * (n % 512), 16)) for n in range(max(0, w - 512), w)]
    return [r for r in rows if r[0] == event]


def s18(fast, debug):
    OUT("S18. The timing probe (pk_stats) of debug-log-peaking-fast.")
    ok = True
    JOB = 0x7D400300
    with Scenario(debug, name="debug-fast") as sc:
        sc.write(PST, bytes(128))
        sc.write(RING0, bytes(32))
        want, total, good_all = [], 0, True
        for n in range(1, 21):
            spent = (0, 137, 60000)[n % 3]          # microseconds between the two routines in this pass
            gain = (0, 0x0200, 0xFF00)[n % 3]
            regs = {"sp": 0x7D0F0000, "d0": 0x5555, "d1": 0x1111, "d2": 0x2222, "d3": 0x3333, "a0": 0x7D400000,
                    "a1": 0x7D400100, "a2": 0x7D400200, "a3": JOB}
            sc.write(JOB, bytes(64))
            sc.w32(PST + 88, 0)
            x = sc.piece(T0_SITE, [T0_END], dict(regs))
            start = sc.r32(PST + 88)
            good = (x.fault is None and all(x.regs.get(k) == v for k, v in regs.items() if k != "d0") and x.regs["d0"] == 2
                    and sc.r8(JOB + 37) == 2 and 0 < start < 0x40000000)
            sc.w32(PST + 88, start + spent)         # as if the first routine had run that much earlier
            sc.w16(JOB + 34, gain)
            y = sc.piece(TICK_SITE, [TICK_END], dict(regs))
            good &= (y.fault is None and all(y.regs.get(k) == regs[k] for k in ("sp", "d2", "d3", "a2", "a3"))
                     and sc.r8(JOB + 36) == 16 and sc.r16(JOB + 34) == gain)
            total += spent + 1                      # the emulator's timer: 1 between the two reads
            if n % 8 == 0:
                want.append((total, gain))
                total = 0
            good_all &= good
            if not good:
                OUT("  pass %d: NOT OK faults %s %s, start time 0x%08X" % (n, x.fault, y.fault, start))
        got = [(r[3], r[4]) for r in ring(sc)]
        ok &= good_all and got == want
        OUT("  (a) T_TIME0 and T_TICK alone, 20 passes: the replaced instructions ran, the registers are kept, the timer "
            "value is stored: %s; records (loop_us, gain) %s, expected %s -> %s" % (
                good_all, got, want, "ok" if good_all and got == want else "NOT OK"))
    for what, pm, value, ask, gain in (("Red", NATURAL, RED, True, 0), ("White", NATURAL, WHITE, True, 0x0200),
                                       ("Key Line art filter, no MF Assist", _sc["KEY_LINE"], 1, False, 0xFF00)):
        res = {}
        for name, image in (("fast", fast), ("debug", debug)):
            with open_lv(image, "menu", pm) as lv:
                sc = lv.sc
                lv.settings[TAG] = value
                seen = {"gain": [], "pic": None}

                def fill(sc, g, seen=seen):
                    if value == RED and len(seen["gain"]) == 16:
                        ctx = sc.r32(sc.r32(g["sp"] + 12) + 32)
                        seen["at"], seen["n"] = sc.r32(ctx + 16), sc.r16(ctx + 36) * sc.r16(ctx + 42) * 3
                        p, l = synthetic(sc.r16(ctx + 40), sc.r16(ctx + 42))
                        sc.write(seen["at"], p)
                        sc.write(sc.r32(ctx + 20), l)

                def after(sc, g, seen=seen):
                    seen["gain"].append(g["d0"] & 0xFFFF)
                    if "at" in seen and seen["pic"] is None:
                        seen["pic"] = sc.read(seen["at"], seen["n"])

                sc.probe(HOOK_K, fill, "pass 9 hook K")
                sc.probe(K_END, after, "pass 9 after the gain")
                lv.start()
                if ask:
                    request(lv, True)
                bad = []
                for _ in range(18):
                    bad += anomalies(lv, lv.frame())
                seen["bad"], seen["stats"] = bad, [(r[3], r[4]) for r in ring(sc)] if name == "debug" else None
                res[name] = seen
        a, b = res["fast"], res["debug"]
        loops = [x[0] for x in b["stats"]]
        good = (a["gain"] == b["gain"] and a["pic"] == b["pic"] and not b["bad"] and len(b["stats"]) == len(b["gain"]) // 8
                and all(x[1] == gain for x in b["stats"][-1:]) and b["gain"][-1] == gain and all(8 <= v < 8000 for v in loops))
        ok &= good
        OUT("  (b) %s: %d passes 9, gains fast %s, debug %s; picture of pass 17 equal: %s; anomalies %s; pk_stats (loop_us, gain): %s -> %s" % (
            what, len(b["gain"]), sorted(set("0x%04X" % g for g in a["gain"])), sorted(set("0x%04X" % g for g in b["gain"])),
            a["pic"] == b["pic"], b["bad"] or "none", [(x[0], "0x%04X" % x[1]) for x in b["stats"]], "ok" if good else "NOT OK"))
    OUT("  S18 RESULT: %s" % ("PASS" if ok else "FAIL"))
    return ok


def main():
    if sys.argv[1] == "s18":
        ok = s18(*sys.argv[2:4])
        sys.exit(0 if ok else 1)
    which, base, pinned, fast = sys.argv[1:5]
    outdir = sys.argv[5] if len(sys.argv) > 5 else None
    ok = True
    for s in (["s12", "s13", "s14"] if which == "all" else [which]):
        if s == "s12":
            ok &= s12(base, pinned, fast, outdir)
        elif s == "s13":
            ok &= s13_colours(base, pinned, fast)
        else:
            ok &= s14(base, pinned, fast)
        OUT("")
    sys.exit(0 if ok else 1)


main()

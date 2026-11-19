"""Scenario tests of the build peaking-colours (NOTES.md section 16). Uses emulator.

    python3 scen_colours.py SCENARIO BASE_BLOCK0 PINNED_BLOCK0 COLOURS_BLOCK0 [PNG_DIR]
    SCENARIO: s12 s13 s14 or all
    BASE     the build without focus peaking (seven-films-6-interval-240-level-adjust)
    PINNED   peaking-menu-names
    COLOURS  peaking-colours
    PNG_DIR  folder for the pictures of S12 (outside the repository)
    The block-0 files are `block0_0100.bin` of `python3 tools/oetool.py unpack build/NAME.BIN /tmp/scratch/NAME`.

S12  Red, Yellow, Blue (setting 458 = 2, 4, 5), Natural, MF Assist request set. Before Key Line pass 9 chooses its
     gain, the test writes a synthetic frame into the two 3-byte buffers of the pass: a colour picture, and a line
     image with an edge. The firmware's new code then runs on them. Pass = every pixel of the picture equals the
     model (line byte >= 64 -> the colour, else the old pixel), usGain2 = 0, a picture in every frame, no anomaly.
     Writes PNG files: the picture before, the line image, the result per colour, and for White the model
     picture + 2 x line (the image processor does that add; the emulator does not compute it).
S13  White (3, and 0 and 6 = values outside the list) = PINNED: same memory writes, same device accesses, pass 9
     gain 0x0200, no stock pc lost (the pinned build's T_K2, which T_K3 replaces, is not stock code). Off (1) = BASE: as S8.
S14  T_K alone from its hook site, with a small frame (8 x 2 pixels) in scratch RAM, for packet mode 2 / 0, L2 and
     C = 0 to 6: the gain, the pixels, sp and d2, d3, a2, a3 kept. Also buffers that are not word-aligned and a
     frame with no rows: nothing is written and the gain is 512 (white lines).
"""
import os, struct, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "emulator"))
import scenario  # noqa: E402
from scenario import Scenario  # noqa: E402

# scen_menu.py runs its main() when it is imported. Take its helpers without that last line.
_src = open(os.path.join(HERE, "scen_menu.py")).read()
assert _src.rstrip().endswith("\nmain()")
_sm = {"__file__": os.path.join(HERE, "scen_menu.py"), "__name__": "scen_menu"}
_argv, sys.argv = sys.argv, sys.argv[:1]
exec(compile(_src.rstrip()[:-len("main()")], "scen_menu.py", "exec"), _sm)
sys.argv = _argv
open_lv, request, show, anomalies, run_frames, compare = (_sm[k] for k in (
    "open_lv", "request", "show", "anomalies", "run_frames", "compare"))
NATURAL, KEY_LINE = _sm["NATURAL"], _sm["KEY_LINE"]
L, R, L2, C, TAG = _sm["L"], _sm["R"], _sm["L2"], _sm["C"], _sm["TAG"]

OFF, RED, WHITE, YELLOW, BLUE = 1, 2, 3, 4, 5
COLOURS = {RED: ("red", (255, 0, 0)), YELLOW: ("yellow", (255, 255, 0)), BLUE: ("blue", (0, 80, 255))}
THRESHOLD = 64
HOOK_K, K_END = 0x7E726767, 0x7E72676D          # pass 9: the hooked `mov 65280,d0`, and the instruction after it
OUT = print
OLD_T_K2 = (0x7E4C93D8, 0x7E4C93F0)             # the pinned build's T_K2: the new build runs T_K3 in its place
_diff_pcs = _sm["diff_pcs"]


def _diff_pcs_k2(a, b, new_code=(), hook_sites=()):
    """diff_pcs, but the pinned build's own T_K2 instructions do not count as lost stock code."""
    d = _diff_pcs(a, b, new_code, hook_sites)
    d["only_base"] = [p for p in d["only_base"] if not OLD_T_K2[0] <= p < OLD_T_K2[1]]
    return d


_sm["diff_pcs"] = _diff_pcs_k2


def png(path, w, h, rgb):
    raw = b"".join(b"\0" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                           chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def ycc(r, g, b):
    """BT.601 full range."""
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return round(y), round(128 + 0.564 * (b - y)), round(128 + 0.713 * (r - y))


def synthetic(w, h):
    """(picture, line image): 3 bytes per pixel. Picture: four quadrants (black, white, mid grey, a colour ramp).
    Line image: a slanted edge 5 pixels wide with soft sides, and five bars with the values 32, 63, 64, 128, 255."""
    pic, line = bytearray(w * h * 3), bytearray(w * h * 3)
    for y in range(h):
        for x in range(w):
            if y < h // 2:
                p = (16, 16, 16) if x < w // 2 else (240, 240, 240)
            else:
                p = (128, 128, 128) if x < w // 2 else (255 * (x - w // 2) // (w // 2), 255 * (y - h // 2) // (h // 2), 160)
            pic[(y * w + x) * 3:(y * w + x) * 3 + 3] = bytes(p)
        c = 40 + y * (w - 80) // h                           # the edge crosses all four quadrants
        for dx, v in ((-4, 40), (-3, 100), (-2, 255), (-1, 255), (0, 255), (1, 255), (2, 255), (3, 100), (4, 40)):
            x = c + dx
            line[(y * w + x) * 3:(y * w + x) * 3 + 3] = bytes((v, v, v))
    for k, v in enumerate((32, 63, 64, 128, 255)):
        for y in range(20 + 30 * k, 40 + 30 * k):
            for x in range(w - 120, w - 20):
                line[(y * w + x) * 3:(y * w + x) * 3 + 3] = bytes((v, v, v))
    return bytes(pic), bytes(line)


def s12(base, pinned, colours, outdir):
    OUT("S12. Red, Yellow, Blue on a synthetic frame: the new code of pass 9 runs on the firmware's own buffers.")
    ok = True
    made = {}
    for value in (RED, YELLOW, BLUE, WHITE):
        with open_lv(colours, "menu", NATURAL) as lv:
            sc = lv.sc
            lv.settings[TAG] = value
            got = {}

            def fill(sc, g):
                if not got.get("armed"):
                    return
                ctx = sc.r32(sc.r32(g["sp"] + 12) + 32)
                got["pic"], got["line"] = sc.r32(ctx + 16), sc.r32(ctx + 20)
                got["mem"], got["w"], got["h"] = sc.r16(ctx + 36), sc.r16(ctx + 40), sc.r16(ctx + 42)
                assert got["mem"] == got["w"], got
                p, l = synthetic(got["w"], got["h"])
                got["before"], got["limg"] = p, l
                sc.write(got["pic"], p)
                sc.write(got["line"], l)
                got["regs"] = {k: g[k] for k in ("sp", "d2", "d3", "a2", "a3")}

            def after(sc, g):
                if not got.get("armed") or "pic" not in got:
                    return
                n = got["w"] * got["h"] * 3
                got["after"] = sc.read(got["pic"], n)
                got["line_after"] = sc.read(got["line"], n)
                got["gain"] = g["d0"] & 0xFFFF
                got["regs_after"] = {k: g[k] for k in ("sp", "d2", "d3", "a2", "a3")}
                got["armed"] = False

            sc.probe(HOOK_K, fill, "pass 9 hook K: write the synthetic frame")
            sc.probe(K_END, after, "pass 9 after the gain: read the picture")
            lv.start()
            how = request(lv, True)
            f = lv.frame()
            bad = anomalies(lv, f)
            got["armed"] = True
            f = lv.frame()
            bad += anomalies(lv, f)
            show(lv, f)
            w, h = got["w"], got["h"]
            p, l, a = got["before"], got["limg"], got["after"]
            if value == WHITE:
                good = a == p and got["gain"] == 0x0200 and got["line_after"] == l
                model = bytes(min(255, x + 2 * y) for x, y in zip(p, l))        # the image processor's add (not emulated)
                made["white"] = model
                OUT("  [White] the new code leaves the picture and the line image as they are: %s; usGain1 256, usGain2 0x%04X "
                    "(picture + 2 x line, done by the image processor)" % (a == p and got["line_after"] == l, got["gain"]))
            else:
                name, col = COLOURS[value]
                want = bytearray(p)
                n_line = 0
                for i in range(0, len(p), 3):
                    if l[i + 1] >= THRESHOLD:
                        want[i:i + 3] = bytes(col)
                        n_line += 1
                good = bytes(want) == a and got["gain"] == 0 and got["line_after"] == l
                diff = sum(1 for i in range(0, len(p), 3) if a[i:i + 3] != want[i:i + 3])
                seen = sorted(set(a[i:i + 3] for i in range(0, len(p), 3) if l[i + 1] >= THRESHOLD))
                made[name] = a
                OUT("  [%s] %d x %d, buffers 0x%08X (picture) 0x%08X (line image): %d line pixels (line byte >= %d); "
                    "pixels that differ from the model: %d; usGain2 0x%04X" % (name.capitalize(), w, h, got["pic"],
                                                                              got["line"], n_line, THRESHOLD, diff, got["gain"]))
                OUT("      the line pixels after the new code: %s = bytes %s -> Y %d Cb %d Cr %d (BT.601 full range, if "
                    "the bytes are R, G, B)" % (name, [tuple(s) for s in seen], *ycc(*col)))
                for v in (32, 63, 64, 128, 255):
                    k = (32, 63, 64, 128, 255).index(v)
                    i = ((30 + 30 * k) * w + w - 70) * 3
                    OUT("      bar with line value %3d: pixel before %s, after %s" % (v, tuple(p[i:i + 3]), tuple(a[i:i + 3])))
            kept = got["regs"] == got["regs_after"]
            good = good and kept and not bad and f.state["picture"] and lv.sc.r8(L) == 1 and lv.sc.r8(C) == value
            ok &= good
            OUT("      sp, d2, d3, a2, a3 kept: %s; anomalies: %s; picture: %s; %s -> %s" % (
                kept, bad or "none", f.state["picture"], how, "ok" if good else "NOT OK"))
            made.setdefault("before", p)
            made.setdefault("line", l)
            made["size"] = (w, h)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        w, h = made["size"]
        for name, what in (("before", "s12-0-picture-before.png"), ("line", "s12-1-line-image.png"), ("white", "s12-2-white-model.png"),
                           ("red", "s12-3-red.png"), ("yellow", "s12-4-yellow.png"), ("blue", "s12-5-blue.png")):
            png(os.path.join(outdir, what), w, h, made[name])
            OUT("  wrote %s" % what)
    OUT("  S12 RESULT: %s" % ("PASS" if ok else "FAIL"))
    return ok


def s13(base, pinned, colours):
    OUT("S13. White = PINNED, Off = BASE.")
    a_img, b_img, c_img = open(pinned, "rb").read(), open(colours, "rb").read(), open(base, "rb").read()
    ok = True
    for value in (WHITE, 0, 6):
        for pm, pm_name in ((NATURAL, "Natural"), (KEY_LINE, "Key Line")):
            fa, xa = run_frames(pinned, "pinned-menu", pm, value, True)
            fb, xb = run_frames(colours, "menu", pm, value, True)
            tag = "458=%d %s" % (value, pm_name)
            OUT("  [%s] pass 9 gain: pinned %s, colours %s; pass 7 ucExpose: pinned %s, colours %s; anomalies: %s" % (
                tag, ["0x%04X" % g for g in xa["gain2"]], ["0x%04X" % g for g in xb["gain2"]], xa["expose7"],
                xb["expose7"], [b for b in xb["bad"] if b] or "none"))
            ok &= compare(tag, "pinned", fa, "colours", fb, a_img, b_img, (C, C + 1))
            ok &= xb["gain2"] == [0x0200] == xa["gain2"] and xb["expose7"] == [3] and xb["L"] == 1 and not any(xb["bad"])
    for pm, pm_name in ((NATURAL, "Natural"), (KEY_LINE, "Key Line")):
        fa, xa = run_frames(base, "pinned", pm, OFF, False)
        fb, xb = run_frames(colours, "menu", pm, OFF, True)
        ok &= compare("Off " + pm_name, "base", fa, "colours", fb, c_img, b_img, (L, C + 1)) and xb["L"] == 0
        ok &= xb["gain2"] == xa["gain2"] and xb["expose7"] == xa["expose7"]
        OUT("  [Off %s] pass 9 gain: base %s, colours %s; L=%d" % (pm_name, ["0x%04X" % g for g in xa["gain2"]],
                                                                 ["0x%04X" % g for g in xb["gain2"]], xb["L"]))
    OUT("  S13 RESULT: %s" % ("PASS: White = the pinned build, Off = the build without peaking" if ok else "FAIL"))
    return ok


def s14(base, pinned, colours):
    OUT("S14. T_K alone, from the hook site in pass 9 to the next stock instruction. A frame of 8 x 2 pixels in scratch RAM.")
    ARG, CTX, PKT, PIC, LINE = 0x7D400000, 0x7D400100, 0x7D400200, 0x7D401000, 0x7D402000
    W, H, MEM = 8, 2, 64
    pic0 = bytes((10 + i) % 251 for i in range(MEM * 3 * H))
    line0 = bytearray(MEM * 3 * H)
    vals = [0, 63, 64, 255, 0, 200, 10, 64, 255, 0, 0, 0, 65, 0, 0, 63]          # line value per pixel, row by row
    for i, v in enumerate(vals):
        o = ((i // W) * MEM + i % W) * 3
        line0[o:o + 3] = bytes((v, v, v))
    line0[1 + 8 * 3] = 255                                                       # a pixel past the row width: not looked at
    ok = True
    with Scenario(colours, name="colours") as sc:
        def one(mode, l2, c, pic_at=PIC, line_at=LINE, rows=H):
            sp_ = 0x7D0F0000
            sc.w32(sp_ + 12, ARG); sc.w32(ARG + 32, CTX)
            sc.w32(CTX + 16, pic_at); sc.w32(CTX + 20, line_at)
            sc.w16(CTX + 36, MEM); sc.w16(CTX + 40, W); sc.w16(CTX + 42, rows)
            sc.w16(PKT, mode); sc.w8(L2, l2); sc.w8(C, c)
            sc.write(pic_at, pic0); sc.write(line_at, bytes(line0))
            regs = {"sp": sp_, "a2": PKT, "a3": 0xA3A3A3A0, "d2": 0xD2D2, "d3": 0xD3D3}
            x = sc.piece(HOOK_K, [K_END], dict(regs))
            g = x.regs
            kept = all(g.get(k) == v for k, v in regs.items())
            return x.fault, g.get("d0", 0) & 0xFFFF, sc.read(pic_at, len(pic0)), sc.read(line_at, len(line0)), kept, x.insns

        for mode in (2, 0):
            for l2 in (0, 1):
                for c in range(7):
                    fault, gain, pic, line, kept, n = one(mode, l2, c)
                    lines = mode == 2 and l2 == 1
                    want = bytearray(pic0)
                    if lines and c in COLOURS:
                        for i, v in enumerate(vals):
                            if v >= THRESHOLD:
                                o = ((i // W) * MEM + i % W) * 3
                                want[o:o + 3] = bytes(COLOURS[c][1])
                        wg = 0
                    else:
                        wg = 0x0200 if lines else 0xFF00
                    good = fault is None and gain == wg and pic == bytes(want) and line == bytes(line0) and kept
                    ok &= good
                    OUT("  packet mode %d L2=%d C=%d: gain 0x%04X, pixels changed %d, registers kept %s, %d insns -> %s" % (
                        mode, l2, c, gain, sum(1 for i in range(0, len(pic), 3) if pic[i:i + 3] != pic0[i:i + 3]), kept, n,
                        "ok" if good else "NOT OK %s" % fault))
        for what, kw in (("picture buffer at an odd address", {"pic_at": PIC + 1}), ("line buffer at address + 2", {"line_at": LINE + 2}),
                         ("no rows", {"rows": 0})):
            fault, gain, pic, line, kept, n = one(2, 1, RED, **kw)
            good = fault is None and gain == 0x0200 and pic == pic0 and kept
            ok &= good
            OUT("  Red, %s: gain 0x%04X, pixels changed %d, registers kept %s -> %s" % (
                what, gain, sum(1 for i in range(0, len(pic), 3) if pic[i:i + 3] != pic0[i:i + 3]), kept, "ok" if good else "NOT OK %s" % fault))
    OUT("  S14 RESULT: %s" % ("PASS" if ok else "FAIL"))
    return ok


def main():
    which, base, pinned, colours = sys.argv[1:5]
    outdir = sys.argv[5] if len(sys.argv) > 5 else None
    todo = ["s12", "s13", "s14"] if which == "all" else [which]
    ok = True
    for s in todo:
        ok &= s12(base, pinned, colours, outdir) if s == "s12" else globals()[s](base, pinned, colours)
        OUT("")
    sys.exit(0 if ok else 1)


main()

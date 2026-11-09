"""Steps 2b/2c, model-free: how does each setting change grays and colours relative to Natural?

1. Natural's tone response F (pre-curve value v -> JPEG code) is fitted from the gray row of all
   plain Natural shots as a monotone (isotonic) function in log2(v), then smoothed.
   v = ColorMatrix · (WB ⊙ raw), as in analyze_tone.py.
2. Every other shot's gray row is compared with F at the same v, per channel:
   - same for R, G, B and zero        -> same tone curve as Natural;
   - same for R, G, B but not zero    -> a different (luminance) tone curve;
   - different between R, G and B     -> channel-dependent curves (toning / split curves).
3. Colours: each shot's colour patches are compared with Natural's prediction through
   chroma (Cb, Cr magnitude) and hue angle in BT.601 YCbCr, to separate "saturation" from
   "hue shift" from "tone".

Writes out/modes_report.txt and out/gray_<shot>.png.
"""
import importlib.util
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import isotonic_regression

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
spec = importlib.util.spec_from_file_location("tone", os.path.join(HERE, "analyze_tone.py"))
tone = importlib.util.module_from_spec(spec); spec.loader.exec_module(tone)


def fit_F(V, J):
    """Monotone fit of JPEG code against log2(v), all channels pooled. Returns a callable."""
    x = np.log2(np.maximum(V.ravel(), 0.5)); y = J.ravel()
    o = np.argsort(x); x, y = x[o], y[o]
    yi = isotonic_regression(y).x
    grid = np.linspace(x.min(), x.max(), 200)
    # local averaging on the grid for a smooth, still monotone curve
    yg = np.array([yi[np.abs(x - g) < 0.15].mean() if np.any(np.abs(x - g) < 0.15) else np.nan for g in grid])
    ok = ~np.isnan(yg)
    grid, yg = grid[ok], np.maximum.accumulate(yg[ok])
    return lambda v: np.interp(np.log2(np.maximum(v, 0.5)), grid, yg), (grid, yg)


def ycc(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return y, -0.168736 * r - 0.331264 * g + 0.5 * b, 0.5 * r - 0.418688 * g - 0.081312 * b


def main():
    d, st, meta = tone.load()
    names = [str(n) for n in d["names"]]; roles = [str(r) for r in d["roles"]]
    rows = np.array([m["row"] for m in meta])
    plain = [k for k, n in enumerate(names) if roles[k] in ("B1", "B2", "B3", "B4", "B5", "X-base2", "D1-base",
                                                            "B0a", "B0b", "B0c", "X-base3")]
    V, J = tone.collect(d, st, meta, plain)
    F, (gx, gy) = fit_F(V, J)
    res = J - F(V)
    lines = [f"Natural tone response F from {len(V)} gray points; residual rms {np.sqrt(np.mean(res**2)):.2f} codes",
             "F (log2 v -> code): " + ", ".join(f"{2**x:.0f}:{y:.0f}" for x, y in zip(gx[::20], gy[::20]))]
    # middle gray: v giving code 118 (sRGB 0.18 = 118/255)
    v118 = 2 ** np.interp(118, gy, gx)
    lines.append(f"v at code 118 (sRGB middle gray): {v118:.0f}; code at v=4045: {F(4045.0):.0f}")

    base = [k for k in plain if roles[k] in ("B3", "X-base2", "D1-base", "X-base3")]
    lines.append("\nGray row vs Natural (code difference per channel, by Natural code band 0-64 / 64-128 / 128-192 / 192-255)")
    lines.append("Colour patches vs Natural prediction: chroma ratio (median) and hue shift (deg, median) by hue sextant")
    def colour_stats(k):
        v = tone.precurve(d, st, k)
        c = tone.usable(d, k) & (rows < 6)
        pred = F(v)
        y0, cb0, cr0 = ycc(pred[c]); y1, cb1, cr1 = ycc(d["jpg"][k][c])
        ch0, ch1 = np.hypot(cb0, cr0), np.hypot(cb1, cr1)
        h0 = np.degrees(np.arctan2(cr0, cb0)); dh = (np.degrees(np.arctan2(cr1, cb1)) - h0 + 180) % 360 - 180
        sext = ((h0 + 360) % 360 // 60).astype(int); sel = ch0 > 15
        cr = [np.median(ch1[sel & (sext == s)] / ch0[sel & (sext == s)]) if (sel & (sext == s)).sum() >= 3 else np.nan for s in range(6)]
        hs = [np.median(dh[sel & (sext == s)]) if (sel & (sext == s)).sum() >= 3 else np.nan for s in range(6)]
        return np.array(cr), np.array(hs), np.median(y1 - y0)

    base_cr = np.nanmedian([colour_stats(k)[0] for k in plain], 0)
    base_hs = np.nanmedian([colour_stats(k)[1] for k in plain], 0)
    lines.append("Natural's own colour rendering vs the per-channel model (baseline, removed below): chroma "
                 + " ".join(f"{x:.2f}" for x in base_cr) + "; hue " + " ".join(f"{x:+.0f}" for x in base_hs))
    lines.append("Hue sextants of the predicted colour (BT.601 angle atan2(Cr, Cb)): 0 blue-magenta, 1 magenta-red, "
                 "2 red-yellow, 3 yellow-green, 4 green-cyan, 5 cyan-blue")
    for k, n in enumerate(names):
        if k in plain:
            continue
        v = tone.precurve(d, st, k)
        ok = tone.usable(d, k)
        g = ok & (rows == 6)
        pred = F(v)
        dif = d["jpg"][k] - pred
        bands = []
        for lo, hi in ((0, 64), (64, 128), (128, 192), (192, 256)):
            m = g & (pred.mean(1) >= lo) & (pred.mean(1) < hi)
            bands.append("  ".join(f"{np.median(dif[m, c]):+5.1f}" for c in range(3)) if m.sum() >= 2 else "   n/a          ")
        c = ok & (rows < 6)
        y0, cb0, cr0 = ycc(pred[c]); y1, cb1, cr1 = ycc(d["jpg"][k][c])
        ch0, ch1 = np.hypot(cb0, cr0), np.hypot(cb1, cr1)
        h0, h1 = np.degrees(np.arctan2(cr0, cb0)), np.degrees(np.arctan2(cr1, cb1))
        dh = (h1 - h0 + 180) % 360 - 180
        sel = ch0 > 15
        sext = ((h0 + 360) % 360 // 60).astype(int)
        colour = " ".join(f"{np.median(ch1[sel & (sext == s)] / ch0[sel & (sext == s)]):.2f}/{np.median(dh[sel & (sext == s)]):+4.0f}"
                          if (sel & (sext == s)).sum() >= 3 else "  n/a   " for s in range(6))
        dy = np.median(y1 - y0)
        crk, hsk, _ = colour_stats(k)
        rel = " ".join(f"{a / b:4.2f}/{h - hb:+4.0f}" if not (np.isnan(a) or np.isnan(h)) else "  n/a    "
                       for a, b, h, hb in zip(crk, base_cr, hsk, base_hs))
        lines.append(f"{n[-4:]} {roles[k]:16s} gray R G B per band: " + " | ".join(bands))
        lines.append(f"      {'':16s} colours vs Natural: dY {dy:+5.1f}  chroma x / hue deg by sextant: {rel}")
        if roles[k] in ("A4-crossprocess", "M3-portrait", "A1-popart", "M4-monotone", "M1-vivid", "M2-muted"):
            plot_gray(v[g], d["jpg"][k][g], F, os.path.join(OUT, f"gray_{roles[k]}.png"), f"{n} {roles[k]} vs Natural F")
    open(os.path.join(OUT, "modes_report.txt"), "w").write("\n".join(lines) + "\n")
    np.savez(os.path.join(OUT, "natural_F.npz"), log2v=gx, code=gy)
    print("\n".join(lines))


def plot_gray(v, j, F, path, title):
    W, H = 640, 480
    im = Image.new("RGB", (W, H), "white"); dr = ImageDraw.Draw(im)
    lx = np.log2(np.maximum(v, 0.5)); x0, x1 = 0, 12
    xs = np.linspace(x0, x1, 300)
    pts = [(40 + (W - 60) * (x - x0) / (x1 - x0), H - 30 - (H - 50) * F(2 ** x) / 255) for x in xs]
    dr.line(pts, fill=(0, 0, 0), width=2)
    for l, jj in zip(lx, j):
        for c, col in zip(range(3), [(220, 40, 40), (40, 160, 40), (40, 40, 220)]):
            x, y = 40 + (W - 60) * (l[c] - x0) / (x1 - x0), H - 30 - (H - 50) * jj[c] / 255
            dr.ellipse([x - 3, y - 3, x + 3, y + 3], outline=col)
    dr.text((45, 8), title + " (black = Natural; x = log2 v, 0..12)", fill=(0, 0, 0))
    im.save(path)


if __name__ == "__main__":
    main()

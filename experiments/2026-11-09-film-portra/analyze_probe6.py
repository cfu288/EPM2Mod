"""Six-axis probe result: RAW Data Edits of PB090221 before (238-240) and after (244-246) flashing
sixaxis-probe-1 (Vivid, Muted, Portrait). Per chart hue column (36 hues, 10 degrees of HSV hue apart)
the chroma ratio after/before and the hue shift after-before, in BT.601 CbCr, averaged over the
chart rows whose patches are inside the 8-bit range.    ../../.venv/bin/python -I analyze_probe6.py"""
import json, sys, importlib.util
import numpy as np
sys.argv = ["x"]
sp = importlib.util.spec_from_file_location("ex", "extract.py"); ex = importlib.util.module_from_spec(sp); sp.loader.exec_module(ex)
lay = json.load(open("out/chart_layout.json"))["1920x1080"]

def patches(n):
    jp, small, sc = ex.load_jpeg(f"shots/{n}.JPG"); H = ex.homography(lay, small, sc)
    q, _ = ex.refine(sum(jp) / 3, ex.inner_quads(lay, H)); q, g = ex.grid_quads(sum(jp) / 3, q)
    return np.array([[s[0] for s in ex.sample(jp, qq)] for qq in q]).reshape(7, 36, 3)

def ycc(x):
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    return 0.299 * r + 0.587 * g + 0.114 * b, -0.168736 * r - 0.331264 * g + 0.5 * b, 0.5 * r - 0.418688 * g - 0.081312 * b

out = {}
np.set_printoptions(linewidth=250)
for mode, a, b in (("Vivid", "PB090238", "PB090244"), ("Muted", "PB090239", "PB090245"), ("Portrait", "PB090240", "PB090246")):
    A, B = patches(a), patches(b)
    ok = (A.min(2) > 6) & (A.max(2) < 249) & (B.min(2) > 6) & (B.max(2) < 249); ok[6] = False
    ya, cba, cra = ycc(A); yb, cbb, crb = ycc(B)
    ca, cb = np.hypot(cba, cra), np.hypot(cbb, crb)
    ha = np.degrees(np.arctan2(cra, cba)); dh = (np.degrees(np.arctan2(crb, cbb)) - ha + 180) % 360 - 180
    ok &= ca > 12
    ratio = np.array([np.median((cb / ca)[ok[:, c], c]) if ok[:, c].any() else np.nan for c in range(36)])
    shift = np.array([np.median(dh[ok[:, c], c]) if ok[:, c].any() else np.nan for c in range(36)])
    dy = np.array([np.median((yb - ya)[ok[:, c], c]) if ok[:, c].any() else np.nan for c in range(36)])
    gray = np.abs(B[6] - A[6]).max()
    out[mode] = (ratio, shift, dy)
    print(f"\n{mode}: gray row max change {gray:.1f} codes; usable patches {ok.sum()}")
    print(" chart hue (deg):", " ".join(f"{h:4d}" for h in range(0, 360, 10)))
    print(" chroma x       :", " ".join("  . " if np.isnan(x) else f"{x:4.2f}" for x in ratio))
    print(" hue shift (deg):", " ".join("  . " if np.isnan(x) else f"{x:+4.0f}" for x in shift))
    print(" luma change    :", " ".join("  . " if np.isnan(x) else f"{x:+4.0f}" for x in dy))
np.savez("out/probe6.npz", **{m + "_" + k: v for m, t in out.items() for k, v in zip(("ratio", "shift", "dy"), t)})

"""Step 16.1: does the look curve act per channel (model A) or on luminance after the RGB base gamma (model B)?

A: c_c = LOOK(BASE_c(K v_c)/4)/4 ; out = Y(c) + s (c - Y(c))
B: b_c = BASE_c(K v_c)/4 (8-bit scale) ; Y = w·b ; out = LOOK(Y) + s (b - Y)       (Y replaced, Cb/Cr scaled)
One saturation s per mode family. ΔE2000 model vs camera on colour patches (rows 0-5) away from the 8-bit limits.
Usage: ../../.venv/bin/python -I analyze_lumalook.py   -> out/lumalook_report.txt
"""
import importlib.util, os, struct, sys
import numpy as np
from scipy.optimize import minimize_scalar
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]]
def imp(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(HERE, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
fl = imp("fit_look"); tone = fl.tone
d, st, meta = tone.load(); roles = [str(r) for r in d["roles"]]; rows = np.array([m["row"] for m in meta])
X = np.arange(256); K = fl.K; T = fl.table
E = 0x7E74E9BC
W = {"BT.601": np.array([0.299, 0.587, 0.114]), "BT.709": np.array([0.2126, 0.7152, 0.0722])}
FAM = {
 "Natural family": [("B3", (E,)*3, fl.IDENTITY), ("N1-con-2", (E,)*3, 0x7E75CEF0), ("N2-con+2", (E,)*3, 0x7E75D4F0),
                    ("G1-highkey", (E,)*3, 0x7E75E0F0), ("G2-lowkey", (E,)*3, 0x7E75E2F0)],
 "Portrait family": [("M3-portrait", (E,)*3, 0x7E75DAF0), ("P1-con-2", (E,)*3, 0x7E75D6F0), ("P2-con+2", (E,)*3, 0x7E75DEF0)],
 "Light Tone": [("A3-lighttone", (0x7E74F5BC,)*3, 0x7E75EAF0)],
 "Cross Process I": [("A4-crossprocess", (0x7E74FDBC, 0x7E74FFBC, 0x7E7501BC), 0x7E75F2F0)],
}
def data(role):
    k = roles.index(role); v = tone.precurve(d, st, k); j = d["jpg"][k]
    ok = (~d["rawclip"][k]) & (~tone.BAD[k]) & (d["jpgspread"][k] < 20) & (rows < 6) & (j.min(1) > 4) & (j.max(1) < 250)
    return v[ok], j[ok]
def base(v, bs):
    return np.stack([np.interp(K * np.maximum(v[:, c], 0), X, T(bs[c])) for c in range(3)], 1) / 4.0
def A(v, bs, look, s, w):
    c = np.interp(base(v, bs), X, T(look)) / 4.0; y = c @ w
    return np.clip(y[:, None] + s * (c - y[:, None]), 0, 255)
def B(v, bs, look, s, w):
    b = base(v, bs); y = b @ w; y2 = np.interp(y, X, T(look)) / 4.0
    return np.clip(y2[:, None] + s * (b - y[:, None]), 0, 255)
def de(p, j): return fl.de2000(fl.srgb_to_lab(p), fl.srgb_to_lab(j))
lines = []
for wn, w in W.items():
    lines.append(f"\n=== luma weights {wn} ===")
    for fam, sets in FAM.items():
        D = [(r, bs, lk) + data(r) for r, bs, lk in sets]
        for mn, M in (("A per-channel", A), ("B luminance  ", B)):
            f = lambda s: np.mean(np.concatenate([de(M(v, bs, lk, s, w), j) for r, bs, lk, v, j in D]))
            s = minimize_scalar(f, bounds=(0.4, 2.5), method="bounded").x
            per = []
            for r, bs, lk, v, j in D:
                si = minimize_scalar(lambda q: np.mean(de(M(v, bs, lk, q, w), j)), bounds=(0.4, 2.5), method="bounded").x
                e = de(M(v, bs, lk, s, w), j)
                per.append(f"{r}: {e.mean():.2f} (own sat {si:.3f})")
            lines.append(f"{fam:16s} {mn} shared sat {s:.3f}  mean ΔE {f(s):.2f} | " + "; ".join(per))
open(os.path.join(HERE, "out", "lumalook_report.txt"), "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

"""Step 16.2b: forward model of the six-axis stage with axes fixed at the BT.601 hue angles of R, G, B, C, M, Y.

out = Y' + rot(u_h · W(h)·hue_rec) · (1 + u_s · W(h)·sat_rec) · S0 · gain/282 · (b - Y)      (model B around it)
W(h): linear interpolation between the two neighbouring axes of the pre-stage hue h = atan2(Cr, Cb).
Units u_s, u_h fitted on Vivid + Muted + Portrait; Pop Art I and Light Tone are not fitted (check only).
Usage: ../../.venv/bin/python -I analyze_sixaxis_model.py  -> out/sixaxis_model_report.txt
"""
import importlib.util, os, sys
import numpy as np
from scipy.optimize import minimize
HERE = os.path.dirname(os.path.abspath(__file__)); sys.argv = [sys.argv[0]]
def imp(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(HERE, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
sx = imp("analyze_sixaxis"); fl = sx.fl; tone = sx.tone
AX = np.array([108.7, 231.7, 351.3, 288.7, 51.7, 171.3])      # slot order R, G, B, C, M, Y
ORDER = np.argsort(AX)
def weights(h):
    a = AX[ORDER]; W = np.zeros((len(h), 6))
    for k in range(6):
        span = (a[(k+1) % 6] - a[k]) % 360; t = ((h - a[k]) % 360) / span; sel = ((h - a[k]) % 360) < span
        W[sel, ORDER[k]] += 1 - t[sel]; W[sel, ORDER[(k+1) % 6]] += t[sel]
    return W
def predict(name, us, uh, s0=sx.S0):
    role, bs, lk, gain, srec, hrec = sx.SET[name]
    k = sx.roles.index(role); v = tone.precurve(sx.d, sx.st, k); j = sx.d["jpg"][k]
    ok = (~sx.d["rawclip"][k]) & (~tone.BAD[k]) & (sx.d["jpgspread"][k] < 20) & (sx.rows < 6) & (j.min(1) > 4) & (j.max(1) < 250)
    v, j = v[ok], j[ok]
    b = np.stack([np.interp(sx.K*np.maximum(v[:, c], 0), sx.X, sx.T(bs[c])) for c in range(3)], 1)/4.0
    y = b @ sx.W; y2 = np.interp(y, sx.X, sx.T(lk))/4.0
    c = sx.cbcr(b) * s0 * gain/282.0
    h = np.degrees(np.arctan2(c[:, 1], c[:, 0])) % 360; Wt = weights(h)
    g = 1 + us * (Wt @ np.array(srec)); a = np.radians(uh * (Wt @ np.array(hrec)))
    cb = g*(c[:, 0]*np.cos(a) - c[:, 1]*np.sin(a)); cr = g*(c[:, 0]*np.sin(a) + c[:, 1]*np.cos(a))
    rgb = np.stack([y2 + 1.402*cr, y2 - 0.344136*cb - 0.714136*cr, y2 + 1.772*cb], 1)
    return np.clip(rgb, 0, 255), j
def de(n, us, uh): 
    p, j = predict(n, us, uh); return fl.de2000(fl.srgb_to_lab(p), fl.srgb_to_lab(j))
if __name__ == "__main__":
    fit = ["Vivid", "Muted", "Portrait"]
    r = minimize(lambda x: sum(de(n, x[0], x[1]).mean() for n in fit), [1/256, -0.5], method="Nelder-Mead", options={"xatol": 1e-5, "fatol": 1e-4})
    us, uh = r.x
    L = [f"axes fixed at R G B C M Y = {AX}; fitted units: saturation {us:.5f} per unit (1/{1/us:.0f}), hue {uh:+.3f} deg per unit (angle atan2(Cr, Cb))"]
    for n in ["Natural", "Vivid", "Muted", "Portrait", "Pop Art I", "Light Tone", "Natural Sat+2", "Natural Sat-2"]:
        a, b_, c, d_ = de(n, 0, 0), de(n, us, uh), de(n, us, 0), de(n, 1/256, uh)
        L.append(f"  {n:14s} ΔE2000 model vs camera: without stage {a.mean():.2f} (p95 {np.percentile(a,95):.2f}) | with {b_.mean():.2f} (p95 {np.percentile(b_,95):.2f}) | sat part only {c.mean():.2f} | with u_s = 1/256: {d_.mean():.2f}   n={len(a)}{'' if n in fit or 'Natural' in n else '  (not fitted)'}")
    open(os.path.join(HERE, "out", "sixaxis_model_report.txt"), "w").write("\n".join(L) + "\n"); print("\n".join(L))

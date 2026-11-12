"""Delta refit from the measured xp7 result (NOTES §23). For colours measured on the camera with
xp7 (SpyderCheckr PB110254, monitor chart PB090253): prediction = measured + model(new) - model(xp7),
so only the *change* relies on the model. Model order as the camera showed: art matrix on linear
sRGB (after the colour matrix), then six-axis, then curves, saturation.
   ../../.venv/bin/python -I fit_delta.py"""
import json, struct, sys, importlib.util, io, contextlib
import numpy as np
from scipy.optimize import least_squares
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    sp = importlib.util.spec_from_file_location("fj", "fit_joint.py"); fj = importlib.util.module_from_spec(sp); sp.loader.exec_module(fj)
f4, f3, f2, fs, fl = fj.f4, fj.f3, fj.f2, fj.fs, fj.fl; lab, de = fl.srgb_to_lab, fl.de2000; KN = fj.KN
m7 = np.load("out/fit_matrix.npz"); G7, sat7, S7, H7, A7 = m7["G"], float(m7["sat"]), m7["S"], m7["H"], m7["A"]
def A_of(o):
    o = o.reshape(3, 2); return np.array([[1 - o[0].sum(), o[0, 0], o[0, 1]], [o[1, 0], 1 - o[1].sum(), o[1, 1]], [o[2, 0], o[2, 1], 1 - o[2].sum()]])
def off(A): return np.array([A[0, 1], A[0, 2], A[1, 0], A[1, 2], A[2, 0], A[2, 1]])
def quant(A):
    Q = np.round(A * 256).astype(int)
    for i in range(3): Q[i, i] += 256 - Q[i].sum()
    return Q
def unpack(p): return fj.curves(p), p[3 * KN], p[3 * KN + 1:3 * KN + 7], p[3 * KN + 7:3 * KN + 13], A_of(p[3 * KN + 13:3 * KN + 19])
R = lambda v, G, sat, S, H, A: fj.render(v, G, sat, S, H, A)
# measured sets
sv = fj.sv; Js = np.load("out/spyder_xp7_measured.npy"); stl = fj.stl; base_s = R(sv, G7, sat7, S7, H7, A7)
Bc = f2.patches("PB090253")[:6].reshape(-1, 3); okc = f3.rawok & (Bc.min(1) > 8) & (Bc.max(1) < 247); cv = f3.V[okc]; Jc = Bc[okc]
ctl = fs.tgt(cv / fl.V_GRAY * 0.18); base_c = R(cv, G7, sat7, S7, H7, A7)
p7 = np.concatenate([fj.knots_of(G7), [sat7], S7, H7, off(A7)])
def res(p):
    G, sat, S, H, A = unpack(p)
    ps = np.clip(Js + R(sv, G, sat, S, H, A) - base_s, 0, 255); pc = np.clip(Jc + R(cv, G, sat, S, H, A) - base_c, 0, 255)
    return np.concatenate([np.sqrt(60.0) * de(lab(ps), stl), np.sqrt(3.0) * de(lab(pc), ctl), np.sqrt(fj.w) * de(lab(R(fj.vs, G, sat, S, H, A)), fj.tl),
                           0.05 * np.diff(G[:, ::32], 2, axis=1).ravel(), 0.3 * (p[3 * KN + 1:3 * KN + 13] - p7[3 * KN + 1:3 * KN + 13]), 60 * (p[3 * KN + 13:] - p7[3 * KN + 13:])])
lo = np.concatenate([np.zeros(3 * KN), [0.6], [-40] * 6, [-20] * 6, [-0.5] * 6]); hi = np.concatenate([np.full(3 * KN, 40.0), [1.4], [40] * 6, [20] * 6, [0.5] * 6])
r = least_squares(res, np.clip(p7, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), x_scale="jac", max_nfev=200)
G, sat, S, H, A = unpack(r.x); S, H = np.round(S), np.round(H); Q = quant(A); Aq = Q / 256.0; gain = int(round(282 * sat / 1.078))
ps = np.clip(Js + R(sv, G, sat, S, H, Aq) - base_s, 0, 255); pc = np.clip(Jc + R(cv, G, sat, S, H, Aq) - base_c, 0, 255)
d7, d8 = de(lab(Js), stl), de(lab(ps), stl); c7, c8 = de(lab(Jc), ctl), de(lab(pc), ctl)
dsyn7 = de(lab(R(fj.hv, G7, sat7, S7, H7, A7)), fj.hl); dsyn8 = de(lab(R(fj.hv, G, sat, S, H, Aq)), fj.hl)
names = "D1 D2 D3 D4 D5 D6 C1 C2 C3 C4 C5 C6 B1 B2 B3 B4 B5 B6 A1 A2 A3 A4 A5 A6".split()
lines = ["ΔE2000 vs the Portra target:",
         f"  xp7 measured : Spyder all {d7.mean():.2f} colours {d7[:18].mean():.2f} grays {d7[18:].mean():.2f} worst {d7.max():.2f} | monitor chart {c7.mean():.2f} (n={len(c7)})",
         f"  xp8 predicted: Spyder all {d8.mean():.2f} colours {d8[:18].mean():.2f} grays {d8[18:].mean():.2f} worst {d8.max():.2f} | monitor chart {c8.mean():.2f}   (delta prediction from the xp7 measurement)",
         f"  model-only hold-out (not delta): xp7 {dsyn7.mean():.2f} -> xp8 {dsyn8.mean():.2f}",
         f"  changes: saturation {sat7:.3f} -> {sat:.3f} (gain {gain}); S {S7.astype(int).tolist()} -> {S.astype(int).tolist()}; H {H7.astype(int).tolist()} -> {H.astype(int).tolist()}",
         f"           matrix x256 {quant(A7).tolist()} -> {Q.tolist()}",
         "  Spyder per patch xp7 -> xp8: " + ", ".join(f"{n} {a:.1f}->{b:.1f}" for n, a, b in zip(names, d7, d8))]
b0 = open(fl.tone.BLOCK0, "rb").read(); B = fl.tone.BASE
op = lambda addr, new: {"type": "bytes", "block": 0, "offset": hex(addr - B), "expect": b0[addr - B:addr - B + len(new)].hex(), "new": new.hex()}
ops = fl.xp_ops(G, gain) + [op(0x7E7694FE, struct.pack("<6h", *S.astype(int))), op(0x7E76950A, struct.pack("<6h", *H.astype(int))), op(0x7E768F46, struct.pack("<9h", *Q.ravel())), op(0x7E56C6A6, b"\x55"), op(0x7E56C6AA, b"\x57")]
json.dump({"name": "film-portra-xp8", "description": "As film-portra-xp7, refitted from the measured xp7 camera result by delta prediction (fit_delta.py, NOTES §23).", "status": "built, NOT camera-tested",
           "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "base_sha256": "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", "ops": ops}, open("../../patches/film-portra-xp8.json", "w"), indent=1)
np.savez("out/fit_xp8.npz", G=G, sat=sat, S=S, H=H, A=Aq, spyder_pred=ps)
open("out/delta_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

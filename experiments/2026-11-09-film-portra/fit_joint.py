"""Joint refit for the Cross Process I slot with the corrected model (NOTES §22): three curves on
the base-gamma output + saturation + the 12 six-axis values (pre-gamma, rank-order model), and
optionally a 3x3 pre-gamma matrix (the Pop Art slot of 0x7E56C603, assumed to act on the linear
RGB after the colour matrix: the order is unverified).   ../../.venv/bin/python -I fit_joint.py"""
import json, struct, sys, importlib.util, io, contextlib
import numpy as np
from scipy.optimize import least_squares
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    sp = importlib.util.spec_from_file_location("f4", "fit_sixaxis4.py"); f4 = importlib.util.module_from_spec(sp); sp.loader.exec_module(f4)
f3, f2, fs, fl = f4.f3, f4.f2, f4.fs, f4.fl; lab, de = fl.srgb_to_lab, fl.de2000
Xv, CP0, N1 = f4.Xv, f4.CP0, np.arange(1024); ident = fl.table(fl.IDENTITY)
KN = 16; kx = np.linspace(0, 1023, KN)
def curves(p): return np.array([np.interp(N1, kx, np.minimum(np.cumsum(p[i * KN:(i + 1) * KN] ** 2), 1023.0)) for i in range(3)])
def render(v, G, sat, S, H, M=None):
    if M is not None: v = v @ M.T
    W = f3.comps(v); dS, dH = S - CP0, H - CP0
    delta = sum(W[:, k:k + 1] * (dS[k] * Xv[k, 0] + dH[k] * Xv[k, 1]) for k in range(6))
    return np.clip(f3.down(v + delta, (G, ident, sat)), 0, 255)
lin, w, kind = fl.samples(); vs = lin / 0.18 * fl.V_GRAY; tl = fs.tgt(lin); hv = fs.hold / 0.18 * fl.V_GRAY; hl = fs.hl
x3 = np.load("out/spyder_xp3.npz"); sv, T = x3["v"], x3["target"]; stl = lab(T)
GP = f3.GP
def knots_of(G):   # initial knot parameters reproducing G approximately
    y = np.array([np.interp(kx, N1, G[i]) for i in range(3)]); d = np.diff(np.concatenate([np.zeros((3, 1)), y], 1), axis=1)
    return np.sqrt(np.maximum(d, 1e-3)).ravel()
def unpack(p, with_m):
    G = curves(p); sat = p[3 * KN]; S, H = p[3 * KN + 1:3 * KN + 7], p[3 * KN + 7:3 * KN + 13]
    M = None
    if with_m:
        o = p[3 * KN + 13:3 * KN + 19].reshape(3, 2); M = np.array([[1 - o[0].sum(), o[0, 0], o[0, 1]], [o[1, 0], 1 - o[1].sum(), o[1, 1]], [o[2, 0], o[2, 1], 1 - o[2].sum()]])
    return G, sat, S, H, M
def run(with_m, six=True):
    def res(p):
        G, sat, S, H, M = unpack(p, with_m)
        if not six: S, H = CP0, CP0
        r = [np.sqrt(w) * de(lab(render(vs, G, sat, S, H, M)), tl), np.sqrt(20.0) * de(lab(render(sv, G, sat, S, H, M)), stl),
             0.05 * np.diff(G[:, ::32], 2, axis=1).ravel(), 0.1 * p[3 * KN + 1:3 * KN + 13]]
        if with_m: r.append(20 * p[3 * KN + 13:])
        return np.concatenate(r)
    p0 = np.concatenate([knots_of(GP), [0.937], f4.S5.astype(float), f4.H5.astype(float)] + ([np.zeros(6)] if with_m else []))
    lo = np.concatenate([np.full(3 * KN, 0.0), [0.6], [-40] * 6, [-20] * 6] + ([[-0.5] * 6] if with_m else []))
    hi = np.concatenate([np.full(3 * KN, 40.0), [1.4], [40] * 6, [20] * 6] + ([[0.5] * 6] if with_m else []))
    r = least_squares(res, np.clip(p0, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), x_scale="jac", max_nfev=200)
    G, sat, S, H, M = unpack(r.x, with_m)
    if not six: S, H = CP0.copy(), CP0.copy()
    return G, sat, np.round(S), np.round(H), M
def rep(name, G, sat, S, H, M=None):
    d = de(lab(render(vs, G, sat, S, H, M)), tl); dh = de(lab(render(hv, G, sat, S, H, M)), hl); ds = de(lab(render(sv, G, sat, S, H, M)), stl)
    return (f"  {name:34s} gray {d[kind == 0].mean():5.2f} | ColorChecker {d[kind == 1].mean():5.2f} | hold-out {dh.mean():5.2f} (p95 {np.percentile(dh, 95):5.2f}) | "
            f"Spyder all {ds.mean():5.2f} colours {ds[:18].mean():5.2f} grays {ds[18:].mean():5.2f} worst {ds.max():5.2f}")
lines = ["Predicted ΔE2000 vs the Portra target (corrected model):", rep("xp3 (installed)", GP, 0.937, f2.XP3[0].astype(float), f2.XP3[1].astype(float)),
         rep("xp5 (six-axis refit only)", GP, 0.937, f4.S5.astype(float), f4.H5.astype(float))]
J = run(False); lines += [rep("joint: curves + sat + six-axis", *J), f"      sat {J[1]:.3f}  S {J[2].astype(int).tolist()}  H {J[3].astype(int).tolist()}"]
Mx = run(True); lines += [rep("joint + 3x3 matrix", *Mx), f"      sat {Mx[1]:.3f}  S {Mx[2].astype(int).tolist()}  H {Mx[3].astype(int).tolist()}  matrix x256 {np.round(Mx[4] * 256).astype(int).tolist()}"]
Mo = run(True, six=False); lines += [rep("curves + sat + matrix, no six-axis", *Mo), f"      matrix x256 {np.round(Mo[4] * 256).astype(int).tolist()}"]
np.savez("out/fit_joint.npz", G=J[0], sat=J[1], S=J[2], H=J[3], Gm=Mx[0], satm=Mx[1], Sm=Mx[2], Hm=Mx[3], M=Mx[4])
open("out/joint_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

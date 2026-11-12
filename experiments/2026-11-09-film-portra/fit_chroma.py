"""Refit a film with the chroma curves free (NOTES §43): everything fit_film.py fits, plus one curve on Cb and one on Cr.

Objective: the measured samples of the film's last build (second-generation test image, GRKit weights; as
fit_film.py --anchor ... --robust 3), predicted as  curve(measured + model change before the curve).
   ../../.venv/bin/python -I fit_chroma.py --anchor F2_velvia out/fit_film-velvia100-2.npz --name film-velvia100-3
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import least_squares
argv = sys.argv; sys.argv = ["x"]
import fit_xp9 as f
from mocklib import *
import chroma as C
ap = argparse.ArgumentParser(); ap.add_argument("--anchor", nargs=2, required=True); ap.add_argument("--name", required=True); ap.add_argument("--robust", type=float, default=3.0)
ap.add_argument("--no-chroma", action="store_true", help="control: same refit with the curves held linear")
a = ap.parse_args(argv[1:])
Am = load(a.anchor[0]); za = np.load(a.anchor[1]); lut = str(za["lut"]); cube, size = fl.load_cube(lut)
tgt = lambda v: lab(np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(v, 0) / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255)
assert "weight" in Am, "needs a reading of the second-generation test image"
J, k = Am["jpg"], Am["kind"]; KN = f.KN
wa = np.where(Am["weight"] > 0, Am["weight"], np.where(k == 8, 20.0, np.where(k == 3, 4.0, np.where(k == 2, 20.0, 0.0))))
sel = Am["ok"] & (wa > 0); u, Js, ks, ws = Am["u"][sel], J[sel], k[sel], wa[sel]; tl = tgt(Am["vs"][sel]); unc = (Js.min(1) > 2) & (Js.max(1) < 253)
base = f.R(u, za["G"], float(za["sat"]), za["S"], za["H"], za["P"])                 # the anchor build's model output BEFORE its chroma curves
Q0 = np.tile(C.Q_LINEAR, 2); uncurve = lambda X: X
if "Cb" in za.files:                         # the anchor build had curves: take the measured values back through them (they are monotonic), then work as before
    _c = np.linspace(0, 255, 2041); _cb = C.ev_bytes(_c, za["Cb"][0], za["Cb"][1], za["Cb_slope17"]); _cr = C.ev_bytes(_c, za["Cr"][0], za["Cr"][1], za["Cr_slope17"])
    def uncurve(X):
        y, cb, cr = C.ycc(X); return C.rgb(y, np.interp(cb, _cb, _c), np.interp(cr, _cr, _c))
    Q0 = np.concatenate([C.q_of(za["Cb"][1][:11].astype(float)), C.q_of(za["Cr"][1][:11].astype(float))])
Jpre = uncurve(Js)
def pre(G, sat, S, H, P):
    m = f.R(u, G, sat, S, H, P); return np.where(unc[:, None], Jpre + m - base, m)
def unpack(p):
    H = p[3 * KN + 7:3 * KN + 13].copy(); H[0] = 0.0
    return f.curves(p), p[3 * KN], p[3 * KN + 1:3 * KN + 7], H, f.P_of(p[3 * KN + 13:3 * KN + 19])
n1 = 3 * KN + 19
def res(p, fixed=None, cfix=None):
    if fixed is not None: p = np.concatenate([p[:3 * KN + 1], fixed, p[3 * KN + 1:]])
    G, sat, S, H, P = unpack(p); q = p[n1:] if cfix is None else None
    cb, cr = (C.ys_of(q[:8]), C.ys_of(q[8:])) if cfix is None else cfix
    out = np.clip(C.apply(pre(G, sat, S, H, P), cb, cr, stored=cfix is not None), 0, 255)
    r = [np.sqrt(ws) * de(lab(out), tl), 0.05 * np.diff(G[:, ::32], 2, axis=1).ravel(), 0.1 * p[3 * KN + 1:3 * KN + 13]]
    if cfix is None: r.append(0.3 * np.concatenate([np.diff(np.diff(cb) / np.diff(C.XK)), np.diff(np.diff(cr) / np.diff(C.XK))]))     # smooth slopes
    return np.concatenate(r)
lo = np.concatenate([np.zeros(3 * KN), [0.6], [-40] * 6, [-20] * 6, [-64] * 6]); hi = np.concatenate([np.full(3 * KN, 40.0), [1.4], [40] * 6, [20] * 6, [64] * 6])
sq = np.sqrt(np.concatenate([np.diff(C.XK[:5]), np.diff(C.XK[6:])]))                      # segment widths: slope limits 0.35 .. 1.6
clo, chi = np.tile(sq * np.sqrt(0.35), 2), np.tile(sq * np.sqrt(1.6), 2)
if a.no_chroma: clo = np.tile(C.Q_LINEAR, 2) - 1e-4; chi = np.tile(C.Q_LINEAR, 2) + 1e-4
p0 = np.concatenate([f.knots_of(za["G"]), [float(za["sat"])], za["S"], za["H"], f.off(za["P"] * 128), Q0])
LO, HI = np.concatenate([lo, clo]), np.concatenate([hi, chi])
r = least_squares(res, np.clip(p0, LO + 1e-6, HI - 1e-6), bounds=(LO, HI), x_scale="jac", max_nfev=300, loss="soft_l1", f_scale=a.robust)
G, sat, S, H, P = unpack(r.x); S, H = np.round(S), np.round(H); A = f.find_A(P); Pq = f.renormalise(A) / 128.0
cbb, crb = C.quantise(C.ys_of(r.x[n1:n1 + 8])), C.quantise(C.ys_of(r.x[n1 + 8:]))
fixed = np.concatenate([S, H, f.off(Pq * 128)]); n0 = 3 * KN + 1
r2 = least_squares(lambda q: res(q, fixed, (cbb, crb)), r.x[:n0], bounds=(lo[:n0], hi[:n0]), x_scale="jac", max_nfev=100, loss="soft_l1", f_scale=a.robust)
G = f.curves(r2.x); gain = int(round(r2.x[3 * KN] / f.SAT_PER_GAIN)); sat = gain * f.SAT_PER_GAIN
final = np.clip(C.apply(pre(G, sat, S, H, Pq), cbb, crb, stored=True), 0, 255)
def line(tag, pm):
    dd = de(lab(pm), tl); g = lambda kk: dd[ks == kk].mean()
    return (f"  {tag}: GRKit-weighted {np.average(dd, weights=ws):.3f} | grays {g(6):.2f} ColorChecker {g(7):.2f} (p95 {np.percentile(dd[ks == 7], 95):.2f}) skin {g(8):.2f} "
            f"natural {g(5):.2f} (p95 {np.percentile(dd[ks == 5], 95):.2f}) near-neutral {g(3):.2f} dense grays {g(2):.2f}")
ho = Am["ok"] & (k == 9) & (J.min(1) > 2) & (J.max(1) < 253); ht = tgt(Am["vs"][ho])
hp = np.clip(C.apply(uncurve(J[ho]) + f.R(Am["u"][ho], G, sat, S, H, Pq) - f.R(Am["u"][ho], za["G"], float(za["sat"]), za["S"], za["H"], za["P"]), cbb, crb, stored=True), 0, 255)
ge = Am["ok"] & (k == 10)
lines = [f"Target {os.path.basename(lut)}; anchor {a.anchor[0]} ({a.anchor[1]})", line("anchor build, MEASURED", Js), line("this fit, predicted      ", final),
         f"  hold-out naturals (not in the fit): measured {de(lab(J[ho]), ht).mean():.2f} -> predicted {de(lab(hp), ht).mean():.2f}",
         f"  gain {gain}; S {S.astype(int).tolist()}; H {H.astype(int).tolist()}; art table x256 {A.tolist()}; camera matrix (EXIF, 5300 K) {(f.renormalise(A) * 2).tolist()}",
         f"  Cb curve y at x {C.XK.astype(int).tolist()}: {cbb[1][:11].tolist()}  slopes/128 {cbb[2][1:11].tolist()}",
         f"  Cr curve y: {crb[1][:11].tolist()}  slopes/128 {crb[2][1:11].tolist()}"]
np.savez(f"out/fit_{a.name}.npz", G=G, sat=sat, gain=gain, S=S, H=H, A=A, P=Pq, lut=lut, Cb=np.array(cbb[:2] + (cbb[2][:16],)), Cr=np.array(crb[:2] + (crb[2][:16],)), Cb_slope17=cbb[2], Cr_slope17=crb[2])
open(f"out/{a.name}_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

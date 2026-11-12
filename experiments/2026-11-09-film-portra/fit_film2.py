"""Fit a film with the second camera model (model2.py; NOTES §45): matrix, three curves, six-axis values, saturation
gain and the two chroma curves together.

With --anchor (a reading of the second-generation test image developed with an earlier build of the film, and that
build's fit) the objective is the measured samples, predicted as  curve(un-curve(measured) + model change); clipped
samples use the model alone. Without it: the same samples predicted by the model alone (first fit of a new film).
Weights: GRKit's (grays 150, ColorChecker 20 / skin patches 60, natural colours 1), skin series 20, near-neutrals 4,
dense grays 20, and --edge-weight for the gamut-edge colours (0 = GRKit's choice: not scored).
   ../../.venv/bin/python -I fit_film2.py --lut out/lut/.../x.cube --name film-x-m1 [--anchor F3_x out/fit_film-x-c1.npz]
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import least_squares
argv = sys.argv; sys.argv = ["x"]
import fit_xp9 as f
from mocklib import *
import chroma as C, model2 as M2
ap = argparse.ArgumentParser(); ap.add_argument("--lut"); ap.add_argument("--name", required=True); ap.add_argument("--anchor", nargs=2); ap.add_argument("--robust", type=float, default=3.0)
ap.add_argument("--edge-weight", type=float, default=0.0); ap.add_argument("--image", default="A_natural", help="reading that supplies the sample set when there is no anchor")
a = ap.parse_args(argv[1:])
Am = load(a.anchor[0] if a.anchor else a.image); za = np.load(a.anchor[1]) if a.anchor else None
lut = a.lut or str(za["lut"]); cube, size = fl.load_cube(lut)
tgt = lambda v: lab(np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(v, 0) / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255)
J, k = Am["jpg"], Am["kind"]; KN = f.KN
wa = np.where(Am["weight"] > 0, Am["weight"], np.where(k == 8, 20.0, np.where(k == 3, 4.0, np.where(k == 2, 20.0, np.where(k == 10, a.edge_weight, 0.0)))))
sel = (Am["ok"] if a.anchor else np.isfinite(Am["u"][:, 0])) & (wa > 0); u, ks, ws = Am["u"][sel], k[sel], wa[sel]; tl = tgt(Am["vs"][sel])
if a.anchor:
    Js = J[sel]; unc = (Js.min(1) > 2) & (Js.max(1) < 253); ch_a = M2.chroma_of(za)
    base = M2.render(u, za["G"], M2.gain_of(za), za["S"], za["H"], za["P"], None, clip=False)      # the anchor build, before its chroma curves
    uncurve = lambda X: X
    if ch_a is not None:
        _c = np.linspace(0, 255, 2041); _cb, _cr = C.ev_bytes(_c, *ch_a[0]), C.ev_bytes(_c, *ch_a[1])
        def uncurve(X):
            y, cb, cr = C.ycc(X); return C.rgb(y, np.interp(cb, _cb, _c), np.interp(cr, _cr, _c))
    Jpre = uncurve(Js)
def pre(G, sat, S, H, P):
    m = M2.render(u, G, sat / M2.SAT_PER_GAIN, S, H, P, None, clip=False)
    return np.where(unc[:, None], Jpre + m - base, m) if a.anchor else m
def unpack(p):
    H = p[3 * KN + 7:3 * KN + 13].copy(); H[0] = 0.0
    return f.curves(p), p[3 * KN], p[3 * KN + 1:3 * KN + 7], H, f.P_of(p[3 * KN + 13:3 * KN + 19])
n1 = 3 * KN + 19
def res(p, fixed=None, cfix=None):
    if fixed is not None: p = np.concatenate([p[:3 * KN + 1], fixed, p[3 * KN + 1:]])
    G, sat, S, H, P = unpack(p)
    if cfix is None:
        q = p[n1:]; cb, cr = C.ys_of(q[:8]), C.ys_of(q[8:]); out = C.apply(pre(G, sat, S, H, P), cb, cr)
    else: out = C.apply(pre(G, sat, S, H, P), cfix[0], cfix[1], stored=True)
    r = [np.sqrt(ws) * de(lab(np.clip(out, 0, 255)), tl), 0.05 * np.diff(G[:, ::32], 2, axis=1).ravel(), 0.1 * p[3 * KN + 1:3 * KN + 13]]
    if cfix is None: r.append(0.3 * np.concatenate([np.diff(np.diff(cb) / np.diff(C.XK)), np.diff(np.diff(cr) / np.diff(C.XK))]))
    return np.concatenate(r)
lo = np.concatenate([np.zeros(3 * KN), [0.6], [-40] * 6, [-20] * 6, [-64] * 6]); hi = np.concatenate([np.full(3 * KN, 40.0), [1.5], [40] * 6, [20] * 6, [64] * 6])
sq = np.sqrt(np.concatenate([np.diff(C.XK[:5]), np.diff(C.XK[6:])])); clo, chi = np.tile(sq * np.sqrt(0.35), 2), np.tile(sq * np.sqrt(1.6), 2)
LO, HI = np.concatenate([lo, clo]), np.concatenate([hi, chi])
def start(z):
    q = np.concatenate([C.q_of(z["Cb"][1][:11].astype(float)), C.q_of(z["Cr"][1][:11].astype(float))]) if "Cb" in z.files else np.tile(C.Q_LINEAR, 2)
    return np.concatenate([f.knots_of(z["G"]), [M2.gain_of(z) * M2.SAT_PER_GAIN], z["S"], z["H"], f.off(z["P"] * 128), q])
starts = {"the anchor fit": start(za)} if a.anchor else {"neutral": np.concatenate([f.knots_of(IDG), [1.0], np.zeros(12), f.off(np.round(M5300 * 128)), np.tile(C.Q_LINEAR, 2)]),
                                                         "Portra": start(np.load("out/fit_film-portra-c1.npz"))}
best = None
for nm, p0 in starts.items():
    r = least_squares(res, np.clip(p0, LO + 1e-6, HI - 1e-6), bounds=(LO, HI), x_scale="jac", max_nfev=300, loss="soft_l1", f_scale=a.robust)
    print(f"  start from {nm}: cost {r.cost:.1f}")
    if best is None or r.cost < best.cost: best = r
r = best; G, sat, S, H, P = unpack(r.x); S, H = np.round(S), np.round(H); A = f.find_A(P); Pq = f.renormalise(A) / 128.0
cbb, crb = C.quantise(C.ys_of(r.x[n1:n1 + 8])), C.quantise(C.ys_of(r.x[n1 + 8:]))
fixed = np.concatenate([S, H, f.off(Pq * 128)]); n0 = 3 * KN + 1
r2 = least_squares(lambda q: res(q, fixed, (cbb, crb)), r.x[:n0], bounds=(lo[:n0], hi[:n0]), x_scale="jac", max_nfev=100, loss="soft_l1", f_scale=a.robust)
G = f.curves(r2.x); gain = int(round(r2.x[3 * KN] / M2.SAT_PER_GAIN)); sat = gain * M2.SAT_PER_GAIN
final = np.clip(C.apply(pre(G, sat, S, H, Pq), cbb, crb, stored=True), 0, 255)
allok = Am["ok"] if a.anchor else np.isfinite(Am["u"][:, 0]); Tall = tgt(Am["vs"])
def full(G, gain, S, H, P, ch):                   # every patch of the image, model alone or anchored
    mo = M2.render(Am["u"], G, gain, S, H, P, None, clip=False)
    if a.anchor:
        ua = (J.min(1) > 2) & (J.max(1) < 253) & Am["ok"]; mo = np.where(ua[:, None], uncurve(np.nan_to_num(J)) + mo - M2.render(Am["u"], za["G"], M2.gain_of(za), za["S"], za["H"], za["P"], None, clip=False), mo)
    return np.clip(C.apply(mo, ch[0], ch[1], stored=True), 0, 255)
def line(tag, X):
    dd = de(lab(X), Tall); g = lambda kk: dd[allok & (k == kk)].mean(); wsel = allok & (wa > 0)
    return (f"  {tag}: weighted {np.average(dd[wsel], weights=wa[wsel]):.3f} | grays {g(6):.2f} ColorChecker {g(7):.2f} skin {g(8):.2f} natural {g(5):.2f} hold-out {g(9):.2f} near-neutral {g(3):.2f} dense grays {g(2):.2f} gamut edge {g(10):.2f}")
lines = [f"Target {os.path.basename(lut)}; " + (f"anchor {a.anchor[0]} ({a.anchor[1]})" if a.anchor else "model only") + f"; edge weight {a.edge_weight}"]
if a.anchor: lines.append(line("anchor build, MEASURED", np.nan_to_num(J)))
lines += [line("this fit, predicted      ", full(G, gain, S, H, Pq, (cbb, crb))),
          f"  gain {gain}; S {S.astype(int).tolist()}; H {H.astype(int).tolist()}; art table x256 {A.tolist()}; camera matrix (EXIF, 5300 K) {(f.renormalise(A) * 2).tolist()}",
          f"  Cb curve y at x {C.XK.astype(int).tolist()}: {cbb[1][:11].tolist()}", f"  Cr curve y: {crb[1][:11].tolist()}"]
np.savez(f"out/fit_{a.name}.npz", G=G, sat=sat, gain=gain, S=S, H=H, A=A, P=Pq, lut=lut, Cb=np.array(cbb[:2] + (cbb[2][:16],)), Cr=np.array(crb[:2] + (crb[2][:16],)), Cb_slope17=cbb[2], Cr_slope17=crb[2], model="model2")
open(f"out/{a.name}_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

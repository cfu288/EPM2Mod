"""Recalibrate the model's fitted constants on renderings of test image A alone (NOTES §45-46): the 12 six-axis
direction vectors, the exposure scale K, the saturation per gain unit and one saturation value per stock picture mode.
Fitted on the film builds up to seven-films-3 and on Natural / Vivid / Muted / Portrait; tested on seven-films-5.
   ../../.venv/bin/python -I calib_model.py [--save]"""
import os, sys
argv = sys.argv; sys.argv = ["x"]; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import least_squares
import model2 as M2, eval_model as E
from mocklib import *
FILMS5 = [("F5_portra", "film-portra-m1"), ("F5_ektachrome", "film-ektachrome-m1"), ("F5_pro400h", "film-pro400h-m1"), ("F5_kodachrome", "film-kodachrome64-m1"), ("F5_vis250d", "film-vision3250d-m1"),
          ("F5_velvia", "film-velvia100-m1"), ("F5_superia", "film-superia400-m1")]
TRAIN, TEST = E.SETS, FILMS5
# stock picture modes: reading, look table, six-axis S, H (the "+3 green" member of each record pair; NOTES 25)
MODES = {"Natural": ("M_natural", fl.IDENTITY, (0, 3, 0, 0, 0, 0), (0, 3, 0, 0, 0, 0)), "Vivid": ("M_vivid", fl.IDENTITY, (18, 7, 24, 0, 8, 8), (0, 5, 4, -1, -6, 0)),
         "Muted": ("M_muted", 0x7E75D0F0, (-22, 7, -16, 0, 4, -8), (3, 3, -3, 9, 8, 10)), "Portrait": ("M_portrait", 0x7E75DAF0, (14, 3, 0, 5, 0, 0), (-1, 3, 2, -2, 0, 0))}
def rows(sets, modes=True):
    out = []
    for rd, ft in sets:
        d = load(rd); z = np.load(f"out/fit_{ft}.npz"); out.append(dict(name=rd, d=d, G=z["G"], gain=M2.gain_of(z), S=z["S"], H=z["H"], P=z["P"], ch=M2.chroma_of(z), look=None, mode=None))
    if modes:
        for i, (nm, (rd, look, S, H)) in enumerate(MODES.items()):
            d = load(rd); out.append(dict(name=nm, d=d, G=IDG, gain=None, S=np.array(S, float), H=np.array(H, float), P=M5300, ch=None, look=fl.table(look), mode=i))
    for r in out:
        J, k, ok = r["d"]["jpg"], r["d"]["kind"], r["d"]["ok"]; r["sel"] = ok & (J.min(1) > 3) & (J.max(1) < 252) & np.isin(k, (2, 3, 5, 6, 7, 8, 9, 10))
    return out
Xv0, K0, SPG0 = M2.XV.copy(), M2.K, M2.SAT_PER_GAIN
NP = 38 + len(MODES)                     # 36 direction numbers, K scale, saturation-per-gain scale, one saturation per picture mode
def setp(p, clamp=None):
    M2.XV = p[:36].reshape(6, 2, 3); M2.K = K0 * p[36]; M2.SAT_PER_GAIN = SPG0 * p[37]
    if clamp is not None: M2.CLAMP = clamp
def model(r, p, sel=None):
    gain = r["gain"] if r["mode"] is None else p[38 + r["mode"]] / M2.SAT_PER_GAIN
    u = r["d"]["u"] if sel is None else r["d"]["u"][sel]
    return M2.render(u, r["G"], gain, r["S"], r["H"], r["P"], r["ch"], look=r["look"])
def res(p, D):
    setp(p); out = [(model(r, p, r["sel"]) - r["d"]["jpg"][r["sel"]]).ravel() for r in D]
    out.append(30.0 * (p[:36] - Xv0.ravel()) / np.abs(Xv0).max())           # ridge: a direction the data does not exercise stays near its old value
    return np.concatenate(out)
def score(p, D, clamp=None):
    setp(p, clamp); o = {}
    for r in D:
        J, k, ok = r["d"]["jpg"], r["d"]["kind"], r["d"]["ok"]; dE = de(lab(J), lab(model(r, p))); o[r["name"]] = [dE[ok & (k == g)].mean() for g, _ in E.GROUPS]
    return o
def show(title, sc):
    print(f"{title:36s}" + "".join(f"{v:13.2f}" for v in np.mean(list(sc.values()), 0)))
if __name__ == "__main__":
    Dtr, Dte = rows(TRAIN), rows(TEST, modes=False); Dm = [r for r in Dtr if r["mode"] is not None]; Df = [r for r in Dtr if r["mode"] is None]
    p0 = np.concatenate([Xv0.ravel(), [1.0, 1.0], np.full(len(MODES), 1.05)])
    pm = least_squares(lambda q: res(np.concatenate([p0[:38], q]), Dm), p0[38:], loss="soft_l1", f_scale=2.0).x      # per-mode saturation with the current constants, for a fair "before"
    pb = np.concatenate([p0[:38], pm])
    r = least_squares(res, pb, args=(Dtr,), loss="soft_l1", f_scale=2.0, x_scale="jac", max_nfev=80); best = (1e9, None)
    for c in (118, 120, 122, 124, 126, 128):                 # the chroma limit only shows on clipped patches, which the code residual leaves out: choose it by dE on all patches
        s = np.mean([v[-1] for v in score(r.x, Df, c).values()])
        if s < best[0]: best = (s, c)
    c0 = float(np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "calib", "model2.npz"))["clamp"])
    print("chroma limit", best[1], "| K x", r.x[36].round(4), "| saturation per gain x", r.x[37].round(4), "| mode saturations", dict(zip(MODES, r.x[38:].round(3))),
          "| six-axis: largest change", (np.abs(r.x[:36] - Xv0.ravel()).max() / np.abs(Xv0).max()).round(2), "of the largest component")
    print(f"{'camera vs model':36s}" + "".join(f"{n:>13s}" for _, n in E.GROUPS))
    for tag, p, c in (("before", pb, c0), ("after", r.x, best[1])):
        show(f"{tag}: films fitted on (21)", score(p, Df, c)); sm = score(p, Dm, c)
        for nm, v in sm.items(): print(f"{tag + ': ' + nm:36s}" + "".join(f"{x:13.2f}" for x in v))
        show(f"{tag}: seven-films-5 (not fitted)", score(p, Dte, c))
    if "--save" in argv:
        setp(r.x, best[1]); np.savez("calib/model2.npz", Xv=M2.XV, K=M2.K, sat_per_gain=M2.SAT_PER_GAIN, clamp=float(best[1]), mode_sat=r.x[38:], modes=list(MODES)); print("saved calib/model2.npz")

"""Recalibrate the model's fitted constants on the renderings of test image A alone (NOTES §45): the 12 six-axis
direction vectors, the exposure scale K and the saturation per gain unit. Fit on the builds before seven-films-3,
test on the seven renderings of seven-films-3.   ../../.venv/bin/python -I calib_model.py"""
import os, sys
sys.argv = ["x"]; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import least_squares
import fit_xp9 as f, model2 as M2, mocklib, eval_model as E
from mocklib import *
TRAIN, TEST = E.SETS[:14], E.SETS[14:]
def data(sets):
    out = []
    for rd, ft in sets:
        d = load(rd); z = np.load(f"out/fit_{ft}.npz"); J, k, ok = d["jpg"], d["kind"], d["ok"]
        s = ok & (J.min(1) > 3) & (J.max(1) < 252) & np.isin(k, (2, 3, 5, 6, 7, 8, 9, 10)); out.append((d["u"][s], J[s], z, int(round(float(z["sat"]) / f.SAT_PER_GAIN))))
    return out
Xv0, K0, SPG0 = mocklib.Xv.copy(), mocklib.K, f.SAT_PER_GAIN
def setp(p): mocklib.Xv = p[:36].reshape(6, 2, 3); mocklib.K = K0 * p[36]; M2.CLAMP = p[38]; return SPG0 * p[37]
def res(p, D):
    spg = setp(p); r = [(M2.render(u, z["G"], gain * spg, z["S"], z["H"], z["P"], M2.chroma_of(z)) - J).ravel() for u, J, z, gain in D]
    r.append(30.0 * (p[:36] - Xv0.ravel()) / np.abs(Xv0).max())          # ridge: a direction the data does not exercise (red hue is 0 in every film) stays at its old value
    return np.concatenate(r)
def score(p, sets):
    spg = setp(p); o = []
    for rd, ft in sets:
        d = load(rd); z = np.load(f"out/fit_{ft}.npz"); J, k, ok = d["jpg"], d["kind"], d["ok"]; gain = int(round(float(z["sat"]) / f.SAT_PER_GAIN))
        dE = de(lab(J), lab(M2.render(d["u"], z["G"], gain * spg, z["S"], z["H"], z["P"], M2.chroma_of(z)))); o.append([dE[ok & (k == g)].mean() for g, _ in E.GROUPS])
    return np.mean(o, 0)
if __name__ == "__main__":
    p0 = np.concatenate([Xv0.ravel(), [1.0, 1.0, M2.CLAMP]]); D = data(TRAIN)
    fit = lambda c: least_squares(lambda q: res(np.concatenate([q, [c]]), D), p0[:38], loss="soft_l1", f_scale=2.0, x_scale="jac", max_nfev=60)
    r = fit(M2.CLAMP); best = (1e9, None)
    for c in (116, 118, 120, 122, 124, 126):                 # the chroma limit only shows on clipped patches, which the code residual leaves out: choose it by dE on all patches
        s = score(np.concatenate([r.x, [c]]), TRAIN)[-1]
        if s < best[0]: best = (s, c)
    r.x = np.concatenate([r.x, [best[1]]])
    print("chroma limit", r.x[38].round(2), "K x", r.x[36].round(4), " saturation per gain x", r.x[37].round(4), " six-axis vectors: max change", np.abs(r.x[:36] - p0[:36]).max().round(4), "of max", np.abs(p0[:36]).max().round(3))
    print(f"{'camera vs model':34s}" + "".join(f"{n:>13s}" for _, n in E.GROUPS))
    for nm, p, s in (("before, fitted builds", p0, TRAIN), ("after,  fitted builds", r.x, TRAIN), ("before, seven-films-3 (not fitted)", p0, TEST), ("after,  seven-films-3 (not fitted)", r.x, TEST)):
        print(f"{nm:34s}" + "".join(f"{v:13.2f}" for v in score(p, s)))
    np.savez("out/model2_calib.npz", Xv=r.x[:36].reshape(6, 2, 3), K=K0 * r.x[36], sat_per_gain=SPG0 * r.x[37], clamp=r.x[38])

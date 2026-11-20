"""Recalibrate model2 for the camera without the 12-region stage (NOTES.md §10). Research code; run from
experiments/2026-11-09-film-portra:

    OMP_NUM_THREADS=4 uv run --with colour-science python ../2026-11-20-model-calibration/scripts/calib_off.py [--save]

The constants of calib_model.py (12 six-axis direction vectors, exposure scale K, saturation per gain unit; the chroma
limit by ΔE) are fitted on the films-twelve-off readings (read_OFF_<id>: PB130001 developed with each catalogue film,
no 12-region table) of half the films and scored on the other half, both ways (two folds). --save refits on all 31
and writes calib/model3.npz (model2.npz stays: the shipped fits were made with it).
"""
import json, os, sys
import numpy as np
from scipy.optimize import least_squares

FP = os.getcwd()
sys.path.insert(0, FP)
argv = sys.argv; sys.argv = ["x"]
import calib_model as CM  # noqa: E402
import model2 as M2  # noqa: E402
from mocklib import load  # noqa: E402

CAT = json.load(open(os.path.join(FP, "..", "..", "data", "films", "catalogue.json")))["films"]


def rows(ids):
    out = []
    for fid in ids:
        z = np.load(os.path.join(FP, "..", "..", next(x["fit"] for x in CAT if x["id"] == fid)))
        d = load("OFF_" + fid)
        r = dict(name=fid, d=d, G=z["G"], gain=M2.gain_of(z), S=z["S"], H=z["H"], P=z["P"], ch=M2.chroma_of(z), look=None, mode=None)
        J, k, ok = d["jpg"], d["kind"], d["ok"]
        r["sel"] = ok & (J.min(1) > 3) & (J.max(1) < 252) & np.isin(k, (2, 3, 5, 6, 7, 8, 9, 10))
        out.append(r)
    return out


def fit(D):
    p0 = np.concatenate([CM.Xv0.ravel(), [1.0, 1.0], np.full(len(CM.MODES), 1.05)])
    r = least_squares(lambda q: CM.res(np.concatenate([q, p0[38:]]), D), p0[:38], loss="soft_l1", f_scale=2.0,
                      x_scale="jac", max_nfev=60)
    p = np.concatenate([r.x, p0[38:]])
    best = min((np.mean([v[-1] for v in CM.score(p, D, c).values()]), c) for c in (118, 120, 122, 124, 126, 128))
    return p, best[1]


def mean(sc):
    return np.mean(list(sc.values()), 0)


def main():
    ids = [x["id"] for x in CAT if x["id"] != "double-x" and os.path.exists(os.path.join(FP, "out", "mock", f"read_OFF_{x['id']}.npz"))]
    folds = [ids[0::2], ids[1::2]]
    c0 = float(np.load(os.path.join(FP, "calib", "model2.npz"))["clamp"])
    p_old = np.concatenate([CM.Xv0.ravel(), [1.0, 1.0], np.full(len(CM.MODES), 1.05)])
    groups = [n for _, n in CM.E.GROUPS]
    print(f"{len(ids)} films; camera vs model, mean over the films of the held-out fold, ΔE2000")
    print(f"{'':28s}" + "".join(f"{n:>13s}" for n in groups))
    for i, (tr, te) in enumerate(((folds[0], folds[1]), (folds[1], folds[0]))):
        Dtr, Dte = rows(tr), rows(te)
        p, c = fit(Dtr)
        print(f"fold {i + 1}: model2 (now)      " + "".join(f"{v:13.2f}" for v in mean(CM.score(p_old, Dte, c0))))
        print(f"fold {i + 1}: refitted          " + "".join(f"{v:13.2f}" for v in mean(CM.score(p, Dte, c))) +
              f"   (K x{p[36]:.4f}, saturation/gain x{p[37]:.4f}, limit {c})")
        CM.setp(p_old, c0)
    if "--save" in argv:
        p, c = fit(rows(ids))
        CM.setp(p, c)
        np.savez(os.path.join(FP, "calib", "model3.npz"), Xv=M2.XV, K=M2.K, sat_per_gain=M2.SAT_PER_GAIN, clamp=float(c),
                 mode_sat=p[38:], modes=list(CM.MODES))
        print("saved calib/model3.npz")


if __name__ == "__main__":
    main()

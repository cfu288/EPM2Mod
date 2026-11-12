"""Results of the second-generation test RAWs (NOTES §27-28): scene dependence (A vs B) and the
fit objective measured directly (GRKit weights).   ../../.venv/bin/python -I analyze_mock2.py [PORTRA_TAG EKTA_TAG PORTRA_FIT.npz EKTA_FIT.npz]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
argv = sys.argv; sys.argv = ["x"]
import fit_xp9 as f
from mocklib import *
KN = {6: "GRKit grays (w 150)", 7: "ColorChecker x5 EV (w 20/60)", 8: "skin series", 5: "fit natural colours (w 1)", 9: "hold-out naturals", 3: "near-neutrals", 2: "dense gray ramp", 10: "gamut-edge colours"}
def tgt_of(lut):
    cube, size = fl.load_cube(lut); return lambda v: lab(np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(v, 0) / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255)
EK = "out/lut/spektrafilm_v034_kodak_ektachrome_100_scanfilm_1lut_vlog_srgb/lut_v034_ektachrome100_scanfilm.cube"
print("1. Scene dependence: the same patches in the mixed image (A) and the blue-scene image (B)")
FILMS = sys_args if (sys_args := argv[1:3]) else ["portra_xp9", "ektachrome_lt2"]
FITS = argv[3:5] if len(argv) > 4 else ["out/fit_xp9.npz", "out/fit_film-ektachrome-lt2.npz"]
for film in FILMS:
    a, b = load(f"A_{film}"), load(f"B_{film}")
    ia = {int(s): i for i, s in enumerate(a["sid"]) if s >= 0}; rows = [(ia[int(s)], j) for j, s in enumerate(b["sid"]) if s >= 0 and int(s) in ia]
    i, j = np.array(rows).T; ok = a["ok"][i] & b["ok"][j]; i, j = i[ok], j[ok]
    dJ = b["jpg"][j] - a["jpg"][i]; d = de(lab(a["jpg"][i]), lab(b["jpg"][j])); u = a["u"][i]
    blue = (u[:, 2] > u[:, 0] * 1.1) & (u[:, 2] >= u[:, 1] * 0.9) | ((u[:, 1] > u[:, 0] * 1.15) & (u[:, 2] > u[:, 0] * 1.15))
    print(f"   {film:15s} {len(i)} shared patches: ΔE A vs B mean {d.mean():.3f}, max {d.max():.2f}; identical RGB in {100 * (np.abs(dJ).max(1) == 0).mean():.0f} %, within 1 code in {100 * (np.abs(dJ).max(1) <= 1).mean():.1f} %;"
          f" blue / cyan patches (n={blue.sum()}): mean {d[blue].mean():.3f}, max {d[blue].max():.2f}, mean RGB shift {dJ[blue].mean(0).round(2)}")
print("\n2. Camera vs target on image A, by sample set (ΔE2000 mean / p95 / max)")
for film, lut, fit in ((FILMS[0], CUBE, FITS[0]), (FILMS[1], EK, FITS[1])):
    d = load(f"A_{film}"); T = tgt_of(lut); z = np.load(fit); J, k, ok, w = d["jpg"], d["kind"], d["ok"], d["weight"]
    dT = de(lab(J), T(d["vs"])); P = f.R(d["u"], z["G"], float(z["sat"]), z["S"], z["H"], z["P"]); dP = de(lab(P), T(d["vs"])); dM = de(lab(J), lab(P))
    print(f"   {film}")
    for kk, nm in KN.items():
        m = ok & (k == kk); print(f"      {nm:28s} camera {dT[m].mean():5.2f} / {np.percentile(dT[m], 95):5.2f} / {dT[m].max():5.2f}   model predicted {dP[m].mean():5.2f}   camera vs model {dM[m].mean():5.2f}   (n={m.sum()})")
    m = ok & (w > 0); print(f"      GRKit-weighted objective: camera {np.average(dT[m], weights=w[m]):.3f}   model predicted {np.average(dP[m], weights=w[m]):.3f}")
    c = ok & (k == 7); sk = c & (w == 60); print(f"      ColorChecker skin patches only: camera {dT[sk].mean():.2f} (n={sk.sum()})")
print("\n3. Natural (stock) on image A: model vs camera")
d = load("A_natural"); J, k, ok = d["jpg"], d["kind"], d["ok"]; P = render(d["vs"]); dM = de(lab(J), lab(P))
g = ok & (k == 6); print("   GRKit grays: camera RGB spread (max - min channel) mean", np.ptp(J[g], axis=1).mean().round(2), " (0 = neutral)")
for kk, nm in KN.items():
    m = ok & (k == kk); print(f"      {nm:28s} model vs camera {dM[m].mean():5.2f} / p95 {np.percentile(dM[m], 95):5.2f}  (n={m.sum()})")

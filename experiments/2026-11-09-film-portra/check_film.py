"""Score a mock re-development against any film target and against a fit's model prediction.
   ../../.venv/bin/python -I check_film.py shots/PXXXXXXX.JPG out/fit_<name>.npz"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
argv = sys.argv; sys.argv = ["x"]
import fit_xp9 as f
from mocklib import *
name = os.path.splitext(os.path.basename(argv[1]))[0]
r = subprocess.run([sys.executable, "-I", "read_mock.py", argv[1]], capture_output=True, text=True)      # always re-read: the camera reuses file names, so a cached reading may be of another picture
if r.returncode: sys.exit(r.stdout + r.stderr)
z = np.load(argv[2]); cube, size = fl.load_cube(str(z["lut"]))
tgt = lambda v: lab(np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(v, 0) / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255)
d = load(name); J, k, ok = d["jpg"], d["kind"], d["ok"]
print("camera ColorMatrix x256:", (d["M"] * 256).round().astype(int).ravel().tolist(), " expected:", (f.renormalise(z["A"]) * 2).ravel().tolist())
dT = de(lab(J), tgt(d["vs"])); P = f.R(d["u"], z["G"], float(z["sat"]), z["S"], z["H"], z["P"])
if "Cb" in z.files:                                  # the build has fitted chroma curves (NOTES 43)
    import chroma; P = np.clip(chroma.apply(P, tuple(z["Cb"][:2]) + (z["Cb_slope17"],), tuple(z["Cr"][:2]) + (z["Cr_slope17"],), stored=True), 0, 255)
dM = de(lab(J), lab(P)); dP = de(lab(P), tgt(d["vs"]))
unc = (J.min(1) > 2) & (J.max(1) < 253)
for kk, nm in ((5, "natural colours"), (3, "near-neutrals"), (2, "gray ramp")):
    m = ok & (k == kk); mu = m & unc
    if not m.any(): continue                              # the blue-scene image (mock2b) has no near-neutrals or gray ramp
    print(f"  {nm:15s}: camera vs target {dT[m].mean():.2f} (p95 {np.percentile(dT[m], 95):.2f}, max {dT[m].max():.2f}) | predicted {dP[m].mean():.2f} | camera vs model {dM[mu].mean():.2f}  (n={m.sum()})")
g = ok & (k == 2) & unc
if g.any(): print("  gray ramp mean (camera - model) RGB:", (J[g] - P[g]).mean(0).round(2))

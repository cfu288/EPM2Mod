"""Score one Portra re-development of the mock image: camera vs target, and vs the fit's prediction.
   ../../.venv/bin/python -I check_mock.py shots/PXXXXXXX.JPG [out/fit_xp9.npz]"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from mocklib import *
name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
if not os.path.exists(f"out/mock/read_{name}.npz"):
    subprocess.run([sys.executable, "-I", "read_mock.py", sys.argv[1]], check=True)
d = load(name); J, k, ok = d["jpg"], d["kind"], d["ok"]
print("camera loaded ColorMatrix x256:", (d["M"] * 256).round().astype(int).ravel().tolist(), " WB", (d["wb"][[0, 2]] * 256).round().astype(int).tolist())
dT = de(lab(J), target(np.maximum(d["vs"], 0)))
for kk, nm in ((5, "natural colours"), (3, "near-neutrals"), (2, "gray ramp")):
    m = ok & (k == kk); print(f"  camera vs target, {nm:15s}: mean {dT[m].mean():.2f}  p95 {np.percentile(dT[m], 95):.2f}  max {dT[m].max():.2f}  (n={m.sum()})")
if len(sys.argv) > 2:
    z = np.load(sys.argv[2]); sel = z["mock_sel"] & ok; idx = np.cumsum(z["mock_sel"]) - 1
    dp = de(lab(J[sel]), lab(z["mock_pred"][idx[sel]]))
    for kk, nm in ((5, "natural colours"), (3, "near-neutrals"), (2, "gray ramp")):
        m = k[sel] == kk; print(f"  camera vs prediction, {nm:15s}: mean {dp[m].mean():.2f}  p95 {np.percentile(dp[m], 95):.2f}")

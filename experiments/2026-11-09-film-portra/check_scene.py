"""Real photo check: camera Portra JPEG (RAW Data Edit) vs the target and vs the model, on 64-px blocks of
the central half of the frame (little lens-distortion shift there), flat blocks only.
   ../../.venv/bin/python -I check_scene.py shots/RAW.orf shots/EDIT.JPG out/fit_xp9.npz"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, rawpy, cv2
import fit_xp9 as f
from mocklib import *
raw_p, jpg_p, fit_p = sys.argv[1:4]
e = json.loads(subprocess.run(["exiftool", "-j", "-n", "-WB_RBLevels", "-ColorMatrix", jpg_p], capture_output=True, text=True).stdout)[0]
lv = [float(x) for x in str(e["WB_RBLevels"]).split()]; wb = np.array([lv[0] / 256, 1, lv[1] / 256])
Mx = np.array([float(x) for x in str(e["ColorMatrix"]).split()]).reshape(3, 3) / 256
with rawpy.imread(raw_p) as r:
    im = r.raw_image.astype(float) - np.mean(r.black_level_per_channel)
B = 64; H, W = im.shape; y0, y1, x0, x1 = H // 4, 3 * H // 4, W // 4, 3 * W // 4
jpg = cv2.cvtColor(cv2.imread(jpg_p, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION), cv2.COLOR_BGR2RGB).astype(float)
U, J = [], []
for y in range(y0 - y0 % 2, y1 - B, B):
    for x in range(x0 - x0 % 2, x1 - B, B):
        blk = im[y:y + B, x:x + B]; jb = jpg[y - 8 + 12:y - 8 + B - 12, x - 16 + 12:x - 16 + B - 12].reshape(-1, 3)
        if jb.std(0).max() > 4 or blk.max() > 3700: continue
        U.append([blk[0::2, 0::2].mean(), (blk[0::2, 1::2].mean() + blk[1::2, 0::2].mean()) / 2, blk[1::2, 1::2].mean()]); J.append(jb.mean(0))
U = np.array(U) * wb; J = np.array(J); vs = U @ M5300.T
z = np.load(fit_p); model = f.R(U, z["G"], float(z["sat"]), z["S"], z["H"], Mx)
dT = de(lab(J), target(np.maximum(vs, 0))); dM = de(lab(J), lab(model))
blue = (vs[:, 2] > vs[:, 0] * 1.15) & (vs[:, 2] >= vs[:, 1] * 0.95)
print(f"flat blocks {len(J)}; camera vs target mean {dT.mean():.2f} p95 {np.percentile(dT, 95):.2f}; camera vs model mean {dM.mean():.2f}")
print(f"  blue / cyan-blue blocks (n={blue.sum()}): camera vs target {dT[blue].mean():.2f}; camera vs model {dM[blue].mean():.2f}; mean (camera - model) RGB {(J[blue] - model[blue]).mean(0).round(1)}")
print(f"  other blocks (n={(~blue).sum()}): camera vs target {dT[~blue].mean():.2f}; camera vs model {dM[~blue].mean():.2f}; mean (camera - model) RGB {(J[~blue] - model[~blue]).mean(0).round(1)}")

"""Camera against model2 (stages 1-6) for the 31 colour films: with Natural's 12-region table (confirmation round,
films-look-exif) and with none (films-twelve-off-artbkt round). Research code; run from experiments/2026-11-09-film-portra:

    OMP_NUM_THREADS=2 uv run --with colour-science python ../2026-11-20-model-calibration/scripts/camera_vs_model.py
"""
import os
import sys, json, numpy as np
sys.argv = ["x"]; sys.path.insert(0, os.getcwd())
import fit_xp9 as f
from mocklib import load, lab, de
import model2 as M2
cat = {x["id"]: x for x in json.load(open("../../data/films/catalogue.json"))["films"]}
have = {}
import os
for fn in os.listdir("out/mock"):
    if fn[5:7] in ("CA", "CB", "CC") and fn[7] == "_" and fn.endswith(".npz"): have[fn[8:-4]] = fn[5:-4]
rows = []
for fid, x in cat.items():
    if fid == "double-x" or fid not in have: continue
    z = np.load("../../" + x["fit"])
    out = []
    for tag in (have[fid], "OFF_" + fid):
        d = load(tag); J, k = d["jpg"], d["kind"]
        P = M2.render(d["u"], z["G"], M2.gain_of(z), z["S"], z["H"], z["P"], M2.chroma_of(z))
        ok = d["ok"] & (J.min(1) > 2) & (J.max(1) < 253)
        dm = de(lab(np.nan_to_num(J)), lab(P))
        out.append([dm[ok & (k == kk)].mean() for kk in (5, 7, 8, 6)])
    rows.append((fid, out))
a = np.array([r[1] for r in rows])
for i, n in enumerate(["natural", "ColorChecker", "skin", "grays"]):
    print(f"camera vs model2, {n:12s}: Natural's table {np.median(a[:,0,i]):.2f} ({a[:,0,i].min():.2f}-{a[:,0,i].max():.2f})  ->  no table {np.median(a[:,1,i]):.2f} ({a[:,1,i].min():.2f}-{a[:,1,i].max():.2f}); closer for {np.sum(a[:,1,i] < a[:,0,i] - 0.005)}/{len(a)} films")

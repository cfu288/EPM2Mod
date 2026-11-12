"""First look at the mock-image results (NOTES §25): where is xp8 vs the target, and how good is the model?
   ../../.venv/bin/python -I analyze_mock.py"""
import numpy as np
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mocklib import *
KN = {0: "white", 1: "grid 17^3", 2: "gray ramp", 3: "near-neutral", 4: "mid gray", 5: "natural"}
N, P = load("PB120003"), load("PB120002")
x8 = np.load("out/fit_xp8.npz"); G8, sat8, S8, H8, A8 = x8["G"], float(x8["sat"]), x8["S"], x8["H"], x8["A"]
vs = N["vs"]; ok = N["ok"] & P["ok"]
ingam = (vs.min(1) >= 0)                                   # inside sRGB gamut
noclipN = (N["jpg"].min(1) > 3) & (N["jpg"].max(1) < 252)
noclipP = (P["jpg"].min(1) > 3) & (P["jpg"].max(1) < 252)
def stat(d, m): return f"mean {d[m].mean():5.2f}  median {np.median(d[m]):5.2f}  p95 {np.percentile(d[m], 95):5.2f}  max {d[m].max():5.2f}  (n={m.sum()})"
print("EXIF matrix Portra x256:", (P["M"] * 256).round().astype(int).tolist(), " model A·M x256:", (A8 @ M5300 * 256).round(1).tolist())
print("\n1. Natural: model vs camera (ΔE2000)")
dN = de(lab(render(vs)), lab(N["jpg"]))
for k in (1, 2, 3, 5): print(f"   {KN[k]:13s} unclipped: {stat(dN, ok & (N['kind'] == k) & noclipN)}   in-gamut unclipped: {stat(dN, ok & (N['kind'] == k) & noclipN & ingam)}")
print("\n2. Portra xp8: camera vs target (ΔE2000)   [what the build really does]")
tl = target(np.maximum(vs, 0)); dT = de(lab(P["jpg"]), tl)
for k in (2, 3, 5): print(f"   {KN[k]:13s} all: {stat(dT, ok & (P['kind'] == k))}")
k1 = ok & (P["kind"] == 1) & ingam; print(f"   {KN[1]:13s} in-gamut: {stat(dT, k1)}")
print("\n3. Portra xp8: model vs camera (ΔE2000)")
for nm, pred in (("model, A as fitted", render(vs, G8, sat8, S8, H8, A8)), ("model, EXIF product matrix", render(P["v"], G8, sat8, S8, H8))):
    dM = de(lab(pred), lab(P["jpg"]))
    for k in (1, 2, 3, 5): print(f"   {nm:27s} {KN[k]:13s} unclipped: {stat(dM, ok & (P['kind'] == k) & noclipP)}")

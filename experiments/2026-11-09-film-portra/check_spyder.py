"""Real-chart check: Datacolor SpyderCheckr 24 shots (shots/PB110234-0237), live captures.

Patch centres are bilinear from four hand-picked corner-patch centres (1152 x 864 JPEG scale).
For every patch: raw -> v = ColorMatrix·(WB ⊙ raw) with the file's own EXIF values; then
  model   = camera model (base gamma 0x7E74E9BC, fitted G curves or identity, saturation)
  target  = spektrafilm Portra 400 LUT applied to v (18 % gray = v 264)
and ΔE2000 of the camera JPEG against both.   ../../.venv/bin/python -I check_spyder.py
"""
import json, struct, subprocess, sys
import numpy as np, rawpy
from PIL import Image
import importlib.util
sys.argv = ["x"]
sp = importlib.util.spec_from_file_location("fl", "fit_look.py"); fl = importlib.util.module_from_spec(sp); sp.loader.exec_module(fl)

CORNERS = {"PB110237": [(241, 240), (894, 232), (236, 636), (903, 630)], "PB110235": [(249, 240), (893, 231), (244, 630), (903, 625)]}
CORNERS["PB110236"] = CORNERS["PB110237"]; CORNERS["PB110234"] = CORNERS["PB110235"]
K, X = 0.0621, np.arange(256)
BASE = fl.table(0x7E74E9BC)

def centres(c):
    tl, tr, bl, br = [np.array(p, float) for p in c]
    return np.array([(tl * (1 - u) + tr * u) * (1 - w) + (bl * (1 - u) + br * u) * w for w in np.linspace(0, 1, 4) for u in np.linspace(0, 1, 6)])

def read(n):
    e = json.loads(subprocess.run(["exiftool", "-j", "-n", "-WB_RBLevels", "-ColorMatrix", f"shots/{n}.ORF"], capture_output=True, text=True).stdout)[0]
    lv = [float(x) for x in str(e["WB_RBLevels"]).split()]; wb = np.array([lv[0] / 256, 1, lv[1] / 256])
    M = np.array([float(x) for x in str(e["ColorMatrix"]).split()]).reshape(3, 3) / 256
    jpg = np.asarray(Image.open(f"shots/{n}.JPG").convert("RGB")).astype(float)
    with rawpy.imread(f"shots/{n}.ORF") as r:
        raw = r.raw_image_visible.astype(float); pat = r.raw_pattern; desc = r.color_desc.decode(); blk = r.black_level_per_channel
        pl = {}
        for i in range(2):
            for j in range(2):
                pl.setdefault(desc[pat[i, j]], []).append(raw[i::2, j::2] - blk[pat[i, j]])
    planes = [pl["R"][0], (pl["G"][0] + pl["G"][1]) / 2, pl["B"][0]]
    J, R, clip, spread = [], [], [], []
    for cx, cy in centres(CORNERS[n]) * 4:
        h = 40
        box = jpg[int(cy) - h:int(cy) + h, int(cx) - h:int(cx) + h].reshape(-1, 3)
        J.append(np.median(box, 0)); spread.append((np.percentile(box, 90, 0) - np.percentile(box, 10, 0)).max())
        rx, ry, hh = int((cx + 16) / 2), int((cy + 8) / 2), 20
        rr = [p[ry - hh:ry + hh, rx - hh:rx + hh] for p in planes]
        R.append([np.median(x) for x in rr]); clip.append(max(x.max() for x in rr) >= 4045 - 256)
    R = np.array(R)
    return (R * wb) @ M.T, np.array(J), np.array(clip), np.array(spread)

def cam(v, G, sat):
    b = np.interp(K * np.maximum(v, 0), X, BASE)
    c = np.stack([np.interp(b[:, i], np.arange(1024), G[i]) for i in range(3)], 1) / 4
    y = c @ np.array([.299, .587, .114]); return np.clip(y[:, None] + sat * (c - y[:, None]), 0, 255)

cube, size = fl.load_cube("out/lut/spektrafilm_v034_portra400_portraendura_1lut_vlog_srgb/lut_v034_portra400_portraendura.cube")
GP = np.load("out/fit_crossprocess_G.npy"); GI = np.tile(np.arange(1024.0), (3, 1))
lab, de = fl.srgb_to_lab, fl.de2000
print("shot       mode     WB     | camera vs model: gray  colour | camera vs Portra target: gray  colour  max | usable patches")
out = {}
for n, mode, wbn, G, sat in (("PB110237", "Natural", "Auto ", GI, 1.078), ("PB110236", "Portra ", "Auto ", GP, 0.937),
                             ("PB110234", "Natural", "5300K", GI, 1.078), ("PB110235", "Portra ", "5300K", GP, 0.937)):
    v, J, clip, spread = read(n)
    ok = (~clip) & (spread < 25) & (J.min(1) > 3) & (J.max(1) < 252)
    gray = np.arange(24) >= 18
    T = np.clip(fl.apply_cube(cube, size, fl.encode(v / 264.0 * 0.18, "vlog")), 0, 1) * 255
    dm = de(lab(cam(v, G, sat)), lab(J)); dt = de(lab(J), lab(T))
    f = lambda d, m: f"{d[m & ok].mean():5.2f}" if (m & ok).any() else "  n/a"
    print(f"{n}  {mode}  {wbn}  |                  {f(dm, gray)}  {f(dm, ~gray)}  |                         {f(dt, gray)}  {f(dt, ~gray)}  {dt[ok].max():5.2f} | {ok.sum()}/24  (max spread {spread.max():.0f})")
    out[n] = (v, J, T, ok)
np.savez("out/spyder_patches.npz", **{k + "_" + nm: a for k, t in out.items() for nm, a in zip(("v", "jpg", "target", "ok"), t)})
v, J, T, ok = out["PB110236"]
print("\nPB110236 (Portra, Auto WB) per patch: camera RGB | target RGB | ΔE")
names = "D1 D2 D3 D4 D5 D6 C1 C2 C3 C4 C5 C6 B1 B2 B3 B4 B5 B6 A1 A2 A3 A4 A5 A6".split()
d = de(lab(J), lab(T))
for i in range(24):
    print(f"  {names[i]} {J[i].round(0)} | {T[i].round(0)} | {d[i]:5.2f}{'' if ok[i] else '  (excluded)'}")

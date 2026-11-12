"""Calibrate the six-axis stage on the mock-image renderings (NOTES §25).

Five renderings of the same 6,912 patches, all with known settings: Natural, Vivid, Muted,
Portrait (stock records) and Portra xp8. Model per patch (mocklib.render):
    v (EXIF matrix · WB · raw) -> six-axis: v + sum_k W_k(v) (S_k a_k + H_k b_k) -> base gamma ->
    per-channel curve (Portra only) -> look curve on luma -> saturation gain
Unknowns: the 12 direction vectors a_k, b_k (36 numbers) and one saturation value per mode; fitted
on the JPEG codes of all unclipped patches (robust loss). Compared with the old vectors
(out/sixaxis_rank_lin.npy, from 4 chart pairs).   ../../.venv/bin/python -I fit_mock.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import least_squares
from mocklib import *
import mocklib

x8 = np.load("out/fit_xp8.npz")
VAR = int(os.environ.get("VARIANT", "0"))      # which member of the stock record pair (0: G +3 variant, 1: plain)
g3 = 3.0 if VAR == 0 else 0.0
MODES = {  # file, per-channel curve, look table, nominal saturation, S, H
    "Natural": ("PB120003", IDG, IDENT, 1.078, (0, g3, 0, 0, 0, 0), (0, g3, 0, 0, 0, 0)),
    "Vivid": ("PB120004", IDG, IDENT, 1.078 * 310 / 282, (18, 4 + g3, 24, 0, 8, 8), (0, 2 + g3, 4, -1, -6, 0)),
    "Muted": ("PB120006", IDG, fl.table(0x7E75D0F0), 1.078, (-22, 4 + g3, -16, 0, 4, -8), (3, 0 + g3, -3, 7 + (2 if VAR == 0 else 0), 8, 10)),
    "Portrait": ("PB120005", IDG, fl.table(0x7E75DAF0), 1.078, (14, 0 + g3, 0, 5, 0, 0), (-1, 0 + g3, 2, -2, 0, 0)),
    "Portra xp8": ("PB120002", x8["G"], IDENT, float(x8["sat"]), tuple(x8["S"]), tuple(x8["H"])),
}
ZERO = np.zeros(6)
D = {}
for nm, (f, G, look, sat, S, H) in MODES.items():
    d = load(f); J = d["jpg"]
    m = d["ok"] & (J.min(1) > 2) & (J.max(1) < 253)
    D[nm] = (d["v"][m], J[m], G, look, sat, np.array(S, float), np.array(H, float), d["kind"][m])

def pred(nm, xv, sat=None):
    v, J, G, look, s0, S, H, _ = D[nm]
    mocklib.Xv = xv
    return render(v, G, s0 if sat is None else sat, S, H, None, look, base=ZERO)

def report(tag, xv, sats=None):
    out = []
    for i, nm in enumerate(D):
        P = pred(nm, xv, None if sats is None else sats[i]); J, kind = D[nm][1], D[nm][7]
        d = de(lab(P), lab(J)); out.append(f"{nm} {d.mean():.2f} (natural {d[kind == 5].mean():.2f}, grid {d[kind == 1].mean():.2f})")
    print(f"  {tag}: " + " | ".join(out))

OLD = np.load("out/sixaxis_rank_lin.npy").reshape(6, 2, 3)
def vectors(p):
    """The R hue vector stays at its old (chart-probe, +/-20) value: the mock modes only have R hue -1..3."""
    xv = p[:36].reshape(6, 2, 3).copy(); xv[0, 1] = OLD[0, 1]; return xv

def res(p):
    xv = vectors(p)
    return np.concatenate([(pred(nm, xv, p[36 + i]) - D[nm][1]).ravel() for i, nm in enumerate(D)])

if __name__ == "__main__":
    print("patches per mode:", {nm: len(D[nm][0]) for nm in D}, " variant", VAR)
    old = np.load("out/sixaxis_rank_lin.npy").reshape(6, 2, 3)
    print("ΔE2000 model vs camera, mean:")
    report("no six-axis            ", np.zeros((6, 2, 3)))
    report("old vectors            ", old)
    p0 = np.concatenate([old.ravel(), [D[nm][4] for nm in D]])
    r = least_squares(res, p0, loss="soft_l1", f_scale=3.0, x_scale="jac", max_nfev=60)
    xv = vectors(r.x); sats = r.x[36:]
    report("refitted vectors + sat ", xv, sats)
    print("  saturation per mode: " + ", ".join(f"{nm} {s:.3f} (nominal {D[nm][4]:.3f})" for nm, s in zip(D, sats)))
    for n, k in zip("RGBYCM", range(6)):
        print(f"  {n}: sat x1000 {np.round(xv[k, 0] * 1000, 2)} (old {np.round(old[k, 0] * 1000, 2)})   hue x1000 {np.round(xv[k, 1] * 1000, 2)} (old {np.round(old[k, 1] * 1000, 2)})")
    np.savez(f"out/mock/sixaxis_mock_v{VAR}.npz", Xv=xv, sats=sats, names=list(D))

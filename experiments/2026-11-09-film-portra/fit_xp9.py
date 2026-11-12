"""Refit of the Portra slot from the mock-image measurement of xp8 (NOTES §25) -> patches/film-portra-xp9.json

Model = mocklib.render with: the look table's highlight shoulder, the six-axis vectors calibrated on
five mock renderings (fit_mock.py), saturation = 0.926 x gain / 249 (measured for xp8), and the
matrix the camera really applies (renormalise(), from the code at 0x7E56C4C2; it reproduces the
EXIF ColorMatrix of the xp7 and xp8 JPEGs).

Objective (ΔE2000 vs the spektrafilm Portra 400 target, GRKit weights):
  - the GRKit sample set (gray 150, ColorChecker 20 / skin 60, random natural 1), predicted by the
    model; the grays get the measured-minus-model correction of the mock gray ramp;
  - the mock patches themselves (natural colours, near-neutrals, gray ramp), predicted as
    measured xp8 + model(new) - model(xp8), so only the change relies on the model.
   ../../.venv/bin/python -I fit_xp9.py
"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import least_squares
from mocklib import *
import mocklib

mocklib.Xv = np.load("out/mock/sixaxis_mock_v0.npz")["Xv"]
ZERO = np.zeros(6); SAT_PER_GAIN = 0.926 / 249
M7 = np.round(M5300 * 128).astype(int); MINV = np.linalg.inv(M5300)
x8 = np.load("out/fit_xp8.npz"); G8, S8, H8 = x8["G"], x8["S"], x8["H"]; A8 = np.round(x8["A"] * 256).astype(int); GAIN8 = 249
KN = 16; kx = np.linspace(0, 1023, KN)

def renormalise(A256):
    """Art table (x256) -> the 7-bit matrix the camera loads (x128). Off-diagonals of floor(A·M/2),
    made even where 0x7E56C4C2 does it; each diagonal = 128 - the row's off-diagonals."""
    p = np.floor(A256 @ M7 / 256.0).astype(int)
    p[0, 1] &= ~1
    if (p[1, 0] + p[1, 2]) & 1: p[1, 0] &= ~1; p[1, 2] &= ~1
    p[2, 1] &= ~1
    for i in range(3): p[i, i] = 128 - (p[i].sum() - p[i, i])
    return p
assert (renormalise(A8) * 2 == np.array([[362, -76, -30], [-60, 332, -16], [-2, -160, 418]])).all()
assert (renormalise(np.array([[236, 20, 0], [-5, 242, 19], [-12, -25, 293]])) * 2 == np.array([[386, -104, -26], [-62, 336, -18], [0, -180, 436]])).all()

def curves(p): return np.array([np.interp(N1, kx, np.minimum(np.cumsum(p[i * KN:(i + 1) * KN] ** 2), 1023.0)) for i in range(3)])
def knots_of(G):
    y = np.array([np.interp(kx, N1, G[i]) for i in range(3)]); d = np.diff(np.concatenate([np.zeros((3, 1)), y], 1), axis=1)
    return np.sqrt(np.maximum(d, 1e-3)).ravel()
def P_of(o):   # six off-diagonals (x128) -> full applied matrix (float)
    o = o.reshape(3, 2); return np.array([[128 - o[0].sum(), o[0, 0], o[0, 1]], [o[1, 0], 128 - o[1].sum(), o[1, 1]], [o[2, 0], o[2, 1], 128 - o[2].sum()]]) / 128.0
def off(P): return np.array([P[0, 1], P[0, 2], P[1, 0], P[1, 2], P[2, 0], P[2, 1]], float)
def R(u, G, sat, S, H, P): return render(u @ P.T, G, sat, S, H, None, IDENT, base=ZERO)
def unpack(p): return curves(p), p[3 * KN], np.concatenate([p[3 * KN + 1:3 * KN + 7]]), np.concatenate([[0.0], p[3 * KN + 7:3 * KN + 12]]), P_of(p[3 * KN + 12:3 * KN + 18])

# ---- data ----
# The xp8 measurement this refit is anchored on: PB120002.JPG on the first test RAW. Uploads later reused that file
# name, and the user moves older uploads into shots/archive*/; a copy is kept as shots/mock1/xp8_mock1.JPG (NOTES 37.4).
P8 = renormalise(A8) / 128.0; sat8 = SAT_PER_GAIN * GAIN8
lin, w, kind = fl.samples(); us = (lin / 0.18 * fl.V_GRAY) @ MINV.T; tl_s = target(lin / 0.18 * fl.V_GRAY)
HAVE_ANCHOR = os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "mock", "read_xp8_mock1.npz"))
if HAVE_ANCHOR:
    Pm = load("xp8_mock1"); Jm = Pm["jpg"]; um = Pm["u"]; kd = Pm["kind"]
    sel = Pm["ok"] & np.isin(kd, (2, 3, 5)) & (Jm.min(1) > 2) & (Jm.max(1) < 253)
    um_s, Jm_s, kd_s = um[sel], Jm[sel], kd[sel]; tl_m = target(np.maximum(Pm["vs"][sel], 0)); base_m = R(um_s, G8, sat8, S8, H8, P8)
    w_m = np.where(kd_s == 5, 1.0, np.where(kd_s == 3, 4.0, 20.0))
    # gray correction: measured - model on the mock gray ramp, by green level
    g = Pm["ok"] & (kd == 2); og = np.argsort(um[g][:, 1]); res_g = (Jm[g] - R(um[g], G8, sat8, S8, H8, P8))[og]; lvl_g = um[g][:, 1][og]
    ker = np.ones(9) / 9; res_gs = np.stack([np.convolve(np.pad(res_g[:, c], 4, mode="edge"), ker, "valid") for c in range(3)], 1)
    corr_s = np.zeros((len(us), 3)); gs = kind == 0
    corr_s[gs] = np.stack([np.interp(us[gs][:, 1], lvl_g, res_gs[:, c]) for c in range(3)], 1)
hold = fl.natural(3000, 2); hold = hold[hold.max(1) <= 0.18 * 2 ** 2.6]; uh = (hold / 0.18 * fl.V_GRAY) @ MINV.T; tl_h = target(hold / 0.18 * fl.V_GRAY)

def predict(G, sat, S, H, P):
    pm = np.clip(Jm_s + R(um_s, G, sat, S, H, P) - base_m, 0, 255)
    ps = np.clip(R(us, G, sat, S, H, P) + corr_s, 0, 255)
    return pm, ps

p8 = np.concatenate([knots_of(G8), [sat8], S8, H8[1:], off(P8 * 128)])
def res(p, fixed=None):
    if fixed is not None: p = np.concatenate([p, fixed])
    G, sat, S, H, P = unpack(p); pm, ps = predict(G, sat, S, H, P)
    return np.concatenate([np.sqrt(w_m) * de(lab(pm), tl_m), np.sqrt(w) * de(lab(ps), tl_s), 0.05 * np.diff(G[:, ::32], 2, axis=1).ravel(),
                           0.1 * (p[3 * KN + 1:3 * KN + 12] - p8[3 * KN + 1:3 * KN + 12])])
lo = np.concatenate([np.zeros(3 * KN), [0.6], [-40] * 6, [-20] * 5, [-64] * 6]); hi = np.concatenate([np.full(3 * KN, 40.0), [1.4], [40] * 6, [20] * 5, [64] * 6])

def find_A(Pt):
    """Integer art table (x256, rows summing to 256) whose renormalised matrix is nearest the wanted one."""
    A = np.round(Pt @ MINV * 256).astype(int)
    for i in range(3): A[i, i] += 256 - A[i].sum()
    best, bA = 1e9, A
    for _ in range(4):
        improved = False
        for i in range(3):
            for j in range(3):
                if i == j: continue
                for d in (-2, -1, 1, 2):
                    T = bA.copy(); T[i, j] += d; T[i, i] -= d
                    e = np.abs(renormalise(T) - Pt * 128).sum()
                    if e < best - 1e-9: best, bA, improved = e, T, True
        if not improved: break
    return bA

def summary(tag, pm, ps, ph):
    dm = de(lab(pm), tl_m); ds = de(lab(ps), tl_s); dh = de(lab(ph), tl_h)
    return (f"  {tag:26s} mock: natural {dm[kd_s == 5].mean():.2f} (p95 {np.percentile(dm[kd_s == 5], 95):.2f}) near-neutral {dm[kd_s == 3].mean():.2f} gray ramp {dm[kd_s == 2].mean():.2f} | "
            f"GRKit set: gray {ds[kind == 0].mean():.2f} ColorChecker {ds[kind == 1].mean():.2f} random {ds[kind == 2].mean():.2f} | hold-out (model) {dh.mean():.2f}")

if __name__ == "__main__":
    assert HAVE_ANCHOR, "run read_mock.py shots/mock1/xp8_mock1.JPG first (the xp8 anchor measurement)"
    lines = ["ΔE2000 vs the Portra target:"]
    pm, ps = predict(G8, sat8, S8, H8, P8)
    lines.append(summary("xp8 (mock = MEASURED)", pm, ps, R(uh, G8, sat8, S8, H8, P8)))
    r = least_squares(res, np.clip(p8, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), x_scale="jac", max_nfev=150)
    G, sat, S, H, P = unpack(r.x)
    lines.append(summary("xp9 continuous", *predict(G, sat, S, H, P), R(uh, G, sat, S, H, P)))
    # discrete values, then polish curves + saturation with them fixed
    S, H = np.round(S), np.round(H); A = find_A(P); Pq = renormalise(A) / 128.0
    fixed = np.concatenate([S, H[1:], off(Pq * 128)]); n0 = 3 * KN + 1
    r2 = least_squares(lambda q: res(q, fixed), r.x[:n0], bounds=(lo[:n0], hi[:n0]), x_scale="jac", max_nfev=80)
    G = curves(r2.x); gain = int(round(r2.x[3 * KN] / SAT_PER_GAIN)); sat = gain * SAT_PER_GAIN
    pm, ps = predict(G, sat, S, H, Pq)
    lines.append(summary("xp9 as written", pm, ps, R(uh, G, sat, S, H, Pq)))
    lines += [f"  saturation gain {GAIN8} -> {gain}; S {S8.astype(int).tolist()} -> {S.astype(int).tolist()}; H {H8.astype(int).tolist()} -> {H.astype(int).tolist()}",
              f"  art table x256 {A8.tolist()} -> {A.tolist()}",
              f"  matrix the camera will load (EXIF ColorMatrix at 5300 K) {(renormalise(A8) * 2).tolist()} -> {(renormalise(A) * 2).tolist()}"]
    b0 = open(fl.tone.BLOCK0, "rb").read(); B = fl.tone.BASE
    op = lambda addr, new: {"type": "bytes", "block": 0, "offset": hex(addr - B), "expect": b0[addr - B:addr - B + len(new)].hex(), "new": new.hex()}
    ops = fl.xp_ops(G, gain) + [op(0x7E7694FE, struct.pack("<6h", *S.astype(int))), op(0x7E76950A, struct.pack("<6h", *H.astype(int))), op(0x7E768F46, struct.pack("<9h", *A.ravel())),
                                op(0x7E56C6A6, b"\x55"), op(0x7E56C6AA, b"\x57")]
    json.dump({"name": "film-portra-xp9", "description": "As film-portra-xp8, refitted from the mock-image measurement of xp8 with the recalibrated model (fit_xp9.py, NOTES §25).",
               "status": "built, NOT camera-tested", "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
               "base_sha256": "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", "ops": ops}, open("../../patches/film-portra-xp9.json", "w"), indent=1)
    np.savez("out/fit_xp9.npz", G=G, sat=sat, gain=gain, S=S, H=H, A=A, P=Pq, mock_pred=pm, mock_sel=sel)
    open("out/xp9_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

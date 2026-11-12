"""Shared pieces for the mock-image analyses (NOTES §24-25): data loading and the camera model."""
import importlib.util, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("fl", os.path.join(HERE, "fit_look.py")); fl = importlib.util.module_from_spec(sp); sp.loader.exec_module(fl)
lab, de = fl.srgb_to_lab, fl.de2000
K, X, N1, LUMA = 0.0621, np.arange(256), np.arange(1024), np.array([.299, .587, .114])
BASE, IDENT = fl.table(0x7E74E9BC), fl.table(fl.IDENTITY)
IDG = np.tile(N1.astype(float), (3, 1))
M5300 = np.array([418, -140, -22, -56, 360, -48, 14, -132, 374]).reshape(3, 3) / 256.0
CP0 = np.array([0, 3, 0, 0, 0, 0.0])
Xv = np.load(os.path.join(HERE, "out", "sixaxis_rank_lin.npy")).reshape(6, 2, 3)
CUBE = os.path.join(HERE, "out/lut/spektrafilm_v034_portra400_portraendura_1lut_vlog_srgb/lut_v034_portra400_portraendura.cube")
_cube, _size = fl.load_cube(CUBE)
def target_rgb(lin): return np.clip(fl.apply_cube(_cube, _size, fl.encode(lin, "vlog")), 0, 1) * 255
def target(v): return lab(target_rgb(v / fl.V_GRAY * 0.18))

def load(name):
    d = dict(np.load(os.path.join(HERE, "out", "mock", f"read_{name}.npz")))
    d["vs"] = d["u"] @ M5300.T          # scene-linear sRGB (no art matrix), raw units
    d["ok"] = np.isfinite(d["jpg"][:, 0]) & (d["spread"] < 3)
    return d

def comps(x):
    o = np.argsort(-x, axis=1); mx, md, mn = np.take_along_axis(x, o, 1).T
    W = np.zeros((len(x), 6)); r = np.arange(len(x)); W[r, o[:, 0]] = mx - md
    sec = np.array([[-1, 3, 5], [3, -1, 4], [5, 4, -1]]); W[r, sec[o[:, 0], o[:, 1]]] = md - mn
    return W

def down(lin, G=IDG, look=IDENT, sat=1.078):
    g = np.interp(K * np.maximum(lin, 0), X, BASE)
    b = np.stack([np.interp(g[:, i], N1, G[i]) for i in range(3)], 1) / 4.0
    y = b @ LUMA; yl = np.interp(y, X, look) / 4.0          # the "identity" table 0x7E75B8F0 has a shoulder above luma 208 (NOTES §25)
    return yl[:, None] + sat * (b - y[:, None])

def render(v, G=IDG, sat=1.078, S=None, H=None, A=None, look=IDENT, base=CP0):
    if A is not None: v = v @ A.T
    if S is not None:
        W = comps(v); dS, dH = np.asarray(S, float) - base, np.asarray(H, float) - base
        v = v + sum(W[:, k:k + 1] * (dS[k] * Xv[k, 0] + dH[k] * Xv[k, 1]) for k in range(6))
    return np.clip(down(v, G, look, sat), 0, 255)

"""Camera model, second version (NOTES §45): as mocklib.render / fit_xp9.R, plus what the camera does with values
outside the normal range, found on the gamut-edge patches of the test image:
  - a negative value after the colour matrix is NOT clipped: it goes through the tone curves with its sign
    (curve(-x) = -curve(x)), so it lowers the luma;
  - luma below 0 is held at 0;
  - Cb and Cr are limited to +-CLAMP codes around 128 before the chroma curves;
  - the six-axis directions, exposure scale, saturation per gain unit and the chroma limit are refitted on 14
    renderings of the synthetic test image (calib_model.py -> calib/model2.npz); no photographed chart is involved.
"""
import os
import numpy as np
import mocklib as m
import chroma as C
_c = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "calib", "model2.npz"))     # calib_model.py: fitted on renderings of the synthetic test image only
XV, K, SAT_PER_GAIN, CLAMP, OFFSET = _c["Xv"], float(_c["K"]), float(_c["sat_per_gain"]), float(_c["clamp"]), 0.0
def odd_interp(x, xp, fp): return np.sign(x) * np.interp(np.abs(x), xp, fp)
def pre(v, G=m.IDG, sat=1.078, look=None, clamp=None):
    """Scene-linear values after matrix and six-axis -> RGB before the chroma curves, not clipped."""
    look = m.IDENT if look is None else look; clamp = CLAMP if clamp is None else clamp
    g = odd_interp(K * v, m.X, m.BASE)
    b = np.stack([odd_interp(g[:, i], m.N1, G[i]) for i in range(3)], 1) / 4.0
    y = b @ m.LUMA; yl = np.interp(np.maximum(y, 0), m.X, look) / 4.0
    return C.rgb(yl, np.clip(0.564 * sat * (b[:, 2] - y), -clamp, clamp) + 128, np.clip(0.713 * sat * (b[:, 0] - y), -clamp, clamp) + 128)
def six(u, S, H, P):
    v = u @ P.T; W = m.comps(v); S = np.asarray(S, float); H = np.asarray(H, float)
    return v + sum(W[:, k:k + 1] * (S[k] * XV[k, 0] + H[k] * XV[k, 1]) for k in range(6))
def render(u, G, gain, S, H, P, chroma=None, clip=True, **kw):
    """u: white-balanced raw; gain: the saturation pair's value; P: the matrix the camera loaded (EXIF ColorMatrix / 256);
    chroma: ((x, y, slope), (x, y, slope)) as stored for Cb and Cr, or None for straight lines."""
    o = pre(six(u, S, H, P), G, gain * SAT_PER_GAIN, **kw)
    if chroma is not None: o = C.apply(o, chroma[0], chroma[1], stored=True)
    o = o + OFFSET
    return np.clip(o, 0, 255) if clip else o
def chroma_of(z): return ((z["Cb"][0], z["Cb"][1], z["Cb_slope17"]), (z["Cr"][0], z["Cr"][1], z["Cr_slope17"])) if "Cb" in z.files else None
def gain_of(z): return int(z["gain"])

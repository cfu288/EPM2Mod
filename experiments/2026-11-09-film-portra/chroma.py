"""The camera's last colour stage: one curve on Cb and one on Cr (NOTES §30.2, §43).

Stored per art filter as 97 bytes: x[16], y[16], slope[17] for the first curve and x[16], y[16], slope[16] for the
second. Piecewise linear on 8-bit chroma centred on 128: for the first knot i with x[i] >= c,
out = y[i] + slope[i] * (c - x[i]) / 128, i.e. slope[i] belongs to the segment that ends at knot i. Checked against
the camera with Pop Art's stock curves (same film with and without them): 0.5 codes rms on Cb and Cr.
Which stored curve is Cb and which is Cr is NOT known from stock data (every stock filter has two equal curves);
FIRST_IS_CB is the working assumption until a build with unequal curves is measured."""
import numpy as np
FIRST_IS_CB = True
XK = np.array([0, 28, 58, 88, 108, 128, 148, 168, 198, 228, 255.0])     # knots; 108..148 stay y = x so neutrals and faint colours are left to the saturation gain
NFREE = 8                                                              # per curve: four segment heights below 108, four above 148
LINEAR_Y = XK.copy()

def ycc(J):
    y = J @ np.array([.299, .587, .114]); return y, 128 + (J[:, 2] - y) * 0.564, 128 + (J[:, 0] - y) * 0.713
def rgb(y, cb, cr):
    r = y + (cr - 128) * 1.402; b = y + (cb - 128) * 1.772; return np.stack([r, (y - .299 * r - .114 * b) / .587, b], 1)
def ys_of(q):
    """8 positive segment heights (as square roots) -> y at the 11 knots."""
    h = np.asarray(q, float) ** 2; lo = 108 - np.cumsum(h[3::-1]); hi = 148 + np.cumsum(h[4:])
    return np.concatenate([lo[::-1], [108, 128, 148], hi])
def q_of(ys): return np.sqrt(np.concatenate([np.diff(ys[:5]), np.diff(ys[6:])]))
Q_LINEAR = q_of(LINEAR_Y)
def ev(c, ys):
    """Float curve (during fitting)."""
    return np.interp(c, XK, ys)
def quantise(ys):
    """-> (x[16], y[16], slope[17]) bytes as stored, mutually consistent."""
    y = np.clip(np.round(ys), 0, 255).astype(int); y[4:7] = (108, 128, 148); y = np.maximum.accumulate(y)
    sl = np.concatenate([[0], np.clip(np.round(128 * np.diff(y) / np.diff(XK)), 0, 255)]).astype(int)
    pad = 16 - len(XK); x = np.concatenate([XK.astype(int), np.full(pad, 255)]); yy = np.concatenate([y, np.full(pad, y[-1])]); s = np.concatenate([sl, np.full(pad + 1, sl[-1])])
    return x, yy, s
def ev_bytes(c, x, y, s):
    """The camera's evaluation of stored bytes."""
    i = np.clip(np.searchsorted(x, c, side="left"), 0, 15); return y[i] + s[i] * (c - x[i]) / 128.0
def apply(J, cb_curve, cr_curve, stored=False):
    """J: n x 3 RGB before the stage -> after. Curves: y at the knots (float), or (x, y, slope) byte triples if stored."""
    y, cb, cr = ycc(J)
    if stored: return rgb(y, ev_bytes(cb, *cb_curve), ev_bytes(cr, *cr_curve))
    return rgb(y, ev(cb, cb_curve), ev(cr, cr_curve))
def record(cb_bytes, cr_bytes):
    """97 bytes in stored order."""
    a, b = (cb_bytes, cr_bytes) if FIRST_IS_CB else (cr_bytes, cb_bytes)
    return bytes(np.concatenate([a[0], a[1], a[2], b[0], b[1], b[2][:16]]).astype(np.uint8))
def parse(rec):
    d = np.frombuffer(rec, np.uint8).astype(float); a = (d[0:16], d[16:32], d[32:49]); b = (d[49:65], d[65:81], d[81:97])
    return (a, b) if FIRST_IS_CB else (b, a)

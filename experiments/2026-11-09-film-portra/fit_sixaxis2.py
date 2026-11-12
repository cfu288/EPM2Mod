"""Recalibrate the six-axis model on all camera data, then refit Portra's 12 values (NOTES §20).

Calibration pairs (same RAW, before -> after, record delta known), monitor chart 216 colours each:
  Vivid / Muted / Portrait: stock -> sixaxis-probe-1        (PB090238-240 -> 244-246)
  Cross Process I:          (0,3,0,0,0,0)x2 -> xp3 values    (PB090223 -> PB090250)
Check pairs (not fitted): the same four on the SpyderCheckr RAW PB110237 where available.
Model: axis i (R G B Y C M) maps its unit vector u_i to (1 + a S) u_i + c H u_i_perp, plus luma
lS S + lH H per unit of the axis component; a and c may differ for positive and negative values.
   ../../.venv/bin/python -I fit_sixaxis2.py
"""
import json, struct, sys, importlib.util, io, contextlib
import numpy as np
from scipy.optimize import least_squares
from PIL import Image
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    sp = importlib.util.spec_from_file_location("fs", "fit_sixaxis.py"); fs = importlib.util.module_from_spec(sp); sp.loader.exec_module(fs)
    sp2 = importlib.util.spec_from_file_location("cs", "check_spyder.py"); cs = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(cs)
fl = fs.fl; lab, de = fl.srgb_to_lab, fl.de2000
ycc, rgb, weights, ORDER, IDX, A0, patches = fs.ycc, fs.rgb, fs.weights, fs.ORDER, fs.IDX, fs.A0, fs.patches
U = np.stack([np.cos(np.radians(A0)), np.sin(np.radians(A0))], 1); UP = np.stack([-U[:, 1], U[:, 0]], 1)
XP3 = (np.array([21, -40, 39, -27, 16, -12]), np.array([-2, 20, 14, 20, -9, 20])); CP0 = (np.array([0, 3, 0, 0, 0, 0]),) * 2
PAIRS = {"Vivid": ("PB090238", "PB090244", fs.STOCK["Vivid"], fs.PROBE["Vivid"]), "Muted": ("PB090239", "PB090245", fs.STOCK["Muted"], fs.PROBE["Muted"]),
         "Portrait": ("PB090240", "PB090246", fs.STOCK["Portrait"], fs.PROBE["Portrait"]), "Portra xp3": ("PB090223", "PB090250", CP0, XP3)}

def model(J, S, H, p):
    """p: (6 axes in ORDER) x [a+, a-, c+, c-, lS, lH]."""
    P = p.reshape(6, 6); y, cb, cr = ycc(J); W = weights(cb, cr); out = np.zeros((len(J), 3))
    for k in range(6):
        s, h = S[IDX[k]], H[IDX[k]]; ap, an, cp, cn, ls, lh = P[k]
        g = 1 + (ap if s >= 0 else an) * s; q = (cp if h >= 0 else cn) * h
        vec = g * U[k] + q * UP[k]
        out[:, 1] += W[:, k] * vec[0]; out[:, 2] += W[:, k] * vec[1]; out[:, 0] += W[:, k] * (ls * s + lh * h)
    return np.stack([y + out[:, 0], out[:, 1], out[:, 2]], 1)

DATA = {}
for m, (a, b, st, pr) in PAIRS.items():
    A, B = patches(a)[:6].reshape(-1, 3), patches(b)[:6].reshape(-1, 3)
    ok = (A.min(1) > 6) & (A.max(1) < 249) & (B.min(1) > 6) & (B.max(1) < 249)
    DATA[m] = (A[ok], B[ok], np.subtract(pr[0], st[0]).astype(float), np.subtract(pr[1], st[1]).astype(float))

def resid(p):
    r = [(model(A, dS, dH, p) - np.stack(ycc(B), 1)).ravel() for A, B, dS, dH in DATA.values()]
    P = p.reshape(6, 6)
    return np.concatenate(r + [40 * (P[:, 0] - P[:, 1]), 40 * (P[:, 2] - P[:, 3])])       # weak tie between the two signs
p0 = np.tile([0.004, 0.004, -0.02, -0.02, 0.0, 0.0], 6)
r = least_squares(resid, p0, x_scale=np.tile([0.002, 0.002, 0.01, 0.01, 0.005, 0.005], 6))
P = r.x.reshape(6, 6)
lines = ["Recalibrated six-axis units (axis: chroma %/unit for +S / -S; hue: degrees at +20 / -20; luma per unit S, H):"]
for k, n in enumerate(ORDER):
    ap, an, cp, cn, ls, lh = P[k]
    lines.append(f"  {n}: gain {ap*100:+.2f} / {an*100:+.2f} %   hue {np.degrees(np.arctan(cp*20)):+6.1f} / {np.degrees(np.arctan(-cn*20)):+6.1f} deg   luma {ls:+.4f} {lh:+.4f}")
def toRGB(Y): return np.clip(rgb(Y[:, 0], Y[:, 1], Y[:, 2]), 0, 255)
lines.append("Fit quality, ΔE2000 predicted vs real 'after' (no model / old model / recalibrated):")
for m, (A, B, dS, dH) in DATA.items():
    lines.append(f"  {m:11s} {de(lab(A), lab(B)).mean():5.2f} / {de(lab(fs.sixaxis(A, dS, dH)), lab(B)).mean():5.2f} / {de(lab(toRGB(model(A, dS, dH, r.x))), lab(B)).mean():5.2f}  (n={len(A)})")

# ---- independent check on the SpyderCheckr RAW Data Edits ----
def spy(n):
    jpg = np.asarray(Image.open(f"shots/{n}.JPG").convert("RGB")).astype(float)
    return np.array([np.median(jpg[int(cy) - 40:int(cy) + 40, int(cx) - 40:int(cx) + 40].reshape(-1, 3), 0) for cx, cy in cs.centres(cs.CORNERS["PB110237"]) * 4])
lines.append("Check on SpyderCheckr pairs (not used in the calibration), no model / recalibrated:")
for m, a, b in (("Vivid", "PB110241", "PB110247"), ("Muted", "PB110242", "PB110248"), ("Portrait", "PB110243", "PB110249")):
    A, B = spy(a), spy(b); dS, dH = DATA[m][2], DATA[m][3]
    lines.append(f"  {m:11s} {de(lab(A), lab(B)).mean():5.2f} / {de(lab(toRGB(model(A, dS, dH, r.x))), lab(B)).mean():5.2f}")
x3 = np.load("out/spyder_xp3.npz"); v, Jxp3, T, base = x3["v"], x3["jpg"], x3["target"], x3["base"]
dS3, dH3 = (XP3[0] - CP0[0]).astype(float), (XP3[1] - CP0[1]).astype(float)
lines.append(f"  Portra xp3  {de(lab(base), lab(Jxp3)).mean():5.2f} / {de(lab(toRGB(model(base, dS3, dH3, r.x))), lab(Jxp3)).mean():5.2f}   (base = model of the first build)")

# ---- refit the 12 values with the recalibrated model ----
lin, w, kind = fl.samples(); vs = lin / 0.18 * fl.V_GRAY; bs = fs.cam(vs); tl = fs.tgt(lin)
hold = fs.hold; hb = fs.hb; hl = fs.hl; stl = lab(T)
# real fresh capture PB110252 (Portra xp3 live) is not a 'before' state, so the Spyder base stays the first-build model of PB110237
LS, LH = 40.0, 20.0
def apply(J, S, H): return toRGB(model(J, np.asarray(S, float) - CP0[0], np.asarray(H, float) - CP0[1], r.x))
def res2(q):
    S, H = q[:6], q[6:]
    return np.concatenate([np.sqrt(w) * de(lab(apply(bs, S, H)), tl), np.sqrt(20.0) * de(lab(apply(base, S, H)), stl), 0.15 * q])
q = least_squares(res2, np.concatenate(XP3).astype(float), bounds=([-LS] * 6 + [-LH] * 6, [LS] * 6 + [LH] * 6), x_scale=10.0, diff_step=0.05)
S4, H4 = np.round(q.x[:6]).astype(int), np.round(q.x[6:]).astype(int)
def rep(name, S, H):
    d = de(lab(apply(bs, S, H)), tl); dh = de(lab(apply(hb, S, H)), hl); ds = de(lab(apply(base, S, H)), stl)
    return (f"  {name:26s} gray {d[kind == 0].mean():5.2f} | ColorChecker {d[kind == 1].mean():5.2f} | hold-out {dh.mean():5.2f} (p95 {np.percentile(dh, 95):5.2f}) | "
            f"Spyder all {ds.mean():5.2f} colours {ds[:18].mean():5.2f} grays {ds[18:].mean():5.2f} worst {ds.max():5.2f}")
dm = de(lab(Jxp3), stl)
lines += ["", "Portra vs target with the recalibrated model (predictions):", rep("first build (zero)", CP0[0], CP0[1]), rep("xp3 values", *XP3),
          f"  {'xp3 MEASURED on camera':26s} {'':64s} Spyder all {dm.mean():5.2f} colours {dm[:18].mean():5.2f} grays {dm[18:].mean():5.2f} worst {dm.max():5.2f}",
          rep("refit (xp4)", S4, H4), f"  xp4 saturation (R G B Y C M): {S4.tolist()}   hue: {H4.tolist()}"]
b0 = open(fl.tone.BLOCK0, "rb").read(); Bb = fl.tone.BASE
op = lambda addr, vals: {"type": "bytes", "block": 0, "offset": hex(addr - Bb), "expect": b0[addr - Bb:addr - Bb + 12].hex(), "new": struct.pack("<6h", *[int(x) for x in vals]).hex()}
json.dump({"name": "sixaxis-portra-2", "description": "Cross Process I six-axis records refitted with the model recalibrated on the probe and xp3 camera results (fit_sixaxis2.py, NOTES §20). Apply on top of film-portra-xp.",
           "status": "built, NOT camera-tested", "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
           "base_sha256": "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", "ops": [op(0x7E7694FE, S4), op(0x7E76950A, H4)]}, open("../../patches/sixaxis-portra-2.json", "w"), indent=1)
np.save("out/sixaxis_model2.npy", r.x)
open("out/sixaxis2_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

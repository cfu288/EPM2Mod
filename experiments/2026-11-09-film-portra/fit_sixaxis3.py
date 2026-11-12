"""Where does the six-axis stage act, and with what maths? (NOTES §21)

Hypothesis from the research (other Olympus bodies; US 5,999,230): the stage sits next to the
colour matrix, before the base gamma, and works on RGB by rank order:
    primary component   p = max - mid   -> the axis of the largest channel (R, G or B)
    secondary component q = mid - min   -> Y, C or M (the two largest channels)
    out = in + p * (S_P a_P + H_P b_P) + q * (S_Q a_Q + H_Q b_Q)     a, b: unknown RGB 3-vectors
All four before/after pairs are RAW Data Edits of PB090221, so the true pre-stage signal is known
from the raw (v). 'Before' and 'after' JPEGs are pulled back through the modelled later stages
(saturation, luma look curve, base gamma) into the candidate domain, and the 36 unknowns are
solved by linear least squares. Score = ΔE2000 of the predicted 'after' JPEG, leave-one-pair-out.
Domains: lin = linear RGB after the colour matrix; gam = after the base gamma; out = the previous
model (CbCr sectors on the output, fit_sixaxis2).      ../../.venv/bin/python -I fit_sixaxis3.py
"""
import sys, importlib.util, io, contextlib
import numpy as np
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    sp = importlib.util.spec_from_file_location("f2", "fit_sixaxis2.py"); f2 = importlib.util.module_from_spec(sp); sp.loader.exec_module(f2)
fs, fl = f2.fs, f2.fl; tone = fl.tone; lab, de = fl.srgb_to_lab, fl.de2000
d, st, meta = tone.load(); names = [str(n) for n in d["names"]]; k0 = names.index("PB090221")
V = tone.precurve(d, st, k0)[:216]; rawok = ((~d["rawclip"][k0]) & (~tone.BAD[k0]))[:216]
K, X, BASE = 0.0621, np.arange(256), fl.table(0x7E74E9BC); LUMA = np.array([.299, .587, .114]); N1 = np.arange(1024)
GP = np.load("out/fit_crossprocess_G.npy")
ident = fl.table(fl.IDENTITY)
# per pair: (before file, after file, dS, dH, per-channel curve on base output (3x1024), luma look (256), saturation)
IDG = np.tile(N1.astype(float), (3, 1))
CFG = {"Vivid": (IDG, ident, 1.078 * 310 / 282), "Muted": (IDG, fl.table(0x7E75D0F0), 1.078), "Portrait": (IDG, fl.table(0x7E75DAF0), 1.078),
       "Portra xp3": (GP, ident, 0.937)}
SLOT = {"R": 0, "G": 1, "B": 2, "Y": 3, "C": 4, "M": 5}

def down(lin, cfg, start="lin"):
    """lin (or post-gamma 0..1023 if start='gam') -> 8-bit JPEG RGB."""
    G, look, sat = cfg
    g = np.interp(K * np.maximum(lin, 0), X, BASE) if start == "lin" else lin
    b = np.stack([np.interp(g[:, i], N1, G[i]) for i in range(3)], 1) / 4.0
    y = b @ LUMA; yl = np.interp(y, X, look) / 4.0 if look is not ident else y
    return yl[:, None] + sat * (b - y[:, None])

def up(J, cfg, to="lin"):
    """8-bit JPEG RGB -> post-gamma (0..1023) or linear, inverting the later stages."""
    G, look, sat = cfg
    yo = J @ LUMA
    y = yo if look is ident else np.interp(yo * 4.0, look, X.astype(float))
    b = y[:, None] + (J - yo[:, None]) / sat
    g = np.stack([np.interp(b[:, i] * 4.0, G[i], N1) for i in range(3)], 1)
    if to == "gam": return g
    return np.stack([np.interp(g[:, i], BASE, X.astype(float)) for i in range(3)], 1) / K

def comps(x):
    """Rank-order components of RGB rows: weights (N,6) in slot order R G B Y C M."""
    o = np.argsort(-x, axis=1); mx, md, mn = np.take_along_axis(x, o, 1).T
    W = np.zeros((len(x), 6)); r = np.arange(len(x))
    W[r, o[:, 0]] = mx - md
    sec = {(0, 1): 3, (1, 0): 3, (1, 2): 4, (2, 1): 4, (0, 2): 5, (2, 0): 5}
    W[r, [sec[(a, b)] for a, b in zip(o[:, 0], o[:, 1])]] = md - mn
    return W

PAIR = {}
for m, (a, b, stv, prv) in f2.PAIRS.items():
    A, B = f2.patches(a)[:6].reshape(-1, 3), f2.patches(b)[:6].reshape(-1, 3)
    ok = rawok & (A.min(1) > 8) & (A.max(1) < 247) & (B.min(1) > 8) & (B.max(1) < 247)
    PAIR[m] = (A, B, ok, np.subtract(prv[0], stv[0]).astype(float), np.subtract(prv[1], stv[1]).astype(float))

def design(W, dS, dH):
    """Rows for unknown x = [a_k (3), b_k (3)] for k in 6 axes, per output channel: (N*3, 36)."""
    n = len(W); Amat = np.zeros((n, 3, 36))
    for k in range(6):
        for ch in range(3):
            Amat[:, ch, k * 6 + ch] = W[:, k] * dS[k]; Amat[:, ch, k * 6 + 3 + ch] = W[:, k] * dH[k]
    return Amat.reshape(n * 3, 36)

def run(domain, holdout=None):
    rows, rhs = [], []
    for m, (A, B, ok, dS, dH) in PAIR.items():
        if m == holdout: continue
        cfg = CFG[m]; pre = V[ok] if domain == "lin" else np.interp(K * np.maximum(V[ok], 0), X, BASE)
        rows.append(design(comps(pre), dS, dH)); rhs.append((up(B[ok], cfg, domain) - up(A[ok], cfg, domain)).ravel())
    x = np.linalg.lstsq(np.concatenate(rows), np.concatenate(rhs), rcond=None)[0]
    out = {}
    for m, (A, B, ok, dS, dH) in PAIR.items():
        cfg = CFG[m]; pre = V[ok] if domain == "lin" else np.interp(K * np.maximum(V[ok], 0), X, BASE)
        delta = (design(comps(pre), dS, dH) @ x).reshape(-1, 3)
        pred = np.clip(down(up(A[ok], cfg, domain) + delta, cfg, domain), 0, 255)
        out[m] = de(lab(pred), lab(B[ok])).mean()
    return out, x

lines = ["ΔE2000, predicted vs real 'after' JPEG (216-colour chart, patches inside the 8-bit range):",
         f"  {'pair':11s}  no model | output-CbCr model (§20) | rank-order RGB, linear: fit / held out | rank-order RGB, post-gamma: fit / held out"]
full = {dom: run(dom) for dom in ("lin", "gam")}
for m, (A, B, ok, dS, dH) in PAIR.items():
    old = de(lab(f2.toRGB(f2.model(A[ok], dS, dH, f2.r.x))), lab(B[ok])).mean()
    ho = {dom: run(dom, holdout=m)[0][m] for dom in ("lin", "gam")}
    lines.append(f"  {m:11s}  {de(lab(A[ok]), lab(B[ok])).mean():7.2f}  | {old:10.2f}              | {full['lin'][0][m]:10.2f} / {ho['lin']:5.2f}                     | {full['gam'][0][m]:10.2f} / {ho['gam']:5.2f}   (n={ok.sum()})")
for dom in ("lin", "gam"):
    x = full[dom][1].reshape(6, 2, 3)
    lines.append(f"\n{dom}: per-unit direction vectors (RGB, x1000) for saturation | hue")
    for n, k in SLOT.items():
        lines.append(f"  {n}: sat {np.round(x[k, 0] * 1000, 1)}   hue {np.round(x[k, 1] * 1000, 1)}")
np.save("out/sixaxis_rank_lin.npy", full["lin"][1]); np.save("out/sixaxis_rank_gam.npy", full["gam"][1])
open("out/sixaxis3_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

"""Portra refit with the rank-order, pre-gamma six-axis model (fit_sixaxis3.py; NOTES §21).
Curves and saturation stay as flashed; the 12 record values are refitted.
   ../../.venv/bin/python -I fit_sixaxis4.py"""
import json, struct, sys, importlib.util, io, contextlib
import numpy as np
from scipy.optimize import least_squares
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    sp = importlib.util.spec_from_file_location("f3", "fit_sixaxis3.py"); f3 = importlib.util.module_from_spec(sp); sp.loader.exec_module(f3)
f2, fs, fl = f3.f2, f3.fs, f3.fl; lab, de = fl.srgb_to_lab, fl.de2000
Xv = np.load("out/sixaxis_rank_lin.npy").reshape(6, 2, 3); CFG = f3.CFG["Portra xp3"]; CP0 = np.array([0, 3, 0, 0, 0, 0.0])
def render(v, S, H):
    W = f3.comps(v); dS, dH = np.asarray(S, float) - CP0, np.asarray(H, float) - CP0
    delta = sum(W[:, k:k + 1] * (dS[k] * Xv[k, 0] + dH[k] * Xv[k, 1]) for k in range(6))
    return np.clip(f3.down(v + delta, CFG), 0, 255)
x3 = np.load("out/spyder_xp3.npz"); sv, Jxp3, T = x3["v"], x3["jpg"], x3["target"]; stl = lab(T)
XP3 = f2.XP3
lines = ["SpyderCheckr RAW PB110237 (not used to build the model), ΔE2000 camera xp3 vs model prediction:",
         f"  rank-order linear model: all {de(lab(render(sv, *XP3)), lab(Jxp3)).mean():.2f}, colours {de(lab(render(sv, *XP3)), lab(Jxp3))[:18].mean():.2f}"
         f"   (output-CbCr model: {de(lab(f2.apply(x3['base'], *XP3)), lab(Jxp3)).mean():.2f})"]
lin, w, kind = fl.samples(); vs = lin / 0.18 * fl.V_GRAY; tl = fs.tgt(lin); hold = fs.hold; hv = hold / 0.18 * fl.V_GRAY; hl = fs.hl
def rep(name, S, H):
    d = de(lab(render(vs, S, H)), tl); dh = de(lab(render(hv, S, H)), hl); ds = de(lab(render(sv, S, H)), stl)
    return (f"  {name:24s} gray {d[kind == 0].mean():5.2f} | ColorChecker {d[kind == 1].mean():5.2f} | hold-out {dh.mean():5.2f} (p95 {np.percentile(dh, 95):5.2f}) | "
            f"Spyder all {ds.mean():5.2f} colours {ds[:18].mean():5.2f} grays {ds[18:].mean():5.2f} worst {ds.max():5.2f}")
def res(q, lim):
    S, H = q[:6], q[6:]
    return np.concatenate([np.sqrt(w) * de(lab(render(vs, S, H)), tl), np.sqrt(20.0) * de(lab(render(sv, S, H)), stl), 0.1 * q])
out = {}
for tag, (LS, LH) in (("probe range ±40/±20", (40, 20)), ("wider ±64/±32", (64, 32))):
    q = least_squares(res, np.concatenate(XP3).astype(float), args=(None,), bounds=([-LS] * 6 + [-LH] * 6, [LS] * 6 + [LH] * 6), x_scale=10.0, diff_step=0.05)
    out[tag] = (np.round(q.x[:6]).astype(int), np.round(q.x[6:]).astype(int))
dm = de(lab(Jxp3), stl)
lines += ["", "Portra vs target, predictions with the rank-order model (slots R G B Y C M):", rep("first build (0,3,0,0,0,0)", CP0, CP0), rep("xp3 values", *XP3),
          f"  {'xp3 MEASURED':24s} {'':66s} Spyder all {dm.mean():5.2f} colours {dm[:18].mean():5.2f} grays {dm[18:].mean():5.2f} worst {dm.max():5.2f}"]
for tag, (S, H) in out.items():
    lines += [rep("refit, " + tag.split()[0] + " " + tag.split()[1], S, H), f"      sat {S.tolist()}  hue {H.tolist()}"]
S5, H5 = out["probe range ±40/±20"]
names = "D1 D2 D3 D4 D5 D6 C1 C2 C3 C4 C5 C6 B1 B2 B3 B4 B5 B6 A1 A2 A3 A4 A5 A6".split()
dn = de(lab(render(sv, S5, H5)), stl)
lines.append("  Spyder per patch, measured xp3 -> predicted refit: " + ", ".join(f"{n} {a:.1f}->{b:.1f}" for n, a, b in zip(names, dm, dn) if a > 2.5 or b > 2.5))
b0 = open(fl.tone.BLOCK0, "rb").read(); Bb = fl.tone.BASE
op = lambda addr, vals: {"type": "bytes", "block": 0, "offset": hex(addr - Bb), "expect": b0[addr - Bb:addr - Bb + 12].hex(), "new": struct.pack("<6h", *[int(x) for x in vals]).hex()}
json.dump({"name": "sixaxis-portra-3", "description": "Cross Process I six-axis records refitted with the rank-order pre-gamma model (fit_sixaxis3/4.py, NOTES §21), values inside the probed range. Apply on top of film-portra-xp.",
           "status": "built, NOT camera-tested", "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "base_sha256": "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300",
           "ops": [op(0x7E7694FE, S5), op(0x7E76950A, H5)]}, open("../../patches/sixaxis-portra-3.json", "w"), indent=1)
open("out/sixaxis4_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

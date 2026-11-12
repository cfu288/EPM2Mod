"""Portra with the pre-gamma art matrix (0x7E56C603 slot of Pop Art I, table 0x7E768F46), NOTES §22.
Assumption (unverified, the flash tests it): total = ColorMatrix x A, so A acts on the white-balanced
camera RGB; in linear sRGB terms that is E = M A M^-1 with the shot's own ColorMatrix M.
Joint fit of A (rows sum to 1), three curves, saturation and the 12 six-axis values.
   ../../.venv/bin/python -I fit_matrix.py"""
import json, struct, subprocess, sys, importlib.util, io, contextlib
import numpy as np
from scipy.optimize import least_squares
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    sp = importlib.util.spec_from_file_location("fj", "fit_joint.py"); fj = importlib.util.module_from_spec(sp); sp.loader.exec_module(fj)
f4, f3, f2, fs, fl = fj.f4, fj.f3, fj.f2, fj.fs, fj.fl; lab, de = fl.srgb_to_lab, fl.de2000; KN, CP0 = fj.KN, fj.CP0
MD = np.array([418, -140, -22, -56, 360, -48, 14, -132, 374]).reshape(3, 3) / 256.0            # 5300K ColorMatrix
e = json.loads(subprocess.run(["exiftool", "-j", "-n", "-ColorMatrix", "shots/PB110237.ORF"], capture_output=True, text=True).stdout)[0]
MS = np.array([float(x) for x in str(e["ColorMatrix"]).split()]).reshape(3, 3) / 256.0         # the Spyder shot's (Auto WB, lamp)
def A_of(o):
    o = o.reshape(3, 2); return np.array([[1 - o[0].sum(), o[0, 0], o[0, 1]], [o[1, 0], 1 - o[1].sum(), o[1, 1]], [o[2, 0], o[2, 1], 1 - o[2].sum()]])
def quant(A):                                  # as stored: s16 x256, rows summing to 256
    Q = np.round(A * 256).astype(int)
    for i in range(3): Q[i, i] += 256 - Q[i].sum()
    return Q
def unpack(p):
    G = fj.curves(p); return G, p[3 * KN], p[3 * KN + 1:3 * KN + 7], p[3 * KN + 7:3 * KN + 13], A_of(p[3 * KN + 13:3 * KN + 19])
def eff(A, M): return M @ A @ np.linalg.inv(M)
def res(p):
    G, sat, S, H, A = unpack(p)
    return np.concatenate([np.sqrt(fj.w) * de(lab(fj.render(fj.vs, G, sat, S, H, eff(A, MD))), fj.tl), np.sqrt(20.0) * de(lab(fj.render(fj.sv, G, sat, S, H, eff(A, MS))), fj.stl),
                           0.05 * np.diff(G[:, ::32], 2, axis=1).ravel(), 0.1 * p[3 * KN + 1:3 * KN + 13], 20 * p[3 * KN + 13:]])
p0 = np.concatenate([fj.knots_of(fj.GP), [0.937], f4.S5.astype(float), f4.H5.astype(float), np.zeros(6)])
lo = np.concatenate([np.zeros(3 * KN), [0.6], [-40] * 6, [-20] * 6, [-0.5] * 6]); hi = np.concatenate([np.full(3 * KN, 40.0), [1.4], [40] * 6, [20] * 6, [0.5] * 6])
r = least_squares(res, np.clip(p0, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), x_scale="jac", max_nfev=200)
G, sat, S, H, A = unpack(r.x); S, H = np.round(S), np.round(H); Q = quant(A); Aq = Q / 256.0
gain = int(round(282 * sat / 1.078))
def rep(name, A_, hyp):
    Ed, Es = (eff(A_, MD), eff(A_, MS)) if hyp == "camera" else (A_, A_)
    d = de(lab(fj.render(fj.vs, G, sat, S, H, Ed)), fj.tl); dh = de(lab(fj.render(fj.hv, G, sat, S, H, Ed)), fj.hl); ds = de(lab(fj.render(fj.sv, G, sat, S, H, Es)), fj.stl)
    return (f"  {name:44s} gray {d[fj.kind == 0].mean():5.2f} | ColorChecker {d[fj.kind == 1].mean():5.2f} | hold-out {dh.mean():5.2f} (p95 {np.percentile(dh, 95):5.2f}) | "
            f"Spyder all {ds.mean():5.2f} colours {ds[:18].mean():5.2f} grays {ds[18:].mean():5.2f} worst {ds.max():5.2f}")
lines = ["Portra with the art matrix, predicted ΔE2000 vs target:", rep("as intended (A on camera RGB)", Aq, "camera"), rep("if A instead acts after the colour matrix", Aq, "srgb"),
         rep("if the matrix is not applied at all", np.eye(3), "srgb"),
         f"  A x256 = {Q.tolist()}   saturation {sat:.3f} -> gain {gain}   S {S.astype(int).tolist()}  H {H.astype(int).tolist()}"]
np.savez("out/fit_matrix.npz", G=G, sat=sat, S=S, H=H, A=Aq, Es=eff(Aq, MS), Ed=eff(Aq, MD))
np.save("out/spyder_pred_xp7.npy", np.stack([fj.render(fj.sv, G, sat, S, H, eff(Aq, MS)), fj.render(fj.sv, G, sat, S, H, Aq), fj.render(fj.sv, G, sat, S, H, None)]))
# ---- patch specs ----
b0 = open(fl.tone.BLOCK0, "rb").read(); B = fl.tone.BASE
def op(addr, new): return {"type": "bytes", "block": 0, "offset": hex(addr - B), "expect": b0[addr - B:addr - B + len(new)].hex(), "new": new.hex()}
base = {"status": "built, NOT camera-tested", "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "base_sha256": "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300"}
json.dump({"name": "xp-adaptive-hue-off", "description": "Code immediates only: in 0x7E5460F0 the tests 'dominant bin is B (2)' and 'is C (4)' become comparisons with 0x7F / 0x7E, so the "
           "scene-adaptive hue of Cross Process I and II is never added (CODE_DIG §2). The ROM hue record is still copied.", **base,
           "ops": [op(0x7E546161, b"\x7f"), op(0x7E546167, b"\x7e")]}, open("../../patches/xp-adaptive-hue-off.json", "w"), indent=1)
ops = [o for o in fl.xp_ops(G, gain) ] + [op(0x7E7694FE, struct.pack("<6h", *S.astype(int))), op(0x7E76950A, struct.pack("<6h", *H.astype(int))),
       op(0x7E768F46, struct.pack("<9h", *Q.ravel())), op(0x7E56C6A6, b"\x55"), op(0x7E56C6AA, b"\x57")]
json.dump({"name": "film-portra-xp7", "description": "Portra 400 in the Cross Process I slot with the pre-gamma art matrix: base gammas, look curve, saturation gain, six-axis records, "
           "matrix table 0x7E768F46, and two code immediates in 0x7E56C603 (cmp 70 -> 85, cmp 79 -> 87) that give Pop Art I's matrix slot to Cross Process I (Pop Art I loses its matrix). NOTES §22.", **base, "ops": ops},
          open("../../patches/film-portra-xp7.json", "w"), indent=1)
open("out/matrix_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

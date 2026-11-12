"""Six-axis stage: forward model from sixaxis-probe-1, check, and a Portra refit of the 12 values.

Stage (acts on the output YCbCr, BT.601): a colour's (Cb, Cr) is split onto the two neighbouring
axes of {M 52, R 109, Y 171, G 232, C 289, B 351 deg}; axis i is scaled by (1 + A_i S_i), turned by
B_i H_i degrees, and adds luma L_i per unit of its component. Record slot order: R, G, B, Y, C, M.
Units are single-point estimates from the probe (NOTES §18): provisional.
   ../../.venv/bin/python -I fit_sixaxis.py
"""
import json, struct, sys, importlib.util, os
import numpy as np
from scipy.optimize import least_squares
sys.argv = ["x"]
sp = importlib.util.spec_from_file_location("fl", "fit_look.py"); fl = importlib.util.module_from_spec(sp); sp.loader.exec_module(fl)
ns = {}; exec(open("analyze_probe6.py").read().split("out = {}")[0], ns); patches = ns["patches"]

SLOTS = "R G B Y C M".split()
ANG = {"M": 52.0, "R": 109.0, "Y": 171.0, "G": 232.0, "C": 289.0, "B": 351.0}
ORDER = sorted(ANG, key=ANG.get)                                   # by angle
A0 = np.array([ANG[k] for k in ORDER]); U = np.stack([np.cos(np.radians(A0)), np.sin(np.radians(A0))], 1)
IDX = [SLOTS.index(k) for k in ORDER]                              # axis (angle order) -> record slot
#        per unit:   chroma gain,  degrees,  luma per S,  luma per H        (probe estimates)
UNIT = {"R": (0.0059, -1.21, 0.0, -0.012), "G": (0.0022, -1.27, 0.002, 0.004), "B": (0.0030, -1.41, 0.0, 0.009),
        "Y": (0.0037, -0.40, 0.0068, 0.0), "C": (0.0007, -0.31, 0.0052, 0.0), "M": (0.0042, -0.33, 0.0038, 0.0)}

def ycc(x):
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    return 0.299 * r + 0.587 * g + 0.114 * b, -0.168736 * r - 0.331264 * g + 0.5 * b, 0.5 * r - 0.418688 * g - 0.081312 * b

def rgb(y, cb, cr):
    return np.stack([y + 1.402 * cr, y - 0.344136 * cb - 0.714136 * cr, y + 1.772 * cb], -1)

def weights(cb, cr):
    t = np.degrees(np.arctan2(cr, cb)) % 360; W = np.zeros((len(t), 6)); tt = np.where(t < A0[0], t + 360, t)
    for k in range(6):
        a0, a1 = A0[k], A0[(k + 1) % 6] + (360 if k == 5 else 0); m = (tt >= a0) & (tt < a1)
        ab = np.linalg.solve(np.stack([U[k], U[(k + 1) % 6]], 1), np.stack([cb[m], cr[m]]))
        W[m, k] += ab[0]; W[m, (k + 1) % 6] += ab[1]
    return W

def sixaxis(J, S, H):
    """J: (N,3) 8-bit RGB after the rest of the pipeline; S, H: six values each in record slot order."""
    y, cb, cr = ycc(J); W = weights(cb, cr); out = np.zeros((len(J), 3))
    for k, name in enumerate(ORDER):
        a, b, ls, lh = UNIT[name]; s, h = S[IDX[k]], H[IDX[k]]
        ang = np.radians(A0[k] + b * h); g = 1 + a * s
        out[:, 1] += W[:, k] * g * np.cos(ang); out[:, 2] += W[:, k] * g * np.sin(ang); out[:, 0] += W[:, k] * (ls * s + lh * h)
    return np.clip(rgb(y + out[:, 0], out[:, 1], out[:, 2]), 0, 255)

lab, de = fl.srgb_to_lab, fl.de2000
# ---- 1. in-sample check on the probe (after predicted from before with the record deltas) ----
STOCK = {"Vivid": ((18, 4, 24, 0, 8, 8), (0, 2, 4, -1, -6, 0)), "Muted": ((-22, 4, -16, 0, 4, -8), (3, 0, -3, 7, 8, 10)), "Portrait": ((14, 0, 0, 5, 0, 0), (-1, 0, 2, -2, 0, 0))}
PROBE = {"Vivid": ((40, 0, 0, -40, 0, 0), (0, 20, 0, 0, -20, 0)), "Muted": ((0, 40, 0, 0, -40, 0), (0, 0, 20, 0, 0, -20)), "Portrait": ((0, 0, 40, 0, 0, -40), (20, 0, 0, -20, 0, 0))}
FILES = {"Vivid": ("PB090238", "PB090244"), "Muted": ("PB090239", "PB090245"), "Portrait": ("PB090240", "PB090246")}
lines = ["Probe check (monitor chart, ΔE2000 between predicted and real 'after'; 'no model' = before vs after):"]
for m, (a, b) in FILES.items():
    A, B = patches(a)[:6].reshape(-1, 3), patches(b)[:6].reshape(-1, 3)
    ok = (A.min(1) > 6) & (A.max(1) < 249) & (B.min(1) > 6) & (B.max(1) < 249)
    P = sixaxis(A[ok], np.subtract(PROBE[m][0], STOCK[m][0]), np.subtract(PROBE[m][1], STOCK[m][1]))
    lines.append(f"  {m:9s} no model {de(lab(A[ok]), lab(B[ok])).mean():5.2f}   model {de(lab(P), lab(B[ok])).mean():5.2f}  (n={ok.sum()})")

# ---- 2. Portra refit: curves and saturation stay as flashed; fit only the 12 values ----
cube, size = fl.load_cube("out/lut/spektrafilm_v034_portra400_portraendura_1lut_vlog_srgb/lut_v034_portra400_portraendura.cube")
GP = np.load("out/fit_crossprocess_G.npy"); SAT = 0.937
K, X, BASE = 0.0621, np.arange(256), fl.table(0x7E74E9BC)
def cam(v):
    b = np.interp(K * np.maximum(v, 0), X, BASE); c = np.stack([np.interp(b[:, i], np.arange(1024), GP[i]) for i in range(3)], 1) / 4
    y = c @ np.array([.299, .587, .114]); return np.clip(y[:, None] + SAT * (c - y[:, None]), 0, 255)
tgt = lambda lin: lab(np.clip(fl.apply_cube(cube, size, fl.encode(lin, "vlog")), 0, 1) * 255)
lin, w, kind = fl.samples(); v = lin / 0.18 * fl.V_GRAY; base = cam(v); tl = tgt(lin)
sp_ = np.load("out/spyder_patches.npz"); sv, sj, sok = sp_["PB110236_v"], sp_["PB110236_jpg"], sp_["PB110236_ok"]; stl = tgt(sv / fl.V_GRAY * 0.18)
hold = fl.natural(3000, 2); hold = hold[hold.max(1) <= 0.18 * 2 ** 2.6]; hb = cam(hold / 0.18 * fl.V_GRAY); hl = tgt(hold)
LIM_S, LIM_H = 40.0, 20.0
def resid(p):
    S, H = p[:6], p[6:]
    r = [np.sqrt(w) * de(lab(sixaxis(base, S, H)), tl), np.sqrt(20.0) * de(lab(sixaxis(sj, S, H)), stl), 0.15 * p]   # Spyder: real camera output as the base
    return np.concatenate(r)
r = least_squares(resid, np.zeros(12), bounds=([-LIM_S] * 6 + [-LIM_H] * 6, [LIM_S] * 6 + [LIM_H] * 6), x_scale=10.0, diff_step=0.05)
S, H = np.round(r.x[:6]).astype(int), np.round(r.x[6:]).astype(int)
z = np.zeros(6)
def rep(name, Sx, Hx):
    d = de(lab(sixaxis(base, Sx, Hx)), tl); dh = de(lab(sixaxis(hb, Sx, Hx)), hl); ds = de(lab(sixaxis(sj, Sx, Hx)), stl)
    return (f"  {name:28s} gray {d[kind == 0].mean():5.2f} | ColorChecker ±2 EV {d[kind == 1].mean():5.2f} | hold-out {dh.mean():5.2f} (p95 {np.percentile(dh, 95):5.2f})"
            f" | Spyder (real shot 0236) all {ds.mean():5.2f}, colours {ds[:18].mean():5.2f}, worst {ds.max():5.2f}")
lines += ["", "Portra, Cross Process I slot, ΔE2000 vs target (curves and saturation as flashed):", rep("as flashed (all zero)", z, z), rep(f"fitted six-axis values", S, H),
          f"  saturation slots (R G B Y C M): {S.tolist()}   hue slots: {H.tolist()}   (limits ±{LIM_S:.0f} / ±{LIM_H:.0f}, the range the probe exercised)"]
ds0, ds1 = de(lab(sj), stl), de(lab(sixaxis(sj, S, H)), stl)
names = "D1 D2 D3 D4 D5 D6 C1 C2 C3 C4 C5 C6 B1 B2 B3 B4 B5 B6 A1 A2 A3 A4 A5 A6".split()
lines.append("  Spyder patches, ΔE now -> predicted: " + ", ".join(f"{n} {a:.1f}->{b:.1f}" for n, a, b in zip(names, ds0, ds1) if a > 5 or b > 5))

# ---- 3. patch spec: Cross Process I's own records (sat 0x7E7694FE, hue 0x7E76950A) ----
b0 = open(fl.tone.BLOCK0, "rb").read(); B = fl.tone.BASE
def op(addr, vals):
    old = b0[addr - B:addr - B + 12]
    return {"type": "bytes", "block": 0, "offset": hex(addr - B), "expect": old.hex(), "new": struct.pack("<6h", *[int(x) for x in vals]).hex()}
spec = {"name": "sixaxis-portra-1", "description": "Cross Process I six-axis records (saturation 0x7E7694FE, hue 0x7E76950A; slot order R G B Y C M) set to values fitted "
        "to the Portra target with the provisional model from sixaxis-probe-1 (fit_sixaxis.py, NOTES §18). Apply on top of film-portra-xp.",
        "status": "built, NOT camera-tested", "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
        "base_sha256": "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", "ops": [op(0x7E7694FE, S), op(0x7E76950A, H)]}
json.dump(spec, open("../../patches/sixaxis-portra-1.json", "w"), indent=1)
np.save("out/sixaxis_portra_values.npy", np.concatenate([S, H]))
open("out/sixaxis_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

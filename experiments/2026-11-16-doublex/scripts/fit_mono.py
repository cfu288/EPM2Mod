"""Fit a black-and-white film to the Grainy Film entry: the grey mix (art matrix) and one tone curve.

   .venv/bin/python -I experiments/2026-11-16-doublex/scripts/fit_mono.py --name doublex
   ... --name doublex2 --transfer 2 --matrix-from looks/fits/doublex.npz

Target: monolib.target (spektrafilm dev, Double-X on 2302, neutral). Samples and weights: those of the colour fits
(fit_film2.py: reading A_natural of the test RAW; grays 150, ColorChecker 20, skin 60, natural 1, skin series 20,
near-neutrals 4, dense grays 20, gamut edge 0.25). The error is dE2000 between neutral greys (a function of L* only).
Output: out/fit_mono-NAME.npz and out/mono-NAME_report.txt in the film experiment's out/ folder (not in git).
"""
import argparse, sys
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import monolib as m
from monolib import f

ap = argparse.ArgumentParser(); ap.add_argument("--name", required=True)
ap.add_argument("--transfer", choices=("1", "2"), default="1", help="which measurement of g: results/grain-transfer.json or grain-transfer-2.json"); ap.add_argument("--matrix-from", help="a fit file (path from the repository root) whose matrix is kept; only the tone is fitted")
ap.add_argument("--edge-weight", type=float, default=0.25); ap.add_argument("--bound", type=float, default=64.0, help="limit of a matrix off-diagonal, x128")
a = ap.parse_args()
if a.transfer == "2": m.use_transfer(m.TRANSFER_2)
A = m.load("A_natural"); k = A["kind"]; NK = 25
wa = np.where(A["weight"] > 0, A["weight"], np.where(k == 8, 20.0, np.where(k == 3, 4.0, np.where(k == 2, 20.0, np.where(k == 10, a.edge_weight, 0.0)))))
allok = np.isfinite(A["u"][:, 0]); sel = allok & (wa > 0); u, ws = A["u"][sel], wa[sel]
tall = m.target(A["vs"]); tl = m.grey_lab(tall[sel])

def res(p, fixed=None):
    if fixed is not None: p = np.concatenate([p, fixed])
    D, P = m.tone_of_knots(p[:NK]), f.P_of(p[NK:NK + 6]); out = np.interp(m.y_in(u, P), m.X, D)
    return np.concatenate([np.sqrt(ws) * m.de(m.grey_lab(out), tl), 0.05 * np.diff(D[::8], 2), 0.02 * (p[NK:] - f.off(np.round(m.M5300 * 128)))])
lo = np.concatenate([np.zeros(NK), [-a.bound] * 6]); hi = np.concatenate([np.full(NK, 16.0), [a.bound] * 6])
def mix(b): return np.array([[1 - b, 0, b], [0, 1 - b, b], [0, 0, 1.0]]) @ m.M5300
q0 = np.sqrt(np.full(NK, 255.0 / NK))
best = None
if a.matrix_from:
    z = np.load(m.RESULTS.parents[2] / a.matrix_from); best = type("r", (), {"x": np.concatenate([q0, f.off(z["P"] * 128)])}); At0 = z["A"]
for name, P0 in ({} if a.matrix_from else {"camera matrix": m.M5300, "blue 0.25": mix(0.25), "blue 0.5": mix(0.5)}).items():
    p0 = np.concatenate([q0, np.clip(f.off(P0 * 128), -a.bound + 1, a.bound - 1)])
    r = least_squares(res, np.clip(p0, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), x_scale="jac", max_nfev=400, loss="soft_l1", f_scale=3.0)
    print(f"  start {name}: cost {r.cost:.1f}", flush=True)
    if best is None or r.cost < best.cost: best = r
At = At0 if a.matrix_from else f.find_A(f.P_of(best.x[NK:])); Pq = f.renormalise(At) / 128.0
r2 = least_squares(lambda q: res(q, f.off(Pq * 128)), best.x[:NK], bounds=(lo[:NK], hi[:NK]), x_scale="jac", max_nfev=200, loss="soft_l1", f_scale=3.0)
D = m.tone_of_knots(r2.x); T = m.grain_table(D); L = np.clip(np.round(4 * D), 0, 1023)
yin = m.y_in(A["u"], Pq); out = m.film(A["u"], Pq, D)
rows = {"this fit": out, "stock Grainy Film": m.final(A["u"], m.M5300), "stock Monotone": m.monotone(A["u"], m.M5300)}
lines = [f"Target {m.LUT.rsplit('/', 1)[1]} (input gain {m.target_gain():.4f} undone); model only",
         "Mean |dL*| / mean dE2000 against the target, per patch set (" + ", ".join(n for _, n in m.SETS) + "):"]
for tag, y in rows.items():
    s = m.score(y, tall, k, allok); lines.append(f"  {tag:18s} " + "  ".join(f"{s[n][0]:.2f}/{s[n][1]:.2f}" for _, n in m.SETS))
wsel = allok & (wa > 0); dd = m.de(m.grey_lab(out), m.grey_lab(tall))
inside = (yin[wsel] >= m.MEASURED_RANGE[0]) & (yin[wsel] <= m.MEASURED_RANGE[1])
slope = lambda t: np.gradient(t / 4.0)
mid = (T / 4.0 > 40) & (T / 4.0 < 215); mids = (m.T_STOCK / 4.0 > 40) & (m.T_STOCK / 4.0 < 215)
lines += [f"  weighted dE2000 of the fit {np.average(dd[wsel], weights=wa[wsel]):.3f}; natural p95 {np.percentile(dd[allok & (k == 5)], 95):.2f}",
          f"  art table x256 {At.tolist()}; camera matrix (EXIF, 5300 K) {(f.renormalise(At) * 2).tolist()}; stock {np.round(m.M5300 * 256).astype(int).tolist()}",
          f"  grey mix: weights of scene R, G, B (linear sRGB) in the luma, for a mid grey {(m.LUMA @ Pq @ np.linalg.inv(m.M5300)).round(3).tolist()}; stock {(m.LUMA).tolist()}",
          f"  Y_in of the samples: {yin[wsel].min():.0f} to {yin[wsel].max():.0f}; inside the measured range of g ({m.MEASURED_RANGE[0]:.0f} to {m.MEASURED_RANGE[1]:.0f}): {100 * inside.mean():.1f} %",
          f"  tone D at Y_in 0, 32, ... 255: {D[::32].round(0).astype(int).tolist()} {int(round(D[255]))}",
          f"  grain table slope between picture values 40 and 215: mean {slope(T)[mid].mean():.2f}, max {slope(T)[mid].max():.2f} (stock table: mean {slope(m.T_STOCK)[mids].mean():.2f}, max {slope(m.T_STOCK)[mids].max():.2f});"
          f" predicted spread inside a mid-grey patch {m.SIGMA_X * slope(T)[mid].mean():.0f} codes (stock, measured: up to 52)",
          f"  target: 18 % grey -> {m.target(np.full((1, 3), m.fl.V_GRAY))[0]:.1f}; fit {m.film(np.linalg.solve(m.M5300, np.full(3, m.fl.V_GRAY))[None], Pq, D)[0]:.1f}"]
np.savez(f"out/fit_mono-{a.name}.npz", A=At, P=Pq, D=D, T=T.astype(np.int64), L=L.astype(np.int64), lut=m.LUT, model="model2-mono")
open(f"out/mono-{a.name}_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

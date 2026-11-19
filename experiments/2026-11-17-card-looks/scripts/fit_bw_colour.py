"""Fit a black-and-white film as a normal colour look, for a slot like any other (no grain program).

    .venv/bin/python -I experiments/2026-11-17-card-looks/scripts/fit_bw_colour.py --name doublex3

The look: saturation gain 0 (Cb = Cr = 128: the chroma curves keep 128, every colour fit does), six-axis 0, the
art matrix sets how colours become grey, and one rising tone curve c for all three channels. Model (model2.pre with
sat 0, the identity look table of the film slots):

    grey = IDENT(luma(c(BASE(K u P^T)) / 4))

Target, samples and weights: those of the Double-X fit (experiments/2026-11-16-doublex/scripts/fit_mono.py).
Output: data/films/fits/NAME.npz in the colour fit layout (G, gain, S, H, A, P, Cb, Cr, slopes), and a report.
"""
import argparse, os, sys
import numpy as np
from scipy.optimize import least_squares

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments", "2026-11-16-doublex", "scripts"))
import monolib as m  # noqa: E402  (changes the working directory to the film experiment)
from monolib import f  # noqa: E402
import chroma as C  # noqa: E402
import model2 as M2  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--name", required=True)
ap.add_argument("--matrix-from", default="data/films/fits/doublex2.npz", help="start matrix (fit file, repository path)")
a = ap.parse_args()

A = m.load("A_natural"); k = A["kind"]; NK = 25
wa = np.where(A["weight"] > 0, A["weight"], np.where(k == 8, 20.0, np.where(k == 3, 4.0, np.where(k == 2, 20.0, np.where(k == 10, 0.25, 0.0)))))
allok = np.isfinite(A["u"][:, 0]); sel = allok & (wa > 0); u, ws = A["u"][sel], wa[sel]
tall = m.target(A["vs"]); tl = m.grey_lab(tall[sel])
kx = np.linspace(0, 1023, NK + 1)


def curve(q):
    """A rising 10-bit tone curve over the 1,024 base-gamma values, from NK segment heights (square roots)."""
    y = np.concatenate([[0.0], np.minimum(np.cumsum(np.asarray(q) ** 2), 1023.0)])
    return np.interp(m.N1, kx, y)


def grey(uu, P, c):
    """The picture value of the look (0..255)."""
    return M2.pre(M2.six(uu, m.ZERO6, m.ZERO6, P), np.tile(c, (3, 1)), 0.0)[:, 1]


def res(p, fixed=None):
    if fixed is not None: p = np.concatenate([p, fixed])
    c, P = curve(p[:NK]), f.P_of(p[NK:NK + 6])
    return np.concatenate([np.sqrt(ws) * m.de(m.grey_lab(grey(u, P, c)), tl), 0.05 * np.diff(c[::32], 2) / 4.0])


z = np.load(os.path.join(ROOT, a.matrix_from))
P0 = z["P"]
q0 = np.sqrt(np.full(NK, 1023.0 / NK))
lo = np.concatenate([np.zeros(NK), [-64.0] * 6]); hi = np.concatenate([np.full(NK, 40.0), [64.0] * 6])
r = least_squares(res, np.clip(np.concatenate([q0, f.off(P0 * 128)]), lo + 1e-6, hi - 1e-6), bounds=(lo, hi),
                  x_scale="jac", max_nfev=600, loss="soft_l1", f_scale=3.0)
At = f.find_A(f.P_of(r.x[NK:])); Pq = f.renormalise(At) / 128.0      # the matrix the camera loads from the integer table
r2 = least_squares(lambda q: res(q, f.off(Pq * 128)), r.x[:NK], bounds=(lo[:NK], hi[:NK]), x_scale="jac", max_nfev=300,
                   loss="soft_l1", f_scale=3.0)
c = np.clip(np.round(np.maximum.accumulate(curve(r2.x))), 0, 1023)
G = np.tile(c, (3, 1))
out = grey(A["u"], Pq, c)
x, y, s = C.quantise(C.LINEAR_Y)
rows = {"this fit (colour slot)": out, "Double-X in Grainy Film": m.film(A["u"], z["P"], z["D"]),
        "stock Monotone": m.monotone(A["u"], m.M5300)}
lines = [f"Double-X as a colour look, target {m.LUT.rsplit('/', 1)[1]}; model only",
         "Mean |dL*| / mean dE2000 against the target, per patch set (" + ", ".join(n for _, n in m.SETS) + "):"]
for tag, yv in rows.items():
    sc = m.score(yv, tall, k, allok); lines.append(f"  {tag:24s} " + "  ".join(f"{sc[n][0]:.2f}/{sc[n][1]:.2f}" for _, n in m.SETS))
lines += [f"  art table x256 {At.tolist()} (rows {At.sum(1).tolist()})",
          f"  grey weights of scene R, G, B: {(m.LUMA @ Pq @ np.linalg.inv(m.M5300)).round(3).tolist()}",
          f"  curve at base 0, 128, ... 1023: {c[::128].astype(int).tolist()} {int(c[1023])}; largest step {int(np.diff(c).max())}",
          f"  18 % grey: target {m.target(np.full((1, 3), m.fl.V_GRAY))[0]:.1f}, fit {grey(np.linalg.solve(m.M5300, np.full(3, m.fl.V_GRAY))[None], Pq, c)[0]:.1f}"]
np.savez(os.path.join(ROOT, "data", "films", "fits", a.name + ".npz"), G=G, gain=np.int64(0), sat=np.float64(0.0), S=np.zeros(6),
         H=np.zeros(6), A=At.astype(np.int64), P=Pq, lut=m.LUT, Cb=np.stack([x, y, s[:16]]), Cr=np.stack([x, y, s[:16]]),
         Cb_slope17=s, Cr_slope17=s, model="model2-bw-colour")
rep = os.path.join(ROOT, "experiments", "2026-11-17-card-looks", "results")
os.makedirs(rep, exist_ok=True)
open(os.path.join(rep, f"fit-{a.name}.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

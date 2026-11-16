"""Check the monochrome model against camera data that the film experiment already has (no new shot).

   .venv/bin/python -I experiments/2026-11-16-doublex/scripts/check_model.py > experiments/2026-11-16-doublex/results/model-check.txt

1. Where Monotone makes grey: chart shots of 2026-11-09 (out/patches.npz), Monotone (M4) against Natural (B3).
2. The model's luma of the Natural rendering of the test RAW (reading A_natural).
3. Stock Grainy Film I (reading A_grainy_film): the picture value as contrast table (0x7E75EEF0) of g(Y_in).
   g is measured from the same reading, so this is a check of the shape (one smooth g for all colours), not a blind test.
"""
import sys
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import monolib as m

d = np.load("out/patches.npz", allow_pickle=True); roles = [str(r) for r in d["roles"]]; J = d["jpg"]
b3, m4, x2 = (J[roles.index(r)] for r in ("B3", "M4-monotone", "X-base2"))
ok = np.isfinite(b3[:, 0]) & np.isfinite(m4[:, 0]) & (b3.max(1) < 250) & (b3.min(1) > 5); sat = b3.max(1) - b3.min(1) > 60
code_of = lambda kv: np.interp(kv, m.X, m.BASE) / 4.0; kv_of = lambda c: np.interp(c * 4.0, m.BASE, m.X)
ym = m4 @ m.LUMA
print("1. Monotone (chart shot M4) against the Natural shot B3 of the same chart, 182 patches, picture codes")
print(f"   Monotone has no colour: max |R - G| = {np.nanmax(np.abs(m4[:, 0] - m4[:, 1])):.1f}")
for tag, y in (("grey = luma of the tone-coded R, G, B (0.299, 0.587, 0.114)", b3 @ m.LUMA), ("grey = tone curve of the linear luma", code_of(kv_of(b3) @ m.LUMA))):
    r = ym - y; print(f"   {tag}: mean |difference| all {np.abs(r[ok]).mean():.2f}, saturated patches {np.abs(r[ok & sat]).mean():.2f}")
print(f"   two Natural shots of the chart against each other: {np.abs((x2 @ m.LUMA - b3 @ m.LUMA)[ok]).mean():.2f}")
n, g = m.load("A_natural"), m.load("A_grainy_film"); k = g["kind"]
yn, yj = n["jpg"] @ m.LUMA, g["jpg"] @ m.LUMA
print("2. Natural rendering of the test RAW: camera luma - model luma (codes, mean |difference| / mean)")
mod = m.monotone(n["u"], n["M"]); okn = np.isfinite(yn) & (n["spread"] < 3)
print("   " + "; ".join(f"{name} {np.abs((yn - mod)[okn & (k == kk)]).mean():.2f} / {(yn - mod)[okn & (k == kk)].mean():+.2f}" for kk, name in m.SETS))
print("3. Stock Grainy Film I of the test RAW: camera - model T(g(Y_in)) (codes mean |difference|; mean |dL*|)")
pred = m.final(g["u"], g["M"]); okg = np.isfinite(yj)
print("   " + "; ".join(f"{name} {np.abs((yj - pred)[okg & (k == kk)]).mean():.2f}; {np.abs(m.grey_lab(yj[okg & (k == kk)])[:, 0] - m.grey_lab(pred[okg & (k == kk)])[:, 0]).mean():.2f}" for kk, name in m.SETS))
bx, by, sd = m.measure_transfer()
print("   g (Y_in -> x), every third knot: " + " ".join(f"{a:.0f}:{b:.0f}" for a, b in zip(bx[::3], by[::3])))
print("   spread inside a patch (codes) at those knots: " + " ".join(f"{s:.0f}" for s in sd[::3]) + f"; the noise that gives it has a spread of about {m.SIGMA_X} in x")
print(f"   stock table 0x7E75EEF0 (x -> picture value), every 16th: {(m.T_STOCK[::16] / 4).round(0).astype(int).tolist()}")

"""Second measurement of the grain program's transfer g, from the camera development of the test RAW in the
Double-X entry (first fit), checked against the stock Grainy Film reading.

   .venv/bin/python -I experiments/2026-11-16-doublex/scripts/measure_transfer2.py F12c_doublex > experiments/2026-11-16-doublex/results/grain-transfer-2.txt

Per patch, x = table^-1(picture value) with the table that the build had (the first fit's T, slope about 1; the
stock table, slope up to 3.3 and flat at both ends). g2 = medians of x in bins of Y_in, 4 codes wide, lightly smoothed, from the
Double-X reading alone: it has the matrix and the kind of table of the next build, and it gives x over the whole
range. The stock reading gives x only where its table is steep (picture value 30 to 225) and is the cross-check. Writes results/grain-transfer-2.json. Prints the two readings against each other, how
well g2 explains each reading, and the residual of the Double-X reading by colour.
"""
import json, sys
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import monolib as m

name = sys.argv[1]; first = np.load("../../looks/fits/doublex.npz"); P, T1 = first["P"], first["T"].astype(float)
cam, st = m.load(name), m.load("A_grainy_film")
yi1, yi0 = m.y_in(cam["u"], P), m.y_in(st["u"], st["M"])
x1, ok1 = m.x_of_reading(cam, T1); x0, ok0 = m.x_of_reading(st, m.T_STOCK)
y0 = st["jpg"] @ m.LUMA; ok0 &= (y0 > 30) & (y0 < 225)
def bins(yi, x, ok, step=4):
    e = np.arange(0, 260, step); i = np.digitize(yi, e); rows = []
    for j in range(1, len(e) + 1):
        s = ok & (i == j)
        if s.sum() >= 8: rows.append((yi[s].mean(), np.median(x[s]), int(s.sum())))
    return np.array(rows)
b1, b0 = bins(yi1, x1, ok1), bins(yi0, x0, ok0)
gx = b1[:, 1].copy(); inside = (b1[:, 0] >= b0[0, 0]) & (b1[:, 0] <= b0[-1, 0])
s0 = np.interp(b1[:, 0], b0[:, 0], b0[:, 1])
gx = np.maximum.accumulate(np.convolve(np.r_[gx[0], gx, gx[-1]], [0.25, 0.5, 0.25], "valid"))
old = m.g_of(b1[:, 0])
m.TRANSFER_2.write_text(json.dumps({"what": "g of the grain program of art code 74, second measurement: x = g(Y_in); knots",
    "source": f"reading {name} (test RAW, RAW Data Edit in the Double-X entry of films-12c, table T of data/films/fits/doublex.npz)",
    "y_in": b1[:, 0].round(2).tolist(), "x": gx.round(2).tolist()}, indent=1) + "\n")
print(f"Double-X reading: {int(ok1.sum())} patches give x, Y_in {yi1[ok1].min():.0f} to {yi1[ok1].max():.0f}; stock reading: {int(ok0.sum())} patches, Y_in {yi0[ok0].min():.0f} to {yi0[ok0].max():.0f}")
print("Y_in: x from the Double-X reading | from the stock reading | g2 | first g")
for k in range(0, len(b1), 3):
    print(f"  {b1[k, 0]:6.1f}: {b1[k, 1]:6.1f} | {s0[k] if inside[k] else float('nan'):6.1f} | {gx[k]:6.1f} | {float(old[k]):6.1f}")
d = b1[inside, 1] - s0[inside]
print(f"the two readings where both give x ({int(inside.sum())} bins, Y_in {b1[inside, 0].min():.0f} to {b1[inside, 0].max():.0f}): Double-X - stock mean {d.mean():+.2f}, mean |.| {np.abs(d).mean():.2f}, largest {np.abs(d).max():.1f}")
m.use_transfer(m.TRANSFER_2)
for tag, d_, yi, tab in (("Double-X reading", cam, yi1, T1), ("stock reading", st, yi0, m.T_STOCK)):
    yj = d_["jpg"] @ m.LUMA; ok = np.isfinite(yj); pred = np.interp(np.clip(m.g_of(yi), 0, 255), m.X, tab / 4.0); r = (yj - pred)[ok]
    dl = np.abs(m.grey_lab(yj[ok])[:, 0] - m.grey_lab(pred[ok])[:, 0])
    print(f"one g (g2) for the {tag}: camera - model, picture codes mean {r.mean():+.2f}, mean |.| {np.abs(r).mean():.2f}, 95th percentile {np.percentile(np.abs(r), 95):.1f}; mean |dL*| {dl.mean():.2f}")
    for lo, hi in ((0, 40), (40, 100), (100, 180), (180, 256)):
        s = ok & (pred >= lo) & (pred < hi)
        if s.sum() > 20: print(f"    model value {lo:3d}-{hi:3d}: {int(s.sum()):4d} patches, camera - model mean {(yj - pred)[s].mean():+.2f}")
r = (x1 - m.g_of(yi1))[ok1]; u = cam["u"][ok1] @ m.M5300.T; hue = np.argmax(u, 1); sat = (u.max(1) - u.min(1)) / np.maximum(u.max(1), 1e-6)
print(f"Double-X reading, residual of x against g2 by colour (scene RGB): rms {np.sqrt((r ** 2).mean()):.2f}")
for h, n in enumerate(("red", "green", "blue")):
    print(f"   largest channel {n}: " + "; ".join(f"saturation {lo:.1f}-{hi:.1f}: {r[(hue == h) & (sat >= lo) & (sat < hi)].mean():+.2f} (n {int(((hue == h) & (sat >= lo) & (sat < hi)).sum())})" for lo, hi in ((0, .3), (.3, .6), (.6, 1.01))))

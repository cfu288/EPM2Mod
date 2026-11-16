"""Predict the camera's rendering with a new grain table from a camera reading made with an earlier table.

   .venv/bin/python -I experiments/2026-11-16-doublex/scripts/predict_camera.py F12c_doublex doublex doublex2

Per patch the earlier reading gives x = T_old^-1(picture value): what the grain program fed its table for this
patch, with all that the model does not know. The prediction is T_new(x). It holds if the camera repeats itself
and the matrix is the same in both fits. Patches at the flat ends of the old table give no x; the model stands in.
"""
import sys
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import monolib as m

name, old, new = sys.argv[1:4]
fo, fn = (np.load(f"../../looks/fits/{n}.npz") for n in (old, new))
assert np.array_equal(fo["A"], fn["A"]), "the two fits have different matrices"
cam, ref = m.load(name), m.load("A_natural"); k = ref["kind"]
x, ok = m.x_of_reading(cam, fo["T"]); m.use_transfer(m.TRANSFER_2)
xm = np.clip(m.g_of(m.y_in(cam["u"], fn["P"])), 0, 255)
pred = np.interp(np.where(ok, x, xm), m.X, fn["T"] / 4.0); model = np.interp(xm, m.X, fn["T"] / 4.0)
tgt = m.target(ref["vs"]); good = np.isfinite(cam["jpg"][:, 0]) & np.isfinite(ref["u"][:, 0])
print(f"reading {name} (table of {old}) replayed through the table of {new}: {int((ok & good).sum())} of {int(good.sum())} patches give x")
for tag, y in (("predicted camera - target", pred), ("model - target", model), ("first camera result - target", cam["jpg"] @ m.LUMA)):
    s = m.score(y, tgt, k, good); print(f"{tag:28s} " + "  ".join(f"{n} {s[n][0]:.2f}/{s[n][1]:.2f}" for _, n in m.SETS))
print("predicted camera - target in picture codes, by target value:")
for lo, hi in ((0, 20), (20, 40), (40, 100), (100, 180), (180, 205), (205, 256)):
    s = good & (tgt >= lo) & (tgt < hi)
    if s.sum() > 10: print(f"  target {lo:3d}-{hi:3d}: {int(s.sum()):4d} patches, mean {(pred - tgt)[s].mean():+.2f}, mean |.| {np.abs(pred - tgt)[s].mean():.2f}; first result: mean {(cam['jpg'] @ m.LUMA - tgt)[s].mean():+.2f}")

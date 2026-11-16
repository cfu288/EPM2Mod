"""Measure a camera development of the test RAW in the Double-X entry against the model and the target.

   cd experiments/2026-11-09-film-portra
   ../../.venv/bin/python -I read_mock.py shots/measured/F12c_doublex.JPG
   ../../.venv/bin/python -I ../2026-11-16-doublex/scripts/measure_camera.py F12c_doublex [FIT [TRANSFER]]

FIT: the fit of the build, a file name in looks/fits/ without .npz (default doublex). TRANSFER: 1 or 2, which
measurement of g the model uses (default 1, as the first fit; the second fit takes 2).

Prints, per patch set, mean |dL*| / mean dE2000 of: camera against model, camera against target, model against
target; the grain spread inside a mid-grey patch; and the mean signed difference camera - model in picture codes.
"""
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import monolib as m

name = sys.argv[1]
fit_name = sys.argv[2] if len(sys.argv) > 2 else "doublex"
if len(sys.argv) > 3 and sys.argv[3] == "2":
    m.use_transfer(m.TRANSFER_2)
cam, ref = m.load(name), m.load("A_natural")
fit = np.load(f"../../looks/fits/{fit_name}.npz", allow_pickle=True)
P, D = fit["P"], fit["D"]
kind = ref["kind"]
y_cam = cam["jpg"] @ m.LUMA
y_model = m.film(cam["u"], P, D)
y_target = m.target(ref["vs"])
ok = np.isfinite(y_cam) & np.isfinite(y_model) & np.isfinite(ref["u"][:, 0])
print(f"reading {name}: {int(ok.sum())} patches; white balance applied R, B = {cam['wb'] if 'wb' in cam else 'see read_mock output'}")
print(f"colour in the picture: max |R - G| = {np.nanmax(np.abs(cam['jpg'][:, 0] - cam['jpg'][:, 1])):.1f} codes")
for tag, a, b in (("camera - model", y_cam, y_model), ("camera - target", y_cam, y_target), ("model - target", y_model, y_target)):
    s = m.score(a, b, kind, ok)
    print(f"{tag:16s} " + "  ".join(f"{n} {s[n][0]:.2f}/{s[n][1]:.2f}" for _, n in m.SETS))
d = (y_cam - y_model)[ok]
print(f"camera - model in picture codes: mean {d.mean():+.2f}, mean |.| {np.abs(d).mean():.2f}, 95th percentile |.| {np.percentile(np.abs(d), 95):.2f}")
for lo, hi in ((0, 40), (40, 100), (100, 180), (180, 256)):
    sel = ok & (y_model >= lo) & (y_model < hi)
    if sel.any():
        print(f"  model value {lo:3d}-{hi:3d}: {int(sel.sum()):4d} patches, camera - model mean {(y_cam - y_model)[sel].mean():+.2f}, spread in a patch {np.nanmedian(cam['spread'][sel]):.1f} codes")

"""Score a flashed Cross Process I build against the camera: shots/PB090223.JPG = RAW Data Edit of PB090221.

Usage: ../../.venv/bin/python -I check_flashed.py [JPG] [G.npy] [gain] [look.npy]
Prints camera vs model (ΔE2000), the saturation that best explains the camera, and camera vs the Portra target.
"""
import importlib.util, json, os, sys
import numpy as np
from scipy.optimize import minimize_scalar
HERE = os.path.dirname(os.path.abspath(__file__)); args = sys.argv[1:]; sys.argv = [sys.argv[0]]
def imp(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(HERE, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
ex = imp("extract"); fl = imp("fit_look"); tone = fl.tone
jpg = args[0] if args else "shots/PB090223.JPG"
G = np.load(args[1] if len(args) > 1 else "out/fit_crossprocess_G.npy"); gain = int(args[2]) if len(args) > 2 else 245
look = np.load(args[3]) if len(args) > 3 else None
d, st, meta = tone.load(); names = [str(n) for n in d["names"]]; k = names.index("PB090221"); rows = np.array([m["row"] for m in meta])
lay = json.load(open(os.path.join(HERE, "out", "chart_layout.json")))["1920x1080"]
jp, small, sc = ex.load_jpeg(os.path.join(HERE, jpg)); H = ex.homography(lay, small, sc)
q, _ = ex.refine(sum(jp) / 3, ex.inner_quads(lay, H)); q, g = ex.grid_quads(sum(jp) / 3, q)
S = [ex.sample(jp, qq) for qq in q]; J = np.array([[s[0] for s in x] for x in S]); spread = np.array([max(s[2] - s[1] for s in x) for x in S])
v = tone.precurve(d, st, k); ok = (~d["rawclip"][k]) & (~tone.BAD[k]) & (spread < 20) & (J.min(1) > 4) & (J.max(1) < 250)
gr, co = ok & (rows == 6), ok & (rows < 6)
de = lambda p, j: fl.de2000(fl.srgb_to_lab(p), fl.srgb_to_lab(j))
Jn = d["jpg"][k]; okn = ok & (Jn.min(1) > 4) & (Jn.max(1) < 250) & (rows < 6)
sn = minimize_scalar(lambda s: de(fl.cam_curves(v[okn], fl.IDENT_G, s), Jn[okn]).mean(), bounds=(0.5, 2), method="bounded").x
sc_ = minimize_scalar(lambda s: de(fl.cam_curves(v[co], G, s, look), J[co]).mean(), bounds=(0.5, 2), method="bounded").x
print(f"{jpg}: gain written {gain}; Natural (same RAW, stock JPEG) saturation {sn:.3f}; camera's saturation in this build {sc_:.3f}; "
      f"ratio {sc_/sn:.3f} vs gain ratio {gain/282:.3f}")
for label, s in (("saturation predicted from the gain", sn * gain / 282), ("saturation fitted to the camera", sc_)):
    e = de(fl.cam_curves(v, G, s, look), J)
    print(f"  camera vs model, {label} ({s:.3f}): gray {e[gr].mean():.2f}  colour mean {e[co].mean():.2f} p95 {np.percentile(e[co], 95):.2f}  (n={co.sum()})")
print("  gray row rms per channel (codes):", np.sqrt(np.mean((fl.cam_curves(v, G, 1.0, look) - J)[gr] ** 2, 0)).round(2))
L = os.path.join(HERE, "out/lut/spektrafilm_v034_portra400_portraendura_1lut_vlog_srgb/lut_v034_portra400_portraendura.cube")
cube, size = fl.load_cube(L); T = np.clip(fl.apply_cube(cube, size, fl.encode(v / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255
a, b = de(J, T), de(Jn, T)
print(f"  camera vs Portra target: gray {a[gr].mean():.2f} colour {a[co].mean():.2f} | stock Natural JPEG: gray {b[gr].mean():.2f} colour {b[co].mean():.2f}")

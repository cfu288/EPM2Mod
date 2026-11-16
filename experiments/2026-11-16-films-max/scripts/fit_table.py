"""Table of the model-only fits (fit_more.sh) and of the seven installed looks.

For each fit: the model's prediction against the fit's own target LUT, ΔE2000 mean per patch group of test image A
(the figures fit_film2.py prints, plus the 95th percentile of the natural colours), and the distance of its TARGET to
the target of each installed look (mean ΔE2000 on the 1,000 hold-out natural colours; NOTES §38.2 of
2026-11-09-film-portra). The installed looks are scored the same way: model alone against target (for them the fit
was anchored on a camera measurement, so this is the "model vs target" row of that folder's README).
Run from the film-portra folder:
   cd experiments/2026-11-09-film-portra && ../../.venv/bin/python -I ../2026-11-16-films-max/scripts/fit_table.py
Writes ../2026-11-16-films-max/results/fits.tsv and distances.tsv.
"""
import os, sys
sys.path.insert(0, os.getcwd())
import numpy as np
argv = sys.argv; sys.argv = ["x"]
from mocklib import *
import model2 as M2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
# short name, film, print material, fit file, class
NEW = [("ektar100", "Kodak Ektar 100", "Kodak Portra Endura paper"), ("provia100f", "Fujifilm Provia 100F", "none (slide)"),
       ("gold200", "Kodak Gold 200", "Kodak Portra Endura paper"), ("gold200ca", "Kodak Gold 200", "Fuji Crystal Archive paper"),
       ("portra160", "Kodak Portra 160", "Kodak Portra Endura paper"), ("vision3500t", "Kodak Vision3 500T", "Kodak 2383 print film"),
       ("portra800", "Kodak Portra 800", "Kodak Portra Endura paper"), ("c200", "Fujifilm C200", "Fuji Crystal Archive paper"),
       ("ultramax400", "Kodak UltraMax 400", "Kodak Portra Endura paper"), ("vision350d", "Kodak Vision3 50D", "Kodak 2383 print film"),
       ("vision3200t", "Kodak Vision3 200T", "Kodak 2383 print film"), ("verita200d", "Kodak Verita 200D", "Kodak 2383 print film"),
       ("portra4002383", "Kodak Portra 400", "Kodak 2383 print film")]
OLD = [("portra", "Kodak Portra 400", "Kodak Portra Endura paper"), ("ektachrome", "Kodak Ektachrome 100", "none (slide)"),
       ("pro400h", "Fuji Pro 400H", "Fuji Crystal Archive paper"), ("kodachrome64", "Kodak Kodachrome 64", "none (slide)"),
       ("vision3250d", "Kodak Vision3 250D", "Kodak 2383 print film"), ("velvia100", "Fuji Velvia 100", "none (slide)"),
       ("superia400", "Fuji Superia X-tra 400", "Fuji Crystal Archive paper")]
# two passes per film: n1 = the standard starts of fit_film2.py (neutral, Portra); n2 = starts from the three nearest
# installed looks (fit_more_starts.sh). The pass with the lower weighted ΔE (the fit's own figure) is marked chosen.
CTRL = [("ctrl-portra", "Kodak Portra 400", OLD[0][2]), ("ctrl-velvia100", "Fuji Velvia 100", OLD[5][2])]
d = load("A_natural"); k = d["kind"]; ok = np.isfinite(d["u"][:, 0])
rows = [(f"{n}-{q}", f, p, f"out/fit_film-{n}-{q}.npz", c) for c, L in (("new, model only", NEW), ("control, model only", CTRL)) for n, f, p in L for q in ("n1", "n2")]
rows += [(n, f, p, f"../../looks/fits/{n}.npz", "installed, anchored fit") for n, f, p in OLD]
W = d["weight"]; W = np.where(W > 0, W, np.where(k == 8, 20.0, np.where(k == 3, 4.0, np.where(k == 2, 20.0, np.where(k == 10, 0.25, 0.0)))))    # as fit_film2.py
def target(lut):
    cube, size = fl.load_cube(lut)
    return lab(np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(d["vs"], 0) / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255)
T, Z = {}, {}
for n, _, _, path, _ in rows:
    if os.path.exists(path): Z[n] = np.load(path); T[n] = target(str(Z[n]["lut"]))
hold = ok & (k == 9); inst = [n for n, _, _ in OLD]
dist = lambda a, b: de(T[a][hold], T[b][hold]).mean()
GROUPS = (("natural", 5), ("skin", 8), ("colorchecker_x5", 7), ("grays", 6), ("hold_out", 9), ("near_neutral", 3), ("dense_grays", 2), ("gamut_edge", 10))
head = ["name", "film", "print", "class", "chosen", "weighted"] + [g for g, _ in GROUPS] + ["natural_p95", "gain", "nearest_installed", "nearest_distance"] + [f"dist_{n}" for n in inst] + ["target_lut"]
out = ["\t".join(head)]; D = {}
for n in Z:
    z = Z[n]; D[n] = de(lab(M2.render(d["u"], z["G"], M2.gain_of(z), z["S"], z["H"], z["P"], M2.chroma_of(z))), T[n])
wsel = ok & (W > 0); wm = {n: np.average(D[n][wsel], weights=W[wsel]) for n in D}
for n, film, pr, path, cls in rows:
    if n not in Z: print("missing:", path); continue
    z = Z[n]; dd = D[n]; other = n[:-1] + ("2" if n.endswith("1") else "1")
    chosen = "-" if cls.startswith("installed") else "yes" if other not in wm or wm[n] <= wm[other] else "no"
    ds = {m: dist(n, m) for m in inst if m != n}; near = min(ds, key=ds.get)
    out.append("\t".join([n, film, pr, cls, chosen, f"{wm[n]:.3f}"] + [f"{dd[ok & (k == kk)].mean():.2f}" for _, kk in GROUPS] + [f"{np.percentile(dd[ok & (k == 5)], 95):.2f}", str(M2.gain_of(z)), near, f"{ds[near]:.2f}"]
                         + [f"{ds[m]:.2f}" if m in ds else "0.00" for m in inst] + [os.path.basename(str(z['lut']))]))
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "fits.tsv"), "w").write("\n".join(out) + "\n"); print("\n".join(out))
names = [r[0] for r in rows if r[0] in Z and not r[0].startswith("ctrl-") and not r[0].endswith("-n2")]
m = ["\t".join(["target"] + names)] + ["\t".join([a] + [f"{dist(a, b):.2f}" for b in names]) for a in names]
m = [x.replace("-n1", "") for x in m]
open(os.path.join(OUT, "distances.tsv"), "w").write("\n".join(m) + "\n")

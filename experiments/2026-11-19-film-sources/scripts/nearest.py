"""nearest.py: for each new spectral_film_lut film, the nearest film among SFL's versions of films we already ship
(same simulator, so the cross-simulator offset does not count), as mean ΔE2000 over ColorChecker + random colours."""
import sys, glob, os, numpy as np, colour
exec(open(os.path.join(os.path.dirname(__file__), "cmp.py")).read().split("sets = ")[0].replace("import sys, numpy as np, colour", ""))
scene = np.vstack([lin_cc, rnd[:600]])
have = ["Kodak-Portra-400", "Kodak-Portra-160", "Fuji-Superia-X-Tra-400", "Kodak-Ektachrome-100D", "Kodak-Vision3-250D-5207", "Kodak-Vision3-500T-5219", "Kodak-Vision3-50D-5203", "Kodak-Vision3-200T-5213", "Fuji-Provia-100F", "Kodachrome-64"]
luts = {os.path.basename(p).split("__")[0]: p for p in glob.glob(os.path.join(os.path.dirname(__file__), "luts/*.cube"))}
lab = {k: run(p, scene) for k, p in luts.items()}
for k in sorted(luts):
    if k in have: continue
    d = {o: colour.delta_E(lab[k], lab[o], method="CIE 2000").mean() for o in luts if o != k}
    near = sorted(d.items(), key=lambda x: x[1])[:2]
    print(f"{k:28s} nearest: " + ", ".join(f"{o} {v:.1f}" for o, v in near) + " | vs shipped-film versions: " + ", ".join(f"{o.split('-',1)[1]} {d[o]:.1f}" for o in have))

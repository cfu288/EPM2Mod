"""Camera versus model over every rendering of test image A with known settings (NOTES §45).
   ../../.venv/bin/python -I eval_model.py"""
import os, sys
sys.argv = ["x"]; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fit_xp9 as f, chroma as C, model2 as M2
from mocklib import *
SETS = [("A_portra_xp9", "xp9"), ("A_portra_xp10", "film-portra-xp10"), ("A_ektachrome_lt2", "film-ektachrome-lt2"), ("A_ektachrome_lt3", "film-ektachrome-lt3"), ("A_pro400h_pa1c", "film-pro400h-pa1"),
        ("R2_pro400h_pa2", "film-pro400h-pa2"), ("F1_kodachrome", "cand-kodak_kodachrome_64_scanfilm"), ("F1_vis250d", "cand-vision3250d_2383"), ("F1_velvia", "cand-fujifilm_velvia_100_scanfilm"),
        ("F1_superia", "cand-xtra400_crystalarchive"), ("F2_kodachrome", "film-kodachrome64-2"), ("F2_vis250d", "film-vision3250d-2"), ("F2_velvia", "film-velvia100-2"), ("F2_superia", "film-superia400-2"),
        ("F3_portra", "film-portra-c1"), ("F3_ektachrome", "film-ektachrome-c1"), ("F3_pro400h", "film-pro400h-c1"), ("F3_kodachrome", "film-kodachrome64-c1"), ("F3_vis250d", "film-vision3250d-c1"),
        ("F3_velvia", "film-velvia100-c1"), ("F3_superia", "film-superia400-c1")]
GROUPS = ((5, "natural"), (9, "hold-out"), (7, "ColorChecker"), (8, "skin"), (6, "grays"), (2, "dense gray"), (3, "near-neutral"), (10, "gamut edge"))
def old(u, z):
    mm = f.R(u, z["G"], float(z["sat"]), z["S"], z["H"], z["P"])
    if "Cb" in z.files: mm = C.apply(mm, *M2.chroma_of(z), stored=True)
    return np.clip(mm, 0, 255)
def new(u, z, **kw): return M2.render(u, z["G"], float(z["sat"]), z["S"], z["H"], z["P"], M2.chroma_of(z), **kw)
def table(models, sets=SETS):
    acc = {nm: {g: [] for g, _ in GROUPS} for nm in models}
    for rd, ft in sets:
        d = load(rd); z = np.load(f"out/fit_{ft}.npz"); J, k, ok, u = d["jpg"], d["kind"], d["ok"], d["u"]
        for nm, fn in models.items():
            dE = de(lab(J), lab(fn(u, z)))
            for g, _ in GROUPS: acc[nm][g].append(dE[ok & (k == g)].mean())
    return {nm: {g: float(np.mean(v)) for g, v in a.items()} for nm, a in acc.items()}
if __name__ == "__main__":
    t = table({"old model": old, "new model": new, "new, tables not odd": lambda u, z: new(u, z, odd_g=False), "new, clamp 112": lambda u, z: new(u, z, clamp=112.0), "new, clamp 118": lambda u, z: new(u, z, clamp=118.0), "new, no offset": lambda u, z: new(u, z, offset=0.0)})
    print(f"{'camera vs model, mean of 21 renderings':40s}" + "".join(f"{n:>13s}" for _, n in GROUPS))
    for nm, a in t.items(): print(f"{nm:40s}" + "".join(f"{a[g]:13.2f}" for g, _ in GROUPS))

"""Camera-measured effect of the fitted 12-region tables on their own films (calibration run files 2-4, PB130001):
ART 1 (no table), ART 2 (Natural's table A, as films get it today), the film's fitted table; against the fit_twelve
prediction. Research code. Needs the readings copied as out/mock/read_CAL_f<n>_A_ART<k>.npz of the film-portra
experiment (see NOTES.md §6).

    OMP_NUM_THREADS=4 uv run --with colour-science python experiments/2026-11-20-model-calibration/scripts/table_gain.py
"""
import sys, os, json
sys.path.insert(0, "experiments/2026-11-20-twelve-region/scripts"); sys.argv = ["x"]
import fit_twelve as FT
cat = {f["id"]: f for f in json.load(open("data/films/catalogue.json"))["films"]}
pred = {fid: json.load(open(f"experiments/2026-11-20-twelve-region/out/twelve/{fid}.json")) for fid in ("portra-400", "velvia", "ektachrome")}
for n, fid, art in ((2, "portra-400", 3), (3, "velvia", 4), (4, "ektachrome", 5)):
    fit = os.path.join(FT.ROOT, cat[fid]["fit"])
    f = lambda s: f"natural {s['natural']:.2f}  hold-out {s['holdout']:.2f}  ColorChecker {s['colorchecker']:.2f}  skin {s['skin']:.2f}  grays {s['grays']:.2f}"
    print(f"{fid}:")
    for a, what in ((1, "no table (off)   "), (2, "Natural's table  "), (art, "its fitted table ")):
        F = FT.Film(fid, f"CAL_f{n}_A_ART{a}", fit)
        print(f"   camera, {what}: {f(F.score(F.J))}")
    print(f"   predicted (confirmation round -> table): {f(pred[fid]['measured'])}  ->  {f(pred[fid]['predicted_table'])}")

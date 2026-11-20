"""Film files of the convergence round: build/films-off2/<A|B|C>/EPM2LOOK.BIN, the films of build/films-confirm/ in the
same entries, each with its correction from the films-twelve-off round (fit_film2 --anchor OFF_<id>:
out/fit_film-<fit>-n1.npz in the film-portra experiment; Double-X as before). Research code.

    uv run python experiments/2026-11-20-model-calibration/scripts/pack_round2.py
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
from round_off import FILMS  # noqa: E402

ENTRIES = ["Pop Art", "Soft Focus", "Pale&Light Color", "Light Tone", "Grainy Film", "Pin Hole", "Diorama",
           "Cross Process", "Gentle Sepia", "Dramatic Tone", "Key Line", "Watercolor"]
CAT = {x["id"]: x for x in json.load(open(os.path.join(ROOT, "data", "films", "catalogue.json")))["films"]}


def corrected(fid):
    if fid == "double-x":
        return CAT[fid]["fit"]
    n = os.path.basename(CAT[fid]["fit"])[:-4]
    n = n[:-3] if n.endswith("-c1") else n
    p = os.path.join("experiments", "2026-11-09-film-portra", "out", f"fit_film-{n}-n1.npz")
    assert os.path.exists(os.path.join(ROOT, p)), p
    return p


def main():
    os.chdir(ROOT)
    for b, films in FILMS.items():
        d = os.path.join("build", "films-off2", b); os.makedirs(d, exist_ok=True)
        lst = os.path.join(d, "list.json")
        json.dump({"looks": [{"entry": ENTRIES[i], "name": CAT[fid]["name"], "fit": corrected(fid)} for i, fid in enumerate(films)]},
                  open(lst, "w"), indent=1)
        subprocess.run(["uv", "run", "epm2mod", "films", "pack", lst, "-o", os.path.join(d, "EPM2LOOK.BIN")], check=True,
                       capture_output=True)
        print(b, subprocess.run(["sha256sum", os.path.join(d, "EPM2LOOK.BIN")], capture_output=True, text=True).stdout.strip())


if __name__ == "__main__":
    main()

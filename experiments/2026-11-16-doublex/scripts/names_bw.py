"""Write patches/films12bw-names.json: the names of looks/films-12-bw.json in all 34 menu languages.

    .venv/bin/python experiments/2026-11-16-doublex/scripts/names_bw.py --base build/peaking-fast.BIN

It runs experiments/2026-11-16-films-max/scripts/names_spec.py with the entry -> label pairs of the list
(more-films.json with the black-and-white film in its entry and the colour film of that entry in `moved_to`). The spec takes the place of patches/films12-names.json.
"""
import json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments" / "2026-11-16-films-max" / "scripts"))
import names_spec  # noqa: E402

OUT = "patches/films12bw-names.json"
data = json.loads((ROOT / "looks" / "films-12-bw.json").read_text())
labels = {film["entry"]: film["label"] for film in json.loads((ROOT / "looks" / "more-films.json").read_text())["films"]}
labels[data["moved_to"]] = labels[data["mono"]["entry"]]  # the colour film of the entry moves
labels[data["mono"]["entry"]] = data["mono"]["label"]
films = [{"entry": entry, "label": label} for entry, label in labels.items()]
with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
    json.dump({"films": films}, handle); handle.flush()
    sys.argv = [sys.argv[0], "--films", handle.name, "--out", OUT, *sys.argv[1:]]
    names_spec.main()
if "--table" not in sys.argv:
    spec = json.loads((ROOT / OUT).read_text())
    spec["description"] = ("The list with a black-and-white film (looks/films-12-bw.json): takes the place of patches/films12-names.json. "
                           + spec["description"] + " Run by experiments/2026-11-16-doublex/scripts/names_bw.py.")
    (ROOT / OUT).write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

"""Write web/src/data/films.json, the films the web app offers (epm2mod.looks.lookpack.web_data).

    uv run python web/scripts/export_films.py

Run it after a change of looks/catalogue.json, looks/card-looks.json or a fit; tests/test_lookfile.py fails while the
file is out of date.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from epm2mod.looks.lookpack import web_data  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

out = ROOT / "web/src/data/films.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(web_data(RepoPaths(ROOT)), indent=1) + "\n")
print("wrote", out.relative_to(ROOT))

"""Write looks/film-records.json, the films that look files are packed from (epm2mod.looks.lookpack.web_data).

    uv run python web/scripts/export_films.py

The CLI (`epm2mod install`, `epm2mod films set`), the local app and the web site all read it. Run this after a change of
looks/catalogue.json or a fit; tests/test_lookfile.py fails while the file is out of date.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from epm2mod.looks.lookpack import web_data  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

out = RepoPaths(ROOT).film_records
out.write_text(json.dumps(web_data(RepoPaths(ROOT)), indent=1) + "\n")
print("wrote", out.relative_to(ROOT))

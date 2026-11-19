"""Every byte the film specs of data/builds/log-menu.json change, split into free space (new bytes that nothing stock
reads) and stock bytes (stock code or data changed), with the op's note.

    uv run python experiments/2026-11-18-stock-filters/scripts/inventory.py
"""
import csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "cli" / "src"))
from epm2mod.spec import load_spec, BytesOp, Utf16ReplaceAllOp  # noqa: E402

BASE = 0x7E421020
FILM = ["remap7b-code", "seven-fixes-1", "seven-movie-1", "seven-structure-extra", "seven-films-5",
        "xp-adaptive-hue-off", "seven-labels", "films12-structure", "films12cl-looks", "films12bw-names",
        "films12-entry-grainy-film", "films12-entry-gentle-sepia", "films12-entry-dramatic-tone",
        "films12-entry-key-line", "films12-entry-watercolor"]
areas = [(int(r["start"], 16), int(r["end"], 16), r["verdict"])
         for r in csv.DictReader(open(ROOT / "docs/reference/code-space-map.tsv"), delimiter="\t")]


def area(a):
    for lo, hi, v in areas:
        if lo <= a < hi:
            return v
    return None


tot = {}
for name in FILM:
    raw = json.load(open(ROOT / "data" / "specs" / (name + ".json")))
    sp = load_spec(ROOT / "data" / "specs" / (name + ".json"))
    free = stock = text = 0
    rows = []
    for o, r in zip(sp.ops, raw["ops"]):
        note = (r.get("_note") or "")[:110]
        if not isinstance(o, BytesOp):
            text += 1
            continue
        if o.block != 0:
            text += 1
            continue
        a = BASE + o.offset
        n = sum(x != y for x, y in zip(o.expect, o.new))
        if area(a):
            free += n
        else:
            stock += n
            rows.append("    %08X %4d B  %s" % (a, n, note))
    print("%-30s free %6d B, stock %5d B, text/other-block ops %d" % (name, free, stock, text))
    if "-v" in sys.argv:
        print("\n".join(rows))

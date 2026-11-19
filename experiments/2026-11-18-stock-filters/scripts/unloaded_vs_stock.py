"""F1 at byte level: every byte of block 0 that the film part of builds/stock-films.json changes against Olympus's
firmware, sorted into the classes that leave the stock filters as they are with nothing loaded. A byte in no class
fails.

    uv run python experiments/2026-11-18-stock-filters/scripts/unloaded_vs_stock.py
"""
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from epm2mod.spec import load_spec, BytesOp  # noqa: E402
from epm2mod.looks import slots  # noqa: E402

BASE = 0x7E421020
FILM_SPECS = ["stock-films-structure", "card-looks-5", "looks-menu-4"]
FILM_CODES = [75, 92, 125, 94, 98, 144, 156, 159]
HIDDEN = [111, 112, 114, 115, 118]


def main():
    areas = [(int(r["start"], 16), int(r["end"], 16)) for r in csv.DictReader(open(ROOT / "docs/reference/code-space-map.tsv"), delimiter="\t")]
    layout = json.load(open(ROOT / "build/stock-films/layout.json"))
    switched = {w["address"] + i for e in layout["entries"] for w in e["switch"]
                for i in range(len(bytes.fromhex(w["film"])))}
    unreachable = set()
    for (table, first) in (slots.LOOK_JUMP, slots.SATURATION_JUMP, slots.SIX_AXIS_JUMP, slots.CHROMA_JUMP):
        for c in FILM_CODES:
            unreachable.update(range(table + 4 * (c - first), table + 4 * (c - first) + 4))
    for table in [slots.FILTER_TYPE_JUMP, slots.KIND_JUMP, slots.EXIF_JUMP, slots.IS_ART_JUMP] + \
            [t for s, m, _ in slots.LIVE_VIEW for t in (s, m)]:
        for v in HIDDEN:
            unreachable.update(range(table + 4 * (v - 100), table + 4 * (v - 100) + 4))
    hash_tables = [(slots.GAMMA_HASH, slots.GAMMA_HASH_ENTRIES), (slots.COLOUR_TONE_HASH, 32), (slots.MOVIE_TAG_HASH, 32),
                   (slots.RECORD_CLASS_HASH, 32)]
    classes = {}
    bad = []
    for name in FILM_SPECS:
        raw = json.load(open(ROOT / "patches" / (name + ".json")))["ops"]
        for op, r in zip(load_spec(ROOT / "patches" / (name + ".json")).ops, raw):
            if not isinstance(op, BytesOp) or op.block != 0:
                classes["text (block 1): the row's English texts, as the pinned build"] = classes.get("text (block 1): the row's English texts, as the pinned build", 0) + 1
                continue
            note = r.get("_note", "")
            for i, (x, y) in enumerate(zip(op.expect, op.new)):
                if x == y:
                    continue
                a = BASE + op.offset + i
                if any(lo <= a < hi for lo, hi in areas):
                    k = "free space: new code and data, reached only from hooks and film routes"
                elif a in switched:
                    k = "a switched word: stock with nothing loaded (the sessions dump it)"
                elif a in unreachable:
                    k = "a table entry of a film code or a hidden value (no stock entry reaches it)"
                elif any(t <= a < t + 8 * n for t, n in hash_tables) and ("hash" in note):
                    k = "a new key in a hash table (an empty entry before: absent keys still end at an empty entry)"
                elif note.startswith("hook") or "task table" in note:
                    k = "a hook or the task entry: " + note.split(":")[0].split("(")[0].strip()[:60]
                elif "job block compare" in note:
                    k = "the compares of codes 75 / 125 (no stock entry reaches them)"
                elif name == "looks-menu-4" or "panel 610" in note or "value -> text list 610" in note:
                    k = "the Load Looks row's list (a menu row, as the pinned build)"
                else:
                    bad.append((name, hex(a), note[:80]))
                    continue
                classes[k] = classes.get(k, 0) + 1
    for k, n in sorted(classes.items(), key=lambda t: -t[1]):
        print("%6d  %s" % (n, k))
    for b in bad[:20]:
        print("UNEXPLAINED", b)
    print("ALL BYTES EXPLAINED" if not bad else "%d bytes unexplained" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""The gate "a loaded entry reads the film firmware's values" (design.md): the tables of each entry in the camera-tested
film firmware (data/builds/log-menu.json, which flashes the 12 default films) against the entry's RAM block after a Load
of the same 12 films in data/builds/stock-films.json (loaded_image.py).

    uv run python experiments/2026-11-18-stock-filters/scripts/equal_tables.py FILM_BLOCK0 LOADED_BLOCK0
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "cli", "src"))
from epm2mod.looks import lookfile, slots  # noqa: E402

BASE = 0x7E421020


def main():
    film = open(sys.argv[1], "rb").read()
    new = open(sys.argv[2], "rb").read()
    layout = json.load(open(os.path.join(ROOT, "build", "stock-films", "layout.json")))
    off = layout["offsets"]
    f = lambda a, n: film[a - BASE:a - BASE + n]
    g = lambda a, n: new[a - BASE:a - BASE + n]
    where = {s.entry: s for s in slots.SLOTS}
    where.update({x.entry: x.look for x in slots.EXTRA_SLOTS})
    bad = 0
    for k, entry in enumerate(lookfile.MENU_ENTRIES):
        s = where[entry]
        b = layout["film_ram"] + layout["block"] * k
        checks = [("saturation", f(s.saturation, 4), g(b + off["sat"], 4)),
                  ("six-axis", f(s.six_axis[0], 12) + f(s.six_axis[1], 12), g(b + off["six_s"], 12) + g(b + off["six_h"], 12)),
                  ("matrix", f(s.matrix, 18), g(b + off["matrix"], 18)),
                  ("chroma", f(s.chroma, 97), g(b + off["chroma"], 97))]
        for ch in range(3):
            if isinstance(s.tone, slots.Tables):
                checks.append(("tone %d stills" % ch, f(s.tone.addresses[ch], 512), g(b + off["tone"] + 512 * (8 * ch + 1), 512)))
            else:
                rec = s.tone.addresses[ch]
                for i in range(8):
                    t = struct.unpack("<I", f(rec + 4 * i, 4))[0]
                    checks.append(("tone %d table %d" % (ch, i), f(t, 512), g(b + off["tone"] + 512 * (8 * ch + i), 512)))
        diff = [name for name, x, y in checks if x != y]
        bad += bool(diff)
        print("%-18s %s" % (entry, "equal (%d tables)" % len(checks) if not diff else "DIFFERS: " + ", ".join(diff)))
    print("ALL EQUAL" if not bad else "%d entries differ" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

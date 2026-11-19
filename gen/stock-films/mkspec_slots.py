"""Write patches/films12cl-looks.json: the twelve films of the pinned build in twelve colour slots.

    uv run python experiments/2026-11-17-card-looks/scripts/mkspec_slots.py

Grainy Film becomes a colour slot like the other eleven (patches/films12-entry-grainy-film.json: value 111, art code
94, the tables of the first extra slot), and Gentle Sepia stores its own hidden value again
(patches/films12-entry-gentle-sepia.json: value 112, art code 98). This spec takes the place of
patches/films12-looks.json: the five extra slots get Kodak Double-X as a colour look (looks/fits/doublex3.npz:
saturation 0, scripts/fit_bw_colour.py), Fujifilm Provia 100F, and the three films of films12-looks, so the menu
(patches/films12bw-names.json) keeps the films of the pinned build. The grain program of the stock Grainy Film is no
longer used. Every expect is a byte string of the specs before it in LAYOUT.
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from epm2mod.container import parse  # noqa: E402
from epm2mod.looks import generate, slots  # noqa: E402
from epm2mod.looks.films import Film  # noqa: E402
from epm2mod.spec import op_to_json  # noqa: E402

SPEC = "films12cl-looks"
STOCK = "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN"
# the specs of the layout, in build order; SPEC goes after films12-looks
LAYOUT = [s for s in json.load(open(os.path.join(ROOT, "builds/card-looks.json")))["specs"]
          if s not in ("patches/films12bw-doublex.json", "patches/films12bw-doublex2.json",
                       "patches/films12bw-entry-gentle-sepia.json", "patches/card-looks.json")]
LAYOUT.insert(LAYOUT.index("patches/films12bw-names.json") + 1, "patches/films12-entry-grainy-film.json")
LAYOUT.insert(LAYOUT.index("patches/films12-entry-grainy-film.json") + 1, "patches/films12-entry-gentle-sepia.json")
LAYOUT[LAYOUT.index("patches/films12-looks.json")] = "patches/%s.json" % SPEC
# the layout with the Custom Menu of patches/custom-menu-rows.json (Peaking and Load Looks added) in place of
# peaking-menu (card-looks-4)
LAYOUT4 = [("patches/custom-menu-rows.json" if x == "patches/peaking-menu.json" else x) for x in LAYOUT]
FILMS = [
    (Film("Grainy Film", "Kodak Double-X 5222", "black-and-white negative, on Kodak 2302 print film", "Double-X",
          "looks/fits/doublex3.npz"), slots.EXTRA_SLOTS[0].look),
    (Film("Gentle Sepia", "Fujifilm Provia 100F", "slide", "Provia", "looks/fits/provia100f.npz"),
     slots.EXTRA_SLOTS[1].look),
]
_more = {f["entry"]: f for f in json.load(open(os.path.join(ROOT, "looks/more-films.json")))["films"]}
FILMS += [(Film(**_more[e]), x.look) for e, x in zip(("Dramatic Tone", "Key Line", "Watercolor"), slots.EXTRA_SLOTS[2:])]

if __name__ == "__main__":
    before = LAYOUT[:LAYOUT.index("patches/%s.json" % SPEC)]
    work = os.path.join(ROOT, "build", "card-looks")
    os.makedirs(work, exist_ok=True)
    out = os.path.join(work, "before-cl.BIN")
    subprocess.run(["uv", "run", "epm2mod", "apply", *before, "--from", "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "-o", out], cwd=ROOT, check=True, capture_output=True)
    program = generate.Program(parse(open(out, "rb").read()).blocks[0].payload)
    ops = []
    for film, slot in FILMS:
        ops += generate.film_ops(program, film, generate.load_fit(Path(ROOT) / film.fit), slot)
    ops = [op for op in ops if op.expect != op.new]
    spec = {
        "name": SPEC,
        "attribution": generate.ATTRIBUTION,
        "description": ("The films of the pinned build in twelve colour slots: Kodak Double-X 5222 as a colour look "
                        "(saturation 0, the art matrix sets the grey mix, one tone curve; looks/fits/doublex3.npz) in "
                        "the tables of the first extra slot, which Grainy Film selects with "
                        "patches/films12-entry-grainy-film.json, and Fujifilm Provia 100F in the tables of the second, "
                        "which Gentle Sepia selects with patches/films12-entry-gentle-sepia.json; Kodak Portra 160, "
                        "Kodak Gold 200 and Kodak Vision3 500T as in patches/films12-looks.json, whose place this spec "
                        "takes. No grain program. See experiments/2026-11-17-card-looks/design.md "
                        "section 9.5."),
        "base": STOCK,
        "base_sha256": hashlib.sha256(open(os.path.join(ROOT, STOCK), "rb").read()).hexdigest(),
        "status": "candidate: emulator-checked, not flashed",
        "ops": [op_to_json(op) for op in ops],
    }
    with open(os.path.join(ROOT, "patches", SPEC + ".json"), "w") as fh:
        json.dump(spec, fh, indent=1)
        fh.write("\n")
    print("wrote patches/%s.json: %d ops, %d bytes" % (SPEC, len(ops), sum(len(o.new) for o in ops)))
    print("layout:", " ".join(os.path.basename(s)[:-5] for s in LAYOUT))

"""Write the bits behind the home page's drawing: the bytes EPM2Mod's own patches write into the firmware.

    python3 web/scripts/mod_bits.py

Reads the pinned build's patch specs and takes the "new" bytes of their byte ops in order (the film look data,
derived from spektrafilm, is left out: only the mod's code and menu changes). Writes them as 0s and 1s to
web/apps/site/src/assets/mod-bits.txt.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web/apps/site/src/assets/mod-bits.txt"
BITS = 8192  # more than the drawing's background shows
FILM_DATA = ("seven-films", "films12cl-looks")


def main():
    build = json.loads((ROOT / json.loads((ROOT / "pinned-build.json").read_text())["build"]).read_text())
    bits = []
    for spec in build["specs"]:
        if Path(spec).stem.startswith(FILM_DATA):
            continue
        for op in json.loads((ROOT / spec).read_text()).get("ops", []):
            if op.get("type") == "bytes" and op.get("new"):
                bits += [f"{b:08b}" for b in bytes.fromhex(op["new"])]
    text = "".join(bits)[:BITS]
    OUT.write_text(text + "\n")
    print(f"{len(text)} bits from {len(bits)} bytes -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

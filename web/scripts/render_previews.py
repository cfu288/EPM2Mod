"""Render the camera's Picture Mode strip with the emulator, as two layers the web app stacks.

    uv run python web/scripts/render_previews.py

For each film of data/films/catalogue.json: boots the pinned build (card-looks-4) in the boot lab with a card whose
EPM2LOOK.BIN holds that film in all 12 entries, loads it (MENU -> Custom Menu -> J -> Load Looks -> Load), opens
the Picture Mode strip (OK, UP) and takes a screenshot at ART 1 to ART 12 (the strip: y 356-480 of the screen).

The film's name and the ART position are drawn in separate parts of the strip, so they are saved separately:

- web/packages/ui/src/previews/name/<film>.png: the inside of the name box (NAME), with the film's name;
- web/packages/ui/src/previews/menu/art<N>.png: the strip at ART N with the name box empty.

The web app puts the name of the film in a row over the strip of that row's position, so the preview follows the
order the user sets. The script checks that the films' strips differ only inside NAME and that a film's name does
not change with the position; otherwise the split would be wrong and it stops.

Needs the emulator (emulator/setup.sh), build/card-looks-4.BIN and the state build/emu/state/card-looks-4-p.json
(emulator/mkstate data/builds/card-looks-4.json build/emu/state/card-looks-4-p.json p).
"""
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cli" / "src"))
from PIL import Image, ImageChops  # noqa: E402

from epm2mod.looks import lookfile, records  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

BUILD = "data/builds/card-looks-4.json"
STATE = ROOT / "build/emu/state/card-looks-4-p.json"
OUT = ROOT / "web/packages/ui/src/previews"
CROP = (0, 356, 720, 480)
#: the inside of the name box in the strip (the box is x 155-564, y 7-45; the names fall in x 274-445, y 17-41)
NAME = (160, 12, 560, 44)
BOX = (18, 18, 18)
NAV = ("key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT " + "key:DOWN " * 9 + "key:RIGHT " +
       "key:DOWN " * 5).split()
LOAD = NAV + ["key:RIGHT", "key:DOWN", "key:OK", "w:800", "key:MENU", "key:MENU", "w:800"]
# the strip opens at the current Picture Mode (Natural in the state); ART 1 is five steps to the right
STRIP = ["key:OK", "w:300", "key:UP"] + ["key:RIGHT"] * 5 + ["shot:art1"]
for n in range(2, 13):
    STRIP += ["key:RIGHT", "shot:art%d" % n]


def render(film_id):
    paths = RepoPaths(ROOT)
    looks = records.looks_of_choices(records.load(paths), ["ART%d=%s" % (n, film_id) for n in range(1, 13)])
    with tempfile.TemporaryDirectory() as tmp:
        card = Path(tmp, "card")
        (card / "DCIM" / "100OLYMP").mkdir(parents=True)
        (card / lookfile.CARD_NAME).write_bytes(lookfile.pack(looks))
        state = Path(tmp, "state.json")
        shutil.copy(STATE, state)
        shots = Path(tmp, "shots")
        env = dict(os.environ, E101_STATE=str(state), E101_CARD=str(card), E101_RTC="2026-11-17T12:00:00")
        out = subprocess.run([str(ROOT / "emulator/emu-run"), BUILD, "play.mjs", str(shots), *LOAD, *STRIP],
                             cwd=ROOT, env=env, capture_output=True, text=True)
        if out.returncode:
            raise SystemExit("%s: emulator exit %d %s" % (film_id, out.returncode, out.stdout[-300:]))
        return [Image.open(shots / ("art%d.png" % n)).convert("RGB").crop(CROP) for n in range(1, 13)]


def outside_name(strip):
    """The strip with the inside of the name box blanked."""
    out = strip.copy()
    out.paste(BOX, NAME)
    return out


def save(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.quantize(64).save(path, optimize=True)


if __name__ == "__main__":
    ids = list(records.load(RepoPaths(ROOT)).films)
    with ThreadPoolExecutor(max_workers=4) as pool:
        strips = dict(zip(ids, pool.map(render, ids)))
    first = strips[ids[0]]
    for film_id, shots in strips.items():
        for n, strip in enumerate(shots, start=1):
            if ImageChops.difference(outside_name(strip), outside_name(first[n - 1])).getbbox():
                raise SystemExit("%s ART %d: the strip differs outside the name box" % (film_id, n))
            if ImageChops.difference(strip.crop(NAME), shots[0].crop(NAME)).getbbox():
                raise SystemExit("%s ART %d: the name differs from ART 1" % (film_id, n))
        save(shots[0].crop(NAME), OUT / "name" / ("%s.png" % film_id))
        print("%s: name" % film_id, flush=True)
    for n, strip in enumerate(first, start=1):
        save(outside_name(strip), OUT / "menu" / ("art%d.png" % n))
    print("12 menu strips", flush=True)

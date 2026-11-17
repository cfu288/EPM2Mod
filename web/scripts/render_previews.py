"""Render the camera's Picture Mode strip for every film in every ART slot, with the emulator.

    uv run python web/scripts/render_previews.py [FILM_ID ...]

For each film of looks/catalogue.json: boots the pinned build (card-looks-4) in the boot lab with a card whose
EPM2LOOK.BIN holds that film in all 12 entries, loads it (MENU -> Custom Menu -> J -> Load Looks -> Load), opens
the Picture Mode strip (OK, UP) and takes a screenshot at ART 1 to ART 12. The strip at the bottom of each screen
(y 356-480: the name box and the ART icons) is saved as web/public/previews/<film>/art<N>.png. The web app shows
these as the preview, so the preview is the camera's own drawing.

Needs the emulator (tools/emu/setup.sh), build/card-looks-4.BIN and the state build/emu/state/card-looks-4-p.json
(tools/emu/mkstate builds/card-looks-4.json build/emu/state/card-looks-4-p.json p).
"""
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from PIL import Image  # noqa: E402

from epm2mod.looks import lookfile, lookpack  # noqa: E402
from epm2mod.paths import RepoPaths  # noqa: E402

BUILD = "builds/card-looks-4.json"
STATE = ROOT / "build/emu/state/card-looks-4-p.json"
OUT = ROOT / "web/public/previews"
CROP = (0, 356, 720, 480)
NAV = ("key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT " + "key:DOWN " * 9 + "key:RIGHT " +
       "key:DOWN " * 5).split()
LOAD = NAV + ["key:RIGHT", "key:DOWN", "key:OK", "w:800", "key:MENU", "key:MENU", "w:800"]
# the strip opens at the current Picture Mode (Natural in the state); ART 1 is five steps to the right
STRIP = ["key:OK", "w:300", "key:UP"] + ["key:RIGHT"] * 5 + ["shot:art1"]
for n in range(2, 13):
    STRIP += ["key:RIGHT", "shot:art%d" % n]


def render(film_id):
    paths = RepoPaths(ROOT)
    looks = lookpack.looks_of_choices(paths, ["ART%d=%s" % (n, film_id) for n in range(1, 13)])
    with tempfile.TemporaryDirectory() as tmp:
        card = Path(tmp, "card")
        (card / "DCIM" / "100OLYMP").mkdir(parents=True)
        (card / lookfile.CARD_NAME).write_bytes(lookfile.pack(looks))
        state = Path(tmp, "state.json")
        shutil.copy(STATE, state)
        shots = Path(tmp, "shots")
        env = dict(os.environ, E101_STATE=str(state), E101_CARD=str(card), E101_RTC="2026-11-17T12:00:00")
        out = subprocess.run([str(ROOT / "tools/emu/emu-run"), BUILD, "play.mjs", str(shots), *LOAD, *STRIP],
                             cwd=ROOT, env=env, capture_output=True, text=True)
        if out.returncode:
            return "%s: emulator exit %d %s" % (film_id, out.returncode, out.stdout[-300:])
        dest = OUT / film_id
        dest.mkdir(parents=True, exist_ok=True)
        for n in range(1, 13):
            Image.open(shots / ("art%d.png" % n)).crop(CROP).quantize(64).save(dest / ("art%d.png" % n),
                                                                             optimize=True)
    return "%s: 12 previews" % film_id


if __name__ == "__main__":
    ids = sys.argv[1:] or list(lookpack.load_catalogue(RepoPaths(ROOT)))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for line in pool.map(render, ids):
            print(line, flush=True)

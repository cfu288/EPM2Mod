"""Make the photos of the site's film comparison: one scene per RAW, one photo per look the camera developed it with.

    uv run python web/scripts/film_photos.py

Reads the camera JPEGs of experiments/2026-11-09-film-portra/shots: the eight scenes of filmsimcompare/, each in
Natural and the first seven films, and the gallery RAW in every look of the twelve-film build (PB160NNN.JPG). A
scene is the files with one capture time (RAW Data Edit keeps the RAW's); the look is the Olympus ArtFilter tag.
The camera writes "Pop Art" for the five newer looks, so those files are named by number (as make_readme_sheet.py
does).

Writes web/apps/site/public/films/<scene>/<look>.webp (1600 px on the long side, no metadata) and
web/apps/site/src/filmPhotos.json: the scenes in order, each with its looks in film order.
"""
import json
import struct
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "experiments/2026-11-09-film-portra/shots"
OUT = ROOT / "web/apps/site/public/films"
MANIFEST = ROOT / "web/apps/site/src/filmPhotos.json"
LONG_SIDE = 1600

# ArtFilter value -> the look the first build put there (looks/film-records.json slots, Off = Natural).
BY_FILTER = {0: "natural", 2: "portra-400", 1: "ektachrome", 3: "pro-400h", 4: "kodachrome", 5: "vision3-250d",
             9: "velvia", 10: "superia-400"}
GALLERY = {131: "natural", 119: "portra-400", 120: "ektachrome", 121: "pro-400h", 122: "kodachrome",
           135: "double-x", 123: "vision3-250d", 124: "velvia", 125: "superia-400", 127: "provia",
           128: "portra-160", 129: "gold-200", 130: "vision3-500t"}
ORDER = ["natural", "portra-400", "ektachrome", "pro-400h", "kodachrome", "double-x", "vision3-250d", "velvia",
         "superia-400", "provia", "portra-160", "gold-200", "vision3-500t"]


def _ifd(buf: bytes, off: int):
    for i in range(struct.unpack_from("<H", buf, off)[0]):
        yield struct.unpack_from("<HHII", buf, off + 2 + 12 * i)


def art_filter(maker_note: bytes) -> int:
    """The ArtFilter of an Olympus maker note (CameraSettings 0x2020, tag 0x0529); offsets count from its start."""
    if maker_note[:8] != b"OLYMPUS\0":
        raise ValueError("not an Olympus maker note")
    for tag, _, _, value in _ifd(maker_note, 12):
        if tag == 0x2020:
            for tag2, _, _, value2 in _ifd(maker_note, value):
                if tag2 == 0x0529:
                    return struct.unpack_from("<H", maker_note, value2)[0]
    raise ValueError("no ArtFilter")


def scenes() -> list[dict[str, Path]]:
    by_time: dict[str, dict[str, Path]] = {}
    for path in sorted((SHOTS / "filmsimcompare").glob("*.JPG")):
        exif = Image.open(path).getexif().get_ifd(0x8769)
        by_time.setdefault(exif[0x9003], {})[BY_FILTER[art_filter(exif[0x927C])]] = path
    gallery = {look: SHOTS / f"PB160{n}.JPG" for n, look in GALLERY.items()}
    # the gallery scene first: it has all thirteen looks
    return [gallery] + [by_time[t] for t in sorted(by_time)]


def main() -> None:
    manifest = []
    for i, looks in enumerate(scenes(), 1):
        scene = f"scene-{i}"
        (OUT / scene).mkdir(parents=True, exist_ok=True)
        entry = {"id": scene, "looks": {}}
        for look in [l for l in ORDER if l in looks]:
            im = ImageOps.exif_transpose(Image.open(looks[look])).convert("RGB")
            im.thumbnail((LONG_SIDE, LONG_SIDE), Image.LANCZOS)
            im.save(OUT / scene / f"{look}.webp", "WEBP", quality=80, method=6)
            entry["looks"][look] = f"films/{scene}/{look}.webp"
            entry["width"], entry["height"] = im.size
        manifest.append(entry)
        print(scene, len(entry["looks"]), "looks", entry["width"], "x", entry["height"])
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()

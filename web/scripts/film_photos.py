"""Make the photos of the site's film comparison: one scene per RAW, one photo per film simulation.

    uv run python web/scripts/film_photos.py

Reads the camera JPEGs in .local/site-photos/ (local only: RAW Data Edit -> ART BKT on the site RAWs of
.local/raws/site/, one folder per film file; batches.json lists each file's films in ART order). A run of ART BKT
writes the Natural frame, then one frame per ART entry in menu order, so a frame is named by its place in the run: the
EXIF says Natural for all of them. A scene is the files with one capture time (RAW Data Edit keeps the RAW's).
batch-1b holds batch 1's run of PA280187; trix-n3 holds Tri-X alone, developed again after its fit was corrected.

Writes web/apps/site/public/films/<scene>/<look>.webp (1600 px on the long side, no metadata), a 320 px thumb.webp
of the Natural photo, and web/apps/site/src/filmPhotos.json: the scenes in order, each with its looks in catalogue
order.
"""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / ".local/site-photos"
OUT = ROOT / "web/apps/site/public/films"
MANIFEST = ROOT / "web/apps/site/src/filmPhotos.json"
LONG_SIDE = 1600
THUMB = 320

# Capture time of each site RAW, in the site's scene order (.local/raws/README.md); PA280249 is not on the site.
SCENES = ["2026:03:29 14:45:20", "2026:03:25 21:24:32", "2026:03:26 14:45:35", "2026:03:26 15:02:02",
          "2026:03:26 16:49:58", "2026:03:26 18:25:36", "2026:05:29 16:06:33", "2026:10:28 16:56:28",
          "2026:10:30 19:33:23"]
# folder -> the film file whose ART order its runs follow (None: every frame is Tri-X)
RUNS = {"batch-1": "1", "batch-1b": "1", "batch-2": "2", "batch-3": "3", "trix-n3": None}
ORDER = ["natural"] + [f["id"] for f in json.loads((ROOT / "data/films/catalogue.json").read_text())["films"]]


def capture_times(folder: Path) -> dict[str, list[Path]]:
    """The folder's JPEGs grouped by EXIF DateTimeOriginal, each group in file order."""
    files = sorted(folder.glob("*.JPG"))
    out = subprocess.run(["exiftool", "-q", "-T", "-DateTimeOriginal", *map(str, files)], capture_output=True,
                         text=True, check=True).stdout.splitlines()
    groups: dict[str, list[Path]] = {}
    for path, time in zip(files, out, strict=True):
        groups.setdefault(time, []).append(path)
    return groups


def monochrome(path: Path) -> bool:
    im = Image.open(path)
    im.draft("RGB", (400, 300))
    mean = ImageStat.Stat(im.convert("RGB")).mean
    return max(mean) - min(mean) < 2


def scenes() -> list[dict[str, Path]]:
    batches = json.loads((SHOTS / "batches.json").read_text())
    looks: dict[str, dict[str, Path]] = {t: {} for t in SCENES}
    for folder, batch in RUNS.items():
        for time, frames in capture_times(SHOTS / folder).items():
            if time not in looks:
                continue
            if batch is None:
                looks[time]["tri-x"] = frames[0]          # replaces batch 2's Tri-X (the old fit); repeats are equal
                continue
            films = batches[batch]
            assert len(frames) == 13, f"{folder} {time}: {len(frames)} frames, ART BKT gives 13"
            looks[time].setdefault("natural", frames[0])
            for film, frame in zip(films, frames[1:]):
                looks[time].setdefault(film, frame)
    for time, scene in looks.items():
        assert set(scene) == set(ORDER), f"{time}: missing {set(ORDER) - set(scene)}"
        assert monochrome(scene["double-x"]) and monochrome(scene["tri-x"]), f"{time}: a black-and-white film in colour"
    return [looks[t] for t in SCENES]


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
            if look == "natural":
                im.thumbnail((THUMB, THUMB), Image.LANCZOS)
                im.save(OUT / scene / "thumb.webp", "WEBP", quality=80, method=6)
                entry["thumb"] = f"films/{scene}/thumb.webp"
        manifest.append(entry)
        print(scene, len(entry["looks"]), "looks", entry["width"], "x", entry["height"])
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()

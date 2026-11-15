"""Build the film look A/B page from a folder of camera JPEGs.

    ../../.venv/bin/python -I build.py PHOTOS [--scenes scenes.json] [--out out] [--size 1200]

PHOTOS holds the same pictures developed with each look in the camera (RAW Data Edit keeps the
RAW's capture time). The script groups the files into scenes by capture time and finds the look
of each file from the EXIF art filter, as ../2026-11-09-film-portra/make_comparison.py does.

It writes OUT/index.html, OUT/ranking.js, OUT/app.js, OUT/config.json and OUT/img/sN_LOOK.jpg.
The pictures are made smaller and are written without metadata (no owner name, no serial
number, no place). Publish the folder as it is: the page reads config.json and img/ beside it.

Needs exiftool and Pillow. The output folder is not for the repository (.gitignore).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
PAGE_FILES = ("index.html", "ranking.js", "app.js")

# EXIF ArtFilter value -> (key in file names, film name, name in the camera menu).
# The mod puts each film look in the menu entry of one stock art filter (docs/guide/film-looks.md).
LOOKS = {
    "Off": ("natural", "Natural", "Natural"),
    "Pop Art": ("portra", "Portra 400", "Portra"),
    "Soft Focus": ("ektachrome", "Ektachrome 100", "Ektachrome"),
    "Pale & Light Color": ("pro400h", "Fuji Pro 400H", "Pro 400H"),
    "Light Tone": ("kodachrome", "Kodachrome 64", "Kodachrome"),
    "Pin Hole": ("vis250d", "Vision3 250D", "Vis 250D"),
    "Diorama": ("velvia", "Velvia 100", "Velvia"),
    "Cross Process": ("superia", "Superia X-tra 400", "Superia 400"),
}


class BuildError(Exception):
    """A problem with the input that the user can correct."""


def read_metadata(photos: Path) -> list[dict[str, str]]:
    """Return the art filter and the capture time of each JPEG in a folder."""
    command = ["exiftool", "-j", "-ArtFilter", "-DateTimeOriginal", "-ext", "JPG", str(photos)]
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise BuildError("exiftool is not installed") from None
    if not done.stdout.strip():
        raise BuildError(f"{photos}: exiftool found no JPEG file")
    rows: list[dict[str, str]] = json.loads(done.stdout)
    return rows


def group_scenes(rows: list[dict[str, str]]) -> list[dict[str, Path]]:
    """Group the files into scenes, oldest first: one {look key: file} for each capture time."""
    scenes: dict[str, dict[str, Path]] = collections.defaultdict(dict)
    for row in rows:
        art_filter = str(row.get("ArtFilter", "")).split(";")[0]
        taken = row.get("DateTimeOriginal")
        if art_filter not in LOOKS or not taken:
            print(f"skipped {row['SourceFile']}: art filter {art_filter!r}, time {taken!r}", file=sys.stderr)
            continue
        scenes[taken][LOOKS[art_filter][0]] = Path(row["SourceFile"])
    return [scenes[taken] for taken in sorted(scenes)]


def read_scene_notes(path: Path, count: int) -> list[dict[str, object]]:
    """Return the name and the situation tags of each scene, in the order of capture time."""
    notes: list[dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
    if len(notes) != count:
        raise BuildError(f"{path} describes {len(notes)} scenes, the photo folder has {count}")
    for index, note in enumerate(notes, 1):
        if (
            not isinstance(note.get("name"), str)
            or not isinstance(note.get("tags"), list)
            or not note["tags"]
        ):
            raise BuildError(f"{path}: scene {index} needs a 'name' and a list 'tags' with one tag or more")
    return notes


def write_picture(source: Path, target: Path, size: int) -> tuple[int, int]:
    """Write a smaller copy with the right side up and no metadata. Return its width and height."""
    with Image.open(source) as opened:
        picture = ImageOps.exif_transpose(opened).convert("RGB")
    picture.thumbnail((size, size), Image.Resampling.LANCZOS)
    picture.save(target, "JPEG", quality=84, optimize=True)  # Pillow writes no EXIF unless asked
    return picture.size


def build(photos: Path, scene_notes: Path, out: Path, size: int, title: str) -> None:
    """Write the page, its pictures and config.json to ``out``."""
    scenes = group_scenes(read_metadata(photos))
    if not scenes:
        raise BuildError(f"{photos}: no JPEG with a known art filter and a capture time")
    notes = read_scene_notes(scene_notes, len(scenes))
    keys = [key for key, _, _ in LOOKS.values()]
    for index, files in enumerate(scenes, 1):
        missing = [key for key in keys if key not in files]
        if missing:
            raise BuildError(
                f"scene {index} ({notes[index - 1]['name']}) has no picture for: {', '.join(missing)}"
            )

    (out / "img").mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    config_scenes = []
    for index, (files, note) in enumerate(zip(scenes, notes), 1):
        width = height = 0
        for key in keys:
            target = out / "img" / f"s{index}_{key}.jpg"
            width, height = write_picture(files[key], target, size)
            digest.update(target.read_bytes())
        config_scenes.append(
            {"id": index, "name": note["name"], "wide": width > height, "tags": note["tags"]}
        )

    config = {
        "title": title,
        "id": digest.hexdigest()[:12],  # the page keeps the votes of each photo set apart by this
        "looks": [{"key": key, "name": name, "menu": menu} for key, name, menu in LOOKS.values()],
        "scenes": config_scenes,
    }
    (out / "config.json").write_text(json.dumps(config, indent=1) + "\n", encoding="utf-8")
    for name in PAGE_FILES:
        shutil.copyfile(HERE / "page" / name, out / name)
    megabytes = sum(f.stat().st_size for f in (out / "img").iterdir()) / 1e6
    print(f"wrote {out}: {len(scenes)} scenes x {len(keys)} looks, pictures {megabytes:.1f} MB")


def main() -> int:
    """Run the command line."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("photos", type=Path, help="folder with the camera JPEGs")
    parser.add_argument(
        "--scenes", type=Path, default=HERE / "scenes.json", help="names and tags of the scenes"
    )
    parser.add_argument("--out", type=Path, default=HERE / "out", help="output folder")
    parser.add_argument("--size", type=int, default=1200, help="longest side of a picture, in pixels")
    parser.add_argument("--title", default="Film Look A/B", help="title of the page")
    args = parser.parse_args()
    try:
        build(args.photos, args.scenes, args.out, args.size, args.title)
    except BuildError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

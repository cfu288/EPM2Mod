#!/usr/bin/env python3
"""sheets.py RUNDIR OUTDIR: contact sheets and checks of a lang-all.sh run.

RUNDIR = lang-all/IMAGE (one folder NN-CODE per language). Writes into OUTDIR:
  picture-mode-N.png  per language the two pages of the Picture Mode list (12 languages a page)
  art-list-N.png      per language the titles of ART entries 1..8 and the first page of the ART BKT list
  effects.png         per language the titles of the first two effects of Add Effects (ids 764, 765)
  live-control-N.png  per language the name bar of the live control for ART 1..8 (if live-control.sh IMAGE all ran)
  names.txt           per language: are the film-name rows pixel-equal to the English run's rows
Needs Pillow.
"""
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

run, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
langs = sorted(p for p in run.iterdir() if p.is_dir())
LIST = (40, 70, 700, 410)      # the seven rows of a list page
TITLE = (100, 4, 720, 52)      # the title of an ART list screen
ROW0, ROWH = 74, 48            # first list row and row height


def half(im):
    return im.resize((im.width // 2, im.height // 2), Image.LANCZOS)


def tile(label, parts, width):
    """Stack a label and images (left to right) into one tile."""
    h = max(p.height for p in parts) + 14
    t = Image.new("RGB", (width, h), (0, 0, 0))
    ImageDraw.Draw(t).text((2, 1), label, fill=(255, 255, 0))
    x = 0
    for p in parts:
        t.paste(p, (x, 14))
        x += p.width
    return t


def pages(name, tiles, cols=2, per=12):
    for n in range(0, len(tiles), per):
        chunk = tiles[n:n + per]
        w, h = chunk[0].size
        rows = -(-len(chunk) // cols)
        sheet = Image.new("RGB", (w * cols, h * rows), (0, 0, 0))
        for k, t in enumerate(chunk):
            sheet.paste(t, (w * (k % cols), h * (k // cols)))
        sheet.save(out / f"{name}-{n // per + 1}.png")


def strip(folder, shot, box):
    return Image.open(folder / f"{shot}.png").convert("RGB").crop(box)


pm, art, fx, report = [], [], [], []
english = next(p for p in langs if p.name.endswith("enu"))
# rows of the film names: (shot, box). Picture Mode page 1 rows 1-4, 6, 7; page 2 row 1; ART titles 1-4, 6-8
checks = [("pm-1", (60, ROW0 + ROWH * r, 660, ROW0 + ROWH * (r + 1))) for r in (0, 1, 2, 3, 5, 6)]
checks += [("pm-2", (60, ROW0, 660, ROW0 + ROWH))]
checks += [(f"art-{n:02d}", TITLE) for n in (1, 2, 3, 4, 6, 7, 8)]
checks += [("bkt-1", (60, ROW0 + ROWH * r, 500, ROW0 + ROWH * (r + 1))) for r in (1, 2, 3, 5, 6)]
for folder in langs:
    label = folder.name
    pm.append(tile(label, [half(strip(folder, "pm-1", LIST)), half(strip(folder, "pm-2", LIST))], 660))
    titles = Image.new("RGB", (310, 24 * 8))
    for n in range(8):
        titles.paste(half(strip(folder, f"art-{n + 1:02d}", TITLE)), (0, 24 * n))
    art.append(tile(label, [titles, half(strip(folder, "bkt-1", LIST))], 660))
    both = Image.new("RGB", (310, 48))
    both.paste(half(strip(folder, "fx-1", TITLE)), (0, 0))
    both.paste(half(strip(folder, "fx-2", TITLE)), (0, 24))
    fx.append(tile(label, [both], 330))
    differ = [shot + ("" if box == TITLE else f" row {(box[1] - ROW0) // ROWH + 1}") for shot, box in checks
              if ImageChops.difference(strip(folder, shot, box), strip(english, shot, box)).getbbox()]
    report.append(f"{label}: " + ("all 19 film-name strips equal to English" if not differ else "DIFFER: " + ", ".join(differ)))
pages("picture-mode", pm)
pages("art-list", art)
pages("effects", fx, cols=4, per=36)
(out / "names.txt").write_text("\n".join(report) + "\n")
print("\n".join(report))

# live control (live-control.sh IMAGE all): the name bar of the strip for ART 1..8, per language
if all((f / "lc-12.png").exists() for f in langs):
    BAR = (150, 360, 570, 404)
    lc = []
    for folder in langs:
        bars = Image.new("RGB", (210, 22 * 8))
        for n in range(8):
            bars.paste(half(strip(folder, f"lc-{n + 5:02d}", BAR)), (0, 22 * n))
        lc.append(tile(folder.name, [bars], 220))
    pages("live-control", lc, cols=6, per=36)

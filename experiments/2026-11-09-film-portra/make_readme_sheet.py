"""Make docs/images/film-sim-comparison.jpg: one row per scene, one column per look, then the newer looks.

    ../../.venv/bin/python -I make_readme_sheet.py

Rows: the eight scenes of shots/filmsimcompare/ (found by capture time and EXIF art filter, as make_comparison.py
does) and the gallery RAW that was developed in every look of the twelve-film build (shots/PB160NNN.JPG). The five
looks that the first eight scenes were not developed with are shown below, with the gallery photo. The camera
writes "Pop Art" as the art filter of the newer looks, so their files are named by number here (matched by the
EXIF ColorMatrix of each file, camera log of 2026-11-16). The pictures are written small and without metadata.
"""
import collections, json, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageOps

LOOKS = [("Off", "Natural", "Standard mode"), ("Pop Art", "Portra 400", "Portra 400"), ("Soft Focus", "Ektachrome 100", "Ektachrome"),
         ("Pale & Light Color", "Fuji Pro 400H", "Pro 400H"), ("Light Tone", "Kodachrome 64", "Kodachrome"), ("Pin Hole", "Vision3 250D", "Vis 250D"),
         ("Diorama", "Velvia 100", "Velvia"), ("Cross Process", "Superia X-tra 400", "Superia 400")]
GALLERY = {"Off": 131, "Pop Art": 119, "Soft Focus": 120, "Pale & Light Color": 121, "Light Tone": 122, "Pin Hole": 123, "Diorama": 124, "Cross Process": 125}
NEWER = [(135, "Double-X 5222", "Double-X"), (127, "Provia 100F", "Provia"), (128, "Portra 160", "Portra 160"), (129, "Gold 200", "Gold 200"), (130, "Vision3 500T", "Vis 500T")]
OUT = "../../docs/images/film-sim-comparison.jpg"
W, GAP, M, HEAD, CAP = 300, 10, 30, 96, 22

shot = lambda n: f"shots/PB160{n}.JPG"
font = lambda s, b=False: ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if b else ''}.ttf", s)
load = lambda p: ImageOps.exif_transpose(Image.open(p)).convert("RGB")
meta = json.loads(subprocess.run(["exiftool", "-j", "-ArtFilter", "-DateTimeOriginal", "-ext", "JPG", "shots/filmsimcompare"], capture_output=True, text=True).stdout)
scenes = collections.defaultdict(dict)
for m in meta:
    scenes[m["DateTimeOriginal"]][m["ArtFilter"].split(";")[0]] = m["SourceFile"]
scenes["2026:03:29 14:45:20"] = {key: shot(n) for key, n in GALLERY.items()}
rows = []
for t in sorted(scenes):
    ims = {k: load(p) for k, p in scenes[t].items()}
    rows.append((ims, max(round(W * i.height / i.width) for i in ims.values())))
newer = [load(shot(n)) for n, _, _ in NEWER]
nh = round(W * newer[0].height / newer[0].width)
width = 2 * M + len(LOOKS) * W + (len(LOOKS) - 1) * GAP
height = M + HEAD + sum(h + CAP + GAP for _, h in rows) + 70 + nh + CAP + M
page = Image.new("RGB", (width, height), "white"); d = ImageDraw.Draw(page)
d.text((M, M - 8), "Adding film emulations to the Olympus E-PM2 using custom firmware", font=font(26, True), fill="black")
d.text((M, M + 28), 'Each row is one RAW file developed in the camera with every look. The first column is the default "Natural" profile in camera.', font=font(13), fill=(90, 90, 90))
y = M + HEAD
for c, (_, name, label) in enumerate(LOOKS):
    x = M + c * (W + GAP)
    d.text((x + W / 2, y - 28), name, font=font(16, True), fill="black", anchor="mm")
    d.text((x + W / 2, y - 10), f"Menu name: {label}" if c else label, font=font(11), fill=(110, 110, 110), anchor="mm")
for ims, h in rows:
    for c, (key, name, _) in enumerate(LOOKS):
        x = M + c * (W + GAP)
        if key in ims:
            th = ims[key].resize((W, round(W * ims[key].height / ims[key].width)), Image.LANCZOS)
            page.paste(th, (x, y + (h - th.height) // 2))
        d.text((x + W / 2, y + h + CAP / 2), name, font=font(11), fill=(60, 60, 60), anchor="mm")
    y += h + CAP + GAP
d.text((M, y + 14), "Five more looks", font=font(20, True), fill="black")
d.text((M, y + 42), "The gallery photo above, developed with the looks that were added later. Double-X is black-and-white.", font=font(13), fill=(90, 90, 90))
y += 70
for c, (im, (_, name, label)) in enumerate(zip(newer, NEWER)):
    x = M + c * (W + GAP)
    page.paste(im.resize((W, nh), Image.LANCZOS), (x, y))
    d.text((x + W / 2, y + nh + CAP / 2), f"{name}  (menu name: {label})", font=font(11), fill=(60, 60, 60), anchor="mm")
page.save(OUT, quality=86, optimize=True)
print("wrote", OUT, page.size, len(rows), "scenes")

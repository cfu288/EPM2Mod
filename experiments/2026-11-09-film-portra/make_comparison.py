"""Contact sheet of the film looks: one row per scene, one column per look, labels on a white grid.

Reads camera JPEGs from a folder, groups them by capture time (RAW Data Edit keeps the RAW's DateTimeOriginal) and
orders the columns by art filter (EXIF ArtFilter).   ../../.venv/bin/python -I make_comparison.py FOLDER [OUT.pdf]"""
import collections, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
LOOKS = [("Off", "Natural", "Standard mode"), ("Pop Art", "Portra 400", "Portra"), ("Soft Focus", "Ektachrome 100", "Ektachrome"), ("Pale & Light Color", "Fuji Pro 400H", "Pro 400H"),
         ("Light Tone", "Kodachrome 64", "Kodachrome"), ("Pin Hole", "Vision3 250D", "Vis 250D"), ("Diorama", "Velvia 100", "Velvia"), ("Cross Process", "Superia X-tra 400", "Superia 400")]
folder = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(folder, "film-sim-comparison.pdf")
meta = json.loads(subprocess.run(["exiftool", "-j", "-ArtFilter", "-DateTimeOriginal", "-ext", "JPG", folder], capture_output=True, text=True).stdout)
scenes = collections.defaultdict(dict)
for m in meta: scenes[m["DateTimeOriginal"]][m["ArtFilter"].split(";")[0]] = m["SourceFile"]
W, GAP, M, HEAD, CAP = 900, 28, 90, 260, 64                       # cell width, gap, margin, header height, caption height (pixels; 300 per inch)
font = lambda s, b=False: ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if b else ''}.ttf", s)
rows = []
for t in sorted(scenes):
    ims = {k: ImageOps.exif_transpose(Image.open(p)).convert("RGB") for k, p in scenes[t].items()}
    h = max(round(W * im.height / im.width) for im in ims.values()); rows.append((t, ims, h))
width = 2 * M + len(LOOKS) * W + (len(LOOKS) - 1) * GAP; height = 2 * M + HEAD + sum(h + CAP + GAP for _, _, h in rows)
page = Image.new("RGB", (width, height), "white"); d = ImageDraw.Draw(page)
d.text((M, M - 20), "Adding film emulations to the Olympus E-PM2 using custom firmware", font=font(64, True), fill="black")
d.text((M, M + 62), "Below are some additional optional emulations you can apply in camera to your shots. The first column is the default \"Natural\" profile in camera.", font=font(30), fill=(90, 90, 90))
y = M + HEAD
for c, (_, name, label) in enumerate(LOOKS):
    x = M + c * (W + GAP); d.text((x + W / 2, y - 62), name, font=font(40, True), fill="black", anchor="mm"); d.text((x + W / 2, y - 22), f"Menu name: {label}" if c else label, font=font(26), fill=(110, 110, 110), anchor="mm")
for r, (t, ims, h) in enumerate(rows):
    for c, (key, name, _) in enumerate(LOOKS):
        x = M + c * (W + GAP)
        if key in ims:
            im = ims[key]; th = im.resize((W, round(W * im.height / im.width)), Image.LANCZOS); page.paste(th, (x, y + (h - th.height) // 2))
        else: d.rectangle([x, y, x + W, y + h], outline=(200, 200, 200)); d.text((x + W / 2, y + h / 2), "No picture", font=font(28), fill=(150, 150, 150), anchor="mm")
        d.text((x + W / 2, y + h + CAP / 2 - 6), name, font=font(28), fill=(60, 60, 60), anchor="mm")
    y += h + CAP + GAP
page.save(out, "PDF", resolution=300.0, quality=90)
if os.environ.get("PREVIEW"): page.resize((page.width // 5, page.height // 5), Image.LANCZOS).save(os.environ["PREVIEW"], quality=85)
print("wrote", out, page.size, f"{os.path.getsize(out) / 1e6:.1f} MB;", len(rows), "scenes x", len(LOOKS), "looks")

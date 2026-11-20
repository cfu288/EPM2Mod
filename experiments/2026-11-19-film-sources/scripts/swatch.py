"""swatch.py OUT.png LABEL=CUBE ...: one row per target LUT: the 24 ColorChecker patches and a 9-step grey ramp (-4..+4 EV)."""
import sys, os, numpy as np, colour
from PIL import Image, ImageDraw, ImageFont
exec(open(os.path.join(os.path.dirname(__file__), "cmp.py")).read().split("sets = ")[0].replace("import sys, numpy as np, colour", ""))
ramp9 = np.repeat((0.18 * 2.0 ** np.arange(-4, 5))[:, None], 3, 1)
def srgb(path, lin):
    lut = colour.read_LUT(path)
    v = colour.RGB_to_RGB(lin, colour.RGB_COLOURSPACES["sRGB"], vgamut, chromatic_adaptation_transform=None)
    return np.clip(lut.apply(colour.models.log_encoding_VLog(np.maximum(v, 0))), 0, 1)
rows = [a.split("=", 1) for a in sys.argv[2:]]
P, L = 30, 250
img = Image.new("RGB", (L + 33 * P + 10, len(rows) * (P + 6) + 6), (255, 255, 255))
d = ImageDraw.Draw(img)
for r, (label, path) in enumerate(rows):
    y = 6 + r * (P + 6)
    d.text((6, y + 9), label, fill=(0, 0, 0))
    cols = np.vstack([srgb(path, lin_cc), srgb(path, ramp9)])
    for i, c in enumerate(cols):
        x = L + i * P + (8 if i >= 24 else 0)
        d.rectangle([x, y, x + P - 2, y + P - 1], fill=tuple(int(v * 255 + 0.5) for v in c))
img.save(sys.argv[1]); print(sys.argv[1], img.size)

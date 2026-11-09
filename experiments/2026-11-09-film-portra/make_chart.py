"""Monitor test chart for the film-look shoot (SHOTS.md).

36 hues x 6 saturation/value rows, one 36-step gray row, and white corner markers for
alignment, on a dark background. Show it full screen at 100 % (no scaling) and photograph it.
The colours need not be accurate: the analysis compares each ORF with its own JPEG, so the
chart only has to give many distinct, flat patches. Same idea as gr3-film-mods'
make_hue_chart.py (MIT); this is an independent stdlib-only version.

Usage:  python3 make_chart.py [WIDTH HEIGHT ...]    (default: 1920 1080 2560 1600 3840 2160)
Writes out/chart_<W>x<H>.png and out/chart_layout.json (patch boxes as fractions of the
image, so one layout serves every resolution).
"""
import colorsys
import json
import os
import struct
import sys
import zlib

BG = (40, 40, 40)
WHITE = (255, 255, 255)
HUES = 36
ROWS = [(1.0, 1.0), (0.6, 1.0), (0.3, 1.0), (1.0, 0.55), (0.6, 0.55), (0.3, 0.55)]  # (S, V)
GRAY_STEPS = 36
MARGIN = 0.06   # marker size and grid inset, as a fraction of the height
PAD = 0.08      # gap inside each cell, as a fraction of the smaller cell side


def patches():
    """All patches as (row, col, kind, rgb)."""
    out = []
    for r, (s, v) in enumerate(ROWS):
        for c in range(HUES):
            rgb = tuple(round(255 * x) for x in colorsys.hsv_to_rgb(c / HUES, s, v))
            out.append((r, c, "hue", rgb))
    for c in range(GRAY_STEPS):
        g = round(255 * c / (GRAY_STEPS - 1))
        out.append((len(ROWS), c, "gray", (g, g, g)))
    return out


def geometry(w, h):
    m = round(h * MARGIN)
    gx0, gy0, gx1, gy1 = 2 * m, 2 * m, w - 2 * m, h - 2 * m
    cw, ch = (gx1 - gx0) / HUES, (gy1 - gy0) / (len(ROWS) + 1)
    pad = max(2, round(min(cw, ch) * PAD))
    markers = [(m // 2, m // 2), (w - 3 * m // 2, m // 2),
               (m // 2, h - 3 * m // 2), (w - 3 * m // 2, h - 3 * m // 2)]
    return m, gx0, gy0, cw, ch, pad, markers


def boxes(w, h):
    """Pixel boxes [x0, y0, x1, y1) of every patch, plus the four markers."""
    m, gx0, gy0, cw, ch, pad, markers = geometry(w, h)
    out = []
    for r, c, kind, rgb in patches():
        x0 = round(gx0 + c * cw) + pad
        y0 = round(gy0 + r * ch) + pad
        x1 = round(gx0 + (c + 1) * cw) - pad
        y1 = round(gy0 + (r + 1) * ch) - pad
        out.append({"row": r, "col": c, "kind": kind, "rgb": rgb, "box": [x0, y0, x1, y1]})
    marks = [[x, y, x + m, y + m] for x, y in markers]
    return out, marks


def render(w, h):
    img = [bytearray(bytes(BG) * w) for _ in range(h)]
    pts, marks = boxes(w, h)
    for p in pts:
        x0, y0, x1, y1 = p["box"]
        seg = bytes(p["rgb"]) * (x1 - x0)
        for y in range(y0, y1):
            img[y][3 * x0:3 * x1] = seg
    for x0, y0, x1, y1 in marks:
        seg = bytes(WHITE) * (x1 - x0)
        for y in range(y0, y1):
            img[y][3 * x0:3 * x1] = seg
    return img


def write_png(path, img, w, h):
    raw = b"".join(b"\x00" + bytes(row) for row in img)

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def main(argv):
    sizes = [int(a) for a in argv] or [1920, 1080, 2560, 1600, 3840, 2160]
    if len(sizes) % 2:
        sys.exit("give WIDTH HEIGHT pairs")
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out")
    os.makedirs(out, exist_ok=True)
    layouts = {}
    for w, h in zip(sizes[::2], sizes[1::2]):
        path = os.path.join(out, f"chart_{w}x{h}.png")
        write_png(path, render(w, h), w, h)
        pts, marks = boxes(w, h)
        layouts[f"{w}x{h}"] = {"size": [w, h], "markers": marks, "patches": pts}
        print(path)
    with open(os.path.join(out, "chart_layout.json"), "w") as f:
        json.dump(layouts, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])

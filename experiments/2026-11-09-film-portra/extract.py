"""Shoot 1 extraction: every chart shot -> per-patch raw RGB and JPEG RGB.

For each ORF+JPG pair in shots/:
  1. find the chart's four white corner markers, separately in the JPEG and in the raw data
     (the camera corrects lens distortion in its JPEGs, so the two geometries differ);
  2. map every patch of the chart (out/chart_layout.json) into the photo with a homography (the
     raw is not corrected for lens distortion, so this is off by up to half a patch there); move
     each box to the flattest spot nearby (a first guess, smoothed with a cubic offset field); then
     find the dark gap lines between the patches, fit them as smooth curves, and centre every
     sampling box between the four lines around its patch (grid_quads);
  3. take the median over the central part of each patch:
       raw: camera RGB minus each file's own black level (255 at ISO 200, 253/254 at higher ISO) from the Bayer planes (G = mean of the two greens),
            plus a clip flag (any raw sample at the sensor's saturation, 4045);
       jpg: 8-bit sRGB values as decoded by Pillow;
  4. read the shot settings with exiftool.

Writes out/patches.npz, out/settings.json, out/gridlines.json (gap-line fit statistics per shot)
and, for checking by eye, out/overlay_<shot>.jpg, out/overlay_raw_<shot>.png and full-resolution
crops out/check_{raw,jpg}_<shot>.png with the sampling boxes drawn. Run with the project venv:

    ../../.venv/bin/python -I extract.py
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
import rawpy
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")
OUT = os.path.join(HERE, "out")
SAT = 4045           # sensor saturation in raw units (the nominal white level is 4095)
INNER_X, INNER_Y = 0.45, 0.5  # sampled box = central 45 % x 50 % of the cell between the gap lines
# (a patch fills ~87 % of its cell on screen; defocus blurs ~5 half-size raw px of a ~46 px cell)

# Shot roles from the shoot-1 log in SHOTS.md (file number -> id).
ROLES = {
    185: "B1", 186: "B2", 187: "B3", 188: "B4", 189: "B5",
    190: "M1-vivid", 191: "M2-muted", 192: "M3-portrait", 193: "M4-monotone", 194: "M5-ienhance",
    195: "G1-highkey", 196: "G2-lowkey", 197: "G3-auto",
    198: "N1-con-2", 199: "N1b-con-2", 200: "N3-sat-2", 201: "N4-sat+2", 202: "X-base2",
    203: "P1-con-2", 204: "P2-con+2", 205: "P3-sat-2", 206: "P4-sat+2",
    207: "A1-popart", 208: "X-softfocus", 209: "A2-palelight", 210: "A3-lighttone",
    211: "A4-crossprocess", 212: "I1-iso800", 213: "I2-iso3200", 214: "W1-cwb3200",
    215: "W2-awb", 216: "D1-base", 217: "B0a", 218: "B0b", 219: "B0c", 220: "N2-con+2",
    221: "X-base3",
}
EXIF_TAGS = ["FileName", "ExposureTime", "FNumber", "ISO", "WhiteBalance2",
             "WhiteBalanceTemperature", "PictureMode", "PictureModeContrast",
             "PictureModeSaturation", "PictureModeSharpness", "Gradation", "ArtFilterEffect",
             "WB_RBLevels", "ColorMatrix", "BlackLevel2", "FocalLength"]


# ---------- markers and geometry ----------

def _candidates(gray, thr):
    b = (gray > thr).astype(np.uint8)
    n, _, st, cen = cv2.connectedComponentsWithStats(b, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a >= 20 and 0.7 < w / h < 1.43 and a / (w * h) > 0.7:
            out.append((a, cen[i]))
    return out


def find_markers(gray):
    """Centres of the TL, TR, BL, BR markers in a small grayscale image, or None."""
    H, W = gray.shape
    p = np.percentile(gray, 99.9)
    for f in (0.5, 0.35, 0.25, 0.65, 0.8, 0.18, 0.12):
        c = _candidates(gray, f * p)
        if len(c) < 4:
            continue
        pts = np.array([z[1] for z in c])
        s, d = pts.sum(1), pts[:, 0] - pts[:, 1]
        idx = [s.argmin(), d.argmax(), d.argmin(), s.argmax()]
        if len(set(idx)) < 4:
            continue
        areas = np.array([c[i][0] for i in idx])
        q = pts[idx]
        if areas.max() > 2.2 * areas.min():
            continue
        if np.linalg.norm(q[1] - q[0]) < 0.4 * W or np.linalg.norm(q[2] - q[0]) < 0.3 * H:
            continue
        return q
    return None


def chart_points(layout):
    m = np.array(layout["markers"], float)          # [x0, y0, x1, y1] per marker, TL TR BL BR
    return np.stack([(m[:, 0] + m[:, 2]) / 2, (m[:, 1] + m[:, 3]) / 2], 1)


def inner_quads(layout, Hm):
    """Photo-space quadrilaterals of the sampled centre of every patch."""
    quads = []
    for p in layout["patches"]:
        x0, y0, x1, y1 = p["box"]
        cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * INNER_X / 2, (y1 - y0) * INNER_Y / 2
        sq = np.array([[cx - hw, cy - hh], [cx + hw, cy - hh], [cx + hw, cy + hh], [cx - hw, cy + hh]])
        quads.append(cv2.perspectiveTransform(sq[None].astype(np.float64), Hm)[0])
    return quads


def sample(planes, quad):
    """Per-plane median, 10th and 90th percentile and max inside a quadrilateral."""
    h, w = planes[0].shape
    x0, y0 = np.floor(quad.min(0)).astype(int)
    x1, y1 = np.ceil(quad.max(0)).astype(int) + 1
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mask, [np.round(quad - [x0, y0]).astype(np.int32)], 1)
    sel = mask.astype(bool)
    res = []
    for pl in planes:
        v = pl[y0:y1, x0:x1][sel]
        res.append((np.median(v), np.percentile(v, 10), np.percentile(v, 90), v.max(), v.size))
    return res


def _best_offsets(score_img, quads, rx, ry):
    """Per quad: the shift (within +-rx, +-ry) of the flattest box of the quad's size."""
    H, W = score_img.shape
    off = np.zeros((len(quads), 2))
    for i, q in enumerate(quads):
        bw = max(int(q[:, 0].max() - q[:, 0].min()), 3)
        bh = max(int(q[:, 1].max() - q[:, 1].min()), 3)
        cx, cy = np.round(q.mean(0)).astype(int)
        x0, y0 = max(cx - rx - bw, 0), max(cy - ry - bh, 0)
        x1, y1 = min(cx + rx + bw + 1, W), min(cy + ry + bh + 1, H)
        crop = score_img[y0:y1, x0:x1].astype(np.float64)
        m = cv2.boxFilter(crop, -1, (bw, bh), borderType=cv2.BORDER_REPLICATE)
        m2 = cv2.boxFilter(crop * crop, -1, (bw, bh), borderType=cv2.BORDER_REPLICATE)
        sd = np.sqrt(np.maximum(m2 - m * m, 0))
        eps = 0.01 * max(crop.max(), 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = xx - cx, yy - cy
        score = sd / (m + eps) + 0.02 * np.hypot(dx / max(rx, 1), dy / max(ry, 1))
        score[(np.abs(dx) > rx) | (np.abs(dy) > ry)] = np.inf
        j = np.unravel_index(np.argmin(score), score.shape)
        off[i] = [dx[j], dy[j]]
    return off


def refine(score_img, quads, ncols=36):
    """Move every quad onto its patch. The raw is not corrected for lens distortion, so the
    four-corner homography can be off by up to half a patch. Per patch, find the flattest spot
    nearby; fit a smooth cubic field to those shifts (robustly, distortion is smooth); apply it;
    then a final +-3 px search. Returns the shifted quads and the applied shifts."""
    cen = np.array([q.mean(0) for q in quads])
    grid = cen.reshape(-1, ncols, 2)
    pitch_x = np.median(np.linalg.norm(np.diff(grid, axis=1), axis=2))
    pitch_y = np.median(np.linalg.norm(np.diff(grid, axis=0), axis=2))
    off = _best_offsets(score_img, quads, int(0.45 * pitch_x), int(0.3 * pitch_y))
    u = (cen - cen.mean(0)) / cen.std(0)
    A = np.stack([u[:, 0] ** i * u[:, 1] ** j for i in range(4) for j in range(4 - i)], 1)
    w = np.ones(len(off))
    for _ in range(6):                                   # iteratively reweighted least squares
        coef = [np.linalg.lstsq(A * w[:, None], off[:, c] * w, rcond=None)[0] for c in (0, 1)]
        fit = np.stack([A @ coef[0], A @ coef[1]], 1)
        res = np.linalg.norm(off - fit, axis=1)
        s = max(np.median(res) * 1.5, 1.0)
        w = 1 / np.maximum(1, res / (2 * s))
    shifted = [q + fit[i] for i, q in enumerate(quads)]
    fine = _best_offsets(score_img, shifted, 3, 3)
    return [q + fine[i] for i, q in enumerate(shifted)], fit + fine


# ---------- image loading ----------

def _profile(img, along, centre, half, vertical_lines):
    """Brightness profile along a row (vertical_lines=True: positions x = along, row centre y =
    centre(x)) or a column (x = centre(y), y = along), median over +-half across it."""
    off = np.arange(-half, half + 1, dtype=np.float32)[None, :]
    a = along.astype(np.float32)[:, None] + 0 * off
    c = centre.astype(np.float32)[:, None] + off
    mx, my = (a, c) if vertical_lines else (c, a)
    vals = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return np.median(vals, axis=1)


def _valleys(prof, pitch, thr=0.05):
    """All gap valleys: local minima with relative contrast > 5 %, at least half a pitch apart.
    Returns [(sub-pixel index, relative contrast)]."""
    w = max(int(0.5 * pitch), 2)
    out = []
    for i in range(1, len(prof) - 1):
        if not (prof[i] < prof[i - 1] and prof[i] <= prof[i + 1]):
            continue
        left = prof[max(i - w, 0):i].max(initial=prof[i])
        right = prof[i + 1:i + w + 1].max(initial=prof[i])
        side = min(left, right)
        rel = (side - prof[i]) / max(side, 1e-6)
        if rel <= thr:
            continue
        a, b, c = prof[i - 1], prof[i], prof[i + 1]
        den = a - 2 * b + c
        frac = 0.5 * (a - c) / den if den > 0 else 0.0
        out.append((i + float(np.clip(frac, -0.5, 0.5)), rel))
    out.sort(key=lambda v: -v[1])                       # keep the deepest of any close pair
    kept = []
    for v in out:
        if all(abs(v[0] - u[0]) >= 0.5 * pitch for u in kept):
            kept.append(v)
    return sorted(kept)


def _track(valleys, preds, pitch, nlines):
    """Assign valleys to line indices 1..nlines-1 by walking outward from the middle line.
    preds[k] = first-guess position of line k. Returns {k: (pos, contrast)}."""
    pos = np.array([v[0] for v in valleys]) if valleys else np.zeros(0)
    found = {}

    def nearest(x, tol):
        if not len(pos):
            return None
        j = int(np.argmin(np.abs(pos - x)))
        return j if abs(pos[j] - x) <= tol else None

    mid = nlines // 2
    anchor = None
    for k in sorted(range(1, nlines), key=lambda k: abs(k - mid)):
        j = nearest(preds[k], 0.35 * pitch)
        if j is not None:
            anchor = k; found[k] = valleys[j]; break
    if anchor is None:
        return found
    for step in (1, -1):
        x_prev, spacing, k = found[anchor][0], pitch, anchor + step
        prev_found = True
        while 1 <= k < nlines:
            pred = x_prev + step * spacing
            j = nearest(pred, 0.3 * pitch)
            if j is not None:
                if prev_found:
                    spacing = 0.5 * spacing + 0.5 * abs(valleys[j][0] - x_prev)
                found[k] = valleys[j]; x_prev = valleys[j][0]; prev_found = True
            else:
                x_prev = pred; prev_found = False
            k += step
    return found


def _fit_lines(pts, deg_line=3, deg_along=2):
    """Robust smooth model pos = f(line index, position along the line) from (idx, along, pos, w).
    Returns the model, the median absolute residual and the inlier share (residual < 3 px)."""
    p = np.array(pts, float)
    k, t, x, w = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    km, ks, tm, ts = k.mean(), k.std() + 1e-9, t.mean(), t.std() + 1e-9

    def design(kk, tt):
        u, v = (np.asarray(kk, float) - km) / ks, (np.asarray(tt, float) - tm) / ts
        return np.stack([u ** i * v ** j for i in range(deg_line + 1) for j in range(deg_along + 1)], -1)

    A = design(k, t)
    ww = w.copy()
    for _ in range(10):                                 # iteratively reweighted least squares
        coef = np.linalg.lstsq(A * ww[:, None], x * ww, rcond=None)[0]
        res = np.abs(A @ coef - x)
        s = max(1.4826 * np.median(res), 0.3)
        ww = w / np.maximum(1, res / (2.5 * s))
    return (lambda kk, tt: design(kk, tt) @ coef), float(np.median(res)), float(np.mean(res < 3))


def grid_quads(score_img, quads, ncols=36, inner_x=None, inner_y=None, retry=True):
    """grid_quads_once; if the lines are not found, once more with heavier smoothing and a lower
    contrast threshold (for very dark frames)."""
    out, info = grid_quads_once(score_img, quads, ncols, inner_x, inner_y)
    if info is None and retry:
        out, info = grid_quads_once(score_img, quads, ncols, inner_x, inner_y, sigma=2.5, thr=0.02)
        if info is not None:
            info["retry"] = True
    return out, info


def grid_quads_once(score_img, quads, ncols=36, inner_x=None, inner_y=None, sigma=1.0, thr=0.05):
    """Place every sampling box centred between the dark gap lines around its patch.

    1. Horizontal gap lines (between rows): brightness profiles down every column, valleys
       assigned to lines by tracking outward from the middle; smooth robust fit y = Y(j, x).
    2. Vertical gap lines (between columns): one profile along the centre of each row, following
       Y; all valleys found; assigned to line numbers by walking outward from the chart centre,
       each next line predicted from the last one found plus the local spacing (a missing valley,
       e.g. a near-black patch next to the dark gap, is skipped, not mis-assigned); smooth robust
       fit x = X(k, y), which also carries the lens distortion and the outer edges.
    3. Horizontal lines again, now down the true column centres.
    4. Each box: the central inner_x x inner_y of the cell between its four lines. A cell whose
       width or height is implausible keeps its input quad. (No check against the first guess:
       that guess was itself up to 0.7 of a patch off in places, e.g. 0185 rows 2-4, cols 27-34.)"""
    inner_x = INNER_X if inner_x is None else inner_x
    inner_y = INNER_Y if inner_y is None else inner_y
    C = np.array([q.mean(0) for q in quads]).reshape(-1, ncols, 2)   # first-guess centres [row, col]
    nrows = C.shape[0]
    px = np.median(np.linalg.norm(np.diff(C, axis=1), axis=2))
    py = np.median(np.linalg.norm(np.diff(C, axis=0), axis=2))
    img = cv2.GaussianBlur(score_img.astype(np.float32), (0, 0), sigma)

    def horizontal(colx):
        pts = []
        for c in range(ncols):
            ys = np.arange(C[0, c, 1] - py, C[-1, c, 1] + py, dtype=np.float32)
            prof = _profile(img, ys, colx(c, ys), int(0.15 * px), vertical_lines=False)
            vals = [(ys[0] + v[0], v[1]) for v in _valleys(prof, py, thr)]
            preds = {j: (C[j - 1, c, 1] + C[j, c, 1]) / 2 for j in range(1, nrows)}
            for j, (y, wgt) in _track(vals, preds, py, nrows).items():
                pts.append((j, float(colx(c, np.array([y]))[0]), y, wgt))
        return pts

    hpts = horizontal(lambda c, ys: np.interp(ys, C[:, c, 1], C[:, c, 0]))
    if len(hpts) < 0.5 * ncols * (nrows - 1):
        return quads, None
    Y, hmed, hin = _fit_lines(hpts)
    vpts = []
    for r in range(nrows):
        xs = np.arange(C[r, 0, 0] - px, C[r, -1, 0] + px, dtype=np.float32)
        ymid = (Y(np.full(len(xs), r), xs) + Y(np.full(len(xs), r + 1), xs)) / 2 if r not in (0, nrows - 1) \
            else np.interp(xs, C[r, :, 0], C[r, :, 1])
        prof = _profile(img, xs, ymid, int(0.2 * py), vertical_lines=True)
        vals = [(xs[0] + v[0], v[1]) for v in _valleys(prof, px, thr)]
        preds = {k: (C[r, k - 1, 0] + C[r, k, 0]) / 2 for k in range(1, ncols)}
        for k, (x, wgt) in _track(vals, preds, px, ncols).items():
            vpts.append((k, float(np.interp(x, xs, ymid)), x, wgt))
    if len(vpts) < 0.5 * nrows * (ncols - 1):
        return quads, None
    X, vmed, vin = _fit_lines(vpts)
    hpts = horizontal(lambda c, ys: (X(np.full(len(ys), c), ys) + X(np.full(len(ys), c + 1), ys)) / 2)
    Y, hmed, hin = _fit_lines(hpts)
    out, fallback = [], 0
    for r in range(nrows):
        for c in range(ncols):
            cx, cy = C[r, c]
            for _ in range(3):                         # intersect the four lines around the cell
                xl, xr = X([c], [cy])[0], X([c + 1], [cy])[0]
                yt, yb = Y([r], [cx])[0], Y([r + 1], [cx])[0]
                cx, cy = (xl + xr) / 2, (yt + yb) / 2
            ok = 0.8 * px < xr - xl < 1.2 * px and 0.8 * py < yb - yt < 1.2 * py
            if not ok:
                out.append(quads[r * ncols + c]); fallback += 1; continue
            hw, hh = inner_x * (xr - xl) / 2, inner_y * (yb - yt) / 2
            out.append(np.array([[cx - hw, cy - hh], [cx + hw, cy - hh], [cx + hw, cy + hh], [cx - hw, cy + hh]]))
    return out, {"vpts": len(vpts), "hpts": len(hpts), "vmed": vmed, "hmed": hmed, "vin": vin, "hin": hin,
                 "fallback": fallback}


def load_jpeg(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im)
    small = cv2.resize(a.mean(2).astype(np.float32) / 255, (a.shape[1] // 4, a.shape[0] // 4),
                       interpolation=cv2.INTER_AREA)
    return [a[..., i].astype(np.float32) for i in range(3)], small, 4.0


def load_raw(path):
    with rawpy.imread(path) as r:
        raw = r.raw_image_visible.astype(np.float32)
        pat = r.raw_pattern
        desc = r.color_desc.decode()
        blk = r.black_level_per_channel          # 255 at ISO 200; 253/254 at higher ISO
        planes, blacks = {}, {}
        for i in range(2):
            for j in range(2):
                planes.setdefault(desc[pat[i, j]], []).append(raw[i::2, j::2])
                blacks.setdefault(desc[pat[i, j]], []).append(blk[pat[i, j]])
    R, B = planes["R"][0], planes["B"][0]
    G1, G2 = planes["G"]
    black = [blacks["R"][0], blacks["G"][0], blacks["G"][1], blacks["B"][0]]
    g = np.clip((G1 + G2) / 2 - np.mean(black[1:3]), 0, None)
    g = (g / max(np.percentile(g, 99.9), 1)) ** (1 / 2.2)
    small = cv2.resize(g, (g.shape[1] // 2, g.shape[0] // 2), interpolation=cv2.INTER_AREA)
    return [R, G1, G2, B], small, 2.0, black


def homography(layout, small, scale):
    q = find_markers(small)
    if q is None:
        return None
    return cv2.getPerspectiveTransform(chart_points(layout).astype(np.float32),
                                       (q * scale).astype(np.float32))


def pick_layout(layouts, jpg_planes, small, scale):
    """The chart file shown on screen: the layout whose patch centres are the flattest."""
    best = None
    for name, lay in layouts.items():
        Hm = homography(lay, small, scale)
        quads = inner_quads(lay, Hm)
        spread = [max(s[2] - s[1] for s in sample(jpg_planes, q)) for q in quads]
        score = np.median(spread)
        if best is None or score < best[0]:
            best = (score, name)
    return best[1], best[0]


# ---------- main ----------

def exif_settings(files):
    cmd = ["exiftool", "-j", "-n"] + ["-" + t for t in EXIF_TAGS] + files
    js = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    cmd = ["exiftool", "-j"] + ["-PictureMode", "-Gradation", "-ArtFilterEffect",
                                "-WhiteBalance2"] + files
    txt = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    out = {}
    for n, t in zip(js, txt):
        n["text"] = {k: t.get(k) for k in ("PictureMode", "Gradation", "ArtFilterEffect", "WhiteBalance2")}
        out[os.path.basename(n["SourceFile"])[:-4]] = n
    return out


def overlay(path, quads, out):
    im = cv2.imread(path)
    for q in quads:
        cv2.polylines(im, [np.round(q).astype(np.int32)], True, (255, 0, 255), 3)
    cv2.imwrite(out, cv2.resize(im, (im.shape[1] // 3, im.shape[0] // 3)), [cv2.IMWRITE_JPEG_QUALITY, 85])


def overlay_raw(rp, black, quads, out):
    g = np.clip((rp[1] - black[1]) / max(np.percentile(rp[1] - black[1], 99), 1), 0, 1) ** (1 / 2.2)
    im = cv2.cvtColor((g * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    for q in quads:
        cv2.polylines(im, [np.round(q).astype(np.int32)], True, (255, 0, 255), 1)
    cv2.imwrite(out, im)


def check_crops(n, rp, black, qr, jp, qj, rows=(4, 7), cols=(14, 36)):
    """Full-resolution crops (raw G plane and JPEG) of rows 4-6, columns 14-35 with the boxes."""
    for tag, img, quads, scale in (("raw", rp[1] - black[1], qr, 1), ("jpg", sum(jp) / 3, qj, 1)):
        sel = [quads[r * 36 + c] for r in range(*rows) for c in range(*cols)]
        pts = np.concatenate(sel)
        x0, y0 = np.floor(pts.min(0) - 60).astype(int)
        x1, y1 = np.ceil(pts.max(0) + 60).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        crop = img[y0:y1, x0:x1].astype(np.float32)
        crop = np.clip(crop / max(np.percentile(crop, 99), 1), 0, 1) ** (1 / 2.2)
        im = cv2.cvtColor((crop * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        for q in sel:
            cv2.polylines(im, [np.round(q - [x0, y0]).astype(np.int32)], True, (255, 0, 255), 1)
        cv2.imwrite(os.path.join(OUT, f"check_{tag}_{n}.png"), im)


def main():
    layouts = json.load(open(os.path.join(OUT, "chart_layout.json")))
    layouts = {k: v for k, v in layouts.items() if k in ("1920x1080", "2560x1600")}  # 3840 = 1920 in fractions
    orfs = sorted(f for f in os.listdir(SHOTS) if f.startswith("PB09") and f.endswith(".ORF"))
    names = [f[:-4] for f in orfs]
    settings = exif_settings([os.path.join(SHOTS, f) for f in orfs])

    jp, small, sc = load_jpeg(os.path.join(SHOTS, "PB090187.JPG"))
    lay_name, score = pick_layout(layouts, jp, small, sc)
    print(f"chart layout: {lay_name} (median patch spread {score:.1f}/255)")
    lay = layouts[lay_name]
    npatch = len(lay["patches"])

    raw = np.zeros((len(names), npatch, 3)); rawclip = np.zeros((len(names), npatch), bool)
    rawspread = np.zeros((len(names), npatch)); jpg = np.zeros((len(names), npatch, 3))
    jpgspread = np.zeros((len(names), npatch)); npx = np.zeros((len(names), npatch, 2), int)
    lines = {}
    for k, n in enumerate(names):
        jp, small, sc = load_jpeg(os.path.join(SHOTS, n + ".JPG"))
        Hj = homography(lay, small, sc)
        rp, smallr, scr, black = load_raw(os.path.join(SHOTS, n + ".ORF"))
        Hr = homography(lay, smallr, scr)
        if Hj is None or Hr is None:
            sys.exit(f"{n}: markers not found (jpg {Hj is not None}, raw {Hr is not None})")
        qj, offj = refine(sum(jp) / 3, inner_quads(lay, Hj))
        qr, offr = refine(sum(rp), inner_quads(lay, Hr))
        qj, gj = grid_quads(sum(jp) / 3, qj)
        qr, gr = grid_quads(sum(rp), qr)
        none = {"vpts": 0, "hpts": 0, "vmed": np.nan, "hmed": np.nan, "vin": np.nan, "hin": np.nan, "fallback": 252}
        if gj is None or gr is None:
            print(f"{n}: WARNING gap lines not found in {'jpg' if gj is None else ''} {'raw' if gr is None else ''}; "
                  f"keeping the flatness-search placement there")
        gj, gr = gj or none, gr or none
        lines[n] = {"jpg": gj, "raw": gr}
        for i in range(npatch):
            sj = sample(jp, qj[i])
            jpg[k, i] = [s[0] for s in sj]
            jpgspread[k, i] = max(s[2] - s[1] for s in sj)
            sr = sample(rp, qr[i])                      # R, G1, G2, B
            med = [s[0] - b for s, b in zip(sr, black)]
            raw[k, i] = [med[0], (med[1] + med[2]) / 2, med[3]]
            rawclip[k, i] = max(s[3] for s in sr) >= SAT
            rawspread[k, i] = max((s[2] - s[1]) / max(s[0] - b, 1) for s, b in zip(sr, black))
            npx[k, i] = [sj[0][4], sr[0][4]]
        if n in ("PB090187", "PB090219", "PB090211"):
            overlay(os.path.join(SHOTS, n + ".JPG"), qj, os.path.join(OUT, f"overlay_{n}.jpg"))
        if n in ("PB090187", "PB090185", "PB090198", "PB090211"):
            overlay_raw(rp, black, qr, os.path.join(OUT, f"overlay_raw_{n}.png"))
            check_crops(n, rp, black, qr, jp, qj)
        print(f"{n} {ROLES.get(int(n[-3:]), '?'):16s} jpg spread med {np.median(jpgspread[k]):5.1f}  "
              f"lines jpg {gj['vpts']}/{gj['hpts']} med {gj['vmed']:.1f}/{gj['hmed']:.1f}px in {gj['vin']:.2f}/{gj['hin']:.2f} fb {gj['fallback']}  "
              f"raw {gr['vpts']}/{gr['hpts']} med {gr['vmed']:.1f}/{gr['hmed']:.1f}px in {gr['vin']:.2f}/{gr['hin']:.2f} fb {gr['fallback']}  "
              f"raw clipped patches {rawclip[k].sum():3d}  px/patch jpg {npx[k, :, 0].min()} raw {npx[k, :, 1].min()}")

    meta = [{k: p[k] for k in ("row", "col", "kind", "rgb")} for p in lay["patches"]]
    np.savez_compressed(os.path.join(OUT, "patches.npz"), names=names,
                        roles=[ROLES.get(int(n[-3:]), "?") for n in names], raw=raw, rawclip=rawclip,
                        rawspread=rawspread, jpg=jpg, jpgspread=jpgspread, npx=npx,
                        patch_meta=json.dumps(meta), layout=lay_name)
    json.dump(settings, open(os.path.join(OUT, "settings.json"), "w"), indent=1)
    json.dump(lines, open(os.path.join(OUT, "gridlines.json"), "w"), indent=1, default=float)
    print("wrote out/patches.npz, out/settings.json")


if __name__ == "__main__":
    main()

"""Step 2b: which firmware tone curve does each setting use?

Model (the GR III's, FINDINGS §13, adapted): for each patch,
    v = M · (WB ⊙ raw)              raw = black-subtracted camera RGB (extract.py)
                                    WB  = WB_RBLevels / 256 (R, B; G = 1), M = ColorMatrix / 256
    jpeg_c ≈ C(k · v_c) · 255 / max(C)
C is a 256-entry curve from block 0, interpolated; k (the input scale) is the only free
parameter. Every monotone run of 256 u16 words in block 0 is a candidate.

Usage: ../../.venv/bin/python -I analyze_tone.py      (needs out/patches.npz, out/settings.json)
Writes out/tone_report.txt and out/tone_<group>.png.
"""
import json
import os
import struct

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BLOCK0 = os.path.join(HERE, "..", "..", "build", "blocks", "OLY_E_101_1600_0000_0000.BIN.block0.bin")
BASE = 0x7E421020


def candidates():
    """Every monotone non-decreasing run of exactly 256 u16 words (at any even offset)."""
    b = open(BLOCK0, "rb").read()
    out = []
    for par in (0, 1):
        w = np.frombuffer(b[par:len(b) - ((len(b) - par) % 2)], "<u2").astype(np.int64)
        inc = np.diff(w) >= 0
        start = 0
        for i in range(1, len(w) + 1):
            if i == len(w) or not inc[i - 1]:
                n = i - start
                if n >= 256:
                    for s in range(start, start + n - 255, 1 if n < 300 else n):  # whole run or its start
                        c = w[s:s + 256]
                        if c[-1] - c[0] >= 200 and len(np.unique(c)) > 64:
                            out.append((BASE + par + 2 * s, c))
                start = i
    uniq = {}
    for a, c in out:
        uniq.setdefault(c.tobytes(), (a, c))
    return list(uniq.values())


BAD = None


def load():
    global BAD
    d = np.load(os.path.join(OUT, "patches.npz"))
    BAD = raw_outliers(d)
    st = json.load(open(os.path.join(OUT, "settings.json")))
    meta = json.loads(str(d["patch_meta"]))
    return d, st, meta


def precurve(d, st, k):
    n = str(d["names"][k])
    s = st[n]
    lv = [float(x) for x in str(s["WB_RBLevels"]).split()]
    wb = np.array([lv[0] / 256, 1.0, lv[1] / 256])
    M = np.array([float(x) for x in str(s["ColorMatrix"]).split()]).reshape(3, 3) / 256
    return (d["raw"][k] * wb) @ M.T


def raw_outliers(d):
    """Patches whose raw spread is far above that of patches of similar brightness (a sampling box
    that still touches a patch edge). Absolute spread = relative spread x signal."""
    sig = np.maximum(d["raw"][..., 1], 1)
    ab = d["rawspread"] * sig
    bins = np.digitize(np.log2(sig), np.arange(0, 13, 0.5))
    bad = np.zeros(sig.shape, bool)
    for b in np.unique(bins):
        m = bins == b
        bad[m] = ab[m] > 3 * np.median(ab[m]) + 4
    return bad


def usable(d, k):
    j = d["jpg"][k]
    return (~d["rawclip"][k]) & (d["jpgspread"][k] < 20) & (j.min(1) > 3) & (j.max(1) < 252) & (~BAD[k])


def collect(d, st, meta, shots, rows=(6,)):
    V, J = [], []
    for k in shots:
        v = precurve(d, st, k)
        ok = usable(d, k) & np.isin([m["row"] for m in meta], rows)
        V.append(v[ok]); J.append(d["jpg"][k][ok])
    return np.concatenate(V), np.concatenate(J)


def fit_curve(c, V, J):
    """Best input scale k for curve c; returns (rms in 8-bit codes, k)."""
    v, j = V.ravel(), J.ravel()
    sel = v > 0
    v, j = v[sel], j[sel]
    cs = c.astype(float) * 255.0 / c.max()
    best = (1e9, None)
    for k in np.exp(np.linspace(np.log(1e-3), np.log(2.0), 400)):
        p = np.interp(k * v, np.arange(256), cs)
        e = np.sqrt(np.mean((p - j) ** 2))
        if e < best[0]:
            best = (e, k)
    e0, k0 = best
    for k in np.linspace(k0 * 0.97, k0 * 1.03, 121):
        p = np.interp(k * v, np.arange(256), cs)
        e = np.sqrt(np.mean((p - j) ** 2))
        if e < best[0]:
            best = (e, k)
    return best


def plot(V, J, curve, k, path, title):
    W, H = 640, 480
    im = Image.new("RGB", (W, H), "white"); dr = ImageDraw.Draw(im)
    vmax = np.percentile(V, 99.5)
    for v, j in zip(V, J):
        for c, col in zip(range(3), [(220, 40, 40), (40, 160, 40), (40, 40, 220)]):
            x, y = 40 + (W - 60) * v[c] / vmax, H - 30 - (H - 50) * j[c] / 255
            dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=col)
    if curve is not None:
        xs = np.linspace(0, vmax, 300)
        ys = np.interp(k * xs, np.arange(256), curve * 255.0 / curve.max())
        pts = [(40 + (W - 60) * x / vmax, H - 30 - (H - 50) * y / 255) for x, y in zip(xs, ys)]
        dr.line(pts, fill=(0, 0, 0), width=2)
    dr.text((45, 8), title, fill=(0, 0, 0)); dr.text((W // 2, H - 18), "pre-curve value v (raw units)", fill=(0, 0, 0))
    im.save(path)


def main():
    d, st, meta = load()
    names = [str(n) for n in d["names"]]
    roles = [str(r) for r in d["roles"]]
    cands = candidates()
    lines = [f"{len(cands)} unique candidate curves (monotone 256 x u16) in block 0"]

    def shots(pred):
        return [k for k, n in enumerate(names) if pred(st[n], roles[k])]

    def plain(s, r, mode="Natural"):
        t = s["text"]
        return (t["PictureMode"].startswith(mode) and str(s["PictureModeContrast"]).split()[0] == "0"
                and str(s["PictureModeSaturation"]).split()[0] == "0" and t["Gradation"].startswith("Normal; User")
                and t["ArtFilterEffect"].startswith("Off") and s["ISO"] == 200 and s["WhiteBalanceTemperature"] == 5300)

    groups = {
        "natural": shots(lambda s, r: plain(s, r)),
        "vivid": shots(lambda s, r: plain(s, r, "Vivid")),
        "muted": shots(lambda s, r: plain(s, r, "Muted")),
        "portrait": shots(lambda s, r: plain(s, r, "Portrait")),
        "monotone": shots(lambda s, r: plain(s, r, "Monotone")),
        "ienhance": shots(lambda s, r: plain(s, r, "i-Enhance")),
        "highkey": shots(lambda s, r: r == "G1-highkey"), "lowkey": shots(lambda s, r: r == "G2-lowkey"),
        "gradauto": shots(lambda s, r: r == "G3-auto"),
        "nat_con-2": shots(lambda s, r: r in ("N1-con-2", "N1b-con-2")), "nat_con+2": shots(lambda s, r: r == "N2-con+2"),
        "por_con-2": shots(lambda s, r: r == "P1-con-2"), "por_con+2": shots(lambda s, r: r == "P2-con+2"),
        "iso800": shots(lambda s, r: r == "I1-iso800"), "iso3200": shots(lambda s, r: r == "I2-iso3200"),
        "popart": shots(lambda s, r: r == "A1-popart"), "palelight": shots(lambda s, r: r == "A2-palelight"),
        "lighttone": shots(lambda s, r: r == "A3-lighttone"), "crossprocess": shots(lambda s, r: r == "A4-crossprocess"),
    }
    results = {}
    for g, ks in groups.items():
        V, J = collect(d, st, meta, ks)
        if len(V) < 10:
            lines.append(f"{g}: too few points"); continue
        fits = sorted((fit_curve(c, V, J) + (a, c) for a, c in cands), key=lambda z: z[0])
        results[g] = fits[:5]
        lines.append(f"\n{g}: shots {[names[k][-4:] for k in ks]}, {len(V)} gray points")
        for e, k, a, c in fits[:5]:
            lines.append(f"   {a:#010x}  rms {e:5.2f}  k {k:.5f}  max {c.max()}  s64/128/192 {c[64]} {c[128]} {c[192]}")
        e, k, a, c = fits[0]
        plot(V, J, c, k, os.path.join(OUT, f"tone_{g}.png"), f"{g}: best {a:#x} rms {e:.2f}")
    open(os.path.join(OUT, "tone_report.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

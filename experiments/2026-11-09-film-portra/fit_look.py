"""Camera model of the normal Picture Mode path, and the fit of a look to a target LUT.

Model (NOTES.md §11, §14, corrected in §16; measured or traced):
    v   = ColorMatrix · (WB ⊙ raw)              linear sRGB-primaries RGB, raw units
    b_c = G_c(BASE_c(K·v_c)) / 4                per-channel RGB gamma (G_c = identity for stock), K = 0.0621
    Y   = 0.299 b_R + 0.587 b_G + 0.114 b_B     BT.601 luma
    out = LOOK(Y)/4 + SAT · (b − Y)             the look curve acts on LUMA (model "luma", default);
                                                 Cb/Cr are only scaled by the saturation gain
  --model channel selects the earlier form, out_c = LOOK(b_c)/4 with chroma × SAT afterwards.

Art filters pick their own base gamma per channel (0x7E56B790, NOTES.md §14): Cross Process I
uses three (R, G, B). Slot "crossprocess" therefore fits three curves G_c on the base-gamma output:
    c_c = G_c(BASE(K·v_c)) / 4
and writes them as Cross Process I's 24 base tables (4 variants x 2 x 3 channels), sets its look
curve to the identity and its saturation gain pair. Slot "portrait" fits one shared look curve.

Without --lut: validates the model on shoot 1. With --lut FILE.cube: fits, compares with every
menu setting the model covers, writes patches/<name>.json.

    ../../.venv/bin/python -I fit_look.py
    ../../.venv/bin/python -I fit_look.py --lut portra.cube --slot crossprocess --name film-portra-xp
    ../../.venv/bin/python -I fit_look.py --probe          # writes patches/curve-probe-2.json
"""
import argparse
import importlib.util
import json
import os
import struct

import numpy as np
from scipy.optimize import least_squares, minimize_scalar

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
spec = importlib.util.spec_from_file_location("tone", os.path.join(HERE, "analyze_tone.py"))
tone = importlib.util.module_from_spec(spec); spec.loader.exec_module(tone)

BASE_GAMMA, K = 0x7E74E9BC, 0.0621
IDENTITY = 0x7E75B8F0
PORTRAIT = [0x7E75D6F0, 0x7E75D8F0, 0x7E75DAF0, 0x7E75DCF0, 0x7E75DEF0]   # Contrast -2..+2
V_GRAY = 264.0            # v that Natural renders as code 118 (sRGB 18 % gray), §10.4
STOCK = {"Natural": ("B3", IDENTITY), "Vivid": ("M1-vivid", IDENTITY), "Muted": ("M2-muted", 0x7E75D0F0),
         "Portrait": ("M3-portrait", 0x7E75DAF0), "Natural Sat -2": ("N3-sat-2", IDENTITY),
         "Natural Sat +2": ("N4-sat+2", IDENTITY), "Natural Con +2": ("N2-con+2", 0x7E75D4F0),
         "Low Key": ("G2-lowkey", 0x7E75E2F0)}
_b0 = open(tone.BLOCK0, "rb").read() if os.path.exists(tone.BLOCK0) else None      # stock block 0 (not in git); only the firmware-table helpers need it


def table(a):
    return np.array(struct.unpack("<256H", _b0[a - tone.BASE:a - tone.BASE + 512]), float)


BASE = table(BASE_GAMMA) if _b0 is not None else None
X = np.arange(256)


MODEL = "luma"
LUMA = np.array([0.299, 0.587, 0.114])


def apply_look(c, look, sat):
    """c: (N, 3) 8-bit-scale values after the RGB gamma; look: 256 x (0..1023) table or None (identity)."""
    if MODEL == "channel":
        if look is not None:
            c = np.interp(c, X, look) / 4.0
        y = c @ LUMA
        return np.clip(y[:, None] + sat * (c - y[:, None]), 0, 255)
    y = c @ LUMA
    y2 = y if look is None else np.interp(y, X, look) / 4.0
    return np.clip(y2[:, None] + sat * (c - y[:, None]), 0, 255)


def camera(v, look, sat):
    """8-bit sRGB prediction for pre-curve values v (N, 3), default base gamma in all channels."""
    return apply_look(np.interp(K * np.maximum(v, 0), X, BASE) / 4.0, look, sat)


# ---------- colour difference ----------

def srgb_to_lab(rgb8):
    c = np.clip(rgb8, 0, 255) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def de2000(l1, l2):
    L1, a1, b1 = l1.T; L2, a2, b2 = l2.T
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1 = np.degrees(np.arctan2(b1, a1p)) % 360; h2 = np.degrees(np.arctan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = h2 - h1; dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)); dh = np.where(C1p * C2p == 0, 0, dh)
    dH = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh) / 2)
    Lm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1 + h2
    hm = np.where(np.abs(h1 - h2) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)); hm = np.where(C1p * C2p == 0, hs, hm)
    T = 1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm)) + 0.32 * np.cos(np.radians(3 * hm + 6)) - 0.20 * np.cos(np.radians(4 * hm - 63))
    Sl = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2); Sc = 1 + 0.045 * Cpm; Sh = 1 + 0.015 * Cpm * T
    Rt = -2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25.0 ** 7)) * np.sin(np.radians(60 * np.exp(-((hm - 275) / 25) ** 2)))
    return np.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh))


# ---------- validation on shoot 1 ----------

def shot(d, st, meta, roles, role):
    k = roles.index(role)
    v = tone.precurve(d, st, k)
    ok = (~d["rawclip"][k]) & (~tone.BAD[k]) & (d["jpgspread"][k] < 20)
    return v[ok], d["jpg"][k][ok], np.array([m["row"] for m in meta])[ok]


def validate():
    d, st, meta = tone.load()
    roles = [str(r) for r in d["roles"]]
    out, sats = [], {}
    for name, (role, la) in STOCK.items():
        v, j, rows = shot(d, st, meta, roles, role)
        look = table(la)
        inside = (j.min(1) > 4) & (j.max(1) < 250)            # away from the 8-bit limits
        col = inside & (rows < 6)
        s = minimize_scalar(lambda s: de2000(srgb_to_lab(camera(v[col], look, s)), srgb_to_lab(j[col])).mean(),
                            bounds=(0.5, 2), method="bounded").x        # ΔE-based: the estimator check_flashed.py confirmed on camera
        sats[name] = s
        p = camera(v, look, s)
        de = de2000(srgb_to_lab(p), srgb_to_lab(j))
        out.append(f"  {name:16s} sat {s:.3f}  ΔE2000 model vs camera: in-range patches mean {de[inside].mean():.2f} "
                   f"p95 {np.percentile(de[inside], 95):.2f} (n={inside.sum()}); all patches mean {de.mean():.2f} (n={len(de)})")
    return out, sats


# ---------- target ----------

def load_cube(path):
    size, rows = None, []
    for line in open(path):
        t = line.split()
        if not t or t[0].startswith("#"):
            continue
        if t[0] == "LUT_3D_SIZE":
            size = int(t[1])
        elif t[0][0].isdigit() or t[0][0] in "-.":
            rows.append([float(x) for x in t[:3]])
    return np.array(rows).reshape(size, size, size, 3), size      # index [b, g, r]


def apply_cube(cube, size, rgb):
    p = np.clip(rgb, 0, 1) * (size - 1)
    i0 = np.minimum(p.astype(int), size - 2); f = p - i0
    out = 0
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (f[:, 0] if dr else 1 - f[:, 0]) * (f[:, 1] if dg else 1 - f[:, 1]) * (f[:, 2] if db else 1 - f[:, 2])
                out = out + w[:, None] * cube[i0[:, 2] + db, i0[:, 1] + dg, i0[:, 0] + dr]
    return out


def encode(lin, name):
    """Scene-linear sRGB-primaries RGB (0.18 = mid gray) -> LUT input encoding."""
    if name == "vlog":                                          # Panasonic V-Log curve on V-Gamut primaries
        import colour
        lin = lin @ colour.matrix_RGB_to_RGB(colour.RGB_COLOURSPACES["sRGB"], colour.RGB_COLOURSPACES["V-Gamut"],
                                             chromatic_adaptation_transform=None).T
        cut, b, c, dd = 0.01, 0.00873, 0.241514, 0.598206
        return np.where(lin < cut, 5.6 * lin + 0.125, c * np.log10(np.maximum(lin, cut) + b) + dd)
    if name == "srgb":
        l = np.clip(lin, 0, 1)
        return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)
    if name == "linear":
        return lin
    raise SystemExit(f"unknown input encoding {name}")


# ---------- samples (as GRKit crates/grkit-core/src/fit/mod.rs: gray 150, chart 20, skin 60, random 1) ----------

def colorchecker_linear():
    import colour
    cc = colour.CCS_COLOURCHECKERS["ColorChecker24 - After November 2014"]
    xyY = np.array(list(cc.data.values()))
    XYZ = colour.xyY_to_XYZ(xyY)
    return np.clip(colour.XYZ_to_RGB(XYZ, colour.RGB_COLOURSPACES["sRGB"], illuminant=cc.illuminant,
                                     chromatic_adaptation_transform="Bradford"), 0, None)


def natural(n, seed, ev=(-2, 2)):
    rng = np.random.default_rng(seed)
    base = 0.18 * 2 ** rng.uniform(-3.5, 2.0, n) * 2 ** rng.uniform(*ev, n) ** 0.0
    hue = rng.uniform(0, 2 * np.pi, n); chroma = rng.beta(1.2, 3.5, n) * 0.9
    d = np.stack([np.cos(hue), np.cos(hue - 2.094), np.cos(hue + 2.094)], 1)
    return base[:, None] * np.clip(1 + chroma[:, None] * d, 0.02, None)


def samples():
    """Scene-linear samples and weights: gray ramp, ColorChecker at -2..+2 EV, random natural colours."""
    gray = np.repeat((0.18 * 2 ** np.linspace(-5, 2.5, 120))[:, None], 3, 1)
    cc = colorchecker_linear()
    chart = np.concatenate([cc * 2.0 ** e for e in (-2, -1, 0, 1, 2)])
    wchart = np.tile(np.where(np.arange(24) < 2, 60.0, 20.0), 5)
    rnd = natural(4000, 1)
    lin = np.concatenate([gray, chart, rnd])
    w = np.concatenate([np.full(len(gray), 150.0), wchart, np.ones(len(rnd))])
    keep = lin.max(1) <= 0.18 * 2 ** 2.6                       # within the sensor's range (v <= ~4045 / K scale)
    kind = np.concatenate([np.zeros(len(gray), int), np.ones(len(chart), int), np.full(len(rnd), 2)])
    return lin[keep], w[keep], kind[keep]


# ---------- models ----------

def cam_curves(v, G, sat, look=None):
    """G: (3, 1024) curves on the base-gamma output (0..1023 -> 0..1023); look: 256-entry table or None."""
    b = np.interp(K * np.maximum(v, 0), X, BASE)
    c = np.stack([np.interp(b[:, i], np.arange(1024), G[i]) for i in range(3)], 1) / 4.0
    return apply_look(c, look, sat)


IDENT_G = np.tile(np.arange(1024.0), (3, 1))
SHARED = {-3: 0x7E75CCF0, -2: 0x7E75CEF0, -1: 0x7E75D0F0, 0: IDENTITY, 1: 0x7E75D2F0, 2: 0x7E75D4F0}
GRAD = {"High Key": 0x7E75E0F0, "Low Key": 0x7E75E2F0}
SAT_GAIN = {-2: 226, -1: 254, 0: 282, 1: 310, 2: 338}            # steps of the saturation table (NOTES §12.2)


def menu_grid(sats):
    """Every setting the model covers: mode x (Contrast -2..+2 or Gradation High/Low Key) x Saturation -2..+2.
    Returns (name, look table, saturation). The six-axis records of Vivid / Muted / Portrait are not modelled."""
    out = []
    for mode, (off, s0) in {"Natural": (0, sats["Natural"]), "Vivid": (0, sats["Vivid"]), "Muted": (-1, sats["Muted"]),
                            "Portrait": (None, sats["Portrait"])}.items():
        tones = {f"Contrast {c:+d}": (PORTRAIT[c + 2] if off is None else SHARED[c + off]) for c in range(-2, 3)}
        tones.update(GRAD)
        for tn, la in tones.items():
            for sv, g in SAT_GAIN.items():
                out.append((f"{mode}, {tn}, Saturation {sv:+d}", table(la), s0 * g / 282.0))
    return out


def fit(lin, w, tl, slot, knots=20, free_look=False):
    """crossprocess: three curves G_c (+ optionally a free luma look curve); portrait: the look curve only."""
    v = lin / 0.18 * V_GRAY
    kx = np.linspace(0, 1023, knots); lx = np.linspace(0, 255, knots)
    nch = 3 if slot == "crossprocess" else 0
    use_look = free_look or nch == 0

    def mono(q):
        return np.minimum(np.cumsum(q ** 2), 1023.0)

    def unpack(p):
        G = np.array([np.interp(np.arange(1024), kx, mono(p[i * knots:(i + 1) * knots])) for i in range(nch)]) if nch else IDENT_G
        look = np.interp(X, lx, mono(p[nch * knots:(nch + 1) * knots])) if use_look else None
        return G, look, p[-1]

    def resid(p):
        G, look, sat = unpack(p)
        de = de2000(srgb_to_lab(cam_curves(v, G, sat, look)), tl)
        sm = [0.05 * np.diff(G[:, ::32], 2, axis=1).ravel()] if nch else []
        if use_look:
            sm.append(0.05 * np.diff(look[::8], 2))
        return np.concatenate([np.sqrt(w) * de] + sm)

    p0 = np.sqrt(np.maximum(np.concatenate([[1e-3], np.diff(kx)]), 1e-3))
    r = least_squares(resid, np.concatenate([np.tile(p0, nch + int(use_look)), [1.0]]), x_scale="jac", max_nfev=300)
    return unpack(r.x)


# ---------- patch writers ----------

def rec8(a):
    return list(struct.unpack("<8I", _b0[a - tone.BASE:a - tone.BASE + 32]))


DEFAULT_REC, XP_REC = 0x7E78B39C, (0x7E78B41C, 0x7E78B43C, 0x7E78B45C)   # base-gamma records: default; Cross Process I R, G, B
XP_LOOK, XP_SAT = 0x7E75F2F0, 0x7E7696B4


def op(addr, new):
    old = _b0[addr - tone.BASE:addr - tone.BASE + len(new)]
    return {"type": "bytes", "block": 0, "offset": hex(addr - tone.BASE), "expect": old.hex(), "new": new.hex()}


def pack(c):
    return struct.pack("<256H", *np.clip(np.round(np.maximum.accumulate(c)), 0, 1023).astype(int))


def xp_ops(G, gain, look=None):
    """Cross Process I := G_c applied to each default base-gamma variant; look curve (identity if None); saturation pair."""
    ops = []
    for ch, r in enumerate(XP_REC):
        for dflt, tgt in zip(rec8(DEFAULT_REC), rec8(r)):
            ops.append(op(tgt, pack(np.interp(table(dflt), np.arange(1024), G[ch]))))
    ops.append(op(XP_LOOK, _b0[IDENTITY - tone.BASE:IDENTITY - tone.BASE + 512] if look is None else pack(look)))
    ops.append(op(XP_SAT, struct.pack("<2H", gain, gain)))
    return [o for o in ops if o["expect"] != o["new"]]


def write_spec(name, desc, ops):
    json.dump({"name": name, "description": desc, "status": "built, NOT camera-tested",
               "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
               "base_sha256": "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", "ops": ops},
              open(os.path.join(ROOT, "patches", name + ".json"), "w"), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lut"); ap.add_argument("--input", default="vlog"); ap.add_argument("--exposure", type=float, default=0.0)
    ap.add_argument("--slot", choices=["portrait", "crossprocess"], default="crossprocess")
    ap.add_argument("--name", default="film-portra-xp"); ap.add_argument("--probe", action="store_true")
    ap.add_argument("--model", choices=["luma", "channel"], default="luma")
    ap.add_argument("--free-look", action="store_true", help="crossprocess: also fit the luma look curve")
    a = ap.parse_args()
    global MODEL
    MODEL = a.model
    lines = ["Model check on shoot 1 (normal Picture Mode path):"]
    val, sats = validate()
    lines += val
    if a.probe:
        ident = IDENT_G
        write_spec("curve-probe-2", "Verification of the per-channel base-gamma tables (NOTES §14). Cross Process I := the default "
                   "(Natural) base gammas in all three channels, identity look curve, saturation gain 338 (the Saturation +2 "
                   "step). Prediction: Cross Process I renders exactly like Natural with Saturation +2.", xp_ops(ident, 338))
        lines.append("wrote patches/curve-probe-2.json")
    if a.lut:
        cube, size = load_cube(a.lut)
        lin, w, kind = samples()
        tgt = lambda L: srgb_to_lab(np.clip(apply_cube(cube, size, encode(L * 2 ** a.exposure, a.input)), 0, 1) * 255)
        tl = tgt(lin)
        hold = natural(3000, 2); hold = hold[hold.max(1) <= 0.18 * 2 ** 2.6]; hl = tgt(hold)

        def score(G, s, look=None):
            de = de2000(srgb_to_lab(cam_curves(lin / 0.18 * V_GRAY, G, s, look)), tl)
            dh = de2000(srgb_to_lab(cam_curves(hold / 0.18 * V_GRAY, G, s, look)), hl)
            return np.average(de, weights=w), de[kind == 0].mean(), de[kind == 1].mean(), dh.mean(), np.percentile(dh, 95)

        G, look, sat = fit(lin, w, tl, a.slot, free_look=a.free_look)
        rows = sorted(((score(IDENT_G, s_, lk), n) for n, lk, s_ in menu_grid(sats)), key=lambda z: z[0][0])
        fmt = lambda sc: f"loss-weighted {sc[0]:5.2f} | gray {sc[1]:5.2f} | ColorChecker ±2 EV {sc[2]:5.2f} | hold-out mean {sc[3]:5.2f} p95 {sc[4]:5.2f}"
        lines.append(f"\nTarget {os.path.basename(a.lut)} ({a.input}, exposure {a.exposure:+.1f} EV), ΔE2000, model '{MODEL}'. Samples: GRKit weights "
                     f"(gray 150, chart 20, skin 60, random 1); hold-out = 3,000 unseen natural colours.")
        lines.append(f"  FIT, slot {a.slot}{' + free look curve' if a.free_look else ''}: {fmt(score(G, sat, look))}   (saturation {sat:.3f})")
        lines.append(f"  best of {len(rows)} menu settings: {rows[0][1]}: {fmt(rows[0][0])}")
        for sc, n in rows[1:5]:
            lines.append(f"     next: {n}: {fmt(sc)}")
        for n in ("Natural, Contrast +0, Saturation +0", "Portrait, Contrast +0, Saturation +0"):
            lines.append(f"  stock {n}: {fmt([sc for sc, m in rows if m == n][0])}")
        if a.slot == "crossprocess":
            gain = int(round(282 * sat / sats["Natural"]))
            write_spec(a.name, f"Cross Process I rebuilt as a film look fitted to {os.path.basename(a.lut)} "
                       f"(fit_look.py, model {MODEL}{', free look curve' if a.free_look else ''}; NOTES §14, §16): per-channel base gammas "
                       f"(24 tables), look curve, saturation gain {gain}.", xp_ops(G, gain, look))
            lines.append(f"  saturation gain written: {gain} (Natural = 282, model saturation {sats['Natural']:.3f})")
            np.save(os.path.join(HERE, "out", f"fit_{a.name}_G.npy"), G)
            if look is not None:
                np.save(os.path.join(HERE, "out", f"fit_{a.name}_look.npy"), look)
        else:
            old0 = table(PORTRAIT[2]); ops = []
            for la in PORTRAIT:
                new = look if la == PORTRAIT[2] else np.interp(np.interp(look, old0, X), X, table(la))
                ops.append(op(la, pack(new)))
            write_spec(a.name, f"Portrait look curves (Contrast -2..+2) fitted to {os.path.basename(a.lut)}; tone only (model {MODEL}).", ops)
        lines.append(f"wrote patches/{a.name}.json")
    open(os.path.join(HERE, "out", f"fit_report_{a.name}.txt" if a.lut else "fit_report.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

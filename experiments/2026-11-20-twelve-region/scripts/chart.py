"""The probe's synthetic test RAW: PB200001.ORF and its layout (twelve_layout.npz). Research code.

    cd experiments/2026-11-20-twelve-region && OMP_NUM_THREADS=2 uv run python scripts/chart.py
    -> testraw/PB200001.ORF, testraw/twelve_layout.npz (and copies in out/mock/)
    OMP_NUM_THREADS=2 uv run python scripts/chart.py --selftest    # simulated development read back with read_mock

Geometry, white lattice, header and encoder of make_mock2.py (96 x 72 patches of 48 x 48 raw pixels, 6,804 patches
plus 108 lattice whites, the header of the blanked PB130001.ORF). The patches are chosen in the stage-7 input space:
8-bit JPEG Y, Cb, Cr that the transparent film (identity matrix, tone curves and chroma curves, Natural's gain 282,
no six-axis) gives with WB 5300 K (520 / 470) and stage 7 off, inverted through model2 (camera-checked within
0.3 L*, ../2026-11-20-film-camera-round/NOTES.md). Kinds:
  1 grid: hue every 5 deg (alternate chroma rings shifted 2.5 deg) x chroma 5..56 (7) x Y 40..215 (8), in gamut
  2 hue ring: Y 120, chroma 30, every 1 deg (360)
  3 chroma lines: 12 hues (7.5 + 30 k deg), Y 110, chroma 0 .. gamut edge in steps of 1.5
  4 luma lines: greys and 6 hues at chroma 16, Y 6 .. 249 in steps of 3
  5 references: 300 patches with the raw values of PB130001.ORF patches (sid = index there): the scene check
  6 25 identical mid greys (noise)
  8 filler: random in-gamut colours, placed in the border first (the lens correction crops it)
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
FP = os.path.abspath(os.path.join(EXP, "..", "2026-11-09-film-portra"))
sys.path.insert(0, FP)
import mocklib as m  # noqa: E402
import model2  # noqa: E402
import chroma as C  # noqa: E402

WB = np.array([520 / 256, 1.0, 470 / 256])
M = m.M5300
UMAX = 3790.0
GAIN = 282
SAT = GAIN * model2.SAT_PER_GAIN
NPATCH = 96 * 72 - 108


def to_raw(Y, cb, cr, look=None):
    """8-bit Y and signed Cb, Cr (stage-7 input, transparent film) -> raw RGB (float) and a validity flag."""
    look = m.IDENT if look is None else look
    Y, cb, cr = (np.asarray(a, float) for a in (Y, cb, cr))
    y = np.interp(4 * Y, look, m.X)
    b0 = y + cr / (0.713 * SAT)
    b2 = y + cb / (0.564 * SAT)
    b1 = (y - 0.299 * b0 - 0.114 * b2) / 0.587
    g = 4 * np.stack([b0, b1, b2], -1)
    v = np.sign(g) * np.interp(np.abs(g), m.BASE[:-3], m.X[:-3]) / model2.K
    u = v @ np.linalg.inv(M).T
    raw = u / WB
    ok = (np.abs(g) < m.BASE[-4]) & True
    ok = ok.all(-1) & (raw >= 2).all(-1) & (raw <= UMAX - 2).all(-1) & (np.interp(4 * Y, look, m.X) < 254)
    return raw, ok


def render(raw, gain=GAIN, chroma=None, look=None):
    """Raw RGB -> stage-7 input: 8-bit Y and signed Cb, Cr (transparent film, or the given gain / chroma / look)."""
    kw = {} if look is None else {"look": look}
    rgb = model2.render(raw * WB, m.IDG, gain, np.zeros(6), np.zeros(6), M, chroma=chroma, clip=False, **kw)
    y, cb, cr = C.ycc(rgb)
    return y, cb - 128, cr - 128


def targets(rng):
    rows = []                                   # (kind, Y, cb, cr)

    def add(kind, Y, r, h):
        Y, r, h = np.broadcast_arrays(np.asarray(Y, float), np.asarray(r, float), np.radians(np.asarray(h, float)))
        for a, b, c in zip(Y.ravel(), (r * np.cos(h)).ravel(), (r * np.sin(h)).ravel()):
            rows.append((kind, a, b, c))
    for ci, r in enumerate((5, 10, 16, 24, 33, 44, 56)):
        for Y in (40, 65, 90, 115, 140, 165, 190, 215):
            add(1, Y, r, np.arange(72) * 5.0 + 2.5 * (ci % 2))
    add(2, 120, 30, np.arange(360.0))
    for h in 7.5 + 30 * np.arange(12):
        add(3, 110, np.arange(0, 80, 1.5), h)
    for h in (None, 0, 60, 120, 180, 240, 300):
        add(4, np.arange(6, 250, 3), 0 if h is None else 16, 0 if h is None else h)
    add(6, np.full(25, 118.0), 0, 0)
    t = np.array(rows)
    raw, ok = to_raw(t[:, 1], t[:, 2], t[:, 3])
    keep = ok | (t[:, 0] == 4)                  # luma lines: keep the ends (clipped there by the camera too)
    raw = np.clip(raw, 0, UMAX)
    t = t.copy(); t[~ok, 1:] = np.nan             # kept out-of-gamut luma-line ends: no target
    return t[keep], raw[keep]


def build():
    import make_mock2 as mm
    rng = np.random.default_rng(20261120)
    t, raw = targets(rng)
    L2 = np.load(os.path.join(FP, "testraw", "mock2a_layout.npz"))
    k2 = L2["kind"]
    ref = np.concatenate([np.flatnonzero(k2 == 5)[:200], np.flatnonzero(k2 == 7)[:100]])
    kind = np.concatenate([t[:, 0], np.full(len(ref), 5)]).astype(int)
    tgt = np.concatenate([t[:, 1:], np.full((len(ref), 3), np.nan)])
    raws = np.concatenate([raw, L2["raw_rgb"][ref].astype(float)])
    sid = np.concatenate([np.full(len(t), -1), ref])
    n_fill = NPATCH - len(kind)
    assert n_fill > 0, len(kind)
    fill_t, fill_r = [], []
    while sum(len(x) for x in fill_r) < n_fill:
        Y = rng.uniform(20, 230, 4000); r = rng.uniform(0, 60, 4000); h = rng.uniform(0, 2 * np.pi, 4000)
        rr, ok = to_raw(Y, r * np.cos(h), r * np.sin(h))
        fill_t.append(np.stack([Y, r * np.cos(h), r * np.sin(h)], 1)[ok]); fill_r.append(rr[ok])
    fill_t = np.concatenate(fill_t)[:n_fill]; fill_r = np.concatenate(fill_r)[:n_fill]
    kind = np.concatenate([kind, np.full(n_fill, 8)])
    tgt = np.concatenate([tgt, fill_t]); raws = np.concatenate([raws, fill_r]); sid = np.concatenate([sid, np.full(n_fill, -1)])
    rawi = np.clip(np.round(raws), 0, UMAX).astype(np.int32)
    pos = mm.place(kind, None, kind == 8, rng)
    os.makedirs(os.path.join(EXP, "out", "mock"), exist_ok=True)
    cwd = os.getcwd(); os.chdir(EXP)
    try:
        n = mm.write("PB200001", pos, rawi, dict(tag="twelve", kind=kind, sid=sid, weight=np.zeros(len(kind))))
    finally:
        os.chdir(cwd)
    lay = dict(np.load(os.path.join(EXP, "out", "mock", "twelve_layout.npz")))
    nl = len(lay["pos"]) - len(kind)
    lay["target"] = np.concatenate([np.full((nl, 3), np.nan), tgt])
    np.savez(os.path.join(EXP, "out", "mock", "twelve_layout.npz"), **lay)
    os.makedirs(os.path.join(EXP, "testraw"), exist_ok=True)
    import shutil
    shutil.copy(os.path.join(EXP, "out", "mock", "PB200001.ORF"), os.path.join(EXP, "testraw", "PB200001.ORF"))
    shutil.copy(os.path.join(EXP, "out", "mock", "twelve_layout.npz"), os.path.join(EXP, "testraw", "twelve_layout.npz"))
    # round trip through the forward model
    y, cb, cr = render(rawi.astype(float))
    good = np.isfinite(tgt[:, 0])
    err = np.abs(np.stack([y, cb, cr], 1)[good] - tgt[good])
    print(f"PB200001.ORF: {n} bytes; patches {len(kind)}:", {int(k): int((kind == k).sum()) for k in np.unique(kind)})
    print(f"model round trip (raw rounded): max |dY, dCb, dCr| = {err.max(0).round(2)}, mean {err.mean(0).round(3)}")
    return lay


def layout_path():
    p = os.path.join(EXP, "testraw", "twelve_layout.npz")
    return p if os.path.exists(p) else os.path.join(EXP, "out", "mock", "twelve_layout.npz")


def selftest():
    """Paint a simulated development (the model, stage 7 off) into a distorted 4608 x 3456 JPEG, read it back."""
    import cv2
    import read_mock as rm
    sys.path.insert(0, HERE)
    import simulate
    lay = np.load(layout_path())
    rgb = simulate.patch_rgb(lay["raw_rgb"].astype(float), "CTRL", "clear")
    path = os.path.join(EXP, "out", "selftest.jpg")
    simulate.paint(lay, rgb, path)
    rm.LAYOUTS = {"twelve": layout_path()}
    d, stats, _, jpg = rm.read(path, wb=lay["WB"], M=lay["M"], tag="twelve")
    rm.report(d, stats, {})
    ok = np.isfinite(d["jpg"][:, 0]) & (d["spread"] < 4)
    inner = ok & (lay["kind"] != 8) & (lay["kind"] != 0)
    err = np.abs(d["jpg"][ok] - np.clip(rgb[ok], 0, 255))
    print(f"selftest: patches read {ok.sum()} of {len(ok)}; non-filler patches read {inner.sum()} of "
          f"{((lay['kind'] != 8) & (lay['kind'] != 0)).sum()}; |error| mean {err.mean():.3f}, 99.9th pct "
          f"{np.percentile(err, 99.9):.2f} codes; by kind (read / all):",
          {int(k): f"{int((ok & (lay['kind'] == k)).sum())}/{int((lay['kind'] == k).sum())}" for k in np.unique(lay["kind"])})
    assert inner.sum() > 0.97 * ((lay["kind"] != 8) & (lay["kind"] != 0)).sum() and err.mean() < 1.0
    print("selftest PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        build()

"""Simulated camera developments of the probe (model2 for stages 1-6, tables.apply for stage 7). Research code.

    OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/simulate.py OUTDIR [--truth NAME]
    -> OUTDIR/SIM_ART01.JPG ... SIM_ART12.JPG, SIM_ADOBE_ART01.JPG, SIM_ADOBE_ART03.JPG, OUTDIR/truth.json

The stage-7 position (order) is an option: "after" (on the final Y, Cb, Cr), "mid" (after the saturation gain,
before the chroma curves), "before6" (before the gain), "before5" (before the look curve and stage 6).
TRUTHS holds the hypotheses the analysis is tested on; each is a dict of tables.NOMINAL options plus "order",
"adobe" (True: P+82 selects table B in Adobe RGB) and "cs_matrix" (an Adobe RGB development's change of matrix).
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
FP = os.path.abspath(os.path.join(EXP, "..", "2026-11-09-film-portra"))
sys.path.insert(0, FP)
sys.path.insert(0, HERE)
import mocklib as m  # noqa: E402
import model2  # noqa: E402
import chroma as C  # noqa: E402
import tables as T  # noqa: E402
import films  # noqa: E402

XP1_LOOK = 0x7E75F2F0
BASE = 0x7E421020
_blk = open(os.path.join(EXP, "..", "..", "build", "blocks", "OLY_E_101_1600_0000_0000.BIN.block0.bin"), "rb").read()
TABLE_A = _blk[0x7E76C3C8 - BASE:0x7E76C3C8 - BASE + T.TABLE_BYTES]
TABLE_B = _blk[0x7E76CF9C - BASE:0x7E76CF9C - BASE + T.TABLE_BYTES]
M_ADOBE = np.array([[1.30, -0.22, -0.08], [-0.06, 1.10, -0.04], [0.02, -0.10, 1.08]])   # stand-in for the matrix change

TRUTHS = {
    "nominal": dict(order="after", adobe=True),
    "other": dict(sign=-1.0, h0=7.0, kc=3.1, ky=4.0, kl=0.25, ks=0.5, sat="add", window="clamp", roles="swapped",
                  order="mid", adobe=False, kh=360 / T.HUE_TURN),
}


def odd(x, xp, fp):
    return np.sign(x) * np.interp(np.abs(x), xp, fp)


def entry_table(n, adobe=False):
    t = T.ENTRIES[n - 1][3]
    if t is None:
        return TABLE_B if adobe else TABLE_A
    return T.table({"HUEMAP": "MARKER"}.get(t, t) if adobe else t)


def pipeline(raw, n, truth, adobe_dev=False, wb=None, stage7=True):
    """raw RGB (n, 3) -> 8-bit RGB (float, unclipped) of ART n."""
    o = {**T.NOMINAL, **{k: v for k, v in truth.items() if k in T.NOMINAL}}
    film = T.ENTRIES[n - 1][4]
    gain, s1, s2 = films.FILMS[film]
    (c1, c2) = films.chroma_bytes(s1, s2)
    look = m.fl.table(XP1_LOOK) if n == 12 else m.IDENT
    wb = np.array([520 / 256, 1.0, 470 / 256]) if wb is None else wb
    P = m.M5300 @ (M_ADOBE if adobe_dev else np.eye(3))
    v = (raw * wb) @ P.T
    g = odd(model2.K * v, m.X, m.BASE)
    b = g / 4.0
    y = b @ m.LUMA
    sat = gain * model2.SAT_PER_GAIN
    cb0, cr0 = 0.564 * (b[:, 2] - y), 0.713 * (b[:, 0] - y)
    order = truth.get("order", "after")
    t = T.decode(entry_table(n, adobe_dev and truth.get("adobe", True)))
    s7 = (lambda Y, cb, cr: T.apply(t, Y, cb, cr, o)) if stage7 else (lambda Y, cb, cr: (Y, cb, cr))
    if order == "before5":
        y, cb0, cr0 = s7(y, cb0 * 1.078, cr0 * 1.078)
        cb0, cr0 = cb0 / 1.078, cr0 / 1.078
    yl = np.interp(np.maximum(y, 0), m.X, look) / 4.0
    if order == "before6":
        yl, cb0, cr0 = s7(yl, cb0 * 1.078, cr0 * 1.078)     # the stage sees a Natural-like chroma scale
        cb0, cr0 = cb0 / 1.078, cr0 / 1.078
    cb = np.clip(sat * cb0, -model2.CLAMP, model2.CLAMP)
    cr = np.clip(sat * cr0, -model2.CLAMP, model2.CLAMP)
    if order == "mid":
        yl, cb, cr = s7(yl, cb, cr)
    cb = C.ev_bytes(cb + 128, *c1) - 128
    cr = C.ev_bytes(cr + 128, *c2) - 128
    if order == "after":
        yl, cb, cr = s7(yl, cb, cr)
    return C.rgb(yl, cb + 128, cr + 128)


def patch_rgb(raw, tname, film):
    """Stage 7 off, the transparent film (chart.py self-test)."""
    return pipeline(raw, 1, {"order": "after"}, stage7=False)


def paint(lay, rgb, path, seed=0, noise=0.8):
    import cv2
    H, W, P, X0, Y0 = 3472, 4640, int(lay["P"]), int(lay["X0"]), int(lay["Y0"])
    img = np.zeros((H, W, 3), np.float32)
    for (r, c), v in zip(lay["pos"], np.clip(rgb, 0, 255)):
        img[Y0 + r * P:Y0 + (r + 1) * P, X0 + c * P:X0 + (c + 1) * P] = v
    JW, JH, OX, OY = 4608, 3456, 16, 8
    yy, xx = np.mgrid[0:JH, 0:JW].astype(np.float32)
    cx, cy = JW / 2 + 3, JH / 2 - 2
    r2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (JW / 2) ** 2
    k = -0.027
    mx = cx + (xx - cx) * (1 + k * r2) + OX
    my = cy + (yy - cy) * (1 + k * r2) + OY
    sim = cv2.remap(img, mx, my, cv2.INTER_LINEAR)
    sim += np.random.default_rng(seed).normal(0, noise, sim.shape).astype(np.float32)
    cv2.imwrite(path, cv2.cvtColor(np.clip(np.round(sim), 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, 95])


def main():
    out = sys.argv[1]
    name = sys.argv[sys.argv.index("--truth") + 1] if "--truth" in sys.argv else "nominal"
    truth = TRUTHS[name]
    os.makedirs(out, exist_ok=True)
    sys.path.insert(0, HERE)
    import chart
    lay = np.load(chart.layout_path())
    raw = lay["raw_rgb"].astype(float)
    for n in range(1, 13):
        paint(lay, pipeline(raw, n, truth), os.path.join(out, f"SIM_ART{n:02d}.JPG"), seed=n)
    for n in (1, 3):
        paint(lay, pipeline(raw, n, truth, adobe_dev=True), os.path.join(out, f"SIM_ADOBE_ART{n:02d}.JPG"), seed=20 + n)
    json.dump(dict(name=name, **truth), open(os.path.join(out, "truth.json"), "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()

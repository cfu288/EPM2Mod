"""Monochrome camera model for the Grainy Film entry (art codes 74 / 83), and the Double-X target.

Uses the camera model of experiments/2026-11-09-film-portra (model2.py, mocklib.py). Import this module with that
folder as the working directory (its scripts load their data by relative path); fit_mono.py and report_mono.py do so.

The model (NOTES.md section 1 gives the evidence for each step):

    u (white-balanced raw) -> matrix P (ColorMatrix x art matrix) -> base gamma -> tone curve per channel
      -> luma = 0.299 R' + 0.587 G' + 0.114 B' -> look table of the code (0x7E75B6F0 for 74) = Y_in
      -> grain program: x = g(Y_in), noise added to x, then the contrast table T (0x7E75EEF0 for 74 and 83).

A film look in this entry is the matrix P and one tone curve D (Y_in -> picture value). D is stored as the
grain program's table, T(x) = D(g^-1(x)), and as the look table 0x7E7620F0 that the code uses where no grain
program runs (live view and movie variants of the look stage). The tone curves per channel stay stock: the
tone-curve hash has no place that the firmware would find for code 74 (its key meets the entry of code 70).

The picture value of a patch (the median of its pixels, as read_mock.py reads it) is T(g(Y_in)).
g is not read from the firmware: it is measured, from the test RAW developed with the stock filter
(reading A_grainy_film) and the stock table T. results/grain-transfer.json holds it.
"""
import json, os, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
FILM = HERE.parents[1] / "2026-11-09-film-portra"
RESULTS = HERE.parent / "results"
if Path.cwd().resolve() != FILM:
    os.chdir(FILM)
sys.path.insert(0, str(FILM))
_argv, sys.argv = sys.argv, ["x"]
import fit_xp9 as f  # noqa: E402
from mocklib import *  # noqa: E402,F401,F403
import model2 as M2  # noqa: E402
sys.argv = _argv

LOOK_74 = 0x7E75B6F0          # look table of art code 74 in the development of the picture (op class 0 / 1)
GRAIN_TABLE_74 = 0x7E75EEF0   # contrast table of codes 74 and 83 in the grain program's jobs (op class 2)
GRAIN_TABLE_104 = 0x7E7600F0  # the same for Grainy Film II (codes 104 and 105)
LUT_DIR = "out/lut/spektrafilm_dev6cd00c8_doublex_2302_1lut_vlog_srgb"
LUT = LUT_DIR + "/lut_dev6cd00c8_doublex_2302.cube"
TRANSFER = RESULTS / "grain-transfer.json"
B6, B8 = fl.table(LOOK_74), fl.table(fl.IDENTITY)
T_STOCK = fl.table(GRAIN_TABLE_74)
ZERO6 = np.zeros(6)


def y_in(u, P, G=IDG, look=B6):
    """Luma of the developed picture, before the grain program (0..255)."""
    return M2.pre(M2.six(u, ZERO6, ZERO6, P), G, 0.0, look=look)[:, 1]


def measure_transfer():
    """Measure g from the stock rendering: bin medians of T_stock^-1(camera luma) against the model's Y_in."""
    d = load("A_grainy_film"); yj = d["jpg"] @ LUMA; ok = np.isfinite(yj) & (yj > 3) & (yj < 252)
    yi = y_in(d["u"], d["M"]); gi = np.interp(yj[ok], T_STOCK / 4.0, X)
    edges = np.arange(np.floor(yi[ok].min()), np.ceil(yi[ok].max()) + 4, 4); idx = np.digitize(yi[ok], edges)
    keep = [i for i in range(1, len(edges)) if (idx == i).sum() >= 8]
    bx = np.array([yi[ok][idx == i].mean() for i in keep]); by = np.maximum.accumulate(np.array([np.median(gi[idx == i]) for i in keep]))
    sd = np.array([np.median(d["spread"][ok][idx == i]) for i in keep])
    return bx, by, sd


def load_transfer():
    if not TRANSFER.exists():
        bx, by, sd = measure_transfer()
        TRANSFER.write_text(json.dumps({"what": "g of the grain program of art code 74, measured: x = g(Y_in); knots",
                                        "source": "reading A_grainy_film (test RAW A, RAW Data Edit with stock Grainy Film I) and table 0x7E75EEF0",
                                        "y_in": bx.round(2).tolist(), "x": by.round(2).tolist(), "spread_in_patch": sd.round(1).tolist()}, indent=1) + "\n")
    t = json.loads(TRANSFER.read_text())
    return np.array(t["y_in"]), np.array(t["x"])


_BX, _BY = load_transfer()
_LO, _HI = np.polyfit(_BX[:5], _BY[:5], 1), np.polyfit(_BX[-5:], _BY[-5:], 1)
MEASURED_RANGE = (float(_BX[0]), float(_BX[-1]))


def g_of(y):
    """The measured transfer; a straight line outside the measured range."""
    y = np.asarray(y, float)
    return np.where(y < _BX[0], np.polyval(_LO, y), np.where(y > _BX[-1], np.polyval(_HI, y), np.interp(y, _BX, _BY)))


def final(u, P, G=IDG, table=T_STOCK, look=B6):
    """Picture value (0..255) of a patch in the Grainy Film entry with matrix P, curves G and grain table."""
    return np.interp(np.clip(g_of(y_in(u, P, G, look)), 0, 255), X, table / 4.0)


def monotone(u, P):
    """Stock Monotone: the luma of the Natural rendering (camera check: results/model-check.txt)."""
    return y_in(u, P, IDG, B8)


LIVE_LOOK_74 = 0x7E7620F0     # look table of codes 74 and 83 where no grain program runs (live view, movie variants)
SIGMA_X = 19.5                # spread of the grain program's noise in x (fit to the spread inside the stock patches)
_YG = np.linspace(0, 255, 1021)


def g_inverse(x):
    """Y_in for a value x of the grain program (g rises everywhere)."""
    return np.interp(x, g_of(_YG), _YG)


def tone_of_knots(q):
    """A rising tone curve D (256 values, 0..255) from 25 knot steps."""
    return np.interp(X, np.linspace(0, 255, len(q)), np.minimum(np.cumsum(np.asarray(q) ** 2), 255.0))


def grain_table(D):
    """The contrast table of the grain program (10-bit) that gives the tone D: T(x) = D(g^-1(x))."""
    return np.clip(np.round(4.0 * np.interp(g_inverse(X.astype(float)), X, D)), 0, 1023)


def film(u, P, D):
    """Picture value of a patch in the entry with matrix P and tone D (through the rounded table)."""
    return np.interp(np.clip(g_of(y_in(u, P)), 0, 255), X, grain_table(D) / 4.0)


def grey_lab(y):
    return lab(np.repeat(np.clip(np.asarray(y, float), 0, 255)[:, None], 3, 1))


def target_gain():
    """The dev LUT builder scales its input (bundle.json input_exposure.gain); the 0.3.4 cubes had no gain."""
    return float(json.load(open(LUT_DIR + "/bundle.json"))["input_exposure"]["gain"])


_cube = None


def target(vs):
    """Neutral picture value (0..255) of the Double-X target for scene-linear sRGB in raw units.

    The cube gives sRGB-coded R = G = B within 0.3 code (a black-and-white print has no tint in this
    simulation); the value used is the mean of the three, so the target is neutral grey exactly.
    The input is divided by the builder's gain so that scene 18 % grey is the film's mid grey, as in the colour fits.
    """
    global _cube
    if _cube is None:
        _cube = fl.load_cube(LUT) + (target_gain(),)
    cube, size, gain = _cube
    rgb = np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(vs, 0) / fl.V_GRAY * 0.18 / gain, "vlog")), 0, 1) * 255
    return rgb.mean(1)


SETS = ((5, "natural"), (8, "skin"), (7, "ColorChecker x5 EV"), (6, "grays"), (9, "hold-out"), (2, "dense grays"))


def score(y, t, kind, ok):
    """Per patch set: mean |dL*| and mean dE2000 between two grey renderings."""
    a, b = grey_lab(y), grey_lab(t); dl, dd = np.abs(a[:, 0] - b[:, 0]), de(a, b)
    return {name: (float(dl[ok & (kind == k)].mean()), float(dd[ok & (kind == k)].mean())) for k, name in SETS}

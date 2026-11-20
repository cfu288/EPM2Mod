"""The probe's film file: 12 looks, each "transparent" (stage 7 isolated) except ART 11 (saturation gain and unequal
chroma curves). Research code.

    OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/films.py
    -> out/films/clear.npz, out/films/stage6.npz, out/films/twelve-looks.json, build/twelve-probe/EPM2LOOK.BIN

Transparent ("clear"): identity art matrix (256 on the diagonal), identity tone curves (the film curve after the stock
default table: 0..1023), six-axis 0, Natural's saturation gain 282, straight chroma curves (y = x at the knots,
slope 128). Stage 6 ("stage6", ART 11): gain 423 (1.5 x Natural) and chroma curves that are y = x within +-20 codes
of 128 and flatter outside: the first stored curve slope 0.5, the second 0.75 (unequal, so the run also says which
stored curve is Cb: chroma.py FIRST_IS_CB is still an assumption).
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(EXP, "..", ".."))
sys.path.insert(0, os.path.abspath(os.path.join(EXP, "..", "2026-11-09-film-portra")))
sys.path.insert(0, HERE)
import chroma as C  # noqa: E402
import tables as T  # noqa: E402

GAIN_CLEAR, GAIN_STAGE6 = 282, 423
OUT_FILE = os.path.join(ROOT, "build", "twelve-probe", "EPM2LOOK.BIN")


def curve(slope_out):
    d = C.XK - 128.0
    return 128 + np.sign(d) * np.where(np.abs(d) <= 20, np.abs(d), 20 + slope_out * (np.abs(d) - 20))


def chroma_bytes(first_slope, second_slope):
    """((x, y, slope) of the first stored curve, (x, y, slope) of the second)."""
    return C.quantise(curve(first_slope)), C.quantise(curve(second_slope))


def fit(gain, first_slope, second_slope):
    (x1, y1, s1), (x2, y2, s2) = chroma_bytes(first_slope, second_slope)
    return dict(G=np.tile(np.arange(1024.0), (3, 1)), gain=np.array(gain), S=np.zeros(6), H=np.zeros(6),
                A=np.diag([256, 256, 256]).astype(np.int64), Cb=np.stack([x1, y1]), Cr=np.stack([x2, y2]),
                Cb_slope17=s1.astype(np.int64), Cr_slope17=s2.astype(np.int64), model=np.array("model2"))


FILMS = {"clear": (GAIN_CLEAR, 1.0, 1.0), "stage6": (GAIN_STAGE6, 0.5, 0.75)}
NAMES = {"CTRL": "T CTRL", None: "T NAT A", "HUEMAP": "T HUEMAP", "MAGL": "T MAG L", "MAGS": "T MAG S",
         "MAGH": "T MAG H", "CURVES": "T CURVES", "OVERLAP": "T OVERLAP", "WINDOW": "T WINDOW", "BOX": "T BOX"}


def main():
    d = os.path.join(EXP, "out", "films")
    os.makedirs(d, exist_ok=True)
    for name, args in FILMS.items():
        np.savez(os.path.join(d, f"{name}.npz"), **fit(*args))
    looks = []
    for n, entry, code, tname, film, what in T.ENTRIES:
        nm = {11: "T BOX GAIN", 12: "T BOX LOOK"}.get(n, NAMES[tname])
        looks.append({"entry": entry, "name": nm, "fit": os.path.relpath(os.path.join(d, f"{film}.npz"), ROOT)})
    lst = os.path.join(d, "twelve-looks.json")
    with open(lst, "w") as f:
        json.dump({"looks": looks}, f, indent=1)
        f.write("\n")
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    subprocess.run(["uv", "run", "epm2mod", "films", "pack", os.path.relpath(lst, ROOT), "-o",
                    os.path.relpath(OUT_FILE, ROOT)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

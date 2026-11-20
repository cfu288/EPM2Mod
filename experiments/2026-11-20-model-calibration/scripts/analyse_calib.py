"""Analysis of the calibration run (NOTES.md §5). Research code.

    OMP_NUM_THREADS=2 uv run --with colour-science python experiments/2026-11-20-model-calibration/scripts/analyse_calib.py
    -> stdout and results/analyse.txt; uses the readings of read_calib.py (out/readings/f<n>/)

Q4: the calibration films K01-K24 (ART 7-12 on PB130001) against model2, as check_film.py: camera vs model.
Q1-Q3: the measured change of each test table (ART k minus ART 1, same film, same RAW) against the change the stage
rules predict from the ART 1 development, for each hypothesis: where stage 7 sits (before the saturation gain, between
the gain and the chroma curves, after the chroma curves) and whether saturation adds or multiplies. The constants
(chroma, saturation, lightness and hue scale) are fitted per hypothesis over all files; the residual decides.
"""
import json, os, sys
import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(EXP, "..", ".."))
FP = os.path.join(ROOT, "experiments", "2026-11-09-film-portra")
TW = os.path.join(ROOT, "experiments", "2026-11-20-twelve-region", "scripts")
sys.path[:0] = [HERE, FP, TW]
argv = sys.argv; sys.argv = ["x"]
_cwd = os.getcwd(); os.chdir(FP)
import fit_xp9 as f  # noqa: E402
os.chdir(_cwd)
from mocklib import lab, de  # noqa: E402
import chroma as C  # noqa: E402
import model2 as M2  # noqa: E402
import tables as T  # noqa: E402
import design as D  # noqa: E402

RD = os.path.join(EXP, "out", "readings")
SAT_CLEAR = 282 * M2.SAT_PER_GAIN
LINES = []


def p(s=""):
    print(s, flush=True); LINES.append(s)


def reading(n, role):
    path = os.path.join(RD, f"f{n}", f"{role}.npz")
    return dict(np.load(path)) if os.path.exists(path) else None


class Fit(dict):
    """A fit as a dict, with the .files list that model2.chroma_of reads."""
    @property
    def files(self):
        return list(self)


def film_of(n, art):
    if art <= 6:
        fid = D.FILE_FILM[n]
        z = dict(np.load(os.path.join(EXP, "films", "clear.npz") if fid == "clear" else os.path.join(ROOT, D.CAT[fid]["fit"])))
    else:
        z = dict(np.load(os.path.join(EXP, "films", f"k{6 * (n - 1) + art - 6:02d}.npz")))
    z.setdefault("P", f.renormalise(np.asarray(z["A"])) / 128.0)        # the clear film stores only its art table
    return Fit(z)


# ---- Q4 --------------------------------------------------------------------------------------------------------
def q4(files):
    p("Q4  model2 on the calibration films (PB130001; camera vs model, ΔE2000; camera ColorMatrix = expected?)")
    p(f"    {'film':6s} {'what':12s} {'natural':>8s} {'ColorChecker':>13s} {'skin':>6s} {'grays':>6s}  matrix")
    rows = []
    for n in files:
        for art in range(1, 13):
            d = reading(n, f"A_ART{art}")
            if d is None or (art > 1 and art <= 6):
                continue
            z = film_of(n, art)
            J, k, ok = d["jpg"], d["kind"], np.isfinite(d["jpg"][:, 0]) & (d["spread"] < 3)
            P = M2.render(d["u"], z["G"], M2.gain_of(z), z["S"], z["H"], z["P"], M2.chroma_of(z))
            unc = (J.min(1) > 2) & (J.max(1) < 253)
            dm = de(lab(np.nan_to_num(J)), lab(P))
            g = lambda kk: dm[ok & unc & (k == kk)].mean()
            same = np.array_equal((d["M"] * 256).round().astype(int).ravel(), (f.renormalise(z["A"]) * 2).astype(int).ravel())
            name = "ART1 " + D.FILE_FILM[n] if art == 1 else f"K{6 * (n - 1) + art - 6:02d}"
            what = "reference" if art == 1 else json.load(open(os.path.join(EXP, "films", "design.json")))["calibration"][6 * (n - 1) + art - 7]["what"]
            rows.append((name, what, g(5), g(7), g(8), g(6)))
            p(f"    {name:6s} {what:12s} {g(5):8.2f} {g(7):13.2f} {g(8):6.2f} {g(6):6.2f}  {'yes' if same else 'NO'}")
    return rows


# ---- Q1-Q3 -----------------------------------------------------------------------------------------------------
def sets(files, per=2500, seed=1, arts=(2, 3, 4, 5, 6)):
    """(n, raw, art, film, table, X0, X1) with a fixed random sample of usable patches per set."""
    rng = np.random.default_rng(seed); tb = D.tables(); out = []
    for n in files:
        for raw in ("T", "A"):
            a1 = reading(n, f"{raw}_ART1")
            if a1 is None:
                continue
            for art in arts:
                dk = reading(n, f"{raw}_ART{art}")
                X0, X1 = a1["jpg"], dk["jpg"]
                m = np.isfinite(X0[:, 0]) & np.isfinite(X1[:, 0]) & (a1["spread"] < 3) & (dk["spread"] < 3)
                m &= (X0.min(1) > 3) & (X0.max(1) < 252) & (X1.min(1) > 3) & (X1.max(1) < 252)
                idx = np.flatnonzero(m)
                idx = rng.choice(idx, min(per, len(idx)), replace=False)
                out.append(dict(n=n, raw=raw, art=art, z=film_of(n, art), t=T.decode(tb[D.TABLE_OF[art][1]]),
                                X0=X0[idx], X1=X1[idx]))
    return out


def predict(s, pos, sat, k):
    z, X0 = s["z"], s["X0"]
    ch = M2.chroma_of(z); satz = M2.gain_of(z) * M2.SAT_PER_GAIN
    x = np.linspace(0, 255, 2041)
    if pos == "post" or ch is None:
        X = X0
    else:
        cbt, crt = C.ev_bytes(x, *ch[0]), C.ev_bytes(x, *ch[1])
        y, cb, cr = C.ycc(X0); X = C.rgb(y, np.interp(cb, cbt, x), np.interp(cr, crt, x))
    y, cb, cr = C.ycc(X)
    sc = SAT_CLEAR / satz if pos == "pre" else 1.0
    cb, cr = (cb - 128) * sc, (cr - 128) * sc
    o = dict(D_O, kc=k[0])
    hue, chroma, luma, th = T.coords(y, cb, cr, o)
    W, E = T.weights(s["t"], hue, chroma, luma + o["ky_off"], o)
    dh, ds, dl = (W["H"] * E[:, 0:1]).sum(0), (W["S"] * E[:, 1:2]).sum(0), (W["L"] * E[:, 2:3]).sum(0)
    c = np.hypot(cb, cr)
    c2 = np.maximum(c + k[1] * ds, 0) if sat == "add" else c * np.maximum(1 + k[1] * ds / 256, 0)
    t2 = np.radians(th + k[3] * dh * 360 / T.HUE_TURN)
    out = C.rgb(y + k[2] * dl, c2 * np.cos(t2) / sc + 128, c2 * np.sin(t2) / sc + 128)
    if pos != "post" and ch is not None:
        out = C.apply(out, ch[0], ch[1], stored=True)
    return np.clip(out, 0, 255)


D_O = dict(sign=1.0, h0=0.13, kc=5.96, ky=4.049, ky_off=-4.6, kl=0.239, ks=0.238, kh=360 / T.HUE_TURN,
           window="hard", sat="add", roles="stock", norm=T.FULL, chroma_metric="euclid")
K0 = {"add": [5.96, 0.238, 0.239, 1.0], "mul": [5.96, 1.0, 0.239, 1.0]}


def q123(files, arts=(2, 3, 4, 5, 6)):
    S = sets(files, arts=arts)
    p(""); p(f"Q1-Q3  tables of ART {list(arts)}: change, measured (ART k − ART 1) against predicted; {len(S)} sets of up to 2500 patches")
    best = {}
    for pos in ("pre", "mid", "post"):
        for sat in ("add", "mul"):
            def res(k):
                return np.concatenate([(predict(s, pos, sat, k) - s["X1"]).ravel() for s in S])
            r = least_squares(res, K0[sat], x_scale=[1, 0.1, 0.05, 0.1], max_nfev=60, loss="soft_l1", f_scale=2.0)
            k = r.x
            per = {}
            for s in S:
                e = predict(s, pos, sat, k) - s["X1"]; chg = s["X1"] - s["X0"]
                mv = np.abs(chg).max(1) > 1.5
                per[(s["n"], s["raw"], s["art"])] = (np.sqrt((chg[mv] ** 2).mean()) if mv.any() else 0,
                                                     np.sqrt((e[mv] ** 2).mean()) if mv.any() else 0, mv.sum())
            tot = np.sqrt(np.mean([v[1] ** 2 for v in per.values()]))
            best[(pos, sat)] = (tot, k, per)
            p(f"   stage 7 {pos:4s} the gain/curves, saturation {sat}: residual on moved patches rms {tot:.2f} codes; "
              f"constants chroma {k[0]:.2f}/code, saturation {k[1]:.4f}, lightness {k[2]:.4f}, hue x{k[3]:.3f}")
    (pos, sat), (tot, k, per) = min(best.items(), key=lambda kv: kv[1][0])
    p(f"   best: {pos}, {sat}; per set (change rms -> residual rms, moved patches):")
    for n in files:
        line = []
        for raw in ("T", "A"):
            for art in arts:
                if (n, raw, art) in per:
                    c_, e_, m_ = per[(n, raw, art)]
                    line.append(f"{raw}{art} {c_:.1f}->{e_:.1f}")
        p(f"     file {n} ({D.FILE_FILM[n]}): " + ", ".join(line))
    p("     (T = PB200002, A = PB130001; 2 Natural A, 3 Portra, 4 Velvia, 5 Ektachrome, 6 Natural A flat curves)")
    return best


def main():
    files = [n for n in (1, 2, 3, 4) if os.path.exists(os.path.join(RD, f"f{n}", "roles.json"))]
    p(f"files read: {files}")
    q4(files)
    q123(files)
    q123(files, arts=(2, 3, 4, 5))
    q123(files, arts=(6,))
    os.makedirs(os.path.join(EXP, "results"), exist_ok=True)
    open(os.path.join(EXP, "results", "analyse.txt"), "w").write("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()

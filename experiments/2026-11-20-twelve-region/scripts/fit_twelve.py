"""Fit a 12-region table (stage 7) for each film, on top of the film as the camera renders it now. Research code.

    OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/fit_twelve.py [FILM_ID ...]
    -> out/twelve/<id>.bin (3028 B table), out/twelve/<id>.json (values), out/twelve/report.txt

Anchored, model-free outside stage 7: the camera's reading of PB130001 developed with the film on films-look-exif
(readings CA_/CB_/CC_<id>, NOTES of 2026-11-20-film-camera-round §7) is un-done through the film's chroma curves and
saturation gain, the stage is applied with the rules measured on the camera (NOTES.md §8), and the film's gain and
chroma curves are applied again. Stage 7 sits before the saturation gain and the chroma curves (§8, small margin).
Clipped patches keep their measured value and are not fitted.

Table design: 12 records, hue windows 60 deg wide centred every 30 deg with a tent along hue (neighbours sum to 1),
chroma from 5 with a ramp to full at about 11 codes (greys untouched), full luma with a 5-knot curve per record (so a
colour can change differently when dark or bright). Every hue slot gets the tent, every chroma slot the ramp, so the
unresolved slot roles (c1 / c6) do not matter. Hue shifts within +-30 deg (§8: the rule holds there).
"""
import json, os, sys
import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(EXP, "..", ".."))
FP = os.path.join(ROOT, "experiments", "2026-11-09-film-portra")
sys.path[:0] = [FP, HERE]
argv = sys.argv; sys.argv = ["x"]
from mocklib import load, lab, de, fl  # noqa: E402
import chroma as C  # noqa: E402
import model2 as M2  # noqa: E402
import tables as T  # noqa: E402

SAT_CLEAR = 282 * M2.SAT_PER_GAIN          # the probe's films had Natural's gain: the units below are measured at it
O = dict(sign=1.0, h0=0.13, kc=5.96, ky=4.049, ky_off=-4.6, kl=0.239, ks=0.238, kh=360 / T.HUE_TURN,
         window="hard", sat="add", roles="stock", norm=T.FULL, chroma_metric="euclid")
CENTRES = 30.0 * np.arange(12)
KNOTS = np.array([0, 64, 128, 192, 255.0])
CH_RAMP = 69.0                              # chroma (record units) where the ramp reaches full: the first curve point
OUT = os.path.join(EXP, "out", "twelve")


def readings():
    films = json.load(open(os.path.join(ROOT, "data", "films", "catalogue.json")))["films"]
    have = {f[8:-4]: f[5:-4] for f in os.listdir(os.path.join(FP, "out", "mock")) if f[5:8] in ("CA_", "CB_", "CC_") and f.endswith(".npz")}
    return {f["id"]: (have[f["id"]], os.path.join(ROOT, f["fit"])) for f in films if f["id"] in have}


class Film:
    def __init__(self, fid, tag, fit):
        self.id, self.z = fid, np.load(fit)
        A = load(tag)
        cube, size = fl.load_cube(os.path.join(FP, str(self.z["lut"])) if not os.path.isabs(str(self.z["lut"])) else str(self.z["lut"]))
        self.kind, self.ok = A["kind"], A["ok"]
        self.T = lab(np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(A["vs"], 0) / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255)
        k = self.kind
        self.w = np.where(A["weight"] > 0, A["weight"], np.where(k == 8, 20.0, np.where(k == 3, 4.0, np.where(k == 2, 20.0, np.where(k == 10, 0.25, 0.0)))))
        self.J = np.nan_to_num(A["jpg"])
        self.unc = self.ok & (self.J.min(1) > 2) & (self.J.max(1) < 253)
        self.ch = M2.chroma_of(self.z)
        self.sat = M2.gain_of(self.z) * M2.SAT_PER_GAIN
        x = np.linspace(0, 255, 2041)
        cbt, crt = (C.ev_bytes(x, *self.ch[0]), C.ev_bytes(x, *self.ch[1])) if self.ch else (x, x)
        y, cb, cr = C.ycc(self.J)
        self.y, self.cb, self.cr = y, (np.interp(cb, cbt, x) - 128) * SAT_CLEAR / self.sat, (np.interp(cr, crt, x) - 128) * SAT_CLEAR / self.sat
        self.fitm = self.unc & (self.w > 0)
        th = np.degrees(np.arctan2(self.cr, self.cb)) + O["h0"]
        d = (th[:, None] - CENTRES[None, :] + 180) % 360 - 180
        self.wh = np.maximum(0, 1 - np.abs(d) / 30.0)                                       # (n, 12) tents
        self.wc = np.clip((np.hypot(self.cb, self.cr) * O["kc"] - 5) / (CH_RAMP - 5), 0, 1)  # chroma ramp
        self.th = np.radians(th - O["h0"])

    def back(self, y, cb, cr):
        """clear units after stage 7 -> 8-bit RGB through the film's gain and chroma curves."""
        X = C.rgb(y, cb * self.sat / SAT_CLEAR + 128, cr * self.sat / SAT_CLEAR + 128)
        X = C.apply(X, self.ch[0], self.ch[1], stored=True) if self.ch else X
        return np.clip(X, 0, 255)

    def smooth(self, p):
        """The design's stage on every patch, continuous values. p = 12 x (dh deg, ds, dl, 5 luma knots)."""
        q = p.reshape(12, 8)
        wy = np.stack([np.interp(self.y, KNOTS, q[k, 3:]) for k in range(12)], 1)
        W = self.wh * wy * self.wc[:, None]
        dh, ds, dl = W @ q[:, 0], W @ q[:, 1], W @ q[:, 2]
        c = np.maximum(np.hypot(self.cb, self.cr) + O["ks"] * ds, 0)
        t = self.th + np.radians(dh)
        out = self.back(self.y + O["kl"] * dl, c * np.cos(t), c * np.sin(t))
        return np.where(self.unc[:, None], out, self.J)

    def rules(self, table):
        """The encoded table through the measured rules (tables.weights), as the camera should apply it."""
        t = T.decode(table)
        hue, chroma, luma, th = T.coords(self.y, self.cb, self.cr, O)
        W, E = T.weights(t, hue, chroma, luma + O["ky_off"], O)
        dh, ds, dl = (W["H"] * E[:, 0:1]).sum(0), (W["S"] * E[:, 1:2]).sum(0), (W["L"] * E[:, 2:3]).sum(0)
        c = np.maximum(np.hypot(self.cb, self.cr) + O["ks"] * ds, 0)
        t2 = np.radians(th + O["kh"] * dh)
        out = self.back(self.y + O["kl"] * dl, c * np.cos(t2), c * np.sin(t2))
        return np.where(self.unc[:, None], out, self.J)

    def score(self, X):
        dd = de(lab(X), self.T); g = lambda kk: dd[self.ok & (self.kind == kk)].mean()
        ws = self.ok & (self.w > 0)
        return dict(weighted=np.average(dd[ws], weights=self.w[ws]), natural=g(5), colorchecker=g(7), skin=g(8),
                    holdout=g(9), grays=g(6), near_neutral=g(3), edge=g(10))


def encode(p):
    q = p.reshape(12, 8)
    tent = [round(63 * (1 - abs(16 * i - 128) / 128)) for i in range(17)]
    ramp = [0] + [63] * 16
    recs = []
    for k in range(12):
        lv = [round(63 * float(np.interp(16 * i * 255 / 256, KNOTS, q[k, 3:]))) for i in range(17)]
        hue = T.hue_win(CENTRES[k] - 30, CENTRES[k] + 30)
        r = T.Rec(hue=(hue[0], hue[1] - 1), chroma=(5, 1018), luma=(0, 1023), dh=round(q[k, 0] * T.DEG), ds=round(q[k, 1]),
                  dl=round(q[k, 2]), slot={0: T.points(tent), 1: T.points(tent), 6: T.points(tent),
                                           2: T.points(ramp), 3: T.points(ramp), 4: T.points(ramp), 5: T.points(lv)})
        recs.append(r)
    return T.encode(recs, 0xFFF)


def fit(F):
    p0 = np.tile([0, 0, 0, 1, 1, 1, 1, 1], 12).astype(float)
    lo = np.tile([-30, -400, -400, 0, 0, 0, 0, 0], 12); hi = np.tile([30, 400, 400, 1, 1, 1, 1, 1], 12)
    m, sw = F.fitm, np.sqrt(F.w[F.fitm])
    def res(p):
        q = p.reshape(12, 8)
        r = [sw * de(lab(F.smooth(p)[m]), F.T[m]),
             0.3 * ((q[:, :3] - np.roll(q[:, :3], 1, 0)) / [10, 40, 40]).ravel(),     # neighbouring hues alike
             0.3 * (1 - q[:, 3:]).ravel()]
        return np.concatenate(r)
    r = least_squares(res, p0, bounds=(lo, hi), x_scale=np.tile([5, 30, 30, 0.3, 0.3, 0.3, 0.3, 0.3], 12),
                      max_nfev=200, loss="soft_l1", f_scale=3.0)
    return r.x


def main(ids):
    os.makedirs(OUT, exist_ok=True)
    rd = readings(); ids = ids or list(rd)
    lines = []
    for fid in ids:
        tag, fitp = rd[fid]
        if "doublex" in fitp:
            lines.append(f"{fid}: black and white, skipped"); print(lines[-1]); continue
        F = Film(fid, tag, fitp)
        p = fit(F); tb = encode(p)
        open(os.path.join(OUT, f"{fid}.bin"), "wb").write(tb)
        s0, s1, s2 = F.score(F.J), F.score(F.smooth(p)), F.score(F.rules(tb))
        json.dump(dict(reading=tag, fit=os.path.relpath(fitp, ROOT), params=p.reshape(12, 8).round(3).tolist(),
                       measured=s0, predicted_smooth=s1, predicted_table=s2), open(os.path.join(OUT, f"{fid}.json"), "w"), indent=1)
        f = lambda s: f"wtd {s['weighted']:.2f} nat {s['natural']:.2f} CC {s['colorchecker']:.2f} skin {s['skin']:.2f} hold {s['holdout']:.2f} grey {s['grays']:.2f} edge {s['edge']:.2f}"
        lines.append(f"{fid:17s} camera now: {f(s0)}\n{'':17s} + 12-region: {f(s2)}  (smooth {s1['colorchecker']:.2f} CC)")
        print(lines[-1], flush=True)
    open(os.path.join(OUT, "report.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(argv[1:])

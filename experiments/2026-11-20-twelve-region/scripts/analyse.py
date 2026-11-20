"""Analysis of the probe's camera run: every number of the 12-region stage, with its uncertainty. Research code.

    OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/analyse.py DIR [--map MAP.json]
    OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/analyse.py DIR --guess [--no-frame0]
    OMP_NUM_THREADS=2 uv run python experiments/2026-11-20-twelve-region/scripts/analyse.py --selftest

DIR holds the JPEGs (and MOVs) copied from the card. MAP.json maps file names to roles:
    "ART<n>"            PB200001.ORF developed in ART n (sRGB)
    "ADOBE_ART<n>"      the same with Color Space AdobeRGB
    "REF_ART<n>"        PB130001.ORF developed in ART n
    "CAPTURE_ART<n>"    the ART BKT capture's JPEG of ART n (frame 0, the current Picture Mode: "CAPTURE_PM")
    "MOVIE_ART<n>"      a movie recorded in ART n
--guess writes DIR/map.json from the sheet's order; without --map, roles come from SIM_* names (simulations). The
classification check prints which entry each chart JPEG looks like, so a wrong order shows. The map in use is written to
DIR/map-used.json.

Method (NOTES.md section 6): stage-7 input = the CTRL development (ART 1, every record off); output = each entry.
Patch values: read_mock.py's registration with testraw/twelve_layout.npz, 8-bit JFIF Y, Cb, Cr. Model-free
measurements first (A hue map, B units, C magnitudes, D curve slots), then one least-squares fit of tables.apply
over all entries (E), then the specific tests (F).
"""
import glob, json, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
FP = os.path.abspath(os.path.join(EXP, "..", "2026-11-09-film-portra"))
sys.path.insert(0, FP)
sys.path.insert(0, HERE)
import tables as T  # noqa: E402

SPREAD_MAX, CMIN = 3.0, 6.0


# ---- reading --------------------------------------------------------------------------------------------------
def exif(path):
    tags = ["-FileName", "-ColorSpace", "-PictureMode", "-ImageDescription", "-ColorMatrix", "-WB_RBLevels",
            "-DateTimeOriginal", "-ImageWidth", "-ImageHeight"]
    try:
        return json.loads(subprocess.run(["exiftool", "-j", "-n"] + tags + [path], capture_output=True, text=True).stdout)[0]
    except Exception:
        return {}


_GEOM = {}


def read_chart(path, tag, geom_from=None):
    """Patch values of one development. The displacement field comes from the registration of geom_from (the CTRL
    development of the same RAW: RAW Data Edit gives every entry the same geometry), else from this file; an entry
    with whole sectors clipped (MAG L at +-1023) may not register on its own."""
    import cv2
    import read_mock as rm
    import chart
    rm.LAYOUTS = {"twelve": chart.layout_path(), "mock2a": os.path.join(FP, "testraw", "mock2a_layout.npz")}
    L, P, X0, Y0, NC, NR = rm.layout(tag)
    jpg = cv2.cvtColor(cv2.imread(path, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION), cv2.COLOR_BGR2RGB)
    key = (geom_from or path, tag)
    if key not in _GEOM:
        src = jpg if geom_from is None else cv2.cvtColor(cv2.imread(geom_from, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION), cv2.COLOR_BGR2RGB)
        f, stats = rm.register(src, L, P, X0, Y0, NC, NR)
        assert f is not None, f"{geom_from or path}: matches no test image"
        _GEOM[key] = (f, stats)
    f, stats = _GEOM[key]
    med, spr, xy = rm.sample(jpg, f, L, P, X0, Y0)
    Y = med @ np.array([.299, .587, .114])
    ok = np.isfinite(med[:, 0]) & (spr < SPREAD_MAX) & (L["kind"] != 0)
    return dict(Y=Y, cb=0.564 * (med[:, 2] - Y), cr=0.713 * (med[:, 0] - Y), ok=ok, stats=stats, lay=L)


def guess_map(dirpath, frame0=True):
    """The sheet's order (NOTES.md section 5): JPEGs by file name: PB200001 developed by ART BKT (the current Picture
    Mode first when frame0, then ART 1-12), PB130001 the same, the ART BKT capture (frame 0, ART 1-12), the ART 5
    photo; MOVs: ART 5, then ART 1. Writes DIR/map.json; check it against the classification lines of the run."""
    jpgs = sorted(glob.glob(os.path.join(dirpath, "*.JPG")))
    movs = sorted(glob.glob(os.path.join(dirpath, "*.MOV")))
    roles = []
    for prefix in ("", "REF_", "CAPTURE_"):
        if prefix == "CAPTURE_" or frame0:
            roles.append(prefix + "PM" if prefix else "PM")
        roles += [f"{prefix}ART{n}" for n in range(1, 13)]
    roles.append("PHOTO_ART5")
    mp = {os.path.basename(f): r for f, r in zip(jpgs, roles)}
    mp.update({os.path.basename(f): r for f, r in zip(movs, ("MOVIE_ART5", "MOVIE_ART1"))})
    json.dump(mp, open(os.path.join(dirpath, "map.json"), "w"), indent=1)
    print(f"wrote {os.path.join(dirpath, 'map.json')}: {len(jpgs)} JPEGs, {len(movs)} MOVs; roles in order:")
    for k, v in mp.items():
        print(f"   {k}: {v}")
    if len(jpgs) != len(roles):
        print(f"   WARNING: {len(jpgs)} JPEGs, the sheet gives {len(roles)}: edit map.json by hand")


def roles_from_names(files):
    m = {}
    for f in files:
        b = os.path.basename(f)
        r = re.match(r"SIM_(ADOBE_)?ART(\d+)\.JPG$", b)
        if r:
            m[b] = ("ADOBE_" if r.group(1) else "") + f"ART{int(r.group(2))}"
    return m


# ---- helpers ----------------------------------------------------------------------------------------------------
def wrap180(a):
    return (np.asarray(a) + 180.0) % 360.0 - 180.0


def ang(d):
    return np.degrees(np.arctan2(d["cr"], d["cb"]))


def chroma(d):
    return np.hypot(d["cb"], d["cr"])


def robust(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return np.nan, np.nan, 0
    med = np.median(x)
    mad = 1.4826 * np.median(np.abs(x - med))
    return med, (mad / np.sqrt(len(x)) if len(x) > 1 else np.nan), len(x)


def inrange(d, lo=3.0, hi=252.0):
    """Patches whose RGB is not clipped (from Y, Cb, Cr)."""
    r = d["Y"] + 1.402 * d["cr"]; b = d["Y"] + 1.772 * d["cb"]; g = (d["Y"] - .299 * r - .114 * b) / .587
    return (np.minimum(np.minimum(r, g), b) > lo) & (np.maximum(np.maximum(r, g), b) < hi)


def rec_hue(theta, sign, h0):
    return np.mod(sign * theta + h0, 360.0)


def in_arc(h, lo, hi):
    return np.mod(h - lo, 360.0) < np.mod(hi - lo, 360.0)


class Report:
    def __init__(self):
        self.lines, self.values = [], {}

    def p(self, *a):
        s = " ".join(str(x) for x in a)
        self.lines.append(s)
        print(s)

    def v(self, key, val, unc=None, label="measured"):
        self.values[key] = dict(value=val, unc=unc, label=label)


# ---- stage A: hue convention (HUEMAP, ART 3) ---------------------------------------------------------------------
def stage_a(c, e, R, noise):
    ok = c["ok"] & e["ok"] & (chroma(c) >= CMIN)
    dY = e["Y"] - c["Y"]
    th = ang(c)
    thr = max(4 * noise, 1.5)
    hit = ok & (dY < -thr)
    # dense ring first (kind 2: Y 120, chroma 30, 1 deg), else every patch
    kind = c["lay"]["kind"]
    ring = ok & (kind == 2)
    bins = np.arange(-180, 181, 1.0)
    centres, mags = [], []
    hd = np.mod(th[hit], 360)
    # cluster the affected angles into runs
    order = np.sort(hd)
    if len(order) < 12:
        R.p("A: fewer than 12 affected patches in HUEMAP: no hue map")
        return None
    gaps = np.diff(np.concatenate([order, [order[0] + 360]]))
    cut = np.argsort(gaps)[-12:]
    starts = np.sort((cut + 1) % len(order))
    groups = []
    for i, s in enumerate(starts):
        e_ = starts[(i + 1) % 12]
        idx = np.arange(s, e_ if e_ > s else e_ + len(order)) % len(order)
        groups.append(order[idx])
    for g in groups:
        cen = np.degrees(np.angle(np.exp(1j * np.radians(g)).mean())) % 360
        sel = hit & (np.abs(wrap180(th - cen)) < 15)
        centres.append(cen)
        mags.append(np.median(dY[sel]))
    centres, mags = np.array(centres), np.array(mags)
    srt = np.argsort(centres)
    centres, mags = centres[srt], mags[srt]
    recL = np.array([-(40 + 10 * k) for k in range(12)], float)
    recC = np.array([30 * k + 15 for k in range(12)], float)
    best = None
    for sign in (1, -1):
        for shift in range(12):
            idx = (np.arange(12) * sign + shift) % 12          # record of the i-th group by angle
            r = np.corrcoef(mags, recL[idx])[0, 1]
            if best is None or r > best[0]:
                best = (r, sign, shift, idx)
    r, sign, shift, idx = best
    # refine centres on the ring: edges = half the record's effect
    meas_c, meas_w = [], []
    for i in range(12):
        k = idx[i]
        sel = ring & (np.abs(wrap180(th - centres[i])) < 15)
        if sel.sum() < 6:
            meas_c.append(centres[i]); meas_w.append(np.nan); continue
        a = wrap180(th[sel] - centres[i]); y = dY[sel]
        o = np.argsort(a); a, y = a[o], y[o]
        half = 0.5 * np.min(y)
        inside = y < half
        lo, hi = a[inside].min(), a[inside].max()
        meas_c.append((centres[i] + (lo + hi) / 2) % 360); meas_w.append(hi - lo + 1.0)
    meas_c = np.array(meas_c)
    # rec centre = sign * theta + h0  (mod 360)
    h0s = wrap180(recC[idx] - sign * meas_c)
    h0 = np.degrees(np.angle(np.exp(1j * np.radians(h0s)).mean()))
    res = wrap180(h0s - h0)
    # scale: unwrap rec centres against sign * theta
    x = np.unwrap(np.radians(sign * meas_c[np.argsort(recC[idx])])) * 180 / np.pi
    yv = np.sort(recC[idx])
    slope = np.polyfit(x - x[0], yv - yv[0], 1)[0]
    R.p(f"A  hue convention (ART 3 HUEMAP): record hue = {sign:+d} x atan2(Cr, Cb) + {h0:.2f} deg "
        f"(+- {res.std(ddof=1) / np.sqrt(12):.2f}); residual per window rms {res.std(ddof=1):.2f} deg; "
        f"scale {slope:.4f} record deg per measured deg (1 = 32768 per turn); magnitude order r = {r:.3f}")
    R.p(f"   window widths on the 1-deg ring (10 deg written, trapezoid): {np.round(meas_w, 1).tolist()}")
    R.v("hue_sign", sign); R.v("hue_zero_deg", h0, res.std(ddof=1) / np.sqrt(12)); R.v("hue_scale", slope)
    return dict(sign=sign, h0=h0, centres=meas_c, idx=idx, widths=meas_w)


# ---- stage B: units of luma and chroma (BOX, ART 10) --------------------------------------------------------------
def edges(x, y, level):
    """x sorted; the x values where y crosses level (linear interpolation)."""
    s = np.sign(y - level)
    i = np.flatnonzero(s[:-1] * s[1:] < 0)
    return x[i] + (level - y[i]) * (x[i + 1] - x[i]) / (y[i + 1] - y[i])


def binned(x, y, lo, hi, step):
    b = np.arange(lo, hi + step, step)
    xc, yc = [], []
    for a, z in zip(b[:-1], b[1:]):
        s = (x >= a) & (x < z)
        if s.sum() >= 2:
            xc.append(np.median(x[s])); yc.append(np.median(y[s]))
    return np.array(xc), np.array(yc)


def stage_b(c, e, R, A, noise):
    ok = c["ok"] & e["ok"]
    kind = c["lay"]["kind"]
    dY = e["Y"] - c["Y"]
    # luma: greys and luma lines (kind 4), every hue: bands 192-320 (+80) and 704-832 (-80)
    sel = ok & (kind == 4)
    x, y = binned(c["Y"][sel], dY[sel], 0, 255, 1.0)
    ky = None
    if len(x) > 20:
        up = edges(x, y, 0.5 * np.nanmax(y)); dn = edges(x, -y, 0.5 * np.nanmax(-y))
        written = []
        if len(up) >= 2:
            written += [(up[0], 192 + 4), (up[-1], 320 - 4)]
        if len(dn) >= 2:
            written += [(dn[0], 704 + 4), (dn[-1], 832 - 4)]
        if len(written) >= 2:
            X = np.array(written)
            A_ = np.stack([X[:, 0], np.ones(len(X))], 1)
            (kyv, y0), res, *_ = np.linalg.lstsq(A_, X[:, 1], rcond=None)
            r = X[:, 1] - A_ @ np.array([kyv, y0])
            unc = np.sqrt(np.sum(r ** 2) / max(len(X) - 2, 1) / np.sum((X[:, 0] - X[:, 0].mean()) ** 2)) if len(X) > 2 else np.nan
            ky = kyv
            R.p(f"B  luma units (ART 10 BOX, greys and luma lines): luma_rec = {kyv:.3f} x Y8 + {y0:.1f} "
                f"(slope +- {unc:.3f}); edges at Y8 {np.round(X[:, 0], 1).tolist()} for written {X[:, 1].tolist()}")
            R.v("luma_units_per_code", kyv, unc); R.v("luma_offset", y0)
        R.p(f"   plateaus: band 192-320 dY {np.nanmax(y):+.2f}, band 704-832 dY {np.nanmin(y):+.2f} (8-bit codes)")
    # chroma: hue shift bands at record hue 0-180 (alternating +-15 deg)
    kc = None
    if A is not None:
        hr = rec_hue(ang(c), A["sign"], A["h0"])
        dth = wrap180(ang(e) - ang(c)) * A["sign"]
        sel = ok & (hr > 20) & (hr < 160) & ((kind == 3) | (kind == 1))
        x, y = binned(chroma(c)[sel], dth[sel], 0, 90, 1.5)
        cr_up = edges(x, y, 7.5); cr_dn = edges(x, -y, 7.5)
        allx = np.sort(np.concatenate([cr_up, cr_dn]))
        written = [24 + 1, 56 - 1, 96 + 2, 160 - 2, 224 + 3, 320 - 3, 400 + 5, 560 - 5]
        n = min(len(allx), len(written))
        if n >= 2:
            X = np.array(list(zip(allx[:n], written[:n])))
            kcv = np.sum(X[:, 0] * X[:, 1]) / np.sum(X[:, 0] ** 2)
            r = X[:, 1] - kcv * X[:, 0]
            unc = np.sqrt(np.sum(r ** 2) / max(n - 1, 1) / np.sum(X[:, 0] ** 2))
            kc = kcv
            R.p(f"B  chroma units (ART 10, record hue 20-160): chroma_rec = {kcv:.3f} x radius8 (+- {unc:.3f}); "
                f"edges at radius {np.round(X[:, 0], 1).tolist()} for written {X[:, 1].tolist()}")
            R.v("chroma_units_per_code", kcv, unc)
            # metric: is the first edge the same radius at every hue?
            fe = []
            for h in 7.5 + 30 * np.arange(12):
                s2 = ok & (kind == 3) & (np.abs(wrap180(ang(c) - h)) < 3)
                hr2 = rec_hue(h, A["sign"], A["h0"])
                if s2.sum() > 10 and 20 < hr2 < 160:
                    xx, yy = binned(chroma(c)[s2], dth[s2], 0, 90, 1.5)
                    ee = edges(xx, yy, 7.5)
                    if len(ee):
                        fe.append((h, ee[0]))
            if fe:
                fe = np.array(fe)
                R.p(f"   first chroma edge by hue (radius8): {[(round(a), round(b, 1)) for a, b in fe]}; spread "
                    f"{fe[:, 1].std():.2f} (Euclidean chroma: equal at every hue; |Cb|+|Cr| or max: varies by up to 41 %)")
                R.v("chroma_edge_spread", float(fe[:, 1].std()))
        else:
            R.p("B  chroma units: fewer than two chroma edges found")
    return dict(ky=ky, kc=kc)


# ---- stage C: effect units (MAG entries) ---------------------------------------------------------------------------
def sector_sel(c, A, k, margin=4.0):
    hr = rec_hue(ang(c), A["sign"], A["h0"])
    return in_arc(hr, 30 * k + margin, 30 * k + 30 - margin)


def stage_c(c, eL, eS, eH, R, A, noise):
    out = {}
    ok0 = c["ok"] & (chroma(c) >= CMIN)
    if eL is not None:
        rows = []
        dY = eL["Y"] - c["Y"]
        k0 = [robust(dY[ok0 & eL["ok"] & sector_sel(c, A, k)])[0] / v for k, v in enumerate(T.MAGL) if abs(v) <= 64]
        kl0 = np.median(k0)
        for k, v in enumerate(T.MAGL):
            s = ok0 & eL["ok"] & sector_sel(c, A, k) & inrange(c) & (c["Y"] + kl0 * v > 5) & (c["Y"] + kl0 * v < 250) & inrange(eL)
            clipped = np.mean(~inrange(eL)[ok0 & eL["ok"] & sector_sel(c, A, k)])
            med, unc, n = robust(dY[s])
            slope = np.polyfit(c["Y"][s], dY[s], 1)[0] if s.sum() > 10 else np.nan
            rows.append((v, med, unc, n, slope, clipped))
        rows = np.array(rows)
        lin = np.abs(rows[:, 0]) <= 256
        kl = np.sum(rows[lin, 0] * rows[lin, 1]) / np.sum(rows[lin, 0] ** 2)
        res = rows[lin, 1] - kl * rows[lin, 0]
        ukl = np.sqrt(np.sum(res ** 2) / (lin.sum() - 1) / np.sum(rows[lin, 0] ** 2))
        R.p(f"C  lightness (ART 4 MAG L): dY8 = {kl:.5f} x L (+- {ukl:.5f}; 1/4 = 0.25000 if L is 10-bit luma) over |L| <= 256")
        for v, med, unc, n, sl, cl in sorted(rows.tolist()):
            R.p(f"     L {v:+6.0f}: dY8 {med:+7.2f} +- {unc:.2f} (n {n:.0f} unclipped); ratio to linear {med / (kl * v):.3f}; "
                f"dY vs Y8 slope {sl:+.3f} (0 = added, not scaled); {cl * 100:.0f} % of the sector clipped")
        R.v("light_code_per_unit", kl, ukl)
        out["kl"] = kl
    if eS is not None:
        rows = []
        cc, ce = chroma(c), chroma(eS)
        for k, v in enumerate(T.MAGS):
            s = ok0 & eS["ok"] & sector_sel(c, A, k) & (c["Y"] > 30) & (c["Y"] < 225) & (cc > 8) & inrange(eS)
            ratio = robust(ce[s] / cc[s]); diff = robust(ce[s] - cc[s])
            # which model: ratio constant over chroma (multiply) or difference constant (add)
            if s.sum() > 10:
                rr = np.std(ce[s] / cc[s]) / max(abs(np.mean(ce[s] / cc[s]) - 1), 1e-3)
                rd = np.std(ce[s] - cc[s]) / max(abs(np.mean(ce[s] - cc[s])), 1e-3)
            else:
                rr = rd = np.nan
            rows.append((v, ratio[0], ratio[1], diff[0], diff[1], rr, rd, robust(eS["Y"][s] - c["Y"][s])[0]))
        rows = np.array(rows)
        lin = (np.abs(rows[:, 0]) <= 256) & (rows[:, 1] > 0.05)
        mul = np.nanmedian(rows[lin, 5]) < np.nanmedian(rows[lin, 6])
        if mul:
            ks = np.sum(rows[lin, 0] * (rows[lin, 1] - 1)) / np.sum(rows[lin, 0] ** 2)
            res = rows[lin, 1] - 1 - ks * rows[lin, 0]
        else:
            ks = np.sum(rows[lin, 0] * rows[lin, 3]) / np.sum(rows[lin, 0] ** 2)
            res = rows[lin, 3] - ks * rows[lin, 0]
        uks = np.sqrt(np.sum(res ** 2) / (lin.sum() - 1) / np.sum(rows[lin, 0] ** 2))
        R.p(f"C  saturation (ART 5 MAG S): {'MULTIPLIES chroma: c_out = c_in x (1 + ks x S)' if mul else 'ADDS to chroma: c_out = c_in + ks x S'}"
            f", ks = {ks:.6f} +- {uks:.6f} (over |S| <= 256; relative spread multiply {np.nanmedian(rows[lin, 5]):.3f} vs add "
            f"{np.nanmedian(rows[lin, 6]):.3f}: smaller wins)")
        for v, rt, urt, df, udf, _, _, dy in sorted(rows.tolist()):
            R.p(f"     S {v:+6.0f}: chroma ratio {rt:.3f} +- {urt:.3f}, difference {df:+.2f} +- {udf:.2f} codes, dY8 {dy:+.2f}")
        R.v("sat_mode", "mul" if mul else "add"); R.v("sat_per_unit", ks, uks)
        out["sat"], out["ks"] = ("mul" if mul else "add"), ks
    if eH is not None:
        rows = []
        dth = wrap180(ang(eH) - ang(c)) * A["sign"]
        for k, v in enumerate(T.MAGH):
            s = ok0 & eH["ok"] & sector_sel(c, A, k) & (chroma(c) > 10)
            med = np.degrees(np.angle(np.exp(1j * np.radians(dth[s])).mean())) if s.sum() else np.nan
            rows.append((v, med, robust(dth[s])[1], robust(chroma(eH)[s] / chroma(c)[s])[0], robust(eH["Y"][s] - c["Y"][s])[0]))
        rows = np.array(rows)
        lin = np.abs(rows[:, 0]) <= 2730
        kh = np.sum(rows[lin, 0] * rows[lin, 1]) / np.sum(rows[lin, 0] ** 2)
        res = rows[lin, 1] - kh * rows[lin, 0]
        ukh = np.sqrt(np.sum(res ** 2) / (lin.sum() - 1) / np.sum(rows[lin, 0] ** 2))
        R.p(f"C  hue shift (ART 6 MAG H): {kh * T.HUE_TURN:.2f} deg per 32768 units (+- {ukh * T.HUE_TURN:.2f}; 360 if "
            f"32768 = one turn); positive = the same direction as record hue")
        for v, med, u, rt, dy in sorted(rows.tolist()):
            R.p(f"     H {v:+7.0f} ({v * 360 / T.HUE_TURN:+7.1f} deg written): measured {med:+7.2f} deg +- {u:.2f}; chroma ratio {rt:.3f}; dY8 {dy:+.2f}")
        R.v("hue_deg_per_unit", kh, ukh)
        out["kh"] = kh
    return out


# ---- stage D: curve slots (CURVES, ART 7) --------------------------------------------------------------------------
def stage_d(c, e, R, A, B, C_):
    ok = c["ok"] & e["ok"] & (chroma(c) >= CMIN) & (c["Y"] > 20) & (c["Y"] < 235)
    hr = rec_hue(ang(c), A["sign"], A["h0"])
    eff = {"H": wrap180(ang(e) - ang(c)) * A["sign"] / (C_["kh"] * T.deg(20))}
    if C_["sat"] == "mul":
        eff["S"] = (chroma(e) / np.maximum(chroma(c), 1e-6) - 1) / (C_["ks"] * 160)
    else:
        eff["S"] = (chroma(e) - chroma(c)) / (C_["ks"] * 160)
    eff["L"] = (e["Y"] - c["Y"]) / (C_["kl"] * -160)
    ramp = lambda p: T.curve_eval(np.array([[l, s] for l, s in zip(T.RAMP[:16], np.diff(T.RAMP))]), p) / T.FULL
    found = {}
    R.p("D  curve slots (ART 7 CURVES): record k has slot c_k as a ramp; the weight each effect shows, fitted against the "
        "ramp along each axis (R2; 'flat' = no modulation)")
    for k in range(7):
        lo, hi = 50 * k + 2.5, 50 * k + 47.5
        s = ok & in_arc(hr, lo + 3, hi - 3)
        if s.sum() < 30:
            R.p(f"   c{k}: too few patches"); continue
        ph = np.clip(np.mod(hr[s] - lo, 360) / (hi - lo) * 256, 0, 256)
        pc = np.clip(chroma(c)[s] * (B["kc"] or 4) * 128 / 512, 0, 256)
        py = np.clip(c["Y"][s] * (B["ky"] or 4) * 128 / 512, 0, 256)
        trap_h = np.where((ph > 16) & (ph < 240), 1.0, 0.5)
        line = []
        for ename, w in eff.items():
            w = w[s] / trap_h
            cand = {"flat": np.ones_like(w), "hue": ramp(ph), "chroma": ramp(pc), "luma": ramp(py)}
            err = {ax: np.median(np.abs(w - f)) for ax, f in cand.items()}
            best = min(err, key=err.get)
            line.append(f"{ename}: {best} (median |w - shape|: " + " ".join(f"{a[0]} {v:.2f}" for a, v in err.items()) + ")")
            if best != "flat":
                found.setdefault(k, []).append((ename, best))
        R.p(f"   c{k}: " + "; ".join(line))
    R.v("curve_slots", {f"c{k}": v for k, v in found.items()})
    return found


# ---- stage E: one fit of the whole model -------------------------------------------------------------------------
def stage_e(c, ents, R, start, discrete):
    from scipy.optimize import least_squares
    names = ["h0", "kc", "ky", "kl", "ks", "kh"]
    rng = np.random.default_rng(0)
    data = []
    for n, e in ents.items():
        tname = T.ENTRIES[n - 1][3]
        if tname is None or n in (11, 12):
            continue
        ok = c["ok"] & e["ok"] & inrange(c) & inrange(e)
        t = T.decode(T.table(tname))
        o0 = {**T.NOMINAL, **discrete[0], **start}
        ref = np.stack(T.apply(t, c["Y"], c["cb"], c["cr"], o0), 1)
        for dy, dcb, dcr in ((0.5, 0, 0), (-0.5, 0, 0), (0, 0.5, 0.5), (0, -0.5, 0.5), (0, 0.5, -0.5), (0, -0.5, -0.5)):
            alt = np.stack(T.apply(t, c["Y"] + dy, c["cb"] + dcb, c["cr"] + dcr, o0), 1)
            ok &= np.abs(alt - ref).max(1) < 1.5      # drop patches that a half-code reading error moves across an edge
        idx = np.flatnonzero(ok)
        idx = rng.choice(idx, min(len(idx), 1500), replace=False)
        data.append((t, idx, e))
    x0 = np.array([start[k] for k in names])

    def resid(x, disc):
        o = {**T.NOMINAL, **disc, **dict(zip(names, x))}
        out = []
        for t, idx, e in data:
            Y2, cb2, cr2 = T.apply(t, c["Y"][idx], c["cb"][idx], c["cr"][idx], o)
            out.append(np.concatenate([Y2 - e["Y"][idx], cb2 - e["cb"][idx], cr2 - e["cr"][idx]]))
        return np.concatenate(out)
    results = []
    for disc in discrete:
        try:
            f = least_squares(resid, x0, args=(disc,), x_scale=np.abs(x0) + 1e-3, max_nfev=60, diff_step=1e-3)
        except Exception as ex:
            R.p("E  fit failed", disc, ex); continue
        rms = np.sqrt(np.mean(f.fun ** 2))
        try:
            cov = np.linalg.inv(f.jac.T @ f.jac) * np.mean(f.fun ** 2)
            unc = np.sqrt(np.diag(cov))
        except np.linalg.LinAlgError:
            unc = np.full(len(x0), np.nan)
        results.append((rms, disc, f.x, unc))
    results.sort(key=lambda r: r[0])
    R.p("E  global fit of the stage model (entries 3-10, 1500 patches each), residual rms (8-bit codes) per hypothesis:")
    for rms, disc, x, unc in results:
        R.p(f"     {rms:6.3f}  {disc}")
    rms, disc, x, unc = results[0]
    R.p("   best: " + ", ".join(f"{k} = {v:.5g} +- {u:.2g}" for k, v, u in zip(names, x, unc)) + f"; {disc}")
    for k, v, u in zip(names, x, unc):
        R.v("fit_" + k, float(v), float(u), "fitted")
    R.v("fit_hypothesis", disc, None, "fitted")
    return {**T.NOMINAL, **disc, **dict(zip(names, x))}, rms


# ---- stage F: specific tests ---------------------------------------------------------------------------------------
def region(c, A, lo, hi, cmin=CMIN):
    return in_arc(rec_hue(ang(c), A["sign"], A["h0"]), lo, hi) & (chroma(c) >= cmin) & (c["Y"] > 25) & (c["Y"] < 230)


def effects(c, e, s, A):
    return dict(dY=robust(e["Y"][s] - c["Y"][s]), ratio=robust(chroma(e)[s] / chroma(c)[s]),
                dth=robust(wrap180(ang(e)[s] - ang(c)[s]) * A["sign"]))


def fmt(ef):
    return (f"dY8 {ef['dY'][0]:+.2f}+-{ef['dY'][1]:.2f}, chroma x{ef['ratio'][0]:.3f}+-{ef['ratio'][1]:.3f}, "
            f"hue {ef['dth'][0]:+.2f}+-{ef['dth'][1]:.2f} deg (n {ef['dY'][2]})")


def stage_f(c, ents, R, A, model, adobe):
    ok = c["ok"]
    if 8 in ents:
        e = ents[8]; s = ok & e["ok"]
        R.p("F  overlap and mask (ART 8 OVERLAP), measured | the fitted model's prediction (sum of records):")
        t = T.decode(T.table("OVERLAP"))
        pred = dict(zip(("Y", "cb", "cr"), T.apply(t, c["Y"], c["cb"], c["cr"], model)))
        for lo, hi, what in ((4, 56, "S +64 twice (alone: MAG S +64; sum: +128)"), (64, 116, "H +10 and +20 deg (sum 30)"),
                             (124, 176, "L -64 twice (sum -128)"), (184, 206, "S -128 only"), (214, 236, "S -128 and L +128"),
                             (244, 266, "L +128 only"), (274, 296, "bit 4 off (S -256) + bit 5 on (L -64)"),
                             (304, 326, "bit 4 off only: no change expected"), (332, 343, "bit 10 off (L +256) + bit 11 on (S +128)"),
                             (348, 358, "bit 10 off only: no change expected")):
            r_ = s & region(c, A, lo, hi)
            R.p(f"     {lo:3d}-{hi:3d} {what}: {fmt(effects(c, e, r_, A))} | {fmt(effects(c, pred, r_, A))}")
    if 9 in ents:
        e = ents[9]; s = ok & e["ok"]
        R.p("F  window semantics (ART 9 WINDOW):")
        for lo, hi, what in ((12, 38, "W2 inside the written window"), (42, 68, "W2 beyond the width, p < 256 (effect = no hard edge)"),
                             (92, 108, "W3 first half (p up to 256)"), (112, 128, "W3 second half (p > 256)"),
                             (152, 178, "W4 luma (0,0): S -128 at every luma?"), (352, 358, "W5 before 0"), (2, 8, "W5 after 0"),
                             (252, 278, "W7 chroma (0,0): S +128 at every chroma?"), (292, 318, "W8 levels 126: L -64 x 2?"),
                             (182, 198, "no record: offset = spill of W1 if windows are not hard"),
                             (281, 288, "no record: offset = spill of W1")):
            r_ = s & region(c, A, lo, hi, 4)
            R.p(f"     {lo:3d}-{hi:3d} {what}: {fmt(effects(c, e, r_, A))}")
        # W4 / W7: uniformity across luma / chroma
        for lo, hi, ax, what in ((152, 178, "Y", "W4"), (252, 278, "C", "W7")):
            r_ = s & region(c, A, lo, hi, 4)
            x = c["Y"][r_] if ax == "Y" else chroma(c)[r_]
            q = np.quantile(x, [0, .25, .5, .75, 1]) if r_.sum() > 8 else []
            parts = [f"{a:.0f}-{b:.0f}: x{robust(chroma(e)[r_][(x >= a) & (x <= b)] / chroma(c)[r_][(x >= a) & (x <= b)])[0]:.3f}"
                     for a, b in zip(q[:-1], q[1:])]
            R.p(f"     {what} chroma ratio by {'Y8' if ax == 'Y' else 'chroma'} quartile: {parts}")
        # W6 sawtooth along luma (luma slot: levels 32, slopes +16)
        r_ = s & region(c, A, 204, 236, 4) & (c["Y"] > 4) & (c["Y"] < 250)
        if r_.sum() > 10:
            p = np.clip(c["Y"][r_] * model["ky"] * 128 / 512, 0, 256)
            y = (e["Y"] - c["Y"])[r_]
            saw = 32 + 16 * (np.floor(p) % 16) / 16.0
            X = np.stack([saw, np.ones_like(saw)], 1)       # scale and offset (an offset = W1's spill)
            r1 = np.sqrt(np.mean((y - X @ np.linalg.lstsq(X, y, rcond=None)[0]) ** 2)); r0 = np.std(y)
            R.p(f"     W6 (luma slot levels 32, slopes +16): rms vs a sawtooth along luma (slope used) {r1:.2f}, vs flat "
                f"(levels only) {r0:.2f} codes -> {'the slope byte is used' if r1 < r0 else 'only the levels are used'}")
            R.v("curve_uses_slope", bool(r1 < r0))
        # W1: in the box vs out of it
        kc, ky = model["kc"], model["ky"]
        box = s & region(c, A, 324, 344, 0) & (chroma(c) * kc >= 44) & (chroma(c) * kc < 156) & (c["Y"] * ky >= 260) & (c["Y"] * ky < 636)
        out_ = s & region(c, A, 324, 344, 0) & ~((chroma(c) * kc >= 36) & (chroma(c) * kc < 164) & (c["Y"] * ky >= 250) & (c["Y"] * ky < 646))
        R.p(f"     W1 (flat 63, ends not 0): inside its box {fmt(effects(c, e, box, A))}; same hues outside the box {fmt(effects(c, e, out_, A))}")
    if 2 in ents:
        e = ents[2]; s = ok & e["ok"]
        t = T.decode(open_table_a())
        pred = dict(zip(("Y", "cb", "cr"), T.apply(t, c["Y"], c["cb"], c["cr"], model)))
        res = np.concatenate([(pred["Y"] - e["Y"])[s], (pred["cb"] - e["cb"])[s], (pred["cr"] - e["cr"])[s]])
        d = np.concatenate([(e["Y"] - c["Y"])[s], (e["cb"] - c["cb"])[s], (e["cr"] - c["cr"])[s]])
        R.p(f"F  Natural's table A (ART 2 minus ART 1): rms change {np.sqrt(np.mean(d ** 2)):.2f} codes, largest "
            f"{np.abs(d).max():.1f}; the fitted model predicts it with rms residual {np.sqrt(np.mean(res ** 2)):.2f}")
        for i, r in enumerate(t["recs"]):
            if not r["on"]:
                continue
            hs, hw = r["win"][0] * 360 / T.HUE_TURN
            r_ = s & region(c, A, hs + hw * 0.3, hs + hw * 0.7, 6)
            R.p(f"     record {i} (hue {hs:.0f}+{hw:.0f} deg, written H {r['eff'][0] * 360 / T.HUE_TURN:+.1f} deg S {r['eff'][1]:+d} "
                f"L {r['eff'][2]:+d}): {fmt(effects(c, e, r_, A))}")
        R.v("natural_A_rms_change", float(np.sqrt(np.mean(d ** 2)))); R.v("natural_A_model_rms", float(np.sqrt(np.mean(res ** 2))))
    order_tests(c, ents, R, model)
    if adobe:
        adobe_test(adobe, R, model)


def open_table_a():
    import simulate
    return simulate.TABLE_A


def maps(c, e, s):
    """Per-channel 1-D maps CTRL -> entry from the patches s (binned medians)."""
    out = {}
    for ch, lo, hi, st in (("Y", 0, 255, 2.0), ("cb", -128, 128, 1.5), ("cr", -128, 128, 1.5)):
        x, y = binned(c[ch][s], e[ch][s], lo, hi, st)
        out[ch] = (x, y)
    return out


def apply_maps(mp, d):
    return {ch: np.interp(d[ch], *mp[ch]) for ch in ("Y", "cb", "cr")}


def order_tests(c, ents, R, model):
    t = T.decode(T.table("BOX"))
    for n, what, alts in ((11, "saturation gain x1.5 and chroma curves", ("after", "mid", "before6")),
                          (12, "the look curve (Cross Process I)", ("after", "before5"))):
        if n not in ents:
            continue
        e = ents[n]
        W, _ = T.weights(t, *T.coords(c["Y"], c["cb"], c["cr"], model)[:3], model)
        Wsum = sum(W[k].sum(0) for k in "HSL")
        # unaffected under every hypothesis: no weight on CTRL coordinates and on the entry's own
        W2, _ = T.weights(t, *T.coords(e["Y"], e["cb"], e["cr"], model)[:3], model)
        free = c["ok"] & e["ok"] & (Wsum == 0) & (sum(W2[k].sum(0) for k in "HSL") == 0)
        aff = c["ok"] & e["ok"] & ~free
        F = maps(c, e, free)
        s7 = lambda d: dict(zip(("Y", "cb", "cr"), T.apply(t, d["Y"], d["cb"], d["cr"], model)))
        g = 1.5
        res = {}
        for h in alts:
            if h == "after":
                p = s7(apply_maps(F, c))
            elif h == "before6" or h == "before5":
                p = apply_maps(F, s7(c))
            else:                                     # mid: gain, stage 7, chroma curves
                gc = {"Y": c["Y"], "cb": c["cb"] * g, "cr": c["cr"] * g}
                Fc = {"Y": F["Y"], "cb": (F["cb"][0] * g, F["cb"][1]), "cr": (F["cr"][0] * g, F["cr"][1])}
                p = apply_maps(Fc, s7(gc))
            r = np.concatenate([(p[ch] - e[ch])[aff] for ch in ("Y", "cb", "cr")])
            res[h] = np.sqrt(np.mean(r ** 2))
        best = min(res, key=res.get)
        R.p(f"F  order against {what} (ART {n} vs ART 10's table on {aff.sum()} affected patches; maps from {free.sum()} "
            f"unaffected): rms residual " + ", ".join(f"{k} {v:.3f}" for k, v in res.items()) + f" -> {best}")
        R.v(f"order_ART{n}", best, {k: float(v) for k, v in res.items()})
        if n == 11:
            for ch in ("cb", "cr"):
                x, y = F[ch]
                sls = [np.polyfit(x[m_], y[m_], 1)[0] for m_ in (x > 25, x < -25) if m_.sum() > 3]
                sl = float(np.mean(sls)) if sls else np.nan
                R.p(f"     ART 11 {ch.upper()} slope outside +-25 (each side): {sl:.3f} (first stored curve 0.5 x 1.5 = 0.75; second 0.75 x 1.5 = 1.125)")
                R.v(f"stage6_slope_{ch}", float(sl))


def adobe_test(adobe, R, model):
    if 1 not in adobe or 3 not in adobe:
        R.p("F  table B: needs ADOBE_ART1 and ADOBE_ART3"); return
    c, e = adobe[1], adobe[3]
    s = c["ok"] & e["ok"]
    d = np.concatenate([(e[ch] - c[ch])[s] for ch in ("Y", "cb", "cr")])
    out = {}
    for name in ("HUEMAP", "MARKER"):
        t = T.decode(T.table(name))
        p = dict(zip(("Y", "cb", "cr"), T.apply(t, c["Y"], c["cb"], c["cr"], model)))
        q = np.concatenate([(p[ch] - c[ch])[s] for ch in ("Y", "cb", "cr")])
        out[name] = np.corrcoef(d, q)[0, 1]
    verdict = "table B is used in AdobeRGB (P+82 = colour space)" if out["MARKER"] > out["HUEMAP"] else \
        "table A is used in AdobeRGB too (P+82 is not the colour space, or RAW Data Edit ignores it)"
    R.p(f"F  table B (ADOBE ART 3 minus ADOBE ART 1): correlation with HUEMAP {out['HUEMAP']:.3f}, with MARKER "
        f"{out['MARKER']:.3f} -> {verdict}")
    R.v("adobe_uses_table_B", bool(out["MARKER"] > out["HUEMAP"]))


def scene_test(c, ents, refs, R):
    if 1 not in refs or 2 not in refs or 2 not in ents:
        return
    sid = c["lay"]["sid"]
    s = c["ok"] & ents[2]["ok"] & (sid >= 0)
    a = {ch: ents[2][ch][s] - c[ch][s] for ch in ("Y", "cb", "cr")}
    i = sid[s]
    b = {ch: refs[2][ch][i] - refs[1][ch][i] for ch in ("Y", "cb", "cr")}
    ok = refs[1]["ok"][i] & refs[2]["ok"][i]
    dd = np.concatenate([(a[ch] - b[ch])[ok] for ch in a])
    R.p(f"F  scene content: table A's change on {ok.sum()} raw-identical patches in PB200001 and PB130001: difference "
        f"rms {np.sqrt(np.mean(dd ** 2)):.2f} codes, mean {dd.mean():+.2f} (0 within the noise = no scene-adaptive part)")
    R.v("scene_rms", float(np.sqrt(np.mean(dd ** 2))))


def capture_test(files, R):
    import cv2
    imgs = {}
    for role, f in files.items():
        im = cv2.imread(f, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
        if im is not None:
            imgs[role] = cv2.resize(im, (im.shape[1] // 8, im.shape[0] // 8), interpolation=cv2.INTER_AREA).astype(float)
    if "CAPTURE_ART1" not in imgs:
        return
    ref = imgs["CAPTURE_ART1"]
    R.p("F  capture (ART BKT, one exposure): each entry minus ART 1 (CTRL), 1/8 size: mean |dRGB| and share of pixels over 4 codes")
    for role in sorted(imgs, key=lambda r: (len(r), r)):
        if role == "CAPTURE_ART1":
            continue
        d = np.abs(imgs[role] - ref).max(2)
        R.p(f"     {role}: {d.mean():.2f}, {np.mean(d > 4) * 100:.1f} %")


def movie_test(files, R):
    import cv2
    fr = {}
    for role, f in files.items():
        cap = cv2.VideoCapture(f)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(n // 2, 0))
        ok, im = cap.read()
        if ok:
            fr[role] = cv2.resize(im, (im.shape[1] // 8, im.shape[0] // 8), interpolation=cv2.INTER_AREA).astype(float)
    if "MOVIE_ART1" in fr and "MOVIE_ART5" in fr:
        def red_chroma(im):
            b, g, r = im[..., 0], im[..., 1], im[..., 2]
            y = .299 * r + .587 * g + .114 * b
            return np.hypot(0.564 * (b - y), 0.713 * (r - y))
        a, b = red_chroma(fr["MOVIE_ART1"]), red_chroma(fr["MOVIE_ART5"])
        s = a > 15
        R.p(f"F  movie (pipe B): ART 5 / ART 1 chroma ratio over pixels with chroma > 15: median {np.median(b[s] / a[s]):.3f}; "
            f"compare the stills of the capture (a sector at x0 means stage 7 acts there)")


def classify(c, ents, R):
    """Which entry each chart JPEG resembles: |change from CTRL| against the nominal model's |change| (both hue signs)."""
    R.p("   classification check (correlation of |change| with each entry's nominal |change|):")
    preds = {}
    for n in range(1, 13):
        tname = T.ENTRIES[n - 1][3]
        t = T.decode(open_table_a() if tname is None else T.table(tname))
        best = 0
        for sign in (1, -1):
            Y2, cb2, cr2 = T.apply(t, c["Y"], c["cb"], c["cr"], {"sign": sign})
            preds.setdefault(n, []).append(np.abs(Y2 - c["Y"]) + np.abs(cb2 - c["cb"]) + np.abs(cr2 - c["cr"]))
    for n, e in sorted(ents.items()):
        s = c["ok"] & e["ok"]
        d = (np.abs(e["Y"] - c["Y"]) + np.abs(e["cb"] - c["cb"]) + np.abs(e["cr"] - c["cr"]))[s]
        sc = {m: max(np.corrcoef(d, p[s])[0, 1] if np.std(p[s]) > 0 else 0 for p in ps) for m, ps in preds.items()}
        best = max(sc, key=sc.get)
        R.p(f"     ART {n:2d} file looks like ART {best:2d} (r {sc[best]:.2f}){'' if best == n or n in (1, 10, 11, 12) and best in (10, 11, 12) else '  <- CHECK THE MAP'}")


def analyse(dirpath, mapfile=None):
    files = sorted(glob.glob(os.path.join(dirpath, "*.JPG")) + glob.glob(os.path.join(dirpath, "*.MOV")))
    mp = json.load(open(mapfile)) if mapfile else roles_from_names(files)
    json.dump(mp, open(os.path.join(dirpath, "map-used.json"), "w"), indent=1)
    R = Report()
    ents, adobe, refs, caps, movs = {}, {}, {}, {}, {}
    ctrl = {r: f for f, r in ((f, mp.get(os.path.basename(f))) for f in files) if r in ("ART1", "ADOBE_ART1", "REF_ART1")}
    for f in files:
        role = mp.get(os.path.basename(f))
        if not role:
            continue
        if role.startswith("CAPTURE_"):
            caps[role] = f; continue
        if role.startswith("MOVIE_"):
            movs[role] = f; continue
        m_ = re.search(r"ART(\d+)$", role)
        if not m_ or role.startswith("PHOTO_"):
            continue                              # the Picture Mode frames and the live-view photo: not analysed here
        n = int(m_.group(1))
        if role.startswith("REF_"):
            refs[n] = read_chart(f, "mock2a", ctrl.get("REF_ART1")); continue
        d = read_chart(f, "twelve", ctrl.get("ADOBE_ART1" if role.startswith("ADOBE_") else "ART1"))
        R.p(f"read {os.path.basename(f)} as {role}: {d['ok'].sum()} patches; registration {d['stats']}")
        (adobe if role.startswith("ADOBE_") else ents)[n] = d
    if 1 not in ents:
        R.p("no CTRL (ART1) development: nothing to analyse")
        return R
    c = ents[1]
    noise = np.std(c["Y"][(c["lay"]["kind"] == 6) & c["ok"]]) if ((c["lay"]["kind"] == 6) & c["ok"]).sum() > 3 else 0.7
    noise = max(noise, 0.3)
    R.p(f"noise (25 identical greys in ART 1, floor 0.3): {noise:.2f} codes")
    classify(c, ents, R)
    A = stage_a(c, ents[3], R, noise) if 3 in ents else None
    if A is None:
        return R
    B = stage_b(c, ents[10], R, A, noise) if 10 in ents else dict(ky=4.0, kc=4.0)
    C_ = stage_c(c, ents.get(4), ents.get(5), ents.get(6), R, A, noise)
    D = stage_d(c, ents[7], R, A, B, C_) if 7 in ents else {}
    roles = "swapped" if any(e == ("H", "hue") for e in [x for x in D.get(1, [])]) else "stock"
    start = dict(h0=A["h0"], kc=B.get("kc") or 4.0, ky=B.get("ky") or 4.0, kl=C_.get("kl", 0.25) * 1.0,
                 ks=C_.get("ks", 1 / 256), kh=C_.get("kh", 360 / T.HUE_TURN))
    if C_.get("sat") == "add":
        start["ks"] = C_["ks"]
    base = dict(sign=float(A["sign"]), sat=C_.get("sat", "mul"), roles=roles)
    discrete = [dict(base, window="hard"), dict(base, window="clamp"),
                dict(base, window="hard", roles="stock" if roles == "swapped" else "swapped"),
                dict(base, window="hard", sat="add" if base["sat"] == "mul" else "mul")]
    model, rms = stage_e(c, ents, R, start, discrete)
    stage_f(c, ents, R, A, model, adobe)
    scene_test(c, ents, refs, R)
    capture_test(caps, R)
    movie_test(movs, R)
    json.dump(R.values, open(os.path.join(dirpath, "results.json"), "w"), indent=1, default=lambda x: x if not isinstance(x, np.generic) else x.item())
    return R


def selftest():
    import simulate
    ok = True
    for name in ("nominal", "other"):
        d = os.path.join(EXP, "out", f"sim-{name}")
        if not os.path.exists(os.path.join(d, "SIM_ART12.JPG")):
            subprocess.run([sys.executable, os.path.join(HERE, "simulate.py"), d, "--truth", name], check=True)
        print(f"===== simulated camera run '{name}': {simulate.TRUTHS[name]}")
        R = analyse(d)
        v, tr = R.values, {**T.NOMINAL, **simulate.TRUTHS[name]}
        checks = [("hue sign", v["hue_sign"]["value"] == tr["sign"]),
                  ("hue zero", abs(wrap180(v["hue_zero_deg"]["value"] - tr["h0"])) < 1.0),
                  ("luma units", abs(v["luma_units_per_code"]["value"] - tr["ky"]) < 0.1 * tr["ky"]),
                  ("chroma units", abs(v["chroma_units_per_code"]["value"] - tr["kc"]) < 0.1 * tr["kc"]),
                  ("lightness", abs(v["light_code_per_unit"]["value"] - tr["kl"]) < 0.05 * tr["kl"]),
                  ("sat mode", v["sat_mode"]["value"] == tr["sat"]),
                  ("hue units", abs(v["hue_deg_per_unit"]["value"] - tr["kh"]) < 0.05 * tr["kh"]),
                  ("fit window", v["fit_hypothesis"]["value"]["window"] == tr["window"]),
                  ("fit roles", v["fit_hypothesis"]["value"]["roles"] == tr["roles"]),
                  ("order vs stage 6", v.get("order_ART11", {}).get("value") == ({"after": "after", "mid": "mid", "before6": "before6", "before5": "before6"}[tr["order"]])),
                  ("order vs look", v.get("order_ART12", {}).get("value") == ("before5" if tr["order"] == "before5" else "after")),
                  ("table B", v.get("adobe_uses_table_B", {}).get("value") == tr["adobe"])]
        for k, good in checks:
            print(f"   CHECK {k}: {'ok' if good else 'WRONG'}")
            ok &= bool(good)
    print("selftest", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    if "--guess" in sys.argv:
        guess_map(sys.argv[1], frame0="--no-frame0" not in sys.argv)
        sys.exit(0)
    mapf = sys.argv[sys.argv.index("--map") + 1] if "--map" in sys.argv else None
    analyse(sys.argv[1], mapf)

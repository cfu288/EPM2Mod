"""Read the camera's rendering of the synthetic test RAW (make_mock.py; NOTES §24).

Input: the JPEG the camera wrote when PB120001.ORF was re-developed with RAW Data Edit.
1. Where each patch landed. The JPEG is cropped and lens-distortion corrected, so patch positions
   are found from the picture itself: an "expected" brightness image is drawn from the layout, and
   at 24 x 18 control points a 7 x 7-patch piece of it is matched against the JPEG (normalised
   cross-correlation, quarter resolution, sub-pixel peak). A smooth 5th-degree polynomial
   displacement field is fitted to the matches (outliers dropped).
2. Each patch = median of the central 20 x 20 JPEG pixels (patch is ~48 x 48); the spread inside
   that window is kept as a quality flag.
3. The white balance and ColorMatrix the camera APPLIED are read from the output JPEG's EXIF
   (RAW Data Edit uses the camera's current WB, not the file's), giving per patch
       u = WB ⊙ raw,   v = ColorMatrix · u      (same v as everywhere else in this folder).

Usage:  ../../.venv/bin/python -I read_mock.py shots/PXXXXXXX.JPG   -> out/mock/read_PXXXXXXX.npz + _check.jpg
        ../../.venv/bin/python -I read_mock.py --selftest           (simulated JPEG with known distortion)
"""
import json, os, subprocess, sys
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "mock")
JW, JH = 4608, 3456          # camera JPEG (Large)
OX, OY = 16, 8               # nominal raw -> JPEG crop offset
DS = 4                       # matching resolution divisor
WIN = 10                     # half-size of the sampling window (20 x 20)


LAYOUTS = {"mock1": "mock_layout.npz", "mock2a": "mock2a_layout.npz", "mock2b": "mock2b_layout.npz"}   # PB120001, PB130001, PB130002


def layout(tag="mock1"):
    L = np.load(os.path.join(OUT, LAYOUTS[tag]))
    return L, int(L["P"]), int(L["X0"]), int(L["Y0"]), int(L["NC"]), int(L["NR"])


def expected_luma(L, P, X0, Y0, NC, NR):
    """Rough brightness of each patch in nominal JPEG coordinates, 0..1, at 1/DS scale."""
    u = L["raw_rgb"] * L["WB"]; v = np.clip(u @ L["M"].T, 0, None) / 3790.0
    y = np.clip(v @ np.array([0.299, 0.587, 0.114]), 0, 1) ** (1 / 2.2)
    g = np.zeros((NR, NC), np.float32); g[L["pos"][:, 0], L["pos"][:, 1]] = y
    p = P // DS
    img = np.zeros((JH // DS, JW // DS), np.float32)
    big = np.kron(g, np.ones((p, p), np.float32))
    x0, y0 = (X0 - OX) // DS, (Y0 - OY) // DS
    img[y0:y0 + big.shape[0], x0:x0 + big.shape[1]] = big[:img.shape[0] - y0, :img.shape[1] - x0]
    return img


def poly_terms(x, y, deg=5):
    xn, yn = (x - JW / 2) / (JW / 2), (y - JH / 2) / (JW / 2)
    return np.stack([xn ** i * yn ** j for i in range(deg + 1) for j in range(deg + 1 - i)], -1)


def register(jpg, L, P, X0, Y0, NC, NR, search=96):
    """Returns f(x_nominal, y_nominal) -> (x_jpeg, y_jpeg), and fit statistics."""
    exp = expected_luma(L, P, X0, Y0, NC, NR)
    got = cv2.resize(cv2.cvtColor(jpg, cv2.COLOR_RGB2GRAY), (JW // DS, JH // DS), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    p, s, half = P // DS, search // DS, (7 * (P // DS)) // 2
    pts, dsp, sc = [], [], []
    for r in range(2, NR, 4):
        for c in range(2, NC, 4):
            cx, cy = (X0 - OX) // DS + c * p + p // 2, (Y0 - OY) // DS + r * p + p // 2
            if cx - half < 0 or cy - half < 0 or cx + half >= exp.shape[1] or cy + half >= exp.shape[0]:
                continue
            t = exp[cy - half:cy + half + 1, cx - half:cx + half + 1]
            ax0, ay0 = max(cx - half - s, 0), max(cy - half - s, 0)
            a = got[ay0:min(cy + half + s + 1, got.shape[0]), ax0:min(cx + half + s + 1, got.shape[1])]
            m = cv2.matchTemplate(a, t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, (ix, iy) = cv2.minMaxLoc(m)
            fx = fy = 0.0
            if 0 < ix < m.shape[1] - 1 and 0 < iy < m.shape[0] - 1:
                l, c0, rr = m[iy, ix - 1], m[iy, ix], m[iy, ix + 1]; fx = 0.5 * (l - rr) / (l - 2 * c0 + rr)
                l, c0, rr = m[iy - 1, ix], m[iy, ix], m[iy + 1, ix]; fy = 0.5 * (l - rr) / (l - 2 * c0 + rr)
            pts.append((cx * DS + DS / 2 - 0.5, cy * DS + DS / 2 - 0.5))
            dsp.append(((ax0 + ix + fx + half - cx) * DS, (ay0 + iy + fy + half - cy) * DS)); sc.append(mx)
    pts, dsp, sc = np.array(pts), np.array(dsp), np.array(sc)
    ok = sc > 0.5
    A = poly_terms(pts[:, 0], pts[:, 1])
    if ok.sum() < 60:                                   # not this test image
        return None, dict(points=len(pts), used=0, score=float(np.median(sc)), rms=float("nan"), max_shift=float("nan"))
    for _ in range(4):
        cf = np.linalg.lstsq(A[ok], dsp[ok], rcond=None)[0]
        res = np.hypot(*(A @ cf - dsp).T)
        ok = (sc > 0.5) & (res < max(3.0, 3 * np.median(res[ok])))
        if ok.sum() < 60:
            return None, dict(points=len(pts), used=0, score=float(np.median(sc)), rms=float("nan"), max_shift=float("nan"))
    stats = dict(points=len(pts), used=int(ok.sum()), score=float(np.median(sc)), rms=float(np.sqrt(np.mean(res[ok] ** 2))),
                 max_shift=float(np.hypot(*dsp[ok].T).max()))
    return (lambda x, y: (x + poly_terms(x, y) @ cf[:, 0], y + poly_terms(x, y) @ cf[:, 1])), stats


def sample(jpg, f, L, P, X0, Y0):
    pos = L["pos"]
    xn = X0 - OX + pos[:, 1] * P + P / 2 - 0.5; yn = Y0 - OY + pos[:, 0] * P + P / 2 - 0.5
    xj, yj = f(xn, yn)
    med = np.full((len(pos), 3), np.nan); spr = np.full(len(pos), np.nan)
    for i, (x, y) in enumerate(zip(np.round(xj).astype(int), np.round(yj).astype(int))):
        if x - WIN < 0 or y - WIN < 0 or x + WIN > JW or y + WIN > JH:
            continue
        w = jpg[y - WIN:y + WIN, x - WIN:x + WIN].reshape(-1, 3).astype(float)
        med[i] = np.median(w, 0); spr[i] = w.std(0).max()
    return med, spr, np.stack([xj, yj], 1)


def exif_wb(path):
    e = json.loads(subprocess.run(["exiftool", "-j", "-n", "-WB_RBLevels", "-ColorMatrix", "-PictureMode", "-WhiteBalance2",
                                   "-ImageWidth", "-ImageHeight", path], capture_output=True, text=True).stdout)[0]
    lv = [float(x) for x in str(e["WB_RBLevels"]).split()]
    M = np.array([float(x) for x in str(e["ColorMatrix"]).split()]).reshape(3, 3) / 256
    return np.array([lv[0] / 256, 1.0, lv[1] / 256]), M, e


def check_image(jpg, xy, path):
    small = cv2.resize(jpg, (JW // 3, JH // 3), interpolation=cv2.INTER_AREA).copy()
    for x, y in xy:
        if np.isfinite(x):
            cv2.rectangle(small, (int((x - WIN) / 3), int((y - WIN) / 3)), (int((x + WIN) / 3), int((y + WIN) / 3)), (255, 255, 255), 1)
    cv2.imwrite(path, cv2.cvtColor(small, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])


def read(path, wb=None, M=None, tag=None):
    """tag = which test image; None = try every layout and keep the one that matches the JPEG best."""
    jpg = cv2.cvtColor(cv2.imread(path, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION), cv2.COLOR_BGR2RGB)
    assert jpg.shape[:2] == (JH, JW), f"expected a {JW}x{JH} JPEG (Large), got {jpg.shape[1]}x{jpg.shape[0]}"
    best = None
    for t in ([tag] if tag else [t for t in LAYOUTS if os.path.exists(os.path.join(OUT, LAYOUTS[t]))]):
        L, P, X0, Y0, NC, NR = layout(t); f, stats = register(jpg, L, P, X0, Y0, NC, NR); stats["layout"] = t
        if best is None or stats["used"] * stats["score"] > best[1]["used"] * best[1]["score"]: best = ((L, P, X0, Y0, NC, NR), stats, f)
    (L, P, X0, Y0, NC, NR), stats, f = best
    assert f is not None, "this JPEG matches none of the test images"
    med, spr, xy = sample(jpg, f, L, P, X0, Y0)
    info = {}
    if wb is None:
        wb, M, info = exif_wb(path)
    u = L["raw_rgb"] * wb; v = u @ M.T
    d = dict(jpg=med, spread=spr, xy=xy, raw_rgb=L["raw_rgb"], u=u, v=v, kind=L["kind"], pos=L["pos"], wb=wb, M=M, layout=stats["layout"])
    for k in ("sid", "weight"):
        if k in L.files: d[k] = L[k]
    return d, stats, info, jpg


def L_is_white(d):
    return (d["pos"][:, 0] % 8 == 0) & (d["pos"][:, 1] % 8 == 0)


def report(d, stats, info):
    k, spr, med = d["kind"], d["spread"], d["jpg"]
    print("registration:", {a: round(b, 2) if isinstance(b, float) else b for a, b in stats.items()})
    if info:
        print("camera applied: WB R,B =", d["wb"][[0, 2]] * 256, " ColorMatrix x256 =", (d["M"] * 256).round().astype(int).ravel().tolist(),
              " PictureMode", info.get("PictureMode"), " WhiteBalance2", info.get("WhiteBalance2"))
    good = np.isfinite(spr)
    print(f"patches read {good.sum()} / {len(spr)}; window spread (codes): median {np.nanmedian(spr):.2f}, 99th pct {np.nanpercentile(spr, 99):.2f}, "
          f"over 4.0: {(spr[good] > 4).sum()}")
    w = med[(k == 0) & (L_is_white(d))]; print("white lattice (108): mean RGB", np.nanmean(w, 0).round(1), " range per channel", (np.nanmax(w, 0) - np.nanmin(w, 0)))
    m = med[k == 4]; print("mid-gray repeats (49): mean RGB", np.nanmean(m, 0).round(1), " std", np.nanstd(m, 0).round(2), " range", (np.nanmax(m, 0) - np.nanmin(m, 0)))


def selftest(tag="mock1"):
    """Develop the mock with LibRaw, bend it like a lens correction would, read it back (layout auto-detected)."""
    import rawpy
    L, P, X0, Y0, NC, NR = layout(tag)
    with rawpy.imread(os.path.join(OUT, {"mock1": "PB120001.ORF", "mock2a": "PB130001.ORF", "mock2b": "PB130002.ORF"}[tag])) as r:
        rgb = r.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=8, demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
    rgb = rgb[:3472, :4640] if rgb.shape[0] >= 3472 else rgb
    h, w = rgb.shape[:2]
    # JPEG pixel (x, y) takes raw pixel at centre + (1 + k r^2)(p - centre): ~45 px at the corners, plus a 3 px offset
    yy, xx = np.mgrid[0:JH, 0:JW].astype(np.float32)
    cx, cy = JW / 2 + 3, JH / 2 - 2; r2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (JW / 2) ** 2
    kk = -0.027      # ~85 px at the corners, as measured on the camera
    mx = cx + (xx - cx) * (1 + kk * r2) + OX; my = cy + (yy - cy) * (1 + kk * r2) + OY
    sim = cv2.remap(rgb, mx, my, cv2.INTER_CUBIC)
    path = os.path.join(OUT, "selftest.jpg"); cv2.imwrite(path, cv2.cvtColor(sim, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    d, stats, _, jpg = read(path, wb=L["WB"], M=L["M"])
    assert stats["layout"] == tag, (stats["layout"], tag)
    report(d, stats, {})
    # truth: sample the undistorted development at the true patch centres
    pos = L["pos"]; tx = X0 + pos[:, 1] * P + P // 2; ty = Y0 + pos[:, 0] * P + P // 2
    truth = np.array([np.median(rgb[y - WIN:y + WIN, x - WIN:x + WIN].reshape(-1, 3), 0) for x, y in zip(tx, ty)])
    ok = np.isfinite(d["jpg"][:, 0]); err = np.abs(d["jpg"][ok] - truth[ok])
    print(f"selftest: patches {ok.sum()}; abs code error mean {err.mean():.3f}, 99.9th pct {np.percentile(err, 99.9):.1f}, max {err.max():.0f}; "
          f"patches off by more than 3 codes: {(err.max(1) > 3).sum()}")
    check_image(jpg, d["xy"], os.path.join(OUT, "selftest_check.jpg"))


if __name__ == "__main__":
    if sys.argv[1] == "--selftest":
        selftest(sys.argv[2] if len(sys.argv) > 2 else "mock1")
    else:
        d, stats, info, jpg = read(sys.argv[1])
        report(d, stats, info)
        name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
        np.savez(os.path.join(OUT, f"read_{name}.npz"), **d)
        check_image(jpg, d["xy"], os.path.join(OUT, f"read_{name}_check.jpg"))
        print("wrote", os.path.join(OUT, f"read_{name}.npz"))

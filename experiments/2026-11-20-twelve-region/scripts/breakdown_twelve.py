"""Where the 12-region tables change each film's error: lightness, chroma and hue parts, per subgroup. Research code.

    OMP_NUM_THREADS=2 uv run --with colour-science python experiments/2026-11-20-twelve-region/scripts/breakdown_twelve.py
    -> out/twelve/breakdown.txt (median over the films), out/twelve/breakdown-films.txt (each film)

For each patch, camera minus target in CIELAB: dL* (lightness), dC* (chroma; + = too saturated), dH* (hue, the
metric hue difference; + = turned counter-clockwise in a*b*), and the CIEDE2000 total. "now" = the film's camera
reading on films-look-exif; "table" = the same with the film's fitted table (fit_twelve.py, measured rules).
Subgroups: the test image's patch kinds; the ColorChecker by exposure; natural + hold-out colours by target hue
(6 sectors of 60 deg) and by target lightness (dark L* < 40, mid, bright > 70).
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit_twelve as FT  # noqa: E402
from mocklib import load  # noqa: E402

CC_FIRST_SID = 132          # make_mock2.colours_a: 132 grays, then the ColorChecker copies of 5 x 24 patches


def parts(X, Tl):
    L1 = FT.lab(X); dL = L1[:, 0] - Tl[:, 0]
    c1, c0 = np.hypot(L1[:, 1], L1[:, 2]), np.hypot(Tl[:, 1], Tl[:, 2])
    dh = np.angle(np.exp(1j * (np.arctan2(L1[:, 2], L1[:, 1]) - np.arctan2(Tl[:, 2], Tl[:, 1]))))
    return dict(dE=FT.de(L1, Tl), dL=dL, dC=c1 - c0, dH=2 * np.sqrt(c1 * c0) * np.sin(dh / 2))


def groups(F, sid):
    k, Tl = F.kind, F.T
    h = np.degrees(np.arctan2(Tl[:, 2], Tl[:, 1])) % 360; L = Tl[:, 0]; c = np.hypot(Tl[:, 1], Tl[:, 2])
    nat = (k == 5) | (k == 9)
    g = {"natural": k == 5, "hold-out": k == 9, "skin": k == 8, "grays": k == 6, "near-neutral": k == 3,
         "dense grays": k == 2}
    ev = ((sid - CC_FIRST_SID) % 120) // 24 - 2
    g.update({f"ColorChecker {e:+d} EV": (k == 7) & (ev == e) for e in range(-2, 3)})
    names = ["red", "yellow", "green", "cyan", "blue", "magenta"]          # a*b* hue sectors centred on 0, 60, ... deg
    for i, nm in enumerate(names):
        g[f"nat. {nm} (h {60 * i - 30 if i else 330}-{60 * i + 30})"] = nat & (c > 10) & (((h - 60 * i + 30) % 360) < 60)
    g.update({"nat. dark L*<40": nat & (L < 40), "nat. mid": nat & (L >= 40) & (L <= 70), "nat. bright L*>70": nat & (L > 70)})
    return {n: m & F.ok for n, m in g.items()}


def stats(p, m):
    return [p["dE"][m].mean(), np.abs(p["dL"][m]).mean(), np.abs(p["dC"][m]).mean(), np.abs(p["dH"][m]).mean(),
            p["dL"][m].mean(), p["dC"][m].mean(), p["dH"][m].mean()]


COLS = ["dE00", "|dL|", "|dC|", "|dH|", "mean dL", "mean dC", "mean dH"]


def main():
    rd = FT.readings(); per, rows = [], {}
    for fid, (tag, fitp) in rd.items():
        path = os.path.join(FT.OUT, f"{fid}.bin")
        if not os.path.exists(path):
            continue
        F = FT.Film(fid, tag, fitp); sid = load(tag)["sid"]
        p0, p1 = parts(F.J, F.T), parts(F.rules(open(path, "rb").read()), F.T)
        per.append(f"\n{fid}\n{'':34s}" + "".join(f"{c:>15s}" for c in COLS) + "      n")
        for n, m in groups(F, sid).items():
            if m.sum() < 5:
                continue
            a, b = stats(p0, m), stats(p1, m)
            rows.setdefault(n, []).append((a, b))
            per.append(f"  {n:32s}" + "".join(f"  {x:5.2f} -> {y:5.2f}" for x, y in zip(a, b)) + f"  {m.sum():5d}")
        print(fid, flush=True)
    out = [f"Median over {len(next(iter(rows.values())))} films, "
           "camera now -> with the film's 12-region table (CIELAB parts; dE00 = CIEDE2000)",
           f"{'':34s}" + "".join(f"{c:>15s}" for c in COLS) + "  films better (dE00)"]
    for n, v in rows.items():
        a = np.median([x for x, _ in v], 0); b = np.median([y for _, y in v], 0)
        better = sum(y[0] < x[0] - 0.005 for x, y in v)
        out.append(f"  {n:32s}" + "".join(f"  {x:5.2f} -> {y:5.2f}" for x, y in zip(a, b)) + f"  {better}/{len(v)}")
    open(os.path.join(FT.OUT, "breakdown.txt"), "w").write("\n".join(out) + "\n")
    open(os.path.join(FT.OUT, "breakdown-films.txt"), "w").write("\n".join(per) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()

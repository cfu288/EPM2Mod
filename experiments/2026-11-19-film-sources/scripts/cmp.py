"""cmp.py A.cube B.cube [...]: compare film target LUTs (V-Log/V-Gamut in, sRGB out) on the same scene colours.
Scene: ColorChecker (D65, mid grey 0.18 linear), a grey ramp -4..+3 EV, 2000 random scene colours (seed 1).
Prints mean / p95 ΔE2000 of each LUT against the first, raw and after matching mid-grey L* (exposure offset)."""
import sys, numpy as np, colour
rng = np.random.default_rng(1)
cc = colour.CCS_COLOURCHECKERS["ColorChecker24 - After November 2014"]
xyz = colour.xyY_to_XYZ(np.array(list(cc.data.values())))
lin_cc = colour.XYZ_to_RGB(xyz, "sRGB", illuminant=cc.illuminant, chromatic_adaptation_transform="Bradford", apply_cctf_encoding=False)
lin_cc *= 0.18 / lin_cc[21].mean()  # patch 22 (neutral 5) at 0.18
ramp = np.repeat((0.18 * 2.0 ** np.linspace(-4, 3, 15))[:, None], 3, 1)
rnd = 0.18 * 2.0 ** rng.uniform(-3, 2, (2000, 1)) * rng.dirichlet([1, 1, 1], 2000) * 3
vgamut = colour.RGB_COLOURSPACES["V-Gamut"]
def run(path, lin):
    lut = colour.read_LUT(path)
    v = colour.RGB_to_RGB(lin, colour.RGB_COLOURSPACES["sRGB"], vgamut, chromatic_adaptation_transform=None)
    enc = colour.models.log_encoding_VLog(np.maximum(v, 0))
    out = np.clip(lut.apply(enc), 0, 1)
    return colour.XYZ_to_Lab(colour.sRGB_to_XYZ(out))
sets = {"ColorChecker": lin_cc, "grey ramp": ramp, "random": rnd}
base = {k: run(sys.argv[1], s) for k, s in sets.items()}
g = run(sys.argv[1], np.array([[0.18] * 3]))[0]
print(f"{sys.argv[1].split('/')[-1]}: mid grey L*a*b* {np.round(g, 1)}")
for p in sys.argv[2:]:
    gg = run(p, np.array([[0.18] * 3]))[0]
    line = [f"{p.split('/')[-1]}: mid grey {np.round(gg, 1)}"]
    for k, s in sets.items():
        lab = run(p, s)
        de = colour.delta_E(base[k], lab, method="CIE 2000")
        lab2 = lab.copy(); lab2[:, 0] += g[0] - gg[0]
        de2 = colour.delta_E(base[k], lab2, method="CIE 2000")
        line.append(f"{k} {de.mean():.1f} (p95 {np.percentile(de, 95):.1f}); L*-matched {de2.mean():.1f} (p95 {np.percentile(de2, 95):.1f})")
    print("\n   ".join(line))

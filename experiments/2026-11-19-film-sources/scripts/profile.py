"""profile.py CUBE...: the tone curve (L* of grey at -4..+3 EV), the ColorChecker mean chroma, and the hue shift of six
saturated patches, for each target LUT."""
import sys, numpy as np, colour
sys.argv[0:1] = []
exec(open(__file__.replace("profile.py", "cmp.py")).read().split("sets = ")[0].replace("import sys, numpy as np, colour", ""))
for p in sys.argv:
    g = run(p, ramp)[:, 0]
    lab = run(p, lin_cc)
    C = np.hypot(lab[:, 1], lab[:, 2])
    h = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
    print(p.split("/")[-1][:60])
    print("  grey L* at EV -4..+3:", " ".join(f"{x:.0f}" for x in g[::2]))
    print(f"  ColorChecker mean chroma {C[:18].mean():.1f}; blue/green/red/yellow/magenta/cyan hue", " ".join(f"{x:.0f}" for x in h[12:18]), "chroma", " ".join(f"{x:.0f}" for x in C[12:18]))

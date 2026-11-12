"""Fit a forward model of the six-axis stage to the probe (before/after per patch, three modes).
Model in BT.601 CbCr of the 'before' colour: angle t, chroma c.
  gain(t)  = 1 + a * sum_i dS_i w_i(t)        shift(t) = b * sum_i dH_i w_i(t)   [deg]
w_i = piecewise-linear hats between six axis angles phi_i (fitted), summing to 1.
dS, dH = probe record - stock record (variant with slot 1 = stock +3 or +0: both tried)."""
import json, sys, importlib.util
import numpy as np
from scipy.optimize import least_squares
sys.argv = ["x"]
sp = importlib.util.spec_from_file_location("p6", "analyze_probe6.py")
src = open("analyze_probe6.py").read().split("out = {}")[0]; ns = {}; exec(src, ns)
patches, ycc = ns["patches"], ns["ycc"]
STOCK = {"Vivid": ((18, 4, 24, 0, 8, 8), (0, 2, 4, -1, -6, 0)), "Muted": ((-22, 4, -16, 0, 4, -8), (3, 0, -3, 7, 8, 10)), "Portrait": ((14, 0, 0, 5, 0, 0), (-1, 0, 2, -2, 0, 0))}
PROBE = {"Vivid": ((40, 0, 0, -40, 0, 0), (0, 20, 0, 0, -20, 0)), "Muted": ((0, 40, 0, 0, -40, 0), (0, 0, 20, 0, 0, -20)), "Portrait": ((0, 0, 40, 0, 0, -40), (20, 0, 0, -20, 0, 0))}
FILES = {"Vivid": ("PB090238", "PB090244"), "Muted": ("PB090239", "PB090245"), "Portrait": ("PB090240", "PB090246")}
D = []
for m, (a, b) in FILES.items():
    A, B = patches(a)[:6].reshape(-1, 3), patches(b)[:6].reshape(-1, 3)
    ok = (A.min(1) > 6) & (A.max(1) < 249) & (B.min(1) > 6) & (B.max(1) < 249)
    ya, cba, cra = ycc(A); yb, cbb, crb = ycc(B); ca = np.hypot(cba, cra); ok &= ca > 12
    t = np.degrees(np.arctan2(cra, cba)) % 360
    D.append((m, t[ok], (np.hypot(cbb, crb) / ca)[ok], ((np.degrees(np.arctan2(crb, cbb)) - t + 180) % 360 - 180)[ok], (yb - ya)[ok], ca[ok]))

def hats(t, phi):
    o = np.argsort(phi); p = phi[o]; w = np.zeros((len(t), 6))
    for k in range(6):
        p0, p1 = p[k], p[(k + 1) % 6] + (360 if k == 5 else 0)
        tt = np.where(t < p[0], t + 360, t)
        m = (tt >= p0) & (tt < p1); f = (tt[m] - p0) / (p1 - p0)
        w[m, o[k]] += 1 - f; w[m, o[(k + 1) % 6]] += f
    return w

def model(p, m, t, slot1):
    phi = p[:6] % 360; a, b = p[6], p[7]
    dS = np.array(PROBE[m][0], float) - STOCK[m][0]; dH = np.array(PROBE[m][1], float) - STOCK[m][1]
    dS[1] -= slot1; dH[1] -= slot1
    w = hats(t, phi); return 1 + a * (w @ dS), b * (w @ dH)

def resid(p, slot1):
    r = []
    for m, t, g, s, dy, c in D:
        mg, ms = model(p, m, t, slot1); r += [(mg - g) * 100, (ms - s)]
    return np.concatenate(r)

best = None
for slot1 in (0, 3):
    for start in ([110, 200, 350, 290, 20, 170], [100, 220, 340, 280, 40, 160], [60, 180, 300, 240, 0, 120], [90, 210, 330, 270, 30, 150], [120, 240, 0, 300, 60, 180]):
        for rot in range(0, 360, 60):
            r = least_squares(resid, np.array([(x + rot) % 360 for x in start] + [0.005, -1.0]), args=(slot1,), max_nfev=300)
            if best is None or r.cost < best[0]: best = (r.cost, r.x, slot1)
c, p, slot1 = best
print("best fit: slot-1 offset", slot1, " axis angles (CbCr deg) slots 0..5:", (p[:6] % 360).round(0), f" chroma {p[6]*100:.2f} % per unit, hue {p[7]:.2f} deg per unit")
print("rms: chroma ratio %.3f, hue %.1f deg" % (np.sqrt(np.mean((resid(p, slot1)[0::1][:0] if False else np.concatenate([(model(p,m,t,slot1)[0]-g) for m,t,g,s,dy,cc in D]))**2)), np.sqrt(np.mean(np.concatenate([(model(p,m,t,slot1)[1]-s) for m,t,g,s,dy,cc in D])**2))))
print("no-model baseline rms: chroma %.3f, hue %.1f deg" % (np.sqrt(np.mean(np.concatenate([g-1 for m,t,g,s,dy,cc in D])**2)), np.sqrt(np.mean(np.concatenate([s for m,t,g,s,dy,cc in D])**2))))
ref = {"red (Cr+)": 90, "yellow": 170, "green": 225, "cyan": 270, "blue (Cb+)": 0, "magenta": 45}
print("for orientation, BT.601 CbCr angles of pure colours: R 113, Y 173, G 232, C 293, B 353, M 52")
np.save("out/sixaxis_fit.npy", np.concatenate([p, [slot1]]))

"""Figures for README.md, from the camera readings in out/mock/ and the fits in fits/ (NOTES §45-46).
   ../../.venv/bin/python -I make_figures.py        -> figures/*.png"""
import os, sys
sys.argv = ["x"]; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from mocklib import *
import model2 as M2
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"            # categorical slots 1-4, in this order (validated)
INK, INK2, GRID, SURF, REF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#9b9a94"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "axes.titlesize": 11, "axes.titleweight": "bold"})
FILMS = [("Portra 400", "portra", "portra"), ("Ektachrome 100", "ektachrome", "ektachrome"), ("Pro 400H", "pro400h", "pro400h"), ("Kodachrome 64", "kodachrome", "kodachrome64"),
         ("Vision3 250D", "vis250d", "vision3250d"), ("Velvia 100", "velvia", "velvia100"), ("Superia 400", "superia", "superia400")]
GROUPS = [(5, "Natural colours"), (8, "Skin"), (6, "Grays"), (7, "ColorChecker, five exposures")]
os.makedirs("figures", exist_ok=True)
def target_of(z):
    cube, size = fl.load_cube(str(z["lut"])); return lambda v: np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(v, 0) / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255
nat = load("M_natural"); D = {}
for name, rd, ft in FILMS:
    z = np.load(f"fits/fit_film-{ft}-m1.npz"); d = load("F5_" + rd); T = target_of(z)(d["vs"])
    D[name] = dict(z=z, d=d, T=T, J=d["jpg"], k=d["kind"], ok=d["ok"], model=M2.render(d["u"], z["G"], M2.gain_of(z), z["S"], z["H"], z["P"], M2.chroma_of(z)))
mean = lambda dd, m: float(dd[m].mean())
def save(fig, name): fig.savefig(f"figures/{name}.png", dpi=170, bbox_inches="tight"); plt.close(fig); print("wrote", f"figures/{name}.png")

# 1. ColorChecker swatches: target (upper left) against camera (lower right)
lay = np.load("testraw/mock2a_layout.npz"); sid = lay["sid"]; k7 = np.flatnonzero(lay["kind"] == 7); first = k7[np.argsort(sid[k7])][48:72]           # the 24 patches at 0 EV, first copy
fig, ax = plt.subplots(figsize=(13.5, 4.6)); ax.set_xlim(0, 24); ax.set_ylim(len(FILMS), 0); ax.axis("off")
for r, (name, _, _) in enumerate(FILMS):
    e = D[name]
    for c, i in enumerate(first):
        t, j = np.clip(e["T"][i] / 255, 0, 1), np.clip(np.nan_to_num(e["J"][i]) / 255, 0, 1); x0, y0, s = c + 0.04, r + 0.06, 0.92
        ax.add_patch(Polygon([(x0, y0), (x0 + s, y0), (x0, y0 + s * 0.94)], color=t, lw=0)); ax.add_patch(Polygon([(x0 + s, y0), (x0 + s, y0 + s * 0.94), (x0, y0 + s * 0.94)], color=j, lw=0))
    ax.text(-0.15, r + 0.5, name, ha="right", va="center", fontsize=10)
ax.set_title("ColorChecker patches at normal exposure: film target (upper left half) and camera JPEG (lower right half)", loc="left", pad=10)
save(fig, "swatches")

# 2. accuracy per group, with the stock Natural mode against the same target as reference
fig, axs = plt.subplots(1, 4, figsize=(13.5, 3.6), sharey=True)
for ax, (kk, gname) in zip(axs, GROUPS):
    cam = [mean(de(lab(D[n]["J"]), lab(D[n]["T"])), D[n]["ok"] & (D[n]["k"] == kk)) for n, _, _ in FILMS]
    ref = [mean(de(lab(nat["jpg"]), lab(D[n]["T"])), nat["ok"] & (nat["kind"] == kk)) for n, _, _ in FILMS]; y = np.arange(len(FILMS))
    ax.barh(y, cam, height=0.5, color=BLUE, zorder=3); ax.scatter(ref, y, marker="|", s=260, color=REF, linewidths=2, zorder=4)
    for yi, (c, rf) in enumerate(zip(cam, ref)): ax.text(c + 0.12, yi, f"{c:.2f}", va="center", fontsize=9, color=INK); ax.text(rf + 0.15, yi, f"{rf:.1f}", va="center", fontsize=8, color=INK2)
    ax.set_title(gname, loc="left"); ax.set_xlim(0, 9); ax.set_yticks(y); ax.set_yticklabels([n for n, _, _ in FILMS]); ax.grid(axis="x", color=GRID, lw=0.8, zorder=0); ax.set_xlabel("ΔE2000 against the film target"); ax.tick_params(length=0)
axs[0].invert_yaxis()
axs[0].text(0.02, -0.33, "Blue bar: the film look in the camera.   Gray mark: the camera's stock Natural mode against the same target.", transform=axs[0].transAxes, fontsize=9, color=INK2)
save(fig, "accuracy")

# 3. where the difference comes from (natural colours)
fig, ax = plt.subplots(figsize=(9.5, 3.9)); y = np.arange(len(FILMS)); rows = []
for n, _, _ in FILMS:
    e = D[n]; m = e["ok"] & (e["k"] == 5); rows.append((mean(de(lab(e["model"]), lab(e["T"])), m), mean(de(lab(e["J"]), lab(e["model"])), m), mean(de(lab(e["J"]), lab(e["T"])), m)))
rows = np.array(rows)
for i, (lab_, col) in enumerate((("Model against target: what the camera's stages can express", BLUE), ("Camera against model: rounding and model error", ORANGE), ("Camera against target: the result", AQUA))):
    ax.barh(y + (i - 1) * 0.27, rows[:, i], height=0.22, color=col, label=lab_, zorder=3)
    for yi, v in enumerate(rows[:, i]): ax.text(v + 0.02, yi + (i - 1) * 0.27, f"{v:.2f}", va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels([n for n, _, _ in FILMS]); ax.invert_yaxis(); ax.set_xlim(0, 1.9); ax.grid(axis="x", color=GRID, lw=0.8, zorder=0); ax.tick_params(length=0)
ax.set_xlabel("ΔE2000, natural colours"); ax.set_title("Where the remaining difference comes from", loc="left"); ax.legend(frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1.0, -0.42), ncol=1)
save(fig, "decomposition")

# 4. camera against target, patch by patch (Portra): lightness and chroma, with stock Natural for comparison
e = D["Portra 400"]; m = e["ok"] & np.isin(e["k"], (5, 7, 8)); mn = nat["ok"] & np.isin(nat["kind"], (5, 7, 8)); LT, LJ, LN = lab(e["T"]), lab(e["J"]), lab(nat["jpg"]); ch = lambda L: np.hypot(L[:, 1], L[:, 2])
fig, axs = plt.subplots(1, 2, figsize=(11, 5))
for ax, (title, f, lim) in zip(axs, (("Lightness L*", lambda L: L[:, 0], (0, 100)), ("Chroma C*", ch, (0, 90)))):
    ax.scatter(f(LT)[mn], f(LN)[mn], s=5, color=REF, alpha=0.45, lw=0, label="Stock Natural mode", zorder=2); ax.scatter(f(LT)[m], f(LJ)[m], s=5, color=BLUE, alpha=0.6, lw=0, label="Portra look", zorder=3)
    ax.plot(lim, lim, color=INK, lw=1, zorder=4); ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal"); ax.grid(color=GRID, lw=0.8, zorder=0); ax.tick_params(length=0)
    ax.set_xlabel(f"{title} of the Portra 400 target"); ax.set_ylabel(f"{title} of the camera JPEG"); ax.set_title(title + ", one point per patch", loc="left")
axs[0].legend(frameon=False, fontsize=9, markerscale=3, loc="upper left"); axs[0].text(62, 54, "exact match", rotation=45, fontsize=8, color=INK2)
save(fig, "scatter_portra")

# 5. tone: lightness of gray patches against scene exposure
fig, ax = plt.subplots(figsize=(8.5, 4.6)); g = e["ok"] & (e["k"] == 6); ev = np.log2(np.maximum(e["d"]["vs"][g][:, 1], 1e-6) / fl.V_GRAY); o = np.argsort(ev)
ax.plot(ev[o], lab(nat["jpg"])[g][o, 0], color=REF, lw=2, label="Stock Natural mode (camera)", zorder=2); ax.plot(ev[o], LT[g][o, 0], color=INK, lw=2, label="Portra 400 target", zorder=3)
ax.scatter(ev[o][::3], LJ[g][o, 0][::3], s=22, color=BLUE, zorder=4, label="Portra look (camera)", edgecolors=SURF, linewidths=0.8)
ax.set_xlabel("Scene exposure of a gray patch, stops from middle gray"); ax.set_ylabel("Lightness L* in the JPEG"); ax.set_title("Tone: gray patches from 5 stops under to 4 stops over", loc="left"); ax.grid(color=GRID, lw=0.8, zorder=0); ax.tick_params(length=0); ax.legend(frameon=False, fontsize=9)
save(fig, "tone_portra")

# 6. the steps that got Portra here
steps = [("First camera-\ncorrected fit", "A_portra_xp9"), ("Second\ncorrection", "A_portra_xp10"), ("With chroma\ncurves", "F3_portra"), ("With the\nsecond model", "F5_portra")]
fig, ax = plt.subplots(figsize=(8.5, 4.4)); tg = target_of(D["Portra 400"]["z"])
for (kk, gname), col in zip(((7, "ColorChecker"), (8, "Skin"), (5, "Natural colours"), (6, "Grays")), (BLUE, ORANGE, AQUA, YELLOW)):
    v = []
    for _, rd in steps: d = load(rd); v.append(mean(de(lab(d["jpg"]), lab(tg(d["vs"]))), d["ok"] & (d["kind"] == kk)))
    ax.plot(range(len(steps)), v, color=col, lw=2, marker="o", ms=7, mec=SURF, mew=1.5, zorder=3); ax.text(len(steps) - 1 + 0.08, v[-1] + {"Natural colours": 0.04, "Skin": -0.04}.get(gname, 0), f"{gname} {v[-1]:.2f}", va="center", fontsize=9); ax.text(-0.08, v[0], f"{v[0]:.2f}", va="center", ha="right", fontsize=9)
ax.set_xticks(range(len(steps))); ax.set_xticklabels([s for s, _ in steps]); ax.set_xlim(-0.45, len(steps) - 1 + 1.0); ax.set_ylim(0, 3); ax.set_ylabel("ΔE2000 against the Portra 400 target"); ax.grid(axis="y", color=GRID, lw=0.8, zorder=0); ax.tick_params(length=0)
ax.set_title("Portra 400 on the camera, build by build", loc="left")
save(fig, "progress_portra")

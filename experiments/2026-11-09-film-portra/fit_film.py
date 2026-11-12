"""Fit a film target LUT into a camera slot with the calibrated model (NOTES §25-26); first build, model only.

Slots:
  lighttone  Light Tone (codes 72 / 81): as popart2, plus two compare immediates for the matrix (see SLOTS).
  popart2  Pop Art II (art codes 102 / 103). Its own look table, saturation pair, six-axis records and
           matrix table; per-channel base gamma by re-pointing its two entries in the hash table
           0x7E78C154 from the one-record handler 0x7E56B822 to Cross Process II's three-record
           handler 0x7E56B82A (data only). Cross Process II then shares these curves.
Objective: GRKit sample set and weights, ΔE2000, as fit_xp9.py but without a measured anchor.
   ../../.venv/bin/python -I fit_film.py --lut out/lut/.../x.cube --slot popart2 --name film-ektachrome-pa2
"""
import argparse, json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import least_squares
import fit_xp9 as f
from mocklib import *

SLOTS = {"xp1": dict(gamma_recs=(0x7E78B41C, 0x7E78B43C, 0x7E78B45C), look=0x7E75F2F0, sat=0x7E7696B4, six_s=0x7E7694FE, six_h=0x7E76950A, matrix=0x7E768F46,
                     repoint=[], code=[(0x7E56C6A6, b"\x46", b"\x55"), (0x7E56C6AA, b"\x4f", b"\x57")]),     # Cross Process I (85 / 87)
         # Top-level Pop Art (codes 70 / 79) as a third film slot: needs patches/slot3-code.json (new code; NOTES 29-30).
         # Gamma records = those of Pale&Light, Light Tone, Pop Art II; matrix table t3 inside the new code (holds an identity until written).
         "popart1": dict(gamma_recs=(0x7E78B3DC, 0x7E78B3FC, 0x7E78B47C), look=0x7E75E6F0, sat=0x7E7696A0, six_s=0x7E769486, six_h=0x7E769492, matrix=0x7E880FC2,
                         matrix_expect=struct.pack("<9h", 256, 0, 0, 0, 256, 0, 0, 0, 256), repoint=[], code=[]),
         "popart2": dict(gamma_recs=(0x7E78B49C, 0x7E78B4BC, 0x7E78B4DC), look=0x7E75FAF0, sat=0x7E7696BC, six_s=0x7E76952E, six_h=0x7E76953A, matrix=0x7E768F58,
                         repoint=[(0x7E78C154 + 4, 0x7E56B822, 0x7E56B82A), (0x7E78C154 + 3 * 8 + 4, 0x7E56B822, 0x7E56B82A)], code=[]),
         # Light Tone (codes 72 still / 81 movie; one type, a top-level menu entry). Stock rendering is explained by the
         # model to 0.94 dE (NOTES 26.5). Matrix: the 102 / 103 compares are re-keyed to 72 / 81, so Pop Art II loses its matrix.
         "lighttone": dict(gamma_recs=(0x7E78B49C, 0x7E78B4BC, 0x7E78B4DC), look=0x7E75EAF0, sat=0x7E7696A8, six_s=0x7E7694B6, six_h=0x7E7694C2, matrix=0x7E768F58,
                           repoint=[(0x7E78C154 + 2 * 8 + 4, 0x7E56B7F0, 0x7E56B82A), (0x7E78C154 + 11 * 8 + 4, 0x7E56B7F0, 0x7E56B82A)],
                           code=[(0x7E56C6AE, b"\x66", b"\x48"), (0x7E56C6B2, b"\x67", b"\x51")])}
# The four slots added by patches/slots7-code.json (NOTES 32): three own gamma tables each (the column stills use),
# shared identity look table, linear chroma curves, matrix table in code area 2. Addresses from slots/slots7_layout.json.
_lay = os.path.join(HERE, "slots", "slots7_layout.json")
if os.path.exists(_lay):
    _L = json.load(open(_lay)); _t = lambda k: int(_L["tables"][k], 16); _s = lambda k: int(_L["s2"][k], 16); _id = struct.pack("<9h", 256, 0, 0, 0, 256, 0, 0, 0, 256)
    for _nm, _n, _sat, _six in (("palelight1", "4", 0x7E7696A4, (0x7E76949E, 0x7E7694AA)), ("softfocus", "5", 0x7E76969C, (0x7E76946E, 0x7E76947A)),
                                ("pinhole1", "6", 0x7E7696AC, (0x7E7694CE, 0x7E7694DA)), ("diorama", "7", 0x7E7696B0, (0x7E7694E6, 0x7E7694F2))):
        SLOTS[_nm] = dict(gamma_tabs=[_t(f"G{_n}R"), _t(f"G{_n}G"), _t(f"G{_n}B")], look=None, sat=_sat, six_s=_six[0], six_h=_six[1], matrix=_s("t" + _n), matrix_expect=_id, repoint=[], code=[])
ap = argparse.ArgumentParser(); ap.add_argument("--lut", required=True); ap.add_argument("--slot", default="xp1", choices=sorted(SLOTS), help="where the stand-alone patch writes the look; the fitted numbers do not depend on it. The seven-film build takes them from the fit file (slots/build_seven_films.py), so xp1 is the usual choice; the generic slot names here follow the superseded slots7 layout"); ap.add_argument("--name", required=True)
ap.add_argument("--free-red-hue", action="store_true"); ap.add_argument("--robust", type=float, default=0.0, help="soft-L1 loss scale (0 = plain least squares): limits the pull of the few very large errors")
ap.add_argument("--anchor", nargs=2, metavar=("READ_NAME", "FIT_NPZ"), help="measured mock re-development of an earlier build of this film + that build's fit: adds the mock patches as measured + model change, and starts from that fit")
a = ap.parse_args()
cube, size = fl.load_cube(a.lut)
tgt = lambda v: lab(np.clip(fl.apply_cube(cube, size, fl.encode(np.maximum(v, 0) / fl.V_GRAY * 0.18, "vlog")), 0, 1) * 255)
KN = f.KN; lin, w, kind = fl.samples()
# Extra grays from the top of the GRKit ramp (+2.6 EV) to sensor clipping (+3.95 EV, v = 4106): without them the
# top of each curve is unconstrained and blown highlights take a colour cast (first Ektachrome fit: R 909, G 839).
top = np.repeat((0.18 * 2 ** np.linspace(2.7, 3.95, 12))[:, None], 3, 1)
lin = np.concatenate([lin, top]); w = np.concatenate([w, np.full(12, 150.0)]); kind = np.concatenate([kind, np.zeros(12, int)])
vs = lin / 0.18 * fl.V_GRAY; us = vs @ f.MINV.T; tl = tgt(vs)
uh = f.uh; tlh = tgt(uh @ M5300.T)
Pm = load("A_natural"); mk = Pm["ok"] & (Pm["kind"] == 9); um = Pm["u"][mk]; tlm = tgt(Pm["vs"][mk])       # hold-out naturals of test image A (prediction only)

AN = None; V2 = False
if a.anchor:
    Am = load(a.anchor[0]); za = np.load(a.anchor[1]); Ja = Am["jpg"]; ka = Am["kind"]
    V2 = "weight" in Am                      # second-generation test image: holds the fit's own samples and weights (NOTES 27)
    if V2:   # objective = the measured samples themselves: GRKit weights; skin series 20; near-neutrals 4; dense grays 20 (as before)
        wa = np.where(Am["weight"] > 0, Am["weight"], np.where(ka == 8, 20.0, np.where(ka == 3, 4.0, np.where(ka == 2, 20.0, 0.0))))
        sel = Am["ok"] & (wa > 0)
    else:
        wa = np.where(ka == 5, 1.0, np.where(ka == 3, 4.0, 20.0)); sel = Am["ok"] & np.isin(ka, (2, 3, 5)) & (Ja.min(1) > 2) & (Ja.max(1) < 253)
    AN = dict(u=Am["u"][sel], J=Ja[sel], k=ka[sel], tl=tgt(Am["vs"][sel]), base=f.R(Am["u"][sel], za["G"], float(za["sat"]), za["S"], za["H"], za["P"]), w=wa[sel],
              unc=(Ja[sel].min(1) > 2) & (Ja[sel].max(1) < 253))
def anchored(G, sat, S, H, P):
    """measured + model change; where the measured patch is clipped, the model alone."""
    m = f.R(AN["u"], G, sat, S, H, P)
    return np.where(AN["unc"][:, None], np.clip(AN["J"] + m - AN["base"], 0, 255), m)

def unpack(p):
    H = p[3 * KN + 7:3 * KN + 13].copy()
    if not a.free_red_hue: H[0] = 0.0
    return f.curves(p), p[3 * KN], p[3 * KN + 1:3 * KN + 7], H, f.P_of(p[3 * KN + 13:3 * KN + 19])
def res(p, fixed=None):
    if fixed is not None: p = np.concatenate([p, fixed])
    G, sat, S, H, P = unpack(p)
    r = [0.05 * np.diff(G[:, ::32], 2, axis=1).ravel(), 0.1 * p[3 * KN + 1:3 * KN + 13]]
    if not V2: r.append(np.sqrt(w) * de(lab(f.R(us, G, sat, S, H, P)), tl))          # model-only term; replaced by measured samples with a v2 anchor
    if AN: r.append(np.sqrt(AN["w"]) * de(lab(anchored(G, sat, S, H, P)), AN["tl"]))
    return np.concatenate(r)
lo = np.concatenate([np.zeros(3 * KN), [0.6], [-40] * 6, [-20] * 6, [-64] * 6]); hi = np.concatenate([np.full(3 * KN, 40.0), [1.4], [40] * 6, [20] * 6, [64] * 6])
z9 = np.load("out/fit_xp9.npz")
starts = {"from Portra xp9": np.concatenate([f.knots_of(z9["G"]), [float(z9["sat"])], z9["S"], z9["H"], f.off(z9["P"] * 128)]),
          "from neutral": np.concatenate([f.knots_of(IDG), [1.0], np.zeros(12), f.off(np.round(M5300 * 128))])}
if AN: starts = {"from the anchor fit": np.concatenate([f.knots_of(za["G"]), [float(za["sat"])], za["S"], za["H"], f.off(za["P"] * 128)])}
LOSS = dict(loss="soft_l1", f_scale=a.robust) if a.robust else {}
best = None
for nm, p0 in starts.items():
    r = least_squares(res, np.clip(p0, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), x_scale="jac", max_nfev=200, **LOSS)
    print(f"  start {nm}: cost {r.cost:.1f}")
    if best is None or r.cost < best.cost: best = r
G, sat, S, H, P = unpack(best.x)
S, H = np.round(S), np.round(H); A = f.find_A(P); Pq = f.renormalise(A) / 128.0
fixed = np.concatenate([S, H, f.off(Pq * 128)]); n0 = 3 * KN + 1
r2 = least_squares(lambda q: res(q, fixed), best.x[:n0], bounds=(lo[:n0], hi[:n0]), x_scale="jac", max_nfev=100, **LOSS)
G = f.curves(r2.x); gain = int(round(r2.x[3 * KN] / f.SAT_PER_GAIN)); sat = gain * f.SAT_PER_GAIN

def score(Rf):
    d = de(lab(Rf(us)), tl); dh = de(lab(Rf(uh)), tlh); dm = de(lab(Rf(um)), tlm)
    return f"GRKit gray {d[kind == 0].mean():.2f} ColorChecker {d[kind == 1].mean():.2f} random {d[kind == 2].mean():.2f} | hold-out {dh.mean():.2f} (p95 {np.percentile(dh, 95):.2f}) | mock natural {dm.mean():.2f} (p95 {np.percentile(dm, 95):.2f})"
lines = [f"Target {os.path.basename(a.lut)}, slot {a.slot}; predicted ΔE2000 (model only):",
         "  this fit:             " + score(lambda u: f.R(u, G, sat, S, H, Pq)),
         "  stock Natural:        " + score(lambda u: render(u @ M5300.T)),
         "  Portra xp9 settings:  " + score(lambda u: f.R(u, z9["G"], float(z9["sat"]), z9["S"], z9["H"], z9["P"])),
         f"  gain {gain}; S {S.astype(int).tolist()}; H {H.astype(int).tolist()}; art table x256 {A.tolist()}; camera matrix (EXIF, 5300 K) {(f.renormalise(A) * 2).tolist()}",
         "  curves at 0, 64, 256, 512, 768, 1023: " + "; ".join(f"{n} {G[c][[0, 64, 256, 512, 768, 1023]].round(0).astype(int).tolist()}" for c, n in enumerate("RGB"))]
if AN:
    for tag, pm in (("anchor build, MEASURED", AN["J"]), ("this fit, measured + model change", anchored(G, sat, S, H, Pq))):
        dd = de(lab(pm), AN["tl"]); k_ = AN["k"]
        if V2:
            lines.append(f"  {tag}: GRKit-weighted {np.average(dd[AN['w'] > 0], weights=AN['w'][AN['w'] > 0]):.3f} | grays {dd[k_ == 6].mean():.2f} ColorChecker {dd[k_ == 7].mean():.2f} (p95 {np.percentile(dd[k_ == 7], 95):.2f}) "
                         f"skin {dd[k_ == 8].mean():.2f} natural {dd[k_ == 5].mean():.2f} (p95 {np.percentile(dd[k_ == 5], 95):.2f}) near-neutral {dd[k_ == 3].mean():.2f} dense grays {dd[k_ == 2].mean():.2f}")
        else:
            lines.append(f"  mock patches, {tag}: natural {dd[k_ == 5].mean():.2f} (p95 {np.percentile(dd[k_ == 5], 95):.2f}) near-neutral {dd[k_ == 3].mean():.2f} gray ramp {dd[k_ == 2].mean():.2f}")
    ho = Am["ok"] & (ka == 9) & (Ja.min(1) > 2) & (Ja.max(1) < 253)
    if ho.sum():
        hb = f.R(Am["u"][ho], za["G"], float(za["sat"]), za["S"], za["H"], za["P"]); hp = np.clip(Ja[ho] + f.R(Am["u"][ho], G, sat, S, H, Pq) - hb, 0, 255); ht = tgt(Am["vs"][ho])
        lines.append(f"  hold-out naturals (not in the fit): measured {de(lab(Ja[ho]), ht).mean():.2f} -> predicted {de(lab(hp), ht).mean():.2f}")
sl = SLOTS[a.slot]; ops = []
b0 = fl._b0; B = fl.tone.BASE
if "gamma_tabs" in sl:                       # one table per channel: G_c on the default table stills use (column 0, member 1)
    for ch, t in enumerate(sl["gamma_tabs"]):
        ops.append(fl.op(t, fl.pack(np.interp(fl.table(fl.rec8(fl.DEFAULT_REC)[1]), np.arange(1024), G[ch]))))
else:
    for ch, rec in enumerate(sl["gamma_recs"]):
        for dflt, t in zip(fl.rec8(fl.DEFAULT_REC), fl.rec8(rec)):
            ops.append(fl.op(t, fl.pack(np.interp(fl.table(dflt), np.arange(1024), G[ch]))))
if sl["look"]: ops.append(fl.op(sl["look"], b0[fl.IDENTITY - B:fl.IDENTITY - B + 512]))
ops += [fl.op(sl["sat"], struct.pack("<2H", gain, gain)), fl.op(sl["six_s"], struct.pack("<6h", *S.astype(int))), fl.op(sl["six_h"], struct.pack("<6h", *H.astype(int))),
        fl.op(sl["matrix"], struct.pack("<9h", *A.ravel()))]
if "matrix_expect" in sl: ops[-1]["expect"] = sl["matrix_expect"].hex()
for addr, old, new in sl["repoint"]:
    assert struct.unpack("<I", b0[addr - B:addr - B + 4])[0] == old; ops.append(fl.op(addr, struct.pack("<I", new)))
for addr, old, new in sl["code"]:
    assert b0[addr - B:addr - B + 1] == old; ops.append(fl.op(addr, new))
ops = [o for o in ops if o["expect"] != o["new"]]
json.dump({"name": a.name, "description": f"{os.path.basename(a.lut)} fitted into slot {a.slot} (fit_film.py, NOTES §26). Model-only first fit.", "status": "built, NOT camera-tested",
           "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", "base_sha256": "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", "ops": ops},
          open(f"../../patches/{a.name}.json", "w"), indent=1)
np.savez(f"out/fit_{a.name}.npz", G=G, sat=sat, gain=gain, S=S, H=H, A=A, P=Pq, lut=a.lut)
open(f"out/{a.name}_report.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

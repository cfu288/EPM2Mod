"""Screen the remaining art filters as film-slot candidates (NOTES §31): the test RAW A developed with each
filter's stock look. Spatial effects (blur, vignette, texture) and colour vs the model with the filter's own
stock tables.   ../../.venv/bin/python -I analyze_filters.py"""
import os, re, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
sys.argv = ["x"]
import fit_xp9 as f
from mocklib import *
b0 = fl._b0; B = fl.tone.BASE; u32 = lambda a: struct.unpack("<I", b0[a - B:a - B + 4])[0]
FILTERS = {"soft_focus": 69, "pale_light": 71, "grainy_film": 74, "pin_hole": 73, "diorama": 86, "gentle_sepia": 91, "dramatic_tone": 96, "key_line": 163, "watercolor": 181}
def imm(h, pat): 
    m = re.search(pat + rb"(....)", b0[h - B:h - B + 16], re.S); return struct.unpack("<I", m.group(1))[0] if m else None
def tables(code):
    look = imm(u32(0x7E78C8E4 + 4 * (code - 8)), rb"\xfc\xdc") if 8 <= code <= 184 else None
    sh = u32(0x7E78C514 + 4 * (code - 69)); sat = struct.unpack("<H", b0[imm(sh, rb"\xfc\xdf") - B:][:2])[0] if sh not in (0x7E56DD28, 0x7E56DD26) else 282
    xh = u32(0x7E78C254 + 4 * (code - 9)); S = H = np.zeros(6)
    if xh != 0x7E56D76A:
        a3, a2 = imm(xh, rb"\xfc\xdf"), imm(xh, rb"\xfc\xde")
        if a3 and a2: S = np.array(struct.unpack("<6h", b0[a3 - B:a3 - B + 12]), float); H = np.array(struct.unpack("<6h", b0[a2 - B:a2 - B + 12]), float)
    ch = u32(0x7E78AEA4 + 4 * (code - 69)) if 69 <= code <= 184 else 0x7E56677A
    cc = None
    if ch not in (0x7E56677A, 0x7E566748, 0):
        p = imm(ch, rb"\xfc\xcc"); cc = list(b0[p - B:p - B + 16]) if p else None
    return look, sat, S, H, cc
def ycc(x): return np.stack([x @ LUMA, x @ np.array([-0.168736, -0.331264, 0.5]), x @ np.array([0.5, -0.418688, -0.081312])], 1)
ref = load("A_natural")
for name, code in FILTERS.items():
    if not os.path.exists(f"out/mock/read_A_{name}.npz"):
        subprocess.run([sys.executable, "-I", "read_mock.py", f"shots/stockfilters/A_{name}.JPG"], capture_output=True)
    if not os.path.exists(f"out/mock/read_A_{name}.npz"): print(f"{name}: could not be read (registration failed)"); continue
    d = load(f"A_{name}"); J, k, ok = d["jpg"], d["kind"], np.isfinite(d["jpg"][:, 0]); look, gain, S, H, cc = tables(code)
    pos = d["pos"]; r = np.hypot((pos[:, 1] - 47.5) / 48, (pos[:, 0] - 35.5) / 48)
    white = ok & (k == 0); mid = ok & (k == 4)
    wl = J[white] @ LUMA; slope = np.polyfit(r[white] ** 2, wl, 1)[0] if white.sum() > 5 else np.nan
    print(f"\n== {name} (code {code}); WB {(d['wb'][[0, 2]] * 256).round().astype(int).tolist()}; patches read {ok.sum()}")
    print(f"   spatial: spread inside a patch median {np.nanmedian(d['spread']):.2f} / 99th pct {np.nanpercentile(d['spread'], 99):.1f} codes (Natural: {np.nanmedian(ref['spread']):.2f} / {np.nanpercentile(ref['spread'], 99):.1f});"
          f" identical mid grays range {np.ptp(J[mid] @ LUMA):.1f} codes; white markers centre-to-corner change {slope * (r[white] ** 2).max():+.1f} codes")
    chroma = np.hypot(*ycc(J[ok])[:, 1:].T); print(f"   colour: mean chroma {chroma.mean():.1f} (Natural {np.hypot(*ycc(ref['jpg'][ref['ok']])[:, 1:].T).mean():.1f}); stock tables: look {look and hex(look)}, saturation gain {gain}, six-axis S {S.astype(int).tolist()} H {H.astype(int).tolist()}, chroma curve {cc[:11] if cc else 'default path'}")
    if chroma.mean() < 3: print("   monochrome output: colour model not applicable"); continue
    L = fl.table(look) if look else IDENT
    m = ok & (d["spread"] < 3) & (J.min(1) > 2) & (J.max(1) < 253)
    P = render(d["v"], IDG, gain * f.SAT_PER_GAIN, S, H, None, L, base=np.zeros(6)); dM = de(lab(J), lab(P))
    yj, yp = ycc(J[m]), ycc(P[m]); cp = np.hypot(yp[:, 1], yp[:, 2]); pr = (yj[:, 1] * yp[:, 1] + yj[:, 2] * yp[:, 2]) / np.maximum(cp ** 2, 1e-9)
    print(f"   model with those tables vs camera: natural {dM[m & (k == 5)].mean():.2f}, grays {dM[m & (k == 6)].mean():.2f}, ColorChecker {dM[m & (k == 7)].mean():.2f}  (clean slots: 0.9 / 0.5 / 0.9); usable patches {m.sum()}")
    print("   chroma gain camera/model by chroma:", " ".join(f"{lo}-{hi}:{np.median(pr[(cp >= lo) & (cp < hi)]):.2f}" for lo, hi in ((2, 4), (4, 8), (8, 16), (16, 32), (32, 64)) if ((cp >= lo) & (cp < hi)).sum() > 10),
          f"; luma camera - model median {np.median(yj[:, 0] - yp[:, 0]):+.1f}")

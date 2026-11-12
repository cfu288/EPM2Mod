"""Check the traced tone pipeline against shoot 1 (static trace in NOTES.md §11).

    v    = ColorMatrix · (WB ⊙ raw)                         (EXIF; extract.py / analyze_tone.py)
    base = BASE_GAMMA(k · v)          256 x u16 -> 0..1023  (0x7E74E9BC)
    out  = LOOK(base / 4) / 4         256 x u16 -> 0..1023, then 8-bit
LOOK is the table the selector 0x7E56E837 picks: identity for Natural / Vivid at Contrast 0;
per-mode family + Contrast for the others; one table per art code. k is fitted once, on
the plain Natural shots, and then held fixed for every other setting.

Then, for the settings this does not explain (Cross Process, Pale&Light), the gray row in
BT.601 YCbCr: measured Y vs the look-curve prediction, and the Cb / Cr offsets by brightness
(a split-toning stage).

Usage: ../../.venv/bin/python -I analyze_pipeline.py      -> out/pipeline_report.txt
"""
import importlib.util
import os
import struct

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("tone", os.path.join(HERE, "analyze_tone.py"))
tone = importlib.util.module_from_spec(spec); spec.loader.exec_module(tone)

BASE_GAMMA = 0x7E74E9BC
TWIN = 0x7E74EDBC
IDENTITY = 0x7E75B8F0
# look curve per setting, from the selector 0x7E56E837 (NOTES.md §11)
LOOK = {
    "Natural": (["B1", "B2", "B3", "B4", "B5", "X-base2", "D1-base", "B0a", "B0b", "B0c", "X-base3"], IDENTITY),
    "Vivid": (["M1-vivid"], IDENTITY),
    "Muted": (["M2-muted"], 0x7E75D0F0),            # family table at Contrast offset -1
    "Portrait": (["M3-portrait"], 0x7E75DAF0),
    "High Key": (["G1-highkey"], 0x7E75E0F0),
    "Low Key": (["G2-lowkey"], 0x7E75E2F0),
    "Natural Contrast -2": (["N1-con-2", "N1b-con-2"], 0x7E75CEF0),
    "Natural Contrast +2": (["N2-con+2"], 0x7E75D4F0),
    "Portrait Contrast -2": (["P1-con-2"], 0x7E75D6F0),
    "Portrait Contrast +2": (["P2-con+2"], 0x7E75DEF0),
    "Pop Art I": (["A1-popart"], 0x7E75E6F0),
    "Light Tone": (["A3-lighttone"], 0x7E75EAF0),
    "Pale&Light I": (["A2-palelight"], 0x7E75E8F0),
    "Cross Process I": (["A4-crossprocess"], 0x7E75F2F0),
}


def curve(b0, a):
    return np.array(struct.unpack("<256H", b0[a - tone.BASE:a - tone.BASE + 512]), float)


def model(B, L, k, V):
    base = np.interp(k * V, np.arange(256), B)
    return np.interp(base / 4.0, np.arange(256), L) / 4.0


def ycc(x):
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    return (0.299 * r + 0.587 * g + 0.114 * b, -0.168736 * r - 0.331264 * g + 0.5 * b,
            0.5 * r - 0.418688 * g - 0.081312 * b)


def main():
    d, st, meta = tone.load()
    roles = [str(r) for r in d["roles"]]
    rows = np.array([m["row"] for m in meta])
    b0 = open(tone.BLOCK0, "rb").read()
    lines = []

    def pts(rs):
        return tone.collect(d, st, meta, [roles.index(r) for r in rs])

    ks = np.exp(np.linspace(np.log(0.03), np.log(0.15), 600))
    V, J = pts(LOOK["Natural"][0])
    kb = {}
    for a in (BASE_GAMMA, TWIN):
        B = curve(b0, a)
        e = [np.sqrt(np.mean((model(B, curve(b0, IDENTITY), k, V) - J) ** 2)) for k in ks]
        i = int(np.argmin(e)); kb[a] = ks[i]
        lines.append(f"base {a:#x}: Natural rms {e[i]:.2f} codes at k = {ks[i]:.4f}")
    lines.append("\nk fixed from Natural; rms per channel R G B (codes):")
    for name, (rs, La) in LOOK.items():
        V, J = pts(rs)
        cells = []
        for a in (BASE_GAMMA, TWIN):
            P = model(curve(b0, a), curve(b0, La), kb[a], V)
            cells.append(" ".join(f"{np.sqrt(np.mean((P[:, c] - J[:, c]) ** 2)):5.1f}" for c in range(3)))
        lines.append(f"  {name:22s} n={len(V):3d} look {La:#x}  base {BASE_GAMMA:#x}: {cells[0]}   twin: {cells[1]}")

    B, k = curve(b0, BASE_GAMMA), kb[BASE_GAMMA]
    for name in ("Natural", "Pale&Light I", "Cross Process I"):
        rs, La = LOOK[name]
        role = rs[2] if name == "Natural" else rs[0]
        kk = roles.index(role)
        v = tone.precurve(d, st, kk)
        ok = (~d["rawclip"][kk]) & (~tone.BAD[kk]) & (d["jpgspread"][kk] < 20) & (rows == 6)
        P = model(B, curve(b0, La), k, v[ok]); Jm = d["jpg"][kk][ok]
        yp, cbp, crp = ycc(P); yj, cbj, crj = ycc(Jm)
        lines.append(f"\n{name} ({role}) gray row: Y predicted -> measured; Cb, Cr measured (predicted)")
        o = np.argsort(yp)
        for i in o[::max(1, len(o) // 12)]:
            lines.append(f"   Y {yp[i]:6.1f} -> {yj[i]:6.1f}   Cb {cbj[i]:+6.1f} ({cbp[i]:+5.1f})   Cr {crj[i]:+6.1f} ({crp[i]:+5.1f})")
    open(os.path.join(HERE, "out", "pipeline_report.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

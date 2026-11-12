"""Step 16.2: what do the two six-value records (0x7E56D1C3) do?  Measured chroma gain and hue rotation by hue.

Model B (analyze_lumalook.py) with the setting's saturation gain predicts each patch's (Cb, Cr) before the
six-axis stage; the JPEG gives it after. Per 15-degree bin of the predicted BT.601 hue angle atan2(Cr, Cb):
chroma ratio and hue rotation, relative to Natural (whose records are zero).
Usage: ../../.venv/bin/python -I analyze_sixaxis.py   -> out/sixaxis_profiles.npz, prints the profiles
"""
import importlib.util, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.argv = [sys.argv[0]]
def imp(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(HERE, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
fl = imp("fit_look"); tone = fl.tone
d, st, meta = tone.load(); roles = [str(r) for r in d["roles"]]; rows = np.array([m["row"] for m in meta])
X = np.arange(256); K = fl.K; T = fl.table; E = 0x7E74E9BC; W = np.array([0.299, 0.587, 0.114]); S0 = 1.08
SET = {  # role: (bases, look, saturation gain, sat record, hue record)  records relative to Natural's same variant
 "Natural": ("B3", (E,)*3, fl.IDENTITY, 282, (0,0,0,0,0,0), (0,0,0,0,0,0)),
 "Vivid": ("M1-vivid", (E,)*3, fl.IDENTITY, 310, (18,4,24,0,8,8), (0,2,4,-1,-6,0)),
 "Muted": ("M2-muted", (E,)*3, 0x7E75D0F0, 282, (-22,4,-16,0,4,-8), (3,0,-3,7,8,10)),
 "Portrait": ("M3-portrait", (E,)*3, 0x7E75DAF0, 282, (14,0,0,5,0,0), (-1,0,2,-2,0,0)),
 "Pop Art I": ("A1-popart", (E,)*3, 0x7E75E6F0, 384, (53,79,100,56,-1,48), (2,3,10,0,22,-10)),
 "Light Tone": ("A3-lighttone", (0x7E74F5BC,)*3, 0x7E75EAF0, 281, (0,11,0,0,0,3), (-2,3,0,0,0,-5)),
 "Natural Sat+2": ("N4-sat+2", (E,)*3, fl.IDENTITY, 338, (0,)*6, (0,)*6),
 "Natural Sat-2": ("N3-sat-2", (E,)*3, fl.IDENTITY, 226, (0,)*6, (0,)*6),
}
def cbcr(x):
    return np.stack([-0.168736*x[:,0]-0.331264*x[:,1]+0.5*x[:,2], 0.5*x[:,0]-0.418688*x[:,1]-0.081312*x[:,2]], 1)
def measure(name):
    role, bs, lk, gain, _, _ = SET[name]
    k = roles.index(role); v = tone.precurve(d, st, k); j = d["jpg"][k]
    ok = (~d["rawclip"][k]) & (~tone.BAD[k]) & (d["jpgspread"][k] < 20) & (rows < 6) & (j.min(1) > 6) & (j.max(1) < 248)
    b = np.stack([np.interp(K*np.maximum(v[:,c],0), X, T(bs[c])) for c in range(3)], 1)/4.0
    p = cbcr(b) * S0 * gain / 282.0; m = cbcr(j)
    keep = ok & (np.hypot(*p.T) > 8)
    return p[keep], m[keep]
def profile(name, nb=24):
    p, m = measure(name)
    hp = np.degrees(np.arctan2(p[:,1], p[:,0])) % 360
    ratio = np.hypot(*m.T)/np.hypot(*p.T); rot = (np.degrees(np.arctan2(m[:,1], m[:,0])) - hp + 180) % 360 - 180
    bins = (hp // (360/nb)).astype(int)
    R = np.array([np.median(ratio[bins==i]) if (bins==i).sum() >= 2 else np.nan for i in range(nb)])
    H = np.array([np.median(rot[bins==i]) if (bins==i).sum() >= 2 else np.nan for i in range(nb)])
    return R, H
if __name__ == "__main__":
    np.set_printoptions(linewidth=250, precision=2, suppress=True)
    R0, H0 = profile("Natural"); out = {}
    print("hue bin centres (deg, atan2(Cr,Cb)):", (np.arange(24)*15+7.5))
    print("Natural  ratio", R0); print("Natural  rot  ", H0)
    for n in SET:
        if n == "Natural": continue
        R, H = profile(n); out[n] = (R/R0, H-H0)
        print(f"\n{n}: sat rec {SET[n][4]} hue rec {SET[n][5]}"); print("  ratio/Nat", R/R0); print("  rot-Nat  ", H-H0)
    np.savez(os.path.join(HERE, "out", "sixaxis_profiles.npz"), **{k.replace(" ", "_")+"_ratio": v[0] for k, v in out.items()},
             **{k.replace(" ", "_")+"_rot": v[1] for k, v in out.items()})

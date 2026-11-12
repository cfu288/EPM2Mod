"""Write one fitted film into the generic slots of a layout, without fitting (NOTES §38).
   python3 -I slots/fill_slots.py out/fit_film-portra-xp10.npz slots/remap7_layout.json check-portra-in-new-slots"""
import json, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", ".."); B = 0x7E421020
b0 = open(os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"), "rb").read()
fit, layout, name = sys.argv[1:4]
z = np.load(fit); L = json.load(open(layout))["slots"]
tab = lambda a: np.array(struct.unpack("<256H", b0[a - B:a - B + 512]), float)
pack = lambda c: struct.pack("<256H", *np.clip(np.round(np.maximum.accumulate(c)), 0, 1023).astype(int))
base = tab(0x7E74E9BC); ident = struct.pack("<9h", 256, 0, 0, 0, 256, 0, 0, 0, 256); ops = []
def op(a, new, expect=None): return {"type": "bytes", "block": 0, "offset": hex(a - B), "expect": (expect if expect is not None else b0[a - B:a - B + len(new)]).hex(), "new": bytes(new).hex()}
for n, s in L.items():
    for ch, t in enumerate(s["tabs"]): ops.append(op(int(t, 16), pack(np.interp(base, np.arange(1024), z["G"][ch]))))
    ops += [op(int(s["sat"], 16), struct.pack("<2H", int(z["gain"]), int(z["gain"]))), op(int(s["six"][0], 16), struct.pack("<6h", *z["S"].astype(int))),
            op(int(s["six"][1], 16), struct.pack("<6h", *z["H"].astype(int))), op(int(s["matrix"], 16), struct.pack("<9h", *z["A"].astype(int).ravel()), ident)]
json.dump(dict(name=name, description=f"Test content: the fit {os.path.basename(fit)} written into every generic slot of {os.path.basename(layout)} ({', '.join(L)}). NOTES §38.", status="built, NOT camera-tested",
               base="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", base_sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", ops=[o for o in ops if o["expect"] != o["new"]]),
          open(os.path.join(ROOT, f"patches/{name}.json"), "w"), indent=1)
print(name, len(ops), "ops; slots", list(L))

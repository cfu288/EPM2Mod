"""Seven films in menu order (NOTES §39). Writes
  patches/seven-structure-extra.json   what the three old film patches used to carry besides the look itself
  patches/seven-films-<tag>.json       one fitted film per slot
  patches/seven-labels.json            menu labels (exact strings only)
Build: remap7b-code + slot3-chroma-linear + xp-adaptive-hue-off + the three above.
Slot = menu entry; films are assigned top to bottom in the order they were added (the seven slots are
equivalent: NOTES §38.1).      ../../.venv/bin/python -I slots/build_seven_films.py <tag>"""
import json, os, re, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); ROOT = os.path.join(HERE, "..", "..", ".."); B = 0x7E421020
b0 = open(os.path.join(ROOT, "build/blocks/OLY_E_101_1600_0000_0000.BIN.block0.bin"), "rb").read()
tag = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: build_seven_films.py <tag>   (a key of FITS: the set of fits to build)")
R7 = json.load(open(os.path.join(HERE, "remap7_layout.json")))["slots"]
u32 = lambda a: struct.unpack_from("<I", b0, a - B)[0]
rec8 = lambda r: list(struct.unpack_from("<8I", b0, r - B))
DEF = rec8(0x7E78B39C)
def op(a, new, expect=None, block=0): return {"type": "bytes", "block": block, "offset": hex(a - B if block == 0 else a), "expect": (expect if expect is not None else b0[a - B:a - B + len(new)]).hex(), "new": bytes(new).hex()}
tab = lambda a: np.array(struct.unpack("<256H", b0[a - B:a - B + 512]), float)
pack = lambda c: struct.pack("<256H", *np.clip(np.round(np.maximum.accumulate(c)), 0, 1023).astype(int))
IDENT_M = struct.pack("<9h", 256, 0, 0, 0, 256, 0, 0, 0, 256)
g = lambda n: dict(tables=[(int(t, 16), DEF[1]) for t in R7[n]["tabs"]], sat=int(R7[n]["sat"], 16), six=[int(x, 16) for x in R7[n]["six"]], matrix=int(R7[n]["matrix"], 16), m_expect=IDENT_M)
full = lambda recs: [(t, d) for r in recs for t, d in zip(rec8(r), DEF)]            # 24 tables, each on its own default variant
# slot (menu entry, top to bottom): where a film's numbers go.  tables = [(address, default table it is composed with)] in R, G, B order
SLOTS = {
    "Pop Art":          dict(tables=[(0x7E74F1BC, DEF[1]), (0x7E74F5BC, DEF[1]), (0x7E7505BC, DEF[1])], sat=0x7E7696A0, six=[0x7E769486, 0x7E769492], matrix=0x7E880FC2, m_expect=IDENT_M, per_ch=1),
    "Soft Focus":       dict(per_ch=1, **g("softfocus")),
    "Pale&Light Color": dict(per_ch=1, **g("palelight1")),
    "Light Tone":       dict(tables=full((0x7E78B49C, 0x7E78B4BC, 0x7E78B4DC)), sat=0x7E7696A8, six=[0x7E7694B6, 0x7E7694C2], matrix=0x7E768F58, m_expect=None, per_ch=8),
    "Pin Hole":         dict(per_ch=1, **g("pinhole")),
    "Diorama":          dict(per_ch=1, **g("diorama")),
    "Cross Process":    dict(tables=full((0x7E78B41C, 0x7E78B43C, 0x7E78B45C)), sat=0x7E7696B4, six=[0x7E7694FE, 0x7E76950A], matrix=0x7E768F46, m_expect=None, per_ch=8),
}
CHROMA = {"Pop Art": 0x7E74B8BA, "Soft Focus": 0x7E74BBCA, "Pale&Light Color": 0x7E74B91C, "Light Tone": 0x7E74B97E, "Pin Hole": 0x7E74BB68, "Diorama": 0x7E74BE16, "Cross Process": 0x7E74BAA4}   # 97-byte chroma-curve record of the slot's stills code (needs seven-fixes-1)
WITH_CHROMA = ("3", "4", "5")                       # tags whose build has seven-fixes-1 instead of slot3-chroma-linear: every slot's chroma record is written
# film per slot: (fit file, label). Labels are at most as long as the entry's stock name.
LABELS = {"Pop Art": "Portra", "Soft Focus": "Ektachrome", "Pale&Light Color": "Pro 400H", "Light Tone": "Kodachrome", "Pin Hole": "Vis 250D", "Diorama": "Velvia", "Cross Process": "Superia 400"}
_OLD3 = {"Pop Art": "film-portra-xp10", "Soft Focus": "film-ektachrome-lt3", "Pale&Light Color": "film-pro400h-pa2"}
FITS = {   # tag -> fit file per slot (out/fit_<name>.npz)
    "1": dict(_OLD3, **{"Light Tone": "cand-kodak_kodachrome_64_scanfilm", "Pin Hole": "cand-vision3250d_2383", "Diorama": "cand-fujifilm_velvia_100_scanfilm", "Cross Process": "cand-xtra400_crystalarchive"}),   # model-only first fits (NOTES 39)
    "2": dict(_OLD3, **{"Light Tone": "film-kodachrome64-2", "Pin Hole": "film-vision3250d-2", "Diorama": "film-velvia100-2", "Cross Process": "film-superia400-2"}),                                            # corrected against build 1 (NOTES 40)
    "3": {"Pop Art": "film-portra-c1", "Soft Focus": "film-ektachrome-c1", "Pale&Light Color": "film-pro400h-c1", "Light Tone": "film-kodachrome64-c1", "Pin Hole": "film-vision3250d-c1", "Diorama": "film-velvia100-c1", "Cross Process": "film-superia400-c1"},   # refit with chroma curves (NOTES 43)
    "4": {"Pop Art": "film-portra-c2", "Soft Focus": "film-ektachrome-c2", "Pale&Light Color": "film-pro400h-c2", "Light Tone": "film-kodachrome64-c2", "Pin Hole": "film-vision3250d-c2", "Diorama": "film-velvia100-c2", "Cross Process": "film-superia400-c2"},   # corrected against build 3 (NOTES 44)
    "5": {"Pop Art": "film-portra-m1", "Soft Focus": "film-ektachrome-m1", "Pale&Light Color": "film-pro400h-m1", "Light Tone": "film-kodachrome64-m1", "Pin Hole": "film-vision3250d-m1", "Diorama": "film-velvia100-m1", "Cross Process": "film-superia400-m1"},   # refit with the second model, gamut-edge colours at weight 0.25 (NOTES 45)
}
if tag not in FITS: sys.exit(f"unknown tag {tag!r}; add it to FITS")
FILMS = {slot: (f"out/fit_{FITS[tag][slot]}.npz", LABELS[slot]) for slot in SLOTS}
base = dict(base="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN", base_sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300", status="built, NOT camera-tested")
ATTRIB = "Film look data derived from spektrafilm by Andrea Volpato, https://github.com/andreavolpato/spektrafilm. Licensed CC BY-SA 4.0. Modified: fitted to the Olympus E-PM2's adjustable stages. See NOTICE.md."
ident_look = b0[0x7E75B8F0 - B:0x7E75B8F0 - B + 512]
extra = [op(a, ident_look) for a in (0x7E75F2F0, 0x7E75EAF0, 0x7E75E6F0)]                          # look tables of Cross Process I (shared by the generic slots), Light Tone, Pop Art I := the stock "identity" table
extra += [op(0x7E78C154 + 8 * i + 4, struct.pack("<I", 0x7E56B82A)) for i in (2, 11)]             # Light Tone 72 / 81 -> the three-record handler of Cross Process II
json.dump(dict(name="seven-structure-extra", description="Structure the three first film patches carried besides their look: stock identity look table for Cross Process I, Light Tone and Pop Art I; "
               "Light Tone's gamma hash entries. For builds with remap7b-code that take their films from seven-films-*.json. NOTES §39.", ops=[o for o in extra if o["expect"] != o["new"]], **base),
          open(os.path.join(ROOT, "patches/seven-structure-extra.json"), "w"), indent=1)
ops = []; summary = {}
for slot, (fit, label) in FILMS.items():
    z = np.load(os.path.join(HERE, "..", fit)); s = SLOTS[slot]; n = len(s["tables"]) // 3
    for i, (t, d) in enumerate(s["tables"]): ops.append(op(t, pack(np.interp(tab(d), np.arange(1024), z["G"][i // n]))))
    gain = int(z["gain"])
    ops += [op(s["sat"], struct.pack("<2H", gain, gain)), op(s["six"][0], struct.pack("<6h", *z["S"].astype(int))), op(s["six"][1], struct.pack("<6h", *z["H"].astype(int))),
            op(s["matrix"], struct.pack("<9h", *z["A"].astype(int).ravel()), s["m_expect"])]
    if tag in WITH_CHROMA:
        import chroma
        lin = chroma.quantise(chroma.LINEAR_Y); cb, cr = ((tuple(z["Cb"][:2].astype(int)) + (z["Cb_slope17"].astype(int),)), (tuple(z["Cr"][:2].astype(int)) + (z["Cr_slope17"].astype(int),))) if "Cb" in z.files else (lin, lin)
        ops.append(op(CHROMA[slot], chroma.record(cb, cr)))
    summary[slot] = dict(fit=fit, label=label, gain=gain, S=z["S"].astype(int).tolist(), H=z["H"].astype(int).tolist(), A=z["A"].astype(int).tolist())
json.dump(dict(name=f"seven-films-{tag}", attribution=ATTRIB, description="Seven films, one per film slot, in menu order: " + "; ".join(f"{k} = {os.path.basename(v[0])[9:-4]}" for k, v in FILMS.items()) + ". NOTES §39.",
               ops=[o for o in ops if o["expect"] != o["new"]], **base), open(os.path.join(ROOT, f"patches/seven-films-{tag}.json"), "w"), indent=1)
json.dump(summary, open(os.path.join(HERE, f"seven_films_{tag}.json"), "w"), indent=1)
# labels: only the entry's own string (preceded by NUL or by an '@Axxx@' tag, followed by NUL), not longer strings that contain it
sys.path.insert(0, os.path.join(ROOT, "tools")); import oetool
blocks, _ = oetool.parse(open(os.path.join(ROOT, base["base"]), "rb").read()); b1 = blocks[1]["payload"]            # block 1 of the same stock image the patch is based on
lops = []; counts = {}
for slot, (fit, label) in FILMS.items():
    assert len(label) <= len(slot), (slot, label)
    old = slot.encode("utf-16-le"); new = (label + "\0" * (len(slot) - len(label))).encode("utf-16-le"); k = 0
    for m in re.finditer(re.escape(old), b1):
        i = m.start()
        if i % 2 or b1[m.end():m.end() + 2] != b"\0\0" or b1[i - 2:i] not in (b"\0\0", "@".encode("utf-16-le")): continue
        lops.append({"type": "bytes", "block": 1, "offset": hex(i), "expect": old.hex(), "new": new.hex()}); k += 1
    counts[slot] = k
json.dump(dict(name="seven-labels", description="Menu labels of the seven film slots (replaces label-portra, label-ektachrome-lt, label-pro400h-pa): " + ", ".join(f"'{k}' -> '{v[1]}'" for k, v in FILMS.items())
               + ". Only the entry's own strings; longer strings containing the name (e.g. 'Add Soft Focus Effect') are left alone.", ops=lops, **base), open(os.path.join(ROOT, "patches/seven-labels.json"), "w"), indent=1)
print("film ops", len(ops), "; label strings changed per entry", counts)

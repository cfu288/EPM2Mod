"""The calibration run (NOTES.md): its 12-region tables, 24 calibration films, four film files and the test build.
Research code.

    OMP_NUM_THREADS=2 uv run --with colour-science python experiments/2026-11-20-model-calibration/scripts/design.py
    -> tables/*.bin, films/*.npz, films/list-<n>.json, build/calib/EPM2LOOK-<n>.BIN,
       data/specs/calib-probe.json, data/builds/calib-probe.json

ART 1-6 carry test tables (data edits through mkspec.make, as twelve-region-probe); ART 7-12 keep the default path
(Natural's table A, as every film today). In each film file ART 1-6 hold one film (file 1 the transparent "clear"
film of the probe, files 2-4 Portra 400, Velvia 100, Ektachrome), ART 7-12 six calibration films.
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(EXP, "..", ".."))
TWELVE = os.path.join(ROOT, "experiments", "2026-11-20-twelve-region", "scripts")
FP = os.path.join(ROOT, "experiments", "2026-11-09-film-portra")
sys.path[:0] = [TWELVE, FP]
argv = sys.argv; sys.argv = ["x"]
import tables as T  # noqa: E402
import simulate  # noqa: E402
import mkspec  # noqa: E402
_cwd = os.getcwd(); os.chdir(FP)
import fit_xp9 as f  # noqa: E402  (reads its calibration relative to its folder)
os.chdir(_cwd)

ENTRIES = ["Pop Art", "Soft Focus", "Pale&Light Color", "Light Tone", "Grainy Film", "Pin Hole", "Diorama",
           "Cross Process", "Gentle Sepia", "Dramatic Tone", "Key Line", "Watercolor"]
CODES = [79, 75, 71, 72, 94, 92, 125, 85, 98, 144, 156, 159]
CAT = {x["id"]: x for x in json.load(open(os.path.join(ROOT, "data", "films", "catalogue.json")))["films"]}
FITTED = os.path.join(ROOT, "experiments", "2026-11-20-twelve-region", "out", "twelve")

# ART n -> (case of the worker whose table is replaced, table name); None = default path (table A)
TABLE_OF = {1: ("CTRL", "off"), 2: (None, "natural-a"), 3: ("HUEMAP", "portra-400"), 4: ("MAGL", "velvia"),
            5: ("MAGS", "ektachrome"), 6: ("MAGH", "natural-a-flat")}
LABEL = {"off": "Q OFF", "natural-a": "Q NAT A", "portra-400": "Q PORTRA", "velvia": "Q VELVIA",
         "ektachrome": "Q EKTA", "natural-a-flat": "Q NAT FLAT"}
FILE_FILM = {1: "clear", 2: "portra-400", 3: "velvia", 4: "ektachrome"}


def flat(table):
    """The same records, windows and effects with every curve flat at the top level: separates the curve shapes."""
    d = T.decode(table)
    recs = []
    for r in d["recs"]:
        (hs, hw), (cs, cw), (ys, yw) = r["win"].tolist()
        ms = {ax: tuple(int(x) for x in r["ms"][i]) for i, ax in enumerate(("hue", "chroma", "luma"))}
        recs.append(T.Rec(hue=(hs, hw), chroma=(cs, cw), luma=(ys, yw), dh=r["eff"][0], ds=r["eff"][1], dl=r["eff"][2],
                          msov=ms))
    out = T.encode(recs, d["mask"])
    ref = T.decode(out)
    for a, b in zip(d["recs"], ref["recs"]):
        assert (a["win"] == b["win"]).all() and (a["eff"] == b["eff"]).all() and (a["ms"] == b["ms"]).all()
    return out


def tables():
    t = {"off": T.encode([None] * 12, 0), "natural-a": simulate.TABLE_A, "natural-a-flat": flat(simulate.TABLE_A)}
    for fid in ("portra-400", "velvia", "ektachrome"):
        t[fid] = open(os.path.join(FITTED, f"{fid}.bin"), "rb").read()
    for v in t.values():
        assert len(v) == T.TABLE_BYTES
    return t


def fit_of(fid):
    return dict(np.load(os.path.join(ROOT, CAT[fid]["fit"])))


def clear():
    return dict(np.load(os.path.join(ROOT, "experiments", "2026-11-20-twelve-region", "out", "films", "clear.npz")))


def calibration_films(rng):
    """24 films: 8 mixes of the catalogue's colour fits (curves per channel from different films), 8 with six-axis
    values across the fit's bounds, 4 gains across and past the fitted range, 4 strong art matrices."""
    ids = [k for k, v in CAT.items() if k != "double-x"]
    keys = ("G", "gain", "S", "H", "A", "Cb", "Cr", "Cb_slope17", "Cr_slope17")
    base = {k: v for k, v in fit_of("portra-400").items() if k in keys}
    out = []
    for i in range(8):
        a, b, c, d, e = (fit_of(x) for x in rng.choice(ids, 5, replace=False))
        G = np.stack([fit_of(x)["G"][ch] for ch, x in enumerate(rng.choice(ids, 3, replace=False))])
        out.append((f"mix {i + 1}", dict(G=G, gain=b["gain"], S=c["S"], H=c["H"], A=d["A"], Cb=e["Cb"], Cr=e["Cr"],
                                         Cb_slope17=e["Cb_slope17"], Cr_slope17=e["Cr_slope17"])))
    for i in range(8):
        S = np.round(rng.uniform(-40, 40, 6)); H = np.round(rng.uniform(-20, 20, 6)); H[0] = 0
        out.append((f"six-axis {i + 1}", dict(base, S=S, H=H)))
    for g in (160, 230, 345, 420):
        out.append((f"gain {g}", dict(base, gain=np.array(g))))
    for i in range(4):
        off = rng.uniform(-48, 48, (3, 3)); np.fill_diagonal(off, 0)
        A = np.round(off).astype(np.int64); np.fill_diagonal(A, 256 - A.sum(1))
        out.append((f"matrix {i + 1}", dict(base, A=A)))
    for _, z in out:
        z["P"] = f.renormalise(np.asarray(z["A"])) / 128.0
        z["gain"] = np.array(int(z["gain"]))
        z["model"] = np.array("model2")
    return out


def main():
    os.chdir(ROOT)
    tb = tables()
    os.makedirs(os.path.join(EXP, "tables"), exist_ok=True)
    for k, v in tb.items():
        open(os.path.join(EXP, "tables", f"{k}.bin"), "wb").write(v)
    fd = os.path.join(EXP, "films"); os.makedirs(fd, exist_ok=True)
    cal = calibration_films(np.random.default_rng(20261120))
    meta = []
    for i, (what, z) in enumerate(cal):
        np.savez(os.path.join(fd, f"k{i + 1:02d}.npz"), **z)
        meta.append({"name": f"K{i + 1:02d}", "what": what, "gain": int(z["gain"]), "S": np.asarray(z["S"]).astype(int).tolist(),
                     "H": np.asarray(z["H"]).astype(int).tolist(), "A": np.asarray(z["A"]).astype(int).tolist()})
    np.savez(os.path.join(fd, "clear.npz"), **clear())
    out_dir = os.path.join(ROOT, "build", "calib")
    os.makedirs(out_dir, exist_ok=True)
    for n in (1, 2, 3, 4):
        film = FILE_FILM[n]
        test_fit = os.path.join(fd, "clear.npz") if film == "clear" else os.path.join(ROOT, CAT[film]["fit"])
        looks = [{"entry": ENTRIES[a - 1], "name": LABEL[TABLE_OF[a][1]], "fit": os.path.relpath(test_fit, ROOT)} for a in range(1, 7)]
        for j in range(6):
            k = 6 * (n - 1) + j
            looks.append({"entry": ENTRIES[6 + j], "name": f"K{k + 1:02d}", "fit": os.path.relpath(os.path.join(fd, f"k{k + 1:02d}.npz"), ROOT)})
        lst = os.path.join(fd, f"list-{n}.json")
        json.dump({"looks": looks}, open(lst, "w"), indent=1)
        subprocess.run(["uv", "run", "epm2mod", "films", "pack", os.path.relpath(lst, ROOT), "-o",
                        os.path.relpath(os.path.join(out_dir, f"EPM2LOOK-{n}.BIN"), ROOT)], check=True)
    json.dump({"tables": {f"ART {a}": TABLE_OF[a][1] for a in TABLE_OF}, "files": FILE_FILM, "calibration": meta},
              open(os.path.join(fd, "design.json"), "w"), indent=1)
    entries = [(a, ENTRIES[a - 1], CODES[a - 1], TABLE_OF[a][0] if a in TABLE_OF else None) for a in range(1, 13)]
    used = {TABLE_OF[a][0]: (tb[TABLE_OF[a][1]], tb[TABLE_OF[a][1]], TABLE_OF[a][1]) for a in TABLE_OF if TABLE_OF[a][0]}
    mkspec.make(entries, used, False, "data/specs/calib-probe.json", "data/builds/calib-probe.json", "calib-probe",
                "TEST ONLY. Camera calibration of the colour model: ART 1-6's film codes get 12-region test tables "
                "through the hash 0x7E78C6E4 (empty slots only), written over the stock tables of the descriptors that "
                "the chosen cases return (scene modes and stock filters that share those cases use them in this "
                "build): ART 1 all records off, ART 3-5 the fitted tables of Portra 400, Velvia 100 and Ektachrome, "
                "ART 6 Natural's table A with flat curves; ART 2 and 7-12 keep the default (table A). Data edits "
                "only, no code. Needs films-look-exif-artbkt before it. See "
                "experiments/2026-11-20-model-calibration/NOTES.md.",
                "TEST ONLY, not for use: films-look-exif-artbkt with 12-region test tables in ART 1, 3, 4, 5 and 6. "
                "For the one calibration run of experiments/2026-11-20-model-calibration/NOTES.md; go back to "
                "films-look-exif after it")
    return entries, used


if __name__ == "__main__":
    main()

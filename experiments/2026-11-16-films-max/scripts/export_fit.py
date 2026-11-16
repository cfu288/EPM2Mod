"""Copy model-only fits to looks/fits/ and check them the way the patch generator reads them.

The seven installed files are byte copies of out/fit_film-NAME-m1.npz; this does the same with out/fit_film-NAME-n1.npz,
(or -n2, the pass that fit_table.py marks chosen),
after these checks: same keys, dtypes and shapes as looks/fits/velvia100.npz; the 'lut' field is a relative path
(no machine path); the file loads with epm2mod.looks.generate.load_fit; chroma_record() gives 97 bytes; gain, S, H, A
pass whole_numbers() with the ranges film_ops() uses; the curves are finite and inside 0..1023.
Run from the top of the repository:
   .venv/bin/python experiments/2026-11-16-films-max/scripts/export_fit.py [--check-only] NAME[=SOURCE] ...
NAME is the file name in looks/fits/ (ektar100); SOURCE is the fit in out/ if it is not NAME-n1 (gold200=gold200ca-n2).
"""
import shutil, sys
from pathlib import Path
import numpy as np
from epm2mod.looks import generate as g

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "experiments" / "2026-11-09-film-portra" / "out"
FITS = ROOT / "looks" / "fits"

def check(path: Path, ref: dict) -> list[str]:
    bad = []; fit = g.load_fit(path); where = path.name
    if list(fit) != list(ref): bad.append(f"keys {list(fit)}")
    for key in ref:
        if key not in fit: continue
        if fit[key].dtype.kind != ref[key].dtype.kind or (key != "lut" and fit[key].dtype != ref[key].dtype) or fit[key].shape != ref[key].shape:
            bad.append(f"'{key}' is {fit[key].dtype} {fit[key].shape}, reference {ref[key].dtype} {ref[key].shape}")
    lut = str(fit["lut"])
    if lut.startswith(("/", "~")) or ":" in lut or ".." in lut or not lut.startswith("out/lut/"): bad.append(f"'lut' is not a path below out/lut: {lut}")
    if str(fit["model"]) != "model2": bad.append("'model' is not model2")
    try:
        if len(g.chroma_record(fit, where)) != 97: bad.append("chroma record is not 97 bytes")
        u16, i16 = (0, 0xFFFF), (-0x8000, 0x7FFF)
        g.whole_numbers(fit["gain"], 1, *u16, "'gain'", where); g.whole_numbers(fit["S"], 6, *i16, "'S'", where)
        g.whole_numbers(fit["H"], 6, *i16, "'H'", where); g.whole_numbers(fit["A"], 9, *i16, "'A'", where)
    except g.BuildError as error: bad.append(str(error))
    G = fit["G"]
    if not np.all(np.isfinite(G)) or G.min() < 0 or G.max() > 1023: bad.append("curves outside 0..1023")
    return bad

def main(argv: list[str]) -> int:
    only = "--check-only" in argv; names = [a for a in argv if not a.startswith("--")]; failed = 0
    ref = g.load_fit(FITS / "velvia100.npz")
    for item in names:
        name, _, source = item.partition("="); src = OUT / f"fit_film-{source or name + '-n1'}.npz"; dst = FITS / f"{name}.npz"
        if not only:
            bad = check(src, ref)
            if bad: print(f"{name}: NOT exported:", "; ".join(bad)); failed += 1; continue
            if dst.exists() and dst.read_bytes() != src.read_bytes(): print(f"{name}: NOT exported: {dst.name} exists with other content"); failed += 1; continue
            shutil.copyfile(src, dst)
        bad = check(dst, ref); failed += bool(bad)
        print(f"{name}: " + ("; ".join(bad) if bad else f"ok (looks/fits/{dst.name}, lut {str(g.load_fit(dst)['lut'])})"))
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

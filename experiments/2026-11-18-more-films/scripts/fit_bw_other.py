"""fit_bw_colour.py (card-looks experiment) for another black-and-white film: only the target LUT changes.

    python -I experiments/2026-11-18-more-films/scripts/fit_bw_other.py --lut-dir DIR --cube FILE --name NAME

DIR is a folder under experiments/2026-11-09-film-portra/out/lut (a spektrafilm dev bundle with its bundle.json, so
the input gain is read as for Double-X); FILE is the cube in it. The rest of the arguments go to fit_bw_colour.py.
"""
import os, runpy, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
args = sys.argv[1:]
lut_dir = args[args.index("--lut-dir") + 1]; cube = args[args.index("--cube") + 1]
rest = [a for i, a in enumerate(args) if a not in ("--lut-dir", "--cube") and (i == 0 or args[i - 1] not in ("--lut-dir", "--cube"))]
sys.path.insert(0, os.path.join(ROOT, "experiments", "2026-11-16-doublex", "scripts"))
import monolib  # noqa: E402  (changes the working directory to the film experiment)

monolib.LUT_DIR = "out/lut/" + lut_dir
monolib.LUT = monolib.LUT_DIR + "/" + cube
sys.argv = ["fit_bw_colour.py"] + rest
runpy.run_path(os.path.join(ROOT, "experiments", "2026-11-17-card-looks", "scripts", "fit_bw_colour.py"), run_name="__main__")

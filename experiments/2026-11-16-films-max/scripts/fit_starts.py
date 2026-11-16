"""fit_film2.py, unchanged except for the starting points of the optimiser: the fits of installed looks named with
--starts (looks/fits/NAME.npz) replace the two standard starts (neutral, Portra). Reason: the control fit of Velvia
with the standard starts ended in a worse minimum than the installed Velvia fit scored by the model alone.
Run from the film-portra folder:
   ../../.venv/bin/python -I ../2026-11-16-films-max/scripts/fit_starts.py --starts ektachrome,kodachrome64 --lut out/lut/.../x.cube --name film-x-n2 --edge-weight 0.25
"""
import os, sys
i = sys.argv.index("--starts"); EXTRA = sys.argv[i + 1].split(","); del sys.argv[i:i + 2]
src = open("fit_film2.py").read(); mark = "best = None\n"; assert src.count(mark) == 1
src = src.replace(mark, 'starts = {n: start(np.load(f"../../looks/fits/{n}.npz")) for n in EXTRA}\n' + mark)
sys.path.insert(0, os.getcwd())
exec(compile(src, os.path.abspath("fit_film2.py"), "exec"))

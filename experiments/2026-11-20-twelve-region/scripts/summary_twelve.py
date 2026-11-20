"""Summary of the 12-region fits (fit_twelve.py): averages and how many visibly-off patches each table fixes.
Research code.

    OMP_NUM_THREADS=2 uv run --with colour-science python experiments/2026-11-20-twelve-region/scripts/summary_twelve.py
    -> out/twelve/summary.txt

"Visible" = ΔE2000 > 2 against the target. Groups: natural colours, hold-out, ColorChecker x5, skin (kinds 5, 9, 7, 8).
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit_twelve as FT  # noqa: E402

GROUPS = ((5, "natural"), (9, "hold-out"), (7, "ColorChecker"), (8, "skin"))


def main():
    rd = FT.readings()
    lines = ["film               | ColorChecker  natural  skin | visible (>2) patches now -> with table, per group "
             "natural / hold-out / ColorChecker / skin | newly visible"]
    for fid, (tag, fitp) in rd.items():
        path = os.path.join(FT.OUT, f"{fid}.bin")
        if not os.path.exists(path):
            continue
        F = FT.Film(fid, tag, fitp)
        X = F.rules(open(path, "rb").read())
        d0, d1 = FT.de(FT.lab(F.J), F.T), FT.de(FT.lab(X), F.T)
        s0, s1 = F.score(F.J), F.score(X)
        vis, new = [], 0
        for k, _ in GROUPS:
            m = F.ok & (F.kind == k)
            vis.append(f"{(m & (d0 > 2)).sum()}->{(m & (d1 > 2)).sum()}")
            new += (m & (d0 <= 2) & (d1 > 2)).sum()
        lines.append(f"{fid:18s} | {s0['colorchecker']:.2f}->{s1['colorchecker']:.2f} {s0['natural']:.2f}->{s1['natural']:.2f} "
                     f"{s0['skin']:.2f}->{s1['skin']:.2f} | {' / '.join(vis)} | {new}")
        print(lines[-1], flush=True)
    open(os.path.join(FT.OUT, "summary.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

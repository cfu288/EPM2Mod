"""Read the calibration run's JPEGs into patch values. Research code.

    OMP_NUM_THREADS=2 uv run --with colour-science python experiments/2026-11-20-model-calibration/scripts/read_calib.py DIR N
    -> out/readings/f<N>/<role>.npz, out/readings/f<N>/roles.json

DIR holds one film file's 26 JPEGs. By file name: 13 developments of PB200002 (layout "twelve"), then 13 of
PB130001 (layout "mock2a"); each set is the current Picture Mode (Natural), then ART 1-12. Roles: T_PM, T_ART<k>,
A_PM, A_ART<k>. The layout each JPEG registers to is checked against its role.
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(EXP, "..", ".."))
FP = os.path.join(ROOT, "experiments", "2026-11-09-film-portra")
TW = os.path.join(ROOT, "experiments", "2026-11-20-twelve-region", "scripts")
sys.path[:0] = [FP, TW]
import numpy as np  # noqa: E402
import read_mock as rm  # noqa: E402
import chart  # noqa: E402

rm.LAYOUTS["twelve"] = chart.layout_path()


def roles():
    out = []
    for raw in ("T", "A"):
        out += [f"{raw}_PM"] + [f"{raw}_ART{k}" for k in range(1, 13)]
    return out


def main(d, n):
    files = sorted(glob.glob(os.path.join(d, "*.JPG")))
    assert len(files) == 26, f"{d}: {len(files)} JPEGs, the run gives 26"
    od = os.path.join(EXP, "out", "readings", f"f{n}")
    os.makedirs(od, exist_ok=True)
    mp = {}
    for path, role in zip(files, roles()):
        tag = "twelve" if role.startswith("T_") else "mock2a"
        dd, stats, info, _ = rm.read(path, tag=tag)
        assert stats["score"] > 0.5, (path, stats)
        np.savez(os.path.join(od, f"{role}.npz"), **{k: v for k, v in dd.items() if k != "layout"})
        mp[os.path.basename(path)] = role
        print(f"{os.path.basename(path)} {role}: {np.isfinite(dd['jpg'][:, 0]).sum()} patches, score {stats['score']:.2f}, "
              f"ColorMatrix {(dd['M'] * 256).round().astype(int).ravel().tolist()}", flush=True)
    json.dump(mp, open(os.path.join(od, "roles.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))

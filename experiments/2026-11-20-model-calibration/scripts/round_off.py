"""The camera round on films-twelve-off-artbkt (NOTES.md §8): each film with no 12-region table against its target,
and against the same film's confirmation-round reading (Natural's table, films-look-exif). Research code.

    OMP_NUM_THREADS=4 uv run --with colour-science python experiments/2026-11-20-model-calibration/scripts/round_off.py DIR BATCH
    -> out/mock/read_OFF_<film id>.npz in the film-portra experiment, results/round-off-<BATCH>.txt

DIR holds one batch's 13 JPEGs of PB130001 (ART BKT: the current Picture Mode, then ART 1-12). BATCH is A, B or C,
the film file of build/films-confirm/ (its look list: FILMS below; C fills ART 1-8).
"""
import glob, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(EXP, "..", ".."))
FP = os.path.join(ROOT, "experiments", "2026-11-09-film-portra")
sys.path[:0] = [FP, os.path.join(ROOT, "experiments", "2026-11-20-twelve-region", "scripts")]
argv = sys.argv; sys.argv = ["x"]
import read_mock as rm  # noqa: E402
import fit_twelve as FT  # noqa: E402

FILMS = {"A": ["provia", "portra-160", "gold-200", "vision3-500t", "ektar-100", "portra-800", "portra-800-push1",
               "portra-800-push2", "c200", "ultramax-400", "verita-200d", "vision3-50d"],
         "B": ["vision3-200t", "tri-x", "velvia-50", "natura-1600", "pro-160s", "superia-reala", "agfa-vista-100",
               "vericolor-iii", "aerocolor-iv", "eterna-500", "exr-200t", "fp-100c"],
         "C": ["portra-400", "ektachrome", "pro-400h", "kodachrome", "double-x", "vision3-250d", "velvia", "superia-400"]}
CONFIRM = {"A": "CA", "B": "CB", "C": "CC"}


def main(d, batch):
    files = sorted(glob.glob(os.path.join(d, "*.JPG")))
    if len(files) == 26:          # both test RAWs developed: keep the 13 of PB130001 (layout mock2a), by registration
        sets = [files[:13], files[13:]]
        def score_of(path):
            try:
                return rm.read(path, tag="mock2a")[1]["score"]
            except AssertionError:                    # a development of the other RAW does not register at all
                return 0.0
        score = [score_of(s_[1]) for s_ in sets]
        files = sets[int(np.argmax(score))]
    assert len(files) == 13, f"{d}: {len(files)} JPEGs, ART BKT gives 13 per RAW"
    rd = FT.readings()
    lines = [f"batch {batch}: camera on films-twelve-off (no 12-region table) against films-look-exif (Natural's table), "
             "PB130001 against the film's target, ΔE2000 (natural / hold-out / ColorChecker / skin / grays)"]
    f = lambda s: f"{s['natural']:.2f} / {s['holdout']:.2f} / {s['colorchecker']:.2f} / {s['skin']:.2f} / {s['grays']:.2f}"
    for art, fid in enumerate(FILMS[batch], 1):
        if fid == "double-x":
            lines.append(f"  ART {art:2d} {fid:17s} black and white: not scored here"); continue
        path = files[art]                                        # files[0] is the current Picture Mode
        dd, stats, info, _ = rm.read(path, tag="mock2a")
        tag = f"OFF_{fid}"
        np.savez(os.path.join(FP, "out", "mock", f"read_{tag}.npz"), **{k: v for k, v in dd.items() if k != "layout"})
        fit = rd[fid][1]
        now, off = FT.Film(fid, rd[fid][0], fit), FT.Film(fid, tag, fit)
        cm = (dd["M"] * 256).round().astype(int).ravel().tolist()
        lines.append(f"  ART {art:2d} {fid:17s} table A {f(now.score(now.J))}  ->  none {f(off.score(off.J))}   "
                     f"({os.path.basename(path)}, ColorMatrix {cm})")
        print(lines[-1], flush=True)
    os.makedirs(os.path.join(EXP, "results"), exist_ok=True)
    open(os.path.join(EXP, "results", f"round-off-{batch}.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(argv[1], argv[2])

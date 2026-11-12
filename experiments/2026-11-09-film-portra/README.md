# Film looks in the E-PM2's art-filter slots

Start with the plain-language write-up, `docs/film-emulation.md`. This folder is the lab bench.

| File | What |
|---|---|
| `NOTES.md` | dated lab notes, §1–41, in the order things happened (including what failed) |
| `CODE_DIG.md` | firmware addresses and what was read from the disassembly |
| `make_mock2.py`, `orfcodec.py`, `read_mock.py`, `mocklib.py` | the synthetic test RAW (written with our own ORF encoder), and reading its patches back from a camera JPEG |
| `fit_film.py` (uses `fit_xp9.py`) | fit a film target into the camera's adjustable parts; `--anchor … --robust 3` for the correction round |
| `check_film.py`, `analyze_mock2.py`, `analyze_filters.py` | score a camera JPEG against a target and against the model |
| `bake_slide.py` | target LUT for slide films (spektrafilm with the print step off) |
| `slots/build_seven_films.py` | writes the current patch specs (`patches/seven-*.json`) from the fit files |
| `slots/`, `slot3/` (other files) | assembly for the new code and the generators of earlier builds |
| other `analyze_*`, `fit_*`, `check_*`, `extract.py`, `make_chart.py`, `make_mock.py` | earlier stages (photographed chart, first synthetic RAW); kept because NOTES refers to them |

Not in git: `shots/` (camera files), `out/` (fit results, target LUTs, readings). The fit files in
`out/` are needed to regenerate the patches; the patches themselves are committed. Target LUTs come
from [spektrafilm](https://github.com/andreavolpato/spektrafilm) 0.3.4 (CC BY-SA 4.0).

`shots/` layout (kept small on purpose; only what the current pipeline uses): `testraw/` the
synthetic RAWs and the donor ORF whose header they borrow; `measured/` the camera's development of
the test RAW for each current film (the last measurement and the one its fit was corrected
against), plus stock Natural; `photos/` three ordinary photos taken with the seven-film build.
The photographed-chart series, the per-round folders (`mock1/`, `mock2/`, `stockfilters/`,
`remap7/`, …) and other files that NOTES and the earlier scripts name were deleted on 2026-11-12;
their patch readings remain in `out/mock/read_*.npz` on the machine that made them.

Run scripts from this folder with `../../.venv/bin/python -I <script>`.

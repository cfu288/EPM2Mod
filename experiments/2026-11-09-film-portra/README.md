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

`shots/` layout: `testraw/` the synthetic RAWs; `mock1/`, `mock2/`, `stockfilters/`, `remap7/`,
`remap2/`, `portracheck/`, `films1/`, `films1b/`, `films2/` one folder per measurement round, files
named by look; `archive/` the photographed-chart series and real photos of the early stages (some
scripts expect these directly under `shots/`).

Run scripts from this folder with `../../.venv/bin/python -I <script>`.

"""Bake a target LUT for a POSITIVE (slide) film: film -> scanned directly, no print (NOTES §26).

spektrafilm-lut always sends the film through a print paper, which is right for negatives and wrong
for slides. This runs the unchanged spektrafilm LUT builder with one parameter different: the
pipeline's `scan_film` switch is on, so the developed film is scanned as the final image. The switch
is set by wrapping spektrafilm's `init_params` (the builder's own code is not copied or replaced).
The --print argument is still required by the CLI and is ignored by the pipeline in this mode; the
bundle name is given explicitly to say so.
   ../../.venv/bin/python -I bake_slide.py kodak_ektachrome_100

Needs spektrafilm (GPL-3.0) installed; this script only calls it.
"""
import sys
import spektrafilm.runtime.params_builder as params_builder
from spektrafilm_lut_creator import cli

_init_params = params_builder.init_params
def init_params(*args, **kwargs):
    params = _init_params(*args, **kwargs)
    assert params.film.is_positive, "bake_slide.py is for positive films; use spektrafilm-lut for negatives"
    params.io.scan_film = True
    return params
params_builder.init_params = init_params

film = sys.argv[1]
sys.exit(cli.main(["build", "--film", film, "--print", "kodak_portra_endura", "--input", "vlog", "--output", "srgb", "--resolution", "33",
                   "--name", f"spektrafilm_v034_{film}_scanfilm_1lut_vlog_srgb", "--out", sys.argv[2] if len(sys.argv) > 2 else "out/lut"]))

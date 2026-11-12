"""Bake a target LUT for a POSITIVE (slide) film: film -> scanned directly, no print (NOTES §26).

spektrafilm-lut always sends the film through a print paper, which is right for negatives and wrong
for slides. This runs the same builder with one change: the pipeline's `scan_film` switch is on, so
the developed film is scanned as the final image. The --print argument is still required by the CLI
and is ignored by the pipeline in this mode; the bundle name is given explicitly to say so.
   ../../.venv/bin/python -I bake_slide.py kodak_ektachrome_100
"""
import sys
from spektrafilm_lut_creator import builders, cli

def _make_pipeline(self, spec, in_entry, out_entry, print_stock):
    from spektrafilm.runtime.params_builder import digest_params, init_params
    from spektrafilm.runtime.pipeline import SimulationPipeline
    params = init_params(film_profile=spec.film_profile, print_profile=print_stock)
    assert params.film.is_positive, "bake_slide.py is for positive films; use spektrafilm-lut for negatives"
    params.debug.lut_mode = True
    params.io.scan_film = True
    params.io.input_color_space = in_entry.primaries; params.io.output_color_space = out_entry.primaries
    params.io.input_cctf_decoding = False; params.io.output_cctf_encoding = False
    params.io.input_gamut_compress = spec.input_gamut_compress; params.io.output_gamut_compress = spec.output_gamut_compress
    return SimulationPipeline(digest_params(params))

builders.BundleBuilder._make_pipeline = _make_pipeline
film = sys.argv[1]
sys.exit(cli.main(["build", "--film", film, "--print", "kodak_portra_endura", "--input", "vlog", "--output", "srgb", "--resolution", "33",
                   "--name", f"spektrafilm_v034_{film}_scanfilm_1lut_vlog_srgb", "--out", "out/lut"]))

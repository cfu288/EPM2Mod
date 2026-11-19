"""Apply a build's specs in memory and write the image to a scratch file, for emulator checks while `epm2mod make`
cannot run. Not a way to make firmware for a camera: it runs none of the checks of `make`.

    .venv/bin/python experiments/2026-11-16-doublex/scripts/apply_only.py data/builds/NAME.json /tmp/scratch/NAME.BIN
"""
import sys
from pathlib import Path
from epm2mod import builds, pipeline, stock
from epm2mod.paths import repo_paths

paths = repo_paths()
description = builds.load_description(Path(sys.argv[1]).resolve())
applied, digest = pipeline.build_image(description, pipeline.load_specs(paths, description), stock.read_stock(paths))
Path(sys.argv[2]).write_bytes(applied.image)
print(description.name, digest, applied.changed_bytes, "bytes changed")

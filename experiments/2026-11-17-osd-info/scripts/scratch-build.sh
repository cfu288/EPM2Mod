#!/bin/bash
# scratch-build.sh SPEC.json OUT.BIN: the specs of builds/films-12d.json plus SPEC, as a scratch image
# (epm2mod apply; no build description). Run from the repository root. Also runs the free-space check.
set -e
SPECS=$(python3 -c "import json;print(' '.join(json.load(open('builds/films-12d.json'))['specs']))")
.venv/bin/epm2mod apply $SPECS "$1" --from firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN -o "$2"
sha256sum "$2" | cut -c1-64
python3 tools/freespace.py check $SPECS "$1" | tail -4

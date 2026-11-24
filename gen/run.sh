#!/usr/bin/env bash
# gen/run.sh [--check]: run every generator of gen/, in order. They write their patch specs into data/specs/.
# --check: then fail if a committed spec differs from what its generator makes (CI runs this).
# Needs: the MN103 binutils (tools/setup.sh --binutils) and Olympus's firmware (uv run epm2mod fetch-stock).
set -euo pipefail
cd "$(dirname "$0")/.."
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
uv run python gen/lss-core/mkspec.py "$work/lss-core"
uv run python gen/build-label/mkspec.py
uv run python gen/stock-films/structure.py "$work/structure"
uv run python gen/stock-films/loader.py "$work/loader"
uv run python gen/interval/mkspec_v2.py
uv run python gen/interval/mkspec_frames240.py
uv run python gen/level-gauge/mkspec_step_a.py
uv run python gen/level-gauge/mkspec_step_b.py
uv run python gen/peaking/mkspec_direct4.py "$work/peaking-direct4"
uv run python gen/lss-menu/mkspec.py
uv run python gen/peaking/mkspec_colours.py "$work/peaking-colours"
uv run python gen/peaking/mkspec_fast.py "$work/peaking-fast"
uv run python gen/peaking/mkspec_guard.py "$work/peaking-guard"
uv run python gen/peaking/mkspec_mf.py "$work/peaking-mf"
uv run python gen/gauge-info/mkspec_gauge_info.py
uv run python gen/gauge-info/mkspec_gauge_bar_left.py
uv run python gen/spot-core/mkspec.py "$work/spot-core"
uv run python gen/spot-menu/mkspec.py
# last: it reads the film loader's labels from the loader's spec, and the bytes it hooks from the build's other specs
uv run python gen/log-menu/mkspec.py "$work/log-menu"
if [ "${1:-}" = "--check" ]; then
  git diff --exit-code --stat -- data/specs/ || { echo "gen/run.sh: a committed spec differs from its generator's output" >&2; exit 1; }
  echo "gen/run.sh: every generated spec is as committed"
fi

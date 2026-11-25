#!/usr/bin/env bash
# gen/run.sh [--check]: run every generator of gen/, in order. They write their patch specs into data/specs/.
# --check: then fail if a committed spec differs from what its generator makes (CI runs this).
# Needs: the MN103 binutils (uv run epm2mod init) and Olympus's firmware (uv run epm2mod fetch-stock).
# Not needed and not checked: the E-PL6 firmware. interval/mkspec_v2.py and level-gauge/mkspec_step_b.py compare
# their tables with it when it is on the computer and say "skipped" when it is not (gen/README.md).
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
  # status, not diff: a spec that a generator writes and git does not hold is a difference too
  changed=$(git status --porcelain --untracked-files=all -- data/specs/)
  [ -z "$changed" ] || { printf '%s\n' "$changed" >&2; echo "gen/run.sh: a spec is not committed as its generator writes it (changed, or not in git)" >&2; exit 1; }
  echo "gen/run.sh: every generated spec is as committed"
fi

#!/usr/bin/env bash
# gen/run.sh [--check]: run every generator of gen/, in order. They write their patch specs into data/specs/.
# --check: then fail if a committed spec differs from what its generator makes (CI runs this).
# Needs: the MN103 binutils (uv run epm2mod init) and Olympus's firmware (uv run epm2mod fetch-stock).
# Not read: the E-PL6 firmware. interval/mkspec_v2.py and level-gauge/mkspec_step_b.py compare their tables with it
# only when its file is their argument, and this script gives none (gen/README.md).
set -euo pipefail
cd "$(dirname "$0")/.."
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
touch "$work/started"  # the specs that are newer than this file after the run are the ones the generators write
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
  # Only the specs that the generators wrote in this run: a spec written by hand, or one of a candidate that git
  # does not hold yet, is not this check's business. Status, not diff: a generated spec that git does not hold is
  # a difference too.
  written=$(find data/specs -name '*.json' -newer "$work/started" | sort)
  [ -n "$written" ] || { echo "gen/run.sh: the generators wrote no spec" >&2; exit 1; }
  # shellcheck disable=SC2086
  changed=$(git status --porcelain --untracked-files=all -- $written)
  [ -z "$changed" ] || { printf '%s\n' "$changed" >&2; echo "gen/run.sh: a spec is not committed as its generator writes it (changed, or not in git)" >&2; exit 1; }
  echo "gen/run.sh: every generated spec is as committed ($(printf '%s\n' "$written" | wc -l) specs)"
fi

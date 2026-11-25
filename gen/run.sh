#!/usr/bin/env bash
# gen/run.sh [--check]: run every generator of gen/, in order. They write their patch specs into data/specs/.
# --check: compare, and change nothing. The generators can only write into data/specs/, so the script keeps a copy
#   of that folder, lets them write, compares what they wrote with the copy, and puts the copy back, also when it
#   is interrupted. It fails when a spec in the working tree is not what its generator writes (a hand edit to a
#   generated spec fails and stays as it was), when git does not hold a generated spec, and when a generated spec
#   differs from the committed one. CI runs this.
# Needs: the MN103 binutils (uv run epm2mod init) and Olympus's firmware (uv run epm2mod fetch-stock).
# Not read: the E-PL6 firmware. interval/mkspec_v2.py and level-gauge/mkspec_step_b.py compare their tables with it
# only when its file is their argument, and this script gives none (gen/README.md).
set -euo pipefail
cd "$(dirname "$0")/.."
check=0; [ "${1:-}" = "--check" ] && check=1
work=$(mktemp -d)
restore() {
  # the specs as they were before the generators ran: each file they wrote gets its old content, or goes
  if [ -d "$work/kept" ]; then
    find data/specs -name '*.json' -newer "$work/started" | while read -r spec; do
      if [ -f "$work/kept/$(basename "$spec")" ]; then cp -p "$work/kept/$(basename "$spec")" "$spec"; else rm -f "$spec"; fi
    done
  fi
  rm -rf "$work"
}
trap restore EXIT
if [ $check = 1 ]; then mkdir "$work/kept" && cp -p data/specs/*.json "$work/kept/"; fi
touch "$work/started"  # the specs that are newer than this file after the run are the ones the generators write
# A file system that keeps whole seconds would give a spec written in the same second the time of this file, and
# find -newer would leave it out. So the first generator starts in a later second.
sleep 1.1
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
if [ $check = 1 ]; then
  # Only the specs that the generators wrote in this run: a spec written by hand, or one of a candidate that git
  # does not hold yet, is not this check's business.
  written=$(find data/specs -name '*.json' -newer "$work/started" | sort)
  [ -n "$written" ] || { echo "gen/run.sh: the generators wrote no spec" >&2; exit 1; }
  bad=""
  for spec in $written; do
    cmp -s "$spec" "$work/kept/$(basename "$spec")" || bad="$bad $spec"
  done
  count=$(printf '%s\n' "$written" | wc -l)
  restore; trap - EXIT  # the working tree is as it was; what follows reads it and git
  [ -z "$bad" ] || { echo "gen/run.sh: not what its generator writes (the file is left as it was):$bad" >&2; exit 1; }
  # shellcheck disable=SC2086
  changed=$(git status --porcelain --untracked-files=all -- $written)
  [ -z "$changed" ] || { printf '%s\n' "$changed" >&2; echo "gen/run.sh: a generated spec is not committed (changed, or not in git)" >&2; exit 1; }
  echo "gen/run.sh: every generated spec is as committed ($count specs)"
fi

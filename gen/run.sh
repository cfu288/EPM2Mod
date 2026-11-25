#!/usr/bin/env bash
# gen/run.sh [--check]: run every generator of gen/, in order. They write their patch specs into data/specs/.
# --check: compare, and write nothing in the working tree: the generators run in a temporary copy of the files they
#   read. It fails when a spec in the working tree is not what its generator writes, when git does not hold a
#   generated spec, and when a generated spec differs from the committed one. CI runs this.
# Needs: the MN103 binutils (uv run epm2mod init) and Olympus's firmware (uv run epm2mod fetch-stock).
# Not read: the E-PL6 firmware. interval/mkspec_v2.py and level-gauge/mkspec_step_b.py compare their tables with it
# only when its file is their argument, and this script gives none (gen/README.md).
set -euo pipefail
cd "$(dirname "$0")/.."
check=0; [ "${1:-}" = "--check" ] && check=1
root=$PWD
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
if [ $check = 1 ]; then
  mkdir -p "$work/tree/build"
  # the files as they are in the working tree, also the ones git does not hold; a deleted one is not copied
  git ls-files -z --cached --others --exclude-standard -- gen data tools emulator cli epm2mod.json pyproject.toml \
    | while IFS= read -r -d '' f; do if [ -f "$f" ]; then printf '%s\0' "$f"; fi; done \
    | tar --null -T - -cf - | tar -C "$work/tree" -xf -
  for d in build/toolchain build/map build/blocks firmware; do
    if [ -e "$d" ]; then mkdir -p "$(dirname "$work/tree/$d")" && ln -s "$root/$d" "$work/tree/$d"; fi
  done
  # git answers for the copy (the pinned binutils commit) and does not write the index of the real checkout
  echo "gitdir: $(git rev-parse --absolute-git-dir)" > "$work/tree/.git"
  export GIT_OPTIONAL_LOCKS=0
  touch -t 200001010000 "$work/started" "$work/tree"/data/specs/*.json  # a newer spec is one that a generator wrote
  cd "$work/tree"
fi
uv run --project "$root" python gen/lss-core/mkspec.py "$work/lss-core"
uv run --project "$root" python gen/build-label/mkspec.py
uv run --project "$root" python gen/stock-films/structure.py "$work/structure"
uv run --project "$root" python gen/stock-films/loader.py "$work/loader"
uv run --project "$root" python gen/interval/mkspec_v2.py
uv run --project "$root" python gen/interval/mkspec_frames240.py
uv run --project "$root" python gen/level-gauge/mkspec_step_a.py
uv run --project "$root" python gen/level-gauge/mkspec_step_b.py
uv run --project "$root" python gen/peaking/mkspec_direct4.py "$work/peaking-direct4"
uv run --project "$root" python gen/lss-menu/mkspec.py
uv run --project "$root" python gen/peaking/mkspec_colours.py "$work/peaking-colours"
uv run --project "$root" python gen/peaking/mkspec_fast.py "$work/peaking-fast"
uv run --project "$root" python gen/peaking/mkspec_guard.py "$work/peaking-guard"
uv run --project "$root" python gen/peaking/mkspec_mf.py "$work/peaking-mf"
uv run --project "$root" python gen/gauge-info/mkspec_gauge_info.py
uv run --project "$root" python gen/gauge-info/mkspec_gauge_bar_left.py
uv run --project "$root" python gen/spot-core/mkspec.py "$work/spot-core"
uv run --project "$root" python gen/spot-menu/mkspec.py
# last: it reads the film loader's labels from the loader's spec, and the bytes it hooks from the build's other specs
uv run --project "$root" python gen/log-menu/mkspec.py "$work/log-menu"
if [ $check = 1 ]; then
  # Only the specs that the generators wrote in this run: a spec written by hand, or one of a candidate that git
  # does not hold yet, is not this check's business.
  written=$(find data/specs -name '*.json' -newer "$work/started" | sort)
  cd "$root"
  [ -n "$written" ] || { echo "gen/run.sh: the generators wrote no spec" >&2; exit 1; }
  bad=""
  for spec in $written; do
    cmp -s "$spec" "$work/tree/$spec" || bad="$bad $spec"
  done
  [ -z "$bad" ] || { echo "gen/run.sh: not what its generator writes (the file is left as it was):$bad" >&2; exit 1; }
  # shellcheck disable=SC2086
  changed=$(git status --porcelain --untracked-files=all -- $written)
  [ -z "$changed" ] || { printf '%s\n' "$changed" >&2; echo "gen/run.sh: a generated spec is not committed (changed, or not in git)" >&2; exit 1; }
  echo "gen/run.sh: every generated spec is as committed ($(printf '%s\n' "$written" | wc -l) specs)"
fi

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
if [ "${1:-}" = "--check" ]; then
  git diff --exit-code --stat -- data/specs/ || { echo "gen/run.sh: a committed spec differs from its generator's output" >&2; exit 1; }
  echo "gen/run.sh: every generated spec is as committed"
fi

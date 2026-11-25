#!/usr/bin/env bash
# tools/ci.sh [python|web]: the hard checks. CI runs this script and nothing else; run it before a pull request.
#
#   tools/ci.sh           # both parts
#   tools/ci.sh web       # the web apps: format, lint, types, unit tests, both builds, browser tests
#   tools/ci.sh python    # the package, the scripts, the documents, the generators and the builds
#
# Needs a clone that is set up: uv run epm2mod init. Exit status 0: every check passed. A check that cannot run is a
# failure, not a skip. Nothing here warns: the soft report of a build is `uv run epm2mod lint NAME`.
#
# The builds that the python part makes and checks: the pinned build, and each data/builds/*.json that differs
# from the base commit. CI_BASE names the base (default origin/main).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
part=${1:-all}
case $part in all|python|web) ;; *) echo "usage: tools/ci.sh [python|web]" >&2; exit 2 ;; esac
export CI=1  # the unit tests then fail where they would skip (cli/tests/support.py, needs)
step() { echo; echo "== $*"; }

if [ "$part" != python ]; then
  step "web: npm ci, check, e2e"
  (
    cd web
    ../tools/node.sh npm ci --ignore-scripts
    ../tools/node.sh npm run check
    # shellcheck disable=SC2086
    ../tools/node.sh npx playwright install ${PLAYWRIGHT_INSTALL:-} chromium
    ../tools/node.sh npm run e2e
  )
fi
[ "$part" = web ] && exit 0

if [ ! -f cli/src/epm2mod/app/index.html ]; then
  step "the installer page (the release tests need it)"
  (cd web && ../tools/node.sh npm ci --ignore-scripts && ../tools/node.sh npm run build:app)
fi

step "the staged or committed changes hold no machine path"
base=$(git merge-base "${CI_BASE:-origin/main}" HEAD)
git diff -U0 --no-color --no-renames --diff-filter=AM "$base" HEAD -- . ':(exclude).githooks' | .githooks/machine-paths

step "black, mypy (the files that cli/pyproject.toml names)"
uv run --directory cli black --check --quiet .
uv run --directory cli mypy

step "unit tests (they also run pyflakes on the scripts, the document rules and the feature lists)"
uv run python -m unittest discover -s cli/tests

step "generated documents and generated specs"
uv run epm2mod generate --check
gen/run.sh --check

pinned=$(uv run epm2mod builds --json | uv run python -c 'import json, sys; print(json.load(sys.stdin)["pinned"])')
changed=$(git diff --name-only --no-renames --diff-filter=AM "$base" HEAD -- 'data/builds/*.json' | xargs -r -n1 basename -s .json)
for name in $(printf '%s\n' "$pinned" $changed | sort -u); do
  step "build $name: make, free-space check, load-order check, start in the emulator"
  uv run epm2mod make "$name"
  reason=$(grep -P "^$name\t" tools/check-waivers.tsv | cut -f2 || true)
  if [ -n "$reason" ]; then
    # a camera-tested build that a newer check refuses: its sha256 was compared, and the reason is on record
    echo "the checks of today are not run on $name: $reason"
  else
    uv run python tools/checks.py "data/builds/$name.json" --no-cache
  fi
done
echo
echo "tools/ci.sh: every check passed"

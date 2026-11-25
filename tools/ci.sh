#!/usr/bin/env bash
# tools/ci.sh [python|web]: the hard checks. CI runs this script and nothing else; run it before a pull request.
#
#   tools/ci.sh           # both parts
#   tools/ci.sh web       # the web apps: format, lint, types, unit tests, both builds, browser tests
#   tools/ci.sh python    # the package, the scripts, the documents, the generators and the builds
#
# Needs a clone that is set up: uv run epm2mod init. The python part starts with `epm2mod init --check` and stops
# when the set-up is not the pinned one (the objdump's source commit, the emulator's commit, Node, Olympus's
# firmware, the firmware map). EPM2_BINUTILS, OM_EMU_DIR and OM_EMU_NODE replace pinned tools: with one of them
# set, the checks that use the tool fail here.
# Exit status 0: every check passed. A check that cannot run is a failure, not a skip, and no build is exempt.
# One exception, stated here because it is not a check of this repository: two generators also compare their
# tables with the E-PL6 firmware when that file is on the computer (gen/README.md). No clone has it, the
# generators say so in the log, and the committed specs are compared all the same.
# Nothing here warns: the soft report of a build is `uv run epm2mod lint NAME`.
#
# The builds that the python part makes and checks: the pinned build, and each data/builds/*.json that differs
# from the base commit, committed or not, and each one that git does not hold yet. It prints the list.
# The base is CI_BASE (a commit or a ref). Without it the script fetches origin's main and takes that: a base that
# is behind its remote would leave builds out.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
part=${1:-all}
case $part in all|python|web) ;; *) echo "usage: tools/ci.sh [python|web]" >&2; exit 2 ;; esac
export CI=1  # the unit tests then fail where they would skip (cli/tests/support.py, needs); overrides are refused
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

step "the set-up is the pinned one"
uv run epm2mod init --check

# always: git ignores the page, so one that an earlier run built can be stale
step "the installer page, built from this tree (the release tests read it)"
(cd web && ../tools/node.sh npm ci --ignore-scripts && ../tools/node.sh npm run build:app)

if [ -z "${CI_BASE:-}" ]; then
  git fetch --quiet origin main || { echo "tools/ci.sh: origin's main cannot be fetched, so the base commit is not known. Set CI_BASE to the commit your work starts from" >&2; exit 1; }
  CI_BASE=FETCH_HEAD
fi
base=$(git merge-base "$CI_BASE" HEAD) || { echo "tools/ci.sh: the base $CI_BASE is not a commit of this clone" >&2; exit 1; }

step "no commit since the base $(git rev-parse --short "$base") adds a machine path"
.githooks/machine-paths --since "$base"

step "black, mypy (the files that cli/pyproject.toml names)"
uv run --directory cli black --check --quiet .
uv run --directory cli mypy

step "unit tests (they also run pyflakes on the scripts, the document rules and the feature lists)"
uv run python -m unittest discover -s cli/tests

step "generated documents, the code-space map and generated specs"
uv run epm2mod generate --check
uv run python tools/freespace.py map > /dev/null
[ -z "$(git status --porcelain -- docs/reference/code-space-map.md docs/reference/code-space-map.tsv)" ] \
  || { echo "tools/ci.sh: docs/reference/code-space-map.md is not what 'tools/freespace.py map' writes: commit the new one" >&2; exit 1; }
gen/run.sh --check

pinned=$(uv run epm2mod builds --json | uv run python -c 'import json, sys; print(json.load(sys.stdin)["pinned"])')
# against the working tree, and what git does not hold yet: a description is checked before it is committed
changed=$( { git diff --name-only --no-renames --diff-filter=AM "$base" -- 'data/builds/*.json'
             git ls-files --others --exclude-standard -- 'data/builds/*.json'; } | xargs -r -n1 basename -s .json)
builds=$(printf '%s\n' "$pinned" $changed | sort -u)
for name in $builds; do
  step "build $name: make, free-space check, load-order check, start in the emulator"
  uv run epm2mod make "$name"
  uv run python tools/checks.py "data/builds/$name.json"
done
echo
# shellcheck disable=SC2086
echo "tools/ci.sh: every check passed. Builds made and checked:" $builds

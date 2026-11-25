#!/usr/bin/env bash
# tools/ci.sh [python|web]: the hard checks. CI runs this script and nothing else; run it before a pull request.
#
#   tools/ci.sh           # both parts
#   tools/ci.sh web       # the web apps: format, lint, types, unit tests, both builds, browser tests
#   tools/ci.sh python    # the package, the scripts, the documents, the generators and the builds
#   tools/ci.sh python NAME...   # and also the builds NAME (a new candidate that git does not hold yet)
#
# Needs a clone that is set up: uv run epm2mod init. The python part starts with `epm2mod init --check` and stops
# when the set-up is not the pinned one (the objdump's source commit, the emulator's commit, Node, Olympus's
# firmware, the firmware map). EPM2_BINUTILS, OM_EMU_DIR and OM_EMU_NODE replace pinned tools: with one of them
# set, the checks that use the tool fail here.
# Exit status 0: every check passed. A check that cannot run is a failure, not a skip, and no build is exempt.
# No check reads a file that a clone does not have: two generators can compare their tables with the E-PL6
# firmware, and they do so only when that file is given as their argument, which gen/run.sh never does.
# Nothing here warns: the soft report of a build is `uv run epm2mod lint NAME`.
#
# The builds that the python part makes and checks: the pinned build, each data/builds/*.json that git holds and
# that differs from the base commit (committed or changed in the working tree), and the builds named as
# arguments. A description that git does not hold is not picked up by itself: a leftover file must not change the
# result. The script prints the list, and one line that names the descriptions it did not check.
# No check writes to a file that git holds: gen/run.sh --check and the code-space map compare and put back.
# The base is CI_BASE (a commit or a ref). Without it the script fetches origin's main and takes that: a base that
# is behind its remote would leave builds out.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
part=${1:-all}
case $part in all|python|web) ;; *) echo "usage: tools/ci.sh [python [NAME...]|web]" >&2; exit 2 ;; esac
[ $# -gt 0 ] && shift
named="$*"
for name in $named; do
  [ -f "data/builds/$name.json" ] || { echo "tools/ci.sh: no build description data/builds/$name.json" >&2; exit 2; }
done
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
# an unclosed file is an error here, not a line in the log: a ResourceWarning in a destructor cannot fail a test,
# so the log is read for it
uv run python -W error::ResourceWarning -m unittest discover -s cli/tests 2>&1 | tee "${TMPDIR:-/tmp}/epm2mod-tests.$$"
if grep -q "ResourceWarning" "${TMPDIR:-/tmp}/epm2mod-tests.$$"; then
  rm -f "${TMPDIR:-/tmp}/epm2mod-tests.$$"
  echo "tools/ci.sh: the unit tests left a file open (ResourceWarning above)" >&2; exit 1
fi
rm -f "${TMPDIR:-/tmp}/epm2mod-tests.$$"

step "generated documents, the code-space map and generated specs"
uv run epm2mod generate --check
# the code-space map: freespace.py writes the two files, so they are kept, compared and put back
kept=$(mktemp -d)
cp -p docs/reference/code-space-map.md docs/reference/code-space-map.tsv "$kept/"
uv run python tools/freespace.py map > /dev/null && same=1 || same=0
for f in code-space-map.md code-space-map.tsv; do
  cmp -s "docs/reference/$f" "$kept/$f" || same=0
  cp -p "$kept/$f" "docs/reference/$f"
done
rm -rf "$kept"
[ $same = 1 ] && [ -z "$(git status --porcelain -- docs/reference/code-space-map.md docs/reference/code-space-map.tsv)" ] \
  || { echo "tools/ci.sh: docs/reference/code-space-map.md is not what 'uv run python tools/freespace.py map' writes, or is not committed (the file is left as it was)" >&2; exit 1; }
gen/run.sh --check

pinned=$(uv run epm2mod builds --json | uv run python -c 'import json, sys; print(json.load(sys.stdin)["pinned"])')
# the descriptions git holds, against the working tree: an edit is checked before it is committed
changed=$(git diff --name-only --no-renames --diff-filter=AM "$base" -- 'data/builds/*.json' | xargs -r -n1 basename -s .json)
# shellcheck disable=SC2086
builds=$(printf '%s\n' "$pinned" $changed $named | sort -u)
unheld=$(git ls-files --others --exclude-standard -- 'data/builds/*.json' | xargs -r -n1 basename -s .json)
unchecked=$(for name in $unheld; do printf '%s\n' $builds | grep -qx "$name" || printf '%s ' "$name"; done)
for name in $builds; do
  step "build $name: make, free-space check, load-order check, start in the emulator"
  uv run epm2mod make "$name"
  uv run python tools/checks.py "data/builds/$name.json"
done
echo
# shellcheck disable=SC2086
echo "tools/ci.sh: every check passed. Builds made and checked:" $builds
[ -z "$unchecked" ] || echo "Not checked, because git does not hold them and they were not named (tools/ci.sh python NAME...): $unchecked"

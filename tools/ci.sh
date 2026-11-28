#!/usr/bin/env bash
# tools/ci.sh [python|web]: the hard checks, the same in CI and locally; run it before a pull request.
#
# Needs a clone that is set up: uv run epm2mod init. A check that cannot run is a failure, not a skip. The builds that
# the python part makes and checks: the pinned build, and each data/builds/*.json that differs from the base commit
# (CI_BASE; default: origin's main). Nothing here warns: the soft report of a build is `uv run epm2mod lint NAME`.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
part=${1:-all}
case $part in all|python|web) ;; *) echo "usage: tools/ci.sh [python|web]" >&2; exit 2 ;; esac
export UV_LOCKED=1  # an out-of-date uv.lock is an error here, as in CI
export CI=1  # the unit tests then fail where they would skip (cli/tests/support.py, needs)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
step() { echo; echo "== $*"; }
quiet() { "$@" > "$tmp/log" 2>&1 || { cat "$tmp/log"; exit 1; }; }  # the output of a step that passes is not shown

if [ "$part" != python ]; then
  step "web: npm ci, check, e2e"
  cd web
  quiet ../tools/node.sh npm ci --ignore-scripts
  quiet ../tools/node.sh npm run check
  # shellcheck disable=SC2086
  quiet ../tools/node.sh npx playwright install ${PLAYWRIGHT_INSTALL:-} chromium
  quiet ../tools/node.sh npm run e2e
  cd ..
fi
[ "$part" = web ] && exit 0

step "the set-up is the pinned one"
quiet uv run epm2mod init --check

# always: git ignores the page, so one that an earlier run built can be stale
step "the installer page, built from this tree (the release tests read it)"
cd web
quiet ../tools/node.sh npm ci --ignore-scripts
quiet ../tools/node.sh npm run build:app
cd ..

if [ -z "${CI_BASE:-}" ]; then
  git fetch --quiet origin main || { echo "tools/ci.sh: origin's main cannot be fetched, so the base commit is not known. Set CI_BASE to the commit your work starts from" >&2; exit 1; }
  CI_BASE=FETCH_HEAD
fi
base=$(git merge-base "$CI_BASE" HEAD) || { echo "tools/ci.sh: the base $CI_BASE is not a commit of this clone" >&2; exit 1; }

step "black, mypy (the files that cli/pyproject.toml names)"
quiet uv run --directory cli black --check .
quiet uv run --directory cli mypy

step "unit tests (they also run pyflakes on the scripts, and hold the feature lists)"
quiet uv run python -m unittest discover -s cli/tests

step "generated documents and generated specs"
quiet uv run epm2mod generate --check
quiet gen/run.sh --check

pinned=$(uv run epm2mod builds --json | uv run python -c 'import json, sys; print(json.load(sys.stdin)["pinned"])')
# the descriptions git holds, against the working tree: an edit is checked before it is committed
changed=$(git diff --name-only --no-renames --diff-filter=AM "$base" -- 'data/builds/*.json' | xargs -r -n1 basename -s .json)
# shellcheck disable=SC2086
builds=$(printf '%s\n' "$pinned" $changed | sort -u)
for name in $builds; do
  step "build $name: make, free-space check, load-order check, start in the emulator"
  quiet uv run epm2mod make "$name"  # a candidate: with the three checks
  if grep -q '"camera_tested"' "data/builds/$name.json"; then  # make compares a tested build with its sha256 only
    # shellcheck disable=SC2046
    quiet uv run python tools/freespace.py check $(uv run python -c 'import json, sys; b = json.load(open(sys.argv[1])); print(*b["specs"], *["--first-code"] * bool(b.get("first_code")))' "data/builds/$name.json")
    # the boot report lines the build changes on purpose, as make passes them
    uv run python -c 'import json, sys; json.dump(json.load(open(sys.argv[1])).get("boot_differs", []), open(sys.argv[2], "w"))' "data/builds/$name.json" "$tmp/declared"
    quiet uv run python emulator/boot-test "build/$name.BIN" --declared "$tmp/declared"
    quiet uv run python emulator/update-path-test "build/$name.BIN" --declared "$tmp/declared"
  fi
done
echo
# shellcheck disable=SC2086
echo "tools/ci.sh: every check passed. Builds made and checked:" $builds

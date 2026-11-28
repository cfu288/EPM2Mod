#!/bin/sh
# Plan a release with epm2mod release, for the release workflow (release.yml, job "Plan the release").
#   plan.sh NOTES_FILE
# KIND is rc or final, BUILD is the name of a build that is not pinned or empty, and SUMMARY is the text that comes
# first in the notes. The script writes tag, release_version, title, prerelease, commit and sha256 to GITHUB_OUTPUT
# and the notes to NOTES_FILE. When the release is not ready, it prints each reason and exits with the status of
# epm2mod release.
set -eu
if [ $# -ne 1 ]; then
  echo "usage: plan.sh NOTES_FILE" >&2
  exit 2
fi
NOTES_FILE=$1
OUTPUT=${GITHUB_OUTPUT:?GITHUB_OUTPUT names the file for the step outputs}

set -- --json --summary "${SUMMARY:-}"
if [ "${KIND:-rc}" = final ]; then set -- "$@" --final; fi
if [ -n "${BUILD:-}" ]; then set -- "$@" --build "$BUILD"; fi

PLAN=$(mktemp)
trap 'rm -f "$PLAN"' EXIT
status=0
uv run epm2mod release "$@" > "$PLAN" || status=$?
jq -r '(.problems[]? | "::error::Not ready: \(.)"), (.error.message? // empty | "::error::\(.)")' "$PLAN"
if [ "$status" -ne 0 ]; then
  exit "$status"
fi
jq -r '"tag=\(.tag)", "release_version=\(.release_version)", "title=\(.title)", "prerelease=\(.prerelease)",
  "commit=\(.commit)", "sha256=\(.sha256)"' "$PLAN" >> "$OUTPUT"
jq -r .notes "$PLAN" > "$NOTES_FILE"
cat "$NOTES_FILE"

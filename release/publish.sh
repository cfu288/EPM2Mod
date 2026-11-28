#!/bin/sh
# Publish a GitHub release from the files that the release workflow downloaded (release.yml, job "Publish the
# release").
#   publish.sh TAG VERSION PRERELEASE COMMIT CHECKED PACKAGED
# PRERELEASE is true or false. CHECKED is the firmware sha256 that the plan checked, and PACKAGED is the one that the
# zip installs. The current folder holds release-zip/*.zip, release-dmg/*.dmg and release-notes/notes.md. gh needs
# GH_TOKEN, and GITHUB_REPOSITORY names the repository.
# The files go to a draft first. A draft creates no tag, so a failed upload leaves only a draft, and publishing the
# draft creates the tag on COMMIT. A draft with the same tag that a failed run left is deleted first.
set -eu
if [ $# -ne 6 ]; then
  echo "usage: publish.sh TAG VERSION PRERELEASE COMMIT CHECKED PACKAGED" >&2
  exit 2
fi
TAG=$1
VERSION=$2
PRERELEASE=$3
COMMIT=$4
CHECKED=$5
PACKAGED=$6
REPO=${GITHUB_REPOSITORY:?GITHUB_REPOSITORY names the repository}

if [ -z "$CHECKED" ] || [ "$CHECKED" != "$PACKAGED" ]; then
  echo "The zip installs the firmware $PACKAGED, but the plan checked $CHECKED." >&2
  exit 1
fi

ERR=$(mktemp)
trap 'rm -f "$ERR"' EXIT
if draft=$(gh release view "$TAG" --repo "$REPO" --json isDraft --jq .isDraft 2> "$ERR"); then
  if [ "$draft" != true ]; then
    echo "The release $TAG is already published." >&2
    exit 1
  fi
  gh release delete "$TAG" --repo "$REPO" --yes
elif ! grep -q 'release not found' "$ERR"; then
  cat "$ERR" >&2
  exit 1
fi

gh release create "$TAG" release-zip/*.zip release-dmg/*.dmg --draft --prerelease="$PRERELEASE" \
  --repo "$REPO" --target "$COMMIT" --title "EPM2Mod $VERSION" --notes-file release-notes/notes.md
gh release edit "$TAG" --repo "$REPO" --draft=false

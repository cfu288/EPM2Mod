#!/usr/bin/env bash
# tools/node.sh COMMAND [ARG...]: run COMMAND with the Node that .nvmrc names, or a newer one, first on PATH.
#
#   tools/node.sh npm run check       # from web/: ../tools/node.sh npm run check
#   tools/node.sh node --version
#
# It takes `node` from PATH when that is new enough, else the newest Node that nvm has (NVM_DIR, default ~/.nvm).
# With neither it stops and names the version: exit status 1. tools/setup.sh installs one when nvm is there.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WANT=$(tr -d 'v \n' < "$ROOT/.nvmrc")
major() { "$1" -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0; }
if ! command -v node >/dev/null 2>&1 || [ "$(major node)" -lt "$WANT" ]; then
  newest=$(ls -d "${NVM_DIR:-$HOME/.nvm}"/versions/node/v*/bin/node 2>/dev/null | sort -V | tail -1 || true)
  if [ -z "$newest" ] || [ "$(major "$newest")" -lt "$WANT" ]; then
    have=$(command -v node >/dev/null 2>&1 && node --version || echo none)
    echo "error: this step needs Node $WANT or newer (.nvmrc). The node on PATH: $have. With nvm: nvm install $WANT. Without nvm: https://nodejs.org" >&2
    exit 1
  fi
  PATH="$(dirname "$newest"):$PATH"
fi
exec "$@"

#!/usr/bin/env bash
# tools/node.sh COMMAND [ARG...]: run COMMAND with the Node that .nvmrc names first on PATH. Exactly that version:
# the emulator's results and the web checks must not depend on which Node a computer has.
#
#   tools/node.sh npm run check       # from web/: ../tools/node.sh npm run check
#   tools/node.sh node --version
#
# It takes `node` from PATH when that is the version, else the one nvm has (NVM_DIR, default ~/.nvm). With neither
# it stops and names the version: exit status 1. With EPM2_NODE_INSTALL=1 and nvm on the computer it first
# installs that Node with nvm (`uv run epm2mod init` does this).
# .nvmrc is the one place that names the version. emulator/emuenv.py and web/need-node.mjs read it; a test holds
# web/package.json "engines" to it.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WANT=$(tr -d 'v \n' < "$ROOT/.nvmrc")
NVM=${NVM_DIR:-$HOME/.nvm}
if [ "$(node --version 2>/dev/null || true)" != "v$WANT" ]; then
  found=$NVM/versions/node/v$WANT/bin/node
  if [ ! -x "$found" ] && [ -n "${EPM2_NODE_INSTALL:-}" ] && [ -s "$NVM/nvm.sh" ]; then
    set +u; . "$NVM/nvm.sh"; nvm install "$WANT" >&2; set -u
  fi
  if [ ! -x "$found" ]; then
    have=$(node --version 2>/dev/null || echo none)
    echo "error: this step needs Node $WANT (.nvmrc). The node on PATH: $have. With nvm: uv run epm2mod init, or nvm install $WANT. Without nvm: https://nodejs.org/dist/v$WANT/" >&2
    exit 1
  fi
  PATH="$(dirname "$found"):$PATH"
fi
exec "$@"

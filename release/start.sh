#!/bin/sh
# Start EPM2Mod (macOS and Linux). Everything it downloads stays in this folder (.uv): delete the folder to remove it.
#   ./start.sh            open the installer page in the browser
#   ./start.sh install --card /path/to/card   write EPM2Mod to the SD card on the command line
#   ./start.sh --help     the other commands for camera owners
set -eu
cd "$(dirname "$0")"

# uv, pinned: version and the sha256 of each download (https://github.com/astral-sh/uv/releases/tag/0.13.6)
UV_VERSION=0.13.6
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) ASSET=uv-aarch64-apple-darwin; SHA=60fbd5c8a1ed681845eea28d9d622fcde03c51e91a43465b64a1e17db1ed3472 ;;
  Darwin-x86_64) ASSET=uv-x86_64-apple-darwin; SHA=63ba17fdda55ad1a230d4b37fc6017ffa10c23688c83818bd3bfdf914c652a02 ;;
  Linux-x86_64) ASSET=uv-x86_64-unknown-linux-gnu; SHA=f29c3e94ffabd7e6f3ba521dba169a9b7ec12100bf3257087f0f24f6123f3645 ;;
  Linux-aarch64 | Linux-arm64) ASSET=uv-aarch64-unknown-linux-gnu; SHA=229e194255c7958d86d56e8790d969a6f74736592133f0dfd0076f754c642c1d ;;
  *) echo "EPM2Mod runs on macOS and Linux (x86-64 or ARM) here; this computer is $(uname -s) $(uname -m)." >&2; exit 1 ;;
esac

UV=.uv/bin/uv
if [ ! -x "$UV" ] || [ "$("$UV" --version 2>/dev/null | cut -d' ' -f2)" != "$UV_VERSION" ]; then
  echo "Getting uv $UV_VERSION (once)..." >&2
  mkdir -p .uv/bin
  ARCHIVE=".uv/$ASSET.tar.gz"
  curl --proto '=https' --tlsv1.2 -fsSL -o "$ARCHIVE" \
    "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$ASSET.tar.gz"
  if command -v sha256sum >/dev/null 2>&1; then GOT=$(sha256sum "$ARCHIVE" | cut -d' ' -f1)
  else GOT=$(shasum -a 256 "$ARCHIVE" | cut -d' ' -f1); fi
  if [ "$GOT" != "$SHA" ]; then
    rm -f "$ARCHIVE"
    echo "The uv download has the wrong checksum. Nothing was installed. Try again later." >&2
    exit 1
  fi
  tar -xzf "$ARCHIVE" -C .uv/bin --strip-components 1
  rm -f "$ARCHIVE"
fi

# Python 3.12 from uv, kept in this folder; the package needs nothing else (standard library only).
export UV_CACHE_DIR="$PWD/.uv/cache" UV_PYTHON_INSTALL_DIR="$PWD/.uv/python" PYTHONPATH="$PWD/src"
# the name in usage lines, examples and hints: the one a user types here
export EPM2MOD_PROG=./start.sh
[ $# -eq 0 ] && set -- serve
exec "$UV" run --no-project --managed-python --python 3.12 python -m epm2mod "$@"

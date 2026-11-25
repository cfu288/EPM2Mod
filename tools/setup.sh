#!/usr/bin/env bash
# Set up what the analysis tools and the build checks need, inside this repository. Safe to run again.
#
#   tools/setup.sh            # everything
#   tools/setup.sh --check    # only say what is present. Exit status 1 when an item of 1 to 5 is missing
#   tools/setup.sh --binutils # only the MN103 binutils (what gen/ needs; CI uses this)
#
# 1. The MN103 disassembler, assembler and linker: GNU binutils, built from the submodule
#    third_party/binutils-gdb into build/toolchain/ (ignored by git). Needs gcc, make, m4, bison and flex.
# 2. Node (the major version in .nvmrc) for the emulator and the web apps: tools/node.sh finds it on PATH or in
#    nvm. With nvm present and no such Node, "nvm install" gets it.
# 3. The emulator working tree: emulator/setup.sh.
# 4. Olympus's firmware: uv run epm2mod fetch-stock (a download from the maker, 43 MB).
# 5. The firmware map, for the free-space check: tools/fwmap.py build (1 minute, 470 MB).
#
# It also switches on the commit hooks in .githooks/ for this clone. --check reports them, and the two things the
# web apps need (web/README.md), which this script does not install.
#
# Nothing is installed outside the repository, but a Node version through nvm.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
PREFIX=$ROOT/build/toolchain
OBJDUMP=$PREFIX/bin/mn10300-elf-objdump
WANT=$(tr -d 'v \n' < .nvmrc)
check_only=0; [ "${1:-}" = "--check" ] && check_only=1
binutils_only=0; [ "${1:-}" = "--binutils" ] && binutils_only=1
missing=0
miss() { echo "MISSING: $1"; missing=1; }

# The commit hooks (.githooks): the message format, no machine paths, the writing rules, black and mypy.
[ $check_only = 1 ] || git config core.hooksPath .githooks

echo "== 1. MN103 binutils"
if [ -x "$OBJDUMP" ]; then
  echo "present: $("$OBJDUMP" --version | head -1)"
elif [ $check_only = 1 ]; then
  miss "run tools/setup.sh"
else
  for tool in gcc make m4; do command -v $tool >/dev/null || { echo "error: $tool is needed to build binutils" >&2; exit 1; }; done
  if ! command -v bison >/dev/null || ! command -v flex >/dev/null; then
    # No bison or flex on this computer. Without root: fetch the two packages and unpack them under build/.
    deps=$ROOT/build/hostdeps
    if [ ! -x "$deps/usr/bin/bison" ] || [ ! -x "$deps/usr/bin/flex" ]; then
      command -v apt-get >/dev/null || { echo "error: bison and flex are needed to build binutils (install them and run this again)" >&2; exit 1; }
      mkdir -p "$deps/debs" && (cd "$deps/debs" && apt-get download bison flex > /dev/null)
      for deb in "$deps"/debs/*.deb; do dpkg -x "$deb" "$deps"; done
    fi
    export PATH="$deps/usr/bin:$PATH" BISON_PKGDATADIR="$deps/usr/share/bison"
  fi
  git submodule update --init --depth 1 third_party/binutils-gdb
  # Only the folders that objdump, as and ld need (the repository also holds gdb and the simulators).
  git -C third_party/binutils-gdb sparse-checkout set --cone bfd binutils gas ld opcodes include libiberty libsframe libctf zlib config cpu etc intl texinfo
  work=$ROOT/build/toolchain-build
  rm -rf "$work" && mkdir -p "$work" && cd "$work"
  "$ROOT/third_party/binutils-gdb/configure" --target=mn10300-elf --prefix="$PREFIX" --disable-nls --disable-werror \
    --disable-gdb --disable-gdbserver --disable-sim --disable-gprofng --disable-gold > configure.log 2>&1 \
    || { echo "error: configure failed, see $work/configure.log" >&2; exit 1; }
  make -j"$(nproc)" MAKEINFO=true all-binutils all-gas all-ld > make.log 2>&1 \
    || { echo "error: the build failed, see $work/make.log" >&2; exit 1; }
  make MAKEINFO=true install-binutils install-gas install-ld > install.log 2>&1 \
    || { echo "error: the install failed, see $work/install.log" >&2; exit 1; }
  cd "$ROOT" && rm -rf "$work"
  echo "built: $("$OBJDUMP" --version | head -1)"
fi
[ $binutils_only = 1 ] && exit 0

echo "== 2. Node $WANT or newer"
if node=$(tools/node.sh sh -c 'command -v node' 2>/dev/null); then
  echo "present: $node ($("$node" --version))"
  if [ "$node" != "$(command -v node || true)" ]; then
    echo "note: the node on PATH is $(node --version 2>/dev/null || echo absent). Run node and npm through tools/node.sh, or: nvm use $WANT"
  fi
elif [ $check_only = 1 ]; then
  miss "run tools/setup.sh (it uses nvm), or install Node $WANT"
elif [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then
  set +u; . "${NVM_DIR:-$HOME/.nvm}/nvm.sh"; nvm install "$WANT"; set -u
  echo "installed: $(tools/node.sh node --version)"
else
  tools/node.sh true  # stops with the message that names the version
fi

echo "== 3. Emulator working tree"
if [ $check_only = 1 ]; then emulator/setup.sh --check || missing=1; else emulator/setup.sh; fi

echo "== 4. Olympus's firmware"
if uv run --quiet epm2mod fetch-stock --dry-run 2>/dev/null | grep -q '^kept at'; then
  echo "present"
elif [ $check_only = 1 ]; then
  miss "run: uv run epm2mod fetch-stock"
else
  uv run --quiet epm2mod fetch-stock
fi

echo "== 5. Firmware map"
if [ -s build/map/linear.txt ]; then
  echo "present: build/map"
elif [ $check_only = 1 ]; then
  miss "run: uv run python tools/fwmap.py build"
else
  uv run --quiet python tools/fwmap.py build
fi
[ $check_only = 1 ] || exit 0

echo "== Commit hooks"
if [ "$(git config core.hooksPath || true)" = .githooks ]; then
  echo "on"
else
  echo "off: run tools/setup.sh, or: git config core.hooksPath .githooks"
fi
echo "== Web apps (only for work in web/; this script does not install them)"
if [ -d web/node_modules ]; then
  echo "present: web/node_modules"
else
  echo "absent: web/node_modules. Run: cd web && ../tools/node.sh npm ci && ../tools/node.sh npx playwright install chromium"
fi
exit $missing

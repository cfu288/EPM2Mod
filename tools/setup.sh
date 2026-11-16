#!/usr/bin/env bash
# Set up what the analysis tools and the build checks need, inside this repository. Safe to run again.
#
#   tools/setup.sh            # everything
#   tools/setup.sh --check    # only say what is present
#
# 1. The MN103 disassembler, assembler and linker: GNU binutils, built from the submodule
#    third_party/binutils-gdb into build/toolchain/ (ignored by git). Needs gcc, make, bison and flex.
# 2. Node (the major version in .nvmrc) for the emulator: taken from PATH, else from nvm. With nvm
#    present and no such Node, "nvm install" gets it.
# 3. The emulator working tree: tools/emu/setup.sh.
#
# Nothing is installed outside the repository, but a Node version through nvm.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
PREFIX=$ROOT/build/toolchain
OBJDUMP=$PREFIX/bin/mn10300-elf-objdump
WANT=$(tr -d 'v \n' < .nvmrc)
check_only=0; [ "${1:-}" = "--check" ] && check_only=1

node_ok() { command -v "$1" >/dev/null 2>&1 && [ "$("$1" -p 'process.versions.node.split(".")[0]')" -ge "$WANT" ]; }
find_node() {
  if node_ok node; then command -v node; return; fi
  local newest
  newest=$(ls -d "${NVM_DIR:-$HOME/.nvm}"/versions/node/v*/bin/node 2>/dev/null | sort -V | tail -1 || true)
  if [ -n "$newest" ] && node_ok "$newest"; then echo "$newest"; return; fi
  return 1
}

echo "== 1. MN103 binutils"
if [ -x "$OBJDUMP" ]; then
  echo "present: $("$OBJDUMP" --version | head -1)"
elif [ $check_only = 1 ]; then
  echo "MISSING: run tools/setup.sh"
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

echo "== 2. Node $WANT or newer"
if node=$(find_node); then
  echo "present: $node ($("$node" --version))"
elif [ $check_only = 1 ]; then
  echo "MISSING: run tools/setup.sh (it uses nvm), or install Node $WANT"
elif [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then
  set +u; . "${NVM_DIR:-$HOME/.nvm}/nvm.sh"; nvm install "$WANT"; set -u
  node=$(find_node) && echo "installed: $node"
else
  echo "error: no Node $WANT or newer, and no nvm. Install Node $WANT (https://nodejs.org) and run this again." >&2; exit 1
fi

echo "== 3. Emulator working tree"
if [ $check_only = 1 ]; then tools/emu/setup.sh --check || true; else tools/emu/setup.sh; fi

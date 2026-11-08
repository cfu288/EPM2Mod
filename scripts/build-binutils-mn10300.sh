#!/usr/bin/env bash
# Build GNU binutils (objdump, as, ld) for the MN10300/AM33 target into ~/opt/mn10300. No sudo needed.
# Source: ftp.gnu.org, signature checked against Nick Clifton's key (3A24BC1E8FB409FA9F14371813FCEF89DD9E3C4F).
set -euo pipefail
VER=2.43.1
SRC=$HOME/opt/src
PREFIX=$HOME/opt/mn10300
mkdir -p "$SRC" && cd "$SRC"
[ -f binutils-$VER.tar.xz ]     || curl -sSfLO https://ftp.gnu.org/gnu/binutils/binutils-$VER.tar.xz
[ -f binutils-$VER.tar.xz.sig ] || curl -sSfLO https://ftp.gnu.org/gnu/binutils/binutils-$VER.tar.xz.sig
gpg --list-keys 3A24BC1E8FB409FA9F14371813FCEF89DD9E3C4F >/dev/null 2>&1 || \
  gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys 3A24BC1E8FB409FA9F14371813FCEF89DD9E3C4F
gpg --verify binutils-$VER.tar.xz.sig binutils-$VER.tar.xz
[ -d binutils-$VER ] || tar xf binutils-$VER.tar.xz
mkdir -p build-mn10300 && cd build-mn10300
../binutils-$VER/configure --target=mn10300-elf --prefix="$PREFIX" --disable-nls --disable-werror \
  --disable-gdb --disable-gprof --disable-gold --disable-gprofng --disable-sim > configure.log 2>&1
make -j"$(nproc)" all-binutils all-gas all-ld > make.log 2>&1
make install-binutils install-gas install-ld > install.log 2>&1
"$PREFIX/bin/mn10300-elf-objdump" --version | head -1
echo "OK: $PREFIX/bin"

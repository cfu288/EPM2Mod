#!/bin/sh
# setup.sh [--check]: make the emulator ready: the submodule emulator/om-emu, the om-emu fork with the E-PM2's boot
# lab (https://github.com/cfu288/om-emu, branch e101), at the commit this repository pins.
#   --check   only report (exit 0 ready, 1 not)
# The tools run the fork's own files (emulator/om-emu/emu); nothing is copied or patched. Node 26 or newer is needed
# to run them (tools/setup.sh installs one; OM_EMU_NODE overrides). Exit status: 0 ready, 1 a step failed or not ready.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
sub=emulator/om-emu
check=0
for a in "$@"; do
  case $a in
    --check) check=1 ;;
    *) echo "setup.sh: unknown argument $a (use --check)" >&2; exit 1 ;;
  esac
done
fail() { echo "setup.sh: $*" >&2; exit 1; }
command -v git >/dev/null || fail "git not found"
if [ ! -e "$sub/emu/bin/boot.mjs" ]; then
  [ $check -eq 1 ] && { echo "setup.sh: $sub is not initialised (run emulator/setup.sh)"; exit 1; }
  echo "setup.sh: git submodule update --init $sub"
  git submodule sync -q "$sub"
  git submodule update --init "$sub" || fail "cannot initialise the submodule $sub"
fi
want=$(git ls-files -s "$sub" | cut -d' ' -f2)
have=$(git -C "$sub" rev-parse HEAD)
[ -n "$want" ] || fail "$sub is not a submodule of this repository"
if [ "$want" != "$have" ]; then
  [ $check -eq 1 ] && { echo "setup.sh: $sub is at $have, the repository pins $want (run: git submodule update --init $sub)"; exit 1; }
  fail "$sub is at $have but the repository pins $want (run: git submodule update --init $sub, or commit the new pin)"
fi
[ -e "$sub/emu/bin/boot.mjs" ] || fail "$sub at $have has no emu/bin/boot.mjs: not the fork with the boot lab (.gitmodules)"
echo "setup.sh: ready: om-emu $have in $sub"

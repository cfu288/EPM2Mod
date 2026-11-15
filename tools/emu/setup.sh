#!/bin/sh
# setup.sh [--force] [--check]: make the emulator working tree build/om-emu/ (ignored by git).
#
#   1. initialise the submodule third_party/om-emu (the pinned upstream commit, never edited),
#   2. export that commit into build/om-emu/ (git archive: no .git, no local changes),
#   3. apply tools/emu/om-emu-patches/*.patch in name order (patch -p1),
#   4. write build/om-emu/.epm2-setup: the commit and the sha256 of every patch.
#
# A second run does nothing when the commit and the patches are the same as the stamp says.
# --force builds the tree again. --check only reports (exit 0 = up to date, 1 = not).
# Our drivers (tools/emu/e101/, tools/emu/boot/) are not copied: they import build/om-emu/emu/...
# through OM_EMU_DIR (default build/om-emu). Node 26 or newer is needed to run them: OM_EMU_NODE.
# Exit status: 0 done or up to date, 1 a step failed (the reason is printed).
set -eu
root=$(cd "$(dirname "$0")/../.." && pwd)
cd "$root"
sub=third_party/om-emu
out=${OM_EMU_BUILD:-build/om-emu}
patches=tools/emu/om-emu-patches
force=0; check=0
for a in "$@"; do
  case $a in
    --force) force=1 ;;
    --check) check=1 ;;
    *) echo "setup.sh: unknown argument $a (use --force or --check)" >&2; exit 1 ;;
  esac
done
fail() { echo "setup.sh: $*" >&2; exit 1; }
command -v git >/dev/null || fail "git not found"
command -v patch >/dev/null || fail "patch not found"

if [ ! -e "$sub/LICENSE" ]; then
  [ $check -eq 1 ] && { echo "setup.sh: submodule $sub is not initialised"; exit 1; }
  echo "setup.sh: git submodule update --init $sub"
  git submodule update --init "$sub" || fail "cannot initialise the submodule $sub"
fi
want=$(git ls-files -s "$sub" | cut -d' ' -f2)
have=$(git -C "$sub" rev-parse HEAD)
[ -n "$want" ] || fail "$sub is not a submodule of this repository"
if [ "$want" != "$have" ]; then
  fail "$sub is at $have but the repository pins $want (run: git submodule update --init $sub)"
fi
[ -z "$(git -C "$sub" status --porcelain)" ] || fail "$sub has local changes; it must stay as upstream has it"

stamp="commit $have"
for p in "$patches"/*.patch; do
  stamp="$stamp
$(basename "$p") $(sha256sum "$p" | cut -d' ' -f1)"
done
if [ $force -eq 0 ] && [ -f "$out/.epm2-setup" ] && [ "$(cat "$out/.epm2-setup")" = "$stamp" ]; then
  echo "setup.sh: $out is up to date (om-emu $have, $(ls "$patches"/*.patch | wc -l | tr -d ' ') patches)"
  exit 0
fi
[ $check -eq 1 ] && { echo "setup.sh: $out is missing or not up to date; run tools/emu/setup.sh"; exit 1; }

case $out in build/*) ;; *) fail "OM_EMU_BUILD must be a folder under build/ (it is deleted and made again): $out" ;; esac
rm -rf "$out"
mkdir -p "$out"
git -C "$sub" archive HEAD | tar -x -C "$out" || fail "cannot export $sub"
echo "setup.sh: exported om-emu $have to $out"
for p in "$patches"/*.patch; do
  patch -d "$out" -p1 --forward --fuzz=0 --no-backup-if-mismatch -s < "$p" || fail "$(basename "$p") does not apply to om-emu $have"
  echo "setup.sh: applied $(basename "$p")"
done
printf '%s\n' "$stamp" > "$out/.epm2-setup"
echo "setup.sh: done. The tools use $out (override: OM_EMU_DIR)."

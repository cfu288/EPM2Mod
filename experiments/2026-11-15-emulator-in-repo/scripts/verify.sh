#!/bin/bash
# verify.sh SCRATCH [OLD_WORK]: the checks of the move of the emulator into the repository, from a clean state.
#   SCRATCH    a folder outside the repository for images and screenshots (for example /tmp/scratch/emu-verify)
#   OLD_WORK   optional: the old work folder with stage2-boot.mjs and play.mjs (the tree used before the move,
#              on om-emu 96bf756); with it the boot report and a menu screenshot sequence are compared old against new
# Uses its own working tree build/om-emu-verify and its own unpack folder, so a tree in use is not touched.
# Writes experiments/2026-11-15-emulator-in-repo/results/*.txt. Run from the repository root. Exit 0 = all as expected.
set -u
S=$(mkdir -p "$1" && cd "$1" && pwd); OLD=${2:-}
R=experiments/2026-11-15-emulator-in-repo/results; mkdir -p $R
PINNED=builds/peaking-colours.json
export OM_EMU_BUILD=build/om-emu-verify OM_EMU_DIR=$PWD/build/om-emu-verify EMU_IMAGES=$S/images EMU_TMP=$S EMU_STATE=$S/state EMU_OUT=$S/out
clean() { sed -e "s#$S#/tmp/scratch#g" -e "s#$PWD/##g" -e "s#$PWD#.#g" ${OLD:+-e "s#$OLD#OLD_WORK#g"} -e "s#$HOME#~#g"; }
bad=0
expect() { local want=$1 name=$2; shift 2; "$@" > $S/$name.raw 2>&1; local got=$?; { echo "\$ ${*/$S//tmp/scratch}"; cat $S/$name.raw; echo "exit status $got (expected $want)"; } | clean > $R/$name.txt
  if [ $got -eq $want ]; then echo "ok    $name (exit $got)"; else echo "WRONG $name (exit $got, expected $want)"; bad=1; fi; }

# 1. clean state: submodule, working tree, images
rm -rf build/om-emu-verify $S/images $S/state $S/out
git submodule deinit -f emulator/om-emu > /dev/null 2>&1
{ git submodule update --init emulator/om-emu 2>&1 | tail -1; git submodule status emulator/om-emu; emulator/setup.sh; emulator/setup.sh; emulator/setup.sh --check; echo "exit status $?"; } 2>&1 | clean > $R/setup.txt
tail -3 $R/setup.txt

# 2. boot test: stock, the pinned build, the debug-log build
expect 0 boot-test-stock emulator/boot-test stock --out $S/boot-stock
expect 0 boot-test-peaking-colours emulator/boot-test $PINNED --out $S/boot-pinned
expect 0 boot-test-debug-log emulator/boot-test builds/debug-log.json --out $S/boot-debug
for n in stock pinned debug; do cp $S/boot-$n/boot-image.txt $R/boot-report-$n.txt; done
# 3. update path
expect 0 update-path-test-stock emulator/update-path-test stock
expect 0 update-path-test-peaking-colours emulator/update-path-test $PINNED --out $S/update-pinned
clean < $S/update-pinned/update-image.txt > $R/update-report-pinned.txt
# 4. the withdrawn build must fail
.venv/bin/python experiments/2026-11-15-emulator-in-repo/scripts/build_withdrawn.py $S/peaking-direct-2.BIN > $S/build-withdrawn.txt 2>&1
expect 1 boot-test-peaking-direct-2-withdrawn emulator/boot-test $S/peaking-direct-2.BIN --out $S/boot-withdrawn
{ grep sha256 $S/build-withdrawn.txt; tail -3 $S/boot-withdrawn/boot-image.txt; } | clean >> $R/boot-test-peaking-direct-2-withdrawn.txt
# 5. the function harness on the new tree
expect 0 emurun-memcpy python3 emulator/emurun.py run memcpy
expect 0 emurun-rec-limit python3 emulator/emurun.py run rec_limit

# 6. old tree against new tree (pinned image): boot report and a menu sequence
if [ -n "$OLD" ]; then
  NODE=$(python3 -c "import sys; sys.path.insert(0, 'emulator'); import emuenv; print(emuenv.node())")
  B=$(emulator/emu-run --blocks $PINNED)
  (cd "$OLD" && BLOCKS=$B EPM2_REPO=$OLDPWD $NODE stage2-boot.mjs 2000) > $S/old-boot.txt 2>&1
  { echo "boot report of $PINNED: old tree (om-emu 96bf756, outside the repository) against new tree (build/om-emu-verify)"; echo "diff after 'wall ms N' is taken out of both (no other part is taken out; carriage returns of the console text dropped):"
    if diff <(tr -d '\r' < $S/old-boot.txt | sed 's/wall ms [0-9]*//') <(sed 's/wall ms [0-9]*//' $S/boot-pinned/boot-image.txt); then echo "no line differs: the reports are equal, with the same instruction counts on both CPUs"; else bad=1; fi
    grep '^stop:' $S/old-boot.txt $S/boot-pinned/boot-image.txt; } > $S/old-vs-new.raw 2>&1; clean < $S/old-vs-new.raw > $R/boot-report-old-vs-new.txt
  tail -4 $R/boot-report-old-vs-new.txt | head -1
  emulator/mkstate $PINNED $S/state/peaking-colours-p.json p | clean > $R/menu-sequence-old-vs-new.txt
  STEPS="w:500 shot:01-shooting key:MENU shot:02-top-menu key:RIGHT key:OK shot:03-shooting-menu-1 key:DOWN key:DOWN key:DOWN shot:04-custom-menu-tab key:RIGHT shot:05-custom-menu-A key:RIGHT shot:06-A-rows key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN shot:07-peaking-row key:RIGHT shot:08-peaking-list"
  rm -rf $S/seq; mkdir -p $S/seq; cp $S/state/peaking-colours-p.json $S/seq/new.json; cp $S/state/peaking-colours-p.json $S/seq/old.json
  E101_STATE=$S/seq/new.json emulator/emu-run $PINNED play.mjs $S/seq/new $STEPS > $S/seq/new.log 2>&1
  (cd "$OLD" && BLOCKS=$B E101_STATE=$S/seq/old.json EPM2_REPO=$OLDPWD $NODE play.mjs $S/seq/old $STEPS) > $S/seq/old.log 2>&1
  { echo "menu sequence on $PINNED (MENU, Custom Menu, A, Peaking list), the same state file and steps in both trees"; echo "steps: $STEPS"
    n=0; for f in $S/seq/new/*.png; do n=$((n+1)); b=$(basename $f); if cmp -s $f $S/seq/old/$b; then echo "byte-equal  $b  sha256 $(sha256sum $f | cut -c1-16)"; else echo "DIFFER      $b"; bad=1; fi; done
    [ $n -eq 8 ] || { echo "expected 8 screenshots, got $n"; bad=1; }
    cmp -s $S/seq/new.json $S/seq/old.json && echo "state files after the run: byte-equal"; } > $S/seq.raw 2>&1; clean < $S/seq.raw >> $R/menu-sequence-old-vs-new.txt
  grep -c byte-equal $R/menu-sequence-old-vs-new.txt
fi
[ $bad -eq 0 ] && echo "verify: all as expected" || echo "verify: SOMETHING IS WRONG"
exit $bad

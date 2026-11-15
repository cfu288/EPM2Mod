#!/bin/zsh
# shotdiff.sh IMAGE_A IMAGE_B OUTDIR STEP...   (the pre-flash check of a menu patch)
# Runs the same play.mjs key script on two images and reports which screenshots differ (cmp per PNG).
# IMAGE: stock, builds/NAME.json, a .BIN file or a folder of unpacked blocks.
# Each image starts from a copy of its settings state EMU_STATE/NAME-MODE.json (MODE from SHOTDIFF_MODE, default p;
# made with tools/emu/mkstate when missing), or with SHOTDIFF_STATE=<file> from that file for both,
# or with SHOTDIFF_STATE=none from an empty settings store.
# Exit status 0 = no screenshot differs, 1 = some differ, 2 = a run failed, 3 = the emulator is not set up.
. ${0:A:h}/env.sh
(( $# >= 4 )) || { sed -n '2,8p' $0; exit 2 }
a=$1; b=$2; out=$3; shift 3
rm -rf $out/a $out/b; mkdir -p $out/a $out/b
for s in a b; do
  img=${(P)s}; dir=$(blocks $img) || exit 3; st=$out/$s/state.json
  if [[ $SHOTDIFF_STATE == none ]]; then st=""; elif [[ -n $SHOTDIFF_STATE ]]; then cp $SHOTDIFF_STATE $st; else src=$(state $img ${SHOTDIFF_MODE:-p}) || exit 3; cp $src $st; fi
  BLOCKS=$dir E101_STATE=$st $NODE $BOOT/play.mjs $out/$s "$@" > $out/$s/log.txt 2>&1 || { echo "RUN FAILED for $img:"; tail -3 $out/$s/log.txt; exit 2 }
done
n=0; d=0
for f in $out/a/*.png; do
  n=$((n+1)); g=$out/b/${f:t}
  if cmp -s $f $g; then echo "same    ${f:t}"; else d=$((d+1)); echo "DIFFER  ${f:t}"; fi
done
echo "$d of $n screenshots differ ($a against $b); logs and PNGs in $out/a and $out/b"
grep -h "^STOP\|done at" $out/a/log.txt $out/b/log.txt | cut -c1-160
[[ $d -eq 0 ]]

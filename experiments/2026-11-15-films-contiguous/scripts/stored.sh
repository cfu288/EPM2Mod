#!/bin/zsh
# stored.sh: does a Picture Mode chosen on the pinned build still select the same look on the new build?
# For each of the 12 art entries: on the pinned build choose it in the live control (mode P) and, in ART mode,
# in the ART list; save the settings state; start the new build with that state and take the same screens.
# Output: build/emu/films-contiguous/stored/{p,art}-NN-{pinned,new}.png (NN = place in the pinned build's list)
# and sheet-{p,art}-{a,b}.png (upper row = pinned, lower row = new; a = entries 1..6, b = 7..12).
cd ${0:A:h}/../../.. && . tools/emu/boot/env.sh
export E101_RTC=${E101_RTC:-2026-11-14T12:00:00}
old=${1:-builds/peaking-fast.json}; new=${2:-builds/films-contiguous.json}
pre=build/emu/films-contiguous/state/pinned
out=build/emu/films-contiguous/stored; rm -rf $out; mkdir -p $out
dold=$(blocks $old) || exit 3; dnew=$(blocks $new) || exit 3
rep() { local o=(); repeat $1 o+=($2); print -r -- $o }
for n in {01..12}; do
  k=$(( 10#$n ))
  # mode P: live control, Picture Mode, RIGHT to the entry (Natural is the start; Portra is 5 steps away), OK
  cp $pre-p.json $out/p-$n.json
  print -r -- "env BLOCKS=$dold E101_STATE=$out/p-$n.json $NODE $BOOT/play.mjs $out w:500 key:OK w:500 key:UP $(rep $(( k + 4 )) key:RIGHT) shot:p-$n-pinned key:OK w:500 > $out/p-$n-pinned.out 2>&1 && cp $out/p-$n.json $out/p-$n-new.json && env BLOCKS=$dnew E101_STATE=$out/p-$n-new.json $NODE $BOOT/play.mjs $out w:500 key:OK w:500 shot:p-$n-new > $out/p-$n-new.out 2>&1"
  # ART mode: the ART list is open at the start; DOWN to the entry, OK
  cp $pre-art.json $out/art-$n.json
  print -r -- "env BLOCKS=$dold E101_STATE=$out/art-$n.json $NODE $BOOT/play.mjs $out w:500 $(rep $(( k - 1 )) key:DOWN) shot:art-$n-pinned key:OK w:500 > $out/art-$n-pinned.out 2>&1 && cp $out/art-$n.json $out/art-$n-new.json && env BLOCKS=$dnew E101_STATE=$out/art-$n-new.json $NODE $BOOT/play.mjs $out w:500 shot:art-$n-new > $out/art-$n-new.out 2>&1"
done | xargs -P ${PAR:-8} -I{} zsh -c "{}"
grep -L "^done at" $out/*.out | sed 's/^/RUN FAILED: /'
for m in p art; do
  for h in a b; do
    [[ $h == a ]] && r=({01..06}) || r=({07..12})
    f=(); for n in $r; do f+=($out/$m-$n-pinned.png); done; for n in $r; do f+=($out/$m-$n-new.png); done
    python3 $BOOT/sheet.py $out/sheet-$m-$h.png 6 2 $f
  done
done
ls $out/*.png | wc -l

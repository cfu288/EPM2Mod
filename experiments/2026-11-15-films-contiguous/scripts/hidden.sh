#!/bin/zsh
# hidden.sh: flags that were set on the pinned build, read by the candidate. Run after settings.sh.
# The states settings/pinned/pms-grainy.json (show flag of Grainy Film Off) and settings/pinned/bkt-grainy.json
# (bracket flag of Grainy Film Off) are loaded by both builds. Screens: the live control strip from Kodachrome
# on (lc-1..6), the Picture Mode Settings list (pms) and the ART BKT list (bkt-1, bkt-2).
# Expected on both builds: the strip has no Grainy Film; the row Grainy Film reads Off in both lists.
# Output: build/emu/films-contiguous/hidden/{pinned,new}/*.png and sheet.png (upper row pinned, lower row new)
cd ${0:A:h}/../../.. && . emulator/boot/env.sh
export E101_RTC=${E101_RTC:-2026-11-14T12:00:00}
old=${1:-builds/peaking-fast.json}; new=${2:-builds/films-contiguous.json}
src=build/emu/films-contiguous/settings/pinned; out=build/emu/films-contiguous/hidden; rm -rf $out
rep() { local o=(); repeat $1 o+=($2); print -r -- $o }
lc="w:500 key:OK w:500 key:UP $(rep 8 key:RIGHT)"; for n in {1..6}; do lc+=" shot:lc-$n key:RIGHT"; done
pms="w:500 key:MENU key:RIGHT key:OK $(rep 3 key:DOWN) key:RIGHT $(rep 3 key:DOWN) key:RIGHT $(rep 5 key:DOWN) key:RIGHT $(rep 12 key:DOWN) shot:pms"
bkt="w:500 key:UP key:RIGHT $(rep 4 key:DOWN) shot:bkt-1 $(rep 3 key:DOWN) shot:bkt-2"
for b in pinned new; do
  [[ $b == pinned ]] && d=$(blocks $old) || d=$(blocks $new)
  mkdir -p $out/$b
  for r in lc pms bkt; do
    [[ $r == bkt ]] && s=$src/bkt-grainy.json || s=$src/pms-grainy.json
    cp $s $out/$b/state-$r.json
    print -r -- "env BLOCKS=$d E101_STATE=$out/$b/state-$r.json $NODE $BOOT/play.mjs $out/$b ${(P)r} > $out/$b/$r.out 2>&1"
  done
done | xargs -P ${PAR:-6} -I{} zsh -c "{}"
grep -L "^done at" $out/*/*.out | sed 's/^/RUN FAILED: /'
python3 $BOOT/sheet.py $out/sheet.png 9 2 $out/pinned/lc-{1..6}.png $out/pinned/pms.png $out/pinned/bkt-{1,2}.png $out/new/lc-{1..6}.png $out/new/pms.png $out/new/bkt-{1,2}.png

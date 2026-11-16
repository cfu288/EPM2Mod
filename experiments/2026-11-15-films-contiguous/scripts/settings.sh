#!/bin/zsh
# settings.sh: does the same choice, made by the entry's name, write the same settings on both builds?
# For each art entry, on the pinned and on the new build, from the same start state:
#   pm    Shooting Menu 1 -> Picture Mode -> the entry -> OK                    (stores the Picture Mode)
#   pmr   the same list -> the entry -> RIGHT (the entry's own page) -> second Filter Type -> OK
#   pms   Custom Menu D -> Picture Mode Settings -> the entry -> Off            (the entry's show flag)
#   bkt   ART list -> ART BKT -> the entry -> Off                               (the entry's bracket flag)
#   type  ART list -> the entry -> RIGHT -> second Filter Type -> OK            (the entry's type, if it has two)
#   fx    ART list -> the entry -> RIGHT -> Add Effects -> first effect -> OK   (the entry's effect setting)
# The entry is found by its place in that build's list. cmp_state.py then compares the saved settings states.
# Expected: every pair equal. Output: build/emu/films-contiguous/settings/{pinned,new}/OP-NAME.json and .png
cd ${0:A:h}/../../.. && . tools/emu/boot/env.sh
export E101_RTC=${E101_RTC:-2026-11-14T12:00:00}
old=${1:-builds/peaking-fast.json}; new=${2:-builds/films-contiguous.json}
pre=build/emu/films-contiguous/state/pinned
out=build/emu/films-contiguous/settings; rm -rf $out; mkdir -p $out/pinned $out/new
dold=$(blocks $old) || exit 3; dnew=$(blocks $new) || exit 3
rep() { local o=(); repeat $1 o+=($2); print -r -- $o }
names=(portra ektachrome pro400h kodachrome grainy vis250d velvia superia sepia dramatic keyline watercolor)
pold=(1 2 3 4 5 6 7 8 9 10 11 12); pnew=(1 2 3 4 8 5 6 7 9 10 11 12)
inp="w:500 key:MENU key:RIGHT key:OK"
for i in {1..12}; do
  for b in pinned new; do
    [[ $b == pinned ]] && { d=$dold; p=$pold[i] } || { d=$dnew; p=$pnew[i] }
    n=$names[i]
    pm="$inp key:RIGHT key:DOWN key:RIGHT $(rep $(( p + 4 )) key:DOWN) shot:list-pm-$n key:OK w:500"
    pmr="$inp key:RIGHT key:DOWN key:RIGHT $(rep $(( p + 4 )) key:DOWN) key:RIGHT shot:pmr0-$n key:RIGHT key:DOWN shot:pmr-$n key:OK w:500"
    pms="$inp $(rep 3 key:DOWN) key:RIGHT $(rep 3 key:DOWN) key:RIGHT $(rep 5 key:DOWN) key:RIGHT $(rep $(( p + 4 )) key:DOWN) key:RIGHT key:UP key:OK shot:list-pms-$n key:MENU key:MENU key:MENU key:MENU w:500"
    bkt="w:500 key:UP key:RIGHT $(rep $(( p - 1 )) key:DOWN) key:RIGHT key:UP key:OK shot:list-bkt-$n key:MENU w:500"
    type="w:500 $(rep $(( p - 1 )) key:DOWN) key:RIGHT key:RIGHT key:DOWN shot:type-$n key:OK w:500"
    fx="w:500 $(rep $(( p - 1 )) key:DOWN) key:RIGHT key:DOWN key:RIGHT key:DOWN shot:fx-$n key:OK w:500"
    for op in pm pmr pms bkt type fx; do
      [[ $op == pms && $i == 1 ]] && continue      # Portra (Pop Art) has no row in Picture Mode Settings, as on stock
      [[ $op == pm* ]] && m=p || m=art
      cp $pre-$m.json $out/$b/$op-$n.json
      print -r -- "env BLOCKS=$d E101_STATE=$out/$b/$op-$n.json $NODE $BOOT/play.mjs $out/$b ${(P)op} > $out/$b/$op-$n.out 2>&1"
    done
  done
done | xargs -P ${PAR:-8} -I{} zsh -c "{}"
grep -L "^done at" $out/*/*.out | sed 's/^/RUN FAILED: /'
python3 ${0:A:h}/cmp_state.py $out/pinned $out/new $pre-p.json $pre-art.json
# the screens of the entry's own page (not the list-* screens, which differ by design), below the title line
python3 ${0:A:h}/cmp_png.py $out/pinned $out/new --below 40 --skip list-

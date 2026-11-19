#!/bin/zsh
# screens.sh NEW [OLD]: the emulator checks of a films build (NEW, builds/NAME.json) against the pinned build (OLD).
# Output: build/emu/films-max/NAME/ (ignored by git). Needs both .BIN files (epm2mod make) and emulator/setup.sh.
#   1 screens   every list of looks, English: live control strip (P and movie), Picture Mode list, Picture Mode
#               Settings, ART list, ART BKT list            -> NAME/new/*.png, NAME/pinned/*.png
#   2 stored    a look chosen on OLD (12 entries in P, 12 in ART mode), the state then loaded by NEW: the screen
#               that NEW shows                              -> NAME/stored/{p,art}-NN-{pinned,new}.png
#   3 chosen    on NEW: each of the 12 entries chosen in the live control, the state saved; the stored Picture
#               Mode value is printed (state byte 51880 of the mode bank)
#   4 languages the Picture Mode and ART lists in English, German, Japanese, French -> NAME/lang/
#   5 crawl     shallow menu crawl in P, ART and movie mode, NEW against OLD -> NAME/crawlcmp-*/
cd ${0:A:h}/../../.. && . emulator/boot/env.sh
export E101_RTC=${E101_RTC:-2026-11-14T12:00:00}
new=$1; old=${2:-builds/peaking-fast.json}; name=${new:t:r}
S=experiments/2026-11-15-films-contiguous/scripts
O=build/emu/films-max/$name; mkdir -p $O/state $O/stored $O/chosen
export EMU_OUT=$PWD/$O/out EMU_STATE=$PWD/$O/state
dold=$(blocks $old) || exit 3; dnew=$(blocks $new) || exit 3
for m in p art movie; do [[ -f $O/state/pinned-$m.json ]] || emulator/mkstate $old $O/state/pinned-$m.json $m; done
rep() { local o=(); repeat $1 o+=($2); print -r -- $o }
strip() { local s="shot:$1-00"; for n in {1..$2}; do s+=" key:RIGHT shot:$1-$(printf %02d $n)"; done; print -r -- $s }

echo "== 1 screens"
inp="w:500 key:MENU key:RIGHT key:OK"
lc="w:500 key:OK w:500 key:UP $(strip lc 19)"
mlc="w:500 key:OK w:500 key:UP $(strip mlc 19)"
pm="$inp key:RIGHT key:DOWN key:RIGHT shot:pm-0 $(rep 6 key:DOWN) shot:pm-1 $(rep 7 key:DOWN) shot:pm-2 $(rep 5 key:DOWN) shot:pm-3"
pms="$inp $(rep 3 key:DOWN) key:RIGHT $(rep 3 key:DOWN) key:RIGHT $(rep 5 key:DOWN) shot:pms-0 key:RIGHT $(rep 6 key:DOWN) shot:pms-1 $(rep 7 key:DOWN) shot:pms-2 $(rep 5 key:DOWN) shot:pms-3"
art="w:500 shot:art-01"; for n in {2..13}; do art+=" key:DOWN shot:art-$(printf %02d $n)"; done
art+=" key:RIGHT shot:bkt-1 $(rep 7 key:DOWN) shot:bkt-2 $(rep 7 key:DOWN) shot:bkt-3"
for b in pinned new; do
  [[ $b == pinned ]] && d=$dold || d=$dnew
  mkdir -p $O/$b
  for r in lc pm pms art mlc; do
    case $r in art) m=art;; mlc) m=movie;; *) m=p;; esac
    cp $O/state/pinned-$m.json $O/$b/state-$r.json
    print -r -- "env BLOCKS=$d E101_STATE=$O/$b/state-$r.json $NODE $BOOT/play.mjs $O/$b ${(P)r} > $O/$b/$r.out 2>&1"
  done
done | xargs -P ${PAR:-8} -I{} zsh -c "{}"
grep -L "^done at" $O/*/*.out | sed 's/^/RUN FAILED: /'
for b in pinned new; do
  python3 $BOOT/sheet.py $O/sheet-$b-lc.png 10 2 $O/$b/lc-*.png
  python3 $BOOT/sheet.py $O/sheet-$b-menu.png 4 2 $O/$b/pm-*.png $O/$b/pms-*.png
  python3 $BOOT/sheet.py $O/sheet-$b-art.png 8 2 $O/$b/art-*.png $O/$b/bkt-*.png
done

echo "== 2 stored selection (chosen on $old, shown by $new)"
for n in {01..12}; do
  k=$(( 10#$n ))
  cp $O/state/pinned-p.json $O/stored/p-$n.json
  print -r -- "env BLOCKS=$dold E101_STATE=$O/stored/p-$n.json $NODE $BOOT/play.mjs $O/stored w:500 key:OK w:500 key:UP $(rep $(( k + 4 )) key:RIGHT) shot:p-$n-pinned key:OK w:500 > $O/stored/p-$n-pinned.out 2>&1 && cp $O/stored/p-$n.json $O/stored/p-$n-new.json && env BLOCKS=$dnew E101_STATE=$O/stored/p-$n-new.json $NODE $BOOT/play.mjs $O/stored w:500 shot:p-$n-screen key:OK w:500 shot:p-$n-new > $O/stored/p-$n-new.out 2>&1"
  cp $O/state/pinned-art.json $O/stored/art-$n.json
  print -r -- "env BLOCKS=$dold E101_STATE=$O/stored/art-$n.json $NODE $BOOT/play.mjs $O/stored w:500 $(rep $(( k - 1 )) key:DOWN) shot:art-$n-pinned key:OK w:500 > $O/stored/art-$n-pinned.out 2>&1 && cp $O/stored/art-$n.json $O/stored/art-$n-new.json && env BLOCKS=$dnew E101_STATE=$O/stored/art-$n-new.json $NODE $BOOT/play.mjs $O/stored w:500 shot:art-$n-new > $O/stored/art-$n-new.out 2>&1"
done | xargs -P ${PAR:-8} -I{} zsh -c "{}"
grep -L "^done at" $O/stored/*.out | sed 's/^/RUN FAILED: /'
for m in p art; do
  f=(); for n in {01..12}; do f+=($O/stored/$m-$n-pinned.png); done; for n in {01..12}; do f+=($O/stored/$m-$n-new.png); done
  python3 $BOOT/sheet.py $O/sheet-stored-$m.png 12 1 $f
done

echo "== 3 chosen on $new: the stored Picture Mode value of each entry"
for n in {01..12}; do
  k=$(( 10#$n ))
  for m in p art; do
    cp $O/state/pinned-$m.json $O/chosen/$m-$n.json
    [[ $m == p ]] && keys="w:500 key:OK w:500 key:UP $(rep $(( k + 4 )) key:RIGHT) key:OK w:500 shot:$m-$n" || keys="w:500 $(rep $(( k - 1 )) key:DOWN) key:OK w:500 shot:$m-$n"
    print -r -- "env BLOCKS=$dnew E101_STATE=$O/chosen/$m-$n.json $NODE $BOOT/play.mjs $O/chosen $keys > $O/chosen/$m-$n.out 2>&1"
  done
done | xargs -P ${PAR:-8} -I{} zsh -c "{}"
grep -L "^done at" $O/chosen/*.out | sed 's/^/RUN FAILED: /'
python3 ${0:A:h}/stored_values.py $O/chosen

echo "== 4 languages"
emulator/boot/lang-all.sh $new enu deu jpn fra > $O/lang.log 2>&1
python3 emulator/boot/sheets.py $O/out/lang-all/$name $O/lang >> $O/lang.log 2>&1; tail -2 $O/lang.log

echo "== 5 crawl"
for c in p-nocard-shallow art-nocard-shallow movie-nocard-shallow; do
  emulator/boot/crawl-all.sh $c $old $new > $O/crawl-$c.log 2>&1
  python3 emulator/boot/crawlcmp.py $O/out/crawl/$c/${old:t:r} $O/out/crawl/$c/$name $O/crawlcmp-$c | tail -4
done

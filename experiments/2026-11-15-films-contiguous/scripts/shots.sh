#!/bin/zsh
# shots.sh IMAGE NAME [STATEPREFIX]: the screens that list the art entries, English.
# IMAGE: builds/NAME.json, a .BIN file or stock. Output: build/emu/films-contiguous/NAME/*.png.
# STATEPREFIX: settings states PREFIX-p.json, PREFIX-art.json, PREFIX-movie.json (default: the pinned build's,
# build/emu/films-contiguous/state/pinned; made with tools/emu/mkstate). Copies are used.
#   lc-00..19   mode P, OK (live control), UP (Picture Mode), RIGHT x 19
#   pm-1..3     Shooting Menu 1 -> Picture Mode list, three pages
#   pms-1..3    Custom Menu D -> Picture Mode Settings list
#   art-01..13  ART list (12 entries and ART BKT); bkt-1, bkt-2: the ART BKT list
#   mlc-00..19  movie mode, live control Picture Mode strip
#   alc-00..13  ART mode, live control: first item, RIGHT x 13
cd ${0:A:h}/../../.. && . tools/emu/boot/env.sh
export E101_RTC=${E101_RTC:-2026-11-14T12:00:00}
img=$1; name=$2; pre=${3:-build/emu/films-contiguous/state/pinned}
out=build/emu/films-contiguous/$name; mkdir -p $out
dir=$(blocks $img) || exit 3
rep() { local o=(); repeat $1 o+=($2); print -r -- $o }
strip() { local s="shot:$1-00"; for n in {1..$2}; do s+=" key:RIGHT shot:$1-$(printf %02d $n)"; done; print -r -- $s }
inp="w:500 key:MENU key:RIGHT key:OK"
inart="w:500"
lc="w:500 key:OK w:500 key:UP $(strip lc 19)"
mlc="w:500 key:OK w:500 key:UP $(strip mlc 19)"
alc="w:500 key:OK w:500 $(strip alc 13)"
pm="$inp key:RIGHT key:DOWN key:RIGHT shot:pm-0 $(rep 6 key:DOWN) shot:pm-1 $(rep 7 key:DOWN) shot:pm-2 $(rep 5 key:DOWN) shot:pm-3"
pms="$inp $(rep 3 key:DOWN) key:RIGHT $(rep 3 key:DOWN) key:RIGHT $(rep 5 key:DOWN) shot:pms-0 key:RIGHT $(rep 6 key:DOWN) shot:pms-1 $(rep 7 key:DOWN) shot:pms-2 $(rep 5 key:DOWN) shot:pms-3"
art="$inart shot:art-01"
for n in {2..13}; do art+=" key:DOWN shot:art-$(printf %02d $n)"; done
art+=" key:RIGHT shot:bkt-1 $(rep 7 key:DOWN) shot:bkt-2 $(rep 7 key:DOWN) shot:bkt-3"
for r in lc pm pms art mlc alc; do
  case $r in art|alc) m=art;; mlc) m=movie;; *) m=p;; esac
  cp $pre-$m.json $out/state-$r.json
  print -r -- "env BLOCKS=$dir E101_STATE=$out/state-$r.json $NODE $BOOT/play.mjs $out ${(P)r} > $out/$r.out 2>&1"
done | xargs -P ${PAR:-6} -I{} zsh -c "{}"
grep -L "^done at" $out/*.out | sed 's/^/RUN FAILED: /'
ls $out/*.png | wc -l

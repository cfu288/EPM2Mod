#!/bin/zsh
# lang-all.sh IMAGE [LANG...]: the Picture Mode list and the ART list in every menu language.
# IMAGE is a folder of unpacked blocks under $SCRATCH (tools/oetool.py unpack BUILD.BIN $SCRATCH/IMAGE).
# Per language four runs of play.mjs, each from a copy of an English settings state (lang-all/state/p.json = mode P,
# lang-all/state/art.json = ART mode): set the language in Setup Menu -> language grid, then
#   pm:  Shooting Menu 1 -> Picture Mode list, two pages (Portra..Velvia, Superia 400..)
#   pms: Custom Menu D -> Picture Mode Settings list
#   art: top menu -> ART list, the 12 entries and ART BKT (art-01..13), then the ART BKT list (bkt-1, bkt-2)
#   fx:  ART entry 1 -> Add Effects -> first and second effect (the effect's name is the screen title)
# Output: lang-all/IMAGE/NN-CODE/*.png and one .out per run.
# PAR = runs at a time (default 8).
# Place: this file belongs in ~/opt/om-emu-e101-boot-work/lang-all/ (the emulator work folder, outside the repo).
cd ${0:A:h}/.. && . ./env.sh
export E101_RTC=${E101_RTC:-2026-11-14T12:00:00}
img=$1; shift
# the language grid, 3 columns, left to right and top to bottom (read from the grid's own screenshot)
grid=(enu kor chs cht ind msl tha deu plk fra csy nld hun sky slv esp ita ptg srb ell hrv dan sve lvi lth nor eti fin rus ukr rom trk bgr jpn)
langs=($@); (( $#langs )) || langs=($grid)
rep() { local out=(); repeat $1 out+=($2); print -r -- $out }
jobs=()
for l in $langs; do
  k=$(( ${grid[(i)$l]} - 1 )); (( k < 34 )) || { echo "unknown language $l"; exit 2 }
  nav="$(rep $(( k % 3 )) key:RIGHT) $(rep $(( k / 3 )) key:DOWN)"
  out=lang-all/$img/$(printf %02d $(( k + 1 )))-$l; rm -rf $out; mkdir -p $out
  cp lang-all/state/p.json $out/p.json; cp lang-all/state/art.json $out/art.json
  setlang="$(rep 5 key:DOWN) key:RIGHT key:DOWN key:RIGHT $nav shot:grid key:OK"
  inp="w:500 key:MENU key:RIGHT key:OK $setlang key:LEFT"            # mode P: language set, cursor on the wrench tab
  inart="w:500 key:OK w:500 key:MENU key:LEFT key:OK $setlang key:MENU key:MENU w:500 key:MENU key:OK"   # ART list, entry 1
  pm="$inp $(rep 5 key:UP) key:RIGHT key:DOWN key:RIGHT $(rep 5 key:DOWN) shot:pm-1 $(rep 7 key:DOWN) shot:pm-2"
  pms="$inp $(rep 2 key:UP) key:RIGHT $(rep 3 key:DOWN) key:RIGHT $(rep 5 key:DOWN) shot:pms-0 key:RIGHT $(rep 6 key:DOWN) shot:pms-1 $(rep 7 key:DOWN) shot:pms-2 $(rep 5 key:DOWN) shot:pms-3"
  art="$inart shot:art-01"
  for n in {2..13}; do art+=" key:DOWN shot:art-$(printf %02d $n)"; done
  art+=" key:RIGHT shot:bkt-1 $(rep 7 key:DOWN) shot:bkt-2"
  fx="$inart key:RIGHT key:DOWN key:RIGHT key:DOWN shot:fx-1 key:DOWN shot:fx-2"
  for r in pm pms art fx; do
    st=$out/p.json; [[ $r == art || $r == fx ]] && st=$out/art.json
    cp $st $out/state-$r.json
    jobs+=("env BLOCKS=$SCRATCH/$img E101_STATE=$out/state-$r.json $NODE play.mjs $out ${(P)r} > $out/$r.out 2>&1")
  done
done
print -l $jobs | xargs -P ${PAR:-8} -I{} zsh -c "{}"
grep -L "^done at" lang-all/$img/*/*.out | sed 's/^/RUN FAILED: /'
grep -l "^STOP" lang-all/$img/*/*.out | sed 's/^/STOP in: /'
echo "shots: pm-2 $(ls lang-all/$img/*/pm-2.png | wc -l), pms-3 $(ls lang-all/$img/*/pms-3.png | wc -l), bkt-2 $(ls lang-all/$img/*/bkt-2.png | wc -l), fx-2 $(ls lang-all/$img/*/fx-2.png | wc -l)"

#!/bin/zsh
# crawl-all.sh CONFIG IMAGE...: run the menu crawl units of one configuration on the images, PAR (default 8) at a time.
# CONFIG = <mode>-<card|nocard>-<full|shallow>, mode in iauto p movie art.
# IMAGE: stock, data/builds/NAME.json, a .BIN file or a folder of unpacked blocks.
# Output: EMU_OUT/crawl/CONFIG/<image name>/<unit>.NN...png and <unit>.log.json (EMU_OUT default: build/emu/out).
# "full" = DEPTH 4 (every sub-screen, every list scrolled to its end); "shallow" = DEPTH 1 (each row's first
# sub-screen, scrolled). With a card the clock is set too (E101_RTC), as on a camera in use; without a card the
# clock is not set (the emulator's default). Compare two outputs with crawldiff.py, or with crawlcmp.py when one
# image has one more Custom Menu row. Each image starts from its state EMU_STATE/NAME-MODE.json (emulator/mkstate).
. ${0:A:h}/env.sh
(( $# >= 2 )) || { sed -n '2,9p' $0; exit 2 }
cfg=$1; shift; imgs=($@)
mode=${cfg%%-*}; rest=${cfg#*-}; card=${rest%%-*}; depth=${rest#*-}
case $mode in
  iauto) pre=(w:500 key:MENU key:LEFT key:LEFT key:OK);;
  p)     pre=(w:500 key:MENU key:RIGHT key:OK);;
  movie) pre=(w:500 key:MENU key:RIGHT key:RIGHT key:OK);;
  art)   pre=(w:500 key:OK w:500 key:MENU key:LEFT key:OK);;
  *)     echo "unknown mode $mode"; exit 2;;
esac
[[ $depth == full ]] && D=4 || D=1
cardsrc=$EMU_OUT/crawl/cardsrc; mkdir -p $cardsrc/DCIM/100OLYMP
jobs=()
for img in $imgs; do
  out=$EMU_OUT/crawl/$cfg/$(imgname $img); rm -rf $out; mkdir -p $out
  dir=$(blocks $img) || exit 3; st=$(state $img $mode) || exit 3
  envs="BLOCKS=$dir E101_STATE=$st DEPTH=$D"
  [[ $card == card ]] && envs="$envs E101_CARD=$cardsrc E101_RTC=2026-11-14T12:00:00"
  u() { jobs+=("env $envs ${3:+DEPTH=$3} $4 $NODE $BOOT/crawl.mjs $out $1 $pre shot:start $2 > $out/$1.out 2>&1"); }
  u tabs "" 0
  u sm1 "key:RIGHT" "" BUDGET=500; u sm2 "key:DOWN key:RIGHT" "" BUDGET=700; u pb "key:DOWN key:DOWN key:RIGHT"
  u cust "key:DOWN key:DOWN key:DOWN key:RIGHT" 0
  # the Custom Menu's rows are one long list (groups A..K follow each other): walk it in chunks of 8 rows
  if [[ $depth != full ]]; then u custrows "key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT" 0; fi
  # custA: the lists of the rows of group A (shallow runs)
  if [[ $depth != full ]]; then u custA "key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT" 1 "TOPMAX=11"; fi
  g=""; [[ $depth == full ]] && for k in {00..15}; do u custrows$k "key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT $g" "" "TOPMAX=8"; g="$g key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN"; done
  u acc "key:DOWN key:DOWN key:DOWN key:DOWN key:RIGHT" "" BUDGET=400; u setup "key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:RIGHT" "" BUDGET=400
done
# CRAWL_UNITS="tabs cust": run only these units (default: all)
print -l $jobs | { if [[ -n $CRAWL_UNITS ]]; then grep -E "crawl\.mjs [^ ]+ (${CRAWL_UNITS// /|}) "; else cat; fi } | xargs -P ${PAR:-8} -I{} zsh -c "{}"
for img in $imgs; do echo "== $cfg $(imgname $img)"; cat $EMU_OUT/crawl/$cfg/$(imgname $img)/*.out | cut -c1-260; done

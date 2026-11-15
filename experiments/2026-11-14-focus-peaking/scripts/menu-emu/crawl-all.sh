#!/bin/zsh
# crawl-all.sh CONFIG [IMAGES...]: audit/crawl-all.sh with the output under peaking-menu/crawl/ and one settings state for
# every image (audit/state/pinned-<mode>.json: the settings banks do not depend on the image). Default image: peakmenu.
# CONFIG = <mode>-<card|nocard>-<full|shallow>, mode in iauto p movie art. Uses audit/crawl.mjs unchanged.
cd ${0:A:h}/.. && . ./env.sh
cfg=$1; shift; imgs=($@); (( $#imgs )) || imgs=(peakmenu)
mode=${cfg%%-*}; rest=${cfg#*-}; card=${rest%%-*}; depth=${rest#*-}
case $mode in
  iauto) pre=(w:500 key:MENU key:LEFT key:LEFT key:OK);;
  p)     pre=(w:500 key:MENU key:RIGHT key:OK);;
  movie) pre=(w:500 key:MENU key:RIGHT key:RIGHT key:OK); st=m2;;
  art)   pre=(w:500 key:OK w:500 key:MENU key:LEFT key:OK);;
esac
st=${st:-$mode}
[[ $depth == full ]] && D=4 || D=1
jobs=()
for img in $imgs; do
  out=peaking-menu/crawl/$cfg/$img; rm -rf $out; mkdir -p $out
  envs="BLOCKS=$SCRATCH/$img E101_STATE=audit/state/pinned-$st.json DEPTH=$D"
  [[ $card == card ]] && envs="$envs E101_CARD=$SCRATCH/cardsrc-audit E101_RTC=2026-11-14T12:00:00"
  u() { jobs+=("env $envs ${3:+DEPTH=$3} $4 $NODE audit/crawl.mjs $out $1 $pre shot:start $2 > $out/$1.out 2>&1"); }
  u tabs "" 0
  u sm1 "key:RIGHT" "" BUDGET=500; u sm2 "key:DOWN key:RIGHT" "" BUDGET=700; u pb "key:DOWN key:DOWN key:RIGHT"
  u cust "key:DOWN key:DOWN key:DOWN key:RIGHT" 0
  if [[ $depth != full ]]; then u custrows "key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT" 0; fi
  g=""; [[ $depth == full ]] && for k in {00..15}; do u custrows$k "key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT $g" "" "TOPMAX=8"; g="$g key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN"; done
  u acc "key:DOWN key:DOWN key:DOWN key:DOWN key:RIGHT" "" BUDGET=400; u setup "key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:RIGHT" "" BUDGET=400
done
mkdir -p $SCRATCH/cardsrc-audit/DCIM/100OLYMP
print -l $jobs | xargs -P ${PAR:-8} -I{} zsh -c "{}"
for img in $imgs; do echo "== $cfg $img"; cat peaking-menu/crawl/$cfg/$img/*.out | cut -c1-260; done

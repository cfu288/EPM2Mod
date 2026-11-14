#!/bin/zsh
# run-checks.sh [a] [c] [d] [e] [ram] [b]: the emulator checks of the Level Adjust build (level gauge NOTES.md section 12).
# Lives in <emulator work folder>/level-adjust/ next to trace-adjust.mjs, ramcheck.mjs, crawl-all.sh, crawlcmp.py.
# Needs the unpacked images $SCRATCH/pinned and $SCRATCH/leveladj:
#   python3 tools/oetool.py unpack build/seven-films-6-interval-240-level-adjust.BIN $SCRATCH/leveladj
# No argument = a c d e ram (b, the full crawl, takes about 40 minutes on 8 cores).
cd ${0:A:h}/.. && . ./env.sh
W=level-adjust; mkdir -p $W/state
export E101_RTC=2026-11-14T12:00:00
what=($@); (( $#what )) || what=(a c d e ram)
P=(w:500 key:MENU key:RIGHT key:OK)                                   # P mode: top menu -> SETUP (the menus)
J=(key:DOWN key:DOWN key:DOWN key:RIGHT key:UP key:RIGHT)             # Custom Menu -> groups -> J. Utility -> its rows
LA=(key:DOWN key:DOWN key:DOWN)                                       # -> Level Adjust
GAUGE_ON=($P key:DOWN key:DOWN key:DOWN key:RIGHT key:DOWN key:DOWN key:DOWN key:RIGHT key:DOWN key:DOWN key:DOWN key:RIGHT
          key:DOWN key:RIGHT shot:e01-lv-info key:DOWN key:DOWN key:DOWN key:RIGHT key:UP shot:e02-level-gauge-on key:OK
          key:MENU key:MENU key:MENU key:MENU w:800)
for w in $what; do case $w in
a)  # boot test: the report must equal pinned's except the wall time
    for i in pinned leveladj; do BLOCKS=$SCRATCH/$i $NODE stage2-boot.mjs 2000 > $W/boot-$i.txt 2>&1; echo "boot $i: exit $?"; done
    diff <(sed 's/wall ms [0-9]*//' $W/boot-pinned.txt) <(sed 's/wall ms [0-9]*//' $W/boot-leveladj.txt) && echo "(a) boot reports equal";;
e)  # Level Gauge on, INFO cycle (raw level sample): information -> histogram -> image only -> gauge -> information
    cp audit/state/pinned-p.json $W/state/gauge-on.json
    BLOCKS=$SCRATCH/leveladj E101_STATE=$W/state/gauge-on.json $NODE $W/trace-adjust.mjs $W/info $GAUGE_ON raw:0:1000:0 \
      shot:e03-shooting key:INFO w:1000 shot:e04-info1 key:INFO w:1000 shot:e05-info2 key:INFO w:1500 shot:e06-info3 key:INFO w:1000 shot:e07-info4 | grep -v '^-- key';;
c)  # screenshots: the J page with the row, the Reset / Adjust screen
    cp audit/state/pinned-p.json $W/state/c.json
    BLOCKS=$SCRATCH/leveladj E101_STATE=$W/state/c.json $NODE play.mjs $W/screens $P key:DOWN key:DOWN key:DOWN key:RIGHT shot:01-custom-menu \
      key:UP shot:02-custom-menu-j key:RIGHT shot:03-j-utility $LA shot:04-j-utility-level-adjust key:RIGHT shot:05-level-adjust-reset \
      key:DOWN shot:06-level-adjust-adjust key:MENU shot:07-back | tail -2;;
d)  # Adjust at a raw sample of 2 degrees roll, then a restart, then Reset; needs state/gauge-on.json from "e".
    # The first run ends with three INFO presses: the display is then "image only", and one INFO after the restart
    # shows the gauge.
    [[ -f $W/state/gauge-on.json ]] || { echo "run e first"; exit 1; }
    mkdir -p $W/demo; cp $W/state/gauge-on.json $W/state/demo.json
    G=(key:INFO w:1000 key:INFO w:1000 key:INFO w:1500)
    FLASHLOG=1 BLOCKS=$SCRATCH/leveladj E101_STATE=$W/state/demo.json $NODE $W/trace-adjust.mjs $W/demo w:500 raw:35:999:0 $G shot:d01-gauge-2deg-before \
      dump:before ${P:1} $J $LA shot:d04-j-utility-level-adjust key:RIGHT shot:d05-level-adjust-reset key:DOWN shot:d06-level-adjust-adjust \
      key:OK shot:d07-just-after-ok w:2500 shot:d08-back-at-shooting dump:after-adjust $G | grep -v '^-- key\|^shot' > $W/demo/trace-adjust.txt
    cp $W/state/demo.json $W/state/demo2.json
    BLOCKS=$SCRATCH/leveladj E101_STATE=$W/state/demo2.json $NODE $W/trace-adjust.mjs $W/demo w:500 raw:35:999:0 dump:after-restart key:INFO w:1500 \
      shot:e01-gauge-2deg-after-adjust-and-restart raw:0:1000:0 w:1500 shot:e02-gauge-0deg-after-adjust raw:35:999:0 ${P:1} $J $LA key:RIGHT \
      shot:e03-level-adjust-reset key:OK w:1500 shot:e04-back-at-shooting dump:after-reset key:INFO w:1500 shot:e05 key:INFO w:1500 shot:e06 \
      key:INFO w:1500 shot:e07 key:INFO w:1500 shot:e08 key:INFO w:1500 shot:e09 | grep -v '^-- key\|^shot' > $W/demo/trace-reset.txt
    grep -v 'set tag' $W/demo/trace-adjust.txt $W/demo/trace-reset.txt | cut -c1-200;;
ram) # the two bytes after the old end of the row-state array, and the 314 bytes after them
    S=(w:500 chk:boot ${P:1} key:DOWN key:DOWN key:DOWN key:RIGHT chk:groups key:RIGHT chk:group-a-rows key:MENU key:UP key:RIGHT chk:group-j-rows
       key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN chk:after-7-down key:UP key:UP key:UP chk:after-3-up key:MENU key:MENU key:MENU key:MENU
       w:500 key:INFO w:500 key:INFO w:500 key:INFO w:500 key:INFO w:500 key:PLAY w:800 key:PLAY w:500 chk:after-info-and-play)
    for i in pinned leveladj; do cp audit/state/pinned-p.json $W/state/rc.json; echo "## $i"; n=78; [[ $i == leveladj ]] && n=79
      ROWS=$n BLOCKS=$SCRATCH/$i E101_STATE=$W/state/rc.json $NODE $W/ramcheck.mjs $S | tail -8; done | tee $W/ramcheck.txt;;
b)  # menu crawls of the new image; pinned's are the audit's (audit/crawl/<config>/pinned)
    for c in p-card-full p-nocard-shallow iauto-nocard-shallow art-card-shallow movie-card-shallow; do
      $W/crawl-all.sh $c leveladj > $W/crawl-$c.out 2>&1
      python3 $W/crawlcmp.py audit/crawl/$c/pinned $W/crawl/$c/leveladj $W/diff/$c | head -40
    done;;
esac; done

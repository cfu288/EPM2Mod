#!/bin/zsh
# run-checks.sh [a] [c] [d] [ram] [b] [b0]: the emulator checks of the build peaking-menu (focus-peaking NOTES.md section 15).
# Lives in <emulator work folder>/peaking-menu/ next to crawl-all.sh, crawlcmp.py, tagpeek.mjs. It uses ../level-adjust/ramcheck.mjs.
# Needs the unpacked images $SCRATCH/pinned2x and $SCRATCH/peakmenu:
#   python3 tools/oetool.py unpack build/peaking-gain-2x.BIN $SCRATCH/pinned2x
#   python3 tools/oetool.py unpack build/peaking-menu.BIN $SCRATCH/peakmenu
# No argument = a c d ram (b, the full crawls of both images, takes about 90 minutes on 8 cores).
cd ${0:A:h}/.. && . ./env.sh
W=peaking-menu; mkdir -p $W/state $W/screens $W/persist
export E101_RTC=2026-11-14T12:00:00
what=($@); (( $#what )) || what=(a c d ram)
P=(w:500 key:MENU key:RIGHT key:OK)                                   # P mode: top menu -> SETUP (the menus)
A=(key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT)                    # Custom Menu -> groups (cursor on A) -> rows of A
PK=(key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN)   # -> Peaking (row 8 of A, after MF Assist)
for w in $what; do case $w in
a)  # boot test: the report must equal pinned's except the wall time
    for i in pinned2x peakmenu; do BLOCKS=$SCRATCH/$i $NODE stage2-boot.mjs 2000 > $W/boot-$i.txt 2>&1; echo "boot $i: exit $?"; done
    diff <(sed 's/wall ms [0-9]*//' $W/boot-pinned2x.txt) <(sed 's/wall ms [0-9]*//' $W/boot-peakmenu.txt) && echo "(a) boot reports equal";;
c)  # screenshots: group A with the row, the value list, each value
    cp audit/state/pinned-p.json $W/state/c.json
    BLOCKS=$SCRATCH/peakmenu E101_STATE=$W/state/c.json $NODE play.mjs $W/screens $P key:DOWN key:DOWN key:DOWN key:RIGHT shot:01-custom-menu \
      key:RIGHT shot:02-a-first-row ${PK:0:6} shot:03-a-mf-assist key:DOWN shot:04-a-peaking-white key:RIGHT shot:05-peaking-list-white \
      key:DOWN shot:06-peaking-list-black key:UP key:UP shot:07-peaking-list-off key:MENU shot:08-back-unchanged \
      key:RIGHT key:UP key:OK shot:09-a-peaking-off key:RIGHT key:DOWN key:DOWN key:OK shot:10-a-peaking-black \
      key:UP shot:11-mf-assist-row key:RIGHT shot:12-mf-assist-list key:MENU key:DOWN key:DOWN shot:13-set-home | tail -2;;
d)  # the value over a restart: set Black, restart, read the row and the tag; set Off, restart; set White, restart
    cp audit/state/pinned-p.json $W/state/d.json
    go() { BLOCKS=$SCRATCH/peakmenu E101_STATE=$W/state/d.json $NODE $W/tagpeek.mjs $W/persist $@ | grep -v '^-- key\|^shot'; }
    echo "## run 1: fresh state, then set Black"
    go $P $A $PK shot:d01-row-before tag:before key:RIGHT key:DOWN key:OK shot:d02-row-black tag:after-black key:MENU key:MENU key:MENU key:MENU w:800
    echo "## run 2: restart, then set Off"
    go tag:after-restart $P $A $PK shot:d03-row-after-restart key:RIGHT key:UP key:UP key:OK shot:d04-row-off tag:after-off key:MENU key:MENU key:MENU key:MENU w:800
    echo "## run 3: restart, then set White"
    go tag:after-restart $P $A $PK shot:d05-row-after-restart key:RIGHT key:DOWN key:OK shot:d06-row-white tag:after-white key:MENU key:MENU key:MENU key:MENU w:800
    echo "## run 4: restart"
    go tag:after-restart $P $A $PK shot:d07-row-after-restart;;
ram) # the two bytes after the old end of the row-state array (0x606A31B6-B7), and the bytes after them
    S=(w:500 chk:boot ${P:1} key:DOWN key:DOWN key:DOWN key:RIGHT chk:groups key:RIGHT chk:group-a-rows key:MENU key:UP key:RIGHT chk:group-j-rows
       key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN chk:after-7-down key:UP key:UP key:UP chk:after-3-up key:MENU key:MENU key:MENU key:MENU
       w:500 key:INFO w:500 key:INFO w:500 key:INFO w:500 key:INFO w:500 key:PLAY w:800 key:PLAY w:500 chk:after-info-and-play)
    for i in pinned2x peakmenu; do cp audit/state/pinned-p.json $W/state/rc.json; echo "## $i"; n=79; [[ $i == peakmenu ]] && n=80
      ROWS=$n BLOCKS=$SCRATCH/$i E101_STATE=$W/state/rc.json $NODE level-adjust/ramcheck.mjs $S | tail -8; done | tee $W/ramcheck.txt;;
b)  # full menu crawls, P mode, card, clock set: both images
    for i in peakmenu pinned2x; do $W/crawl-all.sh p-card-full $i > $W/crawl-p-card-full-$i.out 2>&1; done
    python3 $W/crawlcmp.py $W/crawl/p-card-full/pinned2x $W/crawl/p-card-full/peakmenu $W/diff/p-card-full | head -40;;
b0) # shallow crawls: P without card, iAUTO, ART, movie
    for c in p-nocard-shallow iauto-nocard-shallow art-card-shallow movie-card-shallow; do
      $W/crawl-all.sh $c pinned2x peakmenu > $W/crawl-$c.out 2>&1
      python3 $W/crawlcmp.py $W/crawl/$c/pinned2x $W/crawl/$c/peakmenu $W/diff/$c | head -40
    done;;
esac; done

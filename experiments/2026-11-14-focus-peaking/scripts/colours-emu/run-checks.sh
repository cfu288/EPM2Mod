#!/bin/zsh
# run-checks.sh [a] [c] [d] [b0]: the emulator checks of the build peaking-colours (focus-peaking NOTES.md section 16).
# Lives in <emulator work folder>/peaking-colours/ next to crawl-all.sh, crawlcmp.py, tagpeek.mjs.
# Needs the unpacked images $SCRATCH/pc-pinned and $SCRATCH/pc-colours:
#   python3 tools/oetool.py unpack build/peaking-menu-names.BIN $SCRATCH/pc-pinned
#   python3 tools/oetool.py unpack build/peaking-colours.BIN $SCRATCH/pc-colours
# No argument = a c d b0.
cd ${0:A:h}/.. && . ./env.sh
W=peaking-colours; mkdir -p $W/state $W/screens $W/persist
export E101_RTC=2026-11-14T12:00:00
what=($@); (( $#what )) || what=(a c d b0)
P=(w:500 key:MENU key:RIGHT key:OK)                                   # P mode: top menu -> SETUP (the menus)
A=(key:DOWN key:DOWN key:DOWN key:RIGHT key:RIGHT)                    # Custom Menu -> groups (cursor on A) -> rows of A
PK=(key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN)   # -> Peaking (row 8 of A, after MF Assist)
OUTM=(key:MENU key:MENU key:MENU key:MENU w:800)
for w in $what; do case $w in
a)  # boot test: the report must equal pinned's except the wall time
    for i in pc-pinned pc-colours; do BLOCKS=$SCRATCH/$i $NODE stage2-boot.mjs 2000 > $W/boot-$i.txt 2>&1; echo "boot $i: exit $?"; done
    diff <(sed 's/wall ms [0-9]*//' $W/boot-pc-pinned.txt) <(sed 's/wall ms [0-9]*//' $W/boot-pc-colours.txt) && echo "(a) boot reports equal";;
c)  # screenshots: group A with the row, the value list with the cursor on each value
    cp audit/state/pinned-p.json $W/state/c.json
    BLOCKS=$SCRATCH/pc-colours E101_STATE=$W/state/c.json $NODE play.mjs $W/screens $P $A $PK shot:01-a-peaking-white \
      key:RIGHT shot:02-list-white key:DOWN shot:03-list-red key:DOWN shot:04-list-yellow key:DOWN shot:05-list-blue \
      key:UP key:UP key:UP key:UP shot:06-list-off key:MENU shot:07-back-unchanged \
      key:UP shot:08-mf-assist-row key:DOWN key:DOWN shot:09-set-home | tail -2;;
d)  # each value over a restart: set it, read the tag, restart, read the tag and the row
    cp audit/state/pinned-p.json $W/state/d.json
    go() { BLOCKS=$SCRATCH/pc-colours E101_STATE=$W/state/d.json $NODE $W/tagpeek.mjs $W/persist $@ | grep -v '^-- key\|^shot'; }
    echo "## run 1: fresh state (White), then set Red"
    go $P $A $PK shot:d01-row-before tag:before key:RIGHT key:DOWN key:OK shot:d02-row-red tag:after-red $OUTM
    echo "## run 2: restart, then set Yellow"
    go tag:after-restart $P $A $PK shot:d03-row-after-restart key:RIGHT key:DOWN key:OK shot:d04-row-yellow tag:after-yellow $OUTM
    echo "## run 3: restart, then set Blue"
    go tag:after-restart $P $A $PK shot:d05-row-after-restart key:RIGHT key:DOWN key:OK shot:d06-row-blue tag:after-blue $OUTM
    echo "## run 4: restart, then set Off"
    go tag:after-restart $P $A $PK shot:d07-row-after-restart key:RIGHT key:UP key:UP key:UP key:UP key:OK shot:d08-row-off tag:after-off $OUTM
    echo "## run 5: restart, then set White"
    go tag:after-restart $P $A $PK shot:d09-row-after-restart key:RIGHT key:DOWN key:OK shot:d10-row-white tag:after-white $OUTM
    echo "## run 6: restart"
    go tag:after-restart $P $A $PK shot:d11-row-after-restart;;
b0) # shallow crawls of both images: P without card, iAUTO, ART, movie; the unit custA opens the lists of group A
    for c in p-nocard-shallow iauto-nocard-shallow art-card-shallow movie-card-shallow; do
      $W/crawl-all.sh $c pc-pinned pc-colours > $W/crawl-$c.out 2>&1
      python3 $W/crawlcmp.py $W/crawl/$c/pc-pinned $W/crawl/$c/pc-colours $W/diff/$c | head -40
    done;;
esac; done

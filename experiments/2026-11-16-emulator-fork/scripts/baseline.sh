#!/bin/zsh
# baseline.sh OUT: raw outputs of the current (old-layout) E-PM2 emulator tools, for comparison after the refactor.
set -u
OUT=$1; mkdir -p $OUT
R=${EPM2_REPO:-$(cd "$(dirname "$0")/../../.." && pwd)}
cd $R
ER=$R/emulator/emu-run
# 1. boot reports (raw, not normalised)
$ER stock stage2-boot.mjs 2000 > $OUT/boot-stock.txt 2>&1; echo "boot-stock exit $?" >> $OUT/exits.txt
$ER builds/films-12.json stage2-boot.mjs 2000 > $OUT/boot-films12.txt 2>&1; echo "boot-films12 exit $?" >> $OUT/exits.txt
# 2. update path: OK held, a card with the stock file as DCOLYMP/E1019999.BIN
mkdir -p $OUT/card/DCOLYMP && cp firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN $OUT/card/DCOLYMP/E1019999.BIN
E101_CARD=$OUT/card $ER stock update-boot.mjs 3000 > $OUT/update-stock.txt 2>&1; echo "update-stock exit $?" >> $OUT/exits.txt
rm -rf $OUT/card
# 3. menus: a play script from the P-mode state, screenshots
cp build/emu/state/stock-p.json $OUT/state-p.json
E101_STATE=$OUT/state-p.json $ER stock play.mjs $OUT/shots shot:00-start key:MENU shot:01-menu key:DOWN shot:02-down key:RIGHT shot:03-right key:DOWN shot:04 key:MENU key:MENU shot:05-back key:INFO shot:06-info key:PLAY shot:07-play > $OUT/play-stock.txt 2>&1; echo "play-stock exit $?" >> $OUT/exits.txt
# 4. a card and the RTC
mkdir -p $OUT/card2/DCIM && echo hello > $OUT/card2/README.TXT
E101_RTC=2026-11-14T12:00:00 E101_CARD=$OUT/card2 $ER stock play.mjs $OUT/shots-card w:1000 shot:10-card key:PLAY shot:11-play > $OUT/play-card.txt 2>&1; echo "play-card exit $?" >> $OUT/exits.txt
# 5. a small crawl
E101_STATE=build/emu/state/stock-p.json MAXLIST=6 DEPTH=1 $ER stock crawl.mjs $OUT/crawl top key:MENU > $OUT/crawl.txt 2>&1; echo "crawl exit $?" >> $OUT/exits.txt
(cd $OUT && sha256sum shots/*.png shots-card/*.png crawl/*.png > pngs.sha256)
echo done

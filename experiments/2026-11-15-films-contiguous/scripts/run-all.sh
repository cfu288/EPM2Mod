#!/bin/zsh
# run-all.sh: every emulator check of this experiment, pinned build against the candidate. About 40 minutes on 8 cores.
# Needs: build/peaking-fast.BIN and build/films-contiguous.BIN (.venv/bin/epm2mod make ...), emulator/setup.sh done.
# Output: build/emu/films-contiguous/ (ignored by git); the lines that matter are printed.
cd ${0:A:h}/../../..
S=${0:A:h}; O=build/emu/films-contiguous
old=builds/peaking-fast.json; new=builds/films-contiguous.json
export E101_RTC=2026-11-14T12:00:00 EMU_OUT=$PWD/$O/out EMU_STATE=$PWD/$O/state
for m in p art movie; do [[ -f $O/state/pinned-$m.json ]] || emulator/mkstate $old $O/state/pinned-$m.json $m; done
echo "== screens"; $S/shots.sh $old pinned; $S/shots.sh $new new
echo "== stored selection"; $S/stored.sh $old $new
echo "== entry pages"; $S/artsub.sh $old $new
echo "== settings written"; $S/settings.sh $old $new
echo "== flags set on the pinned build"; $S/hidden.sh $old $new
echo "== languages"; emulator/boot/lang-all.sh $old enu deu jpn fra; emulator/boot/lang-all.sh $new enu deu jpn fra
.venv/bin/python emulator/boot/sheets.py $O/out/lang-all/peaking-fast $O/sheets-pinned; .venv/bin/python emulator/boot/sheets.py $O/out/lang-all/films-contiguous $O/sheets-new
echo "== crawl"; for c in p-nocard-shallow art-nocard-shallow movie-nocard-shallow; do emulator/boot/crawl-all.sh $c $old $new > $O/crawl-$c.log 2>&1; python3 emulator/boot/crawlcmp.py $O/out/crawl/$c/peaking-fast $O/out/crawl/$c/films-contiguous $O/crawlcmp-$c; done

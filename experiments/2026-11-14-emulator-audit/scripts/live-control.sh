#!/bin/zsh
# live-control.sh IMAGE OUTDIR [STATE]: mode P, OK (live control), UP (Picture Mode), then RIGHT through the strip.
# Shots lc-00 (Natural) .. lc-13; lc-05 = Portra (ART 1), lc-12 = Superia 400 (ART 8).
# STATE = a settings state in mode P (default the English lang-all/state/p.json); a copy is used.
# "live-control.sh IMAGE all": every language folder of lang-all/IMAGE, from the state its "pm" run saved.
# Place: this file belongs in ~/opt/om-emu-e101-boot-work/lang-all/ (the emulator work folder, outside the repo).
cd ${0:A:h}/.. && . ./env.sh
export E101_RTC=${E101_RTC:-2026-11-14T12:00:00}
img=$1; out=$2
S=(w:500 key:OK w:500 key:UP shot:lc-00)
for n in {1..13}; do S+=(key:RIGHT shot:lc-$(printf %02d $n)); done
if [[ $out == all ]]; then
  for d in lang-all/$img/*-*(/); do cp $d/state-pm.json $d/state-lc.json; print -r -- "env BLOCKS=$SCRATCH/$img E101_STATE=$d/state-lc.json $NODE play.mjs $d $S > $d/lc.out 2>&1"; done | xargs -P ${PAR:-8} -I{} zsh -c "{}"
  grep -L "^done at" lang-all/$img/*/lc.out | sed 's/^/RUN FAILED: /'; echo "lc-12 shots: $(ls lang-all/$img/*/lc-12.png | wc -l)"
else
  mkdir -p $out; cp ${3:-lang-all/state/p.json} $out/state-lc.json
  BLOCKS=$SCRATCH/$img E101_STATE=$out/state-lc.json $NODE play.mjs $out $S > $out/lc.out 2>&1; tail -1 $out/lc.out
fi

#!/bin/zsh
# artsub.sh: the screens behind each ART list entry (Filter Type I / II, Add Effects) on the pinned and the new build.
# For each of the 12 entries, by name: go to its place in that build's ART list, then RIGHT and a fixed walk
# through the Filter Type and Add Effects screen, one screenshot per key. cmp_png.py then compares the two
# builds' screens of one entry below the title line (the title line has the entry's place in the list).
# Expected: 0 differ.
# Output: build/emu/films-contiguous/artsub/{pinned,new}/NAME-NN.png
cd ${0:A:h}/../../.. && . emulator/boot/env.sh
export E101_RTC=${E101_RTC:-2026-11-14T12:00:00}
old=${1:-builds/peaking-fast.json}; new=${2:-builds/films-contiguous.json}
st=build/emu/films-contiguous/state/pinned-art.json
out=build/emu/films-contiguous/artsub; rm -rf $out; mkdir -p $out/pinned $out/new
dold=$(blocks $old) || exit 3; dnew=$(blocks $new) || exit 3
rep() { local o=(); repeat $1 o+=($2); print -r -- $o }
names=(portra ektachrome pro400h kodachrome grainy vis250d velvia superia sepia dramatic keyline watercolor)
pold=(1 2 3 4 5 6 7 8 9 10 11 12); pnew=(1 2 3 4 8 5 6 7 9 10 11 12)
walk=(RIGHT RIGHT DOWN DOWN DOWN LEFT DOWN RIGHT DOWN DOWN DOWN DOWN UP LEFT UP)
for i in {1..12}; do
  for b in pinned new; do
    [[ $b == pinned ]] && { d=$dold; p=$pold[i] } || { d=$dnew; p=$pnew[i] }
    s="w:500 $(rep $(( p - 1 )) key:DOWN) shot:$names[i]-00"; k=0
    for w in $walk; do k=$(( k + 1 )); s+=" key:$w shot:$names[i]-$(printf %02d $k)"; done
    cp $st $out/$b/state-$names[i].json
    print -r -- "env BLOCKS=$d E101_STATE=$out/$b/state-$names[i].json $NODE $BOOT/play.mjs $out/$b $s > $out/$b/$names[i].out 2>&1"
  done
done | xargs -P ${PAR:-8} -I{} zsh -c "{}"
grep -L "^done at" $out/*/*.out | sed 's/^/RUN FAILED: /'
# NAME-00 is the list itself (it differs by design); the title line ends at line 39
python3 ${0:A:h}/cmp_png.py $out/pinned $out/new --below 40 --skip -00.png

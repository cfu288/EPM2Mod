#!/bin/sh
# Setting 447 in the emulator, on the pinned build: is a value kept after a restart, and does the start write it?
#   sh experiments/2026-11-18-log-menu/scripts/run_447.sh /tmp/scratch
# A: read 447, then choose Load in J -> Load Looks; the menu's setSetting(449, 0) is turned into setSetting(447, 1).
# B: restart with the RAM banks kept. C: restart from flash only (RAM banks dropped). B and C print setting447.
set -e
W=${1:?a scratch folder}
HERE=$(cd "$(dirname "$0")" && pwd)
cp build/emu/state/card-looks-4-p.json "$W/st.json"
NAV="key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT"
for i in 1 2 3 4 5 6 7 8 9; do NAV="$NAV key:DOWN"; done
NAV="$NAV key:RIGHT"
for i in 1 2 3 4 5; do NAV="$NAV key:DOWN"; done
run() { E101_STATE="$W/st.json" SAVE=1 emulator/emu-run builds/card-looks-4.json "$HERE/prm447.mjs" "$@" 2>&1 | grep -v '^ '; }
echo "== A"; SWAP=1 run key:INFO $NAV key:RIGHT key:DOWN key:OK w:1000 key:MENU key:MENU w:1500
echo "== B: RAM kept"; run key:INFO w:3000
python3 -c "import json,sys; p=sys.argv[1]; d=json.load(open(p)); d.pop('ram',None); json.dump(d,open(p,'w'))" "$W/st.json"
echo "== C: flash only"; run key:INFO w:1000

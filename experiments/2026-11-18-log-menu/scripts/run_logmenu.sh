#!/bin/zsh
# The emulator checks L2-L4 of builds/log-menu.json (design.md): five sessions on one settings state and one card folder.
#   emulator/mkstate builds/log-menu.json build/emu/state/log-menu-p.json p     (once)
#   zsh experiments/2026-11-18-log-menu/scripts/run_logmenu.sh /tmp/scratch/logmenu
# 1 row Off (default): menu and playback; the ring keeps its start-up records only, no card write; screenshots of J.
# 2 row On: menu and playback; EPM2LOG.BIN appears and decodes.
# 3 restart with the row On: log_setting at the first GUI state; Load Looks -> Load gives card_task load / Loaded.
# 4 row Off again: menu and playback.  5 restart with Off: Load Looks -> Built-in; the file does not grow.
set -e
W=${1:?a scratch folder}
rm -rf $W; mkdir -p $W/card/DCIM/100OLYMP
cp build/emu/state/log-menu-p.json $W/st.json
uv run epm2mod films set --film ART1=velvia --film ART2=portra-400 -o $W/card/EPM2LOOK.BIN > /dev/null 2>&1
J=(key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN
   key:DOWN key:DOWN key:DOWN key:RIGHT key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN)       # Custom Menu J, Load Looks
LOG=($J key:DOWN)                                                                          # Debug Log
OUT=(key:MENU key:MENU key:MENU key:MENU w:500 key:PLAY w:800 key:PLAY w:500)
run() { E101_STATE=$W/st.json E101_CARD=$W/card E101_RTC=2026-11-18T12:00:00 emulator/emu-run builds/log-menu.json \
          logplay.mjs $W/$1 ${@:2} 2>&1 | grep -E '^ring .* cpu0|^card|^STOP' | sed "s/^/  $1 /"; }
size() { [[ -f $W/card/EPM2LOG.BIN ]] && echo "  file: $(stat -c %s $W/card/EPM2LOG.BIN) B" || echo "  file: none"; }
echo "1 Off"; run s1 w:500 ring:start $LOG shot:j-row key:RIGHT shot:j-list $OUT ring:end; size
echo "2 On"; run s2 w:500 $LOG key:RIGHT key:DOWN key:OK w:500 shot:j-on $OUT ring:end; size
echo "3 restart On, Load"; run s3 w:500 $J key:RIGHT key:DOWN key:OK w:1500 key:UP key:DOWN shot:load-row $OUT ring:end; size
echo "4 Off"; run s4 w:500 $LOG key:RIGHT key:UP key:OK w:500 shot:j-off ring:off $OUT ring:end; size
echo "5 restart Off, Built-in"; run s5 w:500 ring:start $J key:RIGHT key:DOWN key:DOWN key:OK w:1500 key:UP key:DOWN \
  shot:load-builtin $OUT ring:end; size
uv run epm2mod log $W/card/EPM2LOG.BIN | head -4
uv run epm2mod log $W/card/EPM2LOG.BIN --json | python3 -c 'import json, sys; [print(json.dumps(e)) for e in json.load(sys.stdin)["events"]]' | grep -E '"(log_setting|card_task)"' | cut -c1-200

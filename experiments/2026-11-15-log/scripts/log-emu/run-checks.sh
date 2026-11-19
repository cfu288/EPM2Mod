#!/bin/zsh
# run-checks.sh [a] [b] [c] [d] [e] [f] [g] [h]: the emulator checks of the build debug-log (epm2-tools
# experiments/2026-11-15-log/NOTES.md). Lives in <emulator work folder>/log/ next to logplay.mjs, crawl-all.sh,
# crawlcmp.py, crawls.sh. Needs the unpacked images $SCRATCH/log-pinned and $SCRATCH/log-debug:
#   python3 tools/oetool.py unpack build/peaking-colours.BIN $SCRATCH/log-pinned
#   python3 tools/oetool.py unpack build/debug-log.BIN $SCRATCH/log-debug
# and the decoder: $EPM2_REPO/.venv/bin/epm2mod. No argument = a b c d e f g h. The menu crawls are crawls.sh.
cd ${0:A:h}/.. && . ./env.sh
W=log; DEC=$EPM2_REPO/.venv/bin/epm2mod
events() { $DEC log $1 --json | python3 -c 'import json, sys; [print(json.dumps(e)) for e in json.load(sys.stdin)["events"]]'; }  # the events, a JSON line each
export E101_RTC=2026-11-14T12:00:00
what=($@); (( $#what )) || what=(a b c d e f g h)
card() { rm -rf $SCRATCH/$1; mkdir -p $SCRATCH/$1/DCIM/100OLYMP; }
state() { cp audit/state/pinned-p.json $SCRATCH/$1.json; }
brief() { python3 -c '
import sys, json
for l in sys.stdin:
    d = json.loads(l)
    if "marker" in d: print("   ", json.dumps(d)); continue
    print("    cpu %d seq %3d session %d %8.1f ms %-14s %s%s" % (d["cpu"], d["seq"], d["session"], d["time_us"] / 1000, d["event"], json.dumps(d["args"], separators=(",", ":")), "  RECOVERED" if d.get("recovered") else ""))'; }
# the session of the notes: quick menu Natural -> Portrait, Custom Menu J -> Level Adjust -> Reset, Custom Menu A -> Peaking -> Red, playback
SESSION=(w:500 key:OK key:UP shot:01-quick-menu-picture-mode key:RIGHT key:RIGHT shot:02-picture-mode-portrait key:OK w:500 shot:03-shooting
  key:MENU key:RIGHT key:OK key:DOWN key:DOWN key:DOWN key:RIGHT key:UP shot:04-custom-menu-J key:RIGHT key:DOWN key:DOWN key:DOWN shot:05-level-adjust-row
  key:RIGHT shot:06-level-adjust-reset key:OK w:2500 shot:07-after-reset key:MENU key:MENU
  key:DOWN key:RIGHT key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN key:DOWN shot:08-peaking-row key:RIGHT shot:09-peaking-list key:DOWN key:OK shot:10-peaking-red
  key:MENU key:MENU key:MENU key:MENU w:500 shot:11-shooting key:PLAY w:800 shot:12-playback)
for w in $what; do case $w in
a)  # boot test: the report must equal pinned's except the wall time and what the new code adds
    for i in log-pinned log-debug; do BLOCKS=$SCRATCH/$i $NODE stage2-boot.mjs 2000 > $W/boot-$i.txt 2>&1; echo "(a) boot $i: exit $?"; done
    diff <(sed 's/wall ms [0-9]*//' $W/boot-log-pinned.txt) <(sed 's/wall ms [0-9]*//' $W/boot-log-debug.txt) > $W/boot-diff.txt; echo "(a) lines that differ: $(grep -c '^[<>]' $W/boot-diff.txt) (in $W/boot-diff.txt)";;
b)  # the session with a card: the log file appears in the host folder and decodes
    card logcard; state lb
    BLOCKS=$SCRATCH/log-debug E101_STATE=$SCRATCH/lb.json E101_CARD=$SCRATCH/logcard $NODE $W/logplay.mjs $W/session $SESSION ring:end > $W/session.txt 2>&1
    grep 'ring end\|card\|done\|STOP' $W/session.txt | cut -c1-200
    events $SCRATCH/logcard/EPM2LOG.BIN > $W/session.jsonl && cp $SCRATCH/logcard/EPM2LOG.BIN $W/session-EPM2LOG.BIN && brief < $W/session.jsonl | tee $W/session-brief.txt;;
c)  # a second run with the same card folder appends a second session
    state lc
    BLOCKS=$SCRATCH/log-debug E101_STATE=$SCRATCH/lc.json E101_CARD=$SCRATCH/logcard $NODE $W/logplay.mjs $W/tmp w:500 key:MENU key:MENU key:PLAY ring:end 2>&1 | grep 'ring end cpu0\|card ->\|STOP'
    events $SCRATCH/logcard/EPM2LOG.BIN > $W/two-sessions.jsonl
    python3 -c '
import sys, json, collections
c = collections.Counter(); m = []
for l in open(sys.argv[1]):
    d = json.loads(l)
    if "marker" in d: m.append(d)
    else: c[d["session"]] += 1
print("(c) records per session:", dict(c), "markers:", m)' $W/two-sessions.jsonl;;
d)  # no card: no hang, the same screens as pinned
    for i in log-pinned log-debug; do state ld; BLOCKS=$SCRATCH/$i E101_STATE=$SCRATCH/ld.json $NODE $W/logplay.mjs $W/nocard-$i $SESSION ring:end > $W/nocard-$i.txt 2>&1; done
    grep 'ring end\|done\|STOP' $W/nocard-log-debug.txt | cut -c1-160
    n=0; for f in $W/nocard-log-pinned/*.png; do cmp -s $f $W/nocard-log-debug/${f:t} || { echo "(d) differs: ${f:t}"; n=$((n+1)); }; done; echo "(d) screens that differ from pinned: $n of $(ls $W/nocard-log-pinned/*.png | wc -l)"
    for i in log-pinned log-debug; do state ld; BLOCKS=$SCRATCH/$i E101_STATE=$SCRATCH/ld.json E101_CARD=$SCRATCH/cardsrc-audit $NODE $W/logplay.mjs $W/card-$i $SESSION > $W/card-$i.txt 2>&1; done
    n=0; for f in $W/card-log-pinned/*.png; do cmp -s $f $W/card-log-debug/${f:t} || { echo "(d) with card differs: ${f:t}"; n=$((n+1)); }; done; echo "(d) with a card: screens that differ from pinned: $n of $(ls $W/card-log-pinned/*.png | wc -l)";;
e)  # ring overflow: 700 records from interrupt context before the first flush; and records of CPU1
    card logcard-e; state le
    BLOCKS=$SCRATCH/log-debug E101_STATE=$SCRATCH/le.json E101_CARD=$SCRATCH/logcard-e $NODE $W/logplay.mjs $W/tmp w:500 burst:700 ring:burst cpu1:3 key:MENU ring:flushed 2>&1 | grep 'ring.*cpu\|card ->\|STOP'
    events $SCRATCH/logcard-e/EPM2LOG.BIN > $W/overflow.jsonl
    python3 -c '
import sys, json
L = [json.loads(l) for l in open(sys.argv[1])]
print("(e) markers:", [d for d in L if "marker" in d])
r = [d for d in L if "marker" not in d]
print("(e) records: cpu0 %d (seq %d..%d), cpu1 %d" % (sum(d["cpu"] == 0 for d in r), min(d["seq"] for d in r if d["cpu"] == 0), max(d["seq"] for d in r if d["cpu"] == 0), sum(d["cpu"] == 1 for d in r)))' $W/overflow.jsonl;;
f)  # a restart that finds the ring in RAM (what a crash and the camera's own restart would leave, if the RAM is kept)
    card logcard-f; state lf
    BLOCKS=$SCRATCH/log-debug E101_STATE=$SCRATCH/lf.json E101_CARD=$SCRATCH/logcard-f $NODE $W/logplay.mjs $W/tmp w:500 key:MENU key:MENU burst:5 ring:A save:$SCRATCH/ringA.bin 2>&1 | grep 'ring A cpu0\|card ->'
    BLOCKS=$SCRATCH/log-debug E101_STATE=$SCRATCH/lf.json E101_CARD=$SCRATCH/logcard-f $NODE $W/logplay.mjs $W/tmp seed:$SCRATCH/ringA.bin w:500 ring:B key:MENU ring:B-flushed 2>&1 | grep 'ring B.* cpu0\|card ->'
    events $SCRATCH/logcard-f/EPM2LOG.BIN > $W/restart.jsonl; brief < $W/restart.jsonl | sed -n '18,32p' | tee $W/restart-brief.txt;;
g)  # the firmware-error hook: the two known start-up errors, by the emulator's own observer and in the log
    grep -o 'firmware error log entries.*' $W/boot-log-debug.txt | cut -c1-200
    grep '"fw_error' $W/session.jsonl | cut -c1-200
    # RAM: the pinned image leaves the whole gap after the kernel zero through the same session
    state lg; BLOCKS=$SCRATCH/log-pinned E101_STATE=$SCRATCH/lg.json E101_CARD=$SCRATCH/cardsrc-audit $NODE $W/logplay.mjs $W/tmp w:500 gap:boot $SESSION key:PLAY key:INFO key:POWER w:2000 gap:end 2>&1 | grep '^gap\|STOP';;
h)  # many flushes: every record must be in the file once and in order, whatever the card commands do
    for run in 1 2; do
      card logcard-h; state lh; K=(); for i in {1..40}; do K+=(key:MENU); done; [[ $run == 2 ]] && K=(burst:3 $K key:PLAY key:PLAY key:MENU)
      BLOCKS=$SCRATCH/log-debug E101_STATE=$SCRATCH/lh.json E101_CARD=$SCRATCH/logcard-h $NODE $W/logplay.mjs $W/tmp w:500 $K ring:end 2>&1 | grep 'ring end cpu0\|card ->\|STOP'
      events $SCRATCH/logcard-h/EPM2LOG.BIN | python3 -c '
import sys, json, collections
L = [json.loads(l) for l in sys.stdin]
seqs = [d["seq"] for d in L if "marker" not in d]
print("(h) records in the file: %d, in order from 0 with none missing or twice: %s; markers: %s" % (len(seqs), seqs == list(range(len(seqs))), [d for d in L if "marker" in d]))
print("(h) results of the flushes:", dict(collections.Counter(d["args"]["previous"]["result"] for d in L if d.get("event") == "flush")))'
    done;;
esac; done

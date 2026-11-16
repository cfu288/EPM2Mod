#!/bin/bash
# shots.sh IMAGE_DIR STATE.json OUTDIR: the screenshots of results/ (run from the repository root).
#   IMAGE_DIR  an image unpacked by `python3 tools/oetool.py unpack FILE.BIN IMAGE_DIR` (keep it outside the repository)
#   STATE.json made by `tools/emu/mkstate IMAGE_DIR STATE.json p`; this script works on a copy
# The emulator's A/D input 0 is the battery voltage input (the battery module's channel 4): 800 counts give 75 %,
# 728 counts give 30 %. The label shows from 3 s after power-on, at the next refresh of the screen (here: INFO).
set -e
cp "$2" "$3.state.json"
E101_STATE="$3.state.json" tools/emu/emu-run "$1" play.mjs "$3" \
  adc:0:800 w:2500 key:INFO key:INFO key:INFO key:INFO shot:osd-battery-75 \
  adc:0:728 w:2500 key:MENU key:MENU w:500 shot:osd-battery-30 key:INFO shot:osd-battery-image-only
rm -f "$3.state.json"

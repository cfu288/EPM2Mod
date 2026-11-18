#!/bin/sh
# Double-click to start EPM2Mod on a Mac. The first time, macOS blocks it: System Settings -> Privacy & Security ->
# Open Anyway, then Open.
exec "$(dirname "$0")/start.sh" "$@"

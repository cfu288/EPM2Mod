#!/bin/sh
# Double-click to start EPM2Mod on a Mac. The first time, macOS blocks it: System Settings -> Privacy & Security ->
# Open Anyway, then Open.
"$(dirname "$0")/start.sh" "$@" || exit
# after a double-click that ended without an error, close this Terminal window (an error stays on screen)
if [ $# -eq 0 ] && [ "${TERM_PROGRAM:-}" = Apple_Terminal ] && TTY=$(tty); then
  (sleep 1; osascript -e 'on run argv' -e 'tell application "Terminal"' -e 'repeat with w in windows' \
    -e 'if tty of selected tab of w is item 1 of argv then close w' -e 'end repeat' -e 'end tell' -e 'end run' \
    "$TTY") >/dev/null 2>&1 &
fi

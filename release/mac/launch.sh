#!/bin/sh
# EPM2Mod.app's start (in Contents/Resources). The app is read-only and signed, so this copies the release folder in
# it (EPM2Mod/) to ~/Library/Application Support/EPM2Mod and starts it there with start.sh. The downloads (uv, Python,
# Olympus's firmware) stay in that folder between starts: the same from the disk image and from Applications.
#   launch.sh            open the installer page in the browser (what the app does)
#   launch.sh ARGS       start.sh ARGS, for tests
set -u
SRC="$(cd "$(dirname "$0")" && pwd)/EPM2Mod"
DEST="$HOME/Library/Application Support/EPM2Mod"
LOG="$DEST/start.log"

# a message in a dialog; without osascript (a test on Linux), on stderr
message() {
  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'on run argv' -e 'activate' \
      -e 'display dialog (item 1 of argv) with title "EPM2Mod" buttons {"OK"} default button 1 giving up after 120' \
      -e 'end run' "$1" >/dev/null 2>&1
  else
    echo "$1" >&2
  fi
}

# one server: a start while one runs opens its page (the log holds its address, with the page's token)
PID=$(cat "$DEST/server.pid" 2>/dev/null) || PID=
if [ $# -eq 0 ] && [ -n "$PID" ] && ps -p "$PID" -o command= 2>/dev/null | grep -q launch.sh; then
  for _ in $(seq 60); do
    URL=$(sed -n 's/^EPM2Mod is open in your browser: //p' "$LOG" 2>/dev/null | tail -n 1)
    [ -n "$URL" ] && { open "$URL"; exit 0; }
    sleep 1
  done
fi

mkdir -p "$DEST" || { message "EPM2Mod could not make its folder: $DEST"; exit 1; }
# a new or changed app: replace the code and data, keep the downloads and the log
if ! diff -rq -x .uv -x firmware -x build -x start.log -x __pycache__ "$SRC" "$DEST" >/dev/null 2>&1; then
  find "$DEST" -mindepth 1 -maxdepth 1 ! -name .uv ! -name firmware ! -name build ! -name start.log -exec rm -rf {} +
  # u+w: a copy keeps the app's modes, and the next new app must be able to replace it
  cp -R "$SRC/." "$DEST/" && chmod -R u+w "$DEST" || { message "EPM2Mod could not copy its files to $DEST"; exit 1; }
fi

cd "$DEST" || exit 1
if [ $# -eq 0 ]; then
  echo $$ > server.pid
  trap 'rm -f server.pid' EXIT
fi
if ! ./start.sh "$@" >"$LOG" 2>&1; then
  message "EPM2Mod stopped with an error:

$(tail -n 3 "$LOG")

The full log is in $LOG"
  exit 1
fi
